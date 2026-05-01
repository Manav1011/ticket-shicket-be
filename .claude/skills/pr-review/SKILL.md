---
name: pr-review
description: >
  Automated pull request code review using multiple specialized agents with confidence-based scoring
  to filter false positives. Supports both GitHub (gh CLI) and GitLab (glab CLI). Uses graphify
  graph reports for smart context loading when available. Use this skill whenever the user asks to
  review a PR, merge request, pull request, do a code review, check a PR, audit changes, or any
  variant of reviewing code changes on GitHub or GitLab. Trigger even on casual phrasing like
  "look at my PR", "check this MR", "review my changes", or "what do you think of this PR".
---

# PR Review Skill

Automated PR/MR review using multiple specialized agents, confidence-based scoring, compulsory
codebase understanding, and surgical per-file diff fetching — all optimized for **accurate,
actionable reviews** rather than high volume of findings.

The guiding principle: **fewer, more certain issues are better than many vague ones.**
Every agent is expected to read deeply and think carefully before flagging anything.

---

## Step 0 — Platform Detection

**First step always**: detect which platform and CLI to use.

```bash
git remote -v | grep -iE "github|gitlab"
```

- **GitHub** → use `gh` CLI. See `references/github.md`
- **GitLab** → use `glab` CLI. See `references/gitlab.md`

If both remotes exist, prefer the one matching the current PR/MR context, or ask the user.

---

## Step 1 — Eligibility Check (Haiku agent)

Check if the PR/MR should be reviewed. Skip if:
- Closed / merged already
- Draft / WIP
- Trivial or automated (e.g., dependency bumps, bot PRs)
- Already has a review from you in this session

See platform reference for exact CLI commands.

---

## Step 2 — Get Changed File List & Filter

Fetch only the list of changed files first — do NOT fetch the full diff yet.

```bash
# GitHub
gh pr diff <PR_NUMBER> --name-only

# GitLab
glab mr diff <MR_IID> --name-only
```

Immediately filter out any files matching these exclusion patterns — they must never
be read or reviewed by any agent, at any point in the pipeline:

| Exclusion | Reason |
|-----------|--------|
| `graphify-out/**` | Auto-generated analysis artifacts |
| `superpowers/plans/**` | Internal planning docs, not code |
| `docs/plans/**` | Internal planning docs, not code |
| `**/plans/**` | Internal planning docs, not code |
| `**/*.lock` | Lockfiles — auto-generated |
| `**/dist/**` | Build output |
| `**/build/**` | Build output |
| `**/__pycache__/**` | Python bytecode |

Store the **clean file list** (after filtering) — this is what all subsequent steps work from.
If the entire PR consists only of excluded files, skip the review entirely.

---

## Step 3 — Codebase Understanding (COMPULSORY — Sonnet agent)

**This step is mandatory. Do not skip it, do not shortcut it.**

Shallow codebase context produces shallow, generic reviews. Before any review agent launches,
a dedicated Sonnet agent must build a deep understanding of the codebase and the changed files'
role within it. This summary is injected into every review agent.

### 3a — Graphify (preferred, use if available)

```bash
ls graphify-out/GRAPH_REPORT.md 2>/dev/null && echo "EXISTS" || echo "MISSING"
ls graphify-out/wiki/index.md 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

**If `graphify-out/GRAPH_REPORT.md` exists:**
1. Read it to identify:
   - High-connectivity nodes (files many others depend on)
   - Module clusters and architectural boundaries
   - Which changed files are "central" vs "leaf" nodes in the graph
2. If `graphify-out/wiki/index.md` exists, navigate it to find wiki pages for
   each changed module — read those wiki pages instead of raw source files.
   The wiki is a structured, pre-digested view of the codebase — always prefer it.
3. Never read files under `graphify-out/` that appear in the PR diff.

**After modifying any code files in the session, rebuild the graph:**
```bash
python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

### 3b — Manual Understanding (if no graphify)

