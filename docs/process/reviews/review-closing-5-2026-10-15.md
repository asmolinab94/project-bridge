# Closing review 5: freeze fixes, Data quality table, Reconciliation by type

This review covers the brief for this round (B-2026-10-15-70). I checked the repo read-only at fa91da8 on `feat/project-bridge`. The working tree is clean and nothing in the repo was written. My scratch files are in a scratch folder: the run is in `out/`, the page data is in `data.json`, and the independent recounts are `bytype.py` and `rest.py`. Neither script imports `bridge`. I also put a 1440x813 frame page in `out/frame.html` to measure with. The local server on port 8781 is stopped and the Chrome tab is closed.

**Verdict: FREEZE AFTER FIXES.**

All five page problems from the last review are fixed, and every figure I recomputed matches. The suite runs 521 tests, all green. `proposed_entries.csv` is unchanged.

One new problem blocks the freeze. Hiding the 131 data flags by default broke the rule the demo sells, that "a figure opens the rows that make it up". On the Summary:
- Leg 1 "Exceptions 255" opens 125 rows.
- Leg 1 "Waiting outside Clara 251" opens 121 rows.
- Leg 3 "Waiting outside Clara 1" opens **0 rows**.

This is the same kind of mismatch Andrés reported on Data quality earlier today. The second fix is a cheap wording change on the Pending actions headline.

## Closure checks

**(a) The material findings of review 4: all five fixed.**

1. **Leg-1 bars now show what they add up to. Fixed.** I clicked all six type bars in Chrome. Each one opens Reconciliation with a "Gross USD" column added before Net, and the footer sums that column:

   | Bar | Rows | Gross footer | Net footer |
   |---|---|---|---|
   | Duplicate in processor | 6 | 3,640.35 | 3,593.63 |
   | Sign flipped | 4 | 2,540.18 | 2,502.45 |
   | Amount differs | 8 | 747.93 | 737.29 |
   | FX rate differs | 95 | 762.72 | 751.93 |
   | Only in processor | 3 | 9,259.40 | 9,127.92 |
   | Only in Mastercard | 5 | −2,066.18 | −2,041.36 |

   - The sentence above the table gives both signs, for example: "Gross of these rows, processor minus Mastercard: -2,066.18 USD. Walking from the processor to Mastercard, the step is +2,066.18."
   - Changing any filter drops the extra column and the sentence (`template.html:303,310`).
   - The Processor and Mastercard total bars open Grouped leg 1.

2. **The Summary fits. Fixed.** In a 1440x813 frame the page is 757 px tall, the footer ends at 745 px, and nothing overflows sideways.
   - The "Leg 1 difference by type" table is gone.
   - "How much is explained" now sits under the leg 2 card.

3. **Printing keeps the task names. Fixed in the print rule** (`button:not(.link)`). I applied the page's print rules on screen: Pending actions still shows "▸ T07 Reconcile bridge account cash…", and source references stay visible. I did not run a real print preview.

4. **The headline is split. Fixed:** "Resolves USD 567,345.29 — 167,345.29 errors to correct · 400,000.00 funding in transit (clears 01-Oct)".
   - T07 carries a "Timing difference" tag.
   - T08 and T13 show "116,160.96 Cr — on 2105, outside the total", and one line says so once.
   - The wording problem is Material 2.

5. **README month paragraph. Fixed.** It now:
   - names `CUTOFF_DATE`;
   - says another month needs the September/October wording reviewed and that the month is "declared, not fully parametrised";
   - explains how to open a terminal in a folder on macOS and Windows;
   - says the Mac developer-tools prompt is fine to accept.

The minors from review 4 are also done:
- The screen list now comes from the page data (`template.html:279`).
- The settlement-days explanation says "31-Aug to 30-Sep".
- Close mentions `proposed_journal_lines.csv`.
- T02, T06 and T05 are pinned by tests.

**(b) The tests were not weakened.** Comparing 0e12c26 with HEAD, I went through every removed or changed assertion.

