# Investigation proposal — what breaks the September reconciliation in Clara's data, and by how much

> Approval type: investigation approval (Andrés's seed, 2026-10-14). What comes back: the brief to the investigator
> and its findings file.

## The question

What concrete differences are there between the processor, Mastercard clearing, the bridge account and the general
ledger in September 2026, what type is each one (timing, real error, data issue), how much does it add up to in USD,
and which rows does it come from?

## Why now

Submission is on Wednesday 2026-10-21 and the actual time is 3 to 4 hours. The scope (Part 0) cannot be decided
without knowing what breaks in the data: if the differences are few and known, a small tool is enough; if there are
data issues that demand fuzzy matching rules, the scope changes.

## Which decision it enables

The scope of Part 0: what kind of tool to build, which exceptions it covers, what gets cut. And it gives the list of
adjusting entries Part 2 has to propose.

## Limits

- **In**: the 13 files in `insumos/datos/` and the brief in `insumos/correo/`. Read-only.
- **Out**: building the tool, writing final entries, any data from any employer or client, anything on the
  internet.
- **Budget**: ≤40 agent steps. If it runs out without a full answer, it delivers what it found and what is missing.

## Already reviewed

The session read the brief, the data dictionary, the policy, the Treasury thread and the Mastercard notice. Leads
already visible (not quantified nor checked against rows): duplicate debit of USD 40,616.94 (BNK324320124),
unidentified receipt of USD 12,500 in suspense (customer C029), a C030 payment of USD 3,100 that does not appear, a
USD 400,000 pre-funding posted on 30-Sep that the bank credits on 1-Oct, a Mastercard invoice of USD 8,412.30 not
accrued in September, and empty or badly formatted `network_ref` values at the processor.
