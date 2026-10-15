# Fresh review of the third repair round — 606f6ce..7a2bd18

Brief B-2026-10-15-35, fresh-context opus reviewer, read-only. **Verdict: not ready, close.** Every finding of the third
repair review is fixed. The verifier is not weakened, apart from one coverage gap. The real data still ties. Two things
stop sign-off, and both are about the new owner and action columns, not the money:

- If the close checklist is readable but a task it should have is renamed, missing, or has a blank owner, the "Clara
  owner" column goes blank on most rows. No check fails and no banner shows.
- The action sentence for the duplicate bank debit tells the reader to book the Mastercard credit when it arrives. The
  tool proposes an entry that books a receivable now (40,616.94 on the real data). A CFO who follows the row skips the
  entry.

Both fixes are small. The second one rewords a sentence the plan quotes word for word, so Andrés has to approve the new
text.

## Closure checks

**(a) Verifier not weakened: yes, with one coverage gap.**
- 306/306 tests pass at 7a2bd18.
- `git diff 3f41821 7a2bd18 -- tests` is empty.
- Every assertion changed between 1870b3f and 3f41821 follows from the plan block "Readings after the third repair
  review":
  - **Owners.** `owner` becomes `who_fixes`, `clara_owner` and `action`. The exact fixer table is pinned (Accounting is
    gone; Finance Ops fixes every ledger correction; Mastercard fixes the duplicate debit). The Clara owner is checked
    against the checklist's `owner_role` and its cited row. A copy of the checklist with T05's owner changed to
    "Payments Ops" is followed. An unreadable checklist leaves the Clara owner empty.
  - **Leg 2.** The 2-Oct `settlement_not_debited` (33,163.52) test is replaced by "October days leave leg 2". That
    test also requires the 1-Oct day and its debit BS0033 to be gone, and the only open leg-2 row to be BS0018. The
    pre-check `settlements_vs_debits` goes from failing with 1 to passing with 0. This is the plan's "Leg 2 is
    September's".
  - **Dropping `settlement_not_debited` from the not-escalating list** is justified, because the list iterates over
    case-data rows and the type no longer occurs there. The side effect: no test anywhere now produces a
    `settlement_not_debited` row. Its class, ageing, Clara task (T06) and action are untested; only the fixer table pins
    its fixer. See Minor 1. The code is right today: my plant (BS0031 deleted) gives one row, 30-Sep, 44,643.99, 3
    working days, not escalating, Treasury / Treasury (T06).
  - **The crossing pair's `ledger_amount_diff`** is now aged from the September side (30-Sep, 3 working days) instead
    of 1-Oct, 2. That is the plan's minor.
  - **The new signed settlement test** expects −1.20 (bank minus Mastercard).
- No case-data figure changed. 40,616.94, 53,986.40, 465.00, 400,000.00 and 0.00 are the same. Only the 2-Oct row was
  removed, as planned.
- No fixture special-casing. Outside policy.py, `bridge/` contains no planted line id, transaction id, reference,
  October date or task id.
- One stale test is kept alive by production code: tests:1490 still reads `policy.OWNER_OF`, so the implementer kept an
  alias (decision 1).

**(b) Findings of the third repair review: all fixed.** Plants are in `review4/scripts/plant.py`, with outputs in
`review4/outs/`.

| Previous finding | Plant | Result | Status |
|---|---|---|---|
| Material 1: coverage read every date column | Mastercard detail settled the next working day | Coverage passes. `summary_vs_detail` still fails on 25 days, but that is the plant's own inconsistency (Minor 8). | fixed |
| Material 2: unreadable file gave no warning | Bank amount typed `30O000.0` | Coverage fails and names the bank file. The banner text includes "missing or unreadable". The input-files table says "No, missing or unreadable". The 54 phantom rows remain, as Andrés accepted. | fixed |
| (same family) | Bank truncated before 28-Sep; summary shifted a month back | Coverage fails in both | fixed |
| Late posting left September short | 465 fee booked 1-Oct | New entry E12 "Move BK-BS0028 into September: post it on 30-Sep and reverse the 01-Oct posting in October", Dr 6150 / Cr 1110 465.00, standard approval. After corrections: 6150 = 465.00 and 1110 = 1,547,965.55, equal to the case data. | fixed |
| Minor 3: 399,000 ageing | TR-20260930 at 399,000 | `ledger_amount_diff` −1,000.00, 3 working days (it was 2); `funding_in_transit` 399,000.00; cash 0.00 | fixed |
| Minor 2: settlement difference unsigned | Mastercard 9-Sep net raised by 5.00 | `settlement_amount_diff` BS0009 −5.00 | fixed |
| Minor 1: email dates sorted as text | — | `sent_on` first 2026-09-21, last 2026-10-02 | fixed |
| Minor 4: balance figure re-filtered the ledger | — | report.py `_ledger_rows` now walks `_balances`' cited sources | fixed |
| Minor 5: processor invoice missing from the input-files table | — | Listed, status `missing` | fixed |
| Minor 6: months hard-coded in the template | — | Label now "Posted after the period end, move it back"; a test bans month names | fixed |
| Minor 7: 2-Oct settlement in September's exceptions | — | Gone. Leg 2 takes summary days on or before 30-Sep | fixed |
| Two rules written twice (period filter; check name in the page) | — | `policy.by_period_end` is used everywhere; the check name and the "read" status reach the page as data | fixed |