- **Five screens in order** (e980cf0): the order is now checked on the page data instead of a list in the script. A new test fails if any list of three or more screen names appears in the script. Required by the plan; not weaker.
- **"Not pinned" docstring** (e980cf0): replaced by real assertions on T02, T06 and T05. Stronger.
- **Type column first** (fe6a631, `test_page.py`): the plan says "the table's first column is the type". Required, and the "notes columns last" check is kept.
- **Per-day leg-1 figures and 21 grouped days retired** (fe6a631): required, because the plan moved Grouped leg 1 from "by day" to "by type".
  - The replacement is stronger: every type row (pair count, processor USD, Mastercard USD) is recomputed from the raw files, and the columns must sum to both month totals.
  - Kept: the column totals, each row's difference, "a group with a difference has exceptions", and "row ids equal the exception count".
- **Weekend stale authorisations** (fe6a631, `test_screens.py:1368`): the test now only checks that those rows sit in the stale-authorisation row. That is close to automatic once grouping is by type. Still acceptable: the behaviour it used to pin (moving them to the next working day) no longer exists.
- **Two gaps**, neither a weakening:
  - Nothing checks that a Summary figure's count equals the rows the Detailed view shows by default. That is how Material 1 got through.
  - The type-then-amount sort is checked only by a pattern match on the script.
- **One inconsistency:** the plan text still says "2 days · 156 rows" (`plan.md:834`). The test pins 155 and explains why: the 156th row was the close-checklist row the check cites for its task. The page shows 155. The plan should be corrected.

**(c) Figures recomputed without importing `bridge`.**

- **Grouped leg 1 by type** (`bytype.py`) matches the page row for row:

  | Group | Rows | Processor USD | Mastercard USD |
  |---|---|---|---|
  | Matched, no difference | 2,997 | 881,142.94 | 881,142.94 |
  | Duplicate in processor | 6 | 3,640.35 | 0 |
  | Sign flipped | 4 | 1,270.09 | −1,270.09 |
  | Amount differs | 8 | 6,926.00 | 6,178.07 |
  | FX rate differs | 95 | 21,123.34 | 20,360.62 |
  | Month cut-off | 4 | 941.33 | 941.33 |
  | Only in processor | 3 | 9,259.40 | 0 |
  | Only in Mastercard | 5 | 0 | 2,066.18 |
  | **Total** | | **924,303.45** | **909,419.05** |

  The difference is 14,884.40, the same as on screen.
- **The headline split.** The exceptions on tasks net 567,345.29: T07 400,000.00 + T02 90,215.88 + T06 40,616.94 + T05 15,600.17 + T09 12,500.00 + T11 8,412.30. Taking out T07 leaves 167,345.29. By exception class, timing is 458,759.78 and real error is 108,585.51.
- **Data quality counts match what each check opens:**
  - clearing days vs entries: "2 days · 155 rows" (151 processor rows of 24-Sep and 4 ledger lines of the 30-Sep entry posted 1-Oct);
  - stale authorisations: 22 rows;
  - impossible dates: 3 rows;
  - references: 105 rows;
  - statuses (passes): 45 rows, and its source opens 45;
  - the six checks with no rows of their own show "passes" or "fails" only.

  The flagged table has 285 rows. Four processor rows appear under two checks.
- **Hidden data flags: 131** = 105 bad references + 22 stale authorisations + 3 authorised after clearing (all leg 1) + 1 missing processor invoice (leg 3). The page shows "Showing 131 of 262 rows".
- **`proposed_entries.csv`** sha256 is still 315ec8d5b4625c84f4a760da3165591c4eef7931fe6c3d6017fe9ccd0adc2a60.

**(d) The session's calls, one by one.**

1. **The timing part of the headline is the 400,000.00 funding in transit, not every timing-class exception (458,759.78). Accept the number; fix the label.** The code's rule is principled: timing is what belongs to a task that needs nothing from Clara (`report.py:389-394`), and only T07 qualifies.

   But the other 167,345.29 is called "errors to correct", and 58,759.78 of it is what Reconciliation itself calls "Timing difference":
   - the misdated entry, 45,331.47;
   - the suspense receipt, 12,500.00 (T09);
   - the cut-off, 928.31 (inside T05).

   A CFO comparing screens sees T09's 12,500 as an "error" here and as "Timing difference" one screen earlier. → Material 2.

