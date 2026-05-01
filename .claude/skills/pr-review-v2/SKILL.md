---
name: pr-review-v2
description: >
  Automated pull request code review using a single sequential agent. Uses graphify
  graph reports for smart context loading when available. Supports GitHub (gh CLI) and
  GitLab (glab CLI). Trigger whenever the user asks to review a PR, merge request, pull
  request, do a code review, check a PR, or any variant.
---

# PR Review Skill

Single-agent review. Keeps graphify intelligence for focusing on high-risk files,
but runs sequentially without multi-agent overhead. Fast and concise.

---

## Step 1 — Platform Detection

```bash
git remote -v | grep -iE "github|gitlab"
```

- **GitHub** → use `gh` CLI. See `references/github.md`
- **GitLab** → use `glab` CLI. See `references/gitlab.md`

---

## Step 2 — Eligibility Check

Skip if:
- PR/MR is closed / merged
- Draft / WIP
- Trivial (dependency bumps, bot PRs)

```bash
# GitHub
gh pr view {PR_NUMBER} --state --jq '.state' 2>/dev/null

# GitLab
glab mr view {MR_IID} --output json 2>/dev/null | jq .state
```

---

## Step 3 — Get PR Metadata

```bash
# GitHub
gh api repos/{owner}/{repo}/pulls/{PR_NUMBER} 2>/dev/null

# GitLab
glab mr view {MR_IID} 2>/dev/null
```

Extract: title, body, state, base branch, head branch, changed_files count, commits count, additions/deletions.

---

## Step 4 — Get Changed Files

```bash
# GitHub
gh pr diff {PR_NUMBER} --name-only 2>/dev/null

# GitLab
glab mr diff {MR_IID} --name-only 2>/dev/null
```

Filter out (never read or review these):
- `graphify-out/**`
- `**/plans/**`, `docs/plans/**`, `superpowers/plans/**`
- `**/*.lock`, `**/dist/**`, `**/build/**`, `**/__pycache__/**`

---

## Step 5 — Codebase Context (use graphify if available)

```bash
ls graphify-out/GRAPH_REPORT.md 2>/dev/null && echo "EXISTS" || echo "MISSING"
ls graphify-out/wiki/index.md 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

**If graphify-out/GRAPH_REPORT.md exists:**
1. Read it to identify which changed files are high-connectivity ("central") vs low-connectivity ("leaf")
2. High-connectivity files = higher review priority
3. If `graphify-out/wiki/index.md` exists, navigate it to find wiki pages for changed modules instead of reading raw source files
4. Never read files under `graphify-out/` that appear in the PR diff

**rebuild the graph at stat to make sure the graph is latest:**
```bash
python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

**If no graphify available — manual approach:**
1. Read top-level module structure via `find` (exclude graphify-out, __pycache__)
2. Read `CLAUDE.md` for conventions
3. Focus on: models, service, repository, auth/payment files as high-risk

---

## Step 6 — Review Strategy

**Priority order for scanning:**
1. High-connectivity files from graphify (or models/service/repository files manually)
2. Files touching auth, payments, data storage, JWT handling
3. New files (brand new code has no safety net)
4. Test files (secondary — real code bugs are more critical)

**Per-file diff on demand:**
```bash
gh pr diff {PR_NUMBER} -- {file}
glab mr diff {MR_IID} -- {file}
```

Never fetch the full PR diff at once. Fetch per file as you get to it.

---

## Step 7 — Review

For each file under review:
1. Read the diff for that file
2. Read surrounding code if diff alone is insufficient
3. Check against CLAUDE.md conventions
4. Check for bugs that would actually be hit in production
5. Calibrate severity — a bug in a central auth/JWT module is more critical than in a utility helper

**Do NOT flag:**
- Pre-existing issues
- Linter/compiler catches
- Nitpicks a senior engineer wouldn't raise
- Intentional changes clearly tied to the PR's goal
- Issues on lines not modified in this PR
- Files matching exclusion patterns

**Files to skip entirely:**
- `graphify-out/**`, `**/plans/**`, `**/*.lock`, `**/dist/**`, `**/build/**`, `**/__pycache__/**`

---

## Output Format

```
PR #N: {title} — Code Review

Overview
{paragraph describing what the PR does and which flows/capabilities it adds}

Summary Statistics
{+/- additions/deletions across N files | N commits | key stats about what was added}

### Summary
{2-3 sentence summary of the PR's purpose and scope}

Code Quality Analysis
Strengths
{positive findings — patterns, guards, architecture choices worth noting}

Concerns & Suggestions
{issues grouped by severity — High/Medium/Low, each with file:line reference where applicable}

Specific Recommendations
{actionable before-merge items — one per line}

Risks
{row risks: High/Medium/Low with brief reason}
```

**Guidelines for output:**
- Be specific — cite file paths and line numbers for every issue
- Calibrate severity: High = likely to cause real production incidents, Medium = could cause issues in specific edge cases, Low = nice-to-have
- Strengths section is required too — acknowledge good work, not just problems
- Concerns should be actionable, not theoretical
- Keep it concise — a senior engineer's note, not an essay

---

## Reference

- `references/github.md` — GitHub CLI commands, output format, link format rules
- `references/gitlab.md` — GitLab CLI commands, output format, link format rules
