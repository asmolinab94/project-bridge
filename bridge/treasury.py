"""Treasury view (spec E9): from the bank statement alone, the bridge account's closing balance per calendar day of the
period, the Mastercard debits per day, and the cover those balances give against an average daily debit."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from bridge import policy
from bridge.inputs import ZERO
from bridge.recon import ONE_DAY, is_working_day


@dataclass
class Treasury:
    rows: list             # per calendar day: date, balance, mc_debits, days_of_coverage, src
    excluded: list         # bank lines left out of the debits: the duplicate debits
    closing_balance: Decimal
    average_debit: Decimal
    std_debit: Decimal
    coverage: object       # days of coverage at the last day; None when there is no average to divide by
    transfer: Decimal


def _cents(value):
    return value.quantize(policy.CENT, ROUND_HALF_UP)


def build(inputs, recon):
    duplicates = {d.key for d in recon.differences if d.type == policy.TYPE.bank_duplicate_debit}
    by_day = {}
    for b in sorted(inputs.bank, key=lambda b: b["line_id"]):
        by_day.setdefault(b["posting_date"], []).append(b)
    days = [policy.PERIOD_START + ONE_DAY * n for n in range((policy.PERIOD_END - policy.PERIOD_START).days + 1)]
    rows, debits, last = [], [], None
    for day in days:
        lines = by_day.get(day, [])
        last = lines[-1] if lines else last
        if last is None:  # no statement line yet: no balance is invented
            continue
        paid = [b for b in lines if b["kind"] == policy.KIND.settlement and b["line_id"] not in duplicates]
        mc_debits = sum((b["debit_usd"] for b in paid), ZERO)
        if is_working_day(day):
            debits.append(mc_debits)
        rows.append(dict(date=day, balance=last["running_balance_usd"], mc_debits=mc_debits,
                         src=[last["src"]] + [b["src"] for b in paid]))
    count = len(debits)
    average = sum(debits, ZERO) / count if count else ZERO
    spread = (sum(((x - average) ** 2 for x in debits), ZERO) / (count - 1)).sqrt() if count > 1 else ZERO  # sample
    for row in rows:
        row["days_of_coverage"] = _cents(row["balance"] / average) if average else None
    horizon = Decimal(policy.TREASURY_HORIZON_WD)
    return Treasury(rows, sorted(duplicates), rows[-1]["balance"] if rows else ZERO, _cents(average), _cents(spread),
                    rows[-1]["days_of_coverage"] if rows else None,
                    _cents(average * horizon + policy.TREASURY_BUFFER_K * spread * horizon.sqrt()))
