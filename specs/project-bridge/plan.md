# Plan — Project Bridge

> Reader: whoever works a task of this plan, in fresh context. Read `spec.md` (same folder) first; this plan adds
> *how*, never *what*. If this plan and the spec disagree, the spec wins and the disagreement is a finding.
> Environment: system Python 3.9.6, standard library only — no `match`, no `X | Y` type unions, no third-party imports.

## Approach

One linear pipeline, each stage a pure function over the previous stage's output, so every golden figure can be
asserted on an in-memory object without touching the HTML:

```
inputs.load(data_dir) ─► checks.run(inputs) ─┐
        │                                    ├─► report.write(result, out_dir)
        └─► recon.reconcile(inputs) ─► close.build(inputs, recon) ─┘
```

`bridge/__init__.py` exposes one entry point, `build(data_dir) -> Result`, that chains the stages; `run.py` is a thin
CLI over `build` + `report.write`. Tests call `build` for figures and `run.py` (subprocess) for output-file checks.

## Alternatives considered

| Choice | Alternative | Why this one |
|---|---|---|
| Plain dataclasses + lists of rows | A small in-memory SQL (sqlite3) | Matching rules are row logic, not joins; sqlite would force float/text conversions on every amount (I6) |
| One `build()` entry point | Tests import each module's internals | Tests pinned to internals break on every refactor; one contract keeps the verifier stable (D16) |
| HTML from a template with one embedded JSON blob | Generating HTML strings in Python | Keeps markup reviewable in one file (`template.html`); data is injected once, as text decimals |
| Type and class codes as string constants in `policy.py` | Enums per module | One declaration (I7); strings serialise straight to CSV/JSON |

## Contracts

These names are the interface the verifier (`tests/test_golden.py`) is written against. Changing one is a change to
the verifier and goes back through review.

**Row.** Every loaded row is a `dict` of the CSV's columns (amount columns as `Decimal`, dates as `datetime.date`)
plus `src: tuple` = `(file_name, line_number)`, header = line 1. Text sources: `(file_name, "<date> <subject>")` for
the Treasury email, `(file_name, "<line item>")` for the invoice. Missing input: `("missing", "<what>")`.

**`inputs.load(data_dir) -> Inputs`** — fields: `processor`, `mc_detail`, `mc_summary`, `bank`, `gl_lines`,
`gl_opening`, `fx`, `customers`, `checklist` (lists of rows); `invoice_lines` (rows from the fee notice);
`treasury_email` (list of messages: `date`, `subject`, `body`, `src`); `missing` (list of `(what, src)`); `fingerprints`
(`{file_name: sha256_hex}` taken at load). Processor rows carry `ref_norm` (normalised reference or `None`),
`ref_status` (`"exact" | "normalised" | "empty" | "invalid"`) and `net`. Bank rows carry `kind` (one of
`policy.BANK_KINDS`).

**`recon.reconcile(inputs) -> Recon`** — fields:
- `matches`: list of `Match(processor_row, mc_row, method)`; `method` in `"exact" | "normalised" | "fuzzy"`.
- `differences`: list of `Difference` with fields `leg` (1, 2 or 3), `type` (a code from `policy.DIFF_TYPES`),
  `cls` (`policy.CLASS_OF[type]`: `"timing" | "real_error" | "data_issue"`), `gross: Decimal`, `net: Decimal`
  (leg 1: September processor side minus September Mastercard side — a Mastercard amount clearing in October counts
  as zero, so a month cut-off pair carries the processor side's full net), `srcs: list`, `age_wd: int` (working days
  at `policy.CUTOFF_DATE`, counting from the day after the origin date up to and including the cut-off date, skipping
  weekends and `policy.HOLIDAYS`), `requires_explanation: bool`, `escalates: bool` (by age only: `age_wd >
  policy.ESCALATE_AGE_WD`, money differences only), `key` (txn_id, network_ref, bank line_id or je reference that
  identifies it).
- `unexplained_total: Decimal` — the policy's aggregate rule ("unexplained aggregate above USD 1,000 escalates"):
  the sum of `abs(gross)` of money differences with no classified cause; `unexplained_escalates = unexplained_total >
  policy.ESCALATE_UNEXPLAINED`. "No classified cause" means the type is in `policy.UNEXPLAINED_TYPES` (see the
  second- and third-review readings). It is a separate figure, never folded into `escalates`.
- **Leg-1 universe** (one predicate, `policy.in_leg1_period`): processor `CLEARED` rows clearing in September,
  Mastercard rows clearing in September, and Mastercard rows clearing in October only when matched to a September
  processor row (month cut-off). Unmatched October Mastercard rows are out of the period — they are October's
  reconciliation, not exceptions.
- **Rounding**: a matched pair whose difference is ≤ `policy.TOL_TXN` gets type `rounding`, class `auto_cleared`; it
  is recorded and counted in `leg1_by_type` (so the residual stays zero) but is not an exception. None occurs in this
  data.
- `leg1_by_type`: `{type: Decimal}` sum of `net` of leg-1 money differences (data-issue flags carry no money and are
  excluded from the sum).

**`close.build(inputs, recon) -> Close`** — fields:
- `entries`: list of `Entry` with `id`, `title`, `lines` (list of `(account, debit, credit)` as `Decimal`, each line
  with debit ≥ 0, credit ≥ 0 and exactly one of them non-zero), `line_tags` (dict line index → tag, used by E8 for
  the variable/fixed classification; empty until then), `status`
  (`"proposed" | "proposed-conditional"`), `missing_evidence` (text or `None`), `preparer` and `approver` (always
  empty strings: the tool cannot fill them, which is how it discharges I11 — people fill them outside the tool), `approval_level` (`"standard" | "controller" | "cfo"`), `total_debits`, `srcs`.
- `balances`: `{account: {"before", "after_confirmed", "after_all", "src"}}` for the eleven accounts, debit positive.
- `cash_recon`: ledger balance, reconciling items (each with `src`), bank balance.
- `tracker`: rows of `close_checklist.csv` plus `blocked_by`, `on_critical_path`, `tool_evidence`.

**Readings fixed by the verifier (T0, commit 2f6b6f1)** — the tests assert these; the implementation follows them:
- `cash_recon` has `ledger_balance`, `reconciling_items` (each with `amount` and `src`) and `bank_balance`.
- Processor and Mastercard totals are not a field: tests sum the loaded `CLEARED` rows, and check that every match and
  every money difference points at a `CLEARED` row.
- Entries are identified by their lines, not by `id`. The closed list yields exactly 11 entries (items 1–5 of spec E4
  plus six processor-correction entries), exactly 2 of them `proposed-conditional` (C029 suspense, processor only).
- Leg-3 difference keys: `PROC-20260924` (missing entry) and `PROC-20260930` (misdated). The pending 2-Oct settlement
  is found by type `settlement_not_debited` and amount.
- Sign of `gross`/`net` is defined for leg 1 only (processor minus Mastercard); legs 2 and 3 are compared in absolute
  value. `requires_explanation` uses `abs(gross) >= policy.EXPLAIN_THRESHOLD`.
- `run_manifest.json` must contain the SHA-256 of each of the 9 CSVs and the two text inputs; its layout is free.
- "Money modules" = every `.py` in `bridge/` plus `run.py`; `policy.py` writes amounts as `Decimal("…")`, never float
  literals.
- Known limits of the static guards: a float created at run time (`json.load`, `/` on ints) is not caught; the card
  number detector looks at unbroken digit strings only. The reviewer weighs whether these need a runtime check.

**Output formats fixed by the verifier (commit 40262d9)**:
- `src` cell: sources joined by `;`, each `file:line`, `file.txt:<label>` or `missing:<what>`; the line must exist in
  that input file (header excluded).
- `balances.csv`: `account, before, after_confirmed, after_all, src`.
- `proposed_entries.csv`: one row per entry line — `entry_id, account, debit, credit, status, approval_level, preparer,
  approver, src`.
- Amounts in every CSV are plain decimal text (`-45572.30`), never float formatting.
- `exceptions.csv`: `leg, type, cls, key, gross, net, age_wd, requires_explanation, escalates, controller_action, src`;
  one row per difference except `auto_cleared` ones; booleans written `true`/`false`.
