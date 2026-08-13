---
name: planning-dialogue
description: Research facts and guide one-decision-at-a-time planning for learning, life, reading, exploration, or work. Use when the user wants a short-term plan, medium-term milestones, priorities, options, or a planning discussion.
---

# Planning Dialogue

Only use this Skill inside `/Users/gaoronghui/Documents/agent_learning`.

## Before Work

1. Confirm `PREFERENCES.md` has been read in the current session; read it if not.
2. Read `AGENTS.md`, the relevant topic README, and recent records.
3. Separate confirmed facts, user decisions, AI suggestions, unknowns and old versions.

## Dialogue Protocol

1. Investigate discoverable facts and constraints before proposing a plan.
2. Discuss one decision that materially changes the plan at a time.
3. Offer 2–3 genuinely different options with costs, benefits and trigger conditions.
4. Test the likely choice with first principles, a counterexample and the main unknown.
5. Record the user's decision only after explicit confirmation.

Do not ask for confirmation on mechanical details that do not change direction. Do not generate a large plan to avoid a missing key decision.

## Draft Boundary

- Every AI-created plan begins as `AI 草案 / 待确认`.
- Never inherit goals or priorities from archived or unconfirmed plans.
- A plan becomes formal only after the user explicitly confirms it.
- Formal plans must identify the planning window, milestones, the next 2–4 weeks, next actions and check dates.

Use [the planning record template](assets/planning-record-template.md) for substantive discussions.
