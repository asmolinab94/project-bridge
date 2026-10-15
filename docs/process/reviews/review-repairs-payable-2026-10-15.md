# Fresh review of the repairs round and the Mastercard payable bridge (b3a73a8..cd9981d)

Brief B-2026-10-15-58. This is a fresh-context, read-only review. I worked in my own clone at a scratch folder, at commit cd9981d, with a worktree of 325f90d at a scratch folder. Throwaway scripts and planted copies are under a scratch folder. Nothing was written in the repo, the records or the workspace; the repo's working tree is clean.

**Verdict: not ready. Two fixes are needed before the demo, and they are small.**

- **Every finding of the five-screens review is answered, and the accounting is right.** I recomputed the payable from the raw files, and the bridge's figures are correct: ledger 70,588.66 → entries −116,160.96 → result −45,572.30 → owed 45,572.30 → difference 0.00. With only the entries that need no evidence, the difference is 9,127.92, which is exactly E10.
- **What stops sign-off is the bridge as a CFO clicks it.** "Result after the entries" opens a red tie error: the page says its own figure doesn't add up. "Proposed entries" opens 1,584 raw processor rows with no total. The block's signs and labels also need explaining out loud: "Confirmed" when nothing is confirmed, and −45,572.30 against 45,572.30 giving 0.00.
- **A smaller defect shows only in a planted run:** the Grouped view would show a settlement the bank never debited as paid.

### Closure checks

**(a) Verifier not weakened: yes.**
- The code commits (49c03e9, cd9981d) touch only `bridge/`. The test commits (72a3eb0, ce6876b, a7e0425) touch only `tests/`.
- Every amended assertion is justified in the plan:
  - The summary-vs-detail check now passes on 31-Aug, which becomes a coverage note. This is plan material 7, in `test_golden.py` and in a7e0425's 8 passed / 5 failed.
  - The `.figures` ban is narrowed to the old blob, and `summary` is read with a default. Both were minor 6 of the last review.
  - The test that forbade entries on T13 is amended.
- The new tests are stronger than before: owed is recomputed from the raw files, a planted +100.00 moves the figures, and each draft holds exactly its own rows, routed by who fixes them.
- **One gap.** `PayableBridge.test_every_bridge_figure_links` (test_screens.py, ce6876b) checks that each link has the right shape, not that the rows it opens add up to the figure. That gap is why Material 1 passes the suite.

**(b) Plan sentences encoded and implemented: mostly.**
- The repairs block is met in full, including its amendment: the duplicate debit sits on the 17-Sep row, drafts are routed by the template's declared fixer, and 9 tasks are blocked.
- Payable block gaps:
  - "Every figure links to its rows (the entries on 2105 …)": the entries and difference links open raw input rows, not the entries on 2105 (Material 2).
  - "Explained as the processor-only rows whose entry is conditional on evidence": no words on the page say this; there is only a link to E10 (Material 3).
  - The owed figure expands its rows in place rather than linking. That is acceptable.

**(c) Real data.**
- Suite: 454/454 green.
- `run.py` compared with 325f90d:
  - exceptions.csv, balances.csv, cash_recon.csv, close_tracker.csv, proposed_entries.csv and treasury.csv are byte-identical.
  - checks.csv changes only on the summary-vs-detail check: it now passes with the note "not compared … 2026-08-31".
  - The run manifest's failed checks go from 6 to 5, and it gains a `processor_duplicate` block (6 rows, 3,593.63).
