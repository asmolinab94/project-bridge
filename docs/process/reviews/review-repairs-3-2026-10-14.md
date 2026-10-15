# Fresh review of the second repair round — 5b82dfc..1870b3f

Brief B-2026-10-15-32, fresh-context opus reviewer, read-only. **Verdict: not ready, close.** The code does what the
plan block says, and every finding of the second repair review is fixed or was dropped on purpose. The verifier is
stronger, not weaker. Two things stop sign-off, and both are in the new per-file read status, not in the money logic:

- The coverage check reads every date column of a file. Ordinary files with a T+1 settlement date or a forward value
  date would fail every month.
- A file that cannot be read at all never shows the "figures are not reliable" warning. Only a truncated file does.

Both fixes are small.

## Closure checks

**(a) Verifier not weakened: yes.**
- 285/285 tests pass at 1870b3f.
- `git diff d01eda3 1870b3f -- tests` is empty.
- Every assertion changed between 54ee3a5 and d01eda3 follows from the new plan block:
  - `unexplained` is renamed `usd_conversion_error`. The −1,200.00, −1,199.94 and 0.06 figures are kept; PX10000601
    gains its owner, Mastercard.
  - The owner texts become the four owners.
  - The unmatched-entry key goes from MAN90002 (the reference) to MJ-90002 (the je_id).
  - The unrecorded half of the duplicate debit is owned by Treasury.
  - A crossing row (`CROSSING`) is added to every cash case.
  - The 399,000 case gains its signed −1,000.00.
- No case-data figure changed: 400,000.00, 40,626.94, 53,986.40, 465.00 and 0.00 are all the same.
- The literal guard got stronger: owner names, the new type codes and the new check name are seeded violations.
- `bridge/` has no fixture special-casing. No planted id, date or amount appears outside policy.py.
- Process note: d01eda3 pinned the 399,000 case (crossing row 399,000.00, difference −1,000.00) while the plan
  (18b2a25) still said the two rows always add up to the item. 7d348b8 then rewrote the plan to match the test. The
  final plan and the tests agree, but for that one step the plan followed the verifier, not the other way round.

**(b) Findings of the second repair review: all fixed, or dropped by decision.** Plants are in
`review3/scripts/plant.py`; copies of the planted data are in `review3/plants/`.

| Plant | Cash unreconciled | Rows (leg 3, crossing) | Owner | Rows explain the item? |
|---|---|---|---|---|
| BK-BS0029 booked 1-Oct | 0.00 | `ledger_posted_late` BS0029 +53,986.40 | Accounting | yes, equal |
| Same, ledger at 53,000 | 0.00 | `ledger_posted_late` +53,000.00 and `ledger_amount_diff` +986.40 | Accounting, both | yes, sum 53,986.40 |
| 465 fee booked 1-Oct | 0.00 | `ledger_posted_late` BS0028 +465.00 | Accounting | yes |
| BS0031 posted 30-Sep | 0.00 | `bank_not_yet_posted` BS0031 −44,643.99 (not funding) | Treasury | yes |
| TR-20260930 at 399,000 | 0.00 | `funding_in_transit` +399,000.00 and `ledger_amount_diff` −1,000.00 | Treasury; Accounting | yes: item 399,000; the 1,000 sits outside the September bridge, as the plan says |
| Extra: bank 53,000 on 30-Sep, ledger 53,986.40 on 1-Oct | 0.00 once the running balance is corrected (986.40 from my plant only) | `ledger_posted_late` +53,000.00 and `ledger_amount_diff` −986.40 | Accounting | yes |
| Extra: BK-BS0018 deleted (unrecorded duplicate) | 40,616.94, cash check fails | `bank_line_unrecorded` 40,616.94 | Treasury, set when the row is built | yes |

