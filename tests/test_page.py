"""Page tests for plan block "Page: a summary by category on every tab, all rows in one table below" (Andrés,
2026-10-15; amended the same day in c628b53: the exceptions table shows net, age and escalation, and its summary
subtotals per leg). They replace the page-by-figure tests: the "By figure" tab and the drill panel go, and every data tab
carries a summary by category whose totals equal the sum of its own table.

The page script cannot run in the suite, so the tests read the JSON blob that report.py embeds in index.html and, for
the presence or absence of a feature only, the page script. The blob shape these tests fix:

    data["page"][tab] = {
        "category": <column of data["tables"][tab] the summary groups by>,
        "sums": [<fields summed: a column of the table, or a field of the page row>],
        "summary": [{"category": <value>, "label": <text>, "count": "<n>", <each sum field>: "<decimal>", ...}],
        "total": {"count": "<n>", <each sum field>: "<decimal>"},   # every tab but exceptions; the money sums only
                                                     # where they mean something (MONEY_TOTAL_TABS): cash carries a
                                                     # count only (its unreconciled line is the tie), balances sum to 0
                                                     # (the trial-balance check, labelled as such)
        "subtotals": [{"leg": "1", "count": "<n>", "net": "<decimal>"}, ...],   # exceptions only, legs 1, 2, 3:
                                                     # never one money total mixing the three legs
        "rows": [{"row_id": <text, unique in the tab>,
                  "sources": [{"ref": "file:locator", "fields": [[column, text], ...]}, ...]},   # every cited row
                                                     # (plan block "Five screens"; was the first one and "+N more")
                 ...],                         # parallel to data["tables"][tab]["rows"]
    }

The exceptions summary sums `net`, the amount that ties to the leg-1 totals; its rows carry `leg` and `cls` and are
grouped by leg (all leg-1 types, then leg 2, then leg 3). `data["tables"]` stays exactly what the CSVs hold. Not automated (checked by hand in Chrome by the session): the
layout at 1440 px without horizontal scroll, a click on a summary row filtering the table in place, the sum row of the
visible rows, the CSV download of a filtered view.

Every expected figure below was recomputed from the CSVs written at 986bc7e by a throwaway script, and the leg-1
amounts agree with V2_EXPECTED (independently derived in the golden suite).
"""

import collections
import datetime
import os
import re
import shutil
import tempfile
import unittest
from decimal import Decimal

from tests import test_golden as g
from tests.test_golden import D, DATA_DIR, V2_EXPECTED, V6_EXPECTED

TABS = ("exceptions", "proposed_entries", "balances", "cash_recon", "close_tracker", "checks")
CATEGORY = {"exceptions": "type", "proposed_entries": "entry_id", "balances": "account", "cash_recon": "line",
            "close_tracker": "status_wd3_0900", "checks": "passed"}
REQUIRED_SUMS = {"exceptions": ["net"], "proposed_entries": ["debit"],
                 "balances": ["before", "after_confirmed", "after_all"], "cash_recon": ["amount"],
                 "close_tracker": [], "checks": []}

# The CSV outputs stay as they are: same files, same columns, same number of rows on the case data. Amended by
# 7b79b4c (named owners): exceptions gains clara_owner_name after clara_owner, close_tracker owner_name after owner_role.
CSV_COLUMNS = {
    "exceptions": ["leg", "type", "cls", "key", "gross", "net", "age_wd", "requires_explanation", "escalates",
                   "controller_action", "who_fixes", "clara_owner", "clara_owner_name", "action", "src"],
    "proposed_entries": g.ENTRY_COLUMNS,
    "balances": ["account", "before", "after_confirmed", "after_all", "src"],
    "cash_recon": ["line", "amount", "src"],
    "close_tracker": ["task_id", "phase", "task", "owner_role", "owner_name", "system", "due_working_day", "depends_on",
                      "status_wd3_0900", "control_type", "blocked_by", "on_critical_path", "tool_evidence", "src"],
    "checks": ["name", "passed", "count", "detail", "src"],
}
ROW_COUNTS = {"exceptions": 262, "proposed_entries": 41, "balances": 11, "cash_recon": 4, "close_tracker": 26,
              "checks": 13}

