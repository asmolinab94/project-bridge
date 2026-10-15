## Fresh review of the five-screens round (95dee86..325f90d)

Brief B-2026-10-15-53. Fresh-context opus reviewer, read-only. I worked in my own clone at a scratch folder, at commit 325f90d. Throwaway scripts and planted data copies are under a scratch folder. Nothing was written in the repo, the records or the workspace.

**Verdict: not ready.**

- **The mechanics are done well:**
  - Every cited input row is now on the page, and leg-1 rows show both sides.
  - Each Close figure has its own source-row table, and each table sums to its figure.
  - Every Summary figure that has a link lands on the right screen with a matching count and sum.
  - Copy and the .txt download work, there are no console errors and no horizontal scroll.
  - The verifier is stronger than before: the Treasury figures are now pinned.
- **What stops sign-off is what a CFO reads.** The first screen contradicts itself on leg 1. It shows an unexplained 130,832.82 gap on the Mastercard payable, using a figure labelled "as the settlements imply it" that is in fact built from the processor's file. On Pending actions, the tool's own red "Blocked" badge sits in the Status column, and the adjusting-entries task (T13) says the tool has "no evidence" for it. The Grouped view hides leg 2's only exception. On top of that, the suite goes red on correct behaviour if both currency-conversion errors are planted.

### Closure checks

**(a) Verifier not weakened: yes.**

- Code commits bb3645d and 325f90d touch only `bridge/`. Test commit 1516c24 touches only `tests/`.
- Changes to existing tests:
  - The extras-review Treasury readings are narrowed to the settled ones: duplicate left out, sample deviation, k = 2. The five headline figures and 21-Sep = 41,402.03 are pinned exactly. This fixes extras-review Material 1.
  - The "first cited row and +N more" test is replaced by one that checks every cited row and its fields, for every table plus Treasury (`EveryCitedRowOnThePage`).
  - The deleted balance test is replaced by `CloseFigureSourceTables`, which recomputes each balance's rows and amounts from the raw ledger files. This restores the guarantee review 6 asked for.
  - The Treasury tab test is loosened to "the script mentions Treasury and reads `PAGE.treasury`". The plan justifies this, because Treasury moves inside the Close screen.
  - Every removed assertion is justified by the plan.
- Two gaps in the new tests:
  1. `SummaryScreen.test_every_linked_figure_equals_its_rows` (test_screens.py:181) only checks figures that already have a link. A figure with no link passes silently (see Minor 1).
  2. `DraftedMessages.test_each_draft_names_only_its_own_rows` (test_screens.py:521-522) ignores who fixes the error. It is wrong for a planted mix of conversion errors (Material 6).

**(b) Plan sentences: mostly encoded and implemented. Gaps:**

- "Every figure links to the screen and filter that shows its rows": six Summary figures have no link, against one settled exception (Minor 1).
- "Data quality … and, above it, one row per input file": the input files table is below the checks.
- Review 6 minor 1, "said in the action sentence": not done. The USD conversion sentence at policy.py:251 says nothing about the case where both sides are wrong.
- "Summary fits with no scrolling at 1440×900": not met (Material 5).
- "The tool never marks a task done — status stays the checklist's": met in the data, not in what the page shows (Material 3).

**(c) Real data**

- Suite: 423/423 green in the clone.
- `run.py` writes nine files, cash unreconciled is 0.00, and there are 11 entries.
- Compared with d2d3a79:
  - exceptions.csv, balances.csv, cash_recon.csv, checks.csv, close_tracker.csv and treasury.csv are byte-identical;
  - proposed_entries.csv changes only in the E05 title (extras minor 2, planned);
  - the manifest's totals are unchanged apart from the new `matches` block.
- Match counts recomputed by my own script from the raw files, without importing `bridge`:

  | Figure | Count | USD |
  |---|---|---|
  | Processor rows | 3,117 | 924,303.45 |
  | Mastercard rows | 3,113 | 909,419.05 |
  | Pairs | 3,108 | |
  | – equal | 2,997 | 881,142.94 |
  | – with a difference | 111 | |
  | Processor duplicates | 6 | |
  | Processor-only (gross) | 3 | 9,259.40 |
  | Mastercard-only (gross) | 5 | -2,066.18 |
  | Mastercard 1-2 Oct rows matched to September | 4 | |
  | Leg-2 settlement days, all paired | 22 | 968,096.50 |

  - The tool shows the one-side rows at net (9,127.92 and -2,041.36), as the session settled.