- The cross-month leftover (465 against an unrelated 100) was dropped by Andrés's decision of 2026-10-14. Not raised.
- Minors of the second review:
  1. Two `owner` columns in the download: **fixed**. They are now `who_resolves` and `owner_note`.
  2. The sentence "Every difference has a type and an owner": **fixed**. It sits under the summary cards.
  3. Type follows the bank line's kind: **fixed** (recon.py:298).
  4. Unmatched entry labelled by je_id: **fixed** (recon.py:284).
  5. Signed amount differences: **partly**. `ledger_amount_diff` is signed (ledger minus bank) and leg 1 was already
     signed. `settlement_amount_diff` is still `abs(gap)` (recon.py:237).
  6. Owner set in two places: **fixed**. It is set once, when the row is built (recon.py:79, 279), and a syntax-tree
     test forbids any later `.owner =`.
  7. Small leftovers:
     - `CASH_CHECK` is gone.
     - The manifest field is now `inputs_not_read`.
     - The suspense lookup keeps every line.
     - The card-number check cites every file it reads (policy `CARD_NUMBER_ATTRS`).
     - Line width is tested.
- The previous "not fixed" item, the balance figure re-filtering the ledger: **still not fixed.**
  report.py:164-170 `_ledger_rows` still selects lines by account and `posting_date <= PERIOD_END`, the same rule as
  close.py:139. The new test (BalanceFigureSources) compares outputs only, so it passes while the rule is written
  twice.

**(c) Real data: passes.**
- Cash: unreconciled 0.00 = ledger 1,547,965.55 − item 400,000.00 − bank 1,147,965.55.
- 11 entries, E01–E11.
- 263 exception rows, every one owned as the plan maps it:
  - Processor 252: 105 bad references, 95 FX rate differences, 22 stale authorisations, 8 amount differences, 6
    processor duplicates, 5 Mastercard-only, 4 sign flips, 3 processor-only, 3 authorised-after-clearing, plus the
    missing processor invoice.
  - Accounting 7: 4 month cut-off, 1 missing processor entry, 1 misdated processor entry, 1 invoice not accrued.
  - Treasury 4: duplicate debit, settlement not debited, funding in transit, suspense.
  - Mastercard 0. Finance Ops 0.
- The page's data blob equals the six CSVs (354 rows, 0 mismatches), and the page's manifest equals
  `run_manifest.json`.
- index.html is 2,279,356 bytes, with no `http(s)://`, `<link` or `src=`.
- The new coverage check (`inputs_cover_period`) passes.
- Per-file status is in the manifest (`files`) and in a new "Input files" table on the Summary tab.

**(e) Code standards: good, with two notes.**
- 1870b3f touches only `bridge/`. The working tree is clean. No remote is configured, so nothing was pushed.
- The four owners are declared once (policy.py:168-187). The type and class codes are declared once.
- `TYPE = policy.TYPE` and `CHECK = policy.CHECK` in recon.py and checks.py are only shorter names for the same
  object. They do not declare anything a second time, and the literal guard still bans the strings.
- Two rules are written twice:
  - The September period filter, in close.py:139 and report.py:169 (see above).
  - The page decides "not reliable" in JavaScript from the literal check name `"inputs_cover_period"`
    (template.html:204). The template is outside the literal guard. It also writes the period into a type label
    ("Posted in October, move into September", template.html:130), while the period is declared in policy.py.
- Comment density is at the file's level.

## Material

1. **The coverage check reads every date column, so ordinary files would fail every month.**
   - Where: checks.py:84-99 checks every column in `read_status["dates"]`, which inputs.py:123-130 fills with every
     column named `auth_date`, `clearing_date`, `settlement_date`, `posting_date` or `value_date`.
   - Why that is wrong: only one column per file says which month the file covers. The others legitimately start
     later or end earlier.
   - Plants, each on otherwise valid data:
     - Mastercard settles each clearing day on the next working day. That is a common convention, and the data
       already has a summary for 31-Aug that is paid on 1-Sep. The detail's `settlement_date` then starts 2-Sep, and
       the check fails on `mastercard_clearing_detail.csv`.
     - A processor extract of cleared rows only, where no authorisation of 30-Sep has cleared yet (clearing is
       usually T+1 to T+3). The last `auth_date` is 29-Sep, and the check fails on `processor_transactions.csv`.
     - On the bank statement, `value_date` is checked separately from `posting_date`. A 1-Sep line value-dated 2-Sep
       passes only because another line is value-dated 1-Sep.
   - Each failure puts the "figures are not reliable" banner on a correct close, every month. People learn to ignore
     it, and then they also ignore it the month a file really is truncated.
   - Fix: declare one period column per dated file, once, in policy.py:
     - processor and Mastercard detail: `clearing_date`
     - Mastercard summary: `settlement_date`
     - bank statement and ledger: `posting_date`
     - FX rates: `date`

     Check only that column. Keep showing every column's range in the read status.
   - This is the session's own gap-filling (decision 4 below), so it needs Andrés's nod.