# Case data, per category: (rows, USD total). Plan block "Extras before submission": E05 is itemised, one debit per
# invoice line item plus the credit to 2150 (5 lines instead of 2, same 8,412.30), so proposed_entries.csv has 41 rows.
EXCEPTION_TYPES = {
    "processor_duplicate": (6, D("3593.63")), "amount_diff": (8, D("737.29")), "sign_flip": (4, D("2502.45")),
    "fx_rate_diff": (95, D("751.93")), "month_cutoff": (4, D("928.31")), "processor_only": (3, D("9127.92")),
    "mastercard_only": (5, D("-2041.36")), "reference_bad": (105, D("0.00")), "auth_after_clearing": (3, D("0.00")),
    "auth_stale": (22, D("0.00")), "bank_duplicate_debit": (1, D("40616.94")),
    "processor_entry_missing": (1, D("44884.41")), "processor_entry_misdated": (1, D("45331.47")),
    "funding_in_transit": (1, D("400000.00")), "suspense_pending_payer": (1, D("12500.00")),
    "invoice_not_accrued": (1, D("8412.30")), "input_missing": (1, D("0.00"))}
LEG_SUBTOTALS = [("1", 255, D("15600.17")), ("2", 1, D("40616.94")), ("3", 6, D("511128.18"))]
ENTRY_DEBITS = {"E01": (4, D("45611.52")), "E02": (4, D("46092.28")), "E03": (2, D("40616.94")),
                "E04": (2, D("12500.00")), "E05": (5, D("8412.30")), "E06": (4, D("763.76")),
                "E07": (4, D("2541.83")), "E08": (4, D("748.88")), "E09": (4, D("3655.04")),
                "E10": (4, D("9271.44")), "E11": (4, D("2077.90"))}
ENTRIES_TOTAL = (41, D("172291.89"))
CASH_LINES = [("ledger_balance", 1, D("1547965.55")), ("reconciling_item", 1, D("400000.00")),
              ("bank_balance", 1, D("1147965.55")), ("unreconciled", 1, D("0.00"))]
CASH_TOTAL_COUNT = 4
# Tabs whose total row sums money. Cash does not: ledger + items + bank + unreconciled adds to a meaningless figure.
MONEY_TOTAL_TABS = frozenset(["proposed_entries", "balances"])
TRACKER_STATUS = {"Not started": 17, "Done": 6, "In progress": 2, "Blocked": 1}
CHECKS_PASSED = {"true": 8, "false": 5}  # summary_vs_detail passes once 31-Aug is a coverage note (plan b3a73a8)

# Loader-computed fields, not columns of the input file.
COMPUTED = frozenset(["src", "ref_norm", "ref_status", "net", "kind", "sent_on"])


def setUpModule():
    g.setUpModule()


def _page(data):
    page = data.get("page")
    if not isinstance(page, dict):
        raise AssertionError("the page blob carries no `page` block (summary and rows per tab)")
    return page


def _value(data, tab, i, field):
    """A sum field of row i of a tab: the page row's own field, else the table column."""
    page_row = _page(data)[tab]["rows"][i]
    return D(page_row[field] if field in page_row else data["tables"][tab]["rows"][i][field])


def _parts(src):
    return [p for p in src.split(g.guards.SRC_SEPARATOR) if p]


def _input_index(result):
    from bridge import policy
    index = {}
    for attr, file_name in policy.INPUT_FILES.items():
        for row in getattr(result.inputs, attr):
            index["%s:%s" % tuple(row["src"])] = row
    return index