- `checks.csv`: `name, passed, count, detail, src`.
- `cash_recon.csv`: `line, amount, src`, where `line` is `ledger_balance`, `reconciling_item` or `bank_balance`.
- Pre-check meanings: `statuses` counts the 45 rows kept out of money (25 authorised, 20 declined) and passes;
  `settlements_vs_debits` counts the settlement side; `summary_vs_detail` treats the 31-Aug summary with no detail as a
  failure; `stale_authorisations` counts authorised rows older than 5 working days from the authorisation date (22 —
  the findings file's "20 older than a week" is a different measure).
- An auto-cleared `rounding` item is not an open item and never escalates by age.

**Second-review readings (fresh-context re-review of 40262d9)**:
- Type `unexplained` (class `real_error`): a matched leg-1 pair whose USD differs while local amount, sign and rate
  agree. It is counted in `leg1_by_type` like any other type. `fx_rate_diff` requires the two rates to differ.
- `unexplained_total` = sum of `abs(gross)` of differences whose type is in `policy.UNEXPLAINED_TYPES`. That set
  holds `unexplained` and, since the third review, `settlement_amount_diff` (Andrés, 2026-10-14: processor-only and
  Mastercard-only are explained; a bank debit differing from the daily net is not). On this data the total is 0.00
  and nothing escalates by the aggregate rule.
- `Difference.controller_action: bool` — explained is not resolved (Andrés, 2026-10-14: «Están explicadas pero
  necesitan acción de la Controller… explicadas es la mitad, hay que solucionarlas» [They are explained but need the
  Controller's action… explained is half of it, they have to be solved]). True for every difference whose type is in
  `policy.CONTROLLER_ACTION_TYPES` = {`processor_only`, `mastercard_only`}, regardless of age; shown on the page and in
  `exceptions.csv`.
- Two reference-less processor rows that share last 4, currency, local amount and clearing date with one Mastercard
  row are an `ambiguous_match`, not duplicates — duplicates are decided only by a shared reference. Uniqueness is
  checked from both sides.
- `src` also accepts `file:*` (the whole file — for a check that passed or a figure computed over a file) and
  `file:a-b` (a line range) — in `checks.csv` only (third-review reading).
- `auto_cleared` items (within tolerance) may be recorded on any leg; they are never exceptions.
- Zero amounts are written `0.00`, never an empty cell. Manifest timestamps are ISO 8601 date-times.
- `close.build` and `checks.run` must not raise on edited data (extra rows, summary no longer matching detail): they
  report, never crash.
- Deviation from the spec, recorded: `auto_cleared` is a fourth class beside the spec's three; it holds no exception.
  Two real-error types are added to the spec's list: `unexplained` (second review) and `settlement_amount_diff`
  (third review; Andrés, 2026-10-14, «Si porfa» [Yes please] to counting it as unexplained).
  Fonts stay embedded (Andrés chose Clara's typography); system fonts are the fallback.

**Third-review readings (fresh-context re-review of d306499)** — they pin values the tests assert. Where a later
block of readings and earlier text disagree, the later block wins and the earlier text is a finding to fix.
- Leg 2 compares the Mastercard **summary file**'s daily net with the bank debit (the detail rows are checked against
  the summary by the `summary_vs_detail` pre-check, not by leg 2). A debit that differs from the summary net by more
  than `policy.TOL_DAY` is type `settlement_amount_diff`, class `real_error`, key the bank `line_id`, `gross` the
  absolute difference. Pairing: summary day D ↔ the settlement debit posted on the next working day after D, with
  bank duplicates (BS0018) set aside before pairing. It is in `policy.UNEXPLAINED_TYPES` beside `unexplained`: like leg 1's `unexplained`, it is a
  difference with no identified driver. A settlement with no debit at all stays `settlement_not_debited`.
- Origin date for ageing on leg 1: the processor row's own clearing date; for `mastercard_only`, the Mastercard row's
  clearing date. Never the counterpart's date.
- `ref_status` is decided on the raw cell, before any trimming: a reference with surrounding spaces is `normalised`,
  not `exact` (11 such rows).
- `reference_bad` flags only rows of the leg-1 universe that are `CLEARED` and whose `ref_status` is not `exact`
  (105 = 60 empty + 45 normalised). Authorised and declined rows are never flagged for their empty reference.
- The `references` pre-check counts the same 105 rows: `ref_status` not `exact` on cleared rows.
- Rows of an `ambiguous_match` still carry their money: the processor rows as `processor_only`, the Mastercard row as
  `mastercard_only`, beside the `ambiguous_match` data-issue flag, so the leg-1 residual stays 0.00.
- Data-issue flags carry `gross = net = 0.00`, `age_wd = 0`, `escalates = false`, and the leg of the row they flag (1
  for processor and Mastercard rows). `input_missing` is leg 3 with the same zero values.
- Empty dates (authorised and declined rows have no `clearing_date`) load as `None`.
- The policy-literal guard flags comparisons such as `wd >= 5` or `page > 5`: a working-day count or a weekday cut-off
  comes from `policy` (e.g. `policy.WEEKEND_FROM`), and unrelated names avoid `age`/`wd` rather than contorting the code.
- `build()`'s result holds no `float` anywhere; a golden test walks it.
- Whole-file (`file:*`) and line-range (`file:a-b`) sources are allowed only in `checks.csv`; every other CSV cites
  single lines. In `inputs.missing`, each entry is `(what, ("missing", what))` — the two `what` are the same text, and
  a `missing:<what>` source must name one of them.
- An `ambiguous_match` flag is keyed by a Mastercard `network_ref`: the one row the processor candidates share, or,
  when one processor row has several Mastercard candidates, the lowest of their `network_ref`s.
- Planted test cases may move more than one figure: the 1.20 daily-tolerance case shifts Mastercard detail, which also
  makes PX10000601 and PX10000722 leg-1 `unexplained` pairs; the tests account for both.

**Readings found during implementation (T2, ffee369)**:
- Leg 3 never drops an unpaired line in silence (spec E3: "bank lines against bank entries; manual entries"). A bank
  line on the bridge account with no ledger entry is type `bank_line_unrecorded`; a manual ledger entry on the bridge
  account with no bank line, and no other leg-3 type, is `ledger_entry_unmatched`. Both are class `real_error`, keyed
  by the bank `line_id` / the entry's reference, `gross` the absolute bridge-cash amount of that line or entry
  (as for `funding_in_transit`), aged from that line's or entry's date, and both are in
  `policy.UNEXPLAINED_TYPES` (no identified driver, like `settlement_amount_diff`). Neither occurs in this data.
- A settlement debit that pairs with no summary day is also `settlement_amount_diff` (gross: the whole debit).

**Closing-review readings (repairs after 6749fd6; review record `review-closing-2026-10-14.md`)** — later block, so it
wins over earlier text.
- **Leg 3 pairs by reference and amount, one to one.** A ledger candidate is one journal entry (lines grouped by
  `je_id`) that has a bridge-cash line; its amount is `debit_usd - credit_usd` on `bridge_cash`. A bank line's amount
  is `credit_usd - debit_usd`. Each bank line pairs with at most one candidate of the same reference and equal amount,
  and each candidate with at most one bank line, both sides taken in (`posting_date`, `line_id` / `je_id`) order.
  A pair whose bank date is later than the ledger date stays `funding_in_transit` (TRF0930, 400,000.00).
- What is left over after pairing: for one reference, exactly one bank line and one candidate with different amounts
  → type `ledger_amount_diff`, class `real_error`, key the bank `line_id`, `gross` the absolute difference, aged from
  the bank date, sources both; in `policy.UNEXPLAINED_TYPES` (Andrés, 2026-10-14, «Si» [Yes]: same reasoning as
  `settlement_amount_diff` — an amount differs and nothing says why). Any other leftover bank line →
  `bank_line_unrecorded` (whole amount); any other leftover manual candidate → `ledger_entry_unmatched`, as before.
  Planted cases: the ledger posts BS0029 at 53,896.40 instead of 53,986.40 (both lines of `BK-BS0029`) →
  `ledger_amount_diff` BS0029, gross 90.00, age 3, no explanation required, no escalation; the two lines of
  `BK-BS0018` deleted → `bank_line_unrecorded` BS0018, gross 40,616.94, age 10, escalates, requires explanation (the
  leg-2 `bank_duplicate_debit` on BS0018 stays as well).
- **Duplicate-debit entry follows what the ledger holds** (Andrés, 2026-10-14, «1 sí» [1 yes]). When the duplicate bank line has its
  own ledger posting, the entry is as today: Dr `mc_receivable` / Cr `mc_payable` (move the payable debit into a claim
  on Mastercard). When it has none (it is also `bank_line_unrecorded`), the entry is Dr `mc_receivable` / Cr
  `bridge_cash` (record the debit the bank made as the claim). Planted BK-BS0018 deletion: Dr 1250 / Cr 1110
  40,616.94, and `after_all` for 1110 equals the bank balance plus the funding in transit.
- **Cash reconciliation states what does not tie.** `cash_recon.csv` gets a fourth line kind, `unreconciled`
  (= ledger − reconciling items − bank), always written, 0.00 on the case data; the page shows it under the cash
  figure. A new check `cash_reconciled` (in `policy.CHECKS`) passes only when it is zero; count 0 or 1; sources the
  ledger and bank sources of the cash recon. Planted: 90.00 and 40,616.94 respectively, check failing.
- **Entries say what they are.** `proposed_entries.csv` columns become `entry_id, title, account, debit, credit,
  status, approval_level, missing_evidence, preparer, approver, src`; `missing_evidence` empty when none. The page's
  entries table shows title and missing evidence. E02's title says both actions: post PROC-20260930 on its clearing
  day (30-Sep) and reverse the 1-Oct posting in October.
- **Exceptions page.** The exceptions table shows `controller_action` as "Controller action" and
  `requires_explanation` as "Needs explanation", each with a yes/no filter.
- **Facets come from the difference, not the first cited row.** `Difference` gets `origin: date` — the date ageing
  already counts from (one rule for age and the page date); the page date facet is `origin`. The 30-Sep misdated entry
  is dated 30-Sep. Country: `program_country` of the cited processor row for leg-1 differences that cite one;
  `merchant_country` for `mastercard_only`, with the facet saying it is the merchant country; empty for every
  day-level or account-level item (legs 2 and 3) — the 24-Sep missing entry has no country.
- **One rule, one place for the pre-checks.** `checks.run(inputs, recon, close)`. A check that has a reconciliation
  counterpart counts the counterpart's differences instead of re-deriving them: `clearing_days_vs_entries` ←
  `processor_entry_missing` + `processor_entry_misdated`; `settlements_vs_debits` ← `settlement_not_debited` +
  `settlement_amount_diff`; `stale_authorisations` ← `auth_stale`; `impossible_dates` ← `auth_after_clearing`;
  `references` ← `reference_bad`; `cash_reconciled` ← `close.cash_recon`. Checks without a counterpart
  (`summary_vs_detail`, `net_formula`, `statuses`, `card_numbers`, `missing_inputs`) keep reading the inputs. Scope:
  `auth_after_clearing` is flagged on every processor row with both dates (as the check did), not only the leg-1
  universe. Counts on the case data are unchanged (2, 1, 22, 3, 105).
- **Page by figure** (Andrés, 2026-10-14, decision log). Each figure — each account balance, each cash-recon line,
  each reconciling item, each exception type — shows its total and below it a filterable table of its source rows
  with the input file's own columns, a sum row of the amount column that ties to the total, and a CSV download of
  that table. Thousands separators on the page only; every CSV keeps plain decimals.
- **Page by figure, as data.** The page blob carries `figures`: one per account balance, per cash-recon line, per
  exception type and per proposed entry, each `{"figure", "label", "total", "columns", "rows"}`. Every row has the
  cited input row's own columns (or, for exception types and entries, the row of `exceptions.csv` /
  `proposed_entries.csv`) plus `contribution`, the signed amount it adds to the figure; the contributions sum exactly
  to `total`. Balances: the opening line plus each ledger line up to 30-Sep, contribution debit − credit; cash: the
  same for 1110, each reconciling item, the bank's last September line; exception types: one row per difference,
  contribution `net` on leg 1 and `gross` elsewhere, total = `leg1_by_type` on leg 1; entries: one row per line,
  contribution debit − credit, total 0.00 with the debit total shown beside it. Each figure's table has a filter box,
  a sum row and a CSV download of exactly its rows. Thousands separators appear on the page only.
- Page-figure details settled by the session: a figure id is `<kind>:<key>` (`balance:1110`, `cash:ledger_balance`,
  `cash_item:BS0032`, `exception_type:fx_rate_diff`, `entry:E03`); one figure per reconciling item; the entry's debit
  total sits in the figure header. `account_unmapped` takes the flagged line's posting date as `origin`.
- **Minor repairs.** The program-invoice accrual is proposed only when `invoice_not_accrued` is raised (no double
  accrual when the ledger already holds one). A ledger line on an account outside `policy.ACCOUNTS` is a data-issue
  flag `account_unmapped` (leg 3, key `je_id`), never dropped in silence. A tracker task whose status is `Blocked` with
  no open dependency gets `blocked_by` = `policy.BLOCKED_OUTSIDE` ("outside the checklist"). Tool evidence says
  "prepares" for T05–T07 (the tool prepares the reconciliation; a person signs it). Status, class, bank-kind and type
  literals used in code come from `policy.py`; the policy-literal guard covers them. Dead conditional
  `inputs.py:130` removed. Known limit kept: the critical path ignores due days.
- The October-leak test covers every leg again (narrowed in 772ab75 without a reason; the wide version passes).
- Readings settled after the verifier builder's report (68bd650), by the session:
  - Data-issue flags carry `origin` = the flagged row's own date (clearing date; authorisation date for
    `auth_stale`), so the date filter never hides them; their `age_wd` stays 0.
  - A facet entry is `{"country", "country_basis", "date"}`; `country_basis` is `"program"`, `"merchant"` or `""`.
  - A processor day is misdated when any of its entry lines is posted on another date (the check's reading wins).
  - `settlements_vs_debits` counts every leg-2 settlement difference, unpaired debits included; its detail says
    "settlement days and debits that do not pair".
  - `references` covers the leg-1 universe (September cleared rows): a bad reference on a row of another month is that
    month's matching problem. `impossible_dates` covers the whole file because a date impossibility is wrong in any
    month.
  - The misdated-entry correction keeps only its September lines; reversing the 1-Oct posting is an October action
    named in its title, not lines of the entry.

**Readings after the repair review (review-repairs-2026-10-14.md)** — later block, wins over earlier text.
- **Explained means classified with an owner; resolved is a separate state** (Andrés, 2026-10-14, decision log).
  `policy.UNEXPLAINED_TYPES` is empty; `unexplained_total` stays a reported figure (0.00) and the page says every
  difference has a type and an owner. `controller_action` is true for every `real_error` type and for
  `processor_only`/`mastercard_only`. `policy.OWNER_OF[type]` names who resolves it: bank/ledger types (leg 3:
  `bank_line_unrecorded`, `ledger_entry_unmatched`, `ledger_amount_diff`, `processor_entry_missing`,
  `invoice_not_accrued`) → "Accounting / Treasury"; `bank_duplicate_debit` → "Treasury, refund claim with
  Mastercard"; `settlement_amount_diff`, `mastercard_only` → "Mastercard review"; leg-1 `unexplained`,
  `amount_diff`, `fx_rate_diff`, `sign_flip`, `processor_duplicate`, `processor_only` → "Processor and Mastercard";
  timing and data-issue types → their existing owner text or "Finance Ops". Shown in `exceptions.csv` (column
  `owner`, after `controller_action`) and on the page. Escalation by age is unchanged.
- **In transit only across the cut-off, both directions, signed.** A leg-3 pair is a reconciling item only when one
  side is dated on or before 30-Sep and the other after it: ledger on/before and bank after → "in the ledger, not yet
  in the bank"; bank on/before and ledger after → "in the bank, not yet in the ledger". The amount is how much the pair makes the September ledger exceed the
  September bank: the ledger side's September effect on 1110 minus the bank side's September effect (debit positive,
  so TRF0930 is +400,000.00), and `unreconciled = ledger − Σ items − bank` uses it signed. A pair
  with both sides in the same month is matched, whatever the day gap. Planted (from the review): BK-BS0027 on 28-Sep
  → no item, cash ties; BK-BS0033 on 1-Oct → no item; BS0031's posting on 30-Sep → item −44,643.99 sign-correct,
  cash ties; BK-BS0029 on 1-Oct → item "in the bank, not yet in the ledger" +53,986.40, cash ties.
- **Only September leftovers are September exceptions.** A leftover bank line or ledger entry dated after 30-Sep
  raises nothing; the October-leak test covers bank and ledger lines.
- **Leftovers pair per reference before falling back.** Leftover bank lines and ledger entries (any source with a
  non-zero cash amount, bank feed included) of one reference pair one to one in date order as `ledger_amount_diff`
  (gross the absolute difference); what remains is `bank_line_unrecorded` / `ledger_entry_unmatched`. A
  `ledger_amount_diff` pair that crosses the cut-off also yields its in-transit item for the matched part.
- A bank line flagged `bank_duplicate_debit` and also unrecorded in the ledger keeps both rows: the leg-2
  `bank_duplicate_debit` (the entry Dr 1250 / Cr 1110 is built from it) and the leg-3 `bank_line_unrecorded`, whose
  owner is the duplicate's. Neither counts as unexplained.
- Settled after the verifier builder's report (8feca7e): rounding needs no owner; the owner lives on `Difference`
  (`owner`) and is written to `exceptions.csv`; the page labels it "Who resolves" so it does not collide with the
  user-entered note "Owner"; a cut-off-crossing `ledger_amount_diff` is aged from the bank date like every leg-3
  leftover.
- Minors: the page shows `country_basis` ("merchant country"); summary cards and leg-1-by-type use the display
  format; the 30-Sep bank balance is the last line by (`posting_date`, `line_id`), not file order; reference
  statuses and match methods come from `policy.py`; `_CHECKS` keys come from `policy.CHECKS`; je_id grouping and the
  bank amount are computed once in recon.py; the balance figure reuses `_balances`' sources; the plan's "Type codes"
  paragraph is current.


**Readings after the second repair review (review-repairs-2-2026-10-14.md)** — later block, wins over earlier text.
Scope rule (Andrés, 2026-10-14): realistic cases only, aimed at the ~95% that happen; the session's timeline of what
can go wrong with the files is in the decision log entry of that date.
- **Every cut-off-crossing leg-3 pair gets an exception row, not only an in-transit item.** Bank on/before 30-Sep and
  ledger after → new type `ledger_posted_late` (class `real_error`, owner Accounting, `controller_action`): a
  September bank movement booked in October; the action text says to move the posting into September. No new
  proposed entry (the close stays E01–E11). Ledger on/before and bank after → `funding_in_transit` only when the bank
  line's kind is `funding`; any other kind → new type `bank_not_yet_posted` (class `timing`, owner Treasury). A
  crossing pair with different amounts yields its `ledger_amount_diff` row for the difference and the crossing row
  for the matched part. A crossing row carries the matched part (the smaller amount), signed like the reconciling
  item. When the September side is the larger, the crossing row plus the `ledger_amount_diff` row add up to the item
  (bank 53,986.40 on 30-Sep, ledger 53,000.00 on 1-Oct → crossing row 53,000.00, difference 986.40). When it is the
  smaller, the crossing row is the whole item and the difference is an amount error outside the September cash
  bridge (ledger 399,000.00 on 30-Sep, bank 400,000.00 on 1-Oct → crossing row 399,000.00, difference −1,000.00). Both
  new rows are aged from the September side's date. Planted: BK-BS0029 on 1-Oct → one `ledger_posted_late` row +53,986.40, cash ties; the 465
  fee booked on 1-Oct → one row +465.00; BS0031's posting on 30-Sep → `bank_not_yet_posted` −44,643.99, not funding.
  Case data unchanged: one `funding_in_transit` row (BS0032), 11 entries, cash 0.00.
- **Who resolves is whoever can fix the cause** (Andrés, 2026-10-14). `policy.OWNER_OF`, four owners:
  "Processor" — `fx_rate_diff`, `usd_conversion_error`, `amount_diff`, `sign_flip`, `processor_duplicate`,
  `processor_only`, `mastercard_only`, `reference_bad`, `auth_after_clearing`, `auth_stale`, `ambiguous_match`;
  "Accounting" — `bank_line_unrecorded`, `ledger_entry_unmatched`, `ledger_amount_diff`, `ledger_posted_late`,
  `processor_entry_missing`, `processor_entry_misdated`, `invoice_not_accrued`, `account_unmapped`, `month_cutoff`
  (confirms it clears in October); "Treasury" — `funding_in_transit`, `bank_not_yet_posted`, `settlement_not_debited`,
  `suspense_pending_payer`, `bank_duplicate_debit` (refund claim); "Mastercard" — `settlement_amount_diff`.
  `input_missing` is owned by the missing file's sender, declared once per input in `policy.py` (processor files and
  invoice → Processor; Mastercard files and rates → Mastercard; bank statement → Treasury; ledger files → Accounting;
  customers and checklist → Finance Ops). `rounding` has none. The owner is set in one place, when the row is built;
  the unrecorded half of a duplicate debit takes the duplicate's owner there, not by a later overwrite.
- **Leg-1 `unexplained` is renamed `usd_conversion_error`** (Andrés: the policy uses Mastercard's rate, so the side
  that is wrong corrects it). Same condition (USD differs beyond `TOL_TXN` while local amount, sign and rate agree);
  owner Processor, unless only Mastercard's own `amount_usd` disagrees with its local amount converted at its own
  rate, then Mastercard. No type, label or page text says "unexplained" except the aggregate figure.
- **Per-file read status.** For each input file the run reports rows read and, for dated files, the first and last
  date; new pre-check `inputs_cover_period` fails for a dated file whose rows do not reach both the first and the
  last working day of September (a truncated or wrong-month file), naming the file. Shown on the page next to the
  pre-checks and in `run_manifest.json`. A failing file still yields results (accepted 2026-10-14); the page says the
  figures are not reliable while it fails. Case data: passes for every file.
- Minors: the "exceptions with notes" download headers are `who_resolves` and `owner_note`; the page states "Every
  difference has a type and an owner" beside the unexplained figure; amount differences show signed (ledger minus
  bank, or processor minus Mastercard); an unmatched ledger entry is labelled by its `je_id`; `policy.CASH_CHECK`
  goes (use `policy.CHECK.cash_reconciled`); the manifest field is not named after a check; the suspense lookup keeps
  every line of a repeated reference; the balance figure reuses `_balances`' sources; the card-number check cites
  every file it reads; lines stay within the file's width.