2. **A file that cannot be read never triggers the "not reliable" warning; only a truncated one does.**
   - Where: checks.py:95 skips a file with no read status ("an absent file is reported by missing_inputs"), and
     template.html:204 shows the banner only when the coverage check fails.
   - Plant: one bank amount typed `30O000.0`. That is the realistic cousin of a format change, such as a thousands
     separator or a renamed column. The whole bank statement is then unread. The result:
     - bank balance 0.00, cash unreconciled 1,547,965.55
     - 30 `ledger_entry_unmatched` rows assigned to Accounting and 24 `settlement_not_debited` rows assigned to
       Treasury, all built from the file's absence
     - no "not reliable" banner
   - What the page does show: a top line "Input not supplied, not estimated: bank (…)". The file was supplied; it was
     damaged.
   - This goes against Andrés's words of 2026-10-14: "the validations we run should also say that something happened
     with a file". The worse case gets the weaker warning.
   - The 54 phantom rows themselves are accepted behaviour ("leave them as they are"); this finding is about the
     warning only.
   - Fix, one line: count a dated file as failing the coverage check when it was not read (no status, or zero rows),
     so the banner fires. Reword the notice to "Input missing or unreadable, not estimated".

## Minor

1. The per-file status sorts the treasury email dates as text. The manifest and the page show first "Fri 2 Oct 2026
   12:10" and last "Wed 30 Sep 2026 17:30" (inputs.py:126-128; the email parser gives `date` as a string). It is
   visible in the Input files table. Fix: parse the date, or leave the text inputs' dates out.
2. `settlement_amount_diff` is still unsigned (recon.py:237 `abs(gap)`). The plan asks that amount differences show
   signed, and names two directions only. A CFO cannot tell whether the bank took more or less than Mastercard
   reported. Fix: sign it bank minus Mastercard; the owner, Mastercard, stays.
3. In a crossing pair, the `ledger_amount_diff` row is aged from the bank date even when that date is in October
   (recon.py:276, `b.date`). In the 399,000 case the crossing row is 3 working days old and its difference row is 2.
   Fix: age it from the earlier date.
4. The balance figure still re-filters the ledger (report.py:164-170). This was asked for in the last two rounds; the
   test checks outputs only.
5. The Input files table lists only the files declared in `policy.INPUT_FILES`. The missing processor invoice, the one
   absent input on the real data, is not in it; only the top notice names it.
6. The type label "Posted in October, move into September" hard-codes the months (template.html:130). Use "Posted
   after the period, move into the period", or build the label from the period dates.
7. This was here before this round, but a CFO will see it: `settlement_not_debited` 2-Oct, 33,163.52, owner Treasury,
   needs explanation. It is an October settlement whose debit (5-Oct) is after the bank file ends. Leg 2 applies no
   period filter to the summary, the same pattern that was fixed for leg 3's October leftovers. Check whether the spec
   intends it.

## Decisions without Andrés (gap-filling, judged)

