# Project Bridge — PRD-lite

*Andrés Molina · 2026-10-15 · Part 0 of the Clara Finance Engineer case*

**Problem.** September card money sits in four records that should agree and do not: processor, Mastercard clearing,
the USD bridge account and the ledger. Reconciled by hand at month-end, breaks surface late. This month
the Mastercard payable (2105) closes with a **debit** of USD 70,588.66, a liability on the wrong side: one daily
processor entry never posted, another posted in October, and the bank paid one settlement twice. No single file
shows it.

**Users.** Finance Ops runs it and works the exceptions; the Controller approves entries and needs every number
traced to a source row; Treasury owns settlement, cash and funding.

**Success measures** (baseline → target)

- Figures traceable to a source file and row: spreadsheets with no row link → 100 % on screen and in exports.
- Processor–Mastercard difference: USD 15,600.17 to explain by hand → USD 0.00 residual, split into timing, real
  error and data issue.
- A missing feed day: found on working day 3 (T02 still in progress) → flagged before reconciling, next business day.
- Reconciliations ready: working day 5, the Controller's deadline → working day 1, on the path to daily (target).

**Options considered**

- *Spreadsheet + AI skill:* fuzzy matching 3,000+ dirty rows is fragile. *Web app:* the reviewer installs a Python
  stack. *Agent as the main tool:* the reconciliation must be deterministic; an agent belongs on top.
- **Chosen: a standard-library Python script → one self-contained page + CSVs.** Opens with a double click; plain,
  tested logic; every row keeps its source id.

**Built beyond the reconciliation.** The Mastercard invoice accrued line by line; a Treasury view with days of
coverage and an illustrative weekly transfer; an ERP import file marked not approved; close tasks with the owner
role and, where the email thread names one, the person.

**Left out.** *Cut:* shared notes (they live in the analyst's browser) and posting (never: people approve and post).
*Written, not built:* live connections to sources, email and Slack; margin by customer and country; two agents for a
day-zero close, one answering questions with citations, one proposing rules with their tests for the Controller.

**Risks**

- *Fuzzy matches can be wrong:* accepted only when unique, and labelled. *Inference dressed as fact:* unprovable
  causes are marked unconfirmed; their entries wait for evidence.
- *Approval limits:* the policy says "net", but a balanced entry nets to zero; we use total debits. *No preparer or
  approver in the ledger extract:* posted entries cannot be checked. *Synthetic data:* rebuild the input contracts.
