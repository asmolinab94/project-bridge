# Closing review 6: freeze fixes 2

This review covers brief B-2026-10-15-71. I checked the repo read-only on `feat/project-bridge` at HEAD 073a17e. The working tree is clean and nothing in the repo was written. My scratch files are in a scratch folder:
- `out/` is this run.
- `outbase/` and `base/` are a run of d8aa455, made with `git archive`, to compare against.
- `data.json` is the page data.
- `out/frame.html` is a 1440x813 frame, because the Chrome window stayed at 3008 px wide.

The local server on port 8791 is stopped and the Chrome tab is closed.

**Verdict: FREEZE.**

Both material findings and all eight minors from review 5 are fixed. The suite runs 527 tests, all green. No figure in any output file moved. In Chrome, every Summary figure that states a row count opens exactly that many rows. Nothing I found blocks the freeze; what is left is cosmetic or a test gap.

## Closure checks

**(a) Review 5's findings: all fixed.**

1. **Material 1, figures open fewer rows than they state. Fixed.**
   - **When flags are hidden:** only on the bare Detailed view (`template.html:892-897`).
   - **Opening from another screen shows them:** `apply` turns them on (`template.html:1066`).
   - **"Clear filters" hides them again** (`template.html:866`).
   - **The hidden group is the 130 leg-1 flags,** declared once as `HIDDEN_FLAG_TYPES` (`policy.py:408`). The missing processor invoice stays visible: on the bare view it appears under its own "Input missing · leg 3 · 1 row" header.
   - **The button counts what the current view hides** (`template.html:978-981`).
   - **In Chrome:** see (d).
2. **Material 2, the headline label. Fixed.** On Pending actions it reads: "Resolves USD 567,345.29 — 167,345.29 needs action by Clara · 400,000.00 funding in transit (clears 01-Oct)". Andrés's approval is logged in DECISION_LOG.md, and the plan was amended in bf757d9.

Minors from review 5:
1. **The plan's "156 rows":** now 155 (`plan.md:834`). Fixed.
2. **Data quality "All" footer:** the amount cell is blank unless one check is selected (`template.html:788`). Seen in Chrome. Fixed.
3. **Copy rows shown:** fixed. In Chrome, the duplicate bar's six rows copied with the same 13 headers, in the same order and with the same labels as the screen (Type, Date, Gross USD, … Source, Assigned person, Status, Comment). Six data rows, and Status came through as "Open". The source cell holds every source joined by ";", where the screen shows the first plus "+3 more". That is acceptable.
4. **One type order:** `TYPE_ORDER` (`policy.py:406`) is now used by Grouped and by the Detailed summary. Detailed now runs Duplicate, Sign flipped, Amount differs, FX, Month cut-off, Only in processor, Only in Mastercard, which matches the waterfall and Grouped. Fixed.
5. **Minus sign in the step sentence:** fixed. It now reads "Gross … −2,066.18 USD … the step is +2,066.18." The remaining hyphens in the summary tables are Minor 2 below.
6. **Grouped leg-1 footer:** reads "3,122 pairs and single rows" (3,108 pairs plus 14 rows on one side only). Fixed.
7. **Search skips flag rows:** fixed. Searching PX10000065, a bad-reference-only row, on the bare view returns it ("Showing 1 of 262").
8. **Missing inputs detail:** now reads "inputs that are absent or unreadable (never estimated): processor invoice". Fixed.

**(b) The tests were not weakened.** Only `tests/test_screens.py` changed (+96/−3).

- **The amended hidden-flags assertion is stronger, not weaker.**
  - Before, it checked only that the count equalled the whole class (131).
  - Now it checks that the hidden row ids are exactly the leg-1 data-issue ids, that there are 130 of them, and that the declared count is 130.
  - The one loosening is that the label check is now conditional ("if label in hidden"). That is fair: the button text moved into the script and is computed live. I checked it in Chrome instead.
- **The pattern-match tests are weak but honest.**
  - I ran the new tests against the d8aa455 code. Six of the seven fail there, so they do catch the old behaviour.
  - The weak point is the one named after the finding. `test_figure_counts_equal_the_rows_they_open` (`test_screens.py:2298`) passes on the old code too, because it computes from the page data assuming nothing is hidden. The real guard is a regex (line 2318) that accepts any `x = true` inside `apply`.
  - The test's docstring says this openly ("the script half is static"). This is Minor 3, not a blocker: Chrome confirms the behaviour.
