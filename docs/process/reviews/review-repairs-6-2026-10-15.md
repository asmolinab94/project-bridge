## Fresh review of the fifth repair round and the page redesign (40f6c5b..1053476)

Brief B-2026-10-15-48. Fresh-context opus reviewer, read-only. I worked on an export of 1053476 in a scratch folder, plus a local clone at a scratch folder for the tests that need git. Nothing was written in the repo, the records or the workspace.

**Verdict: the repair is ready; the page is not ready, but the gap is close.**

- **The fifth repair is done.** Every finding of the previous review is fixed or answered as the plan decided. The verifier is not weakened. The real data ties to the cent, and the only change on the real data is the planned rewording of 116 "What to do" sentences.
- **The page does what the plan's text asks.** Every summary click filters in place, every sum row equals its summary figure, the CSV export carries exactly the rows shown, and the Exceptions columns come in the planned order.
- **Two things stop sign-off on the page:**
  1. **Lost evidence.** Every figure built from more than one input row now shows only the first source row's fields plus "+N more". Andrés's own example from 2026-10-14, "the ledger balance, the total, and below it a table with the transactions", can no longer be done on the page. The test that was supposed to guard this was written in a form that can't fail.
  2. **The click happens out of sight.** On a 1440×900 laptop, the Exceptions table starts below the bottom of the screen, so clicking a type filters a table nobody can see.

### Closure checks

**(a) Verifier not weakened: yes for the repair round. For the page round, yes in the letter, but one replacement test is weaker than what it replaced.**

- **Suite:** 369/369 pass at 1053476, run in the clone.
  - In the plain export, 2 tests fail: `V11InputsUntouched.test_dirty_suffix` and `test_manifest_version_and_totals`. Both need a `.git` folder to read the code version. This comes from how the review was run, not from a defect.
- **Code commits never edit tests.** 2797636 and 1053476 touch only `bridge/`. Test commits touch only `tests/`, plan commits only `plan.md`.
- **Every assertion removed or loosened in the repair round (883ec8e, 386d086) follows from the plan:**
  - The "resend the file" test, which forced the feed clause on every resend sentence, is replaced by two tests:
    - the five types with an entry end on the one feed-clause constant, and it appears exactly once;
    - no other sentence mentions the feed, and `auth_after_clearing` has no feed clause.
    - This was the previous review's Material 1. Justified.
  - `test_usd_conversion_does_not_restate_the_fixer` no longer forbids opening on a fixer name. The plan's sentence opens "Processor re-converts". Justified.
  - `PROCESSOR_ENTRY_TYPES` (a copy in the tests) is replaced by reading `policy.CORRECTION_TYPES`. This was previous Minor 6. USD conversion is left out and asserted on planted rows instead, because its sentence depends on the fixer. Justified.
  - The repeated-list guard (any two string lists sharing 8 or more members) becomes a guard that compares the leg-1 list with the list literals inside `FIXER_OF` and `TASK_OF`, with `month_cutoff` allowed. This was previous Minor 4, and the plan says to do exactly this. It is narrower: a copied list elsewhere in `policy.py` is no longer caught. That is an accepted trade-off, but say so.
- **Page round (3b66755, 3fc5b35):** the page-by-figure tests are deleted, and the plan says what replaces them.
  - The first replacement is encoded faithfully: every tab's summary total equals the sum of its table.
  - The second is not. The plan says "every amount figure on the page can be filtered down to the rows that make it up within its own tab". It is encoded as "a summary row's count and total equal those of its table rows of that category".
  - On Balances and Cash there is one table row per figure, so that check holds trivially.
  - The deleted tests did prove that each balance equals the opening balance plus its September ledger lines, each shown with its amount; `PageByFigure.test_balances` covered that, and `BalanceFigureSources` checked those rows were exactly the ones cited. Their replacement, `test_balance_rows_cite_opening_and_september_lines`, only checks the first reference and the "+N more" count.
  - So no assertion is weaker than the plan's wording requires. But the guarantee the old tests gave is gone, and nothing replaced it. This is Material 1.
- **The cash total is count only, and the balances total is labelled as the trial-balance check (3fc5b35).** This is a sound reading, but it changes the plan ("its rows add up to a total row equal to the sum of the table below") without an amendment in `plan.md` or a line in the decision log. Minor 3.

**(b) Findings of the previous review (review-repairs-5)**