def _same(text, value):
    """Whether the blob's text says the input row's value."""
    if isinstance(value, Decimal):
        return bool(g.DECIMAL_TEXT.match(text or "")) and D(text) == value
    if isinstance(value, datetime.date):
        return text == value.isoformat()
    if isinstance(value, bool):
        return text == ("true" if value else "false")
    return text == ("" if value is None else str(value))


def _source_fields():
    """policy.SOURCE_FIELDS keyed by input file name (keys may be the loader attribute or the file name)."""
    from bridge import policy
    declared = getattr(policy, "SOURCE_FIELDS", None)
    if not isinstance(declared, dict):
        raise AssertionError("policy.SOURCE_FIELDS is not declared")
    return {policy.INPUT_FILES.get(k, k): list(v) for k, v in declared.items()}


class _Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = g._result()
        cls.out_dir = g._run()[0]
        cls.data = g._page_data(cls.out_dir)

    def page(self, tab):
        page = _page(self.data)
        self.assertIn(tab, sorted(page))
        return page[tab]

    def summary(self, tab):
        return {s["category"]: s for s in self.page(tab)["summary"]}


class PageBlockShape(_Page):
    """Each data tab has its page block: the category column, the summed fields, a summary, a total and one page row
    per table row."""

    def test_every_tab(self):
        for tab in TABS:
            with self.subTest(tab=tab):
                block = self.page(tab)
                self.assertEqual(block.get("category"), CATEGORY[tab])
                self.assertEqual(set(REQUIRED_SUMS[tab]) - set(block.get("sums", [])), set())
                self.assertEqual(len(block["rows"]), len(self.data["tables"][tab]["rows"]))
                closing = block.get("subtotals", []) if tab == "exceptions" else [block.get("total", {})]
                self.assertTrue(closing, "no total" if tab != "exceptions" else "no per-leg subtotals")
                money_closing = tab == "exceptions" or tab in MONEY_TOTAL_TABS
                for s in block["summary"] + closing:
                    self.assertRegex(s["count"], r"^\d+$")
                    for field in block["sums"]:
                        if s in block["summary"] or money_closing:
                            self.assertRegex(s[field], g.DECIMAL_TEXT, field)
                for s in block["summary"]:
                    self.assertTrue(str(s.get("label", "")).strip(), s)

    def test_no_money_on_tracker_and_checks(self):
        for tab in ("close_tracker", "checks"):
            self.assertEqual([f for f in self.page(tab)["sums"] if f in ("amount", "net", "gross", "debit")], [], tab)

    def test_exceptions_never_one_total_across_legs(self):
        block = self.page("exceptions")
        self.assertNotIn("gross", block["sums"])
        mixed = {k: v for k, v in (block.get("total") or {}).items() if k != "count"}
        self.assertEqual(mixed, {}, "a money total mixing the three legs")
        self.assertEqual([s.get("leg") for s in block["subtotals"]], ["1", "2", "3"])