- **Chrome, 1440×900 window (viewport 1440×813):**
  - All 19 linked Summary figures land on the right screen and filter. Each count and sum row matches, and the table top sits at 142–657 px, so it is in view.
  - Grouped → Detailed works.
  - The PX10001897 source row expands in place, showing processor 25.04 / 133.68 / 5.339 against Mastercard 24.08 / 133.68 / 5.5526.
  - Every balance and the ledger cash source table sums to its figure (e.g. 1110: 31 rows = 1,547,965.55; 2105: 42 rows = 70,588.66).
  - Copy shows "Copied". The .txt download produces `D03-mastercard.txt`; I intercepted it, so no file was saved.
  - No console errors; page width is 1440 on all five screens.
- **Planted run** (processor row PX10000001 deleted): the Summary moves exactly as my script predicts — processor rows 3,116, equal pairs 2,996, Mastercard-only 6, leg-1 exceptions 256 / 15,565.41. The "2105 as the settlements imply it" figure also moved, by 34.76 (Material 2).
- Tab and server closed.

### Material, ranked by demo risk

**1. The first screen contradicts itself on leg 1.**

- **Where:** template.html:420-422 (the note), report.py `_overview`.
- **What the page shows:**
  - Processor rows 924,303.45 and Mastercard rows 909,419.05, with "Processor minus Mastercard: 15,600.17 USD" directly below. Those two figures differ by 14,884.40; the 15,600.17 is the net difference of the exceptions.
  - The Grouped view's leg-1 sum row shows the difference as 14,884.40 — so the page shows two different "processor minus Mastercard" figures.
  - The processor side doesn't add up: 2,997 + 111 + 3 = 3,111, not 3,117. The 6 duplicates have no line in the block.
- **Failure scenario:** the CFO subtracts the two bold numbers, gets 14,884, reads 15,600 below, and the first minute of the demo goes to explaining it.
- **Fix:**
  - Relabel the note "Net difference of the exceptions: 15,600.17 (gross 14,884.40)", or show the gross figure there.
  - Add a figure "Duplicates in processor: 6, net 3,593.63", linked to `processor_duplicate`.
  - Add a test that the leg-1 counts add up on each side.

**2. "2105 as the settlements imply it" (-60,244.16) is the processor file's view. The 130,832.82 gap is not explained anywhere on the page.**

- **Where:** close.py:228-240 (`_payable_implied`), report.py:368 and 419-422.
- **What the figure really is:**
  - Opening -71,243.18 − what the processor file posts (net 912,453.49) + September settlement debits less the duplicate (923,452.51) = -60,244.16.
  - That equals Mastercard's unpaid 30-Sep settlement (44,643.99) plus the leg-1 difference (15,600.17), so it carries the processor's own errors.
  - Proof: deleting one processor row moved it by 34.76.
- **What the 130,832.82 is made of:**
  - 116,160.96 — the proposed entries on 2105 (before 70,588.66 → after all -45,572.30);
  - 14,671.86 — leg-1 real errors that the processor file carries.
