# Closing review of the readable payable bridge (cd7512e..0ef8363)

Brief B-2026-10-15-61 asked for a fresh-context, read-only review. I worked in my own clone at a scratch folder, at 0ef8363, with a worktree of cd9981d at a scratch folder. Runs, plants and extracted page data are under a scratch folder. Nothing was written in the repo, the records or the workspace, and the repo's working tree is clean. The Chrome tab is closed and the server on port 8773 is stopped.

**Verdict: not ready to submit.**
- **The accounting is still right.** I recomputed it from the raw files and the bridge matches:
  - ledger 70,588.66;
  - 30-Sep settlement 44,643.99 plus the four month cut-off rows 928.31;
  - entries on 2105: −116,160.96 with all entries, −125,288.88 with only the entries that need no evidence;
  - difference 0.00 and 9,127.92.
- **Most of the last review is fixed.** Every bridge link now opens rows that add up to its figure, there is no red tie error, the bridge reads as plain subtraction, and Grouped leg 2 and leg 3 are fixed.
- **What blocks submission:**
  - The workaround for the "no repeated source row" test is far wider than E10. **26 of the 42 entry lines, on every entry E01–E11, now cite an opening-balance row as their evidence**, in the `proposed_entries.csv` deliverable and on the page.
  - The run now **crashes** when `gl_opening_balances.csv` is missing.
  - Two bridge labels **overlap their own figures** on the Summary at 1440 px.
  - In a planted run, the E10 sentence states something false.

All four fixes are small.

### Closure checks

**(a) Verifier not weakened: yes, with one hole.**
- 5616e66 touches only `tests/`; 0ef8363 touches only `bridge/`.
- Every amended assertion cites the plan block:
  - the bridge line set and labels;
  - `DATA_FLAGS` 131 → 130;
  - blocked tasks = 8;
  - the weekend stale authorisations grouped by day.
- `test_every_bridge_figure_links` is replaced by `test_every_bridge_figure_opens_rows_that_sum_to_it`, which is stronger. It sums the opened rows the way the page sums them, and checks the page's own tie.
- **The hole:**
  - `test_source_rows_not_repeated_across_one_entrys_lines` (test_screens.py:1156) checks that a source reference is not repeated across one entry's lines. It never checks that each reference is true.
  - Combined with the output-file guard that every row must cite an input row (test_guards.py:293), it pushed the code into citing unrelated rows. That is Material 1.
- Also, no test renders the page with a missing input. The suite's deleted-opening-balances plant (test_golden.py:2500) only builds the reconciliation, so it never reaches the page code that crashes (Material 2).

**(b) Plan sentences encoded and implemented: mostly.**

| Plan sentence | Status |
|---|---|
| Every bridge link opens rows that sum to its figure | ✓ |
| "Source rows are not repeated across one entry's lines" | ✗ — met by fabricating evidence (Material 1) |
| Title, line labels, column labels, 9,127.92 sentence | ✓ on case data; the sentence is unconditional (Material 4) |
| Grouped leg 2 never shows an undebited day as paid | ✓ — plant3 gives 24-Sep bank 0.00, difference −44,884.41, 1 exception |
| Grouped leg 3 reconciles both rows the same way, with account names | ✓ |
| Weekend stale authorisations keep their real date | ✓ |
| At least 40 px of Summary margin | ✓ (67 px) |
| "Owed rows open … without moving the Summary" | ✗ — the page grows to 817 px and the tables below move 71 px |
| T08 shows the 2105 net | ✓ for the text; ✗ for its click (Material 5) |
| T07 not blocked; new sentence; hidden 2105 figure removed; gross difference in the data | ✓ |
| "The 2105 difference is computed once" | ✗ — still three expressions (code standards, below) |

**(c) Real data.**
- Suite: **469/469 green**.
- `run.py` compared with cd9981d:
  - byte-identical: exceptions.csv, balances.csv, cash_recon.csv, checks.csv, close_tracker.csv, treasury.csv;
  - run_manifest.json differs only in `code_version`;
  - **proposed_entries.csv changed, which the plan does not cover**: the `src` of 26 of 42 lines now cites `gl_opening_balances.csv` (Material 1).