class SummaryEqualsItsTable(_Page):
    """Plan: the summary rows add up to a total row equal to the sum of the table below (money totals only where they
    mean something: not on cash), and every amount on the page
    can be filtered down to the rows that make it up within its own tab (a summary row's count and totals are those of
    the table rows of its category)."""

    def test_every_tab(self):
        for tab in TABS:
            with self.subTest(tab=tab):
                block, rows = self.page(tab), self.data["tables"][tab]["rows"]
                column, sums = block["category"], block["sums"]
                by_cat = collections.OrderedDict()
                for i, row in enumerate(rows):
                    by_cat.setdefault(row[column], []).append(i)
                summary = block["summary"]
                self.assertEqual(len(summary), len({s["category"] for s in summary}))
                self.assertEqual(sorted(s["category"] for s in summary), sorted(by_cat))
                for s in summary:
                    found = by_cat[s["category"]]
                    self.assertEqual(int(s["count"]), len(found), s["category"])
                    for field in sums:
                        self.assertEqual(D(s[field]), sum((_value(self.data, tab, i, f) for i in found
                                                           for f in [field]), D("0")), (s["category"], field))
                self.assertEqual(sum(int(s["count"]) for s in summary), len(rows))
                if tab == "exceptions":
                    self.check_leg_subtotals(block, rows)
                    continue
                total = block["total"]
                self.assertEqual(int(total["count"]), len(rows))
                if tab not in MONEY_TOTAL_TABS:
                    self.assertEqual([f for f in sums if f in total], [], "a summed total that means nothing")
                    continue
                for field in sums:
                    table_sum = sum((_value(self.data, tab, i, field) for i in range(len(rows))), D("0"))
                    self.assertEqual(D(total[field]), table_sum, field)
                    self.assertEqual(sum((D(s[field]) for s in summary), D("0")), table_sum, field)


    def check_leg_subtotals(self, block, rows):
        legs = [s.get("leg") for s in block["summary"]]
        self.assertEqual(legs, sorted(legs), "exception types not grouped under their leg")
        for sub in block["subtotals"]:
            found = [i for i, r in enumerate(rows) if r["leg"] == sub["leg"]]
            self.assertEqual(int(sub["count"]), len(found), sub["leg"])
            for field in block["sums"]:
                table_sum = sum((_value(self.data, "exceptions", i, field) for i in found), D("0"))
                self.assertEqual(D(sub[field]), table_sum, (sub["leg"], field))
                self.assertEqual(sum((D(s[field]) for s in block["summary"] if s.get("leg") == sub["leg"]), D("0")),
                                 table_sum, (sub["leg"], field))


class SummaryFiguresOnCaseData(_Page):
    """The summaries on the case data, figure by figure."""

    def test_exceptions_by_type(self):
        summary = self.summary("exceptions")
        self.assertEqual({k: (int(s["count"]), D(s["net"])) for k, s in summary.items()}, EXCEPTION_TYPES)
        self.assertEqual([(s["leg"], int(s["count"]), D(s["net"])) for s in self.page("exceptions")["subtotals"]],
                         LEG_SUBTOTALS)

    def test_leg1_types_tie_to_leg1_by_type(self):
        summary = self.summary("exceptions")
        by_type = self.data["manifest"]["totals"]["leg1_by_type"]
        for type_, amount in V2_EXPECTED.items():
            self.assertEqual(D(summary[type_]["net"]), amount, type_)
            self.assertEqual(D(summary[type_]["net"]), D(by_type[type_]), type_)
        self.assertEqual({t: D(v) for t, v in by_type.items() if D(v) != 0}, V2_EXPECTED)
        leg1 = sum((D(s["net"]) for s in summary.values() if s.get("leg") == "1"), D("0"))
        self.assertEqual(leg1, D(self.data["manifest"]["totals"]["leg1_difference_usd"]))
        self.assertEqual(leg1, D("15600.17"))

    def test_exception_rows_show_class_and_leg(self):
        rows = self.data["tables"]["exceptions"]["rows"]
        for type_, s in self.summary("exceptions").items():
            with self.subTest(type=type_):
                self.assertEqual((s.get("cls"), s.get("leg")),
                                 next((r["cls"], r["leg"]) for r in rows if r["type"] == type_))

    def test_entries_by_id(self):
        summary = self.summary("proposed_entries")
        self.assertEqual({k: (int(s["count"]), D(s["debit"])) for k, s in summary.items()}, ENTRY_DEBITS)
        total = self.page("proposed_entries")["total"]
        self.assertEqual((int(total["count"]), D(total["debit"])), ENTRIES_TOTAL)
        for entry in self.r.close.entries:
            with self.subTest(entry=entry.id):
                s = summary[str(entry.id)]
                self.assertEqual(D(s["debit"]), entry.total_debits)
                self.assertIn(entry.title, s["label"])
                self.assertEqual((s.get("status"), s.get("approval_level")), (entry.status, entry.approval_level))

    def test_balances_by_account(self):
        summary = self.summary("balances")
        self.assertEqual({k: D(s["before"]) for k, s in summary.items()}, V6_EXPECTED)
        self.assertEqual({k: (D(s["after_confirmed"]), D(s["after_all"])) for k, s in summary.items()},
                         {a: (b["after_confirmed"], b["after_all"]) for a, b in self.r.close.balances.items()})
        # The total row is the trial-balance check: each column sums to 0, and the page labels it so.
        total = self.page("balances")["total"]
        self.assertEqual((int(total["count"]), D(total["before"]), D(total["after_confirmed"]),
                          D(total["after_all"])), (11, D("0"), D("0"), D("0")))
        self.assertRegex(str(total.get("label", "")), r"(?i)trial balance")

    def test_cash_lines(self):
        summary = self.page("cash_recon")["summary"]
        self.assertEqual([(s["category"], int(s["count"]), D(s["amount"])) for s in summary], CASH_LINES)
        from bridge import policy
        self.assertEqual([s["category"] for s in summary], list(policy.CASH_LINES))
        # Count only: the unreconciled line is the tie (ledger - items - bank, V9CashRecon), not a summed total.
        total = self.page("cash_recon")["total"]
        self.assertEqual(int(total["count"]), CASH_TOTAL_COUNT)
        self.assertNotIn("amount", total)

    def test_tracker_by_status(self):
        summary = self.summary("close_tracker")
        self.assertEqual({k: int(s["count"]) for k, s in summary.items()}, TRACKER_STATUS)

    def test_checks_passed_failed(self):
        summary = self.summary("checks")
        self.assertEqual({k: int(s["count"]) for k, s in summary.items()}, CHECKS_PASSED)
        self.assertRegex(summary["true"]["label"], r"(?i)passed")
        self.assertRegex(summary["false"]["label"], r"(?i)failed")
        self.assertEqual(summary["false"]["count"], self.data["manifest"]["totals"]["checks_failed"])