- Not done, by decision: leftovers stay pairable across months (the review's same-reference entry from another month
  is too rare, Andrés 2026-10-14); comparing one run with the previous one goes to the path-to-production document.


**Readings after the third repair review (review-repairs-3-2026-10-14.md)** — later block, wins over earlier text.
- **Two owners and an action per difference** (Andrés, 2026-10-14). Each row carries `who_fixes`, `clara_owner` and
  `action`; they replace `owner`. Page labels "Who fixes", "Clara owner", "What to do"; the editable note becomes
  "Assigned person" (download header `assigned_person`).
  - `who_fixes` (`policy.FIXER_OF`): "Processor" — `fx_rate_diff`, `usd_conversion_error` (Mastercard when only its
    own conversion is off, as before), `amount_diff`, `sign_flip`, `processor_duplicate`, `processor_only`,
    `mastercard_only`, `reference_bad`, `auth_after_clearing`, `auth_stale`, `ambiguous_match`; "Mastercard" —
    `settlement_amount_diff`, `bank_duplicate_debit` (Mastercard confirmed it and credits it, treasury email of 2
    Oct); "Finance Ops" — every correction that is a ledger entry or a ledger check: `bank_line_unrecorded`,
    `ledger_entry_unmatched`, `ledger_amount_diff`, `ledger_posted_late`, `processor_entry_missing`,
    `processor_entry_misdated`, `invoice_not_accrued`, `account_unmapped`, `month_cutoff`; "Treasury" —
    `funding_in_transit`, `bank_not_yet_posted`, `settlement_not_debited`, `suspense_pending_payer`.
    `input_missing`: the file's sender, as before. "Accounting" is gone: it is not a role in Clara's data.
  - `clara_owner`: the `owner_role` of the close-checklist task that covers the difference, read from
    `close_checklist.csv` at run time and cited to that row in `src` — never typed in code. Type → task, declared
    once in `policy.py`: leg-1 types and `month_cutoff` → T05; `settlement_amount_diff`, `bank_duplicate_debit`,
    `settlement_not_debited` → T06; `bank_line_unrecorded`, `ledger_entry_unmatched`, `ledger_amount_diff`,
    `ledger_posted_late`, `funding_in_transit`, `bank_not_yet_posted`, `account_unmapped` → T07;
    `suspense_pending_payer` → T09; `invoice_not_accrued` → T11; `processor_entry_missing`,
    `processor_entry_misdated` → T02; `input_missing` → the task that receives the file (processor files T01, bank
    T03, Mastercard files and rates T04, ledger files T02, processor invoice T12, customers T10, treasury email T03,
    checklist T21). If the checklist cannot be read, `clara_owner` is empty and `input_missing` already says why.
  - The unrecorded half of a duplicate debit takes the duplicate's fixer, Clara owner and action.
  - `action` (`policy.ACTION_OF`): one plain sentence per type saying what the fixer does, e.g. `month_cutoff` →
    "Confirm it clears in October; no entry"; `bank_duplicate_debit` → "Follow the Mastercard credit for the
    duplicate (ticket in the treasury email) and book it when received"; `fx_rate_diff` → "Processor re-rates at
    Mastercard's rate and resends the file; post the proposed correction". Every type has one; `rounding` none.