**(c) Real data: passes.**
- Cash: unreconciled 0.00 = ledger 1,547,965.55 − item 400,000.00 − bank 1,147,965.55.
- 11 entries, E01–E11.
- 262 exception rows. The previous 263 less the 2-Oct row.
- Who fixes / Clara owner (task):
  - 252 rows Processor / Finance Ops (T05): the leg-1 types. The missing processor invoice is the exception here:
    Processor / Finance Ops, through T12 instead of T05.
  - 7 rows Finance Ops / Finance Ops:
    - month cut-off ×4 (T05)
    - processor entry missing and processor entry misdated (T02)
    - invoice not accrued (T11)
  - 1 row Mastercard / Treasury: duplicate debit (T06).
  - 1 row Treasury / Treasury: funding in transit (T07).
  - 1 row Treasury / "Treasury / AR": suspense (T09).
- Each matches the plan's mapping. Every row cites exactly one checklist row, and that row's `owner_role` equals the
  Clara owner: 0 mismatches.
- No "Accounting" anywhere.
- The page's data equals the CSVs: 353 rows, 0 mismatches. The page's manifest equals `run_manifest.json`.
- `index.html` is 2,355,676 bytes, with no `http(s)://`, `<link` or `src=`.

**(e) Code standards: good, with three notes.**
- Each commit touches only its own area:
  - 7a2bd18: seven files under `bridge/`
  - 3f41821: `tests/` only
  - 606f6ce: the plan only
- The working tree is clean. No remote is configured, so nothing was pushed.
- The owner fields are each set once. `who_fixes`, `action` and `task` are set when the row is built; `clara_owner` is
  set in one final pass (decision 2). The syntax-tree guard now covers all four names.
- Three notes:
  - The same 11 leg-1 types are written twice in policy.py: once as the Processor list in `FIXER_OF` (lines 179-181)
    and once as `_LEG1_TYPES` (line 190) (Minor 6).
  - `OWNER_OF = FIXER_OF` (policy.py:188) exists only for one stale test.
  - Appending the checklist row to every difference's sources also puts it in every proposed entry's evidence. E01–E12
    all cite `close_checklist.csv:N` as support (Minor 7).
- Comment density is at the file's level.

## Material

1. **A readable checklist that lacks a mapped task blanks "Clara owner" silently.**
   - Where: recon.py `_with_clara_owner` returns the row unchanged when `checklist.get(d.task)` finds nothing. The same
     happens when the task's `owner_role` cell is empty. No check reads the result.
   - Plant: T05 renamed to T05A in the checklist (a task inserted and the ids renumbered, or a typo). Result:
     - 255 of 262 rows have an empty Clara owner.
     - Every pre-check that passes on the case data still passes.
     - No banner.
   - Why it is realistic: the checklist is Clara's living document, edited every month. The tool reads task ids that
     somebody else maintains. The plan covers only an unreadable checklist ("input_missing already says why"). It does
     not cover a readable one that is missing a task.
   - What the CFO sees: a "Clara owner" column that is blank for 97% of rows, with no reason given. That breaks Andrés's
     rule that someone at Clara answers for every difference.
   - Fix: one pre-check. Every task in `TASK_OF` and `INPUT_SENDERS` exists in the checklist with a non-empty
     `owner_role`. If not, the check fails and names the missing tasks, and the page shows the reason. Add one planted
     test.

2. **The duplicate-debit action contradicts the entry the tool proposes.**
   - Where: policy.py `ACTION_OF["bank_duplicate_debit"]`, "Follow the Mastercard credit for the duplicate (ticket in
     the treasury email) and book it when received". E03 "Recover the duplicate bank debit BS0018" proposes Dr 1250
     receivable / Cr 2105, 40,616.94, Controller approval, in September.
   - Real data: this is the only leg-2 row and the largest real error a CFO will open. The row says "book it when
     received", so the reader waits for October. E03 says book a receivable now. If the row is followed, 2105 stays
     40,616.94 off at 30-Sep.
   - The sentence is the plan's own example, copied word for word, and the verifier pins it. So it was faithfully
     encoded, but it is wrong against the entries the tool produces.
   - Fix (Andrés approves the wording): "Post the proposed receivable from Mastercard now; follow the Mastercard credit
     (ticket in the treasury email) and clear the receivable when it arrives". The unrecorded half inherits it.

