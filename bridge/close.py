"""Close (spec E4): the closed list of proposed entries, balances before and after, cash reconciliation, close tracker.
Nothing is posted; every entry is balanced, unsigned and proposed."""

from dataclasses import dataclass, field
from decimal import Decimal

from bridge import policy
from bridge.inputs import ZERO
from bridge.recon import ONE_DAY

ACC = policy.ACCOUNTS


@dataclass
class Entry:
    id: str
    title: str
    lines: list
    status: str
    missing_evidence: object
    approval_level: str
    total_debits: Decimal
    srcs: list
    line_tags: dict = field(default_factory=dict)   # line index -> cost behaviour, on an itemised entry
    line_srcs: dict = field(default_factory=dict)   # line index -> the one row that line cites, on an itemised entry
    preparer: str = ""
    approver: str = ""


@dataclass
class CashItem:
    description: str
    amount: Decimal  # how much the item makes the ledger exceed the bank, signed
    src: list


@dataclass
class CashRecon:
    ledger_balance: Decimal
    reconciling_items: list
    bank_balance: Decimal
    unreconciled: Decimal
    ledger_src: list
    bank_src: list


@dataclass
class Close:
    entries: list = field(default_factory=list)
    balances: dict = field(default_factory=dict)
    cash_recon: object = None
    tracker: list = field(default_factory=list)
    # What Mastercard says Clara owes at 30-Sep: (src, USD) settlement rows, (src, USD) timing rows, the settlement days
    payable_owed: tuple = field(default_factory=lambda: ([], [], []))
    people: dict = field(default_factory=dict)   # role -> (person, src of the e-mail fragment naming them)


def _lines(deltas):
    """Debit-positive account deltas as entry lines, debits first, zero deltas dropped."""
    lines = [(account, delta, ZERO) if delta > 0 else (account, ZERO, -delta)
             for account, delta in deltas.items() if delta]
    return sorted(lines, key=lambda line: (line[1] == 0, line[0]))


def _feed_deltas(gross, interchange, fee):
    """What the processor feed posts for a day's totals, as net debit-positive deltas per account."""
    amounts = {"amount_usd": gross, "interchange_usd": interchange, "scheme_fee_usd": fee}
    deltas = {}
    for debit, credit, column in policy.PROCESSOR_POSTING:
        deltas[ACC[debit]] = deltas.get(ACC[debit], ZERO) + amounts[column]
        deltas[ACC[credit]] = deltas.get(ACC[credit], ZERO) - amounts[column]
    return deltas


def _add(total, deltas):
    for account, delta in deltas.items():
        total[account] = total.get(account, ZERO) + delta
    return total


