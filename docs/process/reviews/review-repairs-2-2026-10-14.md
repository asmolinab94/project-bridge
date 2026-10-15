# Fresh review of the repair-review fixes — 54ee3a5..b2673b4

Brief B-2026-10-15-29, fresh-context opus reviewer, read-only. Verdict: **not ready, close** — the code does what the
plan says, and every previous finding is fixed or answered, but one gap in the plan itself leaves a September cash
movement with no exception row and no owner. That goes against Andrés's rule "every difference explained, each with an
owner", and only he can decide the fix. Everything else is minor.

Closure checks:
- (a) Verifier not weakened: `git diff 54ee3a5 b2673b4 -- tests specs` is empty; 209/209 tests pass; no fixture id,
  date or amount appears anywhere in `bridge/` outside `policy.py`, so no test is made vacuous by special-casing.
- (b) The three material findings are fixed; seven of the nine minors are fixed, one is not fixed and one was never
  planned (details below).
- (c) Real data: cash unreconciled 0.00 (ledger 1,547,965.55 − item 400,000.00 − bank 1,147,965.55); 11 entries
  E01–E11; 263 exception rows, none with an empty owner; unexplained 0.00; the page's data equals the CSVs (353 rows
  compared, 0 mismatches); index.html is 2,280,007 bytes; no `http(s)://`, `<link` or `src=` in it.
- (e) Only `bridge/` changed; working tree clean; no remote is configured, so nothing was pushed.

## Material

1. **When a pair crosses the cut-off and its cash effect is not a ledger-first pair of equal amounts, the
   reconciling item gets no exception row (so no owner and no ageing).** recon.py:264-273 adds a row only
   `if ledger_first and e.amount == b.amount`. Plants (copies of the data, scratchpad `review2/scripts/plant.py`):
   - BK-BS0029 booked 1-Oct, bank line 30-Sep: cash shows 0.00 unreconciled, with the item "In the bank, not yet in
     the ledger (BS0029) +53,986.40". Leg 3 raises nothing besides the existing 400,000 funding row. The September
     ledger misses a September bank debit of 53,986.40; nobody owns it, it never ages to escalation, and no entry is
     proposed.
   - The same, with the ledger at 53,000.00: the item is +53,986.40 and the only row is `ledger_amount_diff` 986.40.
   - BK-BS0028 (the 465 fee) booked 1-Oct: item +465.00, no row.
   - Bank fee 465 on 30-Sep, its own entry missing, and an unrelated 3-Oct manual entry of 100 on the same
     reference: the leftover pass pairs them regardless of month (recon.py:252), so the row is `ledger_amount_diff`
     365.00, not `bank_line_unrecorded` 465.00, and cash still shows 0.00.
   - TR-20260930 at 399,000 (ledger first, amounts differ): cash ties, the row is `ledger_amount_diff` 1,000.00, and
     the 399,000 in transit has no timing row. This is lower stakes, because the 1,000 row carries both sources and
     an owner.

   Why it matters: a bank-first item is not normal timing. The bank is right and the September books are late, so
   standard bank-reconciliation practice calls for a September adjusting entry. The tool reports it as a quiet
   reconciling item and the cash check passes. The implementer followed the plan: the plan names the item and its
   wording, the verifier test fixes `LEFTOVERS = []` (tests/test_golden.py:936-949), and the plan names no type. So
   this is a plan gap. It does not occur in the case data (the only cross-cut-off pair is TRF0930, ledger first,
   equal amounts).

   Fix, for Andrés to decide: every reconciling item gets an exception row. Bank-first would get a type such as
   "bank movement posted late in the ledger", owner Accounting / Treasury, with an action to post it in September.
   Ledger-first with different amounts would also get its in-transit row. Also restrict the leftover pass
   (recon.py:252) to a mate in the same month, or cross the cut-off only when no same-month mate exists. A new type
   changes the closed type list in the plan, so this goes back through the plan, with a test that plants the bank
   first.

## Previous review, finding by finding

- In-transit across the cut-off, both directions, signed: **fixed.** BK-BS0027 on 28-Sep gives no item and cash
  0.00. BK-BS0033 on 1-Oct gives no item and cash 0.00. BS0031 posted 30-Sep gives item −44,643.99 and cash 0.00.
  The mirror case (BS0029 1-Oct/30-Sep) gives item +53,986.40 and cash 0.00, but no row (Material 1).
- October leftovers in September: **fixed.** Deleting BK-BS0033's entry, or deleting the BS0033 bank line, raises
  nothing and cash shows 0.00. A 5-Oct unmatched manual entry also raises nothing.
- Leftovers too narrow: **fixed.**
  - Duplicate BK-BS0028 (X copy): cash −465.00, explained by `ledger_entry_unmatched` 465.00 (owner Accounting /
    Treasury), and the cash check fails, as it should for a real error.
  - Two bank lines against one entry (BK-BS0016 dropped, BK-BS0018 at 40,626.94): cash 40,606.94, explained by
    `ledger_amount_diff` 10.00 on BS0016 plus `bank_line_unrecorded` 40,616.94 on BS0018, whose owner is the
    duplicate's.
  - 399,000: cash 0.00, item 399,000.00, row 1,000.00.