- My own script (`s/indep2.py`) recomputes from the raw files, without importing `bridge`:

  | Figure | USD |
  |---|---|
  | 2105 ledger at 30-Sep (opening −71,243.18 + September lines) | 70,588.66 |
  | Mastercard summary nets for days up to 30-Sep | 968,096.50 |
  | September settlement debits, without the duplicate BS0018 | 923,452.51 |
  | What Mastercard's statement shows unpaid (the 30-Sep settlement, debited 1-Oct) | 44,643.99 |
  | Month cut-off rows (MC3286778140422, MC5706907923546, MC5451055203583, MC9661041730708) | 928.31 |
  | Entries on 2105, E01–E11 (E10 +9,127.92 is proposed-conditional) | −116,160.96 |
  | 2105 after all entries | −45,572.30 → difference 0.00 |
  | 2105 after the entries that need no evidence | −54,700.22 → difference 9,127.92 |

  The settlement and clearing dates are equal in the detail file, so the 30-Sep settlement covers the 30-Sep clearings; nothing is double-counted with the cut-off rows.
- **Chrome, 1440×900 window (813 px for the page):**
  - The Summary is 813 px tall: no scroll, but with zero to spare.
  - Leg 1 adds up on both sides: 2,997 + 111 + 6 + 3 = 3,117 processor rows; 2,997 + 111 + 5 = 3,113 Mastercard rows. The note reads "Net difference of the exceptions: 15,600.17 USD (gross difference of the files: 14,884.40)".
  - Grouped view: leg 2 totals 968,096.50 against 1,008,713.44, difference 40,616.94. Clicking 17-Sep gives 1 row (BS0018). Clicking 08-Sep gives its 6 exceptions.
  - Pending actions: the Status column equals the checklist for all 26 tasks, and the Tool finding column is in place.
  - Copy shows "Copied" on a real click. The .txt download produces `D05-processor.txt`; I intercepted it, so no file was saved.
  - No console errors.
- **The two-conversion-errors plant** (from the last review; Mastercard MC2827341940727 +1,200 and processor PX10000700 +1,200):
  - D04 goes to Mastercard with PX10000601 only. D07 goes to the processor with PX10000700, under its amount-and-rate template.
  - The draft-routing tests stay green.
  - One test goes red: `test_coverage_note_and_no_draft`. That is a true catch: after the plant, Mastercard's detail disagrees with its own summary on 8-Sep. Andrés should expect it if he plants on the detail file.
- Tab closed, server stopped.

**(d) Judgement calls:** one by one, below.

**(e) Code standards: met, with notes.**
- Owed reuses leg 2's settlement pairing and leg 1's month cut-off type; neither rule is restated.
- `EVIDENCE_ENTRIES` and `FINDING_WORDS` are each declared once.
- Notes:
  - The 2105 difference is computed twice in report.py, in two different forms: `-after - owed` in `_payable_bridge` and `before + owed` in `_grouped`.
  - The template hard-codes the `3.ledger_2105` figure id (template.html:460).
  - The leg-1 gross difference is computed in the page script, not in the data (Minors).

### Material, ranked by demo risk

**1. Clicking "Result after the entries" shows a red error on the page's own figure.**
- **Where:** report.py:407-408 links the result to `balances` with `sum: after_confirmed / after_all`. The Close screen's source table (template.html:858-866) lists the ledger's source rows only, and those add up to the balance before the entries.
- **What the page shows:** "The amounts add up to 70,588.66 USD; the figure is -54,700.22 USD" (and −45,572.30 on the other column), in red. The same happens from Grouped leg 3's 2105 row.
- **Failure scenario:** the CFO clicks the figure the 0.00 rests on, and the tool itself says it doesn't tie.
- **Fix:** link the result to the ledger rows plus the 2105 lines of the entries, so the rows sum to the result. Or make the result cell not clickable, since ledger and entries each already link.
- **Test:** add a test that every bridge link's rows sum to its figure, using the same tie the page draws.

**2. "Proposed entries on 2105" and "Difference" open raw input rows, not the entries.**
- **Where:** template.html `bridgeBlock` → `linkOf` builds `{table: "proposed_entries", filter: {entry_id: ids}}` with no account and no sum.
- **What the page shows:**
  - −116,160.96 opens 1,584 processor source rows with no total.
  - 9,127.92 opens the same 3 processor rows repeated 4 times (12 rows), because E10 has 4 lines.
  - The entries table above stays unfiltered: 11 entries, total 172,291.89.
