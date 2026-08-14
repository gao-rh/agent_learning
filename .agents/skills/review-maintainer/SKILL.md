---
name: review-maintainer
description: Mechanically scan and maintain checklists, topic indexes, review drafts, dates, links, and AI summary regions without deciding priorities or changing user-confirmation status. Use for weekly or monthly review preparation, vault health checks, migration validation, and scheduled maintenance.
---

# Review Maintainer

Only use this Skill inside `/Users/gaoronghui/Documents/agent_learning`.

## Before Work

1. Confirm `PREFERENCES.md` has been read in the current session; read it if not.
2. Read `AGENTS.md`, the four state READMEs and immediate topic READMEs such as `2-进行中/*/README.md`. Do not recursively read experiment, dependency, output, or reference READMEs unless the current anomaly requires one.
3. Treat user-authored text outside `AI-SUMMARY` markers as protected.

## Allowed Automatic Work

- Scan for overdue items, missing check dates and long-inactive topics.
- Rebuild only content between `<!-- AI-SUMMARY:START -->` and `<!-- AI-SUMMARY:END -->`.
- Generate weekly or monthly review drafts.
- Update indexes and links after an already-approved move.
- Validate Markdown links, JSON, Git diffs, file inventories and unexpected large files.
- Commit and push verified mechanical changes when the automation explicitly authorizes it.

## Forbidden Automatic Decisions

Do not automatically:

- change `待判断` to `已确认`;
- turn a planning draft into a formal plan;
- mark a topic completed, abandoned or archived;
- choose priorities, goals or milestones;
- delete source material;
- resolve merge conflicts, force-push or overwrite remote divergence.

## Review Output

Drafts must separate:

1. observed facts;
2. mechanical anomalies;
3. decisions requiring user confirmation;
4. optional AI suggestions clearly labelled as suggestions.

Use `scripts/inventory.py` for migration inventories. On this iCloud-backed repository, use `scripts/stage_safe.py` instead of `git add` so Git does not hang while opening File Provider paths. Use [the review draft template](assets/review-draft-template.md) for periodic drafts.
