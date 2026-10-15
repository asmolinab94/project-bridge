"""Three-leg reconciliation (spec E3): processor vs Mastercard per transaction, Mastercard daily net vs the bank debit,
bridge account and Mastercard payable vs the ledger. Every difference is classified; none is estimated."""

import datetime
from collections import namedtuple
from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_UP, Decimal

from bridge import policy
from bridge.inputs import ZERO

Match = namedtuple("Match", ["processor_row", "mc_row", "method"])
# One side of a leg-3 pair: the amount is debit-positive on 1110; `kind` is the bank line's kind (None for the ledger).
Cash = namedtuple("Cash", ["date", "key", "ref", "amount", "srcs", "kind"], defaults=[None])
Transit = namedtuple("Transit", ["key", "ledger_first", "amount", "srcs"])  # a pair across the cut-off, signed

ONE_DAY = datetime.timedelta(days=1)
TYPE = policy.TYPE


@dataclass
class Difference:
    leg: int
    type: str
    cls: str
    gross: Decimal
    net: Decimal
    srcs: list
    age_wd: int
    requires_explanation: bool
    escalates: bool
    key: str
    controller_action: bool
    origin: object = None  # the date ageing counts from; a data-issue flag carries its own row's date, on a working day
    who_fixes: str = ""    # whoever can fix the cause (policy.FIXER_OF)
    action: str = ""       # what they do (policy.ACTION_OF)
    task: str = ""         # the close-checklist task that covers it (policy.TASK_OF)
    clara_owner: str = ""  # that task's owner_role, read from the checklist


@dataclass
class Recon:
    matches: list = field(default_factory=list)
    differences: list = field(default_factory=list)
    leg1_by_type: dict = field(default_factory=dict)
    unexplained_total: Decimal = ZERO
    unexplained_escalates: bool = False
    transits: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)         # leg -> figure -> (count, USD or None): the page's match figures
    leg1_sides: tuple = ((), ())                       # the leg-1 universe: (processor rows, Mastercard rows)
    settlement_days: list = field(default_factory=list)  # leg 2: (Mastercard summary row, the debits that paid it)


def is_working_day(day):
    return day.weekday() < policy.WEEKEND_FROM and day not in policy.HOLIDAYS


def working_day_on_or_after(day):
    return day if is_working_day(day) else next_working_day(day)


def next_working_day(day):
    day += ONE_DAY
    while not is_working_day(day):
        day += ONE_DAY
    return day


def age_wd(origin):
    """Working days after `origin` up to and including the cut-off date."""
    count, day = 0, origin
    while day < policy.CUTOFF_DATE:
        day += ONE_DAY
        count += is_working_day(day)
    return count


def _difference(leg, type_, gross, net, srcs, key, origin=None, like=None, fixer=None, task=None):
    """`like` takes the fixer, task and action of another type (the unrecorded half of a duplicate debit); `fixer` and
    `task` override them (a side other than the usual one is wrong, or the file a missing input belongs to)."""
    like = like or type_
    fixer = fixer or policy.FIXER_OF.get(like, "")
    cls = policy.CLASS_OF[type_]
    flag = cls == policy.CLASS.data_issue
    open_item = cls in policy.OPEN_CLASSES
    age = age_wd(origin) if open_item and origin else 0
    return Difference(
        leg=leg, type=type_, cls=cls, gross=ZERO if flag else gross, net=ZERO if flag else net,
        srcs=list(dict.fromkeys(tuple(s) for s in srcs)), age_wd=age,
        requires_explanation=open_item and abs(gross) >= policy.EXPLAIN_THRESHOLD,
        escalates=open_item and age > policy.ESCALATE_AGE_WD, key=key,
        controller_action=type_ in policy.CONTROLLER_ACTION_TYPES, origin=origin,
        who_fixes=fixer, action=policy.ACTION_BY_FIXER.get((like, fixer)) or policy.ACTION_OF.get(like, ""),
        task=task or policy.TASK_OF.get(like, ""))


def _flag(leg, type_, srcs, key, origin=None, **owner):
    return _difference(leg, type_, ZERO, ZERO, srcs, key, origin, **owner)


# --- Leg 1 ---------------------------------------------------------------------------------------------------------

def _conversion_off(row):
    """The row's USD amount is not its local amount converted at its own rate (local per USD)."""
    converted = row["amount_local"] / row["fx_rate"] if row["fx_rate"] else row["amount_usd"]
    return converted.quantize(policy.CENT, ROUND_HALF_UP) != row["amount_usd"]


