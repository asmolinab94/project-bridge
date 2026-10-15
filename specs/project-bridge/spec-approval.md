# Spec approval — Project Bridge

> English translation (2026-10-14) of the approval record; the text Andrés answered is the Spanish version at commit
> 8a5a95f. Answer: approved (G-2026-10-15-03).
>
> Type: spec approval · What comes back: your annotations become the revision; once approved, it sets
> `status: approved` and releases the plan.
> **The spec**: `specs/project-bridge/spec.md`. Read its Part 1 first (problem, three diagrams, what it leaves out, two
> questions). Part 2 only if a row below sends you there.

## The question

Approve, approve with annotations, or send back? Approving commits what is built first (the case minimum plus the
completeness checks), the figures it is tested against, and what is left out.

## The decisions it carries

| Decision | Chosen | Closest alternative | Why, in one line | Did you already make it? |
|---|---|---|---|---|
| Shape of the tool | Dependency-free Python + one HTML page | App with a library (Streamlit) | The evaluator opens it without installing anything | Yes, 2026-10-14 |
| Completeness checks | Inside the minimum | First extra | A mandatory test and success measure 3 depend on them | **No: change from the review** |
| Entries that depend on evidence | Flagged "conditional", two "after" columns | Sum them without a flag | Do not present the unconfirmed as fact | No: question 1 |
| Measure of the 250 threshold | Gross amount | Net amount | Flags more cases; it is what the customer pays | No: question 2 |
| Cut-off date | 5-Oct-2026 (working day 3 of the close) | Run date | The case happens on that day; with the real date everything escalates | No, I made it: the brief fixes it |

## Scope

Builds the minimum the case asks for plus the completeness checks; then, if there is time, messages per exception
type, invoice by line item and Treasury view. Left out:
- Live connections — written up in the production note.
- Shared state between analysts — declared as a cut.
- Posting — never, by policy.
- Question-answering assistant over the data — only if time is left.
- Product margin, target balance, cost of idle cash — written, not built.

## Depends on

Repo `repos/project-bridge`, branch `feat/project-bridge`; system Python 3; data in `clara_caso_finance/insumos/datos/`
unmodified.

## What we do not know

**Agent's doubts**: whether the browser allows saving the page's state when opened as a local file varies; the spec
already requires saying so and keeping export working.

**Questions for Andrés**: the two from Part 1 of the spec, same numbering:
1. Two "after" columns (confirmed only / with conditional). Recommended.
2. 250 threshold measured on gross amount. Recommended.

## Evidence

- Critical review in fresh context, one round (opus model): 9 material, 9 minor; 0 blocking. All fixed in the spec
  except the 2 questions. Every individual figure recomputed from the data: correct.
- 12 invariants, 17 checks (V1–V14, V7b, V8b, V8c), each naming its invariant.

---

**Andrés decides**: approve · approve with annotations · send back · send back: not understandable