- Independent recount (`review58/s/indep2.py`, which does not import the tool's code): 70,588.66; 44,643.99; cut-off 928.31. The 2105 lines in the output file net to −116,160.96. All tie.
- **Plants:**
  - plant3 (BS0024 deleted): Grouped 24-Sep is correct. The bridge, however, shows "Mastercard's 30-Sep settlement, debited 1-Oct **89,528.40**" (it now includes 24-Sep) and the sentence "**−35,756.49 = E10**: 3 processor-only rows…" (Material 4).
  - plant2 (two conversion errors): D04 goes to Mastercard with PX10000601 only. D07 goes to the processor and includes PX10000700. The bridge is unchanged, because E12 and E13 net to zero on 2105.
  - New plant, `gl_opening_balances.csv` deleted: 0ef8363 raises `KeyError: '1110'`; cd9981d writes all outputs.

**Chrome.** The window could not be resized (the viewport reported 3008 px), so, like the implementer, I measured in a 1440×813 iframe.
- **Summary height:**
  - 746 px, so 67 px of margin;
  - with the settlement and timing rows open: 817 px, a 4 px scroll.
- **No page-level horizontal scroll on any screen.** The Detailed table scrolls 87 px inside its own frame; I did not check whether that predates this round.
- **Every Summary figure clicked:** no red tie error. 1110 ledger 1,547,965.55, bank 1,147,965.55, items 400,000.00 and unreconciled 0.00 all tie.
- **Every bridge figure clicked:**
  - Ledger: 42 rows, "add up to the figure, 70,588.66".
  - Entries: "The lines in proposed entries add up to −125,288.88 / −116,160.96". But the CFO then sees 394–397 raw processor rows, and the entries table above stays at 41 lines, 172,291.89, with nothing highlighted.
  - Result: three lines — "add up to the figure, 70,588.66", "−125,288.88", "Together: −54,700.22" (Material 6).
  - Difference (first column): E10's 3 rows, 9,127.92. Difference (second column, 0.00): not clickable, which is correct.
- **Grouped leg 3, the clicks the implementer did not make:**
  - Settlement and timing expand in place, the tab does not move, and the rows are correct. One click opens both lines' rows for that column.
  - Difference goes to Close, E10, 9,127.92, no error.
  - The 1110 row goes to Detailed with 6 rows (all of leg 3, as disclosed on the page).
- **Clicking entry E10 in Close** lists "gl_opening_balances.csv:3 — Card Receivable — Customers, opening 3,412,880.55" as evidence.
- **Pending actions:**
  - The sentence and the 8 blocked tasks are right.
  - T08 "Show them in Close" says "add up to **151,379.59**" while T08 says 116,160.96, and it lists 25 opening-balance rows.
- **Drafts:**
  - Download .txt produces `D04-processor.txt`; I intercepted it, so no file was saved.
  - Copy did not show "Copied" inside the iframe. Clipboard access is likely blocked there; the copy code did not change this round.
- No console errors.

**(d) Judgement calls:** one by one, below.

**(e) Code standards: partly met.**
- **Good:**
  - The settlement and timing split reuses leg 2's pairing and leg 1's cut-off type.
  - `BRIDGE_LINES` is declared once.
  - The leg-1 gross difference is in the data.
  - The hidden figure is gone.
- **Drift:**
  - The 2105 difference is still computed three ways: `gap` in `_payable_bridge`, `before + owed`, and `before − after_all` in `_grouped`.
  - `_grouped` reads E10 back out of the rendered link's filter (report.py:568). With no pending entry it would print "including , which waits…".
  - The E10 sentence takes its row count from the leg-1 processor-only count, not from E10 (report.py:457).
  - `payable_owed: tuple = ([], [])` shares its lists as a default (close.py:53).

### Material, ranked by demo risk

**1. Every entry now cites an opening-balance row as evidence, in the output file and on the page.**
- **Where:** report.py:70-85 (the new `entry_lines` loop).
- **What happens:**
  - Once a row has been cited by one line, every other line of that entry that has no row of its own falls back to its account's opening-balance row.
  - This is not only E10: 26 of 42 lines are affected, across E01–E11. Examples:
    - E03's 1250 line cites `gl_opening_balances.csv:4`.
    - E05's 8,412.30 accrual on 2150 cites the 2150 opening row, whose balance is 0.00.
  - `proposed_entries.csv` changed against cd9981d, so the auditable deliverable changed outside the plan.
- **Failure scenario:**
  - The CFO clicks E10 and sees "Card Receivable, opening 3,412,880.55" listed as the support for a 9,259.40 credit.
  - An evaluator opens the output file and finds evidence that is not evidence. For a case graded on traceability and how AI was used, this is the worst finding.
- **Fix (code):**
  - Revert the `entry_lines` hunk to cd9981d: each line keeps `src_cell(_line_src(e, i))`. The output file is then back to byte-identical.
  - The 12-rows-for-3 symptom from the last review is already gone, because the entries and difference links now filter to the 2105 line.
  - If de-duplication is still wanted where several lines of one entry open together (T08, T13), do it at display time: in `drawSource`, skip a source reference already listed for the same entry and say "same evidence as the line above". Do not change the data.
- **Fix (tests):**
  - Replace `test_source_rows_not_repeated_across_one_entrys_lines` with:
    - `proposed_entries.csv` `src` equals the cd9981d rule (the entry's rows, with the rows other lines cite alone replaced by the one row this line cites);
    - no entry line cites `gl_opening_balances.csv` unless the entry is built from it.
  - Optionally, add a source-panel test that the T08 link lists each reference once per entry.

**2. A missing opening-balances file crashes the run.**
- **Where:** report.py:564/570/575. `names[cash_account]` reads account names from `gl_opening_balances.csv`. The old code used the constant `ACCOUNT_NAME`.
- **Failure scenario:**
  - An evaluator deletes an input to show "missing inputs are never estimated".
  - 0ef8363 dies with `KeyError: '1110'`; cd9981d wrote all outputs.
  - An empty data folder crashes the same way.
- **Fix:** `names.get(account, ACCOUNT_NAME[account])`, or keep `ACCOUNT_NAME` as the fallback.
- **Test:** extend the deleted-inputs plant (test_golden.py:2500) to also call `report.write`, or add a page test over the same plant.

**3. Two bridge labels overlap their figures on the Summary at 1440 px.**
- **Where:** template.html:111 sets the first bridge column to `white-space: nowrap; width: 50%`.
- **Measured:** the cell is 221 px wide.

  | Label | Width needed |
  |---|---|
  | "Mastercard's 30-Sep settlement, debited 1-Oct" | 271 px |
  | "September transactions Mastercard cleared in October (timing)" | 362 px |
  | "Ledger at 30-Sep (debit — the wrong side)" | 247 px |

  The screenshot shows "1-Oct44,643.99" and "in Oct928.31ming)".
- **Failure scenario:** on the CFO's first screen, the block the 0.00 rests on has garbled text.
- **Fix:** allow wrapping in that column (the 67 px margin absorbs about two extra lines), or shorten the labels, e.g. "MC 30-Sep settlement (paid 1-Oct)" and "Sep. items MC cleared in Oct. (timing)".
- **Test:** no automated test can see this. Add it to the hand checks: "no bridge label wider than its cell".

**4. The E10 sentence and the settlement label are stated, not computed.** This shows only in a planted run.
- **Where:**
  - report.py:452-458: the sentence prints `gap` followed by "= E10: N processor-only rows".
  - report.py:440: the settlement label is the fixed text "Mastercard's 30-Sep settlement, debited 1-Oct", whatever the settlement line contains.
- **Plant3 (BS0024 deleted):**
  - "Mastercard's 30-Sep settlement, debited 1-Oct **89,528.40**" (30-Sep plus the never-debited 24-Sep).
  - "**−35,756.49 = E10**: 3 processor-only rows; its entry waits for evidence."
- **Failure scenario:** Someone plants a missing debit and the page asserts a false identity.
- **Fix:**
  - Emit the sentence only when `gap == Σ delta[left_out]`. Otherwise say "of which 9,127.92 is E10; −44,884.41 not explained".
  - Take the row count from E10's own sources.
  - Build the settlement label from the unpaid days, e.g. "Mastercard settlements not debited by 30-Sep (24-Sep, 30-Sep)".
- **Test:** on the BS0024 plant, the note does not say "= E10" with −35,756.49, and the label names 24-Sep.

**5. T08's click contradicts T08's figure.**
- **Where:** template.html:812-813: the "Show them in Close" link sums `"debit"` over every line of the 9 entries.
- **What the page shows:** T08 says "9 proposed entries (116,160.96 USD)"; the click says "add up to 151,379.59 USD" and lists 25 opening-balance rows (the second part goes away with fix 1).
- **Failure scenario:** a CFO checks the one task that is about 2105 and gets a different number.
- **Fix:** have `_pending` emit the task's link from the data. For a task with an account in `EVIDENCE_ENTRIES`, use `{entry_id, account}` summed as debit minus credit, the same link as the bridge's entries line. The template then just follows it.
- **Test:** T08's link, opened as `_opened` opens it, equals the figure in T08's text.

**6. Clicking the result shows a "figure" and a total that are not the figure.**
- **Where:** template.html:886-897 and the tie line it prints for each part.
- **What the page shows:** for "Ledger after the entries (credit) 54,700.22":
  - "The amounts add up to the figure, 70,588.66 USD."
  - "The lines in proposed entries add up to −125,288.88 USD."
  - "Together: −54,700.22 USD."
  - A footer "Sum of amounts 70,588.66" under 436 rows.
- **Failure scenario:**
  - "The figure" here is the ledger's figure, not the one clicked.
  - The total carries the opposite sign to the cell. It is explainable out loud, but it is the line a CFO reads.
- **Fix:**
  - When the link has several parts, word the first line "Ledger rows add up to 70,588.66".
  - Print "Together: −54,700.22 USD debit, that is 54,700.22 credit, the figure".
  - Drop or relabel the footer sum when several parts are shown.

### Minor

1. **Nine tasks still read "Lacks…" while the sentence says 8 are blocked.** T07: "Lacks 400,000.00 USD funding in transit, a reconciling item to confirm on 01-Oct." Reword it to "Waits on 400,000.00 USD funding in transit…" or mark the blocked rows.
2. **Opening the settlement or timing rows pushes the page to 817 px** (4 px of scroll) and moves the tables below by 71 px. The plan said "without moving the Summary".
3. **One click on settlement or timing opens both lines' rows** for that column. That is acceptable, but a CFO expects only the clicked line's rows.
4. **The entries link leaves the Close entries table unfiltered and unmarked** (41 lines, 172,291.89). The 8 or 9 lines the tie sentence refers to are not visible as lines, only their 394 raw source rows.
5. **The 2105 difference is computed three ways**, contrary to the plan; `pending` is parsed back from the link filter (report.py:568); `items_note` breaks with no pending entry; `payable_owed` has a shared mutable default (close.py:53).
6. **The Detailed table scrolls 87 px inside its frame at 1440 px**, so the Comment column is cut. I did not check whether this predates this round.

### Judgement calls, one by one

1. **The opening-balance row cited by lines with no row of their own (the known workaround).**
   - **Reject.** It fabricates evidence, on 26 lines, not only E10's three, and it changes the output file.
   - The underlying conflict is not real: the 2105 filter already removed the repetition the last review saw.
   - Fix as in Material 1: revert the code, de-duplicate at display time if wanted, and replace the test with one that pins honest per-line sources.
2. **Settlement and timing as "sources", not links.** Accept. They tie, and the test checks them against the raw recount.
3. **A list of two links for the result.** Accept the mechanism: it is the only way the rows sum to the result. Fix the wording of the tie lines (Material 6).
4. **The entries sum as ["debit", "credit"].** Accept. It is debit-positive, as in balances.csv, and the page's "−125,288.88" reads correctly between "debit 70,588.66" and "(credit) 54,700.22".
5. **The 24-Sep sign in the plant (difference = bank − net = −44,884.41).** Accept. It is consistent with 17-Sep's +40,616.94 (the bank paid more).
6. **The sign of the 2105 reconciling items (+116,160.96, so that difference − items = 0, like 1110).** Accept. The two rows now read the same way.
7. **T07 excluded from the blocked count by name (`NOT_BLOCKED = ("T07",)`, policy.py:302).**
   - Accept the outcome, reject the mechanism.
   - The rule is "a reconciling item to confirm is not a defect", so derive it from the type or class of what T07 lacks: funding in transit, a timing item.
   - As written, a real cash defect planted on T07 would never count as blocked.
8. **T07 not counted as blocked (the session's call).** Accept. The cash reconciliation closes to 0.00 with it as a reconciling item. But the row still says "Lacks" (Minor 1).
9. **The implementer's iframe measurement (746 px).**
   - Confirmed: 746 px, with 67 px of margin.
   - With the settlement and timing rows open: 817 px.
   - Height was the wrong thing to stop at: the label overlap (Material 3) is visible in the same frame.
10. **Is the bridge correct and readable for a CFO?**
    - Accounting: yes.
    - Readability: yes on the case data once Materials 3 and 6 are fixed.
    - Under a plant it still needs Material 4.

### Throwaway files

All under a scratch folder:
- `out_new/`, `out_old/` — the runs at 0ef8363 and cd9981d;
- `out_plant2/`, `out_plant3/` — the reused plants, run at 0ef8363;
- `plant_noopen/` — the case data without `gl_opening_balances.csv`;
- `s/*.json` — the page data extracted from each run.
