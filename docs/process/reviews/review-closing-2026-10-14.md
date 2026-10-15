# Closing review — Project Bridge implementation (T1–T5), HEAD 6749fd6

Brief B-2026-10-15-17, fresh-context opus reviewer, read-only. Verdict: **not ready for sign-off**. Figures are
correct on the case data (108 tests OK; all eleven balances, 11 entries, cash tie re-checked through the real run).

## Verifier weakened?
No material loosening. One unjustified narrowing: the October-leak test was cut from all legs to leg 1 (772ab75);
the wide version still passes at HEAD — restore it.

## Material findings (repair)
1. Leg 3 ties bank lines to the ledger by reference only (recon.py:257-261, :248); `CashRecon.unreconciled`
   (close.py:156) is computed but never written (report.py:65-68). Planted: ledger posts BS0029 at 53,896.40 instead
   of 53,986.40 → no exception, cash off 90.00 silently; deleting the BS0018 posting → cash off 40,616.94 silently
   and E03 proposes the wrong entry. Fix: pair one-to-one by reference and amount; type for an amount difference;
   write `unreconciled` to cash_recon.csv and the page; failing check when non-zero; plant both as tests.
2. A missing/unreadable input is treated as empty and the close proposes entries from the absence
   (inputs.py:137-141; close.py:76-124). Planted: one bad decimal in the ledger → 21 "post missing processor entry"
   proposals; in the processor file → a confirmed CFO-level 911,666.68 entry. Breaks "reported, never estimated".
   Fix: entries depending on a missing input are not proposed (or conditional on it); bad rows reported, not the
   whole file dropped; planted test.
3. Entry title and missing evidence not written (report.py:59-62): CFO sees "E04 proposed-conditional" with no
   description or reason; E02 does not say the 1-Oct posting must be reversed. Fix: columns + page + test.
4. Page exceptions table lacks "Controller action" and "Needs explanation" (template.html:395); Andrés decided the
   first is shown on the page. Fix: columns + filters; check in the Chrome demo.
5. Country/date facets from the first cited row (report.py:118-127) hide real breaks: 24-Sep missing entry tagged
   CO; Mastercard-only shows merchant country unflagged; 30-Sep misdated entry dated 1-Oct. Fix as described.
6. Same rule in two modules (recon.py vs checks.py: next-working-day pairing, clearing day vs entry, stale auth,
   auth-after-clearing and bad references with different scopes already). Fix: checks derive from recon results or
   shared helpers.

## Minor
Thousands separators for display; 2.03 MB page (fonts not subset); tracker says "completes" where "prepares" is
accurate, critical path ignores due day, T09 blocked with empty blocked-by, tracker untested; invoice accrual
proposed even if already accrued; accounts outside the eleven dropped silently; status/class/kind/type literals
outside policy.py (a typo in close.py's `found.get` would silently drop an entry); spec-deviation note lists two
added types, four exist; dead conditional inputs.py:130; unused import checks.py:6.

## Decisions taken by the session/implementers, not by Andrés
The two leg-3 types counting as unexplained (no decision-log entry from Andrés); unpaired settlement debit as
settlement_amount_diff; tracker completes/evidences mapping; critical-path definition; page columns/facets.

## T5b import review
Imports: standard library and package modules only (listed per file in the reviewer's report). No numeric
threshold, tolerance, date or account outside policy.py. Literals outside policy: status codes CLEARED/AUTHORIZED
(recon.py:144,180,233; checks.py:46,96), class codes (recon.py:63,291; report.py:58,88), bank kinds (recon.py:192,276;
checks.py:63; inputs.py:84), type codes in recon.py and close.py:97-114, facet definitions report.py:19-20.

## Checks
(a) fail — paths with no test: leg-3 amount tie, cash unreconciled, close on missing input, page columns/facets,
tracker, double accrual. (b) n/a. (c) pass. (d) pass with evidence required — figures for a CFO and proposed
entries: sign-off must look at cash_recon by hand, E01–E11 vs V6/V7/V7b, E02 reversal, conditional reasons, a run
with one bad input. (e) fail — gaps filled without Andrés listed above.
