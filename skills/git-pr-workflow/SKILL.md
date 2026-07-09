---
name: git-pr-workflow
description: >
  coderAS-family skill for safe, disciplined version-control on any repo: small atomic
  commits, a mandatory pre-publish report + approval gate before any push/PR, and correct
  authorship. Triggers on: "commit this", "make a PR", "push my changes", "open a pull
  request", "prep a commit", "write a commit message", "publish to remote", "raise a PR".
  Encodes coderAS operating rules 18 (VC hygiene), 19 (approval gate before remote publish)
  and 20 (authorship = the owner, never an AI persona). Use whenever work crosses from
  editing files to recording or publishing them. Do NOT use it to bypass the approval gate.
argument-hint: "Tell me the scope to commit and whether this is local-only or headed to a remote"
---

# git-pr-workflow Skill

Turn finished edits into clean, reviewable history — and never cross the local→remote
boundary without the owner's explicit sign-off.

## When to use
- The user asks to commit, stage, amend, push, or open a PR.
- A task has reached a natural, self-contained checkpoint worth recording.
- You are about to publish anything outside the local repo.

## Core principles (from coderAS rules 18–20)
1. **Small, atomic, reviewable commits.** One logical change per commit. Message explains
   *why*, not just *what*. Never bundle unrelated drive-by edits — surface them separately.
2. **No secrets, no generated artifacts.** Respect and maintain `.gitignore`. Never commit
   credentials, tokens, `.env`, or derived/build output.
3. **Authorship = the repository owner.** Author every commit as the owner's real git
   identity (`git config user.name` / `user.email`). **Never** add a `Co-authored-by:`
   trailer for Copilot or any agent persona — strip it if a template injects one.
4. **Approval gate before any remote publish (MANDATORY).** Local commits are free. Crossing
   to a remote (`git push`, PR, release) requires a **pre-publish report** and an explicit
   go-ahead first. If the owner has a standing "local only / no push" instruction, treat it
   as a hard block until lifted.

## Workflow

### A. Local commit (no gate needed)
1. Review what changed: `git status --short` and `git --no-pager diff --stat`.
2. Stage only the files in scope: `git add <paths>` (never blind `git add -A` if unrelated
   changes are present).
3. Sanity-check for secrets in the staged diff before committing.
4. Commit with a message shaped as: a concise imperative title (≤72 chars), a blank line,
   then a body explaining the motivation and any trade-offs.
5. Confirm identity on the resulting commit: `git --no-pager log -1 --format='%an <%ae>'`.

### B. Remote publish (gate REQUIRED — stop and report first)
Before `git push` / opening a PR, present a **pre-publish report** and wait for approval:

```
PRE-PUBLISH REPORT
- Target:        <branch → remote>  |  PR base ← head
- Diff summary:  <git diff --stat output>
- What & why:    <2–4 lines of prose>
- Commit(s):     <title list>
- Full message:  <the commit/PR body to be used>
```

Only after an explicit "yes/approved/go" do you run the push or `gh pr create`.

## Commit message template
```
<imperative title, ≤72 chars>

<why this change exists; what problem it solves; notable trade-offs.
Wrap at ~72 cols. Reference decisions.md anchors or issues where relevant.>
```

## Guardrails / red lines
- Never `git push --force` to a shared branch without explicit, specific approval.
- Never commit to `main`/`master` directly if the repo uses PR flow — branch first.
- Never invent an author identity; read it from `git config`.
- If a pre-commit hook fails, fix the cause — do not blindly `--no-verify` unless the owner
  asked to skip a known-noisy hook.