class SourceFieldsDeclaredOnce(unittest.TestCase):
    """Plan: the key fields per input file are declared once in policy.py (`SOURCE_FIELDS`: 3-5 columns per file,
    fewer only where the file has fewer columns), for every input file some table row cites, and the page reads them
    as data."""

    @classmethod
    def setUpClass(cls):
        cls.r = g._result()
        cls.data = g._page_data(g._run()[0])

    def test_declared_for_every_cited_file(self):
        index = _input_index(self.r)
        declared = _source_fields()
        cited = {p.split(":", 1)[0] for tab in TABS for row in self.data["tables"][tab]["rows"]
                 for p in _parts(row["src"]) if p in index}
        self.assertEqual(sorted(cited - set(declared)), [])
        by_file = {}
        for key, row in index.items():
            by_file.setdefault(key.split(":", 1)[0], set(row) - COMPUTED)
        for file_name, fields in declared.items():
            with self.subTest(file=file_name):
                self.assertIn(file_name, by_file)
                columns = by_file[file_name]
                self.assertTrue(min(3, len(columns)) <= len(fields) <= 5, fields)
                self.assertEqual(len(fields), len(set(fields)))
                self.assertEqual([f for f in fields if f not in columns], [])

    def test_declared_only_in_policy(self):
        found = []
        for path in g.glob_bridge():
            with open(path, encoding="utf-8") as f:
                if re.search(r"^\s*SOURCE_FIELDS\s*=", f.read(), re.M):
                    found.append(os.path.basename(path))
        self.assertEqual(found, ["policy.py"])
        with open(os.path.join(g.REPO_ROOT, "bridge", "report.py"), encoding="utf-8") as f:
            self.assertIn("policy.SOURCE_FIELDS", f.read())


