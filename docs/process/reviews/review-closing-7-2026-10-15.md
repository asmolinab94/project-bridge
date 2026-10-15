# Closing review 7: named owners

## Verdict

**Freeze after one small fix.** The names are right, nothing was invented, no figure moved, and the tests were not weakened. One real defect: an analyst cannot blank the "Assigned person" field. Fixing it touches one line of the page script. If you would rather not reopen the tool for that, freezing as is with the defect listed as a known minor is defensible.

## What I checked, with evidence

**(a) Names only where the email states the role.** The email thread names exactly three checklist roles, all on the first header line: Lucia Ferreira (Treasury), Diego Alvarado (Finance Ops) and Marta Quintero (Controller). Camila Rojas (Customer Success) appears on a later header line. In the run's `close_tracker.csv`, exactly 16 tasks carry a name:
- Finance Ops: 8
- Treasury: 4
- Controller: 3
- Treasury / AR: 1

The other 10 tasks stay role-only: AR, AP, FP&A ×2, Tax, CFO, Billing, Payroll, Revenue Accounting and Compliance Reporting. Owner of record is unchanged everywhere: the `owner_role` and `clara_owner` columns are byte-identical to the frozen run. Across the 262 rows of `exceptions.csv`, the names are Finance Ops → Diego (259), Treasury → Lucia (2) and Treasury / AR → Lucia (1). No name appears outside these roles.

- **Treasury / AR → Lucia (task T09, clearing the suspense receipt):** acceptable. The role stays the owner of record and Lucia did raise the suspense item. But the emails name no AR person, and the "i" text claims every name comes from a line "that states the person and the role". That is not true for this one row, and its source cites "Lucia Ferreira (Treasury)" (see minor 1).
- **Finance Ops read from the "TO:" part of a "FROM:" line:** sound. The email states "Diego Alvarado (Finance Ops)" word for word. The parser keeps the whole header line as the sender field, so the name is read from the recipient part of that line. The only risk is that a stricter parser (sender only) would silently lose Diego. The tests would catch that, because they require all three roles.
- **Names read at run time:**
  - Email file missing: the run completes with no names, the figures are unchanged (`proposed_entries.csv` is identical), and the missing-inputs check fails and names the file. Good.
  - Malformed line: I changed line 1 to "Lucía Ferreira [Treasury] … Diego Alvarado (Finance Operations)". The run completes and only Marta is named. Lucia and Diego disappear silently and no check says so. The failure is safe, since the tool shows fewer names and never a wrong one. Note the name pattern is ASCII-only, so an accented name drops (see minor 2).

**(b) Tests not weakened.** Between the pre-block code (073a17e) and HEAD, the only change to existing tests is the expected column lists in `tests/test_page.py:53-63`. They gained the two new columns, with a comment pointing to the plan. Nothing else was removed or relaxed. The new tests are the named-owners group at `tests/test_screens.py:2348-2450`. The full suite passes: 534 tests (527 at the freeze). As the plan asked, the tests read the names from the email file rather than hard-coding them.

**(c) Nothing else moved.** I ran the frozen tag (tool-frozen-2026-10-15, extracted with git archive) and HEAD on the same data.
- These files are byte-identical: balances, cash_recon, checks, treasury, proposed_entries and proposed_journal_lines. The last two match the hashes in the brief: 315ec8d5… and a8ccdcc3….
- `exceptions.csv` and `close_tracker.csv` differ only by the new name column. All other cells are identical, except 16 tracker `src` cells that gained the email reference.
- `run_manifest.json` differs only in `code_version` ("unknown" for the extracted copy, which has no git history).
- The data embedded in the page differs only in: the new columns and their values, the two new task fields (`owner_name`, `owner_glossary`), two explanation texts, and the code version. Nothing else changed in the page.
- DRY holds. The role → person map is built in one place (`policy.people`, `bridge/policy.py:425-436`), once per run in `bridge/close.py:201-205`, and everything else consumes `close.people`. The plan describes a fixed `PEOPLE` table; the code reads the email at run time instead, which is better, but the plan text is out of date.

**(d) Chrome.** I served the page on a local port, checked it in a 1440×813 frame, then stopped the server and closed the tab.
- **Pending actions:** the 16 named tasks show, for example, "Treasury — Lucia Ferreira" with an "i" button explaining where the name comes from. The other 10 show the role only, with no "i".
- **Reconciliation:** the "Clara owner" column reads role plus name. "Assigned person" defaults to the named person on all 132 rows shown.
- **Typed value wins:** I typed "Ana Test" in one row. It survived a tab switch and a reload.
- **Summary:** fits at 813 px (scroll height 813).
- **Console:** no errors on a fresh load after visiting all five screens.
- I cleared the browser storage I wrote to.

## Material findings

1. **Clearing "Assigned person" brings the default name back** (`bridge/template.html:452`).
   - **Code:** `personOf` returns the typed value, or the email name when that value is empty: `noteOf(x.id).person || x.r.clara_owner_name`.
   - **Failure:** an analyst deletes "Diego Alvarado" to leave a row unassigned. Storage saves an empty value. After a reload, Diego is back (seen in Chrome: "" before the reload, "Diego Alvarado" after). The same fallback also feeds `exceptions_with_notes.csv` and "Copy rows shown". So "a typed value wins" holds except when the typed value is blank.
   - **Fix:** use the default only when no note exists for that row, for example `var n = notes[x.id]; return n ? n.person : (x.r.clara_owner_name || "");`. That is one line, plus a test or a hand check.

## Minors

1. **The "i" text overstates the source for Treasury / AR** (`bridge/policy.py:531`, task T09). Add a sentence such as: "Treasury / AR shows the Treasury person; the e-mails name no AR person."
2. **Names that fail to parse disappear silently.** A non-ASCII name, missing parentheses or a reworded role all drop the name without warning. This is safe, but no check reports it. Optional: say in the "i" text or in Data quality how many roles the email named.
3. **Stale comment and a plan point with nothing to act on.** The comment at `bridge/policy.py:424` says Customer Success is used "only [for] a drafted message", but no draft goes to Customer Success: every draft goes to Mastercard or the processor. So Camila sits in the map unused, and the plan's "drafts address the named person" never applies on the case data. The test does pin that no internal name leaks into those external drafts, which is the useful half.
4. **The test copies the name pattern from the code** (`tests/test_screens.py:2358`). A flaw in the pattern would pass both. The literal check that all three roles are present partly guards against this.
5. **Source citations are uneven.** The plan says the "i" names the email line. The page shows a generic text, and the specific line is only in the tracker CSV's source column. `exceptions.csv` does not cite the email for `clara_owner_name`, although the tracker does.
6. **Record mismatch.** The decision log entry "Unfreeze for named owners" still says 15 tasks; the plan was corrected to 16 (T02).

## Hand checks for you

1. On Pending actions, confirm the line "Treasury / AR — Lucia Ferreira" (task T09) reads the way you want, given that the emails name nobody in AR.
2. On Reconciliation, type a name in one row, reload and see that it stays. Then blank it and reload: today Diego comes back (finding 1).
3. Open `close_tracker.csv` and check that T02 shows Diego Alvarado, and that T10 (AR) and T25 (CFO) have no name.

Nothing was written to the repo: the working tree is clean. Scratch runs are in a scratch folder. The frozen run is in `outF` and the HEAD run in `out`; `d1`/`o_d1` (email file missing) and `d2`/`o_d2` (first header line malformed) are the run-time parsing probes from check (a).