def _classify_pair(p, m):
    """The difference of a matched pair, in the spec's order: month cut-off, sign, local amount, rate; None if equal."""
    srcs, key, owner = [p["src"], m["src"]], p["txn_id"], {}
    if not policy.in_leg1_period(m["clearing_date"]):  # Mastercard cleared outside September: counts as zero
        return _difference(1, TYPE.month_cutoff, p["amount_usd"], p["net"], srcs, key, p["clearing_date"])
    gross, net = p["amount_usd"] - m["amount_usd"], p["net"] - m["net_settlement_usd"]
    if gross == 0 and net == 0:
        return None
    if (p["amount_local"] < 0) != (m["amount_local"] < 0):
        type_ = TYPE.sign_flip
    elif p["amount_local"] != m["amount_local"]:
        type_ = TYPE.amount_diff
    elif p["fx_rate"] != m["fx_rate"]:
        type_ = TYPE.fx_rate_diff
    elif max(abs(gross), abs(net)) <= policy.TOL_TXN:
        type_ = TYPE.rounding
    else:
        type_ = TYPE.usd_conversion_error
        if _conversion_off(m) and not _conversion_off(p):  # only Mastercard's own conversion is wrong
            owner = {"fixer": policy.FIXER.mastercard}
    return _difference(1, type_, gross, net, srcs, key, p["clearing_date"], **owner)


def _fuzzy_key(row):
    return (row["card_last4"], row["txn_currency"], row["amount_local"], row["clearing_date"])


def _reference_matches(procs, mc_rows):
    """Reference pass: (matches, duplicates as (duplicate, original, mc row or None), unmatched originals)."""
    by_ref = {}
    for m in mc_rows:
        by_ref.setdefault(m["network_ref"], m)
    groups = {}
    for p in sorted(procs, key=lambda r: r["txn_id"]):
        if p["ref_norm"]:
            groups.setdefault(p["ref_norm"], []).append(p)
    matches, duplicates = [], []
    for ref, rows in groups.items():
        m = by_ref.get(ref)
        for i, p in enumerate(rows):
            if m:
                matches.append(Match(p, m, policy.MATCH.exact if p["ref_status"] == policy.REF_STATUS.exact
                                         else policy.MATCH.normalised))
            if i:
                duplicates.append((p, rows[0], m))
    return matches, duplicates


def _fuzzy_matches(procs, mc_rows):
    """Reference-less processor rows against Mastercard rows still free, on last 4 + currency + local amount +
    clearing date; accepted only when one row stands on each side. Returns (matches, ambiguous flags)."""
    free_proc, free_mc = {}, {}
    for p in procs:
        free_proc.setdefault(_fuzzy_key(p), []).append(p)
    for m in mc_rows:
        free_mc.setdefault(_fuzzy_key(m), []).append(m)
    matches, flags = [], []
    for key, ps in free_proc.items():
        ms = free_mc.get(key, [])
        if len(ps) == 1 and len(ms) == 1:
            matches.append(Match(ps[0], ms[0], policy.MATCH.fuzzy))
        elif ms:
            flags.append(_flag(1, TYPE.ambiguous_match, [r["src"] for r in ps + ms], min(r["network_ref"] for r in ms)))
    return matches, flags