class SourceRowsInline(_Page):
    """Plan block "Five screens" replaces "the first cited row and +N more": every cited input row is on the page
    (`sources`, the full list; tested in test_screens.EveryCitedRowOnThePage, and for balances and the ledger cash
    balance with amounts in CloseFigureSourceTables, which brings back the deleted guarantee review 6 asked for). The
    case examples stay."""

    def test_case_examples(self):
        rows, page_rows = self.data["tables"]["exceptions"]["rows"], self.page("exceptions")["rows"]
        dup = [p.get("sources") or [] for r, p in zip(rows, page_rows) if r["key"] == "PX10000849"]
        self.assertEqual([(s[0]["ref"] if s else None, len(s)) for s in dup], [("processor_transactions.csv:851", 4)])
        self.assertIn("PX10000849", [t for _c, t in dup[0][0]["fields"]])
        cash = self.page("cash_recon")["rows"]
        bank = [(p.get("sources") or [{}])[0].get("ref") for r, p in zip(self.data["tables"]["cash_recon"]["rows"], cash)
                if r["line"] == "bank_balance"]
        self.assertEqual(bank, [g._line_of(g.BANK, "line_id", "BS0029")[0] + ":%d"
                                % g._line_of(g.BANK, "line_id", "BS0029")[1]])


class RowIds(_Page):
    """Plan (agent citations later): a row has a stable id per tab. Unique in its tab, and a row whose content does
    not change keeps its id when a planted change adds a row before it."""

    def ids(self, data, tab):
        return [p.get("row_id") for p in _page(data)[tab]["rows"]]

    def test_unique_per_tab(self):
        for tab in TABS:
            with self.subTest(tab=tab):
                ids = self.ids(self.data, tab)
                self.assertEqual([i for i in ids if not (isinstance(i, str) and i.strip())], [])
                self.assertEqual(len(ids), len(set(ids)))

    def test_stable_under_a_planted_row(self):
        with tempfile.TemporaryDirectory(prefix="bridge-rowid-") as tmp:
            data_dir = os.path.join(tmp, "datos")
            shutil.copytree(DATA_DIR, data_dir)
            g._shift_mc(data_dir, "MC2604007494015", D("-0.06"))  # PX10000604 becomes an amount_diff, early in leg 1
            planted = g._page_data(g._run_on(data_dir))
        key = lambda row: tuple(sorted(row.items()))  # noqa: E731
        moved = 0
        for tab in TABS:
            with self.subTest(tab=tab):
                before, after = collections.defaultdict(list), collections.defaultdict(list)
                for data, out in ((self.data, before), (planted, after)):
                    for pos, (row, rid) in enumerate(zip(data["tables"][tab]["rows"], self.ids(data, tab))):
                        out[key(row)].append((pos, rid))
                for content in set(before) & set(after):
                    if len(before[content]) == len(after[content]):
                        moved += sum(1 for (p, _a), (q, _b) in zip(before[content], after[content]) if p != q)
                        self.assertEqual(sorted(r for _p, r in before[content]),
                                         sorted(r for _p, r in after[content]))
        self.assertGreater(moved, 0, "the plant moved no unchanged row: the test would not tell ids from positions")


class CsvOutputsUnchanged(_Page):
    """Plan: no figure changes; the CSV outputs and their columns stay as they are, and the page's tables are the CSVs
    (the "+N more" rows are all in the CSV's src column)."""

    def test_files_columns_rows(self):
        for tab in TABS:
            with self.subTest(tab=tab):
                fields, rows = g._read_rows(self.out_dir, tab + ".csv")
                self.assertEqual(fields, CSV_COLUMNS[tab])
                self.assertEqual(len(rows), ROW_COUNTS[tab])
                table = self.data["tables"][tab]
                self.assertEqual(table["columns"], fields)
                self.assertEqual(table["rows"], rows)
        self.assertEqual(sorted(os.listdir(self.out_dir)), sorted(g.OUTPUT_FILES))


