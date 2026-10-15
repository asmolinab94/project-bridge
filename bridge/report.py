"""Output (spec E5): the CSVs, the run manifest and the single-file page. Every table is built once, as rows of text,
and both the CSV writer and the page's JSON blob read that same table, so the page and the files cannot disagree."""

import csv
import base64
import collections
import datetime
import json
import os
import subprocess
from decimal import Decimal

from bridge import policy
from bridge.checks import summary_days
from bridge.inputs import ZERO
from bridge.recon import ONE_DAY

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")
DATA_TOKEN = "__BRIDGE_DATA__"
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FONT_TOKENS = {"__FONT_DMSANS__": "DMSans-Variable.ttf", "__FONT_INTER__": "Inter-Variable.ttf"}
FACET_BASES = ("program", "merchant")  # whose country a facet shows: the programme's or the merchant's
SRC_JOIN = ";"


def money(value):
    """Plain decimal text with at least two decimals; zero is 0.00."""
    cent = policy.CENT
    return format(value if value.as_tuple().exponent <= cent.as_tuple().exponent else value.quantize(cent), "f")


def text(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return money(value)
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return SRC_JOIN.join(text(v) for v in value)
    return "" if value is None else str(value)


def src_cell(srcs):
    """A `src` field (one (file, locator) pair or a list of them) as `file:locator` parts joined by `;`, once each."""
    pairs = srcs if srcs and isinstance(srcs[0], (list, tuple)) else [srcs]
    return SRC_JOIN.join(dict.fromkeys("%s:%s" % tuple(p) for p in pairs if p))


def _line_src(entry, i):
    """An entry line's src: the entry's, the rows other lines cite alone replaced by the one row this line cites."""
    if i not in entry.line_srcs:
        return entry.srcs
    alone = {tuple(s) for srcs in entry.line_srcs.values() for s in srcs}
    return [s for s in entry.srcs if tuple(s) not in alone] + entry.line_srcs[i]


def _table(columns, rows):
    return {"columns": list(columns), "rows": [{c: text(v) for c, v in row.items()} for row in rows]}


def tables(result):
    close, recon = result.close, result.recon
    cash = close.cash_recon
    name_of = lambda role: close.people.get(role, ("",))[0]  # noqa: E731
    exceptions = [dict(leg=d.leg, type=d.type, cls=d.cls, key=d.key, gross=d.gross, net=d.net, age_wd=d.age_wd,
                       requires_explanation=d.requires_explanation, escalates=d.escalates,
                       controller_action=d.controller_action, who_fixes=d.who_fixes, clara_owner=d.clara_owner,
                       clara_owner_name=name_of(d.clara_owner),
                       action=d.action, src=src_cell(d.srcs))
                  for d in recon.differences if d.cls != policy.CLASS.auto_cleared]
    entry_lines = [dict(entry_id=e.id, title=e.title, account=a, debit=dr, credit=cr, status=e.status,
                        approval_level=e.approval_level, missing_evidence=e.missing_evidence, preparer=e.preparer,
                        approver=e.approver, src=src_cell(_line_src(e, i)))
                   for e in close.entries for i, (a, dr, cr) in enumerate(e.lines)]
    balances = [dict(account=a, before=b["before"], after_confirmed=b["after_confirmed"], after_all=b["after_all"],
                     src=src_cell(b["src"])) for a, b in close.balances.items()]
    cash_rows = ([dict(line=policy.CASH_LINES[0], amount=cash.ledger_balance, src=src_cell(cash.ledger_src))]
                 + [dict(line=policy.CASH_LINES[1], amount=i.amount, src=src_cell(i.src))
                    for i in cash.reconciling_items]
                 + [dict(line=policy.CASH_LINES[2], amount=cash.bank_balance, src=src_cell(cash.bank_src)),
                    dict(line=policy.CASH_LINES[3], amount=cash.unreconciled,
                         src=src_cell(cash.ledger_src + cash.bank_src))])
    checks = [dict(name=c.name, passed=c.passed, count=c.count, detail=c.detail, src=src_cell(c.srcs))
              for c in result.checks]
    treasury = [dict(row, src=src_cell(row["src"])) for row in result.treasury.rows]
    tracker = [dict({k: v for k, v in row.items() if k != "src"}, src=src_cell(row["src"])) for row in close.tracker]
    return {
        "exceptions": _table(["leg", "type", "cls", "key", "gross", "net", "age_wd", "requires_explanation",
                              "escalates", "controller_action", "who_fixes", "clara_owner", "clara_owner_name",
                              "action", "src"],
                             exceptions),
        "proposed_entries": _table(["entry_id", "title", "account", "debit", "credit", "status", "approval_level",
                                    "missing_evidence", "preparer", "approver", "src"], entry_lines),
        "balances": _table(["account", "before", "after_confirmed", "after_all", "src"], balances),
        "cash_recon": _table(["line", "amount", "src"], cash_rows),
        "close_tracker": _table(list(tracker[0]) if tracker else ["src"], tracker),
        "checks": _table(["name", "passed", "count", "detail", "src"], checks),
        "treasury": _table(["date", "balance", "mc_debits", "days_of_coverage", "src"], treasury),
    }


def _files(inputs):
    """Per input file: whether it was read, the rows read and, for each date column, the first and last date."""
    out = {}
    for file_name in sorted(set(policy.INPUT_FILES.values()) | set(inputs.missing_files.values())):
        status = inputs.read_status.get(file_name)
        out[file_name] = {"status": policy.FILE_STATUS.read if status else policy.FILE_STATUS.missing,
                          "rows": status["rows"] if status else 0,
                          "dates": {c: {"first": text(lo), "last": text(hi)}
                                    for c, (lo, hi) in (status["dates"] if status else {}).items()}}
    return out


def totals(result):
    recon = result.recon
    by_class = {}
    for d in recon.differences:
        if d.cls != policy.CLASS.auto_cleared:
            by_class[d.cls] = by_class.get(d.cls, 0) + 1
    return {
        "leg1_difference_usd": text(sum(recon.leg1_by_type.values(), Decimal(0))),
        "leg1_by_type": {t: text(v) for t, v in recon.leg1_by_type.items()},
        "unexplained_total_usd": text(recon.unexplained_total),
        "unexplained_escalates": text(recon.unexplained_escalates),
        "exceptions_by_class": {c: str(n) for c, n in sorted(by_class.items())},
        "proposed_entries": str(len(result.close.entries)),
        "checks_failed": str(sum(1 for c in result.checks if not c.passed)),
        "matches": {leg: {name: dict({"count": str(count)}, **({"usd": text(usd)} if usd is not None else {}))
                          for name, (count, usd) in figures.items()} for leg, figures in recon.counts.items()},
    }


def _facets(result):
    """Country and date of each shown exception, in the exceptions table's order; for the page filters only. The date
    is the one ageing counts from; the country is the cited processor row's programme (the merchant's, for a
    Mastercard-only row) on leg 1 and empty on the other legs."""
    processor = {tuple(r["src"]): r for r in result.inputs.processor}
    mastercard = {tuple(r["src"]): r for r in result.inputs.mc_detail}
    facets = []
    for d in result.recon.differences:
        if d.cls == policy.CLASS.auto_cleared:
            continue
        cited = [processor[tuple(s)] for s in d.srcs if d.leg == 1 and tuple(s) in processor]
        country, basis = "", ""
        if cited:
            own = [r for r in cited if r["txn_id"] == d.key] or cited
            country, basis = own[0]["program_country"], FACET_BASES[0]
        elif d.leg == 1 and d.srcs and tuple(d.srcs[0]) in mastercard:
            country, basis = mastercard[tuple(d.srcs[0])]["merchant_country"], FACET_BASES[1]
        facets.append({"country": text(country), "country_basis": basis, "date": text(d.origin)})
    return facets


def _source_rows(result):
    """`file:locator` -> the cited input row, for CSV lines, e-mails and invoice items."""
    index = {}
    for attr in policy.INPUT_FILES:
        for row in getattr(result.inputs, attr):
            index["%s:%s" % tuple(row["src"])] = row
    return index


# Per data tab of the page: the column its summary groups by and the columns it sums; the columns a summary row carries
# from its rows; the columns whose values make a row's id (`#n` added for a repeat); the summary row's label; and
# either the total row (its label, whether it adds money up) or the column it subtotals by. Cash adds no money up:
# ledger, items and bank make no figure (its unreconciled line is the tie). The exceptions never add up across legs.
ACCOUNT_NAME = {number: name.replace("_", " ") for name, number in policy.ACCOUNTS.items()}
_NO = lambda row: False  # noqa: E731
PAGE = {
    "exceptions": dict(category="type", sums=("net",), carry=("leg", "cls"), row_id=("leg", "type", "key"),
                       label=lambda r: r["type"].replace("_", " "), subtotal="leg"),
    "proposed_entries": dict(category="entry_id", sums=("debit",), carry=("status", "approval_level"),
                             row_id=("entry_id", "account"), label=lambda r: "%s %s" % (r["entry_id"], r["title"]),
                             total=("Total", True)),
    "balances": dict(category="account", sums=("before", "after_confirmed", "after_all"), carry=(), row_id=("account",),
                     amount=lambda r: True,
                     label=lambda r: "%s %s" % (r["account"], ACCOUNT_NAME.get(r["account"], "")),
                     total=("Trial balance check: each column sums to zero", True)),
    "cash_recon": dict(category="line", sums=("amount",), carry=(), row_id=("line", "src"),
                       amount=lambda r: r["line"] == policy.CASH_LINES[0],
                       label=lambda r: r["line"].replace("_", " "),
                       total=("All lines, count only: the unreconciled line is the tie", False)),
    "close_tracker": dict(category="status_wd3_0900", sums=(), carry=(), row_id=("task_id",),
                          label=lambda r: r["status_wd3_0900"], total=("Total", False)),
    "checks": dict(category="passed", sums=(), carry=(), row_id=("name",),
                   label=lambda r: "Passed" if r["passed"] == "true" else "Failed", total=("Total", False)),
}


def _group(rows, column):
    groups = {}
    for row in rows:
        groups.setdefault(row[column], []).append(row)
    return groups


def _sums(rows, fields):
    """The count of the rows and, per field, the sum of their decimal text."""
    return dict({f: money(sum((Decimal(r[f]) for r in rows), ZERO)) for f in fields}, count=str(len(rows)))


def _page_rows(rows, id_columns, index, amount=lambda row: False):
    """Per table row: a stable id and every cited input row, in src order, with its key fields; `amount` says whether
    a ledger source also carries its signed share of the row's figure."""
    fields_of = {policy.INPUT_FILES[attr]: fields for attr, fields in policy.SOURCE_FIELDS.items()}
    share = {policy.INPUT_FILES["gl_opening"]: lambda r: r["opening_balance_usd_dr_positive"],
             policy.INPUT_FILES["gl_lines"]: lambda r: r["debit_usd"] - r["credit_usd"]}
    seen, out = {}, []
    for row in rows:
        key = "|".join(row[c] for c in id_columns)
        seen[key] = seen.get(key, 0) + 1
        sources = []
        for ref in (p for p in row["src"].split(SRC_JOIN) if p in index):
            cited = index[ref]
            source = {"ref": ref, "fields": [[c, text(cited[c])] for c in fields_of[cited["src"][0]]]}
            if amount(row) and cited["src"][0] in share:
                source["amount"] = text(share[cited["src"][0]](cited))
            sources.append(source)
        out.append({"row_id": key if seen[key] == 1 else "%s#%d" % (key, seen[key]), "sources": sources})
    return out


def _treasury_block(t, rows, index):
    """The Treasury tab's page block: a lead sentence, the headline figures with their labels, every row below."""
    last = rows[-1]["date"] if rows else ""
    k, horizon = format(policy.TREASURY_BUFFER_K.normalize(), "f"), policy.TREASURY_HORIZON_WD
    lead = ("From the bank statement, less the duplicate debit the reconciliation found (%s), left out of the average "
            "and the daily column. The average daily debit is over the period's business days. Days of coverage = "
            "closing balance / average daily debit. Suggested transfer = average x %d + %s standard deviations x "
            "sqrt(%d); the %s is illustrative, Treasury sets the real target."
            % (text(t.excluded), horizon, k, horizon, k))
    summary = [("Closing balance, %s, USD" % last, t.closing_balance),
               ("Average daily Mastercard debit, USD", t.average_debit),
               ("Standard deviation of the daily debit, USD", t.std_debit), ("Days of coverage, %s" % last, t.coverage),
               ("Suggested weekly transfer, USD (illustrative)", t.transfer)]
    return {"lead": lead, "summary": [{"label": label, "value": text(value)} for label, value in summary],
            "rows": _page_rows(rows, ("date",), index)}


def _thousands(value):
    return format(Decimal(value), ",.2f")


def _plural(count, one, many):
    return "%d %s" % (count, one if count == 1 else many)


def _parts(src):
    return [p for p in src.split(SRC_JOIN) if p]


def _cited(page_row, key):
    """The references of the other input rows an exception cites, after its own key."""
    refs = [row["fields"][0][1] for row in page_row["sources"]
            if row["ref"].split(":", 1)[0] in {policy.INPUT_FILES[a] for a in policy.REFERENCE_ATTRS}]
    return list(dict.fromkeys(r for r in refs if r != key))


def _draft_lines(rows, check_days):
    """One line per exception (key, type, gross amount, day, the other rows' references) and per mismatching day."""
    lines = []
    for r, page_row, facet in rows:
        cited = _cited(page_row, r["key"])
        lines.append(policy.DRAFT_LINE.format(
            key=r["key"], type=r["type"].replace("_", " "), gross=_thousands(abs(Decimal(r["gross"]))),
            day=datetime.date.fromisoformat(facet["date"]).strftime(policy.DAY_FORMAT) if facet["date"] else "",
            cited=("; also cited: " + ", ".join(cited)) if cited else ""))
    return lines + [policy.DRAFT_DAY_LINE.format(
        day=day.strftime(policy.DAY_FORMAT), s_count=sum(int(s["txn_count"]) for s in sums), d_count=len(rows),
        s_net=_thousands(sum((s["net_settlement_usd"] for s in sums), ZERO)),
        d_net=_thousands(sum((x["net_settlement_usd"] for x in rows), ZERO))) for day, sums, rows in check_days]


def _drafts(result, data, page_rows, facets):
    """One drafted message per template that has rows (or its failed check) on the page; nothing is ever sent."""
    failed = {r["name"]: r for r in data["checks"]["rows"] if r["passed"] == "false"}
    days = summary_days(result.inputs)[0]
    out = []
    for key, tpl in policy.DRAFT_TEMPLATES.items():
        rows = [(r, p, f) for r, p, f in zip(data["exceptions"]["rows"], page_rows, facets)
                if r["type"] in tpl["types"] and tpl.get("fixer", r["who_fixes"]) == r["who_fixes"]]
        check = failed.get(tpl.get("check"))
        if not rows and not check:
            continue
        body = policy.DRAFT_FRAME.format(notice=policy.DRAFT_NOTICE, to=tpl["to"], subject=tpl["subject"],
                                         intro=tpl["intro"], rows="\n".join(_draft_lines(rows, days if check else [])),
                                         ask=tpl["ask"])
        out.append({"id": "D%02d" % (len(out) + 1), "to": tpl["to"], "template": key,
                    "types": sorted({r["type"] for r, _p, _f in rows}), "rows": [p["row_id"] for _r, p, _f in rows],
                    "checks": [check["name"]] if check else [], "text": body})
    return out


def _findings(rows):
    """What the exceptions of a task lack, in words: the types with a sentence of their own, then a count and a net."""
    said, plain = [], []
    for row in rows:
        (said if row["type"] in policy.FINDING_WORDS else plain).append(row)
    net = lambda found: sum((Decimal(x["net"]) for x in found), ZERO)  # noqa: E731
    day = (policy.PERIOD_END + datetime.timedelta(days=1)).strftime(policy.DAY_FORMAT)
    out = [policy.FINDING_WORDS[t].format(usd=_thousands(net(found)), day=day, keys=", ".join(x["key"] for x in found))
           for t in policy.FINDING_WORDS for found in [[x for x in said if x["type"] == t]] if found]
    return out + ([_plural(len(plain), "exception", "exceptions") + " (net %s USD)" % _thousands(net(plain))]
                  if plain else [])


def _entries_link(entry_ids, account):
    """The Close link to the entries a task lacks: their lines on the task's account, net debit - credit, or all their
    lines' debits; None when it lacks none."""
    if not entry_ids:
        return None
    return {"screen": "Close", "table": "proposed_entries", "sum": ["debit", "credit"] if account else "debit",
            "filter": dict({"entry_id": entry_ids}, **({"account": account} if account else {}))}


def _pending(result, data, page_rows, facets):
    """What is missing to close September: per checklist task (open ones first) the exceptions, entries and failed
    checks linked to it, its owner and drafts; the checklist's status is never changed."""
    close = result.close
    ids = [p["row_id"] for p in page_rows]
    task_of_ref = {"%s:%s" % tuple(r["src"]): r["task_id"] for r in result.inputs.checklist}
    exceptions, entries, checks_of = (collections.defaultdict(list) for _ in range(3))
    entry_refs, entry_accounts = collections.defaultdict(set), collections.defaultdict(set)
    for row in data["proposed_entries"]["rows"]:
        entry_refs[row["entry_id"]].update(_parts(row["src"]))
        entry_accounts[row["entry_id"]].add(row["account"])
    for row_id, row in zip(ids, data["exceptions"]["rows"]):
        refs = _parts(row["src"])
        others = {p for p in refs if p not in task_of_ref}
        for task in dict.fromkeys(task_of_ref[p] for p in refs if p in task_of_ref):
            exceptions[task].append(row)
            exceptions[task, "ids"].append(row_id)
            if row["cls"] != policy.CLASS.data_issue and others:  # a data-issue flag carries no entry
                entries[task] += [e for e, has in entry_refs.items() if others <= has and e not in entries[task]]
    for task, account in policy.EVIDENCE_ENTRIES.items():  # a task with no exception takes the tool's declared evidence
        if not exceptions[task]:
            entries[task] = [e for e, accounts in entry_accounts.items() if account in (None, *accounts)]
    for row in data["checks"]["rows"]:
        if row["passed"] == "false":
            for task in dict.fromkeys(task_of_ref[p] for p in _parts(row["src"]) if p in task_of_ref):
                checks_of[task].append(row["name"])
    drafts = _drafts(result, data, page_rows, facets)
    debits = {e.id: e.total_debits for e in close.entries}
    lines_of = {e.id: e.lines for e in close.entries}

    def entries_usd(task, ids):
        """What the entries a task lacks come to: their net on the task's account, else their total debits."""
        account = policy.EVIDENCE_ENTRIES.get(task)
        if not account:
            return sum((debits[e] for e in ids), ZERO)
        return abs(sum((d - c for e in ids for a, d, c in lines_of[e] if a == account), ZERO))
    tracker = {r["task_id"]: r for r in data["close_tracker"]["rows"]}
    cls_of = {row_id: r["cls"] for row_id, r in zip(ids, data["exceptions"]["rows"])}
    net_of = {row_id: (r["leg"], Decimal(r["net"])) for row_id, r in zip(ids, data["exceptions"]["rows"])}
    type_of = {row_id: r["type"] for row_id, r in zip(ids, data["exceptions"]["rows"])}
    payable = policy.ACCOUNTS["mc_payable"]

    def resolves(lacks):
        """What closing a task resolves: the net of its exceptions per leg, once; a task whose entries correct no
        exception of its own resolves what they move on 2105."""
        legs = collections.defaultdict(lambda: ZERO)
        for row_id in lacks["exceptions"]:
            legs[net_of[row_id][0]] += net_of[row_id][1]
        on_payable = sum((d - c for e in lacks["entries"] for a, d, c in lines_of[e] if a == payable), ZERO)
        return {"usd": money(sum(legs.values(), ZERO) if lacks["exceptions"] else on_payable),
                "legs": {leg: money(v) for leg, v in sorted(legs.items())}, "entries_2105": money(on_payable)}
    tasks = []
    for r in result.inputs.checklist:
        task = r["task_id"]
        lacks = {"exceptions": exceptions[task, "ids"], "entries": sorted(entries[task]), "checks": checks_of[task]}
        found = _findings(exceptions[task]) \
            + ([_plural(len(lacks["entries"]), "proposed entry", "proposed entries") + " (%s USD)" % _thousands(
                    entries_usd(task, lacks["entries"]))
                + (" and the %s roll-forward" % policy.EVIDENCE_ENTRIES[task] if policy.EVIDENCE_ENTRIES.get(task)
                   else "")] if lacks["entries"] else []) \
            + ([_plural(len(checks_of[task]), "failed check", "failed checks") + " (%s)" % ", ".join(
                    n.replace("_", " ") for n in checks_of[task])] if checks_of[task] else [])
        done = r["status_wd3_0900"] == policy.TASK_DONE
        said = ("Waits on %s." % "; ".join(found)) if found else ("" if done else policy.NO_TOOL_EVIDENCE + ".")
        blocked = bool(lacks["entries"] or lacks["checks"]
                       or any(cls_of[i] != policy.CLASS.timing for i in lacks["exceptions"]))
        named = close.people.get(r["owner_role"])
        tasks.append({"task_id": task, "status": r["status_wd3_0900"], "owner": r["owner_role"], "lacks": lacks,
                      "owner_name": named[0] if named else "", "owner_glossary": "owner.named" if named else "",
                      "blocked": blocked, "resolves": resolves(lacks),
                      "text": said, "link": _entries_link(lacks["entries"], policy.EVIDENCE_ENTRIES.get(task)),
                      "blocked_by": tracker[task]["blocked_by"],
                      "on_critical_path": tracker[task]["on_critical_path"],
                      "drafts": [d["id"] for d in drafts if set(d["rows"]) & set(lacks["exceptions"])
                                 or set(d["checks"]) & set(lacks["checks"])]})
    tasks.sort(key=lambda t: (t["status"] == policy.TASK_DONE, -abs(Decimal(t["resolves"]["usd"]))))
    once = {row_id for t in tasks for row_id in t["lacks"]["exceptions"]}   # an exception on two tasks counts once
    # Timing: what clears on its own, the exceptions of a task that lacks only reconciling items (so is not blocked).
    timing_ids = set()
    for t in tasks:
        if t["lacks"]["exceptions"] and not t["blocked"]:
            t["resolves"]["tag"] = policy.CLASS.timing
            timing_ids.update(t["lacks"]["exceptions"])
    timing_usd = sum((net_of[i][1] for i in timing_ids), ZERO)
    total_usd = sum((net_of[i][1] for i in once), ZERO)
    timing_types = sorted({type_of[i] for i in timing_ids})
    clears = (policy.PERIOD_END + ONE_DAY).strftime(policy.DAY_FORMAT)
    open_tasks = [t for t in tasks if t["status"] != policy.TASK_DONE]
    blocked = sum(1 for t in open_tasks if t["blocked"])
    outside = [r for r in data["exceptions"]["rows"] if r["who_fixes"] in policy.OUTSIDE_FIXERS]
    owed = [r for r in outside if r["cls"] != policy.CLASS.data_issue]
    missing = [r for r in outside if r["type"] == policy.TYPE.input_missing]
    flags = [r for r in outside if r["cls"] == policy.CLASS.data_issue and r not in missing]
    by_fixer = collections.Counter(r["who_fixes"] for r in owed)
    usd = sum(debits.values(), ZERO)
    status = {"open_tasks": str(len(open_tasks)), "blocked_tasks": str(blocked), "entries": str(len(debits)),
              "entries_usd": money(usd), "waiting_outside": str(len(outside))}
    sentence = ("%d close tasks are open and %d of them are blocked by a problem the tool found; %d proposed entries "
                "(%s USD) wait for approval; %d differences (%s USD net) need a corrected file or a credit, %d from "
                "the processor and %d from Mastercard; %d data flags go back to the %s%s." % (
                    len(open_tasks), blocked, len(debits), _thousands(usd), len(owed),
                    _thousands(sum((Decimal(r["net"]) for r in owed), ZERO)), by_fixer[policy.FIXER.processor],
                    by_fixer[policy.FIXER.mastercard], len(flags),
                    " and the ".join(sorted({r["who_fixes"].lower() for r in flags})),
                    "; the %s was not received" % " and the ".join(r["key"] for r in missing) if missing else ""))
    return {"status": status, "sentence": sentence, "tasks": tasks, "drafts": drafts, "notice": policy.DRAFT_NOTICE,
            "resolves_usd": money(total_usd),
            "resolves_split": {policy.CLASS.timing: money(timing_usd), "errors": money(total_usd - timing_usd),
                               "timing_label": "%s (clears %s)" % (", ".join(t.replace("_", " ") for t in timing_types),
                                                                   clears)}}


# What each match figure of the Summary shows: its label and where its rows are: an exceptions filter (summed on net),
# a column of the Grouped view's leg, or nothing (matched with no difference lists no row).
MATCH_FIGURES = {
    "1": {"processor_rows": ("Processor rows", "processor_usd"),
          "mastercard_rows": ("Mastercard rows", "mastercard_usd"),
          "matched_equal": ("Matched, no difference", None),
          "matched_diff": ("Matched, with a difference (net)", {"type": list(policy.PAIR_TYPES)}),
          policy.TYPE.processor_duplicate: ("Processor duplicates (net)", {"type": policy.TYPE.processor_duplicate}),
          policy.TYPE.processor_only: ("Processor side only (net)", {"type": policy.TYPE.processor_only}),
          policy.TYPE.mastercard_only: ("Mastercard side only (net)", {"type": policy.TYPE.mastercard_only})},
    "2": {"settlement_days": ("Settlement days", "mastercard_net"), "paired": ("Days paired with a bank debit",
                                                                                "mastercard_net"),
          "unpaired": ("Days with no bank debit", {"type": policy.TYPE.settlement_not_debited}),
          "duplicate_debits": ("Duplicate bank debits", {"type": policy.TYPE.bank_duplicate_debit})}}


def _short_day(day):
    return day.strftime("%d-%b").lstrip("0")


def _payable_bridge(result):
    """2105 against what Mastercard's own files say Clara owes, one column per set of entries (those with no condition,
    and all of them), as plain subtraction: the result as a credit minus the two Mastercard lines is the difference.
    Every figure carries the rows it opens: a link whose rows sum to it, or its own sources."""
    close, payable, L = result.close, policy.ACCOUNTS["mc_payable"], policy.BRIDGE_LINE
    settlement, timing, unpaid_days = close.payable_owed
    balance = close.balances[payable]
    unconditional = {e.id: e.status == policy.ENTRY_STATUSES[0] for e in close.entries
                     if any(a == payable for a, _d, _c in e.lines)}
    delta = {e.id: sum((d - c for a, d, c in e.lines if a == payable), ZERO) for e in close.entries}
    day = _short_day(policy.PERIOD_END)
    link = lambda table, filter_, sum_: {"screen": "Close", "table": table, "filter": filter_,  # noqa: E731
                                         "sum": sum_}
    owed = lambda rows: [{"ref": src_cell(src), "amount": money(amount)} for src, amount in rows]  # noqa: E731
    pending = [i for i, plain in unconditional.items() if not plain]
    cited = {e.id: {src_cell([s]) for s in e.srcs} for e in close.entries}
    bridge = []
    for basis, column in (("confirmed", "after_confirmed"), ("all", "after_all")):
        ids = [i for i, plain in unconditional.items() if plain or basis == "all"]
        left_out = [i for i in unconditional if i not in ids]
        entries = link("proposed_entries", {"entry_id": ids, "account": payable}, ["debit", "credit"])
        ledger = link("balances", {"account": payable}, "before")
        result_credit = -balance[column]
        gap = result_credit - sum((a for _s, a in settlement + timing), ZERO)
        lines = [
            {"line": L.ledger, "label": "Ledger at %s (debit \u2014 the wrong side)" % day, "side": "debit",
             "usd": money(balance["before"]), "link": ledger},
            {"line": L.entries, "label": "Proposed entries on %s" % payable,
             "usd": money(sum((delta[i] for i in ids), ZERO)), "link": entries},
            {"line": L.result, "label": "Ledger after the entries (credit)", "side": "credit",
             "usd": money(result_credit), "link": [ledger, entries]},
            {"line": L.settlement, "label": "Mastercard settlements not debited by %s (%s)" % (
                 day, ", ".join(_short_day(d) for d in unpaid_days)),
             "usd": money(sum((a for _s, a in settlement), ZERO)), "sources": owed(settlement)},
            {"line": L.timing, "label": "September transactions Mastercard cleared in October (timing)",
             "usd": money(sum((a for _s, a in timing), ZERO)), "sources": owed(timing)},
            {"line": L.difference, "label": "Difference", "usd": money(gap)}]
        if left_out:
            lines[-1]["link"] = link("proposed_entries", {"entry_id": left_out, "account": payable},
                                     ["debit", "credit"])
        for line in lines:
            line["glossary"] = "bridge." + line["line"]
        column_ = {"basis": basis, "lines": lines}
        if basis == "confirmed":
            column_["label"] = "Entries with no condition (%d)" % len(ids)
            column_["waiting"] = left_out
            if left_out:
                names, explained = ", ".join(left_out), sum((delta[i] for i in left_out), ZERO)
                files = {r for i in left_out for r in cited[i] if r.startswith(policy.INPUT_FILES["processor"] + ":")}
                column_["note"] = ("%s = %s: %d processor-only rows; its entry waits for evidence." % (
                    _thousands(gap), names, len(files)) if gap == explained else
                    "%s, of which %s is %s; %s not explained." % (_thousands(gap), _thousands(explained), names,
                                                                  _thousands(gap - explained)))
        else:
            column_["label"] = "All entries, if %s's evidence arrives (%d)" % (", ".join(pending), len(ids))
        bridge.append(column_)
    return bridge


def _step(label, usd, glossary, tone, **more):
    return dict({"label": label, "usd": money(usd), "glossary": glossary, "tone": tone}, **more)


def _walk(leg, title, start, bars, end, lands, **more):
    """A waterfall: start + bars = end, said once here (`ties`, and in words) so the page only draws it."""
    signed = lambda bar: -Decimal(bar["usd"]) if bar.get("side") == "credit" else Decimal(bar["usd"])  # noqa: E731
    gap = signed(end) - signed(start) - sum((signed(b) for b in bars), ZERO)
    return dict({"leg": leg, "title": title, "glossary": "waterfall." + leg, "start": start, "bars": bars, "end": end,
                 "ties": not gap, "said": lands if not gap else "The steps miss the end by %s USD" % _thousands(gap)},
                **more)


# Per leg: what a difference row's gross is, and which way the waterfall walks.
WALK_WORDS = {1: ("processor minus Mastercard", "the processor to Mastercard"),
              2: ("bank minus Mastercard", "Mastercard to the bank")}


def _signed_text(value, plus=True):
    """An amount as the page shows a step: a true minus sign, and a plus on a rise."""
    return ("+" if plus and value > 0 else "") + _thousands(value).replace("-", "\u2212")


def _waterfalls(result, figures, bridge, grouped):
    """One per pair of records, from one side's total to the other's. A step opens what its Summary figure or bridge
    line opens; a difference step opens its exceptions, whose gross is processor minus Mastercard on leg 1 (the step's
    negative) and bank minus Mastercard on leg 2. A month cut-off row is in both leg-1 totals, so it moves the walk by
    its pair's own difference (0.00 when the amounts agree) and opens nothing."""
    recon, T = result.recon, policy.TYPE
    figure = {f["id"]: f for f in figures}
    mastercard = {m["src"]: m["amount_usd"] for m in result.inputs.mc_detail}
    moves, counts = collections.defaultdict(lambda: ZERO), collections.Counter()
    for d in recon.differences:
        if d.leg in policy.WATERFALL_TYPES and d.cls != policy.CLASS.data_issue:
            move = d.gross - mastercard[d.srcs[1]] if d.type == T.month_cutoff else d.gross
            # leg 1 walks from the processor to Mastercard; leg 2 from Mastercard to the bank, short of an undebited day
            moves[d.leg, d.type] += -move if d.leg == 1 or d.type == T.settlement_not_debited else move
            counts[d.leg, d.type] += 1

    def bars(leg):
        out = []
        for t in policy.WATERFALL_TYPES[leg]:
            if not counts[leg, t] and t not in (policy.WATERFALL_ALWAYS if leg == 1 else ()):
                continue
            bar = _step(t.replace("_", " "), moves[leg, t], "type." + t,
                        policy.TONE.wrong if policy.CLASS_OF[t] == policy.CLASS.real_error else policy.TONE.owed,
                        type=t, count=str(counts[leg, t]))
            if t == T.month_cutoff:
                bar["note"] = "%s in both totals; owed as timing on %s" % (
                    _plural(counts[leg, t], "row", "rows"), policy.ACCOUNTS["mc_payable"])
            elif moves[leg, t] and policy.CLASS_OF[t] != policy.CLASS.auto_cleared:
                bar["link"] = {"screen": "Reconciliation", "table": "exceptions",
                               "filter": {"leg": str(leg), "type": t}, "sum": "gross", "show": ["gross"]}
                gross = -moves[leg, t] if leg == 1 or t == T.settlement_not_debited else moves[leg, t]
                bar["said"] = "Gross of these rows, %s: %s USD. Walking from %s, the step is %s." % (
                    WALK_WORDS[leg][0], _signed_text(gross, plus=False), WALK_WORDS[leg][1],
                    _signed_text(moves[leg, t]))
            out.append(bar)
        return out

    def total(fid, label):
        f = figure[fid]
        return _step(label, Decimal(f["usd"]), f["glossary"], policy.TONE.total, link=f["link"])

    grouped_bank = {"screen": "Reconciliation", "grouped": "2", "sum": "bank_debit"}
    bank = sum((Decimal(r["bank_debit"]) for r in grouped["2"]), ZERO)
    walks = [_walk("1", "Processor to Mastercard, gross USD", total("1.processor_rows", "Processor total"), bars(1),
                   total("1.mastercard_rows", "Mastercard total"), "Lands on Mastercard's total to the cent"),
             _walk("2", "Mastercard settlements to bank debits, USD",
                   total("2.settlement_days", "Mastercard settled"), bars(2),
                   _step("Bank debits", bank, "waterfall.bank_debits", policy.TONE.total, link=grouped_bank),
                   "Lands on the bank's debits to the cent")]
    for walk in walks:
        walk["end"]["tone"] = policy.TONE.ties if walk["ties"] else policy.TONE.wrong

    # Payable 2105: the ledger, the entries that need no evidence, those that wait for it, then what Mastercard's files
    # say is owed, landing on the difference with every entry. The bridge's own lines and links, read once.
    confirmed, every = ({x["line"]: x for x in b["lines"]} for b in bridge)
    L, waiting = policy.BRIDGE_LINE, bridge[0]["waiting"]
    steps = [_step("Proposed entries with no condition", Decimal(confirmed[L.entries]["usd"]),
                   "waterfall.entries_confirmed", policy.TONE.fix, link=confirmed[L.entries]["link"])]
    if waiting:
        steps.append(_step("%s, waits for evidence" % ", ".join(waiting),
                           Decimal(every[L.entries]["usd"]) - Decimal(confirmed[L.entries]["usd"]),
                           "waterfall.entries_waiting", policy.TONE.waiting, link=confirmed[L.difference]["link"]))
    day = _short_day(policy.PERIOD_END)
    steps += [_step(said, Decimal(every[x]["usd"]), every[x]["glossary"], policy.TONE.owed, sources=every[x]["sources"])
              for x, said in ((L.settlement, "Settlements not debited by " + day),
                              (L.timing, "Cleared by Mastercard after " + day))]
    ledger, gap = every[L.ledger], Decimal(every[L.difference]["usd"])
    payable = _walk("3", "Payable %s: ledger to what Mastercard says is owed, USD" % policy.ACCOUNTS["mc_payable"],
                    _step("Ledger at " + day, Decimal(ledger["usd"]), ledger["glossary"], policy.TONE.total,
                          side=ledger["side"], link=ledger["link"]),
                    steps, _step("Difference, all entries", gap, every[L.difference]["glossary"],
                                 policy.TONE.ties if not gap else policy.TONE.wrong, side="credit"),
                    "Every entry posted, the payable equals what Mastercard says is owed" if not gap else
                    "With every entry, %s USD is still off" % _thousands(gap), basis="all")
    return walks + [payable]


def _overview(result, data, sentence, bridge, grouped):
    """The Summary: a block of figures per leg, how much is explained, the two sentences. A linked figure equals the
    sum of the rows its link shows; a figure of no rows (count 0) links nowhere."""
    rows, figures = data["exceptions"]["rows"], []

    def figure(name, leg, label, count=None, usd=None, link=None):
        found = {"id": "%s.%s" % (leg, name), "leg": leg, "label": label, "glossary": "figure." + name}
        found.update({k: v for k, v in (("count", count), ("usd", usd), ("link", None if count == "0" else link))
                      if v is not None})
        figures.append(found)

    def link(screen, table, filter_, sum_=None):
        return dict({"screen": screen, "table": table, "filter": filter_}, **({"sum": sum_} if sum_ else {}))

    for leg, counts in result.recon.counts.items():
        for name, (count, usd) in counts.items():
            label, where = MATCH_FIGURES[leg][name]
            where = {"screen": "Reconciliation", "grouped": leg, "sum": where} if isinstance(where, str) else (
                link("Reconciliation", "exceptions", dict(where, leg=leg), "net") if where else None)
            figure(name, leg, label, str(count), text(usd) if usd is not None else None, where)
    cash, close = result.close.cash_recon, result.close
    for name, label, line, amount in (("ledger_1110", "Ledger 1110", 0, cash.ledger_balance),
                                      ("bank_balance", "Bank statement", 2, cash.bank_balance),
                                      ("reconciling_items", "Reconciling items", 1,
                                       sum((i.amount for i in cash.reconciling_items), ZERO)),
                                      ("unreconciled", "Unreconciled", 3, cash.unreconciled)):
        figure(name, "3", label, usd=text(amount),
               link=link("Close", "cash_recon", {"line": policy.CASH_LINES[line]}, "amount"))
    for leg in ("1", "2", "3"):
        mine = [r for r in rows if r["leg"] == leg]
        figure("exceptions", leg, "Exceptions (net)", str(len(mine)),
               money(sum((Decimal(r["net"]) for r in mine), ZERO)),
               link("Reconciliation", "exceptions", {"leg": leg}, "net"))
        figure("escalates", leg, "Escalate", str(sum(1 for r in mine if r["escalates"] == "true")),
               link=link("Reconciliation", "exceptions", {"leg": leg, "escalates": "true"}))
        figure("waiting_outside", leg, "Waiting outside Clara",
               str(sum(1 for r in mine if r["who_fixes"] in policy.OUTSIDE_FIXERS)),
               link=link("Reconciliation", "exceptions", {"leg": leg, "who_fixes": list(policy.OUTSIDE_FIXERS)}))
    explained = []
    for leg in ("1", "2", "3"):
        net = lambda cls=None: money(sum((Decimal(r["net"]) for r in rows  # noqa: E731
                                          if r["leg"] == leg and cls in (None, r["cls"])), ZERO))
        unexplained = sum((abs(d.gross) for d in result.recon.differences
                           if str(d.leg) == leg and d.type in policy.UNEXPLAINED_TYPES), ZERO)
        explained.append(dict({"leg": leg, "total": net(), "unexplained": money(unexplained)},
                              **{cls: net(cls) for cls in (policy.CLASS.timing, policy.CLASS.real_error,
                                                           policy.CLASS.data_issue)}))
    failed, unread = sum(1 for c in result.checks if not c.passed), [w for w, _s in result.inputs.missing]
    quality = "%d of %d pre-checks failed; %s." % (failed, len(result.checks), (
        "%s not read (%s)" % (_plural(len(unread), "expected input was", "expected inputs were"), ", ".join(unread))
        if unread else "every expected input was read"))
    counts = result.recon.counts["1"]
    return {"figures": figures, "explained": explained, "close_status": sentence, "data_quality": quality,
            "leg1_gross_difference": money(counts["processor_rows"][1] - counts["mastercard_rows"][1]),
            "payable_bridge": bridge, "waterfalls": _waterfalls(result, figures, bridge, grouped)}


def _grouped_leg1(result, found):
    """Grouped leg 1, by type; each processor and Mastercard row of the leg sits in exactly one money group."""
    processor = {r["src"]: r["amount_usd"] for r in result.inputs.processor}
    mastercard = {r["src"]: r["amount_usd"] for r in result.inputs.mc_detail}
    in_a_group = {d.srcs[0] for d, _i in found if d.type in policy.PAIR_TYPES + (policy.TYPE.processor_duplicate,)}
    equal = [m for m in result.recon.matches if m.processor_row["src"] not in in_a_group]
    groups = collections.OrderedDict([("matched_equal", [_usd_of(equal, "processor_row"), _usd_of(equal, "mc_row"),
                                                         [], str(len(equal))])])
    groups.update((t, None) for t in policy.TYPE_ORDER)   # one type order; the placeholders without rows drop out
    flags = collections.OrderedDict()
    for d, row_id in found:
        held = flags if d.cls == policy.CLASS.data_issue else groups
        if held.get(d.type) is None:
            held[d.type] = [ZERO, ZERO, [], None]
        group = held[d.type]
        if d.cls != policy.CLASS.data_issue:
            for src in d.srcs[:1] if d.type in policy.SINGLE_ROW_TYPES else d.srcs[:2]:
                group[0] += processor.get(src, ZERO)
                group[1] += mastercard.get(src, ZERO)
        group[2].append(row_id)
    groups.update(sorted(flags.items(), key=lambda kv: policy.TYPE_ORDER.index(kv[0])))
    return [dict({"type": t, "processor_usd": money(p), "mastercard_usd": money(m), "difference": money(p - m),
                  "exceptions": str(len(i)), "ids": i}, **({"count": n} if n else {}),
                 **({"flag": True} if t in flags else {}))
            for t, (p, m, i, n) in ((t, g) for t, g in groups.items() if g)]


def _usd_of(matches, side):
    return sum((getattr(m, side)["amount_usd"] for m in matches), ZERO)


def _grouped(result, shown, ids, bridge):
    """Leg 1 by type: the pairs that match exactly, then one row per difference type with the processor and Mastercard
    rows it holds (a data flag carries no money: its rows are already in the groups above, so it shows 0.00 and comes
    last); leg 2 by settlement date (the duplicate debit on the day it duplicates); leg 3 one row per bridged account.
    Each row carries the ids of its exceptions, which a click filters to; `shown` and `ids` run in parallel."""
    recon, close = result.recon, result.close
    leg1 = _grouped_leg1(result, [(d, row_id) for d, row_id in zip(shown, ids) if d.leg == 1])
    where, leg2 = {}, {}
    for s, paid in recon.settlement_days:
        day = s["settlement_date"]
        leg2[day] = {"net": s["net_settlement_usd"], "bank": sum((b["debit_usd"] for b in paid), ZERO), "ids": []}
        where.update({src: day for src in [s["src"]] + [b["src"] for b in paid]})
    for d, row_id in zip(shown, ids):
        if d.leg == 2:
            day = next((where[src] for src in d.srcs if src in where), None)
            alone = day is None
            if alone:  # a debit on no summary day stands on its own date
                day = d.origin
                leg2.setdefault(day, {"net": ZERO, "bank": ZERO, "ids": []})
            if alone or d.type == policy.TYPE.bank_duplicate_debit:  # money the bank paid beyond the pairs
                leg2[day]["bank"] += d.gross
            leg2[day]["ids"].append(row_id)
    leg2 = [{"date": text(day), "mastercard_net": money(v["net"]), "bank_debit": money(v["bank"]),
             "difference": money(v["bank"] - v["net"]), "exceptions": str(len(v["ids"])), "ids": v["ids"]}
            for day, v in sorted(leg2.items())]
    cash_account, payable, L = policy.ACCOUNTS["bridge_cash"], policy.ACCOUNTS["mc_payable"], policy.BRIDGE_LINE
    cash = close.cash_recon
    names = dict(ACCOUNT_NAME, **{r["account"]: r["account_name"] for r in result.inputs.gl_opening})
    every = {line["line"]: line for line in bridge[1]["lines"]}
    owed = Decimal(every[L.settlement]["usd"]) + Decimal(every[L.timing]["usd"])
    reconciling, unreconciled = -Decimal(every[L.entries]["usd"]), -Decimal(every[L.difference]["usd"])
    pending = bridge[0]["waiting"]   # the entries on a condition
    leg3_ids = [row_id for d, row_id in zip(shown, ids) if d.leg == 3]   # exceptions carry no account: all of leg 3
    leg3 = [{"account": cash_account, "name": names[cash_account], "ledger": money(cash.ledger_balance),
             "record_label": "Bank statement", "record": money(cash.bank_balance),
             "difference": money(cash.ledger_balance - cash.bank_balance),
             "reconciling_items": money(sum((i.amount for i in cash.reconciling_items), ZERO)),
             "unreconciled": money(cash.unreconciled), "ids": leg3_ids},
            {"account": payable, "name": names[payable], "ledger": every[L.ledger]["usd"],
             "record_label": "Owed to Mastercard, as a credit", "record": money(-owed),
             "difference": money(reconciling + unreconciled), "reconciling_items": money(reconciling),
             "unreconciled": money(unreconciled),   # the bridge's, signed as a debit
             "items_note": "The entries on %s%s." % (payable, ", including %s, which waits for evidence" % ", ".join(
                 pending) if pending else ""),
             "ids": leg3_ids, "bridge": bridge}]
    return {"1": leg1, "2": leg2, "3": leg3}


# The amount of a flagged input row, where its file has one (debit-positive on the ledger).
FLAG_AMOUNT = {policy.INPUT_FILES["processor"]: lambda r: r["amount_usd"],
               policy.INPUT_FILES["mc_detail"]: lambda r: r["amount_usd"],
               policy.INPUT_FILES["bank"]: lambda r: r["credit_usd"] - r["debit_usd"],
               policy.INPUT_FILES["gl_lines"]: lambda r: r["debit_usd"] - r["credit_usd"]}


def _unit(count, words):
    return {"count": str(count), "unit": words[0] if count == 1 else words[1]}


def _flagged(rows, page_rows, index):
    """Data quality: per check, its count with its unit (and, counted in another unit, the rows it opens); below, one
    row per input row a failed check flags, with the check's reason. The close-checklist row a check cites for its task
    is not a flagged row; a check with no rows of its own is a pass/fail line only."""
    checklist = policy.INPUT_FILES["checklist"] + ":"
    flagged = []
    for row, page_row in zip(rows, page_rows):
        name, units = row["name"], []
        own = [s for s in page_row["sources"] if not s["ref"].startswith(checklist)]
        page_row["task_refs"] = [s["ref"] for s in page_row["sources"] if s["ref"].startswith(checklist)]
        if name not in policy.CHECKS_WITHOUT_ROWS:
            units.append(_unit(int(row["count"]), policy.CHECK_UNITS.get(name, policy.ROW_UNIT)))
            if name in policy.CHECK_UNITS and own:
                units.append(_unit(len(own), policy.ROW_UNIT))
            if row["passed"] == "false":
                for s in own:
                    cited = index[s["ref"]]
                    amount = FLAG_AMOUNT.get(cited["src"][0])
                    flagged.append(dict({"check": name, "reason": row["detail"], "ref": s["ref"],
                                         "fields": s["fields"]}, **({"amount": text(amount(cited))} if amount else {})))
        page_row["units"] = units
    return {"rows": flagged}


def page(result, data, facets):
    """Per data tab of the page: the summary by category with its total (or subtotals) and, parallel to the table's
    rows, each row's id and source. Every figure is summed from the table's own text, so it equals the table's sum."""
    index, out = _source_rows(result), {}
    for tab, spec in PAGE.items():
        rows = data[tab]["rows"]
        summary = [dict({c: found[0][c] for c in spec["carry"]}, category=key, label=spec["label"](found[0]),
                        **_sums(found, spec["sums"])) for key, found in _group(rows, spec["category"]).items()]
        block = {"category": spec["category"], "sums": list(spec["sums"]), "carry": list(spec["carry"]),
                 "summary": summary, "rows": _page_rows(rows, spec["row_id"], index, spec.get("amount", _NO))}
        if "subtotal" in spec:
            by = spec["subtotal"]
            summary.sort(key=lambda s: (s[by], policy.TYPE_ORDER.index(s["category"])))   # by leg, then type order
            block["subtotals"] = [dict(_sums(found, spec["sums"]), **{by: key})
                                  for key, found in sorted(_group(rows, by).items())]
        else:
            label, adds_money = spec["total"]
            block["total"] = dict(_sums(rows, spec["sums"] if adds_money else ()), label=label)
        out[tab] = block
    for row, page_row in zip(data["checks"]["rows"], out["checks"]["rows"]):
        if row["passed"] == "false":
            page_row["meaning"] = policy.CHECK_MEANING[row["name"]]
    out["flagged"] = _flagged(data["checks"]["rows"], out["checks"]["rows"], index)
    flags = sum(1 for r in data["exceptions"]["rows"]
                if r["cls"] == policy.CLASS.data_issue and r["type"] in policy.HIDDEN_FLAG_TYPES)
    out["exceptions"]["hidden_by_default"] = {   # the bare Detailed view opens on the money; the flags are a click away
        "cls": policy.CLASS.data_issue, "types": list(policy.HIDDEN_FLAG_TYPES), "count": str(flags)}
    out["treasury"] = _treasury_block(result.treasury, data["treasury"]["rows"], index)
    out["pending"] = _pending(result, data, out["exceptions"]["rows"], facets)
    bridge = _payable_bridge(result)
    out["grouped"] = _grouped(result, [d for d in result.recon.differences if d.cls != policy.CLASS.auto_cleared],
                              [p["row_id"] for p in out["exceptions"]["rows"]], bridge)
    out["overview"] = _overview(result, data, out["pending"]["sentence"], bridge, out["grouped"])
    out["screens"] = [{"name": name, "glossary": "screen." + name} for name in policy.SCREENS]
    out["glossary"] = dict(policy.GLOSSARY)
    out["period"] = policy.PERIOD_START.strftime("%B %Y")
    return out


def erp_lines(result, entry_rows):
    """The proposed entries in gl_journal_lines.csv's own columns, line for line, marked as not approved."""
    names = dict(ACCOUNT_NAME, **{r["account"]: r["account_name"] for r in result.inputs.gl_opening})
    rows = [dict(je_id=policy.ERP_JE_PREFIX + e["entry_id"], posting_date=text(policy.PERIOD_END),
                 source=policy.ERP_SOURCE, account=e["account"], account_name=names[e["account"]],
                 debit_usd=e["debit"], credit_usd=e["credit"], description=e["title"],
                 reference=policy.ERP_REFERENCE.format(level=e["approval_level"], status=e["status"]))
            for e in entry_rows]
    return _table(policy.GL_LINE_COLUMNS, rows)


def code_version(repo_root):
    """The git commit of the code, with `-dirty` when tracked or new source files differ; `unknown` if git fails."""
    def git(*args):
        return subprocess.run(["git", "-C", repo_root] + list(args), capture_output=True, text=True, check=True).stdout
    try:
        commit = git("rev-parse", "HEAD").strip()
        dirty = git("status", "--porcelain", "--", ".", ":(exclude,glob)**/__pycache__/**").strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return commit + ("-dirty" if dirty else "")


def _write_csv(path, table):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=table["columns"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(table["rows"])


def write(result, out_dir, repo_root):
    """Writes the ten output files (spec E5 and E9, and the ERP file) into `out_dir` (created if needed)."""
    os.makedirs(out_dir, exist_ok=True)
    data = tables(result)
    for name, table in data.items():
        _write_csv(os.path.join(out_dir, name + ".csv"), table)
    _write_csv(os.path.join(out_dir, policy.ERP_FILE), erp_lines(result, data["proposed_entries"]["rows"]))
    manifest = {
        "code_version": code_version(repo_root),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "input_sha256": dict(sorted(result.inputs.fingerprints.items())),
        "files": _files(result.inputs),
        "inputs_not_read": [what for what, _src in result.inputs.missing],
        "totals": totals(result),
    }
    with open(os.path.join(out_dir, "run_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    facets = _facets(result)
    blob = json.dumps({"manifest": manifest, "tables": data, "page": page(result, data, facets), "facets": facets,
                       "names": {"cover_check": policy.CHECK.inputs_cover_period,
                                 "owned_check": policy.CHECK.checklist_tasks_owned, "read": policy.FILE_STATUS.read}},
                      ensure_ascii=True).replace("<", "\\u003c")
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    for token, file_name in FONT_TOKENS.items():  # a missing font file leaves an empty src: the page uses system fonts
        try:
            with open(os.path.join(FONT_DIR, file_name), "rb") as f:
                html = html.replace(token, base64.b64encode(f.read()).decode("ascii"))
        except OSError:
            html = html.replace(token, "")
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html.replace(DATA_TOKEN, blob))
