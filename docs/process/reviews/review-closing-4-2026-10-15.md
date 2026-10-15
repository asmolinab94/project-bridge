# Closing review 4: the last round before freezing (dee2151..0e12c26)

Brief B-2026-10-15-68 asked for a fresh-context, read-only review. I worked in the repo at 0e12c26 on `feat/project-bridge`. Nothing in the repo was written and the working tree is clean. My runs and scratch scripts are in a scratch folder: the output is in `out/`, the extracted page data is `data.json`, and the independent recounts are `leg1.py` and `rest.py`. None of the scripts imports `bridge`. The Chrome tab is closed and the local server on port 8776 is stopped.

**Verdict: FREEZE AFTER FIXES.**

- **The data side is right.** Every figure I recomputed from the raw files matches:
  - all three waterfalls;
  - each task's "Resolves USD";
  - the top total;
  - the ERP file, line for line.
- `proposed_entries.csv` is unchanged: its sha256 is still 315ec8d5…, and the suite is 507/507 green.
- **What blocks the freeze is on the page:**
  - The leg-1 waterfall steps open rows that the reader cannot add up to the step.
  - The Summary no longer fits a 1440x900 window.
  - Printing drops the task names on Pending actions.
- Two more are worth fixing before Clara sees it: the headline "Resolves USD 567,345.29" is 70% a transfer in transit, and the README overclaims how to change the month.
- After the fixes, the only re-check needed is by hand: one leg-1 click, the Summary height, and a print preview of Pending actions.

## Closure checks

**(a) Verifier not weakened: yes, with one gap it cannot see.**

- Comparing 97b0051 with HEAD, no old assertion was removed. The only deleted lines in the tests are a docstring sentence and the three amended lines below.
- **The list of output files.** The list grows to ten, and a new assertion pins `len == 10`. This is exactly what the plan says.
- **The exemption from the source column for the ERP file.** It is narrow. Only the exact message "`<out>/proposed_journal_lines.csv: no src column`" is filtered, so any other violation in any file still fails. The evidence chain is kept by the new ERP-file tests, which pin every ERP line to the `proposed_entries.csv` line in the same position, and that line carries its source.
- **The `isinstance` skip in 3334735** (the older test that checks no label says "unexplained"). It skips page entries that are not dicts. On this data those are `page.screens` (a list) and `page.period` (a string). Neither carries summary labels, so nothing that should be checked escapes.
- **The gap.** The test that every waterfall bar opens rows summing to it reads the `gross` column of the page data. The Reconciliation table does not show that column; it shows Net USD. So the test is green while the screen does not tie (Material 1). The page script still cannot run in the suite, so what is on screen needs a hand check.
- **The clarification in b9eef94 is not pinned by any test.** The tests were written before it, and the impact-per-task test says outright that X is not pinned for a task with both exceptions and entries. Nothing fixes T02 at 90,215.88, T06 at 40,616.94 or T05 at 15,600.17 (Minor 7).

**(b) Figures recomputed independently.**

**Leg 1 (`leg1.py`).** The match runs on cleared processor rows, with network references reduced to letters and digits. Rows with a blank reference are matched by card, clearing date and currency.

- Processor: 3,117 rows, 924,303.45.
- Mastercard: 3,113 rows, 909,419.05.

| Type | Rows | Gross (processor minus Mastercard) | Bar |
|---|---|---|---|
| Duplicate in processor | 6 | 3,640.35 | −3,640.35 |
| Sign flipped | 4 | 2,540.18 | −2,540.18 |
| Amount differs | 8 | 747.93 | −747.93 |
| FX rate differs | 95 | 762.72 | −762.72 |
| Month cut-off | 4 | 0 | 0.00 |
| Only in processor | 3 | 9,259.40 | −9,259.40 |
| Only in Mastercard | 5 | −2,066.18 | +2,066.18 |

- The steps land on 909,419.05 exactly.
- Every bar equals the page's figure.

**Leg 2.**

