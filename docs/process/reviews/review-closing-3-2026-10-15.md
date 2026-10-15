# Closing review 3: honest evidence and the closing fixes (de0b6cb..df98933)

Brief B-2026-10-15-64 asked for a fresh-context, read-only review. I worked in my own clone at a scratch folder, at df98933, with worktrees of cd9981d (`../old`) and 0ef8363 (`../prev`). Runs, plants and extracted page data are under a scratch folder. Nothing was written in the repo, the records or the workspace, and both the clone and the source repo have clean working trees. The Chrome tab is closed and the server on port 8775 is stopped.

**Verdict: NOT YET.**
- **The data side is done.**
  - `proposed_entries.csv` is byte-identical to cd9981d's (sha256 315ec8d5…).
  - No entry line cites an opening-balance row, in the file or on the page.
  - A missing input no longer crashes the run.
  - The bridge's words are computed, not stated.
  - T08's click equals T08's figure.
- **What remains is two display defects**, both in `template.html`, both one or two lines to fix:
  - The Grouped view's settlement and timing figures throw a JavaScript error and open nothing. This is a regression: they worked at 0ef8363.
  - The bridge's column headers slide over its figures once the owed lists are open and the Summary scrolls.
- Fix both and the tool can be frozen. No re-review is needed beyond a hand check of those two clicks.

## Closure checks

**(a) Verifier not weakened: yes.**
- Each commit stays in its lane:
  - d20ff36 touches only `tests/`;
  - 47e3056 touches only `bridge/`;
  - df98933 touches only `tests/` (judged below).
- The withdrawn test (`test_source_rows_not_repeated_across_one_entrys_lines`) is replaced by stronger ones:
  - a sha256 pin on `proposed_entries.csv` against cd9981d;
  - no opening-balance citation, in the file or on the page;
  - page sources equal each line's own `src`.
- The "missing opening balances" and "five deleted inputs" plants now run through to the page.
- The BS0024 plant checks:
  - the note's exact figures;
  - that the label names 24-Sep;
  - Grouped leg 3 equals the bridge.
- The BS9001 plant pins that T07 becomes blocked (9).
- Suite: **487/487 green** (469 last round).
- **The hole is the same as last round:** the page script cannot run in the suite. Both material findings live in the script and need a hand check.

**(b) Plan sentences encoded and implemented.**

| Plan sentence | Status |
|---|---|
| Evidence is never invented; file is cd9981d's; no opening-balance citation | ✓ (sha matches; 0 of 41 lines cite `gl_opening_balances.csv`) |
| Page lists each source row once per entry and says "same evidence as the line above" | Partly. Repeats are still listed, with the marker in place of their fields (Minor 2) |
| A missing input never crashes the run | ✓ All 12 single-file deletions and an empty folder write all 9 files |
| Bridge labels never overlap their figures | ✓ at rest. ✗ when the owed lists are open and the page scrolls (Material 2) |
| E10 sentence only when it holds; otherwise "of which X is E10; Y not explained"; settlement label names unpaid days | ✓ |
| T08's click equals T08's figure | ✓ 116,160.96, the same link as the bridge's entries line (the click shows −116,160.96 debit-positive; Minor 4) |
| A multi-part click names each part; "Together … that is … credit — the figure"; no single footer sum | ✓ |
| T07 "Waits on"; not-blocked derived from timing items | ✓ |
| Owed rows open below the Summary; one click opens one line's rows | ✓ on the Summary. ✗ in Grouped: the click throws (Material 1) |
| 2105 difference computed once; no read-back from a link; no shared mutable default | ✓ `gap` is computed once in `_payable_bridge`, and `_grouped` reads the bridge's figures |

**(c) Real data.**
- `run.py` compared with cd9981d:
  - byte-identical: balances.csv, cash_recon.csv, checks.csv, close_tracker.csv, exceptions.csv, **proposed_entries.csv**, treasury.csv;
  - run_manifest.json differs only in `code_version`.
