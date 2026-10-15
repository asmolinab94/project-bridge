# Project Bridge — PRD-lite

*Andrés Molina · draft 2026-10-14, updated 2026-10-15 · long version; the submitted PRD is the one-page version*

## Problem

September card money sits in four records that should agree and do not: the processor ledger, Mastercard clearing,
the USD bridge account and the GL. Today they are reconciled by hand in spreadsheets at month-end, so a missing feed
or a duplicate debit is found weeks late, when it is expensive to unwind. In this month's data the Mastercard payable
(2105) closes September with a **debit** balance of USD 70,588.66 — a liability on the wrong side — because one daily
processor journal never posted, another posted in October, and the bank paid one settlement twice. None of the three
is visible from any single file. Meanwhile the bridge account is funded well beyond what it pays out: USD 1.5M of
funding in, USD 0.96M out in September, ending with 26 business days of cover (`treasury.csv`).

## Users

- **Finance Ops analyst** — runs it daily, works the exceptions, assigns owners.
- **Controller** — reviews reconciliations and approves proposed entries; needs every number traced to a source row.
- **Treasury** — owns bank-side items (duplicate debit, unidentified receipts, prefunding) and decides funding.

## Success measures

1. Every number on screen and in every export carries the source file and row id it came from.
2. The processor–Mastercard difference is explained to zero residual, split into timing, real error and data problem.
3. A gap (a day present in one source and missing in the other) is flagged *before* reconciliation runs.
4. Running it for a new day takes minutes, not a spreadsheet session — the path to daily reconciliation.

## Design: inputs first, then rules, then work

1. **Input contracts.** For each file: its key, cleaning rules (e.g. normalise `network_ref`: trim, upper-case, strip
   spaces and hyphens), duplicate rule and anomaly checks. Only CLEARED processor rows carry money (declined rows
   still hold a USD amount). Bank lines are typed first (Mastercard settlement, Mastercard invoice, bank charges,
   Treasury funding, customer receipt), so the monthly invoice is never mistaken for an unmatched settlement.
2. **Pre-reconciliation checks, shown with their result even when clean.** Per source pair and per day: date present
   on both sides, amount and count tie (Mastercard daily summary vs clearing detail; processor clearing days vs GL
   processor journals; settlement days vs bank debits). Mastercard's own net formula (amount − interchange + scheme
   fee) holds on every line. No full card numbers in any file. Authorizations older than 5 business days, and
   authorization dates after the clearing date, are flagged. A required input that is absent (e.g. the processor's
   September invoice, which the checklist asks to accrue) is reported as missing, never estimated.
3. **Matching rules.** Processor ↔ Mastercard by normalised reference, then by card last-4 + currency + local amount +
   clearing date, verified unique. Every break says which side is missing the transaction, or splits the USD
   difference into amount (local amount differs) and FX (rate differs from the network rate), so each dollar has one
   cause. Mastercard daily net ↔ bank debit on the next US business day (7 Sep holiday). Bridge account and 2105 ↔ GL
   by bank reference and journal reference.
4. **Policy as rules.** Each line of the reconciliation and close policy becomes an explicit, testable rule:
   tolerances (USD 0.05 per transaction, USD 1.00 per day), the USD 250 must-explain threshold, escalation at
   USD 1,000 unexplained or 5 business days open, and approval limits (USD 10k Controller, USD 100k CFO). The policy
   says "net" for approval limits, but a balanced entry nets to zero; we read it as the entry's total debits and say so.
5. **Exception types, each with a default owner, action and message.** E.g. processor duplicate → processor, with a
   pre-written request to reverse; duplicate bank debit → Treasury, with the Mastercard ticket; missing GL feed day →
   Finance Ops, with a proposed journal. The analyst can override owner, status and comment, and export.