If graphify is not available, the context agent must build understanding manually.
This is not optional — do the work.

1. **Directory structure** — understand the module layout:
   ```bash
   find . -type f \( -name "*.ts" -o -name "*.py" -o -name "*.go" -o -name "*.rs" -o -name "*.js" \) \
     | grep -v node_modules | grep -v dist | grep -v graphify-out | grep -v __pycache__ | head -80
   ```

2. **Root orientation files** (read if present):
   - `README.md` — overall project purpose and architecture
   - `CLAUDE.md` — conventions and patterns
   - Architecture docs in `docs/` (skip `docs/plans/`)

3. **For each file in the clean file list** — read its top-level structure:
   - Imports and what they reveal about dependencies
   - Exported functions, classes, types
   - Any module-level comments explaining intent
   - Do NOT read the entire file — focus on structure and signatures

4. **Blast radius per changed file** — find what depends on it:
   ```bash
   # Adjust pattern to match the language/import style
   grep -r "from ['\"].*<module_name>" --include="*.ts" -l 2>/dev/null | head -20
   grep -r "import <module_name>" --include="*.py" -l 2>/dev/null | head -20
   ```

5. **Read the actual file content** for any changed file that is:
   - High-connectivity (many dependents)
   - Touching authentication, payments, data storage, or other critical paths
   - Small enough to read fully (<200 lines)

### 3c — Context Summary Output

The context agent produces this structured summary, passed to all review agents:

```
CODEBASE CONTEXT SUMMARY
========================
Architecture: <description of overall structure and patterns>

Changed files analysis:
  - <file>: <central|leaf> node
    Depended on by: <list of key dependents or "N modules">
    Role: <what this file does in the system>
    Risk level: <high|medium|low> — <reason>

Key codebase patterns:
  - <pattern agents should be aware of when reviewing>

Conventions (from CLAUDE.md / README):
  - <convention 1>
  - <convention 2>

Watch carefully:
  - <any architectural concerns raised by these specific changes>
```

The "Watch carefully" section is the most important — it tells review agents where
to focus their deepest scrutiny based on what was actually changed.

---

## Step 4 — Gather Guidelines (Haiku agent)

Collect relevant guideline files:
- Root `CLAUDE.md` (if exists)
- `CLAUDE.md` files in directories containing any file from the clean file list
- If graphify wiki exists, note relevant wiki pages for changed modules

Return file paths only — agents fetch contents themselves when needed.

---

## Step 5 — Summarize the PR (Haiku agent)

Fetch the PR/MR metadata and return:
- Title, description, and stated intent
- Which files changed (from the clean file list)
- Which changed files were flagged as high-risk in the context summary
- Any linked issues or tickets that clarify intent

---

## Step 6 — Per-File Diff Fetching Strategy

All review agents fetch diffs **per file, on demand** — never the full diff at once.

```bash
# GitHub — diff for a specific file
gh pr diff <PR_NUMBER> -- path/to/file.ts

# GitLab — diff for a specific file
glab mr diff <MR_IID> -- path/to/file.ts
```

**Each agent must:**
1. Start from the clean file list (Step 2)
2. Decide which files are relevant to its specific focus area
3. Fetch diffs for those files individually
4. Read surrounding file context (full file or relevant sections) when the diff
   alone is insufficient to understand correctness — this is expected and encouraged
   for high-risk files

**Never** fetch the full PR diff in one call. Surgical fetching keeps context clean
and ensures each agent is reasoning about code it has fully read, not skimming.

---

## Step 7 — Launch Review Agents

Each agent receives:
- The clean file list (Step 2)
- The codebase context summary (Step 3)
- The CLAUDE.md file paths (Step 4)
- The PR summary (Step 5)
- Instructions to fetch per-file diffs on demand (Step 6)

**Accuracy mandate given to every agent:**
> Your job is not to find as many issues as possible. Your job is to find real issues
> that will actually matter in production. Before flagging anything, fetch the full
> context of that file, understand how it fits in the codebase, and verify the issue
> is real. One well-verified finding is worth more than ten uncertain ones.