def _build_entries(inputs, recon):
    processor = {r["src"]: r for r in inputs.processor}
    mastercard = {r["src"]: r for r in inputs.mc_detail}
    ledger = {g["src"]: g for g in inputs.gl_lines}
    found = {}
    for d in recon.differences:
        found.setdefault(d.type, []).append(d)
    entries = []

    def add(title, deltas, diffs, srcs=(), evidence_type=None, lines=None):
        lines = lines or _lines(deltas)
        total = sum((debit for _a, debit, _c in lines), ZERO)
        if not total:
            return None
        evidence = policy.CONDITIONAL_EVIDENCE.get(evidence_type)
        entries.append(Entry(
            id="E%02d" % (len(entries) + 1), title=title, lines=lines,
            status=policy.ENTRY_STATUSES[1] if evidence else policy.ENTRY_STATUSES[0], missing_evidence=evidence,
            approval_level=policy.approval_level(total), total_debits=total,
            srcs=list(dict.fromkeys(tuple(s) for d in diffs for s in d.srcs
                                    if s[0] != policy.INPUT_FILES["checklist"])) + list(srcs)))
        return entries[-1]

    for d in found.get(policy.TYPE.processor_entry_missing, []):
        rows = [processor[s] for s in d.srcs if s in processor]
        add("Post the missing processor entry %s" % d.key,
            _feed_deltas(*(sum((r[c] for r in rows), ZERO)
                           for c in ("amount_usd", "interchange_usd", "scheme_fee_usd"))),
            [d])
    def late_lines(d):
        return [ledger[s] for s in d.srcs if s in ledger and not policy.by_period_end(ledger[s]["posting_date"])]

    for d in found.get(policy.TYPE.processor_entry_misdated, []):
        late = late_lines(d)
        posted = late[0]["posting_date"] if late else d.origin
        add("Post %s on its clearing day %s and reverse the %s posting in October" % (
                d.key, d.origin.strftime(policy.DAY_FORMAT), posted.strftime(policy.DAY_FORMAT)),
            _add({}, {g["account"]: g["debit_usd"] - g["credit_usd"] for g in late}), [d])
    unrecorded = {d.key for d in found.get(policy.TYPE.bank_line_unrecorded, [])}
    for d in found.get(policy.TYPE.bank_duplicate_debit, []):
        # The debit the ledger holds is moved off the payable; one it never recorded is booked against cash.
        credit = ACC["bridge_cash"] if d.key in unrecorded else ACC["mc_payable"]
        add("Recover the duplicate bank debit %s" % d.key, {ACC["mc_receivable"]: d.gross, credit: -d.gross}, [d])
    for d in found.get(policy.TYPE.suspense_pending_payer, []):
        add("Clear suspense receipt %s to the customer receivable" % d.key,
            {ACC["suspense"]: d.gross, ACC["card_receivable"]: -d.gross}, [d], evidence_type=d.type)
    if policy.TYPE.invoice_not_accrued in found:  # a ledger that already holds the accrual is not accrued twice
        items = [line for line in inputs.invoice_lines if line["amount_usd"]]
        variable = [line["item"] for line in items if line["item"] in policy.VARIABLE_INVOICE_ITEMS]
        total = sum((line["amount_usd"] for line in items), ZERO)
        # The chart has no sub-account for a variable line item, so every debit sits on the programme-cost account.
        fixed = [line["item"] for line in items if line["item"] not in policy.VARIABLE_INVOICE_ITEMS]
        title = "Accrue the Mastercard program invoice by line item"
        if variable:
            title += " (%s: variable cost, no sub-account in the chart, so on %s; %s: fixed programme cost; reverse " \
                     "on %s)" % (", ".join(variable), ACC["network_fees"], ", ".join(fixed),
                                 (policy.PERIOD_END + ONE_DAY).strftime(policy.DAY_FORMAT).lstrip("0"))
        entry = add(title, {}, found[policy.TYPE.invoice_not_accrued], [line["src"] for line in inputs.invoice_lines],
                    lines=[(ACC["network_fees"], line["amount_usd"], ZERO) for line in items]
                    + [(ACC["accrued_fees"], ZERO, total)])
        if entry:
            entry.line_tags = {i: policy.COST.variable if line["item"] in policy.VARIABLE_INVOICE_ITEMS
                               else policy.COST.fixed for i, line in enumerate(items)}
            entry.line_srcs = {i: [line["src"]] for i, line in enumerate(items)}
    for type_ in policy.CORRECTION_TYPES:
        deltas = {}
        diffs = [d for d in found.get(type_, []) if d.who_fixes == policy.FIXER.processor]
        for d in diffs:
            used = d.srcs[:1] if type_ in policy.SINGLE_ROW_TYPES else d.srcs[:2]
            parts = [(processor[s], 1) if s in processor else (mastercard[s], -1) for s in used]
            totals = [sum((sign * row[c] for row, sign in parts), ZERO)
                      for c in ("amount_usd", "interchange_usd", "scheme_fee_usd")]
            _add(deltas, {a: -v for a, v in _feed_deltas(*totals).items()})  # reverse what the feed overstated
        add("Correct processor errors: %s" % type_.replace("_", " "), deltas, diffs, evidence_type=type_)
    for d in found.get(policy.TYPE.ledger_posted_late, []):  # the October entry, mirrored onto 30-Sep
        late = late_lines(d)
        add("Move %s into September: post it on %s and reverse the %s posting in October" % (
                late[0]["je_id"], policy.PERIOD_END.strftime(policy.DAY_FORMAT),
                late[0]["posting_date"].strftime(policy.DAY_FORMAT)),
            _add({}, {g["account"]: g["debit_usd"] - g["credit_usd"] for g in late}), [d])
    for d in found.get(policy.TYPE.usd_conversion_error, []):
        if d.who_fixes == policy.FIXER.mastercard:  # Clara settled its net: the gap is owed
            owed = "receivable from" if d.net < 0 else "payable to"
            add("Adjust Mastercard's USD conversion error %s (%s Mastercard)" % (d.key, owed),
                {ACC["mc_receivable"]: -d.net, ACC["mc_payable"]: d.net}, [d])
    return entries