- Mastercard's daily summary from 31-Aug to 30-Sep: 968,096.50.
- Bank settlement debits posted through 1-Oct: 23 rows, 1,008,713.44.
- The difference is 40,616.94: BS0016 and BS0018 carry the same reference, BNK324320124.
- 968,096.50 + 40,616.94 = 1,008,713.44. Ties.

**Payable 2105.**

- Opening balance −71,243.18, plus the September ledger lines, gives 70,588.66 debit.
- Proposed entries on 2105:

  | Entry | 2105 net |
  |---|---|
  | E01 | −44,884.41 |
  | E02 | −45,331.47 |
  | E03 | −40,616.94 |
  | E06 | +751.93 |
  | E07 | +2,502.45 |
  | E08 | +737.29 |
  | E09 | +3,593.63 |
  | E10 | +9,127.92 |
  | E11 | −2,041.36 |

- All entries net −116,160.96. Without E10, −125,288.88.
- After all entries the payable is −45,572.30. Adding 44,643.99 (the 30-Sep settlement) and 928.31 (the 4 timing rows) gives **0.00**.
- The page's waterfall is 70,588.66 − 125,288.88 + 9,127.92 + 44,643.99 + 928.31 = 0.00. Ties.

**Resolves USD per task.** I recomputed it from the checklist lines cited in each `exceptions.csv` row's source. The exception nets match the page exactly:

| Task | Leg | Net |
|---|---|---|
| T07 | 3 | 400,000.00 |
| T02 | 3 | 90,215.88 |
| T06 | 2 | 40,616.94 |
| T05 | 1 | 15,600.17 |
| T09 | 3 | 12,500.00 |
| T11 | 3 | 8,412.30 |
| T12 | 3 | 0.00 |

- On this data, no exception is linked to two tasks. So the "count each once" rule is computed but never exercised.
- **The top total** is 262 exceptions, each counted once: **567,345.29**. It matches.

**ERP file.**

- The header equals `gl_journal_lines.csv`'s.
- It has 41 lines, the same as `proposed_entries.csv`.
- On every line:
  - je_id = `PROPOSED-` + entry id;
  - posting date 2026-09-30;
  - source `PROPOSED_NOT_APPROVED`;
  - account name from the opening balances;
  - description = the entry title;
  - reference holds the approval level and the status.
- Debit and credit are text-identical to `proposed_entries.csv`, and every entry balances.
- E02's title already says it reverses in October, which meets the plan's "says so in description".

**(c) Judgement calls, one by one.**