- **Failure scenario:** "show me the entries" leads to a wall of transactions and a total that matches nothing.
- **Fix:**
  - Filter to `{entry_id: ids, account: "2105"}` with a net debit-minus-credit sum, so the entries table shows the 9 lines (or E10's one line) and ties to the figure.
  - Remove duplicate source rows across one entry's lines.

**3. The bridge needs explaining out loud: implied sign flip, "Confirmed", and an unexplained 9,127.92.**
- **Where:** report.py:395-411; Summary leg-3 block.
- **What a CFO reads:**
  - "Result after the entries −45,572.30", "Owed to Mastercard 45,572.30", "Difference 0.00". Adding the two numbers gives −91,144.60. The rule that the difference is minus the result minus owed is nowhere on the page.
  - "Confirmed entries only": no entry is confirmed. All are proposed; that column is the 8 entries that need no evidence.
  - 9,127.92 has no words; the plan asked for "processor-only rows whose entry is conditional on evidence".
  - The block has no title. It sits under "Unreconciled 0.00" in a leg titled "bank and processor vs ledger".
  - The 928.31 is not owed on Mastercard's 30-Sep statement. It is September transactions Mastercard clears in October: a timing item between books and statement. Calling all 45,572.30 "owed to Mastercard" overstates what the supplier's statement says.
- **Fix:**
  - Title the block "Mastercard payable 2105 against Mastercard's own files".
  - Label "Result after the entries (credit) 45,572.30" and "Owed to Mastercard (credit) 45,572.30", so the difference is a plain subtraction.
  - Split owed into "30-Sep settlement, debited 1-Oct: 44,643.99" and "September transactions Mastercard cleared in October: 928.31", instead of file:line rows.
  - Name the columns "Entries with no condition (8)" and "All 9, if E10's evidence arrives".
  - Add one line: "9,127.92 = E10: 3 processor-only rows, entry waits for evidence."

**4. The Grouped view shows a settlement the bank never debited as paid.** It shows only in a planted run.
- **Where:** report.py:507: `if day == d.origin or d.type == bank_duplicate_debit: leg2[day]["bank"] += d.gross`. The not-debited exception's date is its settlement day, so its amount is added to the bank column.
- **Plant:** I deleted BS0024 (`plant3/`). The Summary correctly says "Days with no bank debit 1, 44,884.41". Grouped's 24-Sep row says bank 44,884.41, difference 0.00, 1 exception.
- **Failure scenario:** Someone plants a missing debit, and the Grouped view hides it.
- **Fix:**
  - Add the amount to the bank column only for a debit on no summary day, and for a duplicate. A not-debited day keeps bank 0.00.
  - Test with a planted deleted debit.

**5. Grouped leg 3: the 2105 row uses the opposite sign convention from the 1110 row.**
- **What the page shows:**
  - 1110: difference 400,000.00, reconciling items 400,000.00.
  - 2105: difference 116,160.96, reconciling items −116,160.96, and the items include the conditional E10.
- **Failure scenario:** reading down the column, one row reconciles and the other appears to double.
- **Fix:** sign the 2105 items so that difference minus items = 0 on both rows, or add an "Unreconciled" column (0.00 / 0.00). Say that the items include E10, or use the no-condition column with 9,127.92 left over.

### Minor

1. **Weekend stale authorisations show the wrong date** (recon.py:210-212). Five flags moved:
   - PX20000019 and PX20000020 (Sun 6-Sep → 08-Sep, since 7-Sep is a holiday);
   - PX20000016 (Sat 12-Sep → 14-Sep);
   - PX20000011 and PX20000023 (26 and 27-Sep → 28-Sep).

   The Detailed view's Date column shows 2026-09-08 while the expanded source row shows auth date 2026-09-06. Fix: keep the real date in `recon`, and map to the next working day only inside `_grouped`, where grouping is a display choice.
2. **No margin at 1440×900:** the Summary is 813/813 px. Opening the owed rows makes it 890 px, so it scrolls, and any longer sentence will too.
3. **T08 shows a different figure for the same entries:** "Lacks 9 proposed entries (151,379.59 USD)", total debits across all accounts. The bridge says −116,160.96 on 2105. Show the 2105 net in T08.
4. **T07 counts as blocked** with "Lacks 400,000.00 USD funding in transit…". The cash reconciliation closes to 0.00 with it as a reconciling item; a reconciling item to confirm is not a defect. Fine if Andrés says so; otherwise blocked tasks = 8.
5. **"131 data flags go back to their sender":** no draft exists for any of them, and 1 of the 131 is a missing invoice (a request, not a flag). Say "130 data flags for the processor; the processor invoice was not received."
6. **The 2105 ledger Summary figure is still in the data but not drawn** (template.html:460), and the bridge's ledger line repeats it. Remove it from the data, so the template does not filter by figure id.
7. **The leg-1 gross difference (14,884.40) is computed in the page script** and is untested. Put it in the overview data.
8. **Grouped leg 3 shows code-like names** ("bridge cash", "mc payable"). Use the account names.
9. **The processor's amount-and-rate draft still runs past 100 lines** (D05 on case data). It was noted last round; still accepted.

### Judgement calls, one by one

1. **Weekend stale authorisations moved to the next working day so leg-1 grouping has 21 days.**
   - exceptions.csv is unchanged: it has no date column, and these flags age 0, so I confirmed it byte-identical.
   - It is not fully honest on the page: the Date column and the filters show a day the authorisation did not happen.
   - Accept the goal, reject the place: the move belongs in `_grouped` (Minor 1).
2. **The tool-evidence and finding-wording tables added to policy.py** (`EVIDENCE_ENTRIES`, `FINDING_WORDS`). Accept. Each is declared once, and the T13/T08/T07/T12 sentences are correct.
3. **Leg-3 account rows carry all leg-3 exception ids.** Accept; it is disclosed on the page, and the type → account map was declined last round.
4. **Draft line format** (key, type, gross, day, other references). Accept. D02 names BS0016; drafts carry gross amounts and dates; routing by declared fixer was confirmed under the plant.
5. **"Data flags go back to their sender".** Accept the split between money and data flags; reword it (Minor 5).
6. **9 blocked tasks.** Accept as intended, with T07 questioned (Minor 4).
7. **Owed computed in close.py from the settlement pairing and the month cut-off rows.** Accept: no rule is duplicated, and the figure is correct. One edge: a debit posted a day late would count as unpaid and also as an unmatched debit; the pairing has the same edge in leg 2, so it is not new.
8. **The 2105 ledger Summary figure kept in the data but not drawn.** Reject; remove it (Minor 6).
9. **Unequal column widths so the Summary fits.** Accept; it fits, with no margin (Minor 2).
10. **The Grouped 2105 row: ledger against owed as a credit, difference 116,160.96 = the entries.** The arithmetic is right; the sign convention is wrong against 1110 (Material 5).
11. **Is the payable bridge correct accounting and readable for a CFO?**
    - **Accounting: yes.** It is books against the supplier's own files. After all proposed entries, 2105 equals Mastercard's unpaid 30-Sep settlement plus four September transactions Mastercard cleared in October, to the cent. With only the entries that need no evidence, the 9,127.92 left is exactly E10.
    - **Readability: not yet.** The page's own tie error, the implied sign flip, "Confirmed", the unexplained 9,127.92, and calling the 928.31 timing item "owed" (Materials 1–3).

### Throwaway files

All under a scratch folder:
- `s/indep2.py` — the payable recount from the raw files;
- `s/blob.py` — extracts the page's embedded data;
- `plant2/` — the two conversion errors;
- `plant3/` — the deleted BS0024 debit;
- `out/` and `old/` — the runs at cd9981d and 325f90d.