## Minor

1. **No test produces a `settlement_not_debited` row any more** (see check a). Add a plant: delete BS0031, so the 30-Sep
   day has no debit. Expected: 44,643.99, timing, 3 working days, not escalating, Treasury / Treasury (T06), with its
   action. This is the realistic month-end case: a bank file downloaded before the 1-Oct debit.
2. **Leg 2 has an upper bound only.** A summary export that starts earlier than needed gives a phantom. Plant: a 28-Aug
   row, paid 31-Aug and therefore in August's bank file. Result: `settlement_not_debited` 50,000.00, 25 working days,
   escalating, Treasury. It is the mirror of the 2-Oct fix. Fix: a summary day is in leg 2 when its debit day (the next
   working day) falls on or after 1-Sep.
3. **The `settlement_not_debited` action only fits the month-end case.** "Confirm the bank debits the settlement on the
   next working day; no entry" is wrong for a mid-month day whose next working day has passed. In the truncated-bank
   plant, the 25-Sep row is 6 working days old, escalating, and still says "next working day". Fix: "Confirm the debit
   with the bank; if it is past the next working day, raise it with Mastercard".
4. **Action sentences:** the 27 sentences in policy.py, judged against what the tool proposes.
   - **Accurate, and readable in one go (20):**
     - month cut-off
     - processor entry misdated (E02)
     - funding in transit
     - bank not yet posted
     - suspense (E04)
     - processor duplicate (E09)
     - sign flip (E07)
     - amount difference (E08)
     - FX rate difference (E06)
     - processor entry missing (E01)
     - invoice not accrued (E05)
     - settlement amount difference
     - bank line unrecorded
     - ledger entry unmatched
     - ledger amount difference
     - posted late (E12)
     - bad reference
     - authorised after clearing
     - stale authorisation
     - ambiguous match
   - **Wrong against the tool:**
     - Duplicate debit (Material 2).
     - Settlement not debited (Minor 3).
     - Processor-only: "Processor confirms the transactions are valid and waits for Mastercard to settle them". It never
       mentions E10, which is conditional on exactly that confirmation and then gets posted. Add "then post the
       proposed correction".
   - **Unclear on first reading:**
     - **Who posts.** "Processor re-rates … and resends the file; post the proposed correction" (and the same in sign
       flip, amount difference, duplicate, Mastercard-only) switches subject mid-sentence. The processor cannot post
       Clara's ledger. Say "Finance Ops posts the proposed correction".
     - **Risk of correcting twice.** Pairing "resend the file" with "post the correction" risks a double correction if
       the processor's ledger feed picks up the resent file. One clause fixes it: "the resent file corrects the
       processor's records; September is corrected by the entry".
     - **Mastercard-only when the processor is the fixer.** "Processor explains why Mastercard cleared transactions it
       never sent" fits: the processor's file is incomplete. The "then post" half has the same subject problem as
       above.
     - **USD conversion error.** "Whoever converted wrongly…" repeats what the "Who fixes" column already says. Use
       "Re-convert at Mastercard's rate and resend the file".
     - **Missing input.** "Send the missing file **again**" is wrong for the processor invoice, which was never sent.
       Use "Send the file, or a readable copy".
5. **`OWNER_OF = FIXER_OF`** (policy.py:188) keeps a dead name in production code for tests:1490. In the next verifier
   round, change that line to `FIXER_OF` and delete the alias.
6. **The 11 leg-1 types are written twice** in policy.py (the Processor list in `FIXER_OF`, and `_LEG1_TYPES`). Build
   one from the other.
7. **Every proposed entry now cites a checklist row as support**, for example E12's sources end in `close_checklist.csv:8`.
   An auditor reading entry evidence will ask why. Keep the checklist citation on the exception row and leave it out of
   the entry's sources.
8. **The "Mastercard detail settles next working day" plant is only half realistic.** The previous review proposed it,
   and the verifier encoded it. If Mastercard settled T+1, its summary would carry the same date convention. With only
   the detail shifted, `summary_vs_detail` fails on 25 days. The coverage fix is right. The scenario as planted still
   raises a different false alarm. No code change is needed; just do not cite it as "a clean T+1 month passes".
9. **Saved notes are keyed by the row's sources.** This round's added checklist citation changed every row's id, so
   every note saved on an earlier build is orphaned, not only the renamed field. A rerun after a corrected input file
   (new line numbers) does the same in a real close. The storage key is still `bridge.notes.v1`. This was already the
   design; it shows in the demo browser.