- **A late posting gets a September entry.** Each `ledger_posted_late` row yields a proposed entry dated 30-Sep that
  mirrors the October ledger entry's lines (same accounts and amounts), titled to reverse that October `je_id` in
  October — the pattern of the misdated processor entry. Entry ids continue after the last one; the "after
  corrections" balances include it. Case data: none occurs, the close stays E01–E11. Planted: the 465 fee booked
  1-Oct → one entry Dr 6150 / Cr 1110 465.00 on 30-Sep.
- **Coverage reads one period column per file**, declared in `policy.py`: processor and Mastercard detail
  `clearing_date`, Mastercard summary `settlement_date`, bank and ledger lines `posting_date`, rates `date`. A dated
  file that could not be read fails the check; the notice says "missing or unreadable". The processor invoice
  appears in the input-files table as missing.
- **Leg 2 is September's**: a Mastercard summary day is in leg 2 when its `settlement_date` is on or before 30-Sep.
  Case data: the 2-Oct `settlement_not_debited` row (33,163.52) and any 1-Oct day leave the exceptions.
- Minors: `settlement_amount_diff` is signed (bank minus Mastercard); a crossing pair's `ledger_amount_diff` is aged
  from the September side like its crossing row; email dates sort as dates; the balance figure reuses `_balances`'
  sources instead of re-filtering; the September filter is written once; month names and check names reach the page
  as data, not as literals in the template.


**Readings after the fourth repair review (review-repairs-4-2026-10-14.md)** — later block, wins over earlier text.
- **A blank Clara owner is never silent.** New pre-check `checklist_tasks_owned`: every task in the type → task map
  exists in `close_checklist.csv` with a non-empty `owner_role`; it fails naming the missing tasks, and the page shows
  the not-reliable banner while it fails. Planted: T05 renamed T05A → fails naming T05.
- **Action sentences match what the tool proposes** (`policy.ACTION_OF`). `bank_duplicate_debit`: "Post the
  proposed receivable from Mastercard now; follow the Mastercard credit and clear the receivable when it arrives"
  (Andrés, 2026-10-15). A type with a proposed entry names it as Finance Ops' step ("Finance Ops posts the proposed
  correction"), never as the processor's; `processor_only` names its conditional entry; a "resend the file"
  sentence says the corrected file must not be posted again by the feed; `usd_conversion_error` does not restate the
  fixer; `input_missing` says "Send the missing file" (no "again"); `settlement_not_debited` says "Confirm the bank
  debits the settlement" without "next working day".
- **Leg 2 has a lower limit too**: a summary day is in leg 2 when its debit falls in September or it is a September
  day awaiting its debit (`settlement_date` on/before 30-Sep and, if debited, debited on/after 1-Sep). A planted
  28-Aug summary day raises nothing. A test plants BS0031 deleted → one `settlement_not_debited` row 44,643.99,
  timing, not escalating, Treasury / Treasury.
- Minors: the `OWNER_OF` alias goes (its test asserts on `FIXER_OF`); the leg-1 type list is written once; proposed
  entries do not cite the checklist row (only exception rows do); the page summary says "Every difference has a
  type, who fixes it, a Clara owner and an action".
- Not done, by decision: notes saved by the analyst are keyed by source rows and are lost on a rerun with a corrected
  file — written up in the path-to-production note with run-to-run comparison.

- Deviation from the spec, corrected: the real-error types added to the spec's list are `unexplained`,
  `settlement_amount_diff`, `bank_line_unrecorded`, `ledger_entry_unmatched` and `ledger_amount_diff`; one
  data-issue type, `account_unmapped`.

**`checks.run(inputs) -> list[Check]`** — `Check(name, passed: bool, count: int, detail, srcs)`; every check returns a
result even when clean. The check names are declared once, in `policy.CHECKS`: `summary_vs_detail` (Mastercard daily
summary vs detail per settlement day, amount and count), `clearing_days_vs_entries` (each processor clearing day has
its ledger entry on that date), `settlements_vs_debits` (each settlement has its bank debit on the next working day),
`net_formula` (Mastercard net = amount − interchange + scheme fee), `statuses` (only `CLEARED` carries money; counts
per status), `stale_authorisations` (authorised older than 5 working days), `impossible_dates` (authorisation after
clearing), `references` (`ref_status` not `exact` on cleared rows: empty, normalised or invalid), `card_numbers` (no 13–19 digit string after
normalising), `missing_inputs` (e.g. the processor invoice).

**`build(data_dir) -> Result`** — `Result(inputs, checks, recon, close)`.

**`run.py --data D --out O`** writes the eight files of spec E5. Every CSV has a `src` column.

**Type codes** (declared once, in `policy.DIFF_TYPES`, with `policy.CLASS_OF`):
timing — `month_cutoff`, `processor_entry_misdated`, `funding_in_transit`, `bank_not_yet_posted`,
`settlement_not_debited`, `suspense_pending_payer`; real_error — `processor_duplicate`, `bank_duplicate_debit`, `sign_flip`, `amount_diff`,
`fx_rate_diff`, `processor_only`, `mastercard_only`, `processor_entry_missing`, `invoice_not_accrued`,
`settlement_amount_diff`, `usd_conversion_error`, `bank_line_unrecorded`, `ledger_entry_unmatched`, `ledger_amount_diff`,
`ledger_posted_late`; data_issue —
`reference_bad`, `auth_after_clearing`, `auth_stale`, `ambiguous_match`, `input_missing`, `account_unmapped`. Plus `rounding`, class `auto_cleared` (not an
exception). Account codes are policy values too: modules use `policy.ACCOUNTS[...]`, never a literal like `"2105"`.

## Changes by file

All files are new, in this repository.

