# GitHub Reference

## Allowed Tools

```
Bash(gh pr view:*), Bash(gh pr diff:*), Bash(gh pr comment:*),
Bash(gh pr list:*), Bash(gh search:*), Bash(gh issue view:*),
Bash(gh issue list:*), Bash(git log:*), Bash(git blame:*)
```

## CLI Commands

### Eligibility Check
```bash
# View PR status
gh pr view <PR_NUMBER> --json state,isDraft,title,author,comments,reviews

# Check if already reviewed (look for your previous comments)
gh pr view <PR_NUMBER> --json comments --jq '.comments[].body' | grep -i "code review"
```

### Gather Context
```bash
# List changed files only (always do this first)
gh pr diff <PR_NUMBER> --name-only

# Diff for a specific file (preferred — fetch per file, on demand)
gh pr diff <PR_NUMBER> -- path/to/file.ts

# View PR details and metadata
gh pr view <PR_NUMBER>

# Never fetch the full diff in one call — always use per-file fetching
```

### Git History & Blame
```bash
# Blame a file
git blame <file_path>

# Log history for a file
git log --oneline -20 -- <file_path>

# Previous PRs touching these files (search issues/PRs)
gh search prs --repo <owner/repo> -- <file_path>
```

### Post Review Comment
```bash
gh pr comment <PR_NUMBER> --body "<COMMENT_BODY>"
```

---

## Output Format

### Issues Found

```markdown
### Code review

Found N issues:

1. <brief description> (CLAUDE.md says "<exact quote>")

https://github.com/<owner>/<repo>/blob/<FULL_SHA>/<path/to/file.ext>#L<start>-L<end>

2. <brief description> (bug due to <short explanation>)

https://github.com/<owner>/<repo>/blob/<FULL_SHA>/<path/to/file.ext>#L<start>-L<end>

🤖 Generated with [Claude Code](https://claude.ai/code)

<sub>- If this code review was useful, please react with 👍. Otherwise, react with 👎.</sub>
```

### No Issues Found

```markdown
### Code review

No issues found. Checked for bugs and CLAUDE.md compliance.

🤖 Generated with [Claude Code](https://claude.ai/code)
```

---

## Link Format Rules

Links **must** follow this exact format or GitHub Markdown won't render them:

```
https://github.com/<owner>/<repo>/blob/<FULL_40-CHAR-SHA>/<path/to/file>#L<start>-L<end>
```

- Full SHA required (40 chars) — **never** use `$(git rev-parse HEAD)` in the comment body
- Repo name must match the repo being reviewed
- `#L` notation with line range `L<start>-L<end>`
- Include at least 1 line of context before and after the flagged lines
- Example: flagging lines 5–6 → link to `#L4-L7`
