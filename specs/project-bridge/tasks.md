# Tasks — Project Bridge

> Reader: whoever works a task, in fresh context. Read `spec.md` and `plan.md` first. One task at a time, in order;
> each closes only when its verification line passes. Branch `feat/project-bridge`; recovery for every task is a
> cheap revert (one commit per task on the branch, nothing outside the repo is written).
> Rung: how much autonomy the task runs at — A3 when a mechanical check closes it, A2 when a named evidence procedure
> does, A0 when it needs judgement by a person.

| # | Task | Deliverable | Verified by | Rung |
|---|---|---|---|---|
| T0 | Build the verifier: `tests/test_golden.py` (V1–V13) and `tests/test_guards.py`; recompute every golden figure with a throwaway script first; prove each guard red on a seeded violation and green on a clean fixture; golden tests red (no implementation) | E0 | Run log showing: golden suite fails on missing `bridge`; each guard's seeded-violation self-test fails then passes; figure recomputation matches the spec | A0 — the verifier cannot close itself; fresh-context review |
| T1 | `bridge/policy.py`, `bridge/inputs.py`, `bridge/__init__.py` skeleton | E1, E2 | V1 load-level tests green (totals summed from loaded rows; the match-level V1 test waits for T2); V11 load fingerprints; V12 missing-input load; `PolicyTypeCodes`; guards for floats and policy literals green on these files | A3 |
| T2 | `bridge/recon.py` | E3 | V1 match-level, V2, V3 (with the two-candidate fixture), V4, V5, V8b, V8c, data-issue flag counts, `V10SourcesInMemory` green | A3 |
| T3 | `bridge/close.py` (single-line invoice accrual) | E4 | V6, V7, V7b, V8, V9, V12 "never estimated" green | A3 |
| T4 | `bridge/checks.py` | E6 | Every name in `policy.CHECKS` present with its expected result and count on this data; missing processor invoice reported (V12) | A3 |
| T5 | `bridge/report.py`, `bridge/template.html`, `run.py`, `README.md` | E5 | V10, V11, V13 green; CSV read-back equals the in-memory result; no external reference in `index.html`; full suite green | A3 |
| T5b | Import review of `bridge/` (spec V10's human part: policy values only come from `policy`) | E1 | A reviewer reads every import and every literal outside `policy.py` and records the list | A2 — evidence: the recorded list |
| T6 | Manual page demo in Chrome | E5 | V14 performed and recorded with screenshots | A0 |
| T7 | Messages per exception type (extra 1) | E7 | Every type code in `policy.DIFF_TYPES` has owner, action, message (mechanical test); shown on the page | A2 — evidence: the page and `exceptions.csv` show them for one row of every type present in the data |
| T8 | Invoice accrual by line item (extra 2) | E8 | V6–V7b still green; entry 5 has four debit lines to 5100 summing 8,412.30, each tagged variable/fixed in `line_tags`, and one credit line to 2150 | A3 |
| T9 | Treasury view (extra 3) | E9 | A2 — evidence: daily balances equal the bank statement's running balance per day; transfer flagged illustrative | A2 |
| T10 | Review before closure (fresh context) and Andrés's sign-off | — | Review findings resolved; Andrés approves | A0 |

Running one task's tests: from the repo root, `BRIDGE_DATA=<data> python3 -I -m unittest -v -k <TestClassName>`
(discovery plus a pattern; naming a module fails under `-I`).

Order is strict for T0–T6 (T0 before any implementation dispatch). T7–T9 only if time allows, in that order; what is
not built is written up as "written, not built" in the deliverable. Every task that used AI gets a line in
the AI usage log (`registro-ia.md`, submitted separately) with what Andrés checked by hand.
