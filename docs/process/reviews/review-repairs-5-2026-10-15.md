# Fresh review of the fourth repair round — 3cbf3c2..90c7a00

Brief B-2026-10-15-38, fresh-context opus reviewer, read-only. **Verdict: not ready, close — one small fix.** Every
finding of the fourth repair review is fixed or answered as the plan decided, the verifier is not weakened, and the real
data still ties to the cent. One thing stops sign-off: the new "the feed must not post the resent file again" clause was
applied to every "resend the file" sentence, including the USD conversion error, which has no proposed entry. For that
difference the tool now tells Finance Ops to block the only path that would correct September, and proposes nothing in
its place. No real-data row is affected; a planted processor conversion error shows it.

## Closure checks

**(a) Verifier not weakened: yes.**
- 333/333 tests pass at 90c7a00, run in the repo (306 at 7a2bd18; +27). Working tree clean.
- `git diff --stat 9e5d114 90c7a00 -- tests` is empty. The code commit touches only `bridge/`; the test commit only
  `tests/test_golden.py` and `tests/test_guards.py`; the plan commit only `plan.md`.
- Every removed or changed assertion follows from the plan block "Readings after the fourth repair review":
  - `policy.OWNER_OF` → `policy.FIXER_OF` (tests:1554), plus a new test that the alias is gone. Plan minor.
  - The duplicate-debit example is replaced by Andrés's 2026-10-15 wording. Plan bullet 2, decision log entry of that date.
  - The `fx_rate_diff` example ("…; post the proposed correction") is dropped. Superseded by "Finance Ops posts the
    proposed correction", which the new `ActionSentences` tests encode. Justified.
  - The summary sentence changes to "Every difference has a type, who fixes it, a Clara owner and an action". Plan minor.
  - The pre-check table gains `checklist_tasks_owned: (True, 0)` on the case data.
- The new tests encode the plan, with three weak spots (none hides a defect today):
  - **"Resend the file" test** (tests:1592) only applies to sentences matching `resends? … file`. A sentence reworded to
    "sends a corrected file" escapes it. It also over-applies: it forces the feed clause onto types with no proposed
    entry, which is the material finding below. The plan wrote it that broadly; the test is faithful to the plan.
  - **"Written once" guard** (test_guards:348, threshold 8 shared strings). It catches the duplication it was built for
    (the old lists shared 11). But at threshold 7 it already reports a legitimate pair today (policy.py:153 and :178 share
    7), so the threshold has zero margin: one more leg-1 real-error type makes it fail on a legitimate overlap, and any
    copied list of seven or fewer strings is never caught (for example `CORRECTION_TYPES`, six). Minor 4.
  - **Banner check** (tests:2656) proves the check's name reaches the page and the script reads `names.<key>`, not that
    the banner depends on it. The template reads it in the banner condition (template.html:204-206), and my runs confirm
    the count of failed pre-checks goes 6 → 7 when the checklist is broken. Adequate together with the session's Chrome
    check.
- Plants cover only tasks from the type map (T05, T06), not tasks used only for missing files (T12, T21). See (d).

**(b) Findings of the fourth repair review.** Plants in `review5/scripts/plant.py`, outputs in `review5/outs/`.

