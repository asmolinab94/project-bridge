# Findings — what breaks the September reconciliation (brief B-2026-10-14-01)

> Reader: whoever works the scope or the tool, in fresh context. Produced by a read-only agent on 2026-10-14.
> **Verified by the main session with its own code**: processor Sep net 912,453.49 (3,117 rows), Mastercard Sep net
> 896,853.32 (3,109), daily summary = detail, duplicate bank reference BNK324320124, 105 empty references, ledger
> balances at 30-Sep (all equal), bank balance 30-Sep 1,147,965.55, the processor entry for 24-Sep missing. Pending:
> Andrés's hand check on a sample of rows.
> Added by the session: account 3900 "Other net assets / equity (plug)" (+258,362.63) is in the opening balances, not
> in the account map and has no movements; it is the opening balancing figure and must appear in the balances table.

## Headline figures
- Processor minus Mastercard (net, Sep): 15,600.17, fully explained, residual 0.00:
  sign flips 2,502.45 + different amount 737.29 + stale BRL rate 751.93 + duplicates 3,593.63
  + processor only 9,127.92 − Mastercard only 2,041.36 + month cut-off 928.31.
- Mastercard daily summary = detail on all 24 days. Bank debits: all agree except the duplicate.
- Account 2105 (payable to Mastercard) closes with a DEBIT balance of 70,588.66; it should be a credit of ~45,572.30.
  Gap 116,160.96 = missing 24-Sep entry (44,884.41) + 30-Sep entry dated 1-Oct (45,331.47)
  + duplicate debit (40,616.94) − net processor errors (14,671.86).

## Leg 1 — processor vs Mastercard
- Matching: normalise the reference (strip spaces/hyphens, upper-case, `MC` + 13 digits): 45 recovered.
  105 empty (60 CLEARED, 25 AUTHORIZED, 20 DECLINED). The 60 CLEARED match 1:1 on
  last 4 + currency + local amount + clearing date (e.g. PX10000145, PX10000185, PX10000196).
- No rounding differences: in the clean pairs everything is identical to the cent.
- Sign flips (purchase at the processor, refund at MC), 4 rows, net 2,502.45: PX10000177, PX10001607,
  PX10001739, PX10002743.
- Different amount, 8 rows, net 737.29: PX10000027, PX10000470, PX10000893, PX10001251, PX10001314, PX10002115
  (difference 253.05), PX10002342, PX10002558.
- Stale BRL rate: 95 rows from 21 and 22-Sep at 5.339 (the 18-Sep rate) instead of 5.5526 / 5.5209; net 751.93;
  overcharge to customers 762.72. Range PX10001897–PX10002203.
- Processor duplicates, 6, net 3,593.63: PX10000849, PX10001294, PX10001450, PX10002140, PX10002274,
  PX10002668 (three of them on a different day from the original).
- Processor only, 3 large BRL rows, net 9,127.92: PX10000159, PX10000598, PX10001003 (cause not proven).
- Mastercard only with Sep clearing, 5 rows, net 2,041.36: MC4775958122250, MC3722033624945,
  MC9205438259111, MC7993584471775, MC5392856109846.
- Cut-off: 4 rows Sep at the processor / Oct at MC, net 928.31: PX10002962, PX10002963, PX10003115, PX10003116
  (three with an authorisation date after clearing: data issue).
- 45 uncleared rows with no reference or clearing; 20 AUTHORIZED older than a week (6,040.43). Not in the ledger.

## Leg 2 — Mastercard vs bridge account
- Rule: debit on the next business day, 7-Sep a holiday. Everything agrees except BS0018 (21-Sep, 40,616.94), a
  duplicate of BS0016. The 2-Oct settlement (33,163.52) falls on 5-Oct: timing.
- Bank narratives use inconsistent dates; match on amount + next business day.

## Leg 3 — bridge account and 2105 vs the ledger
- The processor entry for 24-Sep is missing (net 44,884.41). The 30-Sep PF posted on 1-Oct (net 45,331.47).
- 400,000 pre-funding: manual entry on 30-Sep, the bank credits it on 1-Oct (BS0032). The only ledger–bank difference
  at 30-Sep.
- Mastercard invoice 8,412.30 posted in October with no accrual in September.
- 12,500 in suspense (BS0022) belongs to C029 according to Customer Success; the MT103 support is missing.
- C030 for 3,100: does not exist in any file.

## Proposed entries (proposal only)
1. Missing 24-Sep entry: Dr 1210 45,488.83; Dr 5100 122.69 / Cr 4100 727.11; Cr 2105 44,884.41 — Controller.
2. Re-date the 30-Sep PF to 30-Sep with reversal in Oct (45,331.47) — Controller.
3. Duplicate debit: Dr 1250 / Cr 2105 40,616.94 — Controller.
4. C029 suspense: Dr 2900 / Cr 1210 12,500 when the MT103 arrives — Controller.
5. Accrue the invoice: Dr 5100 / Cr 2150 8,412.30, reversal in Oct — standard.
6. Processor errors (6a–6f above), each balanced against 1210/2105/4100/5100 — standard; 6e (processor only)
   conditional on processor evidence.
- No entry: pre-funding (cash reconciliation item), month cut-off (already in Sep, per policy), hanging
  authorisations, C030.
- Balances after: 1210 4,309,799.60; 1250 40,616.94; 2105 −45,572.30; 2150 −8,412.30; 2900 0; 4100 −14,828.29;
  5100 11,603.17; rest unchanged.

## Traps not mentioned in the emails
- 2105 with a debit balance; the 24 and 30-Sep entries; processor errors flowing untouched into the ledger.
- The Controller posted a 400,000 entry herself: the policy requires CFO approval from 100,000 and a preparer
  different from the approver (inferred from the email).
- Close task T12 (accrue the processor invoice) has no amount in the data.
- Open items older than 5 business days at 5-Oct (duplicate 10 days, suspense 8): escalate to the Controller.

## Notes for designing the tool
- Use decimals, not floats. Filter `status = CLEARED`. Do not infer the sign from `txn_type`.
- Card last 4 digits repeat (7640 on two tokens): check the fuzzy match is unique.
- Key for processor entries: `reference` (PROC-YYYYMMDD), not the posting date.
- Calendar with the 7-Sep holiday. `close_checklist.csv` has CRLF line endings.
