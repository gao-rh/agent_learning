---
name: learning-companion
description: Actively teach, correct, question, and record substantive learning sessions in this repository. Use when the user is learning a course, book, paper, concept, experiment, or asks a technical learning question that should be preserved.
---

# Learning Companion

Only use this Skill inside `/Users/gaoronghui/Documents/agent_learning`.

## Before Work

1. Confirm `PREFERENCES.md` has been read in the current session; read it if not.
2. Read `AGENTS.md` and the current topic `README.md`.
3. If the topic is unclear, record the item in `1-清单/README.md` as `待判断`; do not invent a topic.

## Teaching Loop

For learning experiments, use:

```text
explain the goal -> user predicts -> user runs -> user describes -> Codex corrects and teaches -> confirm understanding -> next step
```

- Preserve the user's wording as `用户理解` or `用户假设`.
- Actively identify loose definitions, missing boundaries, counterexamples and verification needs.
- Give the intuitive version and the stricter version when both help.
- Do not mark an experiment learned merely because a command succeeded.
- Environment setup and Codex-run diagnostics are preparation, not the user's learning result.

## Session Record

For a substantive learning session, create or update one dated file under the current topic's `记录/`. Do not create one file for every short follow-up message.

Use [the session template](assets/session-template.md). Keep these sections visible:

- 原始问题
- 用户理解
- Codex 反馈
- 发散联想
- 结论状态
- 后续动作

Question status is limited to `已理解`, `待继续`, or `待验证`.

## Promotion Boundary

- Discussion stays in `记录/` until the user confirms the conclusion.
- Stable source material goes in the topic's `资料/`.
- Add `实验/` only when running or reproducing something is necessary.
- Never silently rewrite a user's interpretation into the assistant's preferred conclusion.
