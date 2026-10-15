# Fresh review of the extras round: itemised invoice, Treasury view, Mastercard-owned conversion error (a21a330..d2d3a79)

Brief B-2026-10-15-49. Fresh-context opus reviewer, read-only. I worked in my own clone at a scratch folder (checked out at d2d3a79), with a worktree at a21a330 in a scratch folder for the baseline run. Nothing was written in the repo, the records or the workspace.

**Verdict: the code is right and ready. The verifier is not ready, but the fix is small.**

- **Every plan sentence is implemented, and the real data ties.**
  - E05 is now five lines totalling 8,412.30, and each debit line cites its own invoice row.
  - There are 11 entries. E01–E04 and E06–E11 are identical to the a21a330 run.
  - `exceptions.csv`, `balances.csv`, `cash_recon.csv`, `checks.csv` and `close_tracker.csv` are byte-identical to the a21a330 run. Cash unreconciled is 0.00.
  - My own script, reading only the raw bank statement, reproduces every Treasury figure to the cent.
- **One thing stops sign-off: the tests don't pin what the session settled for Treasury.** The verifier was written before those points were decided, so it accepts several answers: duplicate counted or left out, population or sample deviation, and any positive number declared in `policy.py` as k. Nothing pinned them afterwards. I flipped all three settled points in a scratch copy and all 390 tests still passed, with the page showing average 45,908.07 and transfer 305,019.90 instead of 43,973.93 and 255,875.54. That matters more than usual here, because Treasury is exactly where a planted error would not fail.

### Closure checks

**(a) Verifier not weakened: yes.**

- **Suite:** 390/390 pass at d2d3a79, run from the clone.
- **The code commit never edits tests.** `git diff d495d57..d2d3a79 -- tests` is empty, and d2d3a79 touches only `bridge/`.
- **Every removed or changed assertion in d495d57 follows from the plan:**
  - `UsdConversionMastercard.test_no_entry` is deleted. The plan says "Supersedes the a030dcc reading … the tool proposes an entry". It is replaced by two tests:
    - `test_case_entries_unchanged`: the first 11 planted entries equal the case entries.
    - `test_one_adjustment_entry`: exactly one new entry, E12, Dr 1250 / Cr 2105 for 1,200.00, proposed, balanced, citing the Mastercard row.
    - Justified, and stronger than before on the new behaviour.
  - The Mastercard `USD_ACTION` sentence is replaced by the plan's quoted sentence, word for word. Justified.
  - `ROW_COUNTS` goes from 38 to 41 rows and E05 from 2 to 5 lines, with the same total, 172,291.89. Justified: E05 is itemised.
  - `OUTPUT_FILES` adds `treasury.csv`. Justified.
  - `assertIn(tab, page)` becomes `assertIn(tab, sorted(page))`. This changes nothing.
  - The processor-owned plant (`UsdConversionCorrected`) is untouched and still yields its E12.
- **The new Treasury tests are loose by design.** The commit message says "both readings accepted pending Andrés". That was reasonable when they were written, but the session has since settled the points. See Material 1.

**(b) Every plan sentence encoded and implemented**

| Plan sentence | Tests | Code |
|---|---|---|
| E05: one debit per line item, credit of the total to 2150, same id, still proposed only when the invoice is not accrued | `InvoiceItemised.test_lines_and_total`, `test_close_otherwise_unchanged` | close.py:123–138 ✓ |
| No cross-border sub-account in the chart: use 5100, name the line item in the title, say so | `test_title_names_the_cross_border_item`, `test_no_account_outside_policy` | title "(Cross-border assessment adjustment: variable cost, no sub-account in the chart, so on 5100)" ✓ |
| Each debit line cites its invoice row | `InvoiceLinesCiteTheirRow` (CSV level) | report.py:47–52 ✓ |
| Variable/fixed classification (2026-10-14 decision) | `test_debits_tagged_variable_or_fixed`, on the in-memory `line_tags` only | in memory only; not in any output (Minor 1) |
| "Still reversed in October" | not tested | not stated in any output, before or after this round (Minor 2) |
| Treasury: closing balance per calendar day equals the statement's running balance on days with movements | `test_one_row_per_september_day`, `test_daily_balance_is_the_running_balance`, `test_balance_cites_its_bank_line` | treasury.py:30–46 ✓ |
| Mastercard debits per day; average and deviation over September's business days; days of coverage each day; transfer = average × 5 + k × deviation × √5, k declared once and labelled illustrative | `TreasuryView`, `TreasuryTab`, which accept several readings (Material 1) | ✓ |
| `treasury.csv` with the stated columns; a Treasury tab whose summary shows closing balance, average, coverage at 30-Sep and transfer; nine files | `test_table_is_the_csv`, `test_tab`, `OUTPUT_FILES` | ✓. The summary also shows the deviation, which is harmless. `run.py` help and README still say "eight" (Minor 4). |
| Mastercard-owned USD error: proposed entry like the duplicate debit's, plus the plan's action sentence | `test_one_adjustment_entry`, `test_row` | close.py:155–158, policy.py:262 ✓ |
| Figures that must not move: 262 exception rows, cash 0.00, every account's before balance | existing golden tests | byte-identical to a21a330 ✓ |