### Mandatory Agents (always run in parallel)

**Agent #1 — CLAUDE.md Compliance (Sonnet)**
- Fetch relevant CLAUDE.md guideline files + per-file diffs for changed files
- Only flag an issue if the guideline **explicitly and specifically** mentions it
- Vague general guidance does not count — must be a direct match

**Agent #2 — Bug Scan (Sonnet)**
- Start with files flagged as high-risk in the codebase context summary
- Fetch per-file diffs, then read surrounding code before flagging anything
- Focus on bugs that will actually be hit in practice — not theoretical edge cases
- One well-verified bug is worth more than five uncertain ones

### Conditional Agent (only if high-risk files exist)

**Agent #3 — Git Blame & History (Sonnet)**

Only spawn this agent if the codebase context summary from Step 3 flagged **at least one
changed file as high-risk** (e.g. central node, auth, payments, data storage, or
high-connectivity module).

If spawned:
- Run `git blame` and `git log` only on the high-risk files — not all changed files
- Look specifically for regressions (same code was fixed before) or changes that
  contradict an intentional pattern visible in the history
- Skip files that are leaf nodes or low-connectivity — not worth the time

```bash
git blame path/to/high-risk-file.ts
git log --oneline -20 -- path/to/high-risk-file.ts
```

If no high-risk files exist, skip this agent entirely.

---

**All agents must use the codebase context summary to:**
- Prioritize scrutiny on high-risk / high-connectivity files
- Avoid flagging things that follow established codebase patterns
- Distinguish intentional design decisions from actual mistakes
- Calibrate severity — a bug in a central auth module is more critical than in a utility helper

**Files agents must never read or comment on:**
- `graphify-out/**`
- `superpowers/plans/**`, `docs/plans/**`, `**/plans/**`
- `**/*.lock`, `**/dist/**`, `**/build/**`, `**/__pycache__/**`

**False positives — agents must not flag these:**
- Pre-existing issues not introduced in this PR
- Things a linter, typechecker, or compiler would catch
- Nitpicks a senior engineer wouldn't raise in a real review
- General quality issues unless explicitly required by CLAUDE.md
- Issues silenced by lint-ignore / type-ignore comments
- Intentional functional changes clearly tied to the PR's stated goal
- Real issues on lines the user did not modify
- Issues in excluded files

---

## Step 8 — Score Each Issue (parallel Haiku agents, one per issue)

Each issue from Step 7 gets independently scored by a separate Haiku agent.
The scorer receives: the PR, the issue description, the relevant file diff, and the CLAUDE.md paths.

The scorer must **re-read the relevant code** before scoring — not just trust the review agent's description.

| Score | Meaning |
|-------|---------|
| 0 | False positive — doesn't survive light scrutiny, or pre-existing |
| 25 | Might be real but couldn't verify, or stylistic without explicit CLAUDE.md backing |
| 50 | Verified real but minor, or unlikely to be hit often in practice |
| 75 | Double-checked, very likely real, directly impacts functionality or explicitly in CLAUDE.md |
| 100 | Confirmed with direct evidence, will be hit frequently in practice |

**For CLAUDE.md issues:** verify the guideline explicitly and specifically mentions this issue
before scoring above 50. Vague general guidance does not count.

**Filter: drop any issue scoring below 80.**

If no issues remain, do not post a comment — this is a valid and good outcome.

---

## Step 9 — Re-check Eligibility (Haiku agent)

Re-run the Step 1 eligibility check to confirm the PR is still open and unreviewed before posting.

---

## Step 10 — Post Review Comment

Use the platform CLI to post the comment. Follow the exact output format in the relevant
reference file — brief, no emojis, each issue linked to the precise file + line range with full SHA.

---

## Reference Files

- `references/github.md` — GitHub CLI commands, output format, link format rules
- `references/gitlab.md` — GitLab CLI commands, output format, link format rules