- Minors:
  - Duplicate counted twice as unexplained: fixed (no type is unexplained any more; both rows are kept, as planned).
  - Merchant country label: fixed (template.html, the new `BASIS_LABEL`).
  - Card separators: fixed.
  - Bank balance taken in file order: fixed (close.py:157).
  - Type-codes paragraph: current.
  - Literals and check names: fixed.
  - je_id grouping and bank amount computed twice: fixed (`entries` built once in `_leg3`; the bank amount only in
    `_pair_cash`).
  - **Balance figure re-filters the ledger: not fixed.** report.py:151-157 `_ledger_rows` still re-selects lines by
    account and date instead of reusing `_balances`' sources, which the plan asked for.
  - checks.py card-number attribute list against its whole-file list: unchanged; it was not in the plan's list.

## Minor

1. The "exceptions with notes" download has two columns both headed `owner`: the computed one from the data, and the
   user's own note (template.html:316-320). This is the exact collision the plan avoided with the on-page label "Who
   resolves". Fix: head them `who_resolves` and `owner_note`.
2. The page never says "every difference has a type and an owner", which the plan requires. The summary still shows
   a bare "Unexplained, USD 0.00" card (template.html:337).
3. Any ledger-first pair of equal amounts is typed `funding_in_transit`, owner Treasury. With BS0031 posted 30-Sep, a
   Mastercard settlement debit appears as "funding in transit" (recon.py:271-273). The type should follow the bank
   line's kind, or use a neutral "in transit" name.
4. The key of `ledger_entry_unmatched` is the reference, not the entry id (recon.py:263). With the BK-BS0028X
   duplicate, the row reads "FEE0930", the same key as the original entry's bank line. Use `e.key` (the je_id).
5. `ledger_amount_diff` reports the absolute gap. For a pair inside September, the reader cannot tell which way it
   moves cash. For example, the two-against-one plant's 40,606.94 is 40,616.94 − 10.00, but both rows show positive
   figures.
6. The owner is set in two places: by default in `_difference` (recon.py:77), then overwritten after the fact for
   duplicates in `reconcile` (recon.py:334-337). This is acceptable, but it is the second expression of owner
   assignment.
7. Small leftovers:
   - `policy.CASH_CHECK` survives alongside `policy.CHECK.cash_reconciled`.
   - report.py:238 uses a check name (`policy.CHECK.missing_inputs`) as a manifest key, coupling two unrelated names
     by coincidence.
   - recon.py:281 builds a second reference-to-bank-line lookup (the suspense rows), where a repeated reference keeps
     the last line.
   - Lines of 121-147 characters were added at checks.py:102-113 and recon.py:13-14 and 239-263.

## Decisions without Andrés (the implementer's gap-filling, judged)

1. Bank-first pair: item but no row. **Wrong against the decision log** (Material 1). It follows the plan's text,
   though, so Andrés decides the type and owner.
2. `ledger_amount_diff` raised when either side is on or before 30-Sep; the in-transit item only when the pair
   crosses the cut-off; item = ledger September effect − bank September effect; an all-October pair raises nothing.
   **Right.** The plants confirm the arithmetic in every direction. One gap: ledger-first with different amounts
   gets no timing row (Material 1, last bullet).
3. Candidates are any entry with non-zero net on 1110, any source; pairing by reference, then date and je_id (the
   original matches, the X copy is the leftover). **Right and deterministic.** The weak spot is that the leftover
   pass ignores the month (Material 1, the 465/100 plant).
4. Owners the plan left open:
   - processor_entry_misdated and suspense_pending_payer → Accounting / Treasury; funding_in_transit and
     settlement_not_debited → Treasury. **Defensible.** But the plan's default for timing types was "existing owner
     text or Finance Ops", and there is no existing owner text, so these four depart from the default: Andrés
     confirms.
   - month_cutoff and the data-issue types → Finance Ops. **Defensible**, but Finance Ops now owns 131 of 263 rows
     (105 bad references, 22 stale authorisations). Bad references and stale authorisations are arguably the
     processor's to fix.
   - Rounding → no owner. **Right** (the plan settled it).
   - Leg-1 `unexplained` → Processor and Mastercard: this owner is the **plan's**, not the implementer's.
   - The type still literally named "unexplained": **an inconsistency.** It does not occur on the real data, but if
     it ever does, the page shows a row typed "Unexplained", with an owner, next to a card "Unexplained, USD 0.00".
     Relabelling it (for example "USD differs, all else equal") is Andrés's call.
5. `controller_action` = every real-error type, derived from the class map. **Right**: it matches the plan, and
   processor_only and mastercard_only are already real errors.

## What Andrés should look at in the Chrome demo

- Exceptions tab: the "Who resolves" column on every row, and the Finance Ops share. Is that the owner split he
  wants?
- Download "exceptions with notes" and open it: two `owner` columns (Minor 1).
- Summary: the "Unexplained, USD 0.00" card with no sentence saying every difference has a type and an owner
  (Minor 2).
- Cash panel: the single item "In the ledger, not yet in the bank (BS0032) 400,000.00". Ask what would happen if the
  bank had been first (Material 1); there is nothing on the page to show it.
- A merchant-country row, to see the "(merchant country)" label.

Plants: a throwaway script
(throwaway; copies in `review2/plants/`).
