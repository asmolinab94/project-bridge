"""Pre-checks (spec E6): completeness and anomalies of the inputs, one result per name in `policy.CHECKS`, clean or not.
A check reports; it never raises, even on edited data."""

import re
from collections import namedtuple

from bridge import policy
from bridge.inputs import ZERO
from bridge.recon import ONE_DAY, is_working_day

Check = namedtuple("Check", ["name", "passed", "count", "detail", "srcs"])

WHOLE_FILE = "*"
CHECK = policy.CHECK
TYPE = policy.TYPE


def _whole(*attrs):
    return [(policy.INPUT_FILES[a], WHOLE_FILE) for a in attrs]


def _sum(rows, column):
    return sum((r[column] for r in rows), ZERO)


def _by_day(rows, column):
    days = {}
    for r in rows:
        days.setdefault(r[column], []).append(r)
    return days


def summary_days(inp):
    """(days whose summary count or net differs from the detail rows, as (day, summary rows, detail rows); summary days
    left out because they lie outside the detail file's settlement dates, so there is nothing to compare them with)."""
    detail, summary = _by_day(inp.mc_detail, "settlement_date"), _by_day(inp.mc_summary, "settlement_date")
    dates = [d for d in detail if d]
    outside = [d for d in summary if d and dates and not min(dates) <= d <= max(dates)]
    bad = []
    for day in sorted(set(detail) | set(summary), key=lambda d: (d is None, d)):
        rows, sums = detail.get(day, []), summary.get(day, [])
        if day not in outside and (len(rows) != sum(int(s["txn_count"]) for s in sums)
                                   or _sum(rows, "net_settlement_usd") != _sum(sums, "net_settlement_usd")):
            bad.append((day, sums, rows))
    return bad, sorted(outside)


def _summary_vs_detail(inp, *_):
    bad, outside = summary_days(inp)
    detail = "Mastercard summary days whose count or net differs from the detail rows" + (
        "; not compared, outside the detail file's settlement dates: " + ", ".join(d.isoformat() for d in outside)
        if outside else "")
    return [d for d, _s, _r in bad], detail, [r["src"] for _d, sums, rows in bad for r in sums + rows], _whole(
        "mc_summary", "mc_detail")


def _net_formula(inp, *_):
    bad = [m for m in inp.mc_detail
           if m["net_settlement_usd"] != m["amount_usd"] - m["interchange_usd"] + m["scheme_fee_usd"]]
    return bad, "Mastercard rows whose net is not amount - interchange + scheme fee", [m["src"] for m in bad], _whole(
        "mc_detail")


def _statuses(inp, *_):
    unknown = [p for p in inp.processor if p["status"] not in policy.PROCESSOR_STATUSES]
    out = [p for p in inp.processor if p["status"] != policy.PROCESSOR_STATUSES[0]]
    counts = {}
    for p in out:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    detail = "rows kept out of money (%s); passes unless a status is unknown or a row with it has a clearing date" % (
        ", ".join("%s %d" % kv for kv in sorted(counts.items())) or "none")
    flagged = unknown + [p for p in out if p["clearing_date"] is not None and p not in unknown]
    return (out, flagged), detail, [p["src"] for p in out], _whole("processor")


def _card_numbers(inp, *_):
    bad = []
    for attr in policy.CARD_NUMBER_ATTRS:
        for row in getattr(inp, attr):
            for column, value in row.items():
                if column != "src" and isinstance(value, str):
                    stripped = policy.NETWORK_REF.sub("", re.sub(r"[\s-]", "", value.upper()))
                    if policy.CARD_NUMBER.search(stripped):
                        bad.append(row)
                        break
    return bad, "rows holding a 13-19 digit string that is not a Mastercard reference", [r["src"] for r in bad], _whole(
        *policy.CARD_NUMBER_ATTRS)


def _missing_inputs(inp, *_):
    detail = "inputs that are absent or unreadable (never estimated)%s" % (
        ": " + ", ".join(what for what, _src in inp.missing) if inp.missing else "")
    return list(inp.missing), detail, [src for _w, src in inp.missing], []