def _leg1(inputs):
    procs = [p for p in inputs.processor
             if p["status"] == policy.STATUS.CLEARED and policy.in_leg1_period(p["clearing_date"])]
    by_ref = [p for p in procs if p["ref_norm"]]
    matches, duplicates = _reference_matches(by_ref, inputs.mc_detail)
    taken = {m.mc_row["src"] for m in matches}
    fuzzy, flags = _fuzzy_matches([p for p in procs if not p["ref_norm"]],
                                  [m for m in inputs.mc_detail if m["src"] not in taken])
    matches += fuzzy
    dup_srcs = {d["src"] for d, _original, _m in duplicates}
    paired = {m.processor_row["src"] for m in matches}
    taken |= {m.mc_row["src"] for m in fuzzy}

    found = list(flags)
    for d, original, m in duplicates:
        found.append(_difference(1, TYPE.processor_duplicate, d["amount_usd"], d["net"],
                                 [d["src"], original["src"]] + ([m["src"]] if m else []), d["txn_id"],
                                 d["clearing_date"]))
    originals = [m for m in matches if m.processor_row["src"] not in dup_srcs]
    for match in originals:
        diff = _classify_pair(match.processor_row, match.mc_row)
        if diff:
            found.append(diff)
    for p in procs:
        if p["src"] not in paired and p["src"] not in dup_srcs:
            found.append(_difference(1, TYPE.processor_only, p["amount_usd"], p["net"], [p["src"]], p["txn_id"],
                                     p["clearing_date"]))
    for m in inputs.mc_detail:
        if m["src"] not in taken and policy.in_leg1_period(m["clearing_date"]):
            found.append(_difference(1, TYPE.mastercard_only, -m["amount_usd"], -m["net_settlement_usd"], [m["src"]],
                                     m["network_ref"], m["clearing_date"]))

    for p in procs:
        if p["ref_status"] != policy.REF_STATUS.exact:
            found.append(_flag(1, TYPE.reference_bad, [p["src"]], p["txn_id"], p["clearing_date"]))
    for p in inputs.processor:
        if p["auth_date"] and p["clearing_date"] and p["auth_date"] > p["clearing_date"]:
            found.append(_flag(1, TYPE.auth_after_clearing, [p["src"]], p["txn_id"], p["clearing_date"]))
        if p["status"] == policy.STATUS.AUTHORIZED and p["auth_date"] and age_wd(p["auth_date"]) > policy.STALE_AUTH_WD:
            found.append(_flag(1, TYPE.auth_stale, [p["src"]], p["txn_id"], p["auth_date"]))
    mc_rows = [m for m in inputs.mc_detail if m["src"] in taken or policy.in_leg1_period(m["clearing_date"])]
    return matches, found, (procs, mc_rows), originals


def _usd(rows, column):
    return sum((r[column] for r in rows), ZERO)


def _leg1_counts(sides, originals, found):
    """Rows on each side; pairs with no shown difference (their processor USD); pairs with one, the processor's
    duplicate rows, and the rows on one side only (the exceptions' net)."""
    procs, mc_rows = sides
    pairs = [d for d in found if d.type in policy.PAIR_TYPES and d.cls != policy.CLASS.auto_cleared]
    differing = {d.srcs[0] for d in pairs}
    equal = [m.processor_row for m in originals if m.processor_row["src"] not in differing]
    one_side = {t: [d for d in found if d.type == t]
                for t in (TYPE.processor_duplicate, TYPE.processor_only, TYPE.mastercard_only)}
    net = lambda diffs: sum((d.net for d in diffs), ZERO)  # noqa: E731
    return dict({"processor_rows": (len(procs), _usd(procs, "amount_usd")),
                 "mastercard_rows": (len(mc_rows), _usd(mc_rows, "amount_usd")),
                 "matched_equal": (len(equal), _usd(equal, "amount_usd")), "matched_diff": (len(pairs), net(pairs))},
                **{t: (len(diffs), net(diffs)) for t, diffs in one_side.items()})


# --- Leg 2 ---------------------------------------------------------------------------------------------------------

def _settlement_debits(inputs):
    """(debits, duplicates): the settlement debits, and the bank duplicates (a repeated bank_reference) as
    (duplicate, original) set aside before pairing."""
    first_seen, debits, duplicates = {}, [], []
    for b in inputs.bank:
        if b["kind"] != policy.KIND.settlement:
            continue
        original = first_seen.setdefault(b["bank_reference"], b)
        if original is b:
            debits.append(b)
        else:
            duplicates.append((b, original))
    return debits, duplicates


def _settlement_days(debits, inputs):
    """September's Mastercard summary days (settled on or before 30-Sep, debited on the next working day on or after
    1-Sep), each with the settlement debits posted on its debit day."""
    by_day = {}
    for b in debits:
        by_day.setdefault(b["posting_date"], []).append(b)
    return [(s, by_day.get(next_working_day(s["settlement_date"]), [])) for s in inputs.mc_summary
            if policy.by_period_end(s["settlement_date"])
            and next_working_day(s["settlement_date"]) >= policy.PERIOD_START]


