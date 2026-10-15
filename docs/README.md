# Process documents

This folder holds the documents behind the Project Bridge case: what was delivered, how the work was decided, and how
AI was used at each step. The code is in `bridge/`, the spec, plan and tasks in `specs/project-bridge/`.

## What each folder holds

- `deliverables/` - the four documents written for the reader of the case: the one-page PRD and its background, the
  path-to-production note and its annex.
- `process/charter.md` - the project's goals, how success is measured, and what is out of scope.
- `process/ai-usage-log.md` - the log of every relevant AI step, with what the author checked by hand.
- `process/data-findings-2026-10-14.md` and `process/data-investigation-proposal.md` - the first look at the data and
  the proposal that framed it.
- `process/briefs/` - the instructions each AI agent received, one file per agent task, in the order they were issued.
  Each is the brief an agent was dispatched against;
  some agents also received a longer prompt that is not included. The date in a brief's id is the date its numbering
  series started; some were issued on the evening of 14 October. B-2026-10-15-04 was withdrawn and never sent. The
  brief that copied these files, its review and the brief for the presentation materials are not included.
- `process/reviews/` - fresh-context checks: a separate agent, without the conversation that produced the work,
  reviewed it and wrote what it found. Later reviews check that earlier findings were fixed. From B-2026-10-15-68 on,
  the session wrote the review file from the reviewer's report, and some reviews exist only as entries in the AI usage
  log.

## Original file names

| Original | Published as |
|---|---|
| `registro-ia.md` | `process/ai-usage-log.md` |
| `hallazgos-datos-2026-10-14.md` | `process/data-findings-2026-10-14.md` |
| `investigacion-datos-propuesta.md` | `process/data-investigation-proposal.md` |
| `CHARTER.md` | `process/charter.md` |
| `01-PRD-lite.onepage.md` | `deliverables/PRD-lite.md` |
| `01-PRD-lite.md` | `deliverables/PRD-lite-background.md` |
| `03-path-to-production.md` | `deliverables/path-to-production.md` |
| `03-annex.md` | `deliverables/path-to-production-annex.md` |

## What is not included

The case data pack, the case summary (`CASO.md`), the brand notes (`MARCA-clara.md`), the decision log, the
presentation materials and any description of them are not included.

## What was changed before publishing

Names of other companies were replaced with "[another company]". Local file paths were replaced with repository-relative
or descriptive ones. Names and addresses of real people at the company were removed. One table row that was a personal
note unrelated to the case was dropped. Descriptions of the presentation materials were removed or reduced to one
sentence, and a few phrases were reworded. Figures, quotes in Spanish and their English renderings, and internal ids
appear as they were written.