def _inputs_cover_period(inp, *_):
    """Dated files whose rows, on some date column, do not reach both the first and the last working day of the
    period: a truncated or wrong-month file."""
    first, last = policy.PERIOD_START, policy.PERIOD_END
    while not is_working_day(first):
        first += ONE_DAY
    while not is_working_day(last):
        last -= ONE_DAY
    bad = []
    for attr, column in policy.COVERAGE_COLUMNS.items():
        status = inp.read_status.get(policy.INPUT_FILES[attr])
        span = status["dates"].get(column) if status else None  # a file that was not read has no span
        if not span or span[0] > first or span[1] < last:
            bad.append(policy.INPUT_FILES[attr])
    return bad, "dated input files that are missing or unreadable, or whose period column does not span the first " \
        "to the last working day of the period", [(name, WHOLE_FILE) for name in bad], _whole(*policy.COVERAGE_COLUMNS)


def _checklist_tasks_owned(inp):
    """Close-checklist tasks the type -> task map relies on that are absent or have no owner_role."""
    rows = {r["task_id"]: r for r in inp.checklist}
    needed = set(policy.TASK_OF.values()) | {task for _fixer, task in policy.INPUT_SENDERS.values()}
    bad = sorted(t for t in needed if not (rows.get(t) or {}).get("owner_role", "").strip())
    srcs = [rows[t]["src"] if t in rows else (policy.INPUT_FILES["checklist"], WHOLE_FILE) for t in bad]
    return bad, "close-checklist tasks that are missing or have no owner_role (%s)" % (", ".join(bad) or "none"), \
        srcs, _whole("checklist")


def _counted(types, detail, whole):
    """A check with a reconciliation counterpart: it counts the counterpart's differences."""
    def check(_inp, recon, _close):
        found = [d for d in recon.differences if d.type in types]
        return found, detail, [src for d in found for src in d.srcs], _whole(*whole)
    return check


def _cash_reconciled(_inp, _recon, close):
    cash = close.cash_recon
    sides = cash.ledger_src + cash.bank_src
    detail = "ledger cash less reconciling items, against the bank"
    return ([cash.unreconciled] if cash.unreconciled else []), detail, sides, sides


def _own(check):
    return lambda inp, _recon, _close: check(inp)


# name -> function(inputs, recon, close) returning (offenders, detail, offender srcs, whole-file srcs when clean)
_CHECKS = {
    CHECK.summary_vs_detail: _own(_summary_vs_detail), CHECK.net_formula: _own(_net_formula),
    CHECK.statuses: _own(_statuses),
    CHECK.card_numbers: _own(_card_numbers), CHECK.missing_inputs: _own(_missing_inputs),
    CHECK.clearing_days_vs_entries: _counted(
        (TYPE.processor_entry_missing, TYPE.processor_entry_misdated),
        "processor clearing days with no ledger entry, or an entry posted on another date", ("processor", "gl_lines")),
    CHECK.settlements_vs_debits: _counted(
        (TYPE.settlement_not_debited, TYPE.settlement_amount_diff), "settlement days and debits that do not pair",
        ("mc_summary", "bank")),
    CHECK.stale_authorisations: _counted(
        (TYPE.auth_stale,), "authorised rows older than the stale limit in working days, from the authorisation date",
        ("processor",)),
    CHECK.impossible_dates: _counted((TYPE.auth_after_clearing,), "rows authorised after they cleared", ("processor",)),
    CHECK.references: _counted(
        (TYPE.reference_bad,), "cleared rows whose network reference is empty, mistyped or needed normalising",
        ("processor",)),
    CHECK.cash_reconciled: _cash_reconciled, CHECK.inputs_cover_period: _own(_inputs_cover_period),
    CHECK.checklist_tasks_owned: _own(_checklist_tasks_owned),
}


def _one(name, inp, recon, close):
    try:
        found, detail, srcs, clean_srcs = _CHECKS[name](inp, recon, close)
        if name == CHECK.statuses:  # counts the rows kept out of money; fails only on an unknown status or a dated row
            found, flagged = found
            passed, count = not flagged, len(found)
        else:
            passed, count = not found, len(found)
        srcs = list(dict.fromkeys(tuple(s) for s in srcs)) or clean_srcs
        return Check(name, passed, count, detail, srcs)
    except Exception as exc:  # noqa: BLE001 - a check reports its own failure, never crashes the run
        return Check(name, False, 0, "could not run: %s" % exc, _whole("processor"))


def run(inputs, recon, close):
    return [_one(name, inputs, recon, close) for name in policy.CHECKS]