| Previous finding | Plant | Result | Status |
|---|---|---|---|
| Material 1: blank Clara owner was silent | T05 renamed T05A | `checklist_tasks_owned` fails, count 1, detail names T05; failed pre-checks 7 (was 6); banner shown. The 255 rows still have a blank Clara owner, as the plan intends: the page now says why. | fixed |
| (same) | T06 owner_role blank | Fails naming T06, source `close_checklist.csv:7`; banner shown | fixed |
| (same) | T12 row deleted (only used for the missing processor invoice) | Fails naming T12; the `input_missing` row's Clara owner is blank, and this time it is announced | fixed |
| (same) | Checklist missing | Fails with the 12 tasks; `missing_inputs` also fails. Two signals for one cause, acceptable | fixed |
| Material 2: duplicate-debit action contradicted E03 | — | "Post the proposed receivable from Mastercard now; follow the Mastercard credit and clear the receivable when it arrives", Andrés's approved text | fixed |
| Minor 1: no test produced `settlement_not_debited` | BS0031 deleted | One row: 30-Sep, 44,643.99, timing, 3 working days, not escalating, Treasury / Treasury, cites the summary row and `close_checklist.csv:7`; `settlements_vs_debits` fails with 1. A test now pins it. | fixed |
| Minor 2: leg 2 had no lower limit | 28-Aug summary day, 50,000.00 | Nothing raised; `settlements_vs_debits` passes with 0 | fixed |
| (lower limit kept the right day) | BS0001 deleted (the 1-Sep debit of the 31-Aug day) | `settlement_not_debited` 31-Aug, 71,243.18 — correct: that debit belongs to September | fixed |
| Minor 3: "next working day" wrong mid-month | same BS0001 plant | Now "Confirm the bank debits the settlement; no entry". On a row 24 working days old and escalating it is still thin (Minor 2). The plan chose the shorter wording. | fixed as planned |
| Minor 4: action sentences | — | Subject switch gone ("Finance Ops posts…"); processor-only names its conditional entry; feed clause added; "Whoever" gone; "again" gone from input_missing | fixed, with the material finding below |
| Minor 5: `OWNER_OF` alias | — | Deleted; test asserts it is gone | fixed |
| Minor 6: leg-1 list written twice | — | Written once (policy.py:178); the processor list is built from it | fixed |
| Minor 7: entries cited the checklist | — | 0 of 38 entry lines cite it; all 262 exception rows still do | fixed |
| Minor 8: half-realistic T+1 plant | — | Not a code item | n/a |
| Minor 9: notes lost on rerun | — | Not done, by decision; goes to the path-to-production note | accepted |
| Minor 10: summary sentence | — | Updated on the page | fixed |

**(c) Real data: passes.**
- Suite green (333). Cash: unreconciled 0.00 = ledger 1,547,965.55 − item 400,000.00 − bank 1,147,965.55.
- Eight output files. 11 distinct entry ids, E01–E11.
- Against the run at 7a2bd18, field by field:
  - `exceptions.csv`: same 262 rows, same order. Only the `action` column changed, on 126 rows: fx rate diff 95, amount
    diff 8, processor duplicate 6, mastercard only 5, sign flip 4, processor only 3, auth after clearing 3, duplicate
    debit 1, missing input 1. Every change is a planned rewording. Who fixes / Clara owner unchanged: 252 Processor /
    Finance Ops, 7 Finance Ops / Finance Ops, 1 Mastercard / Treasury, 1 Treasury / Treasury, 1 Treasury /
    "Treasury / AR".
  - `proposed_entries.csv`: same 38 lines, same accounts and amounts; only `src` changed, and the only difference is the
    removed checklist citation (asserted line by line).
  - `checks.csv`: one new row, `checklist_tasks_owned` passed, 0. Failed pre-checks still 6. No banner.
  - `balances.csv`, `cash_recon.csv`, `close_tracker.csv`, and `run_manifest.json` (except its timestamp): identical.
- `index.html` 2,368,737 bytes, no `http(s)://`, `<link` or `src=`.

**(d) Gap-filling decisions, judged one by one.**

Verifier author:
1. **The check covers the type map; plants only test type-map tasks. Acceptable, with a gap.** The implementer also
   covers the missing-file tasks (T01–T04, T10, T12, T21); no test pins that, so a regression that drops it passes
   unnoticed. My T12 plant shows it matters: without it, the missing-invoice row's owner goes blank silently. Minor 3.
2. **"Fails naming T05" read as a whole word. Right.** `\bT05\b` does not match "T05A", so a detail that only echoes the
   renamed id fails the test. The count assertion of 1 stops a detail that names every task.