| File | Content |
|---|---|
| `tests/test_golden.py` | E0. V1–V13 as `unittest` cases against `build()` and a `run.py` subprocess into a temp dir; fails loudly (not skips) if `BRIDGE_DATA` is unset. V14 is manual and listed in a docstring only |
| `tests/test_guards.py` | The structural checks (no `float` in money modules, no policy literal outside `policy.py`, no 13–19 digit string in outputs, `src` on every CSV row) written as functions with seeded-violation self-tests, so they are shown to fail before they are trusted |
| `bridge/policy.py` | E1 + E7. Every tolerance, threshold, date, holiday, account, posting rule, type code, class map, bank kind; later the per-type owner/action/message table |
| `bridge/inputs.py` | E2. CSV reading with `Decimal`, `src`, normalisation, bank line typing, fingerprints, missing inputs |
| `bridge/recon.py` | E3. Three legs and classification, in the spec's order |
| `bridge/close.py` | E4 + E8. Closed list of 11 entries (spec E4 items 1–5 plus six processor-correction entries), balances in three columns, cash recon, tracker |
| `bridge/checks.py` | E6. Pre-checks |
| `bridge/treasury.py` | E9. Daily balance, working days of coverage, illustrative weekly transfer |
| `bridge/report.py` | E5. CSV writers, manifest, injection of the JSON blob into the template |
| `bridge/template.html` | Single page: summary, filterable exceptions, drill-down, owner/status/comment in `localStorage` with the blocked-storage warning, CSV export. Clara's colours and type per `clara_caso_finance/MARCA-clara.md` (navy #032257, accent #00E66B), no logo, visible line "Case study by Andrés Molina — not a Clara product". No external reference of any kind (no `http(s)://`, no external `<link>` or `src=`): DM Sans and Inter are embedded as base64 `@font-face` from files kept in `bridge/fonts/` with their OFL licence; if the files are not available, system fonts — never a network link |
| `bridge/__init__.py` | `build()` |
| `run.py` | CLI |
| `README.md` | How to run it and the tests |

## Risks

| Risk | What contains it |
|---|---|
| A golden figure in the verifier is itself wrong | Figures recomputed independently twice already (findings file and the spec teardown); the verifier builder recomputes them a third time with its own throwaway script before writing them down |
| Brand fonts vs "no external dependencies" | Fonts embedded in the file; a guard rejects any external reference in `index.html` |
| `localStorage` blocked on `file://` in some browsers | Spec E5 already requires the warning and export still working; V14 checks it in Chrome |
| Fuzzy matching picks up a last-4 collision (7640 appears on two tokens) | I5 check: no Mastercard row matched twice; ambiguous goes to exceptions |
| Code version in the manifest: `git` missing or not a repo | Falls back to `"unknown"`, never fails the run |
| Time: due 2026-10-21 | Minimum (E0–E6) first and complete; extras in spec order; unbuilt ones stay "written, not built" |

## Simplicity check

- No new structure beyond the spec's file list except `tests/test_guards.py` — it exists so structural checks can be
  proven to discriminate (red on a seeded violation) without polluting the golden suite. Folding it into
  `test_golden.py` is acceptable if the reviewer prefers one file.
- No classes beyond plain dataclasses; no plugin or rule engine — the type→class map is a dict.
- Treasury view (E9) is last and optional.

## Readings after the fifth repair review

Answers the fresh review of 2026-10-15 (`review-repairs-5-2026-10-15.md`). Andrés approved the fix of its material
finding in session on 2026-10-15 («Sí vamos con ese orden» [Yes, let's go in that order], answering the proposal to
treat the USD conversion error like the other processor errors). None of these changes moves a real-data figure:
262 exception rows, entries E01–E11, cash unreconciled 0.00.

- **USD conversion error is corrected like the other processor errors.** `usd_conversion_error` joins
  `CORRECTION_TYPES` (its fixer is the Processor): the tool proposes one entry reversing what the feed overstated or
  understated, the same mechanism as `fx_rate_diff`, with its own entry id after the existing ones on new data (no
  entry on the case data, which has no such row). Its action sentence becomes "Processor re-converts at Mastercard's
  rate and resends the file; Finance Ops posts the proposed correction and the feed does not post the resent file".
  Planted: PX10000700's processor amount_usd +1,200.00 → one proposed entry of 1,200.00 citing that row, balanced.
- **The feed clause belongs to Finance Ops, and only where an entry already corrects the amount.** For the five
  processor types with a resend and a proposed entry (fx rate, sign flip, amount, processor duplicate, USD
  conversion), the sentence ends "…; Finance Ops posts the proposed correction and the feed does not post the resent
  file". The clause is one constant. `auth_after_clearing` loses the clause (it moves no money).
- **An old unpaid settlement says what to do, as the policy says it.** `settlement_not_debited` reads "Confirm the
  bank debits the settlement; still open after 5 business days, it escalates to the Controller; no entry"
  (`recon_and_close_policy.md`: "Open reconciling items older than 5 business days escalate to the Controller").
  Amended 2026-10-15 by the session: the first wording ("Treasury escalates to Mastercard") contradicted the policy.
- **A USD conversion error that is Mastercard's own** (`fixer` Mastercard: only Mastercard's conversion is off) gets
  no entry — the processor amount the ledger holds is right — and reads "Mastercard corrects its conversion and the
  settlement; Treasury follows the adjustment; no entry". Session reading, 2026-10-15, to confirm with Andrés; the
  case data has no such row.
- **Month cut-off is Finance Ops' in one place.** The Processor list is `_LEG1_TYPES` minus the Finance Ops list; the
  `!= "month_cutoff"` filter and its comment go.
- **Tests read the lists from policy.** The tests take the processor-correction types from `policy.CORRECTION_TYPES`
  instead of a copy. A plant deleting T12 (a task used only for a missing file) makes `checklist_tasks_owned` fail
  naming T12. The "written once" guard compares only the declared type lists that must not overlap (leg-1 types vs
  each other list) instead of a shared-member threshold.

## Page: a summary by category on every tab, all rows in one table below

Andrés, in session, 2026-10-15 (decision log): the side panel that opens on click ("Source rows") and the separate
"By figure" tab make the analyst lose which row they were on. Every tab instead shows a summary by category on top
and, below it, one table with all its rows, the source row's own fields inline. No figure changes; the CSV outputs
and their columns stay as they are. Only `bridge/report.py` and `bridge/template.html` change (plus `policy.py` for
the one declaration below).

- **Layout of every data tab** (Exceptions, Proposed entries, Balances, Cash reconciliation, Close tracker,
  Checks): (1) a heading and one lead sentence; (2) a summary table by category with a count column and, where the
  tab has money, a USD total column; its rows add up to a total row equal to the sum of the table below; (3) the
  filter bar; (4) one table with every row of the tab, a sum row of its amount column for the visible rows, and a
  CSV download of exactly the visible rows. Clicking a category row in the summary filters the table below to that
  category in place (the category filter in the bar shows it, and "All" clears it); nothing opens beside or over the
  page.
- **Categories per tab.** Exceptions: difference type (with its class and leg shown in the row). Proposed entries:
  entry id with title, status and approval level; total = debit total. Balances: account, with before and after.
  Cash reconciliation: line kind (ledger balance, reconciling items, bank balance, unreconciled). Close tracker:
  status. Checks: passed / failed.
- **Source rows inline, not behind a click.** Each row that cites input rows shows a "Source" column with
  `file:row` as plain text and, next to it, the cited row's key fields as their own columns. The key fields per
  input file are declared once in `policy.py` (`SOURCE_FIELDS`: 3–5 columns per file — date, reference/id, amount,
  currency, description where the file has them) and the page reads them as data. A row citing several input rows
  shows the first one's fields and "+N more"; the CSV download of that tab carries every cited row id. The
  `data.sources` blob stays only for what the tables need.