- Compared with 0ef8363, only `proposed_entries.csv` (the honest version is back), index.html and the manifest differ.
- Independent recount from the output file (no tool imports): the 2105 lines net to −116,160.96 with all entries, −125,288.88 without E10, and E10 alone is +9,127.92. All tie with the bridge.
- **Plants:**
  - **BS0024 deleted** (`review58/plant3/data`). Note: "-35,756.49, of which 9,127.92 is E10; -44,884.41 not explained." Label: "Mastercard settlements not debited by 30-Sep (24-Sep, 30-Sep)", 89,528.40. Arithmetic: 54,700.22 − 89,528.40 − 928.31 = −35,756.49. Blocked tasks: 9, because T07 now lacks a non-timing item.
  - **`gl_opening_balances.csv` deleted:** runs. Account names fall back to "bridge cash" / "mc payable" (Minor 6).
  - **Every other single-input deletion and an empty folder:** all run. Wording defects under the plants: Minor 6.

**Chrome.** The window resized properly this time: viewport 1440×813 at dpr 2, so no iframe was needed.
- **Summary at rest:** content is 789 px, no scroll, no horizontal scroll. The bridge labels wrap and no cell overflows. The margin is now 24 px, down from 67 px, because the labels wrap onto two lines (Minor 5).
- **Every Summary figure clicked** (22 leg figures, 11 bridge cells, 14 explained or by-type cells): no red tie error anywhere.
  - Ledger: "The amounts add up to the figure, 70,588.66 USD."
  - Entries: "−125,288.88" / "−116,160.96".
  - Result: "Ledger rows add up to 70,588.66 USD. / Proposed-entry lines on 2105 add up to −125,288.88 USD. / Together: −54,700.22 USD debit, that is 54,700.22 USD credit — the figure." The footer shows only "Source rows: 436".
  - Difference: E10's 3 rows, 9,127.92.
