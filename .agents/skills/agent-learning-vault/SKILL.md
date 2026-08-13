---
name: agent-learning-vault
description: Maintain this repository's learning action hub, reading index, and note-routing workflow. Use when the user asks to add learning todos, add reading-list items, organize Codex/Agent learning, update the learning action hub, or run an on-demand review when things feel messy.
---

# Agent Learning Vault Skill

Use this skill only inside `/Users/gaoronghui/Documents/agent_learning`.

This skill turns raw learning inputs into a maintained learning action system. It complements `AGENTS.md`; it does not replace the repository-wide rules.

## Primary Files

Read these before making changes:

1. `AGENTS.md`
2. `30-projects/Codex与Agent学习行动中枢.md`
3. `30-projects/Codex与Agent阅读索引.md`
4. `50-systems/长期学习工作流.md`
5. `学习资料/README.md` and the relevant core course/question summaries.

## When To Use

Use this skill when the user says or implies:

- 添加一个学习待办
- 添加到阅读清单
- 更新学习行动中枢
- 帮我整理接下来要做什么
- 我有点乱，帮我复盘
- Codex / Agent / MCP / Skill / Hook / Plugin 相关学习路线
- 把某个资料、链接、想法纳入这个 vault

Do not use it for unrelated coding tasks unless the user explicitly wants the result recorded as learning material.

## Core Workflow

Follow this process:

1. Clarify the input into one of these types: `阅读`, `概念`, `实验`, `整理`, `分享`, `系统优化`.
2. Assign a direction: `Codex`, `Agent`, `Harness`, `MCP`, `Skill`, `PKM`, `学习方法`, or a more specific existing direction from the maps.
3. Decide whether the input belongs in:
   - the learning action table,
   - the reading index,
   - an inbox note,
   - a detailed source or concept note,
   - a code lab,
   - a project note,
   - a system note,
   - or a cognition/review note.
4. Add or update the smallest useful artifact. Avoid broad rewrites.
5. Every task must have a concrete next action that can be started in 30-60 minutes.
6. Every reading item must have:
   - summary,
   - why read,
   - expected output,
   - next step.
7. Preserve unconfirmed user ideas as `用户假设` or `待确认`; do not silently promote them into stable concept or system notes.
8. Keep action plans and long reading lists in `30-projects/`; do not expose them in `学习资料/`.
9. Update `学习资料/` only when a course-level mainline or recurring core question is mature enough to help the user review.

## Routing Rules

| Input | Default Destination | Required Detail |
| --- | --- | --- |
| Rough note or temporary idea | `00-inbox/` | source, date, trigger, open question |
| Article, paper, video, official doc | reading index, then `10-sources/` after reading | summary, why read, output target, origin metadata |
| Stable concept in user's own words | `20-concepts/` | one-line definition, mechanism, example, misconception, origin metadata |
| Course milestone or recurring core question | matching two files under `学习资料/<topic>/` | concise mainline or question plus current conclusion |
| Technical claim that needs verification | `40-code-labs/` | minimal experiment and expected conclusion |
| Real applied project work | `30-projects/` | background, action, result, next step |
| Durable workflow or rule | `50-systems/` or this skill | trigger, steps, verification |
| Judgment change or DeepMe note | `60-cognition/` | old belief, evidence, new belief |
| Periodic or milestone review | `90-reviews/` | progress, unresolved questions, next focus |

## Updating The Action Hub

When adding a task to `30-projects/Codex与Agent学习行动中枢.md`:

- Use the next available `LA-###` id.
- Prefer `Next` unless the user is actively working on it.
- Keep `Doing` to at most 3 items. If it would exceed 3, move a lower-priority item back to `Next` or ask the user only if the tradeoff is genuinely unclear.
- Keep visible `Next` to at most 7 items when doing a review. Move overflow to `Later`.
- Link to expected output files when the path is clear.
- If no output path is clear, choose the smallest appropriate destination from the routing rules.
- Do not turn the action hub into a long knowledge index. Keep detailed sources in the reading index.

## Updating The Reading Index

When adding a reading item:

- Add it to `30-projects/Codex与Agent阅读索引.md` under the closest existing section.
- If the source content is available, write a short summary in the user's own words.
- If the source content is not available, mark the summary as `待摘要` and add a next step to read or fetch it.
- Do not add bare links without explaining why they matter.
- Prefer official docs or primary sources for technical rules.
- For current product behavior, verify with official docs or live state when practical.
- Only promote one or two active reading items into the action hub.

## On-demand Review

Run this when the user says they feel messy, asks what to do next, or the hub exceeds the WIP limits.

Review protocol:

1. List current `Doing`, `Next`, and blocked items.
2. Choose 1-3 `Doing` items that best serve the current north star.
3. Move stale or low-leverage items to `Later`.
4. Convert vague items into specific next actions.
5. Recommend the next single action in the final response.

Do not create a long new plan if the user asked to reduce confusion. The output should narrow choices.

## Quality Bar

A useful update should answer at least one of these:

- What should I do next?
- Why does this source matter?
- What output should this reading produce?
- Which note layer should this belong to?
- What concept or experiment should be created from this?
- What should be deferred?

Avoid:

- dumping links,
- creating concept notes before understanding is stable,
- rewriting the user's hypothesis as if it were confirmed,
- expanding the system while the user is asking for focus,
- changing unrelated vault files.