2. **131 hidden data flags, including the missing invoice. Reject that one row.**
   - The control says "no money", but a processor invoice that never arrived is an unaccrued cost of unknown size. It is the reason T12 exists, not something with no money.
   - Hiding it is also what makes leg 3 "Waiting outside Clara 1" open zero rows (Material 1).
   - Hide the 130 processor flags and keep the missing invoice visible.
   - The plan was moved from 130 to 131 in fa91da8, but the decision log still records Andrés's request as "the 130 zero-money data flags". Either revert to 130 or log why it changed.

3. **Data-flag rows at 0.00 in Grouped leg 1. Accept.** Their amounts already sit in the matched or difference rows, so counting them again would break the column totals. They are greyed, listed last, and explained in a note under the table. Clicking one still opens its rows.

**(e) The page as a CFO demo, in Chrome.**

- **Setup.** I served the output folder on 127.0.0.1 and measured inside a 1440x813 frame. The window itself stayed at 3008 px wide.
- **Summary:** fits, as in (a).
- **Leg-1 bar clicks:** all six tie, as in (a).
- **Data quality:**
  - Thirteen check lines, each with its count and unit.
  - Clicking a failed check filters the table below and scrolls to it; the "Check" dropdown filters too.
  - The footer says "Rows shown: 155 of 285" and sums the amounts (45,488.83 for clearing days).
  - "Copy rows shown" and "Download CSV" each produced 155 data rows plus a header, so both act on the rows shown.
  - Row text is selectable.