- **Owed lists, opened one by one:**

  | Lists open | Page height | Scrolled to |
  |---|---|---|
  | 1 | 854 px | 41 px |
  | 2 | 1,014 px | 202 px (bridge's first row still at 152 px) |
  | 3 | 1,079 px | 266 px |
  | 4 | 1,239 px | 426 px; the sticky bridge headers sit over "928.31" (Material 2) |

- **Grouped leg 3:**
  - It renders and the figures match the bridge.
  - Clicking its settlement figure bolds the cell and throws `TypeError: Cannot set properties of undefined (setting 'innerHTML') at drawOwed` (Material 1). This is the only console error of the whole walk.
- **Close:**
  - Clicking E10 shows 12 rows: 3 processor rows with fields, 9 marked "same evidence as the line above", tie 9,271.44 (E10's debits), no opening-balance row.
  - E01: 604 rows, 453 of them marked. E03: 4 rows, 2 marked. E05: 23 rows, 16 marked.
- **Pending actions:**
  - The sentence and the 8 blocked tasks are right. Every open task with a finding reads "Waits on …".
  - "Show them in Close" ties for every task, with no red error:

    | Task | Total | Rows | Of which marked "same evidence" |
    |---|---|---|---|
    | T02 | 91,703.80 | 620 | 465 |
    | T05 | 19,058.85 | 960 | 720 |
    | T06 | 40,616.94 | 4 | 2 |
    | T08 | −116,160.96 | 397 | 0 |
    | T09 | 12,500.00 | 4 | 2 |
    | T11 | 8,412.30 | 23 | 16 |
    | T13 | 172,291.89 | 1,611 | 1,205 |

- **Drafts:** D04 renders. Copy now shows "Copied" at top level, which settles last round's iframe doubt. I did not click Download .txt: the download code is unchanged since last round.
- **Data quality and Reconciliation:** no page-level horizontal scroll. The Detailed table scrolls 137 px inside its own frame; this predates the round.

**(d) Judgement calls:** one by one, below.

**(e) Code standards: met.**
- `_entries_link` is declared once and shared by T08, T13 and the per-task links.
- The blocked rule is derived from exception classes.
- `payable_owed` uses `default_factory`.
- `_grouped` reads `bridge[0]["waiting"]` instead of parsing a link.
- The one drift is Material 1: `bridgeBlock` gained a required `host` argument, and only one of its two callers passes it.

## Material, ranked by demo risk

**1. Grouped leg 3: clicking the settlement or timing figure throws and opens nothing. This is a regression.**
- **Where:**
  - template.html:720: `cell.appendChild(bridgeBlock(r.bridge))` passes no host.
  - template.html:426: `drawOwed` runs `host.innerHTML = ""` on that undefined host.
  - template.html:449 is the handler that calls it.
- **Failure scenario:**
  - The CFO, or an evaluator, goes Reconciliation → Grouped → leg 3 and clicks "44,643.99" or "928.31".
  - The cell turns bold and blue as if open, nothing appears, and the console shows a TypeError.
  - At 0ef8363 these rows expanded in place, and review 2 walked that click.
- **Fix:** in `bridgeBlock`, when no host is given, create one under the table: `host = host || box.appendChild(el("div"))`, before the `drawOwed` definition is used. Or pass a host from line 720 and append it after the block.
- **Test:** the script cannot run in the suite. Add a static assertion that every `bridgeBlock(` call in the template passes two arguments, or that the function defaults `host`. Add "Grouped leg 3 settlement click opens its rows, no console error" to the hand checks.

**2. The bridge's sticky column headers cover its figures when the Summary scrolls.**
- **Where:**
  - template.html:56 makes every `th` sticky at top 0.
  - template.html:110 gives `.bridge th` no background.
  - Opening the owed lists now lengthens the Summary and scrolls it (`intoView`, template.html:409/449).
- **Failure scenario:** opening all four owed lists (settlement and timing, both columns) scrolls the Summary 426 px. The headers "Entries with no condition (8)" and "All entries, if E10's evidence arrives (9)" then sit over "928.31" in the same spot. It looks like the overlap fixed last round.
- **Fix:**
  - Add `.bridge th { position: static; }`.
  - Optionally, use `scrollIntoView({ block: "nearest" })` for the owed host, so the bridge stays on screen longer.
- **Test:** hand check: "no bridge header overlaps a figure with all four owed lists open".

## Minor (can wait, or be said aloud)

1. **BS0024 plant: clicking the −35,756.49 difference opens E10's rows** and says "add up to 9,127.92 USD".
   - The note explains the split, but this breaks "every figure opens rows that sum to it" under a plant.
   - Fix: when `gap != explained`, title the click "E10's part: 9,127.92" or drop the link (report.py:449-451).
2. **The "same evidence as the line above" rows.**
   - They are listed, not skipped: T13 opens 1,611 rows, 1,205 of them marked.
   - "The line above" is literally wrong: `processor_transactions.csv:2371` is marked right below `:2521`. The marker means "an earlier line of E01", not the row above it.
   - Fix (template.html, `drawSource`): skip the repeats, and add one line per repeated entry line, e.g. "E01, line 2 (5100): the same 151 rows as line 1". The row count then counts distinct rows.
3. **"Waits on" is now on all 9 open tasks with findings, but nothing on the page says which 8 are blocked.**
   - The only "Blocked" a CFO sees is T09's checklist status.
   - Fix: prefix the 8 with "Blocked:", or add a column. See judgement call 2.
4. **The T08 text and its click show the same number with different signs.** T08 says "116,160.96 USD"; the click says "−116,160.96 USD", debit-positive. It can be explained out loud, or the click can append "(credit)".
5. **The Summary margin is down to 24 px**, from 67 px. An earlier plan block asked for at least 40 px. It still fits at 813 px with no scroll.
6. **Wording under missing-input plants:**
   - Account names fall back to `ACCOUNT_NAME` ("bridge cash", "mc payable", report.py:165).
   - With the settlement summary missing, the label ends "(… by 30-Sep ()".
   - With no pending entry, "All entries, if 's evidence arrives (2)" (report.py:466).
   - With the processor file missing, "0 data flags go back to the ; the processor (processor_transactions.csv) and the processor invoice was not received" (report.py:383-390; this predates the round).
   - The E10 sentence calls every processor row that a pending entry cites "processor-only" (report.py:460), whatever the entry's type.
7. **The Detailed table scrolls 137 px inside its frame at 1440 px.** This predates the round.

## Judgement calls, one by one

1. **The session's test fix df98933 (the E10 note sign). Accept: the code was right and the original test was wrong.**
   - E10 *debits* 2105: the recount gives +9,127.92 on its 2105 line.
   - On the case data the gap is therefore +E10: 54,700.22 − 44,643.99 − 928.31 = +9,127.92.
   - On the plant, the unexplained part is gap − E10 = −35,756.49 − 9,127.92 = −44,884.41. That is the plan's own figure, and the figure in the test's header comment.
   - d20ff36's `-e10` / `gap + e10` would have demanded "of which −9,127.92 is E10; 26,628.57 not explained", which is false.
   - The fix still pins exact figures, so it does not weaken the verifier. The process point: the test author's sign slip was caught only because the code was right. Worth one line in `registro-ia.md`.
2. **The implementer's call: every task reads "Waits on". Accept the word, but it needs a blocked marker.**
   - The word is honest for what each row lists: the task does wait for those exceptions, entries and checks to be resolved.
   - "Lacks" was the word that read as a defect on T07.
   - But for the 8 tasks that really lack something, "Waits on" alone softens the message. Next to a sentence that says "8 of them are blocked", the CFO cannot tell which 8. A failed check is something to fix, not something to wait on.
   - Cheapest honest fix: keep "Waits on", and show "Blocked —" before it on the 8 rows the count includes (Minor 3).
3. **The derived blocked rule. Accept.**
   - A task is blocked if it lacks an entry, a failed check, or any exception whose class is not timing.
   - Case data: T02, T05, T06, T08, T09, T11, T12, T13 = 8.
   - The BS9001 plant makes T07 blocked (9), and so does the BS0024 plant: a real cash defect lands on T07 and counts.
   - The rule reads from the data, not an id.
4. **The page grows to 1,014 px when owed rows open, and scrolls to them. Acceptable, with Material 2 fixed.**
   - One list: 41 px of scroll. Two: 202 px, and the bridge stays visible.
   - The plan sentence was "does not move the Summary": it reflows nothing above, it only scrolls, which meets the intent.
   - At four lists (1,239 px) the bridge leaves the screen, and the sticky headers overlap.
   - Fix the headers. `block: "nearest"` would keep the bridge visible longer.
5. **Listing repeated evidence with a marker instead of skipping it. Accept the honesty, reject the form** (Minor 2). Nothing fabricated is shown. But 1,205 marked rows on T13, and "the line above" pointing at the wrong row, are noise in the panel an evaluator uses to check traceability.
6. **The settlement label lists every unpaid day.** Accept. It is computed and matches its figure. Under the missing-bank-statement plant it lists all 22 days and wraps. That is honest: with no statement, nothing is known to be debited.
7. **The fallback account names (`ACCOUNT_NAME`) when opening balances are missing.** Accept: no crash, which is what mattered. Cosmetic (Minor 6).
8. **Is the tool ready to freeze?** After Materials 1 and 2, yes.
   - The accounting has not moved since cd9981d, and every case-data click ties.
   - The evidence is honest again.
   - The remaining minors are wording under plants, or things to say aloud.

## Throwaway files

All under a scratch folder:
- `out_clone/`, `out_old/`, `out_prev/`: the runs at df98933, cd9981d and 0ef8363;
- `out_plant3/`: the BS0024 plant;
- `out_no_<file>/` and `out_empty/`: the missing-input plants, with their data in `plants/`;
- `s/pd.py`: the page-data extractor;
- `web/`: the served copies.
