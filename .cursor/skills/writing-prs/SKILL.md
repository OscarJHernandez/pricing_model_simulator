---
name: writing-prs
description: Drafts pull request titles and bodies with clear scope, executable test steps, risks, and rollback. Use when the user asks for a PR description, merge request text, reviewers’ summary, or pre-merge write-up for a branch.
---

# Writing high-quality PRs

## When to apply

- User asks for a PR / merge request title or body, or “what should reviewers know?”
- User is about to open a PR and wants a structured summary from local changes.
- User wants a concise branch overview before requesting review.

## Information to collect first

Gather or infer from context; if unknown, **ask** or mark **TBD**—do not invent facts.

- Base branch and feature branch name (if relevant).
- Linked issues, tickets, or specs.
- User-visible behavior and any API/schema changes.
- Migrations, config, or env vars.
- Performance, data volume, or operational impact (if any).

## Output contract

Always deliver:

1. **Title** — One line, imperative mood. Use a scoped prefix when it helps (`api:`, `frontend:`, `docs:`). If the repo’s recent PRs follow a convention (e.g. Conventional Commits), match that when obvious.
2. **Body** — Use this skeleton (omit sections only when clearly N/A; say “N/A” briefly if needed):

```markdown
## Summary

[2–4 sentences: what changed and why, outcome-focused.]

## Scope

**In:** …  
**Out:** …

## How to test

1. …
2. …

## Risks & rollback

[Risks, feature flags, data backfill, or “low risk”. How to revert or mitigate.]

## Screenshots / metrics

[UI before/after, graphs, or “N/A”.]
```

## Quality checklist

- [ ] Scope in the body matches what was actually changed (no over-claiming).
- [ ] “How to test” steps are concrete and runnable by another developer.
- [ ] Risks and rollback are honest; unknowns are TBD, not hidden.
- [ ] No huge pasted diffs; synthesize instead of dumping commit messages.
- [ ] No vague one-liners like “misc fixes” without substance.

## Anti-patterns

- Marketing or hype tone; internal jargon without a one-line gloss.
- Listing every commit hash instead of a coherent narrative.
- Stating “tests pass” or “no regressions” without evidence when the user did not provide it.

## Additional resources

For filled-in samples using this template, see [examples.md](examples.md).
