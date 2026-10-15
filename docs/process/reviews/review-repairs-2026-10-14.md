# Fresh review of the closing-review repairs — 6749fd6..528d600

Brief B-2026-10-15-25, fresh-context opus reviewer, read-only. Verdict: **not ready, close**. Case-data figures right
(160 tests, cash 0.00 unreconciled, E01–E11, 44 page figures tie, 2.26 MB, no external reference). Verifier not
weakened. Closing-review findings 3, 4, 6 fixed; 1 fixed for both plants; 5 partly (country_basis not shown on page).

## Material (all in recon.py `_pair_cash` 225-270 / close.py cash items)
1. In-transit ignores the cut-off and the sign: any pair with bank date later than ledger date becomes a reconciling
   item, now for bank-feed pairs too, amount abs(). Plants: BK-BS0027 on 28-Sep (both Sep) → phantom item, cash
   -40,663.23; BK-BS0033 1-Oct vs 2-Oct → September item; BS0031 booked 30-Sep → wrong sign; mirror (ledger 1-Oct,
   bank 30-Sep) → no item, 53,986.40 unexplained by any row. Fix: in transit only across 30-Sep, both directions,
   signed debit-positive; plant all four.
2. October leftovers enter September's unexplained total (delete BK-BS0033 → 26,163.36 escalates while cash ties).
   Fix: leftovers dated after 30-Sep are not September exceptions; October-leak test over bank and ledger lines.
3. Leftovers too narrow: bank-feed leftover entry dropped (dup BK-BS0028: cash -465.00, no row); two bank lines vs one
   entry → two whole-amount unrecorded (81,233.88 vs real 40,626.94); ledger_amount_diff across the cut-off loses its
   in-transit item (399,000 transfer → 399,000.00 unreconciled, exception 1,000.00). Fix: flag every leftover entry
   with cash, pair leftovers per reference first, cross-cut-off pair also yields its in-transit item.

## Minor
Duplicate debit counted twice when unposted (explained + unexplained); merchant country unlabelled; summary cards
without separators; bank balance by file order (close.py:157); plan Type-codes paragraph stale; literals "exact",
"normalised", "fuzzy", check names in `_CHECKS`; je_id grouping and bank amount computed twice in recon.py; balance
figure re-filters the ledger (report.py:152-158); checks.py:64 vs :73 attribute lists.

## Decisions without Andrés
Pairing algorithm; bank-feed leftovers unflagged; in-transit on bank-feed pairs; unposted duplicate counted
unexplained; cash_reconciled as a pre-check; flag dates, country_basis, misdated definition; check scopes; misdated
entry September-only; settlements check counts unpaired debits; page layout (separate "By figure" tab), filtered
download; account_unmapped as data issue; accrual/BLOCKED_OUTSIDE/"prepares" wordings; critical path without due days.

Plants: session scratchpad review/plant.py (throwaway).
