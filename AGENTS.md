# Agent Learning Repository Instructions

This repository is a long-term learning vault for AI Agent, machine learning, lectures, papers, code labs, and project learning.

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
- Review: summarize weekly/monthly progress and decide the next learning target.

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
- `90-reviews/`: weekly, monthly, and milestone reviews.
- `assets/`: small images and diagrams only.
- `templates/`: note templates.

## When the User Is Currently Learning

If the user is taking a course, watching a lecture, or pasting rough notes:

1. Put raw notes in `00-inbox/YYYY-MM-DD-topic.md` unless the user asks for a fully organized note.
2. Preserve source, date, open questions, and concepts to extract.
3. Do not over-polish during capture; avoid breaking the user's learning flow.
4. If enough context is available, add a short "next action" section.

## When Organizing Notes

Move or rewrite notes according to maturity:

- Course/lecture/paper/book material -> `10-sources/`.
- One clear idea in the user's own words -> `20-concepts/`.
- Code verification -> `40-code-labs/`.
- Real product/project experience -> `30-projects/`.
- Durable method or framework -> `50-systems/`.
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
- `templates/weekly-review.md` for weekly reviews.

## Quality Bar

A durable note should pass at least one of these checks:

- It answers a question the user is likely to meet again.
- It reduces future trial-and-error.
- It explains a key concept in the user's own words.
- It connects two previously separate topics.
- It supports a code experiment or project decision.

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
- `50-systems/长期学习工作流.md`
- `00-inbox/`
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

