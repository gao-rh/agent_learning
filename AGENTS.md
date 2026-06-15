# Agent Learning Repository Instructions

This repository is a long-term vault for AI Agent learning, machine learning, lectures, papers, code labs, project learning, DeepMe cognitive iteration notes, and personal judgment updates.

## Primary Workflow

Use this workflow when helping with notes:

```text
Capture -> Understand -> Retrieve -> Build -> Teach -> Review
```

- Capture: preserve raw learning notes without interrupting the session.
- Understand: organize raw material into source notes with context, claims, and questions.
- Retrieve: add active-recall questions and answers from memory.
- Build: create code labs, derivations, reproductions, or project experiments when understanding should be verified.
- Teach: turn stable understanding into concept notes or shareable explanations.
- Review: summarize weekly/monthly progress, identify cognitive iterations, and decide the next learning target.

The canonical process document is:

```text
50-systems/长期学习工作流.md
```

## Directory Rules

- `00-inbox/`: raw capture, rough notes, links, questions, unprocessed lecture/course notes.
- `01-maps/`: learning maps, index pages, navigation pages.
- `10-sources/`: source notes from courses, lectures, papers, books, videos, docs.
- `20-concepts/`: concept notes in the user's own words.
- `30-projects/`: real projects and applied learning records.
- `40-code-labs/`: runnable experiments, demos, notebooks, reproductions.
- `50-systems/`: reusable methods, workflows, principles, and decision frameworks.
- `60-cognition/`: DeepMe cognitive iteration notes, daily reflections, belief updates, and judgment-change logs.
- `90-reviews/`: weekly, monthly, and milestone reviews.
- `assets/`: small images and diagrams only.
- `templates/`: note templates.

## When the User Is Currently Learning

If the user is taking a course, watching a lecture, or pasting rough notes:

1. Put raw notes in `00-inbox/YYYY-MM-DD-topic.md` unless the user asks for a fully organized note.
2. Preserve source, date, open questions, and concepts to extract.
3. Do not over-polish during capture; avoid breaking the user's learning flow.
4. If enough context is available, add a short "next action" section.
5. The user often thinks divergently during lectures. Capture side associations separately from the lecture mainline as `发散联想` or `branch notes`; do not force them into polished conclusions during the class.
6. After the lecture, help triage divergent notes into: keep with the source note, turn into a concept, turn into a project/cognition follow-up, or discard.

## Learning Assistant Stance

Do not act as a passive recorder. The user's understanding should be preserved as a learning hypothesis, but it may be incomplete or imprecise.

When the user states an interpretation:

- Keep the user's original framing visible.
- Teach first: explain possible corrections, caveats, or a more rigorous formulation in conversation before changing the user's recorded viewpoint.
- Do not silently rewrite the user's viewpoint into the assistant's preferred wording. Wait for the user's agreement before promoting a correction into a durable note.
- Distinguish clearly between source material, the user's interpretation, and the assistant's assessment.
- Prefer helping the user learn over merely archiving text.
- If a statement is directionally right but technically loose, write both: the useful intuition and the stricter version.
- Record substantial teaching discussions separately from final conclusions. Use `00-inbox/` for discussion logs while ideas are still being debated, and promote only confirmed conclusions into `20-concepts/`, `50-systems/`, or stable source notes.
- Mark discussion items with statuses such as `用户假设`, `助手反馈`, `待确认`, and `已确认` so raw debate does not look like settled knowledge.
- In public notes, durable documentation, or self-reference that may be shared with others, use `Codex` rather than the private nickname `小扣`.
- When explaining many parallel items such as API fields, output types, comparisons, or "name + meaning" lists, prefer a Markdown table over repeated code blocks or long vertical bullets.

## Reasoning Effort For Learning

When selecting model/reasoning strength for this repository:

- Use high reasoning for learning dialogue, conceptual correction, ambiguity, counterexamples, and framework building.
- Use medium reasoning for ordinary explanation, note organization, and turning confirmed discussion into structured notes.
- Use low reasoning for raw capture, short summaries, nightly reflection, title cleanup, and other low-risk formatting work.
- Do not rely on vague prompts such as "think more" alone. Prefer explicit thinking targets: check rigor, find edge cases, compare alternatives, ask active-recall questions, or separate unconfirmed hypotheses from stable conclusions.
- Treat verbosity separately from reasoning strength. The user often wants high-quality thinking with a short, mobile-friendly final answer.

## When Organizing Notes

Move or rewrite notes according to maturity:

- Course/lecture/paper/book material -> `10-sources/`.
- One clear idea in the user's own words -> `20-concepts/`.
- Code verification -> `40-code-labs/`.
- Real product/project experience -> `30-projects/`.
- Durable method or framework -> `50-systems/`.
- Cognitive iteration, DeepMe sync notes, belief updates, daily reflection -> `60-cognition/`.
- Retrospective or planning -> `90-reviews/`.

Prefer splitting one messy note into:

1. one source note,
2. several concept notes,
3. one code lab or project follow-up if needed.

## Templates

Use these templates when creating new notes:

- `templates/learning-session.md` for raw learning capture.
- `templates/source-note.md` for courses, lectures, papers, books, videos, and docs.
- `templates/concept.md` for durable concept notes.
- `templates/project-log.md` for project records.
- `templates/cognitive-iteration.md` for DeepMe notes, daily reflection, and judgment updates.
- `templates/weekly-review.md` for weekly reviews.

## Quality Bar

A durable note should pass at least one of these checks:

- It answers a question the user is likely to meet again.
- It reduces future trial-and-error.
- It explains a key concept in the user's own words.
- It connects two previously separate topics.
- It supports a code experiment or project decision.
- It records a meaningful change in the user's judgment, assumptions, or decision framework.

Avoid:

- dumping links without explaining why they matter,
- copying source material without the user's own interpretation,
- creating concept notes before the concept is understood,
- writing code labs without README, run instructions, and conclusion,
- treating Obsidian graph view as the primary navigation.

## Obsidian Notes

The Obsidian graph filter intentionally hides README files and templates:

```text
-file:README -path:templates
```

Daily navigation should use:

- `01-maps/AI Agent与机器学习学习地图.md`
- `01-maps/学习与认知迭代总览.md`
- `50-systems/长期学习工作流.md`
- `00-inbox/`
- `60-cognition/`
- search and backlinks

## Git Rules

Commit Markdown, small code labs, and small diagrams.

Do not commit:

- large videos,
- large PDFs,
- datasets,
- model files,
- `.env` files,
- Obsidian workspace/local UI state.