def _balances(inputs, entries):
    before, src = {}, {}
    for row in inputs.gl_opening:
        before[row["account"]] = row["opening_balance_usd_dr_positive"]
        src[row["account"]] = [row["src"]]
    for g in inputs.gl_lines:
        if policy.by_period_end(g["posting_date"]):
            before[g["account"]] = before.get(g["account"], ZERO) + g["debit_usd"] - g["credit_usd"]
            src.setdefault(g["account"], []).append(g["src"])
    confirmed, every = {}, {}
    for entry in entries:
        for account, debit, credit in entry.lines:
            if entry.status == policy.ENTRY_STATUSES[0]:
                _add(confirmed, {account: debit - credit})
            _add(every, {account: debit - credit})
    return {account: {"before": before.get(account, ZERO),
                      "after_confirmed": before.get(account, ZERO) + confirmed.get(account, ZERO),
                      "after_all": before.get(account, ZERO) + every.get(account, ZERO),
                      "src": src.get(account, [])}
            for account in (ACC[name] for name in policy.ACCOUNT_ORDER)}


def _cash_recon(inputs, recon, balances):
    cash = balances[ACC["bridge_cash"]]
    in_period = [b for b in inputs.bank if policy.by_period_end(b["posting_date"])]
    last = max(in_period, key=lambda b: (b["posting_date"], b["line_id"]), default=None)
    items = [CashItem(policy.TRANSIT_TEXT[t.ledger_first] % t.key, t.amount, list(t.srcs)) for t in recon.transits]
    bank = last["running_balance_usd"] if last else ZERO
    return CashRecon(cash["before"], items, bank, cash["before"] - sum((i.amount for i in items), ZERO) - bank,
                     cash["src"], [last["src"]] if last else [])


def _people(inputs):
    """role -> (person, the (file, fragment) source naming them)."""
    file_name = policy.INPUT_FILES["treasury_email"]
    return {role: (person, (file_name, fragment))
            for role, (person, fragment) in policy.people(inputs.treasury_email).items()}


def _tracker(inputs, people):
    rows = {r["task_id"]: r for r in inputs.checklist}
    open_ids = {t for t, r in rows.items() if r["status_wd3_0900"] != policy.TASK_DONE}
    needs = {t: [d for d in rows[t]["depends_on"].split(";") if d in rows] for t in rows}
    memo = {}

    def chain(task, deps_of, visiting=()):
        """Longest chain of open tasks ending at `task` along `deps_of`; a cycle in edited data counts as zero."""
        if task not in open_ids or task in visiting:
            return 0
        key = (id(deps_of), task)
        if key not in memo:
            memo[key] = 1 + max([chain(d, deps_of, visiting + (task,)) for d in deps_of[task]] or [0])
        return memo[key]

    needed_by = {t: [u for u in rows if t in needs[u]] for t in rows}
    longest = max([chain(t, needs) for t in rows] or [0])
    tracker = []
    for task, row in rows.items():
        role, what = policy.TOOL_EVIDENCE.get(task, ("", ""))
        on_path = bool(longest) and task in open_ids and chain(task, needs) + chain(task, needed_by) - 1 == longest
        blocked = [d for d in needs[task] if d in open_ids]
        if not blocked and row["status_wd3_0900"] == policy.TASK_BLOCKED:
            blocked = policy.BLOCKED_OUTSIDE
        named = people.get(row["owner_role"])
        out = {}
        for column, value in row.items():   # the person sits next to the role; the src also cites where the name is
            out[column] = [value, named[1]] if column == "src" and named else value
            if column == "owner_role":
                out["owner_name"] = named[0] if named else ""
        tracker.append(dict(out, blocked_by=blocked, on_critical_path=on_path,
                            tool_evidence=("%s: %s" % (role, what)) if role else ""))
    return tracker


def _payable_owed(inputs, recon):
    """([(src, USD)], [(src, USD)], [day]) Mastercard's own files say Clara owes at 30-Sep: the summary net of each
    settlement day the bank had not debited by 30-Sep (the pairing is leg 2's, and the days), and the net of each
    September transaction Mastercard cleared after 30-Sep (leg 1's month cut-off differences)."""
    unpaid = [(s, paid) for s, paid in recon.settlement_days
              if not any(policy.by_period_end(b["posting_date"]) for b in paid)]
    mastercard = {m["src"]: m for m in inputs.mc_detail}
    return ([(s["src"], s["net_settlement_usd"]) for s, _paid in unpaid],
            [(d.srcs[1], mastercard[d.srcs[1]]["net_settlement_usd"])
             for d in recon.differences if d.type == policy.TYPE.month_cutoff],
            [s["settlement_date"] for s, _paid in unpaid])


def build(inputs, recon):
    entries = _build_entries(inputs, recon)
    balances = _balances(inputs, entries)
    people = _people(inputs)
    return Close(entries, balances, _cash_recon(inputs, recon, balances), _tracker(inputs, people),
                 _payable_owed(inputs, recon), people)