- **Removed:** the "By figure" tab, the `drill` panel and its Escape/close handlers, the `figures` blob if nothing
  else reads it (the per-figure rows now live in each tab's table; the summary totals replace the figure totals).
  The page-by-figure tests are replaced by: every tab's summary total equals the sum of its table, and every
  amount figure on the page can be filtered down to the rows that make it up within its own tab.
- **Fits a laptop.** The Exceptions table shows, in this order: date, type, net USD, age (business days),
  escalates, who fixes, Clara owner, what to do, source, the source key fields, then assigned person, status,
  comment. Net is the amount that ties to the leg-1 totals on the Summary (e.g. sign flip 2,502.45; leg 1
  15,600.17); gross stays in the CSV and as a filterable hidden column. The Exceptions summary groups types under
  their leg with a subtotal per leg, never one total mixing the three legs (amended 2026-10-15 after the drafts
  review: the demo reads net, age and escalation aloud). Columns that today duplicate
  these (leg, class, country, origin, needs explanation, controller action) move to the filter bar and the CSV, not
  the visible table. Long text wraps; no horizontal scroll at 1440 px wide for the columns up to "what to do".
- **Agent citations later** (decision log, 2026-10-15): a row has a stable id per tab so a future citation can
  scroll to it and highlight it. No agent code now.
- Checked by hand in Chrome by the session after the build: each tab at 1440 px, clicking a summary row filters the
  table, the sum row matches the summary, CSV download of a filtered view, the "not reliable" banner with the T05
  plant.

## Extras before submission: itemised invoice, Treasury view, Mastercard's own conversion error

Andrés, in session, 2026-10-15 (decision log): build the itemised Mastercard invoice accrual and the Treasury view
before the 21st, and adjust a USD conversion error that is Mastercard's own instead of leaving it without an entry.
Spec rows E8 and E9 (`spec.md`) are the contract; this block fixes what they leave open. Real-data figures that must
not move: 262 exception rows, cash unreconciled 0.00, every account's before balance.

- **Itemised invoice accrual (E8).** The program-invoice accrual (today one 8,412.30 line, E05) becomes one debit
  line per invoice line item of `mastercard_invoice_lines` (or the file's real name) — the cross-border adjustment
  to its own expense sub-account (variable cost), the other line items to 5100 (fixed programme cost) — and one
  credit of the total to 2150; still proposed only when `invoice_not_accrued` is raised, still reversed in October,
  same entry id E05. Each debit line cites its invoice row. Accounts: if the chart in the data has no sub-account
  for the cross-border adjustment, use 5100 with the line item named in the entry title and say so; never invent an
  account number without declaring it in `policy.ACCOUNTS`. The classification follows the 2026-10-14 decision
  (cross-border adjustment variable; network access, licensing, brand fee fixed; none below EBITDA).
- **Treasury view (E9), `bridge/treasury.py`.** From the bank statement alone: the bridge account's closing balance
  per calendar day of September (it must equal the statement's running balance on each day with movements); the
  Mastercard debits per day; the average daily debit and its standard deviation over September's business days; days
  of coverage at each day's close = balance / average daily debit; a suggested weekly transfer = expected debits of
  the next five business days (average × 5) + a buffer of k standard deviations × √5, with k declared once in
  `policy.py` and labelled illustrative (Treasury sets the real target). Output file `treasury.csv` (date, balance,
  mc_debits, days_of_coverage, src); the page gets a "Treasury" tab built like every other tab (summary on top —
  closing balance, average debit, days of coverage at 30-Sep, suggested transfer — and the daily table below). The
  run writes nine files.
- **Mastercard's own USD conversion error is adjusted and followed.** Supersedes the a030dcc reading. When the fixer
  is Mastercard, the tool proposes an entry like the duplicate debit's: the settlement Clara paid differs from what
  the processor (and the ledger) hold, so record a receivable from (or payable to) Mastercard for the difference
  against the Mastercard payable, status proposed, cleared when Mastercard's correction arrives. Action: "Post the
  proposed adjustment now; Mastercard corrects its conversion and the settlement; Treasury follows the correction and
  clears the adjustment when it arrives". The case data has no such row, so E01–E11 stay (E05 becomes itemised).
- Tests pin: E05's lines and total 8,412.30 with each line citing its invoice row; `treasury.csv` daily balances equal
  the statement's running balance; 30-Sep days of coverage and the suggested transfer recomputed by a throwaway
  script; the Mastercard-owned conversion plant (MC2827341940727 +1,200.00) gets one balanced proposed entry citing
  the Mastercard row, and the processor-owned plant keeps its E12.

## Five screens by the person who operates them

Andrés, in session, 2026-10-15 (decision log): the page is organised by the person using it, not by output file.
Five screens replace the tabs: Summary, Data quality, Reconciliation, Pending actions, Close. This round also fixes
review 6's two material findings (`review-repairs-6-2026-10-15.md`). It is the last page redesign before submission.
No reconciliation figure changes; the nine output files keep their columns, and new files are added only where
listed below. Changes: `bridge/report.py`, `bridge/template.html`, `bridge/policy.py`, plus counts in
`bridge/recon.py` and the close-status logic in `bridge/close.py`.

- **Summary (first screen).** What someone sees on opening the page, with no scrolling at 1440×900:
  - one block per leg, the "bridge" between its two records: leg 1 processor vs Mastercard — rows on each side,
    matched with no difference (count, USD), matched with a difference (count, net USD), on one side only (count,
    USD each side); leg 2 Mastercard daily net vs bank debits — settlement days, paired, unpaired, duplicate debits
    (count, USD); leg 3 bridge account and payable vs ledger — each account's ledger balance, the record it is
    compared with, and the difference;
  - how much is explained: the total difference per leg split into timing, real error and data issue, and the
    unexplained residual (today 0.00);
  - what is wrong: exception count and net USD per leg, how many escalate, how many wait on an outside party;
  - one close-status sentence (from Pending actions) and one data-quality sentence (from Data quality).
  Every figure links to the screen and filter that shows its rows, and equals the sum of those rows. The per-leg
  match counts are computed once in `recon.py` and written to `run_manifest.json` `totals`.
- **Data quality (audit phase, before the result).** The pre-checks table (today's Checks tab) and, above it, one
  row per input file: read or missing, rows, period covered (from the manifest). A failed check says what it means
  for the result. The "not reliable" banner stays.
- **Reconciliation.** Two views of the same rows, switched in place:
  - *Detailed*: today's Exceptions table and filters, with assigned person, status and comment per row.
  - *Grouped*: one row per day for legs 1 and 2 (leg 1 by clearing date: processor USD, Mastercard USD,
    difference, exception count; leg 2 by settlement date: Mastercard net, bank debit, difference) and one row per
    account for leg 3; clicking a group row switches to *Detailed* filtered to that day or account.
  - **Every cited input row is on the page** (fixes review 6, material 1). A row citing several input rows shows the
    first and expands in place to all of them, each with its key fields; nothing opens beside the page. Leg-1 rows
    show both sides: `SOURCE_FIELDS` for the processor and Mastercard files carries the local amount and the rate
    (merchant name dropped to stay within 5 fields).
- **Pending actions ("what is missing to close September").** Andrés, 2026-10-15: built on the case's close
  checklist with what the tool found.
  - On top, one sentence with figures: open checklist tasks, those blocked by a problem the tool found, entries to
    approve (count, USD), items waiting on Mastercard or the processor.
  - One row per checklist task (open ones first; the tracker's dependencies, blockers and critical path stay): what
    it lacks, concretely — the exceptions, entries or failed checks linked to it through the existing type → task
    map, with counts, USD and their rows; its owner; and the drafted message where one applies.
  - **The tool never marks a task done** — status stays the checklist's; preparer and approver differ. A task the
    tool has no evidence for says "No tool evidence; depends on the owner".
  - **Drafted messages, never sent.** Templates declared once in `policy.py`: to Mastercard (summary vs detail
    mismatch, charges with no processor record, the duplicate debit, a Mastercard-owned conversion error) and to the
    processor (resend file with duplicates, sign flips, amount and rate errors, misdated clearing). Each draft fills
    in the cited rows and amounts, has a copy button and a .txt download, and says "Draft — not sent".
- **Close.** Proposed entries, balances before and after, cash reconciliation, Treasury. For a figure built from
  many rows (each balance, the ledger cash balance) a second table under the summary lists the source rows of the
  selected figure, with amounts, a sum row equal to the figure, and a CSV (Andrés, 2026-10-14: "the ledger balance,
  the total, and below it a table with the transactions").
- **Every screen:** summary on top that filters in place; a click keeps the table in view (scroll it into view —
  fixes review 6, material 2); sum row of the visible rows; CSV of the visible rows. Cash keeps a count-only total
  and balances keep the "trial balance check" label (recording the page-round reading, review 6 minor 3).
- **Review 6 minors taken:** saved notes keyed by leg|type|key (with `#n` for repeats), not by the source list;
  the stale "no money is added up in the browser" comment fixed; the balances label said once. The both-sides USD
  conversion edge (minor 1) is left to the analyst and said in the action sentence.
- Tests pin: every Summary figure equals the sum of the rows its link filters to, and the per-leg match counts
  recomputed by a throwaway script from the raw files; every cited input row of every page row is present on the
  page; each Close figure's source-row table sums to the figure; each open checklist task's "what it lacks" names
  exactly its linked exceptions, entries and failed checks, and a task with none says so; no task status differs
  from the checklist; each draft names only rows of its own type and is marked not sent. Checked by hand in Chrome
  by the session at 1440×900: Summary fits without scrolling, every click keeps the table in view.

## Repairs after the five-screens review

Fresh review `review-screens-2026-10-15.md` (verdict: not ready). Session decisions on its findings; the 2105 rule
(material 2) waits for Andrés and is added to this block when he answers.

- **Leg 1 adds up on the first screen (material 1).** The processor side shows equal + with a difference +
  duplicates (6, net 3,593.63, linked to `processor_duplicate`) + processor-only = 3,117; the Mastercard side adds
  up the same way. The note under the block reads "Net difference of the exceptions: 15,600.17 (gross difference of
  the files: 14,884.40)". Tests: each side's counts add up to its row count.
- **Pending actions keeps the checklist's status (material 3).** The Status column shows only the checklist status.
  The tool's finding has its own column ("Tool finding"). A task's evidence comes from the existing type → task map
  and, where a task has no exception, from `policy.TOOL_EVIDENCE` (declared once): T13 lacks the 11 entries awaiting
  approval; T08 lacks the 2105 entries and the roll-forward. T07 says the 400,000 funding in transit is a reconciling
  item to confirm on 1-Oct; T12 says the invoice was not received, not "net 0.00". A Done task shows no
  "No tool evidence" sentence. The test of 1516c24 that forbids entries on T13 is amended first, in the test commit.
- **Grouped view shows what the Summary shows (material 4).** Leg 2: the duplicate debit sits on the settlement day
  it duplicates, bank 82,018.97, difference 40,616.94, 1 exception. Leg 1: each pair sits on the processor's clearing
  date (the date its exception carries), so no day shows a difference with 0 exceptions. A group-row click filters
  to that group's exception row ids, never to a date range; a group with no exceptions is not clickable.
- **The Summary fits at 1440×813, a normal Chrome window at 1440×900 (material 5).** The "input not supplied" banner
  leaves the Summary (the data-quality sentence says it); the by-type figures go on fewer rows.
- **Drafts follow who fixes (material 6).** A draft holds the rows whose type is in its template's types and whose
  fixer matches the template's party; a processor-owned conversion error goes in the processor's amount-and-rate
  draft. Drafts show gross amounts, dates and the other side's reference; D03 names the original debit BS0016.
- **No draft about the edge of our own file (material 7).** The summary-vs-detail check skips summary days outside
  the detail file's settlement dates and lists them as a coverage note; each remaining mismatching day appears in its
  draft with both counts and nets; no draft when none remains.
- **Minors taken:** every Summary figure links unless it is on a declared list ("matched with no difference" only);
  processor and Mastercard rows link to Grouped leg 1, leg-2 figures to Grouped leg 2; the close-status sentence
  separates money from data flags ("122 differences (USD …) need a corrected file or a credit — … from the processor,
  … from Mastercard; 131 data flags go back to the processor", figures from the run); `CHECK_TASK` removed (dead);
  the old tests' `.figures` ban and `summary` requirement narrowed in the test commit, then `FIGURE_LIST` and the
  empty summaries removed; "Draft — not sent" read from the data; task names do not break mid-word; zero-count
  figures are not clickable; currency dropped from the leg-1 source fields is recorded here (local amount and rate
  need the five slots). Not taken: leg-3 type → account map (the page discloses it).
- **Amended by the session after the verifier (72a3eb0):** the duplicate debit BS0018 duplicates BS0016, which paid
  the 17-Sep settlement, so it sits on the 17-Sep row (bank 81,233.88, difference 40,616.94); the 82,018.97 above
  was wrong. "Fixer matches the template's party" means the template's declared fixer, not the recipient (D02 stays:
  Mastercard-only rows are drafted to Mastercard). Blocked tasks rise to 9 once T08 and T13 lack entries: intended.
  The close sentence's USD is net, like every other figure on the Summary.

## The Mastercard payable reconciled against Mastercard

Andrés, in session, 2026-10-15 (decision log): 2105 is reconciled the way a controller reconciles a payable — books
against the supplier's own statement — replacing the "as the settlements imply it" figure (`_payable_implied`,
built from the processor file; review-screens material 2).

- **Owed to Mastercard at 30-Sep, from Mastercard's files only:** the settlement-summary nets for settlement dates up
  to 30-Sep that the bank had not debited by 30-Sep (case: the 30-Sep settlement, 44,643.99, debited 1-Oct), plus
  September transactions that Mastercard cleared in October (the month cut-off rows, 928.31). Each part cites its
  rows. Computed once (leg 3, `recon.py` or `close.py`, where the leg-3 figures live).
- **The bridge, on the Summary's leg-3 block and as Grouped leg 3's 2105 row:** ledger balance (70,588.66, shown as
  a debit, the wrong side) → proposed entries on 2105, confirmed only (net) → result → owed to Mastercard → difference;
  and the same with all proposed entries, labelled "if the proposed entries are approved". Case: all entries →
  owed 45,572.30, difference 0.00; confirmed only → difference 9,127.92, explained as the processor-only rows whose
  entry is conditional on evidence. Every figure links to its rows (the entries on 2105; the Mastercard rows owed).
- `_payable_implied` and its figure are removed. No other figure moves.
- Tests pin: owed 45,572.30 = 44,643.99 + 928.31 recomputed from the raw Mastercard and bank files; both bridge
  lines (0.00 and 9,127.92) from `balances.csv` before / after_confirmed / after_all; a planted +100.00 on the 30-Sep
  settlement net moves "owed" and the difference by 100.00; every bridge figure links.

## The payable bridge reads on its own, and the last page fixes

Fresh review `review-repairs-payable-2026-10-15.md` (verdict: not ready; the accounting is right, the page is not
yet readable). Session decisions on its findings:

- **Every bridge link opens rows that sum to its figure (material 1, 2).** The result links to the ledger's rows plus
  the 2105 lines of the entries, so they sum to the result; entries and difference open the proposed-entries table
  filtered to those entries' 2105 lines with a net (debit − credit) sum equal to the figure; source rows are not
  repeated across one entry's lines. Test: for every bridge figure, the rows its link opens sum to the figure.
- **The bridge reads as plain subtraction (material 3).** Title "Mastercard payable 2105 against Mastercard's own
  files". Lines: "Ledger at 30-Sep (debit — the wrong side)" 70,588.66; "Proposed entries on 2105"; "Ledger after the
  entries (credit)" 45,572.30; "Mastercard's 30-Sep settlement, debited 1-Oct" 44,643.99; "September transactions
  Mastercard cleared in October (timing)" 928.31; "Difference" 0.00. Columns "Entries with no condition (8)" and
  "All entries, if E10's evidence arrives (9)"; under the first, one line: "9,127.92 = E10: 3 processor-only rows;
  its entry waits for evidence." Credits shown as positive amounts labelled "(credit)", so the difference is the
  result minus the two Mastercard lines.
- **Grouped leg 2 never shows an undebited settlement as paid (material 4).** The bank column adds an exception's
  amount only for a debit on no summary day and for a duplicate. Test: a planted deleted debit (BS0024) leaves the
  24-Sep bank at 0.00 with difference 44,884.41.
- **Grouped leg 3 reconciles both rows the same way (material 5).** Columns: ledger, compared with, difference,
  reconciling items, unreconciled — 0.00 on 1110 and 2105 with all entries; the items say they include E10. Account
  names, not codes.
- **Minors taken:** weekend stale authorisations keep their real date in the data; only the grouping maps them to
  the next working day. The Summary keeps at least 40 px of margin at a 1440×900 window, the owed rows open below
  the fold without moving the Summary. T08 shows the 2105 net (116,160.96), not total debits. T07 is not blocked: a
  reconciling item to confirm is not a defect (blocked tasks = 8). The sentence says "130 data flags go back to the
  processor; the processor invoice was not received". The hidden 2105 ledger Summary figure is removed from the data.
  The leg-1 gross difference (14,884.40) is computed in the data. The 2105 difference is computed once.

## Honest evidence on every entry line, and the closing fixes

Fresh review `review-closing-2-2026-10-15.md` (verdict: not ready). The previous block's sentence "source rows are
not repeated across one entry's lines" was the session's error: it pushed the code to cite opening-balance rows as
evidence on 26 entry lines. It is withdrawn. Session decisions:

- **Evidence is never invented (material 1).** Each entry line's `src` in `proposed_entries.csv` is back to the
  cd9981d rule (the file is byte-identical to cd9981d's again); no line cites `gl_opening_balances.csv` unless the
  entry is built from it. Where several lines of one entry open together, the page lists each source row once per
  entry and says "same evidence as the line above"; the data is not changed for display. The repeated-rows test is
  replaced by: `proposed_entries.csv` equals cd9981d's; no opening-balance citation on an entry line.
- **A missing input never crashes the run (material 2).** Account names fall back to `policy.ACCOUNT_NAME`; the
  deleted-inputs plant also writes the page.
- **Bridge labels never overlap their figures (material 3):** the label column wraps. Checked by hand in Chrome.
- **The bridge's words are computed, not stated (material 4).** The E10 sentence appears only when the
  confirmed-column difference equals the conditional entries' 2105 net, with the row count taken from those
  entries' own sources; otherwise "of which X is E10; Y not explained". The settlement label names the unpaid days
  ("Mastercard settlements not debited by 30-Sep (30-Sep)"). Test: on the BS0024-deleted plant, no "= E10" with a
  wrong figure, and the label names 24-Sep.
- **T08's click equals T08's figure (material 5).** The task's link comes from the data, the same link as the
  bridge's entries line ({entry_id, account}, debit − credit).
- **A multi-part click reads plainly (material 6).** Each part names itself ("Ledger rows add up to 70,588.66";
  "Proposed-entry lines on 2105 add up to −125,288.88"); "Together: −54,700.22 debit, that is 54,700.22 credit — the
  figure"; no single footer sum when several parts show.
- **Minors taken:** T07 reads "Waits on …", not "Lacks"; not-blocked derives from what the task lacks being a
  reconciling (timing) item, not from its id; opening settlement or timing rows does not move the Summary (they open
  below it); one click opens only that line's rows; the 2105 difference is computed once and read everywhere; no
  parsing back from a rendered link; no shared mutable default.

## Last round before freezing: waterfalls, impact per action, ERP file, explanations

Andrés, in session, 2026-10-15 (decision log). After this round the tool is frozen; anything later is said aloud or
written as a proposal. No existing output file changes (proposed_entries.csv keeps sha256 315ec8d5…); one file is
added.

- **A waterfall per pair of records, on the Summary.** Inline SVG, no library, in the one self-contained page.
  Leg 1: processor total → one bar per difference type (duplicates, sign flips, amount, FX rate, month cut-off,
  processor-only, Mastercard-only; signed, net) → Mastercard total; it must land on Mastercard's total to the cent.
  Leg 2: Mastercard settlements → duplicate debit → bank debits. Payable 2105: ledger → proposed entries → owed
  (settlement, timing) → difference 0.00 (all entries), the 9,127.92 shown as E10 on the confirmed basis. Every
  bar is clickable and opens the rows that sum to it (the same links as the figures). Bars and labels are computed
  in Python into the page data; the script only draws. Accessible: each bar has a text label with its amount.
- **Click-to-open explanations.** A small "i" next to each figure, column header and screen title opens a short box
  saying what it means and where it comes from; it opens on click (works on a phone), closes on click outside or
  Escape. The texts live once, in `policy.py` (`GLOSSARY`: key → one or two plain sentences), and the page reads
  them as data. Every Summary figure, bridge line, waterfall and screen has one.
- **Impact per action on Pending actions.** Each task shows "Resolves USD X" = the net of the exceptions it lacks
  (signed by leg, per leg), plus, for entry tasks, the 2105 net of its entries. Clarified 2026-10-15 after the
  verifier read it as a sum: a task whose entries correct its own exceptions (T02, T06) shows the exceptions' net
  once, never exceptions plus entries, which would net to 0.00; only a task with entries and no exceptions of its
  own shows its entries' 2105 net. A 0.00 waterfall bar (month cut-off rows sit in both totals) shows 0.00 and says
  why. A total on top counts each
  exception once (an exception linked to two tasks counts once; entries correcting the same exceptions are not
  added on top). Tasks are ordered open first, then by the absolute USD they resolve.
- **ERP file `proposed_journal_lines.csv`** (tenth output): exactly the columns of `gl_journal_lines.csv`, in its
  order (je_id, posting_date, source, account, account_name, debit_usd, credit_usd, description, reference). je_id
  "PROPOSED-E01"…; posting_date 2026-09-30 (an entry that reverses in October says so in description); source
  "PROPOSED_NOT_APPROVED"; account_name from the opening balances (fallback `ACCOUNT_NAME`); description = the entry
  title; reference = the entry's approval level and status. Lines and amounts equal `proposed_entries.csv` exactly.
- **Visual pass.** Cards with clear hierarchy, one accent colour, red only for what is wrong, green for what ties,
  numbers right-aligned in tabular figures, generous spacing; the Summary still fits a 1440x900 window with no scroll.
  Light theme, printable.
- **README:** "How to run it" for a finance reader — install Python 3 (macOS and Windows), where to put the 13 files
  (same names and columns), the one command, where the page appears, how to open it; that the period is September
  2026 and is declared in `policy.py` (PERIOD_START, PERIOD_END, HOLIDAYS) for another month; the ten output files.
- Tests pin: each waterfall's bars sum from its start to its end to the cent and each bar's link sums to the bar;
  every Summary figure, bridge line, waterfall and screen has a GLOSSARY key and the texts live only in policy.py;
  impact per task recomputed independently and the top total counts each exception once; the ERP file's header
  equals gl_journal_lines.csv's, its lines equal proposed_entries.csv's, every je_id starts "PROPOSED-" and every
  source is "PROPOSED_NOT_APPROVED"; proposed_entries.csv unchanged; README names the command and Python 3.

### Freeze fixes from the closing review of the last round (review-closing-4-2026-10-15.md)

Page and README only; no figure changes; proposed_entries.csv unchanged.
- **A waterfall bar shows what it sums.** When the exceptions table opens from a waterfall bar, it shows the column the
  bar sums (`gross` for leg 1) and its footer sums that column. The sentence states both signs: the rows' gross
  (processor minus Mastercard) and the step walking from the processor to Mastercard. The direction stays processor
  to Mastercard.
- **Summary fits a 1440x813 viewport** (a 1440x900 window) with no scroll: the leg-1 "difference by type" table on
  the Summary is removed (the waterfall replaces it), and spacing is tightened as needed.
- **Printable Pending actions:** printing hides controls only; task names and source references stay.
- **"Resolves USD" headline split:** the total on top also says how much of it is timing (funding in transit, which
  clears on its own) and how much is errors to correct; T07 is tagged "timing". Entry tasks (T08, T13) show the
  2105 amount as a credit, unsigned ("116,160.96 Cr on 2105"), and are outside the top total, said once.
- **One screen list:** the page reads the five screens from `page.screens`; the script holds no copy.
- **README month paragraph:** the run is built for September 2026; the month is declared in `policy.py`
  (PERIOD_START, PERIOD_END, HOLIDAYS, CUTOFF_DATE) and another month also needs the September/October wording
  reviewed. How to open a terminal in a folder on macOS and Windows; the Mac developer-tools prompt is fine to accept.
- **Wording:** the settlement-days explanation says "settlement days 31-Aug to 30-Sep"; Close says the entries are
  also in `proposed_journal_lines.csv`, ready to load into the ERP and marked not approved.
- Tests pin: a bar that links on a column has that column among the shown columns; T02 90,215.88, T06 40,616.94,
  T05 15,600.17 (exceptions' net, not plus entries); the headline split adds to the total and T07's 400,000.00 is
  the timing part; the page script holds no screen-name list; README names CUTOFF_DATE; the print rule does not hide
  task buttons. Summary height and print preview are hand checks in Chrome.
- **Data quality as a filterable table** (Andrés, 2026-10-15, after the block above). On top, one line per check:
  passes or not, its count with its unit, and the count matches what it opens ("2 days · 155 rows", never a count
  of one unit that opens rows of another). Checks with no rows of their own (summary vs detail, net formula, missing
  inputs, cash reconciled, coverage, owners) stay as pass/fail lines on top only. Below, one table of every flagged
  row: check, why it fails in one sentence (from GLOSSARY or the check's detail), source file:line, amount where the
  row has one; filter by check; footer sums the shown rows. Reuses the Reconciliation table pattern, no new
  structure. Row text is selectable; a "Copy" and a "Download CSV" control act on the shown rows, here and on
  Reconciliation, built in the page (no network).
- Tests pin, additionally: every check line states a unit and its count equals the rows or days it says; the
  flagged-rows table has one row per flagged source row, each with a check key, a reason and a source; the page
  script has copy and CSV-download handlers acting on the shown rows.
- **Reconciliation reads by type, not by date** (Andrés, 2026-10-15: «cuando uno abre el detalle, la misma fecha se
  repite varias veces y no cambia nada más» — "when you open the detail the same date repeats and nothing else
  changes"). *Detailed*: the per-type summary on top shows every type with no inner scroll, and clicking a type
  filters the table; the table's first column is the type, rows ordered by type (the summary's order) then by
  absolute net, with a header row per type carrying its count and net, collapsible; the data-issue class (net 0.00:
  bad references, stale authorisations, impossible dates, ambiguous matches) is hidden by default behind one control
  naming its count ("show the 130 data flags — no money; also in Data quality"; superseded by freeze fixes 2: the missing processor invoice is not hidden); columns narrowed so assigned
  person, status and comment fit at 1440 px. *Grouped*: leg 1 by type — one row for the pairs that match exactly
  (2,997, 881,142.94) and one row per type, with processor USD, Mastercard USD and difference columns summing to
  924,303.45, 909,419.05 and the leg's difference; leg 2 stays by settlement day; leg 3 stays by account. Leg-1
  total bars keep linking to Grouped leg 1. exceptions.csv unchanged.
- Tests pin, additionally: Grouped leg 1 has the matched row plus one row per leg-1 type, and its columns sum to the
  two totals; the Detailed default hides exactly the data-issue class and the control names its count; the page
  script orders Detailed by type then absolute net.

### Freeze fixes 2, from closing review 5 (review-closing-5-2026-10-15.md)

Page only; no figure changes.
- **A figure opens exactly as many rows as it says.** The data flags are hidden only on the bare, unfiltered Detailed
  view. Opening Reconciliation from any other screen, any filter, or a search shows them. The hidden group is the 130
  leg-1 flags (bad references, stale authorisations, authorised after clearing); the missing processor invoice is
  not hidden (it is an unaccrued cost, not "no money"). The control names the number hidden under the current view.
- **Copy rows shown copies what is on screen:** the shown columns in the shown order, with the shown labels, plus the
  notes columns, the same as the CSV.
- **One type order** everywhere (waterfall, Grouped, Detailed): the waterfall's.
- **Small:** minus sign "−" in the step sentence; Grouped leg-1 footer counts pairs, not groups; the Data quality
  "All" footer shows no sum across checks (sum only when one check is selected); "Missing inputs" detail names the
  processor invoice.
- Tests pin: every Summary figure that links to the exceptions table states a count equal to the rows its link
  shows under the hiding rule; the hidden group is exactly the 130 leg-1 flags; copy uses the shown columns.
- **Headline label** (Andrés, 2026-10-15, «Me gusta tu recomendación»): the 167,345.29 part reads "needs action by
  Clara", not "errors to correct"; the 400,000.00 part stays "funding in transit (clears 01-Oct)".

### Named owners from the email thread (Andrés, 2026-10-15, after the freeze)

Andrés: «pongámosles nombres también a las tareas de las que sabemos de quién son, porque ya con esos correos tenemos
quién es quién» ("let's name the owners of the tasks we know, since the emails tell us who is who"). The tool is
unfrozen for this block only; no figure changes.
- **One declaration** in `policy.py`: `PEOPLE` maps a checklist `owner_role` to the person the email thread names
  in that role, with the source line: Controller → Marta Quintero, Treasury → Lucia Ferreira, Finance Ops → Diego
  Alvarado (each from a `FROM:` line of `treasury_email_thread.txt` that states the role in parentheses); Treasury /
  AR → Lucia Ferreira (she raised the suspense item, 24 Sep). Customer Success → Camila Rojas is declared for the
  drafted messages only (no checklist task has that role). No other role gets a name: Billing, CFO, AP, AR, FP&A,
  Payroll, Revenue Accounting and the rest stay role-only. The tool never invents a name.
- **Shown as role plus person, with provenance:** "Treasury — Lucia Ferreira" wherever an owner role appears
  (Pending actions owner, Reconciliation "Clara owner", Close tracker), with an "i" text saying the name comes from
  the email thread and which line. The role stays the owner of record; the name is who to contact.
- **Drafted messages** address the named person where one exists ("Lucia, …") and keep the role otherwise.
- **Outputs:** `close_tracker.csv` gains an `owner_name` column next to `owner_role` (blank when no name), and its
  `src` cites the email line for the name. `exceptions.csv` gains `clara_owner_name` likewise. proposed_entries.csv
  unchanged; proposed_journal_lines.csv unchanged.
- **Assigned person** in Reconciliation defaults to the named owner when the analyst has typed nothing; a typed value
  wins and is kept in the browser as today.
- Tests pin: the three role names are read from the email file (not hard-coded in the tests), each with its source
  line; exactly the tasks of those four roles carry a name (16 tasks: T01 T02 T03 T04 T05 T06 T07 T08 T09 T11 T12 T13
  T17 T18 T21 T26; T02 was first left out by a session parsing slip on a quoted comma); no other task does; the new columns; proposed_entries.csv sha256 unchanged.

### Modern visual style (Andrés, 2026-10-15, session 2, after the second freeze)

Andrés: «Podemos hacer un estilo moderno del dashboard, podemos tomar a [otra empresa] como ejemplo. El dashboard
esta muy plano» ("Can we do a modern style for the dashboard, taking [another company] as an example. The dashboard is
very flat"); he chose the feel only, with an own palette — no other company's brand, logo, colours or assets. The tool is
unfrozen for this block only. **Style only.**
- **What changes:** `bridge/template.html` only — the CSS (tokens on `:root`, cards, shadows, header, tabs, headline
  figures, tables, buttons, waterfalls' colours) and, where a style needs it, class names or wrapper elements. Aim:
  depth and hierarchy instead of a flat sheet — a dark header band, white cards with a soft shadow and rounded
  corners on a tinted background, the headline figures large with a coloured accent per meaning (needs action /
  in transit / reconciled), tabs that read as tabs, tables with a sticky header, quieter grid lines and hover rows,
  more air between sections. Fonts stay the embedded DM Sans and Inter (no network fetch: the page is a single
  offline file). Colour still never carries meaning alone; text contrast at least 4.5:1.
- **What does not change:** any figure, label text, row, column, filter, click behaviour, explanation text, or
  any file other than `index.html`. `policy.py`, `report.py` and the rest of `bridge/` untouched; no test edited.
- **Verifier (mechanical, already exists):** (1) the whole suite green with `git diff --stat tool-frozen-2-2026-10-15
  HEAD -- tests` empty; (2) a run into a fresh folder gives the nine non-page outputs byte-identical to the frozen
  run's, `run_manifest.json` excepted only in `code_version` and `generated_at`; (3) `git diff --stat
  tool-frozen-2-2026-10-15 HEAD -- bridge` touches only `template.html`. Judged by the fresh review: the page in
  Chrome at 1440x813 and at phone width, every tab, the Summary still fits, nothing lost.