6. **Close outputs.** Proposed adjusting entries (balanced, with support, preparer and approver, and the approval level
   policy requires), September 30 balances before and after, cash reconciliation of ledger to bank, and the close
   checklist as a tracker with dependencies and critical path, marking which tasks the tool completes or evidences.
   The Mastercard monthly invoice (USD 8,412.30, only booked as one October total today) is accrued in September
   **line by line**, with a proposal for the Controller: the cross-border assessment (USD 1,862.30) is variable — its
   own sub-account, allocated to cross-border transactions so it lands in customer and country margin — while network
   access, BIN sponsorship and brand/program fees (USD 6,550.00) are fixed program costs, kept below contribution
   margin and not allocated per transaction. Built: four lines, all on 5100 for now, because the chart of accounts has
   no cross-border sub-account; the Controller opens one.
7. **Treasury view.** Daily bridge balance and business days of cover (26.11 at 30 Sep). A suggested weekly
   transfer: five business days of average debit (September average USD 43,973.93) plus a buffer of two standard
   deviations × √5, USD 255,875.54. Treasury decides; the buffer is illustrative until Mastercard's minimum balance and
   the transfer lead time are known. Not built from the first design: netting tomorrow's known debit and the current
   balance into the suggestion.

**FX source:** the Mastercard network rate in `fx_rates_daily.csv`, because policy says customers are billed at the
network rate and the processor must use the same one. Official central-bank rates belong to financial-statement
translation, not to this reconciliation.

## Options considered

| Option | Why not / why |
|---|---|
| Spreadsheet + AI skill | Familiar to finance, but fuzzy matching of 3,000+ rows with dirty references is fragile, and drill-down to source rows is clumsy. |
| A web app framework | Polished, but reviewers must install a Python stack to open it. |
| Agent as the main tool | The reconciliation must be deterministic and repeatable; an agent belongs on top of it, not in place of it. |
| **Chosen: a Python script (standard library only) that builds one self-contained HTML page plus CSV outputs** | Opens with a double click, nothing to install; the logic is plain, testable code; every output row keeps its source id. |

## Scope ledger (updated as the build progresses)

- **In the tool:** input contracts, pre-reconciliation checks, three-way reconciliation, policy rules, exception
  types with owner/action/message, proposed entries (also as an ERP import file marked not approved), balances, cash
  reconciliation, close tracker with owner roles and the people the email thread names, treasury view, and the USD
  each pending action resolves.
- **Left out by design:** posting — nothing is posted; a different person approves.
- **Left out for time (written, not built):** shared state — owner, status and comment live in the analyst's browser
  and are exported to CSV, and production needs a shared store; live connections to the processor, Mastercard, the
  bank, the GL, email and Slack (in the path-to-production note); target balance and the cost of idle cash; margin by
  product, customer and country; two agents for a day-zero close.

## Main risks

- **Fuzzy matches can be wrong.** Mitigation: a fallback match is accepted only when unique, and is labelled as such.
- **Inference dressed up as fact.** Some causes cannot be proven from the data (three processor-only rows; the USD
  3,100 payment a customer reports that appears nowhere). They are marked "unconfirmed", and their entries are
  conditional on evidence.
- **Approval controls cannot be verified from the GL extract.** It has no preparer, approver or approval-status fields,
  so "preparer ≠ approver" and the USD 10k / 100k approval limits cannot be checked for any posted entry — including
  the USD 400,000 manual prefunding entry, which the Controller says she booked herself. ERP roles prevent unauthorised
  approval but do not evidence who approved each entry. Requirement: the extract carries created-by, approved-by,
  approval status and timestamps (NetSuite approval workflow and system notes). The tool leaves preparer and
  approver empty on every entry it proposes, by design: it proposes, people sign; in production they fill from the
  login.
- **The funding suggestion rests on an assumed buffer.** It is shown as illustrative until Treasury supplies the
  minimum balance and transfer lead time.
- **Synthetic, scaled-down data.** Real file formats differ; the input contracts are the part that must be rebuilt.