| Previous finding | Evidence | Status |
|---|---|---|
| Material 1: USD conversion error blocked its own correction, with no entry | Test plant PX10000700 +1,200 → one row (Processor / Finance Ops) with the new sentence, and one new entry E12 of 1,200.00, Dr 2105 / Cr 1210, balanced, citing the row (`UsdConversionCorrected`). Fixer filter at close.py:127. | fixed |
| (Mastercard-owned conversion) | Plant MC2827341940727 +1,200 → fixer Mastercard, Mastercard's sentence, no feed clause, no entry. This follows the session's reading in a030dcc; Andrés replaced it later the same day ("it can be adjusted"), in plan block a21a330, which is not built yet. | as planned at a030dcc, already overtaken by a later decision |
| (Edge case: both sides converted wrongly) | My plant: PX10000601 processor +1,200, Mastercard +500 → fixer Processor, E12 = 700.00. The processor's own error is 1,200. | not addressed. Minor 1 |
| Minor 1: feed clause read as the processor's job | "…resends the file; Finance Ops posts the proposed correction and the feed does not post the resent file", one constant (policy.py:208) | fixed |
| (Feed clause on auth after clearing was noise) | Removed. The 3 real-data rows now read "Processor corrects the authorisation or clearing date and resends the file". | fixed |
| Minor 2: thin wording on an old unpaid settlement | "Confirm the bank debits the settlement; still open after 5 business days, it escalates to the Controller; no entry", matching the company's close policy | fixed |
| Minor 3: no test for the missing-file checklist tasks | `ChecklistTaskDeleted` (T12 deleted → the checklist-ownership check fails naming T12) | fixed |
| Minor 4: guard threshold had no margin | Replaced by a guard that compares named lists (see a) | fixed, narrower |
| Minor 5: "month cut-off is Finance Ops'" said three times | `_FINANCE_OPS_TYPES` declared once; the Processor list is the leg-1 list minus it (policy.py:182-188) | fixed |
| Minor 6: test copy of the correction types | Read from `policy.CORRECTION_TYPES` | fixed |

**(c) Real data: passes.**

- Suite 369/369.
- **Cash:** unreconciled 0.00 = ledger 1,547,965.55 − reconciling item 400,000.00 − bank 1,147,965.55.
- **Entries:** `proposed_entries.csv` has 38 lines and 11 distinct `entry_id`, E01–E11.
- **Field by field against a run at 90c7a00:**
  - `balances`, `cash_recon`, `checks`, `close_tracker` and `proposed_entries` are byte-identical.
  - `exceptions.csv` has the same 262 rows, same order, same columns. Only `action` changed, on 116 rows: fx rate 95, amount 8, processor duplicate 6, sign flip 4, auth after clearing 3. All are the planned rewording.
  - Still 6 failed pre-checks, and no "not reliable" banner.
- **Page in Chrome.** The window would not go past 865 CSS pixels, so I measured inside a 1440 px iframe of the same page.
  - All 6 tabs, every summary row clicked. 20 on Exceptions (17 types plus 3 leg subtotals), 11 on Proposed entries, 11 on Balances, 4 on Cash, 4 on Close tracker, 2 on Checks.
  - Every click: the row count shown equals the summary count, the sum row equals the summary figure (59 comparisons, 0 mismatches), and the category select shows the value. "Clear filters" brings back 262.
  - Unfiltered sum rows:
    - Exceptions: "Leg 1: 15,600.17 / Leg 2: 40,616.94 / Leg 3: 511,128.18", never one mixed total.
    - Entries: 172,291.89.
    - Balances: 0.00 in all three columns, under the label "Trial balance check: each column sums to zero".
    - Cash: "Not added across lines", with a count-only total.
  - CSV export:
    - Sign flipped → 4 rows, only `sign_flip`, with notes columns.
    - Leg 3 subtotal → 6 rows.
    - Entry E03 → 2 lines, CSV columns.
  - Exceptions columns at 1440 px, in order: Date, Type, Net USD, Age, Escalates, Who fixes, Clara owner, What to do (right edge at 1039 px of a 1412 px box), Source, Source fields. Then the notes columns, which scroll inside the table box. No page-level horizontal scroll on any tab. This meets the plan.
  - The banner check with the T05 plant was not repeated; that code is unchanged since review 5.

**(d) Gap-filling decisions, judged one by one**

Repair round:

1. **The entry is only proposed when the fixer is the Processor, and the filter applies to every correction type (close.py:127). Right.** Only `usd_conversion_error` can get a Mastercard fixer (recon.py:118-121), so nothing else changes. One line, no new structure.
2. **A new map from (type, fixer) to sentence, `ACTION_BY_FIXER` (policy.py:243), read in `_difference` (recon.py:86). Acceptable.** It is a new structure for a single sentence, and a21a330 will rewrite that sentence anyway. A per-call override (the `fixer=` path already exists) would have avoided it. Keep it if a21a330 adds more fixer-dependent sentences; otherwise fold it in.
3. **The USD sentence is asserted on planted rows, not on the policy text. Right.** The loop over `USD_ACTION` in `test_feed_clause_only_where_an_entry_corrects` only checks the test's own constants, so it proves nothing. Harmless. Minor 4.
4. **The guard checks only the leg-1 list against the fixer and task maps. Right per the plan**, narrower than before (see a).
5. **The Mastercard-owned conversion gets no entry, and "Treasury follows the adjustment". Right at the time, now overtaken.** Andrés decided after this round to propose an entry. The a21a330 block covers it, so do not leave the "no entry" wording in the demo.
6. **The USD correction gets id E12 on new data, after the existing ones. Right**, as the plan says.

Page round:

7. **The cash total is a count only; the balances total is labelled as the trial-balance check. Right in substance.** Summing ledger + item + bank + unreconciled gives 3,095,931.10, which means nothing. But it is not recorded in the plan (Minor 3).
8. **Sum row of the visible rows: one figure when the rows shown share a category or the tab has a money total; per-leg lines on Exceptions; "Not added across lines" on Cash (template.html:468-475). Right**, and consistent with "never one total mixing the three legs".
9. **Leg subtotal rows are clickable and filter by leg. Right.** It is a sensible addition the plan did not ask for, and it was checked in Chrome.
10. **Which source fields are shown (policy.py, `SOURCE_FIELDS`). Faithful to the plan's list, wrong for leg 1.** For the processor and Mastercard files it is id, date, amount_usd, currency, merchant: no local amount, no rate. Combined with "first cited row only", an FX-rate row shows the processor's 25.04 next to a net of 0.94, with neither rate nor Mastercard's amount anywhere on the page. Part of Material 1.
11. **Row id = leg|type|key|src (report.py:153). Stable under a planted row (tested). One weakness:** the id includes the full source list. A rerun where a cited row moves, for example a renumbered checklist, gives a new id, and the saved note on that row disappears without warning. Minor 5.
12. **The gross-amount filter stays on gross while the visible column is net. Right**, and it is labelled "Gross at least (USD)".
13. **The summary carries leg and class on Exceptions, and status and approval level on Entries. Right**, as the plan asks.

**(e) Code standards: good.**

- **New rules declared once:**
  - `SOURCE_FIELDS` in policy only (tested);
  - one declarative `PAGE` map per tab in report.py:152-168 (category, sums, carried columns, row id, label, total);
  - summaries computed from the same table text the CSV writes, so the page and the files cannot disagree;
  - `ACCOUNT_NAME` derived from `policy.ACCOUNTS`;
  - one feed-clause constant.
- **The drill panel, the figures blob and the "By figure" tab are gone** (tested, net −6 lines across the three files).
- **Notes:**
  - The Balances lead sentence (template.html, `balances:`) and the total label in report.py:160 say the same sentence in two places. Small.
  - The sum row adds in JavaScript (`cents`/`plainCents`), not in Python. This is a change from the old "no money is added up in the browser" comment, which still sits at template.html:321. The arithmetic is exact to the cent for these sizes, and Chrome matched all 59 figures. Fix the comment or say why.

### Material

**1. Every figure built from several input rows can no longer be traced on the page to the rows that make it up.**

- **Where:**
  - report.py:183-197 (`_page_rows` keeps only `cited[0]`);
  - template.html:237-251 (the source cell shows that one row, "+N more", and the other references only in a mouse-hover tooltip);
  - tests/test_page.py `SummaryEqualsItsTable` and `test_balance_rows_cite_opening_and_september_lines`, which accept that.