10. **The summary sentence "Every difference has a type and an owner."** is now short of the truth: there are two owners
    and an action. Use "Every difference has a type, who fixes it, who at Clara answers for it, and what to do".

## Decisions without Andrés (gap-filling, judged)

1. **`OWNER_OF = FIXER_OF` alias kept so a stale test passes. Defensible as a stopgap, wrong as an end state.** The
   implementer cannot edit tests. The right fix is a one-line test change by the verifier builder, then delete the
   alias. No need for Andrés.
2. **`clara_owner` filled in a final pass with `dataclasses.replace`. Right.** The checklist is read once and each field
   is still set once. The alternative, threading the checklist through every row builder, is more code for nothing. The
   cost is the source-list side effect (Minor 7) and the silent blank (Material 1). No need for Andrés.
3. **An unpaired leg-2 debit is flagged only when posted on or before 30-Sep; a 1-Oct debit still pays the 30-Sep day.
   Right.** It is the mirror of "leg 2 is September's". An unpaired 1-Oct debit can only mean the 30-Sep summary day is
   missing, and the coverage check catches that. The gap is on the other side: there is no lower bound on summary days
   (Minor 2). No need for Andrés.
4. **The late-posting entry is appended at the end of the entry list. Right.** The plan says "ids continue after the
   last one", and the case data keeps E01–E11. No need for Andrés.
   - Consequence worth knowing: when the October entry's amount differs from the September bank line, E12 mirrors the
     October amount. Example: bank 53,000.00 on 30-Sep, ledger 53,986.40 on 1-Oct gives E12 at 53,986.40, plus a
     `ledger_amount_diff` of −986.40 for Finance Ops. The plan's "same accounts and amounts" says exactly this.
5. **Email rows get a parsed `sent_on`; page names are passed as a data block. Right.** It is the smallest change that
   makes dates sort and keeps check names out of the template. No need for Andrés.
6. **Editable note renamed `person`; notes saved under the old key are lost. Defensible.** No one uses the page in
   production. In practice every old note was already orphaned by the id change (Minor 9). No need for Andrés, but
   mention it before the demo if he typed notes earlier.
7. **The 27 action sentences: mostly right.** Two are wrong against the tool (duplicate debit, Material 2; settlement
   not debited, Minor 3), one omits its entry (processor-only), and four are unclear on first reading (Minor 4).
   **Andrés should approve** the duplicate-debit rewording, because it changes a sentence the plan quotes word for word.

## Can a CFO read the exceptions page?

Reading index.html as text, each row now carries the following:
- **What happened:** a plain type label ("Duplicate bank debit", "FX rate differs", "Posted after the period end, move
  it back").
- **Who fixes:** Processor, Mastercard, Finance Ops or Treasury.
- **Clara owner:** read from the checklist.
- **What to do:** one sentence.

So yes for "who" and mostly yes for "what to do". It falls short on four rows or kinds of row:
- **The duplicate-debit row** tells the reader to wait, while the entries tab says to book now (Material 2).
- **The key is still an internal id** (PX…, BS…, BK-…). The CFO needs the source drill-down to know which transaction it
  is.
- **The processor-only row** never mentions E10, so its entry is invisible from the row.
- **"Escalates: Yes"** still sits on many sub-dollar FX rows. That is the ageing policy, not this round.

The table is now 19 columns wide (16 data columns plus 3 note columns), so on a laptop "What to do" sits off to the
right.

## What Andrés should look at in the Chrome demo

- **Exceptions, row "Duplicate bank debit BS0018":** read "What to do" next to entry E03 on the entries tab. Does he
  want "book it when received" or "post the receivable now"? (Material 2)
- **Exceptions, filter Who fixes = Processor:** 252 rows, all with Clara owner "Finance Ops" (T05). Is a single Clara
  owner for 96% of rows what he wants to show?
- **The suspense row:** Clara owner reads "Treasury / AR", exactly as the checklist writes it. Is a two-team owner
  acceptable?
- **Summary:** the sentence "Every difference has a type and an owner" is now behind the two-owner model (Minor 10). On
  the real data there is no banner. The Input files table lists the processor invoice as "No, missing or unreadable",
  and the treasury email shows 2026-09-21 to 2026-10-02.
- **Ask what happens if someone renumbers the checklist:** today, the Clara owner goes blank with no warning
  (Material 1).
- **Download "exceptions with notes":** the columns `who_fixes`, `clara_owner`, `action` and `assigned_person` are
  there. Notes typed on earlier builds are gone.
- **Entries tab:** every entry's evidence cites a checklist row (Minor 7).

Plants: a throwaway script
(throwaway). The planted data is in `review4/plants/` and the outputs are in `review4/outs/`. The renumbered checklist
is `review4/plants/renum` with its output in `review4/outs/renum`. The real-data run is in `review4/out/`.
