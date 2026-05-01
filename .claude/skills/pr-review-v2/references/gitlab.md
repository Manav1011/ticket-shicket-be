# GitLab Reference

GitLab uses **Merge Requests (MRs)** instead of Pull Requests. All concepts are identical;
only the terminology and CLI differ.

## Allowed Tools

```
Bash(glab mr view:*), Bash(glab mr diff:*), Bash(glab mr note:*),
Bash(glab mr list:*), Bash(glab mr approvals:*),
Bash(git log:*), Bash(git blame:*)
```

## CLI Commands

### Eligibility Check
```bash
# View MR status (state: opened, closed, merged)
glab mr view <MR_IID> --output json

# Check existing notes/comments for previous review
glab mr note list <MR_IID>
```

### Gather Context
```bash
# List changed files only (always do this first)
glab mr diff <MR_IID> --name-only

# Diff for a specific file (preferred — fetch per file, on demand)
glab mr diff <MR_IID> -- path/to/file.ts

# View MR details including description and labels
glab mr view <MR_IID>

# Never fetch the full diff in one call — always use per-file fetching
```

### Git History & Blame
```bash
# Blame a file
git blame <file_path>

# Log history for a file
git log --oneline -20 -- <file_path>

# List previous MRs (search by file path in title/description is limited;
# use git log to find previous commits and correlate)
glab mr list --state merged --label "" 2>/dev/null | head -20
```

### Post Review Comment
```bash
glab mr note create <MR_IID> --message "<COMMENT_BODY>"
```

---

## Eligibility Rules for GitLab

Skip review if:
- MR state is `closed` or `merged`
- MR has `Draft:` or `WIP:` prefix in title
- MR is from a bot (check author username for bot patterns)
- MR already has a note from you with "Code review" heading
- MR is marked with `skip-review` label

---

## Output Format

### Issues Found

```markdown
### Code review

Found N issues:

1. <brief description> (CLAUDE.md says "<exact quote>")

https://<gitlab-host>/<namespace>/<repo>/-/blob/<FULL_SHA>/<path/to/file.ext>#L<start>-<end>

2. <brief description> (bug due to <short explanation>)

https://<gitlab-host>/<namespace>/<repo>/-/blob/<FULL_SHA>/<path/to/file.ext>#L<start>-<end>

🤖 Generated with [Claude Code](https://claude.ai/code)

<sub>- If this code review was useful, please 👍 this comment. Otherwise, 👎.</sub>
```

### No Issues Found

```markdown
### Code review

No issues found. Checked for bugs and CLAUDE.md compliance.

🤖 Generated with [Claude Code](https://claude.ai/code)
```

---

## Link Format Rules

GitLab line links use a **different format** than GitHub:

```
https://<gitlab-host>/<namespace>/<repo>/-/blob/<FULL_40-CHAR-SHA>/<path/to/file>#L<start>-<end>
```

Key differences from GitHub:
- Path includes `/-/blob/` (note the `/-/`)
- Line range format is `#L<start>-<end>` (no second `L` before end line)
  - Example: `#L10-15` (GitHub would be `#L10-L15`)
- Self-hosted GitLab: replace `gitlab.com` with your instance hostname

Full example:
```
https://gitlab.com/mygroup/myrepo/-/blob/a1b2c3d4e5f6.../src/auth.ts#L67-72
```

- Always use the full 40-character SHA
- Never use branch names or `HEAD` in comment links — they will drift