- **Failure scenario,** in the demo, on Andrés's own example from 2026-10-14: «yo montaría el ledger balance, el total, y abajo una tabla con las transacciones» [I would show the ledger balance, the total, and below it a table with the transactions].
  - The Cash tab shows "ledger balance 1,547,965.55", source `gl_opening_balances.csv:2 +30 more`, and the opening row's three fields. The 30 September ledger lines that make up the other movements are not on the page, with or without a click.
  - The same holds for every balance on the Balances tab.
  - On Exceptions, a leg-1 pair shows only the processor row: an FX-rate row reads net 0.94 next to "amount usd: 25.04", with no rate and no Mastercard amount, so the page cannot answer "why is this a rate difference?"
  - The 2026-10-15 decision log entry says the redesign is "consistent with the 2026-10-14 decision 'source rows as tables per figure'". For multi-row figures it is not: before this round the drill panel delivered it and tests proved it; now neither does.
- **Fix** (session can decide the shape; it changes no figure):
  - Put every cited input row on the page, not just the first one: in the page block, `sources` as the full list of cited refs with their fields.
  - Render them inline under the row. Either the first row plus an expandable list in the same table cell (no side panel; expanding in place keeps the row in view), or, for Balances and Cash, a second table under the first listing the source rows of the figure selected in the summary, with amounts, a sum row equal to the figure, and a CSV. That second option is exactly Andrés's 2026-10-14 wording and keeps "summary on top, click filters in place".
  - Add the local amount and the rate to `SOURCE_FIELDS` for the processor and Mastercard files (drop merchant name to stay within 5 fields).
  - **Verifier:** bring back the deleted guarantee. For each balance and cash line, the source rows on the page sum to the figure, and they are exactly the cited rows. For each leg-1 pair, both sides' fields are present.

**2. On a 1440×900 laptop the Exceptions table starts below the screen, so a summary click visibly does nothing.**

- **Where:** template.html:415 (summary, then filter bar, then table, in page flow), with `.wrap` boxes up to `100vh − 230px` tall.
- **Measured** at 1440×900 in Chrome:
  - Exceptions: the summary is 686 px tall and starts at 295; the table starts at y = 1158, viewport 896.
  - Proposed entries: the table starts at 808.
  - Balances: the table starts at 829.
- **Failure scenario:** in the demo Andrés clicks "FX rate differs". The row turns green, and nothing else on screen changes, because the 95 rows appear below the fold. This is the "I lose where I was" complaint the redesign exists to fix.
- **Fix:** after a summary click, scroll the table's top into view (`host.scrollIntoView({block: "start"})` in `set()` when the change came from a summary row). Or cap the summary box height (about 40vh, with its own scroll) so the first table rows are visible. One line or a few CSS lines. Check by hand in Chrome; this cannot be tested in the suite.

### Minor

1. **USD conversion with both sides wrong under-corrects.** Plant: PX10000601 processor +1,200, Mastercard +500 → E12 700.00. The feed overstated by 1,200. The previous review flagged this edge; the plan did not take it up. It is rare, and the real data has none. Either correct using the processor's local amount converted at its own rate, or document it as left to the analyst.
2. **The Mastercard-owned USD sentence and "no entry"** are overtaken by Andrés's later decision. Make sure a21a330 replaces both, and the test `UsdConversionMastercard.test_no_entry` with them.
3. **Cash count-only total and the trial-balance label are not in the plan.** Add one line to the page block in `plan.md` (or the decision log) so the change of "rows add up to a total row" has a written source.
4. **The `USD_ACTION` loop asserts the test's own constants** (test_golden, `test_feed_clause_only_where_an_entry_corrects`). Delete it, or assert against the planted rows only.
5. **Saved notes are keyed by a row id that includes the source list** (report.py:153 for exceptions, and the cash row ids). A rerun that renumbers a cited row orphans the saved note without warning. Using leg|type|key, with `#n` for repeats, would be enough for exceptions.
6. **Stale comment** "no money is added up in the browser" (template.html:321), and the lead sentence repeating the balances total label (see e).

### What Andrés should look at in the Chrome demo

- **Cash tab**, the ledger balance row: decide whether "+30 more" is acceptable or whether the September lines must be visible (Material 1).
- **Exceptions:** click a type and see whether the table comes into view (Material 2). Then read one FX-rate row's source fields: rate and Mastercard side missing.
- **Exceptions sum row** with no filter: three per-leg lines. Click a leg subtotal to filter by leg.

**Throwaway files:**
Throwaway scripts and scratch copies were used for these runs; none is included.

The web server on port 8766 is stopped and the Chrome tab is closed.