def _leg2(debits, duplicates, days):
    """Each summary day against the settlement debit posted on its debit day; the difference is the bank's minus
    Mastercard's."""
    found = [_difference(2, TYPE.bank_duplicate_debit, b["debit_usd"], b["debit_usd"], [b["src"], original["src"]],
                         b["line_id"], b["posting_date"]) for b, original in duplicates]
    used = set()
    for s, paid in days:
        used.update(b["src"] for b in paid)
        if not paid:
            found.append(_difference(2, TYPE.settlement_not_debited, s["net_settlement_usd"], s["net_settlement_usd"],
                                     [s["src"]], s["settlement_date"].isoformat(), s["settlement_date"]))
            continue
        gap = sum((b["debit_usd"] for b in paid), ZERO) - s["net_settlement_usd"]
        if gap:
            tolerated = abs(gap) <= policy.TOL_DAY
            found.append(_difference(2, TYPE.rounding if tolerated else TYPE.settlement_amount_diff, gap, gap,
                                     [s["src"]] + [b["src"] for b in paid], paid[0]["line_id"],
                                     paid[0]["posting_date"]))
    for b in debits:
        # A September debit on no summary day: the whole debit is the difference.
        if b["src"] not in used and policy.by_period_end(b["posting_date"]):
            found.append(_difference(2, TYPE.settlement_amount_diff, b["debit_usd"], b["debit_usd"], [b["src"]],
                                     b["line_id"], b["posting_date"]))
    return found


def _leg2_counts(days, duplicates):
    paid = [s for s, debits in days if debits]
    unpaid = [s for s, debits in days if not debits]
    net = "net_settlement_usd"
    return {"settlement_days": (len(days), _usd([s for s, _d in days], net)), "paired": (len(paid), _usd(paid, net)),
            "unpaired": (len(unpaid), _usd(unpaid, net)),
            "duplicate_debits": (len(duplicates), _usd([b for b, _o in duplicates], "debit_usd"))}


# --- Leg 3 ---------------------------------------------------------------------------------------------------------

def _pair_cash(inputs, entries, duplicate_lines):
    """Bank lines against ledger entries holding a bridge-cash line, by reference and amount, one to one, both sides in
    date order. The leftovers of one reference then pair in date order as a ledger amount difference (ledger minus
    bank); any other bank line is unrecorded and any other entry unmatched. Only a pair across the cut-off is in
    transit, and only September leftovers are September exceptions. Returns (differences, transits)."""
    cash_account, found, transits = policy.ACCOUNTS["bridge_cash"], [], []
    ledger = sorted((Cash(lines[0]["posting_date"], je_id, lines[0]["reference"], amount, [g["src"] for g in lines])
                     for je_id, lines in entries.items()
                     if (amount := sum((g["debit_usd"] - g["credit_usd"] for g in lines
                                        if g["account"] == cash_account), ZERO))),
                    key=lambda e: (e.date, e.key))
    bank = [Cash(b["posting_date"], b["line_id"], b["bank_reference"], b["credit_usd"] - b["debit_usd"], [b["src"]],
                 b["kind"]) for b in sorted(inputs.bank, key=lambda b: (b["posting_date"], b["line_id"]))]
    pairs, left = [], []
    for b in bank:
        hit = next((e for e in ledger if e.ref == b.ref and e.amount == b.amount), None)
        if hit:
            ledger.remove(hit)
            pairs.append((hit, b))
        else:
            left.append(b)
    for b in left:
        mate = next((e for e in ledger if e.ref == b.ref), None)
        if mate:
            ledger.remove(mate)
            gap = mate.amount - b.amount
            if policy.by_period_end(min(mate.date, b.date)):  # aged from the September side, the bank's if both are
                found.append(_difference(3, TYPE.ledger_amount_diff, gap, gap, mate.srcs + b.srcs, b.key,
                                         b.date if policy.by_period_end(b.date) else mate.date))
            pairs.append((mate, b))
        elif policy.by_period_end(b.date):
            like = TYPE.bank_duplicate_debit if b.key in duplicate_lines else None  # resolved as the duplicate is
            found.append(_difference(3, TYPE.bank_line_unrecorded, abs(b.amount), abs(b.amount), b.srcs, b.key,
                                     b.date, like))
    for e in ledger:
        if policy.by_period_end(e.date):
            found.append(_difference(3, TYPE.ledger_entry_unmatched, abs(e.amount), abs(e.amount), e.srcs, e.key,
                                     e.date))
    for e, b in pairs:
        ledger_first = policy.by_period_end(e.date)
        if ledger_first == policy.by_period_end(b.date):
            continue
        # How much the pair makes the September ledger exceed the September bank; the side after 30-Sep has no effect.
        item = e.amount if ledger_first else -b.amount
        transits.append(Transit(b.key, ledger_first, item, e.srcs + b.srcs))
        # The crossing row carries the matched part (the smaller amount), signed like the item.
        matched = min(abs(e.amount), abs(b.amount)) * (1 if item > 0 else -1)
        if not ledger_first:
            type_ = TYPE.ledger_posted_late
        else:
            type_ = TYPE.funding_in_transit if b.kind == policy.KIND.funding else TYPE.bank_not_yet_posted
        origin = e.date if ledger_first else b.date  # aged from the September side
        found.append(_difference(3, type_, matched, matched, e.srcs + b.srcs, b.key, origin))
    return found, transits