**(c) Real data**

- Suite green. Cash unreconciled 0.00.
- 11 distinct entries, E01–E11. E05 has five lines: 3,250.00, 2,000.00, 1,862.30 and 1,300.00 to 5100, and 8,412.30 credited to 2150.
- Nine files written.
- E01–E04 and E06–E11 are identical to the a21a330 run. Only E05 differs.
- `exceptions.csv` and the other four CSVs are byte-identical to the a21a330 run.
- **Treasury, recomputed by a throwaway script from `bridge_account_statement.csv` alone** (settlement narratives, BS0018 removed):
  - 21 debit days, total 923,452.51.
  - Closing balance 1,147,965.55.
  - Average 43,973.93.
  - Sample standard deviation 8,051.16.
  - Days of coverage 26.11.
  - Transfer 255,875.54.
  - All 30 daily balances and all 30 daily Mastercard debit figures match `treasury.csv`.
  - With the duplicate counted, the average would be 45,908.07.

**(d) Judgement calls:** judged one by one in the section below.

**(e) Code standards: met.**

- k, the five-day horizon, the variable line items and the cost tags are each declared once in `policy.py`.
- The duplicate rule is not restated: Treasury reads the reconciliation's duplicate-debit type.
- The settlement kind comes from `policy.KIND`, and the business-day rule is reused from `recon.is_working_day`.
- No needless new structure, with one small exception: `line_tags` (pre-existing and unused at a21a330) is now filled but read only by a test (Minor 1).
- Comment density matches the surrounding code.

### Material

**1. The settled Treasury readings are not pinned. Three of them can be reversed with the suite still green.**

- **Where:**
  - `tests/test_golden.py`: `TREASURY_READINGS`, `_treasury_reading`, `_treasury_averages` and `TreasuryView.test_mastercard_debits_per_day` / `test_days_of_coverage` accept "duplicate counted" or "left out".
  - `tests/test_page.py`, `TreasuryTab.test_suggested_transfer`: accepts both deviations, and any positive number in `policy.py` not on the pre-Treasury list as k. That includes `TREASURY_HORIZON_WD = 5`.
- **Shown, not argued.** In a scratch copy (a scratch folder) I made three changes:
  - put BS0018 back into the debits;
  - switched to the population deviation;
  - set `TREASURY_BUFFER_K = 3`.

  Result: 390/390 still pass, and the page shows average 45,908.07, deviation 11,251.83, coverage 25.01 and transfer 305,019.90.
- **Failure scenario:** any later round, for example the five-screen restructuring that touches report.py and treasury.py, silently changes the headline Treasury figures, and the suite stays green. 
- **Fix:** a test-only commit that narrows the readings to the settled ones:
  - drop the "duplicate counted" reading and the population deviation;
  - pin `policy.TREASURY_BUFFER_K == 2`;
  - assert the summary carries exactly 1,147,965.55, 43,973.93, 8,051.16, 26.11 and 255,875.54;
  - assert 21-Sep's `mc_debits` is 41,402.03.

  These numbers come from my throwaway script, not from the code. Delete the "pending Andrés" comment. No code change is needed; the code already produces these values.

### Minor

1. **The variable/fixed classification exists only in memory.**
   - `Entry.line_tags` (close.py:23, 136–137) is read only by `test_debits_tagged_variable_or_fixed`. No CSV or page shows it.
   - A reader of `proposed_entries.csv` learns that the cross-border line is variable (from the title), but nowhere that the other three are fixed, which is what spec E8 asks for: "with the variable/fixed classification".
   - Cheapest fix: complete the title, e.g. "… (Cross-border assessment adjustment: variable cost …; the other line items: fixed programme cost)". Alternatively, surface the tag on the page when the screens are rebuilt.
