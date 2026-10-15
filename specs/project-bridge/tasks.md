# Tasks — Project Bridge

> Reader: whoever works a task, in fresh context. Read `spec.md` and `plan.md` first. One task at a time, in order;
> each closes only when its verification line passes. Branch `feat/project-bridge`; recovery for every task is a
> cheap revert (one commit per task on the branch, nothing outside the repo is written).
> Rung: how much autonomy the task runs at — A3 when a mechanical check closes it, A2 when a named evidence procedure
> does, A0 when it needs judgement by a person.

| # | Task | Deliverable | Verified by | Rung | Status |
|---|---|---|---|---|---|
| T0 | Build the verifier: `tests/test_golden.py` (V1–V13) and `tests/test_guards.py`; recompute every golden figure with a throwaway script first; prove each guard red on a seeded violation and green on a clean fixture; golden tests red (no implementation) | E0 | Run log showing: golden suite fails on missing `bridge`; each guard's seeded-violation self-test fails then passes; figure recomputation matches the spec | A0 — the verifier cannot close itself; fresh-context review | done — 2f6b6f1 and the verifier fix commits 40262d9, d9d0219, 772ab75, 9f5512e, 8d84314; fresh reviews in the AI log (2026-10-14) |
| T1 | `bridge/policy.py`, `bridge/inputs.py`, `bridge/__init__.py` skeleton | E1, E2 | V1 load-level tests green (totals summed from loaded rows; the match-level V1 test waits for T2); V11 load fingerprints; V12 missing-input load; `PolicyTypeCodes`; guards for floats and policy literals green on these files | A3 | done — 7ae062a |
| T2 | `bridge/recon.py` | E3 | V1 match-level, V2, V3 (with the two-candidate fixture), V4, V5, V8b, V8c, data-issue flag counts, `V10SourcesInMemory` green | A3 | done — ffee369, 30a9c4d |
| T3 | `bridge/close.py` (single-line invoice accrual) | E4 | V6, V7, V7b, V8, V9, V12 "never estimated" green | A3 | done — 181497a |
| T4 | `bridge/checks.py` | E6 | Every name in `policy.CHECKS` present with its expected result and count on this data; missing processor invoice reported (V12) | A3 | done — 1642cfb |
| T5 | `bridge/report.py`, `bridge/template.html`, `run.py`, `README.md` | E5 | V10, V11, V13 green; CSV read-back equals the in-memory result; no external reference in `index.html`; full suite green | A3 | done — e7def37, 6749fd6 |
| T5b | Import review of `bridge/` (spec V10's human part: policy values only come from `policy`) | E1 | A reviewer reads every import and every literal outside `policy.py` and records the list | A2 — evidence: the recorded list | done — review-closing-2026-10-14.md, section "T5b import review"; guard tests in `tests/test_guards.py` |
| T6 | Manual page demo in Chrome | E5 | V14 performed and recorded with screenshots | A0 | done — page checked in Chrome by the session and by reviews, recorded in the AI log and review-closing-6-2026-10-15.md; no screenshots kept in the repository |
| T7 | Messages per exception type (extra 1) | E7 | Every type code in `policy.DIFF_TYPES` has owner, action, message (mechanical test); shown on the page | A2 — evidence: the page and `exceptions.csv` show them for one row of every type present in the data | done — messages per type declared in `bridge/policy.py`, mechanical test in `tests/` |
| T8 | Invoice accrual by line item (extra 2) | E8 | V6–V7b still green; entry 5 has four debit lines to 5100 summing 8,412.30, each tagged variable/fixed in `line_tags`, and one credit line to 2150 | A3 | done — d2d3a79; entry E05 itemised; review-extras-2026-10-15.md |
| T9 | Treasury view (extra 3) | E9 | A2 — evidence: daily balances equal the bank statement's running balance per day; transfer flagged illustrative | A2 | done — d2d3a79; `treasury.csv` (30 days) in the frozen run; review-extras-2026-10-15.md |
| T10 | Review before closure (fresh context) and Andrés's sign-off | — | Review findings resolved; Andrés approves | A0 | done — closing reviews 1 to 7 and the style review in the project records, all resolved; Andrés approved closing in session on 2026-10-15 (project decision log, "Close the spec before the public push") |
| T10a | Repair rounds 1–4 (14–15 Oct): closing-review repairs and the readings after repair reviews 1–4 | Plan section "Contracts", the bold "Readings…" blocks | Planted tests written first for each round; fresh review each round | A2 | done — 68bd650, 4b85a24, 1b8182e, 0e683ed, 528d600, 62d0f92, b2673b4, 1870b3f, 7a2bd18, 90c7a00 (tests 68bd650, fd4b789, 8feca7e, e78bc6e, 3f41821, 9e5d114); review-closing-2026-10-14.md, review-repairs-2026-10-14.md, review-repairs-2-2026-10-14.md, review-repairs-3-2026-10-14.md, review-repairs-4-2026-10-14.md |
| T11 | Fifth-repair readings: USD conversion error corrected by the processor, feed clause, settlement sentence | Plan section "Readings after the fifth repair review" | The plan block's own tests green; fresh review | A2 | done — 2797636 (tests 883ec8e, 386d086) |
| T12 | Page: a summary by category on every tab, all rows in one table | Plan section "Page: a summary by category on every tab, all rows in one table below" | The plan block's own tests green; fresh review | A2 | done — 1053476 (tests 3b66755, 3fc5b35) |
| T13 | Extras before submission: itemised invoice, Treasury view, Mastercard-owned conversion adjustment | Plan section "Extras before submission: itemised invoice, Treasury view, Mastercard's own conversion error" | The plan block's own tests green; fresh review | A2 | done — d2d3a79 (tests d495d57) |
| T14 | Five screens by the person who operates them | Plan section "Five screens by the person who operates them" | The plan block's own tests green; fresh review | A2 | done — bb3645d, 325f90d (tests 1516c24) |
| T15 | Repairs after the five-screens review | Plan section "Repairs after the five-screens review" | The plan block's own tests green; fresh review | A2 | done — 49c03e9 (tests 72a3eb0, a7e0425); review-screens-2026-10-15.md |
| T16 | Mastercard payable reconciled against Mastercard | Plan section "The Mastercard payable reconciled against Mastercard" | The plan block's own tests green; fresh review | A2 | done — cd9981d (tests ce6876b) |
| T17 | Payable bridge reads on its own; last page fixes | Plan section "The payable bridge reads on its own, and the last page fixes" | The plan block's own tests green; fresh review | A2 | done — 0ef8363 (tests 5616e66); review-repairs-payable-2026-10-15.md |
| T18 | Honest evidence on every entry line; closing fixes | Plan section "Honest evidence on every entry line, and the closing fixes" | The plan block's own tests green; fresh review | A2 | done — 47e3056, 97b0051 (tests d20ff36, df98933); review-closing-2-2026-10-15.md, review-closing-3-2026-10-15.md |
| T19 | Last round before freezing: waterfalls, impact per action, ERP file, explanations | Plan section "Last round before freezing: waterfalls, impact per action, ERP file, explanations" | The plan block's own tests green; fresh review | A2 | done — 3430253 (tests c3d058e); judged by review-closing-4-2026-10-15.md |
| T20 | Freeze fixes from closing review 4, Data quality table, Reconciliation by type | Plan section "Freeze fixes from the closing review of the last round" | The plan block's own tests green; fresh review | A2 | done — 65a8f86, d8aa455 (tests e980cf0, fe6a631); answers review-closing-4-2026-10-15.md |
| T21 | Freeze fixes 2 from closing review 5 | Plan section "Freeze fixes 2, from closing review 5" | The plan block's own tests green; fresh review | A2 | done — 073a17e (tests 0ab8411); answers review-closing-5-2026-10-15.md, checked by review-closing-6-2026-10-15.md |
| T22 | Named owners from the email thread | Plan section "Named owners from the email thread" | The plan block's own tests green; fresh review | A2 | done — b276015, 10abf47 (tests aca36c7); review-closing-7-2026-10-15.md |
| T23 | Modern visual style, template only | Plan section "Modern visual style" | The plan block's own tests green; fresh review | A2 | done — 0f710ce, 20115be (frozen tag `tool-frozen-3-2026-10-15`); review-style-2026-10-15.md |

Running one task's tests: from the repo root, `BRIDGE_DATA=<data> python3 -I -m unittest -v -k <TestClassName>`
(discovery plus a pattern; naming a module fails under `-I`).

Rows T11–T23 were added at closing (2026-10-15): one per later round the plan records, in the order built; they ran
before T10's final sign-off. Order was strict for T0–T6 (T0 before any implementation dispatch). T7–T9 were to be built only if time allowed; all three were. What is not built is listed in the spec's "As delivered" section.
Every task that used AI gets a line in
the AI usage log (`docs/process/ai-usage-log.md`) with what Andrés checked by hand.

Commit ids refer to the private development history; the public code is commit c68e35d.