def _decimal_leaves(node):
    """Every decimal text reachable from `node` (dict values, list items)."""
    if isinstance(node, dict):
        return [x for v in node.values() for x in _decimal_leaves(v)]
    if isinstance(node, list):
        return [x for v in node for x in _decimal_leaves(v)]
    return [node] if isinstance(node, str) and g.DECIMAL_TEXT.match(node) else []


class TreasuryTab(_Page):
    """Plan block "Extras before submission", E9: the page gets a "Treasury" tab built like every other tab — its
    table is treasury.csv, one page row (with a unique id) per table row, and a summary on top with the closing
    balance, the average debit, the days of coverage at 30-Sep and the suggested weekly transfer = average x 5 + k
    standard deviations x sqrt(5), k declared once in policy.py and labelled illustrative. The settled readings are
    pinned (fresh review of the extras, Material 1): the duplicate debit left out, the sample deviation, k = 2. Figures
    recomputed by a throwaway script from the bank statement; the summary's layout inside the block is left free, so
    each figure is looked for among its decimal texts (rows excluded). The five-screens round moves Treasury into the
    Close screen; its figures stay in data["page"]["treasury"]."""

    def summary_texts(self):
        block = self.page("treasury")
        return _decimal_leaves({k: v for k, v in block.items() if k != "rows"})

    def test_tab(self):
        # Five screens replace the tabs: Treasury is a section of the Close screen, still built from its page block.
        script = g._page_script(self.out_dir)
        self.assertRegex(script, r"[\"']Treasury[\"']")
        self.assertRegex(script, r"PAGE\.treasury\b|PAGE\[\s*[\"']treasury[\"']\s*\]")

    def test_table_is_the_csv(self):
        self.assertTrue(os.path.isfile(os.path.join(self.out_dir, "treasury.csv")), "run.py wrote no treasury.csv")
        self.assertIn("treasury", sorted(self.data["tables"]), "the page carries no Treasury table")
        fields, rows = g._read_rows(self.out_dir, "treasury.csv")
        table = self.data["tables"]["treasury"]
        self.assertEqual((table["columns"], table["rows"]), (fields, rows))
        page_rows = self.page("treasury")["rows"]
        self.assertEqual(len(page_rows), len(rows))
        ids = [p.get("row_id") for p in page_rows]
        self.assertEqual([i for i in ids if not (isinstance(i, str) and i.strip())], [])
        self.assertEqual(len(ids), len(set(ids)))

    def test_summary_is_the_settled_reading(self):
        # Exactly the five settled figures (duplicate debit left out, sample deviation, k = 2), recomputed by a
        # throwaway script from bridge_account_statement.csv: 1,147,965.55; 43,973.93; 8,051.16; 26.11; 255,875.54.
        self.assertEqual(sorted(D(t) for t in self.summary_texts()), sorted(g.TREASURY_SUMMARY.values()))

    def test_suggested_transfer(self):
        import decimal
        from bridge import policy
        with decimal.localcontext() as ctx:
            ctx.prec = 50
            transfer = (g.TREASURY_MC_TOTAL / g.SEPTEMBER_BUSINESS_DAYS * policy.TREASURY_HORIZON_WD
                        + Decimal(policy.TREASURY_BUFFER_K) * g.TREASURY_SAMPLE_SD
                        * Decimal(policy.TREASURY_HORIZON_WD).sqrt())
        self.assertEqual(transfer.quantize(D("0.01"), decimal.ROUND_HALF_UP), g.TREASURY_SUMMARY["transfer"])
        self.assertIn(g.TREASURY_SUMMARY["transfer"], [D(t) for t in self.summary_texts()])

    def test_labelled_illustrative(self):
        import json
        text = g._page_script(self.out_dir) + json.dumps(self.page("treasury"))
        self.assertRegex(text, r"(?i)\billustrative\b")