3. **Banner asserted through the names block and the script key. Adequate.** Indirect (see a), but the template's
   banner condition reads it, and Chrome and my runs confirm the 6 → 7 count.
4. **28-Aug rule as "expected debit day on or after 1-Sep and summary day on or before 30-Sep". Right.** The plan says
   "if debited, debited on/after 1-Sep". Since a summary day only pairs with a debit on its expected day, the two
   readings give the same result, and the code's reading also covers the day that was never debited. Both plants
   behave.
5. **"Type with a proposed entry" limited to the six processor-fixed types. Right reading of the plan** ("never as the
   processor's"). The other entry types (E01, E02, E05, E12) are Finance Ops' own, so their imperative already has the
   right subject. Two gaps: the list is copied into the tests rather than read from `policy.CORRECTION_TYPES`, so a
   seventh correction type (the fix below) is not covered; and the duplicate-debit row's fixer is Mastercard while
   Treasury or Finance Ops posts E03 — Andrés approved that wording, so leave it.
6. **Duplicate-debit sentence pinned without the trailing period. Right.** No `ACTION_OF` sentence ends with a period;
   the words match the decision log exactly.

Implementer:
7. **`checklist_tasks_owned` also covers missing-file tasks. Right.** Those tasks are the Clara owner of the
   `input_missing` rows, so the plan's "never silent" needs them. Side effect: the banner fires if the checklist drops
   T12 even when the invoice arrived and no row is blank. The banner text names the cause, so this is acceptable.
8. **Processor-only sentence "…; Finance Ops posts the proposed conditional entry once the processor confirms".
   Right.** It matches E10: status proposed-conditional, waiting for "Processor confirmation that these transactions are
   valid and not yet settled by Mastercard".
9. **Entries stop citing the checklist; exception rows still do. Right.** Done as a filter when the entry gathers its
   sources (close.py:95-96) rather than keeping the task citation in a separate field. One line, no new structure.

**Every action sentence, read as a Finance Ops analyst at Clara.**
- Clear, correct, and consistent with the entries: month cut-off, misdated processor entry (E02), funding in transit,
  bank not yet posted, suspense (E04), duplicate debit (E03, Andrés's text), processor entry missing (E01), invoice not
  accrued (E05), settlement amount difference, bank line unrecorded, ledger entry unmatched, ledger amount difference,
  posted late, bad reference, stale authorisation, ambiguous match, missing input, unmapped account, processor only
  (E10), Mastercard only (E11).
- Correct but slow to read: the four with the feed clause and an entry (fx rate, sign flip, amount, processor duplicate:
  E06–E09). "(the feed must not post the resent file again)" sits inside the processor's half, so it reads like the
  processor's job, and "again" is odd because the resent file was never posted. Minor 1.
- Wrong against the tool: **USD conversion error** (Material 1). Noise: **auth after clearing** carries the feed clause
  but moves no money.
- Thin: **settlement not debited** on an old, escalating row (Minor 2).

**(e) Code standards: good, with two notes.**
- New rules declared once: the check's task set is computed from `TASK_OF` and `INPUT_SENDERS` (checks.py:105), the
  feed clause is one constant (policy.py:206), the leg-2 window is one condition (recon.py:237), the page reads the
  check name as data (report.py:267).
- Notes:
  - "month_cutoff is Finance Ops'" is now stated three times: the filter `if t != "month_cutoff"` (policy.py:182), the
    Finance Ops list (:186), and the comment at :180. Building the Processor list as `_LEG1_TYPES` minus the Finance Ops
    list would say it once. Minor 5.
  - The checklist citation is added to every difference (recon.py:376) and then removed again for entries
    (close.py:95-96). Acceptable at this size.
- Comment density is at the file's level. No new structure.

## Material

1. **The USD conversion error is told to block its own correction, and no entry replaces it.**
   - Where: policy.py:231, `"usd_conversion_error": "Re-convert at Mastercard's rate and resend the file (%s)" %
     _FEED_NOT_AGAIN`. `usd_conversion_error` is not in `CORRECTION_TYPES` (policy.py:87), so close.py:125 proposes no
     entry for it.
   - Failure: plant PX10000700's processor amount_usd +1,200.00 (the existing test plant). The row reads Processor /
     Finance Ops, real error, escalating, "Re-convert at Mastercard's rate and resend the file (the feed must not post the
     resent file again)". Entries are still E01–E11; none touches that transaction. In a real month the ledger feed
     posted the processor's overstated 1,200.00. The tool says not to let the corrected file through and proposes no
     correction, so September closes 1,200.00 overstated. A careful analyst who follows the row does exactly that.
   - Why it happened: the plan's rule ("a 'resend the file' sentence says the corrected file must not be posted again by
     the feed") was written for the types that pair a resend with a proposed entry, where reposting would correct twice.
     The plan and the test applied it to every resend sentence. The same clause on auth after clearing is harmless noise.
   - Fix (session can decide; it does not change the real data, which has no such row): add `usd_conversion_error` to
     `CORRECTION_TYPES` when the processor is the fixer. The existing mechanism (reverse what the feed overstated, processor
     minus Mastercard) gives the correction. The sentence then reads like the other four: "Processor re-converts at
     Mastercard's rate and resends the file (…); Finance Ops posts the proposed correction". Drop the feed clause from
     auth after clearing. Add one plant test (PX10000700 +1,200 → one correction entry of 1,200.00), and make
     `PROCESSOR_ENTRY_TYPES` in the tests include it. Edge to note: when both sides converted wrongly (the PX10000601
     plant), processor minus Mastercard is not the processor's own error; correct by the processor's local amount at
     Mastercard's rate instead, or leave that case to the analyst.

## Minor

1. **The feed clause reads as the processor's job.** "Processor re-rates … and resends the file (the feed must not post
   the resent file again); Finance Ops posts the proposed correction". Clearer: "Processor re-rates at Mastercard's
   rate and resends the file; Finance Ops posts the proposed correction and does not let the feed post the resent
   file". One constant changes.