1. **`ledger_posted_late` gets no proposed entry; the type label carries the action ("Posted in October, move into
   September").** Defensible, and it keeps E01–E11. The consequence Andrés should know: the 1110 balance after the
   proposed entries leaves the late posting out. With the 465 fee booked 1-Oct, September's bank charges stay 465
   short in every "after" column. The label is a type name doing the job of an action text, and its months are
   hard-coded (Minor 6). **Andrés confirms.**
2. **A ledger-first crossing that is not funding → `bank_not_yet_posted`, timing, Treasury.** Defensible. It clears
   when the bank posts, and Treasury watches the bank. One could argue for Accounting: a settlement debit booked on
   30-Sep before the bank took it is usually a manual, early posting, which is the accountant's to confirm. A one-line
   yes/no for Andrés.
3. **The missing file's sender owns `input_missing`; customers and checklist → Finance Ops; treasury email →
   Treasury.** Right. It is per file, not per type, so "Finance Ops owns no type" still holds. On the real data the
   only missing input is the processor invoice, owned by Processor.
4. **Coverage = a dated file's rows reach the first and last working day of September; results still produced, with
   a banner. The implementer applied this to every date column.**
   - The session's rule is right.
   - The implementer's reading is **too strict**, and it would fail realistic files (Material 1).
   - Skipping unreadable files is **wrong** against Andrés's intent (Material 2).
   - Andrés should confirm "one period column per file".
5. **A crossing row carries the matched part, signed like the item.** Right as accounting:
   - When the September side is larger, the matched part is the late posting (or the money in transit) and the rest
     is an amount error. Together they explain the September cash difference: 53,000.00 + 986.40 = 53,986.40.
   - When the September side is smaller, the September cash difference is the September side only. The amount error
     lives in the October books: 399,000 in transit, −1,000 to correct.
   - The plants confirm both directions, and cash ties in each.
6. **Implementer choices:**
   - `funding_in_transit` is aged from the September side: right.
   - `settlement_amount_diff` is still unsigned: wrong against the plan's general rule, minor (Minor 2).
   - The owner of `usd_conversion_error` is Mastercard only when Mastercard's own conversion is off and the
     processor's is not; otherwise Processor. Right. It follows the plan, and the PX10000601 and planted +3.00 cases
     both give Mastercard.
   - The short `TYPE`/`CHECK` names are fine. They are the same objects, so nothing is declared twice, and the guard
     still bans the literal strings.

## Can a CFO read the exceptions page?

Mostly yes for "what happened" and "who acts":
- Each row shows a plain type label (e.g. "Bad network reference", "Funding in transit", "Duplicate bank debit").
- The "Who resolves" column holds one of four names.
- The new summary sentence says every difference has a type and an owner.

Where it falls short:
- **No "what to do" text per row.** "Month cut-off — Accounting" does not say that Accounting only confirms it
  clears in October. "In the ledger, bank not yet posted — Treasury" does not say "confirm the bank posts it".
- **The key column is an internal id** (PX…, BS…, MJ-…). The CFO needs the drill-down to know which transaction it
  is.
- **Data-issue rows show 0.00 amounts.** That is correct but looks odd next to a label like "Bad network reference".
- **"Escalates: Yes" on 121 rows,** 95 of them FX differences of under a dollar or so (36 escalating rows are under
  USD 5). A CFO will read that as noise. This follows the ageing policy, not this round.

## What Andrés should look at in the Chrome demo

- **Summary, Input files table:**
  - The treasury email shows first 2-Oct and last 30-Sep (Minor 1).
  - The bank statement has two date columns, each checked on its own (Material 1).
  - The processor invoice is absent from the table (Minor 5).
- **Summary:** the sentence "Every difference has a type and an owner", and the "Unexplained, USD 0.00" card. No
  banner on the real data.
- **Exceptions, filtered on Who resolves:** Processor 252, Accounting 7, Treasury 4, Mastercard 0. Is a programme
  where the processor owns 96% of the rows what he wants to show?
- **The row "Settlement not yet debited 2026-10-02 — Treasury" (33,163.52):** is that a September problem (Minor 7)?
- **Download "exceptions with notes":** the headers are now `who_resolves` and `owner_note`.
- **Ask what the page shows if the bank file arrives damaged:** today, a "not supplied" notice, 54 phantom rows and
  no "not reliable" banner (Material 2).

Plants: a throwaway script
(throwaway; planted data in `review3/plants/`, damaged-bank output in `review3/out_bank_damaged/`).