2. **"Still reversed in October" is not said anywhere.** The plan says "still", but no output states the reversal, at a21a330 or now. The misdated and late-posting entries name their October reversal in the title; E05 doesn't. Add "reverse on 1-Oct" to the E05 title. This is not a regression.
3. **The Treasury lead sentence says "From the bank statement alone"** (report.py:214), yet the duplicate exclusion comes from the reconciliation. Reword: "From the bank statement, less the duplicate debit the reconciliation found (BS0018)."
4. **Stale "eight files"** in `run.py:18` (help text) and `README.md:19`. `run.py` was inside the implementer's allowed scope. These are one-word fixes.
5. **k shows as "2.00"** in the lead ("2.00 standard deviations … the 2.00 is illustrative"), because `text()` formats it as money. Write `"%s" % policy.TREASURY_BUFFER_K`, or format it as an integer.
6. **Untested direction of the Mastercard-owned adjustment.**
   - I planted −1,200 (Mastercard understates). Result: E12 Dr 2105 / Cr 1250 1,200.00. On the plant, 1250 ends at 39,416.94: the E03 duplicate claim (40,616.94) netted against the 1,200 owed to Mastercard, in one account named "receivable".
   - The plan allows "(or payable to)", and the chart has no separate account, so this is acceptable. But the title doesn't say the direction, and no test covers it.
   - Fix: say "receivable from" or "payable to" in the title by sign, and add the mirror plant to the tests.
7. **Treasury edges that don't occur in the case data:**
   - A September day before the statement's first line gets no row: one row per calendar day is no longer guaranteed, and no opening balance is derived.
   - A Mastercard debit on a weekend or holiday appears in the daily column but drops out of the average and deviation.
   - Neither happens in the data. Worth one sentence in the production note, not code now.

### Judgement calls, one by one

**The session's four settled points**

1. **Average excludes the duplicate BS0018.** Agree. Mastercard confirmed the refund (ticket MCS-88213), so counting it would overstate normal outflows. It reproduces the decision log's 43,973.93. Not pinned by tests (Material 1).
2. **Sample standard deviation.** Agree. 21 days are a sample of an ongoing process. It reproduces the decision log's 8,051. Not pinned (Material 1).
3. **k = 2, illustrative.** Agree. Declared once (policy.py:269), and labelled illustrative in both the lead and the summary label. Formatting nit (Minor 5).
4. **Days of coverage to 2 decimals.** Agree. The implementation rounds each day's figure half-up to the cent (26.11 at 30-Sep).

**The verifier's open readings**

The verifier's list of 8 ambiguities is not on disk; I judged the ones visible in the tests. The two readings left open — the duplicate in the average, and population versus sample deviation — are settled above (points 1 and 2), and the loose k is in Material 1.

**The implementer's calls**

5. **BS0018 also dropped from the daily `mc_debits` column.** Accept, and say so.
   - Benefit: the column and the average agree. The business-day column sums to 923,452.51, and 923,452.51 / 21 = 43,973.93, so a reader can recompute the average from the table.
   - Cost: on 21-Sep the column (41,402.03) no longer explains the balance movement, and BS0018 is cited nowhere in `treasury.csv`.
   - Fix: extend the lead's sentence to "left out of the average and the daily column", or cite BS0018 in 21-Sep's `src`.
6. **Treasury reads the duplicate keys from the reconciliation.** Agree. Re-detecting duplicates inside treasury.py would be a second copy of the duplicate rule. Only the lead's wording is off (Minor 3).
7. **Average over business days only.** Agree. That is the plan's wording, and with Sep 7 a holiday it gives 21 days, each with exactly one Mastercard debit. Edge case in Minor 7.
8. **Sign handling of the Mastercard-owned adjustment.** Agree for the overstated case: Dr 1250 / Cr 2105 mirrors the duplicate debit's entry and clears the payable residual. The understated case is defensible but untested and netted (Minor 6).
9. **`run.py` help text still says "eight output files".** Reject. It was in scope and is a one-word fix (Minor 4).

### Throwaway files

Throwaway scripts and scratch copies were used for these runs; none is included.
- Under- and over-conversion plants: a throwaway script, with data in a scratch folder and a scratch folder