def _leg3(inputs, duplicate_lines):
    found, accounts = [], policy.ACCOUNTS
    by_ref, entries = {}, {}
    for g in inputs.gl_lines:
        by_ref.setdefault(g["reference"], []).append(g)
        entries.setdefault(g["je_id"], []).append(g)
    bank_by_ref = {}
    for b in inputs.bank:
        bank_by_ref.setdefault(b["bank_reference"], []).append(b)

    days = {}
    for p in inputs.processor:
        if p["status"] == policy.STATUS.CLEARED and policy.in_leg1_period(p["clearing_date"]):
            days.setdefault(p["clearing_date"], []).append(p)
    for day, rows in sorted(days.items()):
        key = day.strftime(policy.PROCESSOR_ENTRY_REF)
        entry = [g for g in by_ref.get(key, []) if g["source"] == policy.GL_SOURCES["processor"]]
        gross, net = sum((r["amount_usd"] for r in rows), ZERO), sum((r["net"] for r in rows), ZERO)
        if not entry:
            found.append(_difference(3, TYPE.processor_entry_missing, gross, net, [r["src"] for r in rows], key, day))
        elif any(g["posting_date"] != day for g in entry):
            found.append(_difference(3, TYPE.processor_entry_misdated, gross, net, [g["src"] for g in entry], key, day))

    paired, transits = _pair_cash(inputs, entries, duplicate_lines)
    found += paired

    for g_ref, lines in by_ref.items():
        pending = [g for g in lines if g["account"] == accounts["suspense"]]
        amount = abs(sum((g["credit_usd"] - g["debit_usd"] for g in pending), ZERO))
        if amount:
            banks = bank_by_ref.get(g_ref, [])
            found.append(_difference(3, TYPE.suspense_pending_payer, amount, amount,
                                     [g["src"] for g in pending] + [b["src"] for b in banks],
                                     banks[0]["line_id"] if banks else g_ref,
                                     banks[0]["posting_date"] if banks else pending[0]["posting_date"]))

    accrued = any(g["account"] == accounts["accrued_fees"] and policy.by_period_end(g["posting_date"])
                  for g in inputs.gl_lines)
    for b in inputs.bank:
        if b["kind"] == policy.KIND.invoice and not accrued:
            found.append(_difference(3, TYPE.invoice_not_accrued, b["debit_usd"], b["debit_usd"],
                                     [b["src"]] + [g["src"] for g in by_ref.get(b["bank_reference"], [])],
                                     b["line_id"], b["posting_date"]))

    mapped = set(accounts.values())
    for je_id, lines in entries.items():
        if any(g["account"] not in mapped for g in lines):  # never dropped in silence
            found.append(_flag(3, TYPE.account_unmapped, [g["src"] for g in lines], je_id,
                               lines[0]["posting_date"]))

    for what, src in inputs.missing:
        fixer, task = policy.INPUT_SENDERS[inputs.missing_files[what]]
        found.append(_flag(3, TYPE.input_missing, [src], src[1], fixer=fixer, task=task))
    return found, transits


def _with_clara_owner(d, checklist):
    """The difference with the owner_role of its checklist task, and that task's row among its sources."""
    row = checklist.get(d.task)
    return replace(d, clara_owner=row["owner_role"], srcs=d.srcs + [row["src"]]) if row else d


def reconcile(inputs):
    matches, leg1, sides, originals = _leg1(inputs)
    debits, duplicates = _settlement_debits(inputs)
    days = _settlement_days(debits, inputs)
    leg3, transits = _leg3(inputs, {b["line_id"] for b, _original in duplicates})
    checklist = {row["task_id"]: row for row in inputs.checklist}
    differences = [_with_clara_owner(d, checklist) for d in leg1 + _leg2(debits, duplicates, days) + leg3]
    by_type = {}
    for d in differences:
        if d.leg == 1 and d.cls != policy.CLASS.data_issue:
            by_type[d.type] = by_type.get(d.type, ZERO) + d.net
    unexplained = sum((abs(d.gross) for d in differences if d.type in policy.UNEXPLAINED_TYPES), ZERO)
    counts = {"1": _leg1_counts(sides, originals, leg1), "2": _leg2_counts(days, duplicates)}
    return Recon(matches, differences, by_type, unexplained, unexplained > policy.ESCALATE_UNEXPLAINED, transits,
                 counts, sides, days)