2. **"Confirm the bank debits the settlement; no entry" on an old row.** BS0001 plant: 31-Aug, 71,243.18, 24 working
   days, escalating, still "confirm". The plan chose the short wording; a second clause ("if the debit is late, raise it
   with the bank and Mastercard") would fit both cases.
3. **No test pins the missing-file tasks in `checklist_tasks_owned`.** Add a plant: T12 row deleted → fails naming T12.
4. **The repeated-list guard threshold has no margin** (test_guards:348). Today's legitimate overlap is 7, the
   threshold 8. Lowering it is not possible without exemptions. Either record the known pair as an exemption and lower
   the threshold, or accept the guard as a check for this one duplication.
5. **"month_cutoff is Finance Ops'" said three times** (policy.py:180-186). See (e).
6. **`PROCESSOR_ENTRY_TYPES` in the tests copies `policy.CORRECTION_TYPES`** (tests:1448). Independent on purpose, but it
   will not follow a seventh correction type. If Material 1 is fixed, update it in the same verifier round.

## What Andrés should look at in the Chrome demo

- Entries tab: no checklist row in any entry's evidence. Exceptions: the "What to do" column for fx rate diff (95 rows)
  now carries the feed clause; read one and decide whether it is clear enough (Minor 1).
- Duplicate debit row BS0018: the sentence is his approved text, next to E03.
- Only if asked how the tool handles a renumbered checklist: the banner and the failed pre-check name the missing task.

Plants and runs, throwaway: scripts in
a scratch folder,
planted data in `…/review5/plants/`, outputs in `…/review5/outs/`, real-data runs in `…/review5/out_new/` (90c7a00) and
`…/review5/out_old/` (7a2bd18).