- **The true story:** after all proposed entries, 2105 = -45,572.30. That is 44,643.99 (Mastercard's 30-Sep settlement, debited 1-Oct) + 928.31 (cleared by Mastercard in October). Difference 0.00.
- **Failure scenario:** the CFO sees a ledger at 70,588.66 against -60,244.16, or the Grouped view's "Difference 130,832.82", and asks why the payable is off by 130k. Nothing on the page answers.
- **Fix — Andrés decides, since this is a leg-3 rule:** compare 2105 after the proposed entries with what Mastercard's own settlements leave unpaid (30-Sep summary + October cut-off), giving 0.00. Show the bridge as ledger → proposed entries → Mastercard-owed, and label it as such.

**3. Pending actions: the tool puts its own "Blocked" in the Status column, and the task the tool exists for says "no evidence".**

- **Where:** template.html:764-765; report.py `_pending`; test_screens.py:401-460.
- **The "Blocked" badge:**
  - A red "Blocked" badge replaces the checklist status, which drops to grey below it. T02 and T05 are "In progress" in the checklist; T06, T07, T11 and T12 are "Not started".
  - The checklist has its own "Blocked" status, so T09 reads "Blocked / Blocked".
  - That breaks Andrés's condition: status stays the checklist's.
- **T13 and T08:**
  - T13, "Prepare and post adjusting JEs", and T08, "Roll forward 2105", read "No tool evidence; depends on the owner".
  - Yet the status sentence right above says 11 entries (172,291.89) wait for approval, and the close tracker table on the same page says the tool evidences both tasks (`policy.TOOL_EVIDENCE`).
  - The verifier forces this. It derives a task's entries only through exceptions that cite the task's checklist row, so T13 cannot list any entry.
- **T07 and T12:**
  - T07 is "Blocked" by the 400,000 funding in transit, although the cash reconciliation closes to 0.00 with that as a reconciling item.
  - T12 reads "Lacks 1 exception (net 0.00 USD)".
- **Fix:**
  - The Status column shows only the checklist status; the tool's finding goes in its own column ("Tool finding: blocked by …").
  - T13 lacks = the 11 entries awaiting approval; T08 lacks = the 2105 entries and roll-forward. For a task with no exception, use `TOOL_EVIDENCE`, which is already declared once.
  - T07 and T12 say what is missing in words (a reconciling item to confirm on 1-Oct; the invoice was not received).
  - Amend the test in a test commit first.

**4. The Grouped view hides leg 2's only exception, and most day clicks land on empty tables.**

- **Where:** report.py `_grouped`; template.html:668.
- **Leg 2:**
  - Every one of the 22 days shows difference 0.00, and the sum row is 0.00, because the duplicate debit BS0018 is left out of the bank column. Meanwhile the Summary says leg 2 has a 40,616.94 exception.
  - Clicks filter on the exception's own date, not the settlement day. Clicking 18-Sep gives 0 rows; the duplicate would show under the 21-Sep settlement row, which is not the day it duplicates.
- **Leg 1:** the 2-Oct row shows a difference of -697.39 with 0 exceptions, and clicking it gives an empty table. The matching +697.39 sits in the 30-Sep row, mixed with 5 unrelated exceptions.
- **Failure scenario:** "Grouped" is the CFO view. The headline duplicate is invisible there, and clicks show empty tables.
- **Fix:**
  - Put the duplicate on the settlement day it duplicates: bank 82,018.97, difference 40,616.94, 1 exception.
  - Make a group-row click filter to that group's exception row ids, not a date range.
  - For leg 1, either place pairs on the processor's clearing date (the date the exception carries), or make the 1-2 Oct rows open the month cut-off rows and say so in the row.

**5. The Summary does not fit at 1440×900.**

- The page is 936 px tall: even a bare 900 px viewport scrolls (the footer drops below), and in a normal 1440×900 Chrome window, which leaves 813 px for the page, the last two rows of "Leg 1 difference by type" (Only in processor, Only in Mastercard) are cut off.
- The plan asked for no scrolling; the session's hand check missed it.
- **Fix:** drop the "Input not supplied" banner on the Summary (the data-quality sentence already says it, and it saves ~50 px), or put the by-type figures in one row.

**6. The suite goes red on correct behaviour when both conversion errors are planted, and the processor-owned one gets no draft.**

- **Where:** test_screens.py:521-522; policy.py `DRAFT_TEMPLATES`.
- **Shown:** I planted Mastercard MC2827341940727 +1,200 and processor PX10000700 +1,200, both currency-conversion errors. D04 (to Mastercard) correctly lists only PX10000601. `test_each_draft_names_only_its_own_rows` then fails, because it expects every conversion-error row. No draft goes to the processor for PX10000700.
- **Failure scenario:** Someone who plants an error to watch a test fail hits a test that is wrong, not one that caught a bug.
- **Fix:**
  - Test commit: the expected rows are those whose type is in the template's types **and** whose fixer matches the template's fixer.
  - Code: route processor-owned conversion errors to the processor's amount-and-rate template (fixer = Processor). The plan's "amount and rate errors" covers them.

**7. The D01 draft to Mastercard complains about the edge of our own file.**

- The single failing summary day is 31-Aug (`mastercard_daily_settlement_summary.csv:2`). It has no detail rows because the clearing detail file starts on 1-Sep.
- The draft names no day and no amount, only the check's generic sentence. The plan said each draft fills in its rows and amounts.
- The check was already failing on the same day before this round; drafting a message on it is new.
- **Failure scenario:** the CFO asks which days. The answer is "the day before our extract starts".
- **Fix:** have the check skip summary days outside the detail file's settlement dates (or report them as a coverage note). List each mismatching day with both counts and nets in the draft. Draft nothing when no day remains.

### Minor

1. **Six Summary figures have no link:** processor rows, Mastercard rows, settlement days, days paired, the 2105 implied figure, and "matched with no difference" (that last one was settled). Processor and Mastercard rows can link to Grouped leg 1, whose sum row equals them to the cent; the leg-2 figures can link to Grouped leg 2. Make the test require a link unless the figure is on a declared list.
2. **"253 items wait on Mastercard or the processor" is arithmetically right but misleading.**
   - It is 251 + 1 + 1. Of those, 130 are zero-money data flags (105 bad references, 22 stale authorisations, 3 authorised after clearing) and 1 is the missing invoice. Only 122 carry money, and most of those already have a proposed entry, so the close itself does not wait on outsiders.
   - The 5 Mastercard-only rows are marked as fixed by the processor, but their draft goes to Mastercard.
   - Reword: "122 differences (X USD) need a corrected file or a credit — 121 from the processor, 1 from Mastercard; 131 data flags go back to the processor."
3. **A leg-3 account row filters to all of leg 3:** 6 rows summing to 511,128.18, against the row's 400,000. The page says so, which is honest. A type → account map declared once in policy would fix it.
4. **Currency dropped from the source fields as well as merchant.** Accept: id, date, USD, local amount and rate already make 5 fields. Record it in the plan, because the plan's text says only merchant was dropped, and a local amount like 624,409.0 has no currency beside it.
5. **The check → task map is dead code.** Emptying `CHECK_TASK` keeps all 423 tests green, and checks.csv is identical with or without it: failed checks already cite the checklist row through the existing type → task map. It is a second statement of the same link. Remove it, together with report.py:81-83.
6. **Workarounds to dodge old tests:**
   - `FIGURE_LIST = "figures"` (template.html:145) dodges the old ban on `.figures` (test_page.py:510);
   - empty `summary: []` lists on the overview, pending and grouped blocks satisfy test_golden.py:2728.

   Fix both old tests in a test commit (narrow the regex to the deleted top-level blob; use `block.get("summary", [])`), then remove the workarounds.
7. **"Draft — not sent" is also a literal in template.html:785.** The "declared once" test scans only Python files. Read the wording from the data.
8. **The links on the "how much is explained" cells are built in the template, not the data.** They tie (same leg + class filter as the tested sums) but are not tested. Acceptable; say so in the plan or add them to the data's figures.
9. **Drafts to outside parties:**
   - they say "net", and Mastercard-only rows carry minus signs;
   - D03 doesn't name the original debit BS0016 or the dates;
   - D06 runs to 103 lines.

   Use gross amounts, dates, and the other side's reference.
10. **Small display issues:**
    - Done tasks read "Done in the checklist. No tool evidence; depends on the owner." Drop the second sentence.
    - Task names on Pending actions break mid-word ("cle aring").
    - "Days with no bank debit: 0" is clickable and opens an empty table.
    - The Summary's leg-3 block shows no 2105 difference line; it appears only in Grouped.

### Judgement calls, one by one

1. **Leg 1 grouped on Mastercard's own clearing date (1-2 Oct rows with processor 0).** Reject as built. The day totals are right, but the rows show a difference with 0 exceptions and clicks open empty tables (Material 4).
2. **2105 "implied by settlements" = -60,244.16 against ledger 70,588.66, and its 130,832.82 explanation.** Reject. The figure comes from the processor file, and the gap is 116,160.96 of proposed entries plus 14,671.86 of processor errors. The settled ambiguity said "no new rule", but `_payable_implied` is a new rule (Material 2).
3. **Currency dropped to fit local amount and rate.** Accept, and record it (Minor 4).
4. **Processor-owned conversion errors get no draft.** Reject. The plan's processor list covers them, and the test behind the choice is wrong (Material 6).
5. **T08 and T13 forced to "No tool evidence".** Reject. The tool evidences both, according to its own policy and its own tracker. The test forced it (Material 3).
6. **checks.csv source column changed for linked checks.** Accept: it is a no-op on the case data, since the output is byte-identical. But the mechanism is dead code (Minor 5).
7. **Empty `summary` lists to satisfy an old test.** Workaround; fix the test (Minor 6).
8. **`FIGURE_LIST` to dodge the `.figures` ban.** Workaround. The test's intent (the old blob is gone) still holds; fix the regex (Minor 6).
9. **A leg-3 account click filters to all of leg 3.** Accept for now, since it is disclosed on the page (Minor 3).
10. **Explained-split links in the template, not the data.** Accept; they tie, but are untested (Minor 8).
11. **"253 items wait on Mastercard or the processor".** The count is right; the wording is not useful (Minor 2).
12. **"Blocked" = an open task lacking at least one item (settled).** Fine as a count in the sentence. Wrong as a badge in the Status column (Material 3).

### Throwaway files

All under a scratch folder:
- `s/indep.py` — the match recount from raw files;
- `s/blob.py` — extracts the page's embedded data;
- `plant/` — the deleted-row run;
- `plant2/` — the two conversion errors;
- `mut/` — the copy with the check → task map emptied;
- `old/` — a git worktree of d2d3a79, used for the output comparison.