- **Reconciliation, Detailed:**
  - The type is the first column.
  - Rows are ordered by type (in the summary's order), then by absolute amount.
  - Each type has a header row such as "▾ Duplicate in processor · leg 1 · 6 rows · net 3,593.63 USD". It collapses on click (6 rows hidden, arrow flips) and opens again.
  - The summary on top shows all 21 lines with no inner scroll.
  - The data flags are hidden by default, and "Show the 131 data flags — no money; also in Data quality" reveals them (262 of 262), then "Hide the data flags" hides them again.
  - At 1440 px, Assigned person, Status and Comment are all on screen; the Comment column ends at 1415 px.
  - Copy and CSV act on the rows shown (131 rows each).
- **Reconciliation, Grouped:**
  - Leg 1 is by type, as in the table in (c).
  - Leg 2 is by settlement day: 22 days, 968,096.50 against 1,008,713.44, with 17-Sep showing the 40,616.94 duplicate.
  - Leg 3 is by account, with the payable bridge.
  - Clicking "FX rate differs" opens its 95 rows in Detailed.
- **Pending actions:** order, tags and Cr amounts are as in (a) item 4.
- **"i" boxes:** there are 56 on the Summary. I checked one by real mouse click: it opens, stays inside the frame, and reads cleanly.
- **Console errors:** none on a clean reload while switching all five screens, clicking every bar and summary line, toggling flags and headers, expanding every task, and switching every Close tab.
  - One "Maximum call stack" error appeared in an earlier run where I had overridden the browser's clipboard and copy functions to capture output. It did not recur without my overrides, so I attribute it to my test harness, not the page.
- **Not checked:**
  - a real print preview;
  - a phone;
  - opening the file by double-click;
  - whether the clipboard really receives the text (I captured it in place of the clipboard);
  - a fresh install on a clean Mac or on Windows;
  - every "i" box by real click (I clicked one).

## Material findings, ranked

**1. Hiding the data flags breaks "a figure opens its rows" on the Summary.**

- **Where:** `bridge/template.html:886-889`. The filter hides flag rows whenever the incoming filter does not name a type, a class or row ids. A filter by leg alone, or by leg plus "who fixes" or "escalates", still hides them. The incoming filter is applied at `template.html:1054`.
- **What a CFO sees:**

  | Summary figure | Says | Opens |
  |---|---|---|
  | Leg 1, Exceptions (net) | 255 | 125 rows |
  | Leg 1, Waiting outside Clara | 251 | 121 rows |
  | Leg 1, "How much is explained" difference 15,600.17 | — | 125 rows |
  | Leg 3, Exceptions (net) | 6 | 5 rows |
  | Leg 3, Waiting outside Clara | 1 | **0 rows** |

  The button next to the count always says "Show the 131 data flags" (`template.html:970`), even when 130 or 1 rows are hidden.
- **Why it matters:** it is the exact complaint Andrés made about Data quality ("the counter says 2 but opening it shows a lot of transactions"), moved to the Summary. The money still ties because flags are 0.00, but the counts do not.
- **Fix, in two parts:**
  - When Reconciliation is opened from another screen, show the flags. Hide them only on the bare, unfiltered Detailed view: set the "show flags" switch to on inside `apply` at line 1054, and reset it in "Clear filters".
  - Take the missing processor invoice out of the hidden group (`report.py:795-797`, filter on type as well as class). That gives 130 hidden flags, matching the decision log, and makes "no money" true.

  Make the button state the number actually hidden under the current filter.
- **Missing test:** "every Summary figure that links to the exceptions table states a count equal to the rows that link keeps under the default hiding rule". It can be computed from the page data in Python, the same way the Data quality test is.

**2. "Errors to correct" puts 58,759.78 of timing items under "errors".**

- **Where:** `bridge/template.html:1086`; the split is computed at `report.py:419`.
- **What a CFO sees:** "167,345.29 errors to correct" on Pending actions. On Reconciliation and in the Summary's "How much is explained", the misdated entry (45,331.47), the suspense receipt (12,500.00) and the cut-off (928.31) are labelled "Timing difference". The Summary's leg-3 Timing column says 457,831.47, while the headline says timing is 400,000.00. The same item is classed differently on two screens.
- **Fix:** keep the numbers and change the label to "167,345.29 needs action by Clara" (or "to correct or confirm"). The 400,000.00 can stay "funding in transit (clears 01-Oct)". The plan's own wording ("errors to correct") needs the same one-word change, so this is a decision for Andrés to confirm.

## Minors

1. **The plan says "2 days · 156 rows"** (`plan.md:834`); the test and the page say 155. Correct the plan text.
2. **The Data quality "All" footer adds unlike things.** Its 86,804.90 mixes processor USD with ledger lines and counts the 4 rows flagged by two checks twice (482.73). Show the sum only when one check is selected, or label it.
3. **Reconciliation's "Copy rows shown" doesn't copy what is on screen** (`template.html:866`):
   - it puts the date before the type, while the screen shows the type first;
   - it copies internal keys ("processor_duplicate") instead of the labels shown;
   - it leaves out the notes columns, which the CSV includes.
4. **Detailed orders the types differently from the waterfall:** Amount differs comes before Sign flipped, while the waterfall and Grouped show Sign flipped first. Use one order.
5. **Small number formatting:** the step sentence uses a hyphen "-3,640.35" while the waterfall uses a minus sign "−3,640.35".
6. **The Grouped leg-1 footer says "Sum of rows shown: 11"**, counting groups, not pairs.
7. **A search while flags are hidden silently skips flag rows.** For example, a transaction id that has only a bad reference returns nothing. Material 1's fix covers this if search also turns the flags on.
8. **"Missing inputs" shows "Fails" with "no source"**, which is correct by the plan. Its detail text should name the processor invoice so the line stands on its own.

## Hand checks left for the owner, after the fixes

- On the Summary, click leg 1 "Exceptions 255" and leg 3 "Waiting outside Clara 1". Each should open exactly that many rows.
- On Pending actions, read the headline split against Reconciliation's Timing column and confirm the new label.
- Do a real print preview (Cmd+P) of Pending actions: task names present.
- Paste "Copy rows shown" into a spreadsheet once, to confirm the columns land.