- Nothing was deleted.

**(c) What 073a17e could have broken: nothing found.**

- **Every output file compared with the d8aa455 run:**
  - byte-identical: `balances`, `cash_recon`, `close_tracker`, `exceptions`, `proposed_entries`, `proposed_journal_lines`, `treasury`;
  - `checks.csv`: only the `missing_inputs` detail text changed. Its result (false) and count (1) are the same;
  - `run_manifest.json`: only the code version and timestamp changed.
- **`proposed_entries.csv` sha256** is 315ec8d5b4625c84f4a760da3165591c4eef7931fe6c3d6017fe9ccd0adc2a60, unchanged.
- **The new sort keys** in `report.py:668,680,786` look up `TYPE_ORDER.index(...)`. That would crash on a type missing from the order, but the run passes and the order is built from every declared type.

**(d) Chrome, in the 1440x813 frame.**

- **Summary:** content is 757 px tall, the footer ends at 745 px, and nothing overflows sideways (1440).
- **I clicked all 57 Summary links** and checked each count against the rows it opened:

  | Summary figure | States | Opens |
  |---|---|---|
  | Leg 1, Exceptions | 255 | 255 |
  | Leg 1, Escalate | 118 | 118 |
  | Leg 1, Waiting outside Clara | 251 | 251 |
  | Leg 1, Matched with a difference | 111 | 111 |
  | Leg 1, the six type bars | 6 / 4 / 8 / 95 / 3 / 5 | the same |
  | Leg 2, Exceptions, Escalate, Waiting, Duplicate | 1 each | 1 each |
  | Leg 3, Exceptions | 6 | 6 |
  | Leg 3, Escalate | 2 | 2 |
  | Leg 3, Waiting outside Clara | 1 | **1** (was 0) |

  - "How much is explained" opens 255 / 4 / 121 / 1 / 1 / 6 / 3 / 2 rows. Those figures state no count.
  - Totals and settlement days open Grouped. The Close-section figures open Close.
- **Bare Detailed:** "Showing 132 of 262 rows". The button reads "Show the 130 data flags — no money; also in Data quality". Clicking it gives 262 and "Hide the 130 data flags"; clicking again gives 132.
- **Search finds a flag row:** yes, as in (a) minor 7.
- **Copy matches the screen:** yes, as in (a) minor 3.
- **Type order is consistent:** yes, as in (a) minor 4.
- **The headline reads exactly as required.**
- **The Grouped "Stale authorisation" row** opens 22 rows.
- **No console errors.** I reloaded cleanly, then clicked every Summary link, cleared filters, toggled the type headers, and switched every screen.
- **Not checked:**
  - a real mouse click on every element (I clicked through the page's own DOM);
  - whether the real clipboard receives the text (I stubbed it, without recursion this time);
  - print preview;
  - a phone;
  - opening the file by double-click;
  - a fresh install on a clean machine.

## Material findings

None.

## Minors

1. **The flags stay shown after a hand-emptied filter** (`template.html:866,1066`). Open "Exceptions 255" from the Summary, then set the Leg dropdown back to empty by hand instead of pressing "Clear filters". The view is now unfiltered but shows 262 rows, not 132. The button is visible and correctly says "Hide the 130 data flags", so nothing is misleading. Possible fix: reset `showFlags` whenever `bare()` becomes true.
2. **Hyphens remain in the Detailed summary and type headers.** For example, "Only in Mastercard … net -2,041.36" comes from `fmt`, while the waterfall uses "−". Cosmetic.
3. **The figure-count test cannot fail on the hiding rule** (`test_screens.py:2298,2318`). Proper coverage would need the script run in a headless browser. Leave it as a known limit; it is the hand check below.
4. **The plan still says "show the 131 data flags … 130 on leg 1 plus the missing processor invoice"** (`plan.md:850`). The freeze-fixes-2 block at `plan.md:863` supersedes it, but the earlier sentence was not corrected.
5. **The copied amounts carry thousands commas** ("3,593.63"), as on screen. In a spreadsheet set to a comma-decimal locale (common in Latin America), these could paste wrongly. The CSV keeps plain numbers.

## Hand checks left for the owner

- On the Summary, click leg 3 "Waiting outside Clara 1" and leg 1 "Exceptions 255" by real mouse. Each should open exactly that many rows.
- Paste "Copy rows shown" into the spreadsheet Clara would use, and confirm the columns and amounts land.
- Do a real print preview (Cmd+P) of Pending actions.