# Amended by 795490d (Reconciliation reads by type): the type is the first column, then the date.
EXCEPTION_DATE = "date|origin"
EXCEPTION_VISIBLE = ("type", EXCEPTION_DATE, "net", "age_wd", "escalates", "who_fixes", "clara_owner", "action",
                     "src|source")
EXCEPTION_HIDDEN = ("leg", "cls", "country", "origin", "requires_explanation", "controller_action", "gross")


class PageScript(unittest.TestCase):
    """Plan, static half: the "By figure" tab, the drill panel and the figures blob are gone; the page reads the page
    block; every table has a sum row, a filter and a CSV download; the exceptions table shows its columns in the
    amended plan's order (date, type, net, age, escalates, who fixes, Clara owner, what to do, source, then the notes),
    with leg, class, country, origin, needs explanation, controller action and gross kept as filters or hidden."""

    @classmethod
    def setUpClass(cls):
        cls.out_dir = g._run()[0]
        # The page script without the blob and without the embedded fonts (base64 can spell any word).
        cls.script = re.sub(r"data:[\w/+.-]+;base64,[A-Za-z0-9+/=]+", "", g._page_script(cls.out_dir))
        cls.data = g._page_data(cls.out_dir)

    def test_by_figure_gone(self):
        self.assertNotIn("By figure", self.script)
        self.assertNotIn("figures", self.data)
        # Narrowed by the repairs block (minors): the ban is on the deleted top-level blob, data.figures; the Summary's
        # own list (page.overview.figures) is allowed to be read by its key.
        self.assertNotRegex(self.script, r"\bdata\.figures\b|\bdata\[\s*[\"']figures[\"']\s*\]")

    def test_drill_gone(self):
        self.assertNotIn('id="drill"', self.script)
        self.assertNotRegex(self.script, r"function\s+drill\b")
        self.assertNotRegex(self.script, r"(?i)drill")

    def test_reads_the_page_block(self):
        found = re.search(r"\bdata\.page\b|\bdata\[\s*[\"']page[\"']\s*\]", self.script)
        self.assertTrue(found, "the page script never reads data.page")
        after = self.script[found.start():]
        self.assertRegex(after, r"createTFoot\(|[\"']tfoot[\"']|<tfoot")
        self.assertRegex(after, r"download\(")
        self.assertRegex(after, r"[\"']All[\"']")

    def test_exceptions_visible_columns_in_order(self):
        lists = []
        for m in re.finditer(r"\[[^\[\]]*\]", self.script):
            keys = re.findall(r"[\"'](\w+)[\"']", m.group(0))
            if {"who_fixes", "clara_owner", "action"} <= set(keys):
                lists.append(keys)
        visible = [k for k in lists if "gross" not in k]
        self.assertTrue(visible, "no visible-column list for the exceptions table (without gross)")
        keys = visible[0]
        at = []
        for pattern in EXCEPTION_VISIBLE:
            hits = [i for i, k in enumerate(keys) if re.fullmatch(pattern, k)]
            self.assertTrue(hits, "%s missing from %s" % (pattern, keys))
            at.append(hits[0])
        self.assertEqual(at, sorted(at), keys)
        self.assertEqual([k for k in keys if k in EXCEPTION_HIDDEN and not re.fullmatch(EXCEPTION_DATE, k)],
                         [], keys)
        notes = [i for i, k in enumerate(keys) if k in ("assigned_person", "status", "comment")]
        self.assertEqual([i for i in notes if i < at[-1]], [], keys)

    def test_moved_columns_are_filters(self):
        state = re.search(r"var filt\s*=\s*\{[^}]*\}", self.script)
        self.assertTrue(state, "no filter state in the page script")
        for field in ("leg", "cls", "country", "requires_explanation", "controller_action"):
            self.assertRegex(self.script, r"filt(\.%s\b|\[\s*[\"']%s[\"']\s*\])" % (field, field))
            self.assertRegex(state.group(0), r"\b%s\s*:" % field)