1. **The clarification in b9eef94** (a task whose entries correct its own exceptions shows the exceptions' net once). **Right.** Read as a sum, T02 and T06 would resolve 0.00, and that contradicts the plan's own rule for the top total.
   - The code applies a broader rule than the sentence: any task with exceptions shows their net (`report.py:355-363`). T05 falls under it, even though its exceptions are on leg 1 and its entries move 2105 by +14,671.86. That outcome is fine, but the sentence names only T02 and T06.
   - Two small fixes: name T05 in the decision log, and pin the three figures (Minor 7).
   - The sentence about the 0.00 cut-off bar was added inside the impact bullet. It is misplaced but harmless.
2. **One payable waterfall on the all-entries basis, with E10 as a dashed bar.** **Accept.**
   - The confirmed basis is still readable on the same screen:
     - the dashed E10 bar (+9,127.92);
     - its "i" text: "Until it arrives, this amount is the payable's difference";
     - the bridge table right below, which shows both bases.
   - Two waterfalls would cost height the Summary no longer has.
3. **Leg-1 bars as the negative of their rows' gross.** **The arithmetic is right; on screen it fails** (Material 1). Simplest alternative: walk from Mastercard to the processor, so each step equals its rows' gross with the same sign. That needs a one-line plan amendment. Keeping the current direction is the other fix.
4. **The 0.00 cut-off bar.** **Accept.**
   - It shows 0.00 with "4 rows in both totals; owed as timing on 2105".
   - Its "i" text explains why.
   - It opens nothing, which the plan clarification allows.
5. **README says 13 files while the tool reads 11.** **Accept.** It names all 13, says the tool reads the first eleven, and says the last two are reference documents that may stay in the folder. That is clearer than saying "11".
6. **The screen list in two places**: `policy.py:411` (`SCREENS`) and `template.html:273` (a hard-coded `var SCREENS`). **A duplication under your same-rule-once standard.** The page copy predates this round. The new copy in `policy.py` made it a second statement of the same list, and the page already receives `page.screens`. Fix: `var SCREENS = PAGE.screens.map(function (s) { return s.name; });` (Minor 1).
7. **Shortened Summary labels.** **Accept.**
   - The changes: "Bridge account 1110, ledger" → "Ledger 1110"; "Bank statement balance" → "Bank statement"; "Waiting on Mastercard or the processor" → "Waiting outside Clara".
   - Each has an "i" text that restores the meaning. They read cleanly at 1440 px.

**(d) The page as a CFO demo, in Chrome.**

- **Setup.** I served the output folder over http on 127.0.0.1. The window would not shrink (the viewport stayed at 3008x1604 CSS px). So I measured inside a 1440x813 frame: what a 1440x900 window leaves for the page, the same viewport the last review used.
- **Summary fit: fails.** The content is 895 px tall, so it scrolls 82 px (it was 789 px last round). Below the fold: the bottom of "How much is explained", its sentence, and the footer. Nothing overflows sideways. → Material 2.
- **Waterfalls: readable.**
  - Dark totals; red for errors; blue for proposed entries; dashed outline for E10; grey for owed amounts; a green end.
  - Signed amounts, right-aligned.
  - A green line under each waterfall saying it ties.
- **Every bar clicked:**

  | Bar | What it opens | Ties? |
  |---|---|---|
  | Leg-1 type bars | the exceptions table | No: it shows net, and the sentence's sign contradicts the bar (Material 1) |
  | Leg-1, leg-2 and payable totals | their grouped view or table | Yes |
  | Duplicate bank debit 40,616.94 | its row | Yes |
  | Proposed entries −125,288.88 | Close, with "The lines in proposed entries add up to -125,288.88 USD." | Yes |
  | E10 | its 3 rows, 9,127.92 | Yes |
  | Settlement 44,643.99 | one row (`mastercard_daily_settlement_summary.csv:23`), listed below the Summary | Yes |
  | Timing 928.31 | four rows, listed below the Summary | Yes |
  | Month cut-off and final difference (0.00) | nothing, by design | — |

  Detail for the leg-1 type bars, step and rows' net:

  | Step | Rows' net |
  |---|---|
  | −3,640.35 | 3,593.63 |
  | −2,540.18 | 2,502.45 |
  | −747.93 | 737.29 |
  | −762.72 | 751.93 |
  | −9,259.40 | 9,127.92 |
  | +2,066.18 | −2,041.36 |

- **The "i" boxes work.**
  - There are 56 on the Summary.
  - Each opens on click and closes on a click outside, on Escape, and on a second click of the same button.
  - None runs off screen.
  - An "i" inside a clickable waterfall row opens its box without following the row.
  - The texts are plain and correct, with one wording slip (Minor 6).
- **Pending actions.**
  - "Resolves USD" is in its own column with the leg it comes from.
  - Order is open first, then by money: T07 400,000.00, T08 and T13 −116,160.96, T02 90,215.88, T06 40,616.94, T05 15,600.17, T09 12,500.00, T11 8,412.30, then the zeros; done tasks last.
  - The headline is 567,345.29 (Material 3).
- **Console errors:** none. I caught errors in the page frame while switching all five screens, expanding all 26 tasks and clicking every bar.
- **Visual hierarchy: no longer flat.** Cards, one accent colour, red only for what is wrong, green for what ties, tabular figures, and generous spacing on Pending actions.
- **Not checked:**
  - **A real print preview.** I only applied the print rule's effect to the page and read what disappears (Material 4).
  - **A phone.**
  - **Opening the file with a double-click** (`file://`). I served it over http.
  - **An install from scratch** on a clean Mac or on Windows.

**(e) README.**

- **All ten output files are named**, each with one line saying what it is. The README also says the ERP file has no source column and why.
- **Install and run**, for a finance reader:
  - It names Python 3.9 or later and the python.org installers.
  - It names the "Add python.exe to PATH" tick-box on Windows, and `py` instead of `python3`.
  - It gives the one command, says where the page appears, and says to double-click it.
- **Two gaps** for someone who has never used a terminal (Minor 5):
  - It says "open a terminal in this folder" without saying how.
  - On a Mac without developer tools, `python3 --version` opens an install prompt for Apple's developer tools instead of printing a version.
- **The month paragraph is wrong** (Material 5).

## Material findings, ranked

**1. The leg-1 waterfall steps open rows that do not add up, on screen, to the step.**

- **Where:**
  - `bridge/template.html:765`: the Reconciliation columns (`EX_COLS`) have `net` and no `gross`.
  - `bridge/template.html:896-898`: the sentence shown after the click.
- **What a CFO sees.** They click "Only in Mastercard +2,066.18". The Reconciliation table opens with five rows. The only amount column is Net USD, and its footer says "Sum of rows shown: 5 −2,041.36". Above it, the sentence says the gross of these rows is −2,066.18 USD, "the size of the step", but the step on the Summary read **+**2,066.18.
- **The other five type bars behave the same:**
  - Duplicate in processor: −3,640.35 opens 3,593.63.
  - Sign flipped: −2,540.18 opens 2,502.45.
  - Amount differs: −747.93 opens 737.29.
  - FX rate differs: −762.72 opens 751.93.
  - Only in processor: −9,259.40 opens 9,127.92.
- **Why it matters.** The plan says "every bar opens the rows that sum to it", and "every figure opens its rows" is what the demo sells. The test is green because it sums a column the page hides.
- **Fix, in two parts:**
  - When the table is opened from a waterfall step, add the `gross` column and sum it in the footer. The page data already carries `gross` per row.
  - Reword the sentence to state both signs: "Gross of these rows, processor minus Mastercard: −2,066.18 USD. Walking from the processor to Mastercard, the step is +2,066.18."
- **Alternative:** walk from Mastercard to the processor. Every step then equals its rows' gross with the same sign, and the sentence needs no explanation. This needs a one-line plan amendment.
- **Also:** add a verifier line asserting the page shows the column its link sums (in the static part, `gross` must be among the shown columns when a bar links on `gross`).

**2. The Summary no longer fits a 1440x900 window.**

- **Where:** the Summary layout. Card 3, "Ledger vs bank and Mastercard", ends at about 707 px; "How much is explained" runs from 739 to 837 px; the footer is at 884 px.
- **What happens.** With a 1440x813 viewport (a 1440x900 window), the page is 895 px tall and the CFO must scroll to see "How much is explained". The plan says "the Summary still fits a 1440x900 window with no scroll". The last round measured 789 px.
- **Fix.** Card 3 now shows the payable twice: the waterfall, then the bridge table with the same five lines. And on the Summary, "Leg 1 difference by type, net USD" (`template.html:711`) repeats the leg-1 waterfall in other numbers (Minor 3).
  - Cheapest, in order:
    - remove the by-type table;
    - tighten the waterfall rows (18 rows: 3 px each frees 54 px);
    - or fold the bridge table behind a "both bases" toggle.
  - Re-measure until the page is at most 813 px.
- If "1440x900" was meant as the viewport, it fits by 5 px. That is a tolerance too thin to rely on.

**3. The headline "Resolves USD 567,345.29" is 70% a timing item.**

- **Where:** `bridge/report.py:407` (`resolves_usd`) and `bridge/template.html:990`.
- **What a CFO sees.** The biggest number on Pending actions is 567,345.29, introduced as "if every task below is closed". 400,000.00 of it is T07: Treasury's 30-Sep prefund (BS0032), which the bank credited on 1-Oct. The page itself calls it "a reconciling item to confirm on 01-Oct" that clears by itself. So the screen overstates what closing the tasks fixes by 2.4 times. A CFO who knows the prefund will see that in the first minute.
- **This follows the plan's wording** ("the net of the exceptions it lacks"), so it is your call, not a defect.
- **Fix.** Keep the total and add the split on the same line. The data already carries each exception's class.
  - Example: "of which 400,000.00 is timing (funding in transit, clears 01-Oct); 167,345.29 is errors to correct".
  - Optionally, tag T07's cell "timing".

**4. Printing drops the task names on Pending actions.**

- **Where:** `bridge/template.html:207`: `nav, button.i, .filters, button, .switch { display: none !important; }`.
- **What happens.** Each task name ("▸ T07 Reconcile bridge account cash…") is a `button.task`. When I applied this rule to the page, the Task cell came out empty. A printed Pending actions page would list statuses, owners and amounts against no task. Source references drawn as buttons would disappear the same way. The plan says "printable".
- **Fix.** Narrow the rule to the controls only, for example `nav, button.i, .filters, .switch, button.ghost, button.primary`, or add `button.task { display: inline !important; }`. Then do a real print preview.

**5. The README says another month needs three changed lines; it needs more.**

- **Where:** `README.md:56-58`.
- **What is also month-bound:**
  - `CUTOFF_DATE` (`bridge/policy.py:21`) fixes ageing and escalation to 5-Oct.
  - Fixed words: "September" and "October" in `close.py:115,156`, `report.py:464` and `policy.py:233-257`.
- **What goes wrong.** A reader who follows the README for October gets ageing counted to 5-Oct, wrong escalation, and labels that still say September. Nothing warns them. It is also a written claim Clara's evaluators may test. The decision log says "the month is declared, not parametrised".
- **Fix.** One sentence:
  - "The run is built for September 2026. The month is declared in `bridge/policy.py` (`PERIOD_START`, `PERIOD_END`, `HOLIDAYS`, `CUTOFF_DATE`); another month also needs the September/October wording reviewed."
  - Or drop the "to run another month" promise.

## Minors

1. **The screen list is declared twice:** `template.html:273` and `policy.py:411`. Read it from `PAGE.screens`.
2. **Negative "Resolves" on T08 and T13.** They show "Resolves USD −116,160.96", which reads as making things worse, and both count the same entries.
   - Show "116,160.96 Cr on 2105", or the absolute amount with "credit on 2105".
   - Say once that entry tasks are outside the top total.
3. **The same type shows two amounts and two signs on one screen.** Leg 1 on the Summary shows "Only in Mastercard +2,066.18" in the waterfall (gross) and −2,041.36 under "Rows matched" and in the by-type table (net).
   - The by-type table at `template.html:711` is now redundant with the waterfall. Removing it also helps Material 2.
4. **The entries bar shows the full table above the right sum.** It opens Close with the proposed-entries table unfiltered ("Total 41 172,291.89") above the correct sentence "add up to −125,288.88". Same for E10. This pattern predates this round.
5. **README for someone new to the terminal.**
   - Say how to open a terminal in the folder:
     - macOS: right-click the folder → Services → New Terminal at Folder, or type `cd ` and drag the folder in.
     - Windows: type `cmd` in File Explorer's address bar.
   - Say that on a Mac without developer tools, `python3` opens an install prompt, and accepting it is fine.
   - Say where the code folder comes from (the zip).
6. **Wording in the "i" text for "figure.settlement_days".** It says "days … that the bank debits in the month". The 30-Sep settlement, which the bank debits on 1-Oct, is included. Say "settlement days 31-Aug to 30-Sep".
7. **The clarification in b9eef94 is unpinned.** Add assertions for T02 90,215.88, T06 40,616.94 and T05 15,600.17 (exceptions' net, not the sum with entries). Name T05 in the decision log entry.
8. **The leg-2 waterfall's broken axis.** It draws the 968,096.50 start much shorter than the 1,008,713.44 end, and the break mark is small. Consider a clearer break, or the same scale-break note under the title.
9. **The ERP file is not mentioned on the page.** One line on Close ("also in `proposed_journal_lines.csv`, ready to load into the ERP, marked not approved") would help the demo. The plan does not require it.

## Hand checks after the fixes

- Click "Only in Mastercard" and "Duplicate in processor". The footer and sentence should equal the step's amount, with the sign explained.
- Summary height at a 1440x813 viewport: 813 px or less.
- Print preview of Pending actions: task names present.
