"""Tests for plan block "Five screens by the person who operates them" (95dee86; Andrés, 2026-10-15). Five screens
replace the tabs: Summary, Data quality, Reconciliation, Pending actions, Close. The round also fixes review 6's
material findings (every cited input row on the page; a click keeps the table in view) and minors 3, 5 and 6. The plan
block "Repairs after the five-screens review" (b3a73a8) is encoded at the end of this file; the assertions of 1516c24
it changes are amended in place and say so. The plan block "The Mastercard payable reconciled against Mastercard"
(297c8bf, 01788a5) is encoded after it, then the plan block "The payable bridge reads on its own, and the last page
fixes" (cd7512e), the plan block "Honest evidence on every entry line, and the closing fixes" (de0b6cb), and the plan
block "Last round before freezing: waterfalls, impact per action, ERP file, explanations" (dee2151) last; the
assertions each changes are amended in place and say so.

The page script cannot run in the suite, so, as in test_page.py, the tests read the JSON blob in index.html and, for
the presence of a feature only, the page script. The blob shape these tests fix (on top of test_page.py's):

    data["manifest"]["totals"]["matches"] = {           # computed once in recon.py
        "1": {"processor_rows" | "mastercard_rows" | "matched_equal" | "matched_diff" | "processor_only"
              | "mastercard_only": {"count": "<n>", "usd": "<decimal>"}},
        "2": {"settlement_days" | "paired" | "unpaired" | "duplicate_debits": {"count": "<n>", "usd"?: "<decimal>"}}}
    data["page"]["overview"] = {                         # the Summary screen
        "figures": [{"id": "<leg>.<name>", "leg": "1"|"2"|"3", "label": <text>, "count"?: "<n>", "usd"?: "<decimal>",
                     "link"?: {"screen": <text>, "table": <data["tables"] key>, "filter": {<column>: <value or
                               [values]>}, "sum"?: <column summed into usd>}
                              | {"screen": "Reconciliation", "grouped": "1"|"2", "sum": <column of grouped[leg]>}},
                     ...],                               # "1.processor_duplicate" among them; every figure links but
                                                         # "1.matched_equal" and a figure whose count is 0
        "explained": [{"leg", "total", "timing", "real_error", "data_issue", "unexplained"}, ...],   # legs 1, 2, 3
        "close_status": <the Pending actions sentence>, "data_quality": <one sentence>,     # no "summary" key
        <the leg-1 gross difference of the files, "14884.40">}   # cd7512e: in the data under a key of the
                                                 # implementer's choosing (the test finds it outside "figures"); no
                                                 # "3.ledger_2105" figure
    data["page"]["grouped"] = {                          # no "summary" key
        "1": [{"type": "matched_equal" | <leg-1 difference type>, "count"?: "<pairs>", "processor_usd",
               "mastercard_usd", "difference", "exceptions", "ids": [row_id]}],
                                                         # 795490d: by type, the matched-exactly pairs first (was by
                                                         # the processor's clearing date)
        "2": [{"date", "mastercard_net", "bank_debit", "difference", "exceptions", "ids": [row_id]}],
                                                         # by settlement date, the duplicate debit on its day
        "3": [{"account", "name": <account name from gl_opening_balances.csv>, "ledger", "record_label", "record",
               "difference": ledger - record, "reconciling_items", "unreconciled": difference - items (0.00),
               "ids", ...}]}                    # one row per account; "ids" = the row ids a click filters to; the
                                                # 2105 items say they include E10 (amended by cd7512e)
    data["page"][tab]["rows"][i]["sources"] = [{"ref": "file:locator", "fields": [[column, text], ...],
                                                "amount"?: "<decimal>"}, ...]   # every cited input row, in src order;
                                                # "amount" (the row's signed share of the figure) on balances and cash
    data["page"]["checks"]["rows"][i]["meaning"] = <what a failed check means for the result>
    data["page"]["pending"] = {                          # no "summary" key
        "status": {"open_tasks", "blocked_tasks", "entries", "entries_usd", "waiting_outside"}, "sentence": <text>,
        "tasks": [{"task_id", "status", "owner", "lacks": {"exceptions": [row_id], "entries": [entry_id],
                   "checks": [check name]}, "text": <the tool finding: what it lacks, or that there is no tool evidence>,
                   "drafts": [draft id],                        # one per checklist task, open ones first; the page
                                                                # shows "text" in a "Tool finding" column, never in Status
                   "link"?: <a Close link, as the bridge's>}],  # de0b6cb: T08's is the bridge's entries link
                                                                # ({entry_id, account: 2105}, debit - credit); it sums
                                                                # to T08's figure; "text" of a task that lacks only a
                                                                # reconciling (timing) item reads "Waits on ...", and
                                                                # such a task is not blocked
        "drafts": [{"id", "to": "Mastercard"|"Processor", "template": <key of a policy.py templates dict>,
                    "types": [difference type], "rows": [exception row_id], "checks": [check name], "text": <draft>}]}
    data["page"]["overview"]["payable_bridge"] = [       # 2105 against Mastercard's own files (amended by cd7512e);
                                                         # its title "Mastercard payable 2105 against Mastercard's own
                                                         # files" is in the data or the page script
        {"basis": "confirmed" | "all",                   # columns: the entries with no condition / all of them
         "label": "Entries with no condition (8)" | "All entries, if E10's evidence arrives (9)",
         "note"?: "9,127.92 = E10: 3 processor-only rows; its entry waits for evidence."   # on "confirmed" only;
                                                                                             # computed (de0b6cb)
         "lines": [{"line": "ledger" | "entries" | "result" | "settlement" | "timing" | "difference",   # this order
                    "label": <text>, "usd": "<decimal>", "side"?: "debit" | "credit", ...}]}, ...]
        # usd as shown: a "credit" line is positive ("Ledger after the entries (credit)" 45,572.30), so debit-positive
        # it is -usd; ledger "side": "debit" ("Ledger at 30-Sep (debit — the wrong side)"); entries debit - credit
        # ("Proposed entries on 2105"); settlement "Mastercard settlements not debited by 30-Sep (30-Sep)" (de0b6cb:
        # it names the unpaid days) and timing "September transactions Mastercard cleared in October (timing)",
        # positive; difference = result - settlement - timing. The "note" is computed (de0b6cb): "X = E10: N
        # processor-only rows ..." only when the difference equals E10's 2105 net, N from E10's own sources;
        # otherwise "of which X is E10; Y not explained".
        # Every figure opens rows that sum to it (debit-positive): either "link" or "sources" [{"ref", "amount"}].
        # A link here: {"screen": "Close", "table", "filter", "sum": <column> | ["debit", "credit"] (debit - credit)},
        # or a list of such links whose rows are shown together. Where opened rows carry source amounts, they add up
        # to the link's sum (the page's tie).
        # ledger:  {"table": "balances", "filter": {"account": "2105"}, "sum": "before"}
        # result:  [the ledger's link, the entries' link] — the ledger's rows plus the entries' 2105 lines
        # entries: {"table": "proposed_entries", "filter": {"entry_id": [ids], "account": "2105"},
        #           "sum": ["debit", "credit"]} — the 2105 lines of the column's entries (8 or 9)
        # difference on "confirmed": the same link over E10, the entry waiting for evidence (9,127.92)
        # settlement, timing: "sources", the Mastercard rows owed (summary line / the four cut-off rows), or a link
    data["page"]["proposed_entries"]["rows"][i]["sources"]: the refs of the line's own `src` in proposed_entries.csv
        (de0b6cb: the file is cd9981d's again, byte for byte, and no line cites gl_opening_balances.csv unless its
        entry is built from it); the page lists a ref once per entry and says "same evidence as the line above"
        (the display marker, in the page script or the data), the data is not changed for display
    data["page"]["grouped"]["3"][<the 2105 row>]["bridge"] = data["page"]["overview"]["payable_bridge"]
    # dee2151 (last round before freezing):
    data["page"]["overview"]["waterfalls"] = [           # one per pair of records; computed in Python, the script draws
        {"leg": "1" | "2" | "3", "basis"?: "confirmed" | "all",       # leg 3 = the payable 2105, per bridge basis
         "title": <text>, "glossary": <GLOSSARY key>,
         "start" | "end": <bar>, "bars": [<bar>, ...]}, ...]          # start + sum(bars) = end, to the cent
        # <bar> = {"label": <text>, "usd": "<decimal>", "side"?: "debit" | "credit" (as the bridge), "glossary": <key>,
        #          "type"?: <difference type, leg 1>, "link"?: <a Summary figure's or bridge line's link>,
        #          "sources"?: [{"ref", "amount"}]}       # what it opens sums to it (to its negative allowed for the
        #                                                 # bars of a whole waterfall); a 0.00 bar may open nothing
        # leg 1: 924,303.45 -> one bar per type in LEG1_BAR_TYPES -> 909,419.05; leg 2: 968,096.50 -> the duplicate
        # debit 40,616.94 -> 1,008,713.44; leg 3: ledger 70,588.66 -> ... -> the bridge's difference (0.00 on "all"),
        # "E10" and 9,127.92 on it
    data["page"]["overview"]["figures"][i]["glossary"], ...["payable_bridge"][j]["lines"][k]["glossary"]: <key>
    data["page"]["screens"] = [{"name": <screen>, "glossary": <key>}, ...]   # SCREENS, in order
    data["page"]["glossary"] = {<key>: <text>}           # the texts of policy.GLOSSARY the page uses, read as data
    data["page"]["pending"]["tasks"][i]["resolves"] = {"usd": <X, what it is ordered by>, "legs": {leg: <net>},
                                                       "entries_2105"?: <the 2105 net of its entries>}
    data["page"]["pending"]["resolves_usd"] = <the total on top: each exception once, no entry on top>
    # a6596cf (freeze fixes): data["page"]["pending"]["resolves_split"] = {"timing": <T07's funding in transit>,
    # "errors": <the rest>}, adding to resolves_usd; task["resolves"]["tag"] = "timing" on T07; a waterfall bar's
    # exceptions link that sums a column hidden by default carries "show": [<column>]; the script reads the screens
    # from data["page"]["screens"] and holds no list of them.

Case figures recomputed from the raw files by throwaway scripts that never import bridge
(/private/tmp/claude-501/verifier50/recount.py): leg 1 has 3,117 processor rows (924,303.45) and 3,113 Mastercard rows
(909,419.05, four of them cleared on 1-2 Oct and matched to September rows), 2,997 pairs with no difference
(881,142.94), 111 with a difference (net 4,919.98 = fx 751.93 + amount 737.29 + sign 2,502.45 + cut-off 928.31), 3
processor-only rows (net 9,127.92) and 5 Mastercard-only rows (net -2,041.36); leg 2 has 22 settlement days
(968,096.50), all paired, and one duplicate debit (40,616.94).

Not automated (checked by hand in Chrome by the session at 1440x900): the Summary fits without scrolling, with at least
40 px of margin, and the owed rows open below the fold without moving it (cd7512e); every click keeps the table in view;
a group row switches to Detailed filtered to its day or account; a source row expands in place; the copy button and the
.txt download work. Not encoded: "the 2105 difference is computed once" (a code-structure rule; the tests only tie the
bridge and Grouped leg 3 figures to each other; de0b6cb adds that each Grouped leg-3 2105 figure equals the bridge's,
on the case data and on the BS0024 plant, and that bridge/*.py reads no filter back from a link). Also by hand
(de0b6cb): the bridge label column wraps and no label overlaps its figure; opening the settlement or timing rows does
not move the Summary; one click opens only that line's rows; a multi-part click shows no single footer sum.
"""

import collections
import json
import os
import re
import unittest
from decimal import Decimal

from tests import test_golden as g
from tests.test_golden import D, DATA_DIR, GL_LINES, GL_OPENING
from tests.test_page import EXCEPTION_TYPES, LEG_SUBTOTALS, TABS, _input_index, _parts, _same, _source_fields

SCREENS = ("Summary", "Data quality", "Reconciliation", "Pending actions", "Close")
MATCHES = {
    "1": {"processor_rows": (3117, D("924303.45")), "mastercard_rows": (3113, D("909419.05")),
          "matched_equal": (2997, D("881142.94")), "matched_diff": (111, D("4919.98")),
          "processor_only": (3, D("9127.92")), "mastercard_only": (5, D("-2041.36"))},
    "2": {"settlement_days": (22, None), "paired": (22, None), "unpaired": (0, None),
          "duplicate_debits": (1, D("40616.94"))}}
LEG1_PAIR_TYPES = ("fx_rate_diff", "amount_diff", "sign_flip", "month_cutoff", "usd_conversion_error")
ESCALATES = {"1": 118, "2": 1, "3": 2}
WAITING_OUTSIDE = {"1": 251, "2": 1, "3": 1}   # who fixes is Mastercard or the processor
OUTSIDE = ("Mastercard", "Processor")
# 795490d retired the per-day leg-1 figures (Grouped leg 1 is by type); the two column totals stay.
LEG1_DAY_TOTALS = (D("924303.45"), D("909419.05"))
# Amended by the repairs block (material 4): the duplicate debit BS0018 (40,616.94) now sits in the bank column.
LEG2_DAYS = (22, D("968096.50"), D("1008713.44"))
OPEN_TASKS, ENTRIES, ENTRIES_USD = 20, 11, D("172291.89")
PAYABLE = "2105"
NO_EVIDENCE = "No tool evidence; depends on the owner"
# The drafts the case data needs: (recipient, a difference type it covers) or (recipient, a failed check).
DRAFT_TYPES = [("Mastercard", "mastercard_only"), ("Mastercard", "bank_duplicate_debit"),
               ("Processor", "processor_duplicate"), ("Processor", "sign_flip"), ("Processor", "amount_diff"),
               ("Processor", "fx_rate_diff")]
# Amended by the repairs block (material 7): the only failing summary day, 31-Aug, lies outside the detail file's
# settlement dates, so it becomes a coverage note and no draft remains; the draft is planted in SummaryCheckDraft.
DRAFT_CHECKS = []


def setUpModule():
    g.setUpModule()


def _num(text):
    return D(text) if text not in (None, "") else D("0")


def _tool_evidence_entries(entry_rows):
    """Repairs block, material 3: the entries a task with no exception lacks — T13 every proposed entry (they wait for
    approval), T08 the entries with a line on the payable 2105 (the roll-forward)."""
    return {"T13": {e["entry_id"] for e in entry_rows},
            "T08": {e["entry_id"] for e in entry_rows if e["account"] == PAYABLE}}


def _draft_rows(tpl, by_id):
    """Repairs block, material 6: the row ids a draft template holds — its types, and the fixer it declares."""
    return [i for i, r in by_id.items() if r["type"] in tpl.get("types", ())
            and r["who_fixes"] == tpl.get("fixer", r["who_fixes"])]


class _Screens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = g._result()
        cls.out_dir = g._run()[0]
        cls.data = g._page_data(cls.out_dir)
        cls.script = re.sub(r"data:[\w/+.-]+;base64,[A-Za-z0-9+/=]+", "", g._page_script(cls.out_dir))

    def block(self, name):
        page = self.data.get("page") or {}
        self.assertIn(name, sorted(page), "the page blob has no %r block" % name)
        return page[name]

    def table(self, tab):
        return self.data["tables"][tab]["rows"]

    def exceptions(self):
        """(table row, page row) per exception."""
        return list(zip(self.table("exceptions"), self.data["page"]["exceptions"]["rows"]))


class FiveScreens(_Screens):
    """Five screens replace the tabs, in the order the person works: Summary, Data quality, Reconciliation (Detailed
    and Grouped views), Pending actions, Close (with Treasury)."""

    def test_screens_in_order(self):
        # Amended by a6596cf (one screen list): the page reads the five screens from data["page"]["screens"] and the
        # script holds no copy (FreezeFixes.test_no_screen_list_in_the_script), so the order is pinned on the data.
        self.assertEqual([s.get("name") for s in self.block("screens")], list(SCREENS), "the five screens in order")

    def test_old_tabs_gone(self):
        self.assertNotRegex(self.script, r"\[\s*[\"']close_tracker[\"']\s*,\s*[\"']Close tracker[\"']\s*\]")
        self.assertNotRegex(self.script, r"\[\s*[\"']checks[\"']\s*,\s*[\"']Checks[\"']\s*\]")

    def test_two_views_of_reconciliation(self):
        for word in ("Detailed", "Grouped"):
            self.assertRegex(self.script, r"[\"']%s[\"']" % word)

    def test_click_keeps_the_table_in_view(self):
        # Review 6, material 2: the click scrolls the table into view (whether it lands in view is the Chrome check).
        self.assertRegex(self.script, r"\.scrollIntoView\(")


class MatchCountsInManifest(_Screens):
    """Plan: the per-leg match counts are computed once in recon.py and written to run_manifest.json totals; recomputed
    here against a throwaway script that reads the raw files."""

    def test_counts(self):
        import json
        with open(os.path.join(self.out_dir, "run_manifest.json"), encoding="utf-8") as f:
            matches = json.load(f)["totals"].get("matches")
        self.assertIsInstance(matches, dict, "run_manifest.json totals carry no per-leg match counts")
        for leg, expected in MATCHES.items():
            for name, (count, usd) in expected.items():
                with self.subTest(leg=leg, figure=name):
                    got = matches.get(leg, {}).get(name, {})
                    self.assertEqual(int(got.get("count", -1)), count)
                    if usd is not None:
                        self.assertEqual(_num(got.get("usd")), usd)

    def test_matches_tie_to_the_exceptions(self):
        # A pair with a difference is an exception of a pair type; the one-side rows are the one-side exceptions.
        found = sum(EXCEPTION_TYPES[t][0] for t in LEG1_PAIR_TYPES if t in EXCEPTION_TYPES)
        self.assertEqual(found, MATCHES["1"]["matched_diff"][0])
        self.assertEqual(sum((EXCEPTION_TYPES[t][1] for t in LEG1_PAIR_TYPES if t in EXCEPTION_TYPES), D("0")),
                         MATCHES["1"]["matched_diff"][1])
        p, m = MATCHES["1"]["processor_rows"][0], MATCHES["1"]["mastercard_rows"][0]
        pairs = MATCHES["1"]["matched_equal"][0] + MATCHES["1"]["matched_diff"][0]
        dups = EXCEPTION_TYPES["processor_duplicate"][0]
        self.assertEqual(p, pairs + dups + MATCHES["1"]["processor_only"][0])
        self.assertEqual(m, pairs + MATCHES["1"]["mastercard_only"][0])


class SummaryScreen(_Screens):
    """Plan: the Summary shows one block per leg, how much is explained, what is wrong, one close-status sentence and
    one data-quality sentence; every figure links to the screen and filter that shows its rows and equals the sum of
    those rows."""

    def figures(self):
        figures = self.block("overview").get("figures", [])
        self.assertTrue(figures, "the Summary carries no figures")
        return {f["id"]: f for f in figures}

    def rows_of(self, link):
        if "grouped" in link:   # repairs block, minors: a link to a Grouped leg (its rows, summed by its column)
            return self.block("grouped")[link["grouped"]]
        self.assertIn(link.get("table"), sorted(self.data["tables"]), link)
        rows = self.table(link["table"])
        for column, value in link.get("filter", {}).items():
            wanted = value if isinstance(value, list) else [value]
            rows = [r for r in rows if r.get(column) in wanted]
        return rows

    def test_every_linked_figure_equals_its_rows(self):
        linked = [f for f in self.figures().values() if f.get("link")]
        self.assertTrue(linked, "no Summary figure links to its rows")
        for f in linked:
            with self.subTest(figure=f["id"]):
                link = f["link"]
                self.assertTrue(str(link.get("screen", "")) in SCREENS, link)
                rows = self.rows_of(link)
                if "count" in f and ("grouped" not in link or link["grouped"] == "2"):   # a leg-1 count is input rows
                    self.assertEqual(int(f["count"]), len(rows))
                if "usd" in f:
                    self.assertIn("sum", link, "a USD figure whose link names no column to sum")
                    self.assertEqual(D(f["usd"]), sum((_num(r[link["sum"]]) for r in rows), D("0")))

    def test_what_is_wrong_per_leg(self):
        figures = self.figures()
        for leg, count, net in LEG_SUBTOTALS:
            with self.subTest(leg=leg):
                f = figures.get("%s.exceptions" % leg, {})
                self.assertEqual((int(f.get("count", -1)), _num(f.get("usd"))), (count, net))
                self.assertEqual(f.get("link", {}).get("filter"), {"leg": leg})
                self.assertEqual(int(figures.get("%s.escalates" % leg, {}).get("count", -1)), ESCALATES[leg])
                waiting = figures.get("%s.waiting_outside" % leg, {})
                self.assertEqual(int(waiting.get("count", -1)), WAITING_OUTSIDE[leg])
                self.assertEqual(sorted(waiting.get("link", {}).get("filter", {}).get("who_fixes", [])),
                                 sorted(OUTSIDE))

    def test_match_figures_equal_the_manifest(self):
        figures = self.figures()
        for leg, expected in MATCHES.items():
            for name, (count, usd) in expected.items():
                with self.subTest(figure="%s.%s" % (leg, name)):
                    f = figures.get("%s.%s" % (leg, name), {})
                    self.assertEqual(int(f.get("count", -1)), count)
                    if usd is not None:
                        self.assertEqual(_num(f.get("usd")), usd)

    def test_leg3_shows_the_ledger_and_the_bank(self):
        usd = {_num(f.get("usd")) for f in self.figures().values() if f.get("leg") == "3" and "usd" in f}
        for figure in (D("1547965.55"), D("1147965.55")):
            self.assertIn(figure, usd)

    def test_how_much_is_explained(self):
        rows = self.table("exceptions")
        explained = {e["leg"]: e for e in self.block("overview").get("explained", [])}
        self.assertEqual(sorted(explained), ["1", "2", "3"])
        for leg, _count, net in LEG_SUBTOTALS:
            with self.subTest(leg=leg):
                e = explained[leg]
                self.assertEqual(D(e["total"]), net)
                for cls in ("timing", "real_error", "data_issue"):
                    self.assertEqual(D(e[cls]), sum((D(r["net"]) for r in rows if r["leg"] == leg and r["cls"] == cls),
                                                    D("0")), cls)
                self.assertEqual(D(e["unexplained"]), D("0.00"))
                self.assertEqual(D(e["timing"]) + D(e["real_error"]) + D(e["data_issue"]) + D(e["unexplained"]),
                                 D(e["total"]))

    def test_close_status_and_data_quality_sentences(self):
        overview = self.block("overview")
        self.assertEqual(overview.get("close_status"), self.block("pending").get("sentence"))
        quality = str(overview.get("data_quality", ""))
        self.assertTrue(quality.strip())
        self.assertRegex(quality, r"\b%s\b" % self.data["manifest"]["totals"]["checks_failed"])


class GroupedView(_Screens):
    """Plan: the Grouped view has one row per day for legs 1 and 2 and one row per account for leg 3. Day totals
    recomputed by the throwaway script from the raw files."""

    def test_leg1_columns_add_up(self):
        # Amended by 795490d (Reconciliation reads by type): Grouped leg 1 is by type, not by clearing date, so the
        # per-day figures (LEG1_DAYS) and the per-day exception counts are retired; the column totals and each row's
        # difference stay. The by-type rows are pinned in ReconciliationByType.
        rows = self.block("grouped").get("1", [])
        self.assertTrue(rows)
        self.assertEqual((sum((_num(r["processor_usd"]) for r in rows), D("0")),
                          sum((_num(r["mastercard_usd"]) for r in rows), D("0"))), LEG1_DAY_TOTALS)
        for r in rows:
            with self.subTest(row=r.get("type") or r.get("date")):
                self.assertEqual(D(r["difference"]), _num(r["processor_usd"]) - _num(r["mastercard_usd"]))

    def test_leg2_by_settlement_date(self):
        rows = self.block("grouped").get("2", [])
        self.assertEqual((len(rows), sum((_num(r["mastercard_net"]) for r in rows), D("0")),
                          sum((_num(r["bank_debit"]) for r in rows), D("0"))), LEG2_DAYS)
        for r in rows:
            self.assertEqual(D(r["difference"]), _num(r["bank_debit"]) - _num(r["mastercard_net"]), r["date"])

    def test_leg3_one_row_per_account(self):
        rows = self.block("grouped").get("3", [])
        accounts = [r.get("account") for r in rows]
        self.assertEqual(len(accounts), len(set(accounts)))
        self.assertIn("1110", accounts)


class EveryCitedRowOnThePage(_Screens):
    """Review 6, material 1: every cited input row of every page row is on the page, with its key fields; leg-1 rows
    show both sides, and the processor and Mastercard fields carry the local amount and the rate (merchant name
    dropped)."""

    def test_every_tab(self):
        index, declared = _input_index(self.r), _source_fields()
        for tab in TABS + ("treasury",):
            with self.subTest(tab=tab):
                wrong = []
                for row, page_row in zip(self.table(tab), self.data["page"][tab]["rows"]):
                    cited = [p for p in _parts(row["src"]) if p in index]
                    sources = page_row.get("sources")
                    if not isinstance(sources, list) or [s.get("ref") for s in sources] != cited:
                        wrong.append((row["src"][:80], "sources", sources and [s.get("ref") for s in sources][:3]))
                        continue
                    for s in sources:
                        fields = [list(f) for f in s.get("fields", [])]
                        input_row = index[s["ref"]]
                        if ([f[0] for f in fields] != declared[s["ref"].split(":", 1)[0]]
                                or not all(_same(t, input_row[c]) for c, t in fields)):
                            wrong.append((s["ref"], fields))
                self.assertEqual(wrong[:5], [])

    def test_leg1_fields_carry_local_amount_and_rate(self):
        declared = _source_fields()
        for file_name, gone in ((g.PROCESSOR, "merchant_name"), (g.MC_DETAIL, "merchant_descriptor")):
            with self.subTest(file=file_name):
                self.assertIn("amount_local", declared[file_name])
                self.assertIn("fx_rate", declared[file_name])
                self.assertNotIn(gone, declared[file_name])
                self.assertLessEqual(len(declared[file_name]), 5)

    def test_leg1_pairs_show_both_sides(self):
        for row, page_row in self.exceptions():
            if row["leg"] == "1" and row["type"] in LEG1_PAIR_TYPES:
                files = {s["ref"].split(":", 1)[0] for s in page_row.get("sources") or []}
                self.assertTrue({g.PROCESSOR, g.MC_DETAIL} <= files, row["key"])


def _raw_figure_rows(account):
    """The opening line and the September ledger lines of an account, with their debit-positive amounts."""
    _f, opening = g._read_rows(DATA_DIR, GL_OPENING)
    _f, lines = g._read_rows(DATA_DIR, GL_LINES)
    out = [("%s:%d" % (GL_OPENING, i + 2), D(o["opening_balance_usd_dr_positive"]))
           for i, o in enumerate(opening) if o["account"] == account]
    out += [("%s:%d" % (GL_LINES, i + 2), D(x["debit_usd"] or "0") - D(x["credit_usd"] or "0"))
            for i, x in enumerate(lines) if x["account"] == account and x["posting_date"] <= "2026-09-30"]
    return out


class CloseFigureSourceTables(_Screens):
    """Plan: for a figure built from many rows (each balance, the ledger cash balance) a second table lists the source
    rows of the selected figure, with amounts and a sum row equal to the figure (Andrés, 2026-10-14). Recomputed
    from the raw ledger files: exactly the opening line and the September lines, each with its amount."""

    def check(self, page_row, figure, account):
        sources = page_row.get("sources") or []
        got = [(s.get("ref"), _num(s.get("amount"))) for s in sources]
        self.assertEqual(sorted(got), sorted(_raw_figure_rows(account)))
        self.assertEqual(sum((a for _r, a in got), D("0")), figure)

    def test_each_balance(self):
        for row, page_row in zip(self.table("balances"), self.data["page"]["balances"]["rows"]):
            with self.subTest(account=row["account"]):
                self.check(page_row, D(row["before"]), row["account"])

    def test_ledger_cash_balance(self):
        found = [(r, p) for r, p in zip(self.table("cash_recon"), self.data["page"]["cash_recon"]["rows"])
                 if r["line"] == "ledger_balance"]
        self.assertEqual(len(found), 1)
        self.assertEqual(D(found[0][0]["amount"]), D("1547965.55"))
        self.check(found[0][1], D("1547965.55"), "1110")

    def test_source_table_downloads(self):
        self.assertGreaterEqual(len(re.findall(r"\bdownload\(", self.script)), 3)


class DataQualityScreen(_Screens):
    """Plan: one row per input file (from the manifest), the pre-checks table, a failed check says what it means for
    the result, and the "not reliable" banner stays."""

    def test_failed_check_says_what_it_means(self):
        for row, page_row in zip(self.table("checks"), self.data["page"]["checks"]["rows"]):
            if row["passed"] == "false":
                with self.subTest(check=row["name"]):
                    meaning = str(page_row.get("meaning", "")).strip()
                    self.assertTrue(meaning, "a failed check without its meaning for the result")
                    self.assertNotEqual(meaning, row["detail"])

    def test_inputs_and_banner(self):
        self.assertTrue(self.data["manifest"]["files"])
        self.assertIn("not reliable", self.script)


def _checklist_lines():
    """task_id -> its `close_checklist.csv:<line>` reference, from the raw checklist."""
    _f, rows = g._read_rows(DATA_DIR, g.CHECKLIST)
    return {r["task_id"]: "%s:%d" % (g.CHECKLIST, i + 2) for i, r in enumerate(rows)}, rows


class PendingActions(_Screens):
    """Plan: "what is missing to close September", built on the close checklist. One sentence with figures; one row per
    checklist task, open ones first, saying what it lacks — the exceptions, entries and failed checks linked to it
    through the existing type -> task map; the tool never marks a task done; drafted messages, never sent.

    The link, as the expected sets are derived here: an exception is linked to the task whose checklist row it cites
    (the type -> task map writes that row into its src); an entry to the tasks of the money exceptions it corrects (all
    of their input rows are among the entry's; data-issue flags carry no entry); a failed check to the tasks whose
    checklist row it cites (a failed check citing none is not constrained)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lines, cls.checklist = _checklist_lines()
        cls.task_of_line = {v: k for k, v in cls.lines.items()}

    def tasks(self):
        tasks = self.block("pending").get("tasks", [])
        self.assertTrue(tasks)
        return tasks

    def expected(self):
        ex = collections.defaultdict(set)
        money = []
        for row, page_row in self.exceptions():
            refs = _parts(row["src"])
            for ref in refs:
                if ref in self.task_of_line:
                    ex[self.task_of_line[ref]].add(page_row["row_id"])
                    if row["cls"] != "data_issue":
                        money.append((self.task_of_line[ref], {p for p in refs if p not in self.task_of_line}))
        entry_refs = collections.defaultdict(set)
        for e in self.table("proposed_entries"):
            entry_refs[e["entry_id"]].update(_parts(e["src"]))
        entries = collections.defaultdict(set)
        for task, refs in money:
            for entry_id, has in entry_refs.items():
                if refs and refs <= has:
                    entries[task].add(entry_id)
        # Amended by the repairs block (material 3): a task with no exception takes its evidence from
        # policy.TOOL_EVIDENCE — T13 lacks the 11 entries awaiting approval, T08 the entries on 2105.
        for task, ids in _tool_evidence_entries(self.table("proposed_entries")).items():
            if not ex.get(task):
                entries[task] |= ids
        checks = collections.defaultdict(set)
        for c in self.table("checks"):
            if c["passed"] == "false":
                for ref in _parts(c["src"]):
                    if ref in self.task_of_line:
                        checks[self.task_of_line[ref]].add(c["name"])
        return ex, entries, checks

    def test_one_row_per_checklist_task_open_first(self):
        tasks = self.tasks()
        self.assertEqual(sorted(t["task_id"] for t in tasks), sorted(self.lines))
        done = [t["status"] == "Done" for t in tasks]
        self.assertEqual(done, sorted(done), "open tasks first")

    def test_no_status_differs_from_the_checklist(self):
        status = {r["task_id"]: r["status_wd3_0900"] for r in self.checklist}
        owner = {r["task_id"]: r["owner_role"] for r in self.checklist}
        for t in self.tasks():
            self.assertEqual((t["status"], t.get("owner")), (status[t["task_id"]], owner[t["task_id"]]), t["task_id"])
        # The tracker table keeps the checklist's status too.
        for row in self.table("close_tracker"):
            self.assertEqual(row["status_wd3_0900"], status[row["task_id"]], row["task_id"])

    def test_what_each_open_task_lacks(self):
        ex, entries, checks = self.expected()
        cited_by_others = {c["name"] for c in self.table("checks") if c["passed"] == "false"
                           and any(p in self.task_of_line for p in _parts(c["src"]))}
        for t in self.tasks():
            if t["status"] == "Done":
                continue
            task = t["task_id"]
            with self.subTest(task=task):
                lacks = t.get("lacks", {})
                self.assertEqual(set(lacks.get("exceptions", [])), ex.get(task, set()))
                self.assertEqual(set(lacks.get("entries", [])), entries.get(task, set()))
                got = set(lacks.get("checks", []))
                self.assertTrue(checks.get(task, set()) <= got, (got, checks.get(task)))
                self.assertEqual((got & cited_by_others) - checks.get(task, set()), set())
                text = str(t.get("text", "")).strip()
                self.assertTrue(text)
                if not any(lacks.get(k) for k in ("exceptions", "entries", "checks")):
                    self.assertIn(NO_EVIDENCE, text)

    def test_case_links(self):
        ex, entries, checks = self.expected()
        self.assertEqual({t: sorted(e) for t, e in entries.items()},
                         {"T02": ["E01", "E02"], "T05": ["E06", "E07", "E08", "E09", "E10", "E11"], "T06": ["E03"],
                          "T09": ["E04"], "T11": ["E05"],
                          # Amended by the repairs block (material 3), as in expected().
                          "T08": ["E01", "E02", "E03", "E06", "E07", "E08", "E09", "E10", "E11"],
                          "T13": ["E%02d" % i for i in range(1, 12)]})
        self.assertEqual(len(ex["T05"]), 255)
        self.assertEqual({t: sorted(c) for t, c in checks.items()},
                         {"T02": ["clearing_days_vs_entries"],
                          "T05": ["impossible_dates", "references", "stale_authorisations"]})

    def test_status_sentence(self):
        pending = self.block("pending")
        status = pending.get("status", {})
        tasks = [t for t in self.tasks() if t["status"] != "Done"]
        self.assertEqual(int(status.get("open_tasks", -1)), OPEN_TASKS)
        self.assertEqual(int(status.get("open_tasks", -1)), len(tasks))
        # Amended by the payable-reads block (minors): T07's funding in transit is a reconciling item to confirm, not a
        # defect, so T07 is not blocked though it still lists what it waits for (blocked tasks = 8). Amended by de0b6cb
        # (minors): not-blocked is derived from what the task lacks (only reconciling, timing, items), not its id.
        self.assertEqual(int(status.get("blocked_tasks", -1)), sum(1 for t in tasks if _blocked(self.data, t)))
        self.assertEqual(int(status.get("blocked_tasks", -1)), BLOCKED_TASKS)
        self.assertEqual((int(status.get("entries", -1)), _num(status.get("entries_usd"))), (ENTRIES, ENTRIES_USD))
        self.assertEqual(int(status.get("waiting_outside", -1)), sum(WAITING_OUTSIDE.values()))
        sentence = str(pending.get("sentence", ""))
        # Amended by the repairs block (minors): the sentence splits the 253 into 122 differences and 131 data flags
        # (Repairs.test_close_status_separates_money_from_data_flags), so "253" no longer has to appear.
        for figure in (str(OPEN_TASKS), str(ENTRIES), "172,291.89"):
            self.assertIn(figure, sentence)


class DraftedMessages(_Screens):
    """Plan: drafted messages, never sent. Templates declared once in policy.py; each draft fills in the cited rows,
    names only rows of its own type, says "Draft — not sent", and has a copy button and a .txt download."""

    def drafts(self):
        drafts = self.block("pending").get("drafts", [])
        self.assertTrue(drafts, "no drafted messages")
        return drafts

    def test_templates_declared_once_in_policy(self):
        from bridge import policy
        templates = {k: v for name, value in vars(policy).items() if name.isupper()
                     and re.search(r"DRAFT|MESSAGE|TEMPLATE", name) and isinstance(value, dict) for k, v in value.items()}
        for d in self.drafts():
            self.assertIn(d.get("template"), templates, d.get("id"))
        found = []
        for path in g.glob_bridge():
            with open(path, encoding="utf-8") as f:
                if re.search(r"not sent", f.read(), re.I):
                    found.append(os.path.basename(path))
        self.assertEqual(found, ["policy.py"], "the 'not sent' wording is declared outside policy.py, or nowhere")

    def test_each_draft_names_only_its_own_rows(self):
        # Amended by the repairs block (material 6): a draft holds the rows whose type is in its template's types and
        # whose fixer matches the template's party (its declared fixer); the types come from the template, not from
        # the rows the draft happens to hold.
        from bridge import policy
        by_id = {p["row_id"]: r for r, p in self.exceptions()}
        failed = {c["name"] for c in self.table("checks") if c["passed"] == "false"}
        for d in self.drafts():
            with self.subTest(draft=d.get("id")):
                self.assertIn(d.get("to"), OUTSIDE)
                self.assertRegex(d.get("text", ""), r"Draft\s*[—-]+\s*not sent")
                tpl = policy.DRAFT_TEMPLATES[d["template"]]
                types = set(tpl.get("types", ()))
                rows = [by_id.get(i) for i in d.get("rows", [])]
                self.assertNotIn(None, rows, "a draft cites a row not on the page")
                self.assertEqual({r["type"] for r in rows} - types, set())
                self.assertEqual(sorted(d.get("rows", [])), sorted(_draft_rows(tpl, by_id)))
                self.assertEqual(set(d.get("checks", [])) - failed, set())
                for r in rows:
                    self.assertIn(r["key"], d["text"])

    def test_case_drafts(self):
        drafts = self.drafts()
        covered = {(d["to"], t) for d in drafts for t in d.get("types", [])}
        covered |= {(d["to"], c) for d in drafts for c in d.get("checks", [])}
        for want in DRAFT_TYPES + DRAFT_CHECKS:
            self.assertIn(want, covered)

    def test_copy_and_txt_download(self):
        self.assertRegex(self.script, r"navigator\.clipboard|execCommand\(\s*[\"']copy")
        self.assertRegex(self.script, r"\.txt\b")


class ReviewSixMinors(_Screens):
    """Review 6 minors taken: notes keyed by leg|type|key (#n for repeats), not by the source list; the stale "no money
    is added up in the browser" comment fixed; the balances label said once."""

    def test_exception_ids_leave_the_sources_out(self):
        seen, expected = collections.Counter(), []
        for row in self.table("exceptions"):
            key = "|".join((row["leg"], row["type"], row["key"]))
            seen[key] += 1
            expected.append(key if seen[key] == 1 else "%s#%d" % (key, seen[key]))
        self.assertEqual([p["row_id"] for p in self.data["page"]["exceptions"]["rows"]], expected)

    def test_stale_comment_gone(self):
        with open(os.path.join(g.REPO_ROOT, "bridge", "template.html"), encoding="utf-8") as f:
            self.assertNotIn("no money is added up in the browser", f.read())

    def test_balances_label_said_once(self):
        import json
        text = self.script + json.dumps(self.data["page"])
        self.assertEqual(len(re.findall(r"(?i)trial[- ]balance", text)), 1)


# --- Repairs after the five-screens review (plan block b3a73a8) ----------------------------------------------------
# Figures recomputed from the raw files by /private/tmp/claude-501/verifier54/recount.py, which never imports bridge:
# 6 processor duplicates, net 3,593.63; processor side 2,997 + 111 + 6 + 3 = 3,117 and Mastercard side
# 2,997 + 111 + 5 = 3,113; gross difference of the files 924,303.45 - 909,419.05 = 14,884.40; 121 leg-1 money
# differences (net 14,671.86) plus the duplicate debit = 122 (net 55,288.80); 105 bad references and 3 authorisations
# after clearing among the data flags; leg 1 by the processor's clearing date gives 21 September days, none in October;
# 31-Aug is the only summary day outside the detail file's settlement dates (1-Sep to 2-Oct).

DUPLICATES = (6, D("3593.63"))
LEG1_GROSS = D("14884.40")
MONEY_OUTSIDE = {"count": 122, "Processor": 121, "Mastercard": 1, "net": D("55288.80")}
DATA_FLAGS = 130   # amended by the payable-reads block: 131 less the missing processor invoice (a request)
LEG2_DUPLICATE = D("40616.94")
UNLINKED = ("1.matched_equal",)   # the declared list of Summary figures with no link
GROUPED_LINKS = {"1.processor_rows": ("1", "processor_usd"), "1.mastercard_rows": ("1", "mastercard_usd"),
                 "2.settlement_days": ("2", "mastercard_net"), "2.paired": ("2", "mastercard_net")}
ID_COLUMN = {g.PROCESSOR: "txn_id", g.MC_DETAIL: "network_ref", g.BANK: "line_id"}


def _days(iso):
    """The ways a draft may write a day: 2026-09-08, 08-Sep, 8-Sep."""
    import datetime
    day = datetime.date.fromisoformat(iso)
    return {iso, day.strftime("%d-%b"), "%d-%s" % (day.day, day.strftime("%b"))}


def _figures(case):
    return {f["id"]: f for f in case.block("overview").get("figures", [])}


class RepairsLeg1AddsUp(_Screens):
    """Material 1: the processor side shows equal + with a difference + duplicates (6, net 3,593.63, linked to
    processor_duplicate) + processor-only = 3,117; the Mastercard side adds up the same way; the note reads "Net
    difference of the exceptions: 15,600.17 (gross difference of the files: 14,884.40)"."""

    def test_duplicates_figure(self):
        f = _figures(self).get("1.processor_duplicate", {})
        self.assertEqual((int(f.get("count", -1)), _num(f.get("usd"))), DUPLICATES)
        link = f.get("link", {})
        self.assertIn(link.get("filter", {}).get("type"), ("processor_duplicate", ["processor_duplicate"]), link)
        self.assertEqual((link.get("filter", {}).get("leg"), link.get("sum")), ("1", "net"))

    def test_each_side_adds_up(self):
        count = lambda name: int(_figures(self).get("1." + name, {}).get("count", -1))  # noqa: E731
        self.assertEqual(count("processor_rows"), count("matched_equal") + count("matched_diff")
                         + count("processor_duplicate") + count("processor_only"))
        self.assertEqual(count("mastercard_rows"), count("matched_equal") + count("matched_diff")
                         + count("mastercard_only"))

    def test_note_says_net_and_gross(self):
        f = _figures(self)
        self.assertEqual(_num(f["1.processor_rows"]["usd"]) - _num(f["1.mastercard_rows"]["usd"]), LEG1_GROSS)
        self.assertIn("Net difference of the exceptions", self.script)
        self.assertIn("gross difference of the files", self.script)
        self.assertNotIn("Processor minus Mastercard", self.script)


class RepairsPendingActions(_Screens):
    """Material 3: the Status column shows only the checklist status and the tool's finding has its own column ("Tool
    finding"); T13 lacks the 11 entries awaiting approval, T08 the 2105 entries and the roll-forward (evidence from
    policy.TOOL_EVIDENCE where a task has no exception); T07 says the 400,000 funding in transit is a reconciling item
    to confirm on 1-Oct; T12 says the invoice was not received, not "net 0.00"; a Done task shows no "No tool
    evidence" sentence."""

    def tasks(self):
        return {t["task_id"]: t for t in self.block("pending").get("tasks", [])}

    def test_status_column_is_the_checklist_status(self):
        self.assertIn("Tool finding", self.script)
        self.assertNotRegex(self.script, r"\?\s*[\"']Blocked[\"']\s*:", "the tool's Blocked replaces the status")

    def test_t13_and_t08_from_tool_evidence(self):
        from bridge import policy
        tasks, wanted = self.tasks(), _tool_evidence_entries(self.table("proposed_entries"))
        self.assertEqual(len(wanted["T13"]), ENTRIES)
        for task in ("T13", "T08"):
            with self.subTest(task=task):
                self.assertIn(task, policy.TOOL_EVIDENCE)
                self.assertEqual(set(tasks[task]["lacks"].get("entries", [])), wanted[task])
                self.assertNotIn(NO_EVIDENCE, tasks[task]["text"])
        self.assertRegex(tasks["T08"]["text"], r"(?i)roll[- ]?forward")

    def test_t07_and_t12_in_words(self):
        tasks = self.tasks()
        t07, t12 = tasks["T07"]["text"], tasks["T12"]["text"]
        self.assertIn("400,000.00", t07)
        self.assertRegex(t07, r"(?i)reconciling item")
        self.assertRegex(t07, r"\b0?1-Oct\b")
        self.assertRegex(t12, r"(?i)not received")
        self.assertNotIn("net 0.00", t12)

    def test_done_tasks_say_no_no_evidence(self):
        for t in self.tasks().values():
            if t["status"] == "Done":
                self.assertNotIn(NO_EVIDENCE, t["text"], t["task_id"])


class RepairsGroupedView(_Screens):
    """Material 4: leg 2's duplicate debit sits on the settlement day it duplicates (difference 40,616.94, 1 exception);
    in leg 1 each pair sits on the processor's clearing date, so no day shows a difference with 0 exceptions; a group
    row filters to its exception row ids, never to a date range; a group with no exceptions has none to filter to."""

    def leg_ids(self, leg):
        return [p["row_id"] for r, p in self.exceptions() if r["leg"] == leg]

    def test_leg2_duplicate_on_its_day(self):
        rows = self.block("grouped").get("2", [])
        hit = [r for r in rows if _num(r["difference"]) != 0]
        self.assertEqual(len(hit), 1, "the duplicate debit is on no settlement day, or on several")
        self.assertEqual((_num(hit[0]["difference"]), int(hit[0].get("exceptions", -1))), (LEG2_DUPLICATE, 1))
        self.assertEqual(_num(hit[0]["bank_debit"]), _num(hit[0]["mastercard_net"]) + LEG2_DUPLICATE)
        self.assertEqual([int(r.get("exceptions", -1)) for r in rows if r is not hit[0]], [0] * (len(rows) - 1))

    def test_leg1_difference_has_exceptions(self):
        # Amended by 795490d: Grouped leg 1 is by type, so the 21 September clearing days are retired; a group with a
        # difference still has exceptions.
        rows = self.block("grouped").get("1", [])
        self.assertTrue(rows)
        for r in rows:
            if _num(r["difference"]) != 0:
                self.assertGreater(int(r["exceptions"]), 0, "a group with a difference and no exception: %r" % r)

    def test_group_rows_carry_their_exception_ids(self):
        # Amended by the payable-reads block (minors): the group day, not the facet date, for a weekend stale flag.
        kind = {p["row_id"]: r["type"] for r, p in self.exceptions()}
        for leg in ("1", "2"):
            with self.subTest(leg=leg):
                rows, mine = self.block("grouped").get(leg, []), self.leg_ids(leg)
                ids = [i for r in rows for i in r.get("ids", [])]
                self.assertEqual(sorted(ids), sorted(mine), "each exception of the leg in exactly one group")
                for r in rows:
                    self.assertEqual(len(r.get("ids", [])), int(r.get("exceptions", -1)), r.get("date") or r.get("type"))
                    if leg == "1":   # amended by 795490d: a leg-1 group holds its type's exceptions, not a day's
                        self.assertEqual({kind[i] for i in r["ids"]} - {r.get("type")}, set(), r.get("type"))

    def test_group_click_filters_to_ids_not_dates(self):
        self.assertNotRegex(self.script, r"from:\s*r\.date", "a group row still filters to a date range")
        self.assertRegex(self.script, r"\bids\s*:\s*\w+\.ids\b")


class RepairsSummaryMinors(_Screens):
    """Minors taken: every Summary figure links unless it is on the declared list ("matched with no difference" only)
    or its count is 0; processor and Mastercard rows link to Grouped leg 1, the leg-2 figures to Grouped leg 2; the
    close-status sentence separates money from data flags; CHECK_TASK removed; FIGURE_LIST and the empty summaries
    removed; "Draft — not sent" read from the data."""

    def test_every_figure_links_unless_declared(self):
        # Amended by the payable block (297c8bf): the 2105 "as the settlements imply it" figure, which this test
        # required to link, is removed; the bridge figures' links are pinned in PayableBridge.
        for f in _figures(self).values():
            with self.subTest(figure=f["id"]):
                if f["id"] in UNLINKED or f.get("count") == "0":
                    self.assertNotIn("link", f, "a zero-count or declared figure is clickable")
                else:
                    self.assertIn("link", f, "a Summary figure with no link")

    def test_grouped_links(self):
        figures = _figures(self)
        for name, (leg, column) in GROUPED_LINKS.items():
            with self.subTest(figure=name):
                link = figures[name].get("link", {})
                self.assertEqual((link.get("screen"), link.get("grouped"), link.get("sum")),
                                 ("Reconciliation", leg, column))

    def test_close_status_separates_money_from_data_flags(self):
        outside = [r for r in self.table("exceptions") if r["who_fixes"] in OUTSIDE]
        money = [r for r in outside if r["cls"] != "data_issue"]
        # Amended by the payable-reads block (minors): the missing processor invoice is a request, not a data flag, so
        # the flags are 130 and the sentence names the invoice apart.
        flags = [r for r in outside if r["cls"] == "data_issue" and r["type"] != "input_missing"]
        missing = [r for r in outside if r["type"] == "input_missing"]
        self.assertEqual([(r["who_fixes"], r["key"]) for r in missing], [("Processor", "processor invoice")])
        self.assertEqual(len(money), MONEY_OUTSIDE["count"])
        for who in OUTSIDE:
            self.assertEqual(sum(1 for r in money if r["who_fixes"] == who), MONEY_OUTSIDE[who], who)
        self.assertEqual(sum((D(r["net"]) for r in money), D("0")), MONEY_OUTSIDE["net"])
        self.assertEqual((len(flags), {r["who_fixes"] for r in flags}), (DATA_FLAGS, {"Processor"}))
        sentence = self.block("pending").get("sentence", "")
        self.assertIn("%d differences" % MONEY_OUTSIDE["count"], sentence)
        usd = {format(MONEY_OUTSIDE["net"], ",.2f"), format(sum((abs(D(r["gross"])) for r in money), D("0")), ",.2f")}
        self.assertTrue(any(u in sentence for u in usd), (usd, sentence))
        self.assertIn("%d from the processor" % MONEY_OUTSIDE["Processor"], sentence)
        self.assertIn("%d from Mastercard" % MONEY_OUTSIDE["Mastercard"], sentence)
        self.assertIn("%d data flags go back to the processor" % DATA_FLAGS, sentence)
        self.assertIn("the processor invoice was not received", sentence)
        self.assertNotIn("their sender", sentence)

    def test_check_task_removed(self):
        from bridge import policy
        self.assertFalse(hasattr(policy, "CHECK_TASK"))
        for path in g.glob_bridge():
            with open(path, encoding="utf-8") as f:
                self.assertNotIn("CHECK_TASK", f.read(), os.path.basename(path))

    def test_workarounds_removed(self):
        self.assertNotIn("FIGURE_LIST", self.script)
        for name in ("overview", "pending", "grouped"):
            self.assertNotIn("summary", self.block(name), name)

    def test_draft_notice_read_from_the_data(self):
        with open(os.path.join(g.REPO_ROOT, "bridge", "template.html"), encoding="utf-8") as f:
            self.assertNotRegex(f.read(), r"(?i)not sent")


class RepairsDraftLines(_Screens):
    """Material 6: drafts show gross amounts, dates and the other side's reference; D03 names the original debit
    BS0016. Each draft row's line carries its key, its gross amount (unsigned), its day and the reference of every row
    it cites from the other side's file."""

    def test_each_line(self):
        index = _input_index(self.r)
        rows = {p["row_id"]: (r, p, f) for (r, p), f in zip(self.exceptions(), self.data["facets"])}
        for d in self.block("pending").get("drafts", []):
            wrong = []
            for row_id in d.get("rows", []):
                r, p, facet = rows[row_id]
                lines = [x for x in d["text"].splitlines() if r["key"] in x]
                if len(lines) != 1:
                    wrong.append((r["key"], "the row's key on %d lines" % len(lines)))
                    continue
                cited = [(ref.split(":", 1)[0], str(index[ref][ID_COLUMN[ref.split(":", 1)[0]]]))
                         for ref in (s["ref"] for s in p.get("sources") or []) if ref.split(":", 1)[0] in ID_COLUMN]
                own = {f for f, ref in cited if ref == r["key"]}
                missing = [m for m in [format(abs(D(r["gross"])), ",.2f")] + [ref for f, ref in cited if f not in own]
                           if m not in lines[0]]
                if not _days(facet["date"]) & set(re.findall(r"[\w-]+", lines[0])):
                    missing.append(facet["date"])
                if missing:
                    wrong.append((lines[0], "lacks", missing))
            with self.subTest(draft=d["id"]):
                self.assertEqual(wrong[:3], [])

    def test_d03_names_the_original_debit(self):
        found = [d for d in self.block("pending").get("drafts", []) if "bank_duplicate_debit" in d.get("types", [])]
        self.assertEqual(len(found), 1)
        self.assertIn("BS0016", found[0]["text"])


class _PlantedPage(unittest.TestCase):
    """Runs run.py on a temp copy of the data after `plant(data_dir)`; the page blob is in `cls.data`."""

    @classmethod
    def setUpClass(cls):
        import shutil
        import tempfile
        tmp = tempfile.TemporaryDirectory(prefix="bridge-planted-")
        cls.addClassCleanup(tmp.cleanup)
        data_dir = os.path.join(tmp.name, "datos")
        shutil.copytree(DATA_DIR, data_dir)
        cls.plant(data_dir)
        cls.data_dir = data_dir
        cls.data = g._page_data(g._run_on(data_dir))

    def exceptions(self):
        return {p["row_id"]: r for r, p in zip(self.data["tables"]["exceptions"]["rows"],
                                               self.data["page"]["exceptions"]["rows"])}


class RepairsPlantedConversionErrors(_PlantedPage):
    """Material 6, planted (review 53's plant2): a Mastercard-owned conversion error (MC2827341940727 +1,200) and a
    processor-owned one (PX10000700 +1,200). Each goes in the draft of its fixer: the processor's in the processor's
    amount-and-rate draft, Mastercard's in Mastercard's conversion draft; every draft holds exactly its own rows."""

    @classmethod
    def plant(cls, data_dir):
        g._shift_mc(data_dir, "MC2827341940727", D("1200"))
        _f, rows = g._read_rows(data_dir, g.PROCESSOR)
        row = [r for r in rows if r["txn_id"] == "PX10000700"][0]
        g._edit(data_dir, g.PROCESSOR, "txn_id", "PX10000700", amount_usd=D(row["amount_usd"]) + D("1200"))

    def test_each_conversion_error_in_its_fixer_draft(self):
        conv = {i: r for i, r in self.exceptions().items() if r["type"] == "usd_conversion_error"}
        self.assertEqual(sorted(r["who_fixes"] for r in conv.values()), sorted(OUTSIDE), "the plant did not take")
        drafts = self.data["page"]["pending"]["drafts"]
        for i, r in conv.items():
            with self.subTest(fixer=r["who_fixes"]):
                holding = [d for d in drafts if i in d["rows"]]
                self.assertEqual([d["to"] for d in holding], [r["who_fixes"]])
                if r["who_fixes"] == "Processor":
                    self.assertEqual(holding[0]["template"], "processor_amount_and_rate")

    def test_each_draft_holds_exactly_its_rows(self):
        from bridge import policy
        by_id = self.exceptions()
        for d in self.data["page"]["pending"]["drafts"]:
            with self.subTest(draft=d["id"]):
                self.assertEqual(sorted(d["rows"]), sorted(_draft_rows(policy.DRAFT_TEMPLATES[d["template"]], by_id)))


class RepairsSummaryCheckCase(_Screens):
    """Material 7, case data: the summary-vs-detail check skips 31-Aug (outside the detail file's settlement dates)
    and lists it as a coverage note; no draft remains."""

    def test_coverage_note_and_no_draft(self):
        check = [c for c in self.table("checks") if c["name"] == "summary_vs_detail"][0]
        self.assertEqual(check["passed"], "true")
        self.assertTrue(_days("2026-08-31") & set(re.findall(r"[\w-]+", check["detail"])), check["detail"])
        self.assertEqual([d["id"] for d in self.block("pending")["drafts"] if "summary_vs_detail" in d["checks"]], [])


class RepairsPlantedSummaryMismatch(_PlantedPage):
    """Material 7, planted: the 15-Sep summary net moved by +100.00, a day inside the detail file. The check fails on
    that day only, and its draft to Mastercard names the day with both counts and both nets — not 31-Aug."""

    DAY = "2026-09-15"

    @classmethod
    def plant(cls, data_dir):
        g._shift_summary(data_dir, cls.DAY, D("100.00"))

    def test_draft_names_the_day_with_both_sides(self):
        _f, summary = g._read_rows(self.data_dir, g.MC_SUMMARY)
        _f, detail = g._read_rows(self.data_dir, g.MC_DETAIL)
        s = [r for r in summary if r["settlement_date"] == self.DAY][0]
        mine = [r for r in detail if r["settlement_date"] == self.DAY]
        figures = [str(int(s["txn_count"])), str(len(mine)), format(D(s["net_settlement_usd"]), ",.2f"),
                   format(sum((D(r["net_settlement_usd"]) for r in mine), D("0")), ",.2f")]
        found = [d for d in self.data["page"]["pending"]["drafts"] if "summary_vs_detail" in d["checks"]]
        self.assertEqual([d["to"] for d in found], ["Mastercard"])
        text = found[0]["text"]
        self.assertTrue(_days(self.DAY) & set(re.findall(r"[\w-]+", text)), text)
        for figure in figures:
            self.assertIn(figure, text)
        self.assertFalse(_days("2026-08-31") & set(re.findall(r"[\w-]+", text)), "the draft names 31-Aug")


# --- The Mastercard payable reconciled against Mastercard (plan block 297c8bf, 01788a5) -----------------------------
# Figures recomputed from the raw files by /private/tmp/claude-501/verifier56/recount.py, which never imports bridge:
# the only settlement day up to 30-Sep with no bank debit of its net by 30-Sep is 30-Sep (44,643.99, summary line 23,
# debited 1-Oct as BS0031); the September transactions Mastercard cleared in October are the four month cut-off rows
# (clearing_detail lines 3147, 3177, 3297, 3362; net 928.31) -> owed 45,572.30. balances.csv 2105: before 70,588.66,
# after_confirmed -54,700.22, after_all -45,572.30 -> difference 9,127.92 confirmed only, 0.00 with all entries.
# Replaces the "as the settlements imply it" figure, whose link RepairsSummaryMinors required: that figure is gone
# (PayableBridge.test_implied_figure_removed) and the bridge figures' links are pinned here instead.

OWED_PARTS = (D("44643.99"), D("928.31"))
OWED = D("45572.30")
PERIOD_END = "2026-09-30"


def _owed_rows(data_dir):
    """[(ref, amount)] Mastercard says Clara owes at 30-Sep: the summary nets of settlement days up to 30-Sep that no
    bank debit of the same amount, posted on or after the day and by 30-Sep, paid; plus the Mastercard rows cleared in
    October whose processor row cleared in September (the month cut-off rows), at their net."""
    _f, summary = g._read_rows(data_dir, g.MC_SUMMARY)
    _f, detail = g._read_rows(data_dir, g.MC_DETAIL)
    _f, bank = g._read_rows(data_dir, g.BANK)
    _f, processor = g._read_rows(data_dir, g.PROCESSOR)
    debits = [(b["posting_date"], D(b["debit_usd"])) for b in bank if b["debit_usd"]]
    out = [("%s:%d" % (g.MC_SUMMARY, i + 2), D(s["net_settlement_usd"])) for i, s in enumerate(summary)
           if s["settlement_date"] <= PERIOD_END
           and not any(a == D(s["net_settlement_usd"]) and s["settlement_date"] <= day <= PERIOD_END
                       for day, a in debits)]
    cleared = {p["network_ref"]: p["clearing_date"] for p in processor}
    out += [("%s:%d" % (g.MC_DETAIL, i + 2), D(r["net_settlement_usd"])) for i, r in enumerate(detail)
            if r["clearing_date"] > PERIOD_END and cleared.get(r["network_ref"], "9999") <= PERIOD_END]
    return out


def _bridge(data):
    """{basis: {line: line dict}} from the Summary's payable bridge."""
    bridge = (data.get("page") or {}).get("overview", {}).get("payable_bridge")
    if not isinstance(bridge, list) or not bridge:
        raise AssertionError("the Summary carries no payable bridge")
    return {b.get("basis"): {x.get("line"): x for x in b.get("lines", [])} for b in bridge}


def _entries_on_payable(data):
    """{entry_id: its 2105 debit - credit} over the proposed-entries table."""
    out = collections.defaultdict(lambda: D("0"))
    for e in data["tables"]["proposed_entries"]["rows"]:
        if e["account"] == PAYABLE:
            out[e["entry_id"]] += _num(e["debit"]) - _num(e["credit"])
    return dict(out)


class PayableBridge(_Screens):
    """Plan: 2105 is reconciled against what Mastercard's own files say Clara owes, with the entries that need no
    evidence and with all of them; on the Summary's leg-3 block and as Grouped leg 3's 2105 row; `_payable_implied`
    and its figure removed.

    Amended by the plan block "The payable bridge reads on its own, and the last page fixes" (cd7512e): the lines are
    ledger (debit) -> entries -> ledger after the entries (credit) -> Mastercard's 30-Sep settlement -> September
    transactions Mastercard cleared in October -> difference = result - the two Mastercard lines; credits are shown as
    positive amounts with "side": "credit"; "owed" is split in two lines; every figure opens rows that sum to it."""

    def bridge(self):
        bridge = _bridge(self.data)
        self.assertEqual(sorted(bridge), ["all", "confirmed"])
        for b in self.block("overview")["payable_bridge"]:
            self.assertEqual([x.get("line") for x in b.get("lines", [])], list(BRIDGE_LINES), b.get("basis"))
        return bridge

    def balance(self):
        found = [r for r in self.table("balances") if r["account"] == PAYABLE]
        self.assertEqual(len(found), 1)
        return found[0]

    def test_owed_recomputed_from_the_raw_files(self):
        rows = _owed_rows(DATA_DIR)
        self.assertEqual([a for r, a in rows if r.startswith(g.MC_SUMMARY)], [OWED_PARTS[0]])
        self.assertEqual(sum((a for r, a in rows if r.startswith(g.MC_DETAIL)), D("0")), OWED_PARTS[1])
        self.assertEqual(sum(OWED_PARTS), OWED)
        for basis, lines in self.bridge().items():
            with self.subTest(basis=basis):
                self.assertEqual((D(lines["settlement"]["usd"]), D(lines["timing"]["usd"])), OWED_PARTS)

    def test_both_lines_from_balances(self):
        # Amended: the result is shown as a credit (positive) and the difference is the result minus the two
        # Mastercard lines — plain subtraction down the column.
        before = D(self.balance()["before"])
        self.assertEqual(before, D("70588.66"))
        for basis, lines in self.bridge().items():
            with self.subTest(basis=basis):
                after = D(self.balance()["after_%s" % basis])
                shown = {line: D(lines[line]["usd"]) for line in BRIDGE_LINES}
                self.assertEqual({k: v for k, v in shown.items() if k != "entries"}, BRIDGE_FIGURES[basis])
                self.assertEqual(_signed(lines["ledger"]), before)
                self.assertEqual(_signed(lines["result"]), after)
                self.assertEqual(_signed(lines["entries"]), BRIDGE_ENTRIES[basis])
                self.assertEqual(_signed(lines["ledger"]) + _signed(lines["entries"]), _signed(lines["result"]))
                self.assertEqual(shown["result"] - shown["settlement"] - shown["timing"], shown["difference"])

    def test_ledger_shown_as_a_debit(self):
        # Amended: and the result as a credit.
        for basis, lines in self.bridge().items():
            self.assertEqual(lines["ledger"].get("side"), "debit", basis)
            self.assertEqual(lines["result"].get("side"), "credit", basis)

    def test_all_entries_line_labelled(self):
        # Amended: the columns are "Entries with no condition (8)" and "All entries, if E10's evidence arrives (9)";
        # the counts are the entries each column posts on 2105.
        self.bridge()
        bridge = {b.get("basis"): b for b in self.block("overview")["payable_bridge"]}
        counts = {basis: len(_entry_ids(lines["entries"])) for basis, lines in self.bridge().items()}
        self.assertEqual(counts, {"confirmed": 8, "all": 9})
        self.assertRegex(str(bridge["confirmed"].get("label", "")), r"(?i)entries with no condition \(8\)")
        self.assertRegex(str(bridge["all"].get("label", "")), r"(?i)all entries, if E10.s evidence arrives \(9\)")
        self.assertNotRegex(json.dumps(bridge), r"(?i)\bconfirmed entries\b|proposed entries are approved")

    def test_title_and_line_labels(self):
        page = self.script + json.dumps(self.data["page"])
        self.assertIn(BRIDGE_TITLE, page)
        for basis, lines in self.bridge().items():
            for line, pattern in BRIDGE_LABELS.items():
                with self.subTest(basis=basis, line=line):
                    self.assertRegex(str(lines[line].get("label", "")), pattern)
        self.assertRegex(page, r"(?i)the wrong side", "the ledger's debit is not said to be the wrong side")

    def test_e10_line_under_the_first_column(self):
        bridge = {b.get("basis"): b for b in self.block("overview")["payable_bridge"]}
        note = re.compile(r"9,127\.92 = E10: 3 processor-only rows; its entry waits for evidence")
        self.assertRegex(json.dumps(bridge["confirmed"], ensure_ascii=False), note)
        self.assertNotRegex(json.dumps(bridge["all"], ensure_ascii=False), note)
        self.assertEqual(MATCHES["1"]["processor_only"], (3, BRIDGE_FIGURES["confirmed"]["difference"]))

    def test_every_bridge_figure_opens_rows_that_sum_to_it(self):
        # Replaces test_every_bridge_figure_links (material 1): a link's shape was checked, not that its rows add up.
        # A figure opens either a link (the rows it filters, summed as the page sums them; where the rows carry source
        # amounts, those add up to the same total — the page's tie) or its own "sources" (ref and amount).
        owed = sorted(_owed_rows(DATA_DIR))
        for basis, lines in self.bridge().items():
            for name in BRIDGE_LINES:
                line = lines[name]
                with self.subTest(basis=basis, line=name):
                    if name == "difference" and D(line["usd"]) == 0 and not line.get("link"):
                        continue   # nothing left over: no rows to open
                    self.assertTrue(line.get("link") or line.get("sources"), "a bridge figure that opens nothing")
                    if line.get("link"):
                        self.assertEqual(_opened(self, line["link"])[0], _signed(line))
                    else:
                        self.assertEqual(sum((_num(s.get("amount")) for s in line["sources"]), D("0")), D(line["usd"]))
            got = sorted((s.get("ref"), _num(s.get("amount"))) for name in ("settlement", "timing")
                         for s in lines[name].get("sources") or [])
            if got:
                self.assertEqual(got, owed, basis)

    def test_result_opens_the_ledger_rows_plus_the_entries(self):
        # Material 1: the result opens the ledger's rows plus the 2105 lines of the entries, so they sum to it.
        for basis, lines in self.bridge().items():
            with self.subTest(basis=basis):
                total, opened = _opened(self, lines["result"].get("link") or {})
                tables = {t for t, _r in opened}
                self.assertEqual(tables, {"balances", "proposed_entries"})
                self.assertEqual({r["account"] for _t, r in opened}, {PAYABLE})
                self.assertEqual({r["entry_id"] for t, r in opened if t == "proposed_entries"},
                                 _entry_ids(lines["entries"]))
                self.assertEqual(total, D(self.balance()["after_%s" % basis]))

    def test_entries_and_difference_open_the_2105_lines(self):
        # Material 2: the proposed-entries table filtered to the entries' 2105 lines, with a net (debit - credit) sum.
        on_payable = _entries_on_payable(self.data)
        status = {e["entry_id"]: e["status"] for e in self.table("proposed_entries")}
        unconditional = {i for i in on_payable if status[i] == "proposed"}
        self.assertEqual(sorted(set(on_payable) - unconditional), ["E10"])
        wanted = {("confirmed", "entries"): unconditional, ("all", "entries"): set(on_payable),
                  ("confirmed", "difference"): set(on_payable) - unconditional}
        bridge = self.bridge()
        for (basis, name), ids in wanted.items():
            with self.subTest(basis=basis, line=name):
                link = bridge[basis][name].get("link") or {}
                self.assertIsInstance(link, dict, "one table, not several")
                self.assertEqual((link.get("table"), link.get("filter", {}).get("account")),
                                 ("proposed_entries", PAYABLE))
                self.assertEqual(link.get("sum"), NET_SUM)
                total, opened = _opened(self, link)
                self.assertEqual(sorted((r["entry_id"], r["account"]) for _t, r in opened),
                                 sorted((i, PAYABLE) for i in ids))
                self.assertEqual(total, sum((on_payable[i] for i in ids), D("0")))
        self.assertEqual(sum((on_payable[i] for i in wanted[("confirmed", "difference")]), D("0")),
                         BRIDGE_FIGURES["confirmed"]["difference"])

    # test_source_rows_not_repeated_across_one_entrys_lines is withdrawn by de0b6cb (material 1): it pushed the code to
    # cite opening-balance rows as evidence on 26 entry lines. HonestEntryEvidence replaces it.

    def test_grouped_2105_row_is_the_bridge(self):
        self.bridge()
        rows = [r for r in self.block("grouped").get("3", []) if r.get("account") == PAYABLE]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get("bridge"), self.block("overview")["payable_bridge"])
        self.assertNotRegex(str(rows[0].get("record_label", "")), r"(?i)settlements imply")

    def test_implied_figure_removed(self):
        self.assertFalse("3.settlements_imply" in _figures(self), "the 'as the settlements imply it' figure remains")
        self.assertNotRegex(self.script + json.dumps(self.data["page"]), r"(?i)settlements imply")
        for path in g.glob_bridge():
            with open(path, encoding="utf-8") as f:
                self.assertNotIn("payable_implied", f.read(), os.path.basename(path))


class PayableBridgePlanted(_PlantedPage):
    """Plan: a planted +100.00 on the 30-Sep settlement net moves the settlement line and the difference by 100.00, on
    both columns. Amended by cd7512e: "owed" is now the settlement line plus the timing line."""

    DAY, DELTA = "2026-09-30", D("100.00")

    @classmethod
    def plant(cls, data_dir):
        g._shift_summary(data_dir, cls.DAY, cls.DELTA)

    def test_owed_and_difference_move(self):
        owed = sorted(_owed_rows(self.data_dir))
        self.assertEqual(sum((a for _r, a in owed), D("0")), OWED + self.DELTA, "the plant did not take")
        bridge = _bridge(self.data)
        for basis in ("confirmed", "all"):
            with self.subTest(basis=basis):
                lines = bridge[basis]
                self.assertEqual(D(lines["settlement"]["usd"]), OWED_PARTS[0] + self.DELTA)
                self.assertEqual(D(lines["timing"]["usd"]), OWED_PARTS[1])
                self.assertEqual(D(lines["difference"]["usd"]),
                                 BRIDGE_FIGURES[basis]["difference"] - self.DELTA)
                got = sorted((s.get("ref"), _num(s.get("amount"))) for name in ("settlement", "timing")
                             for s in lines[name].get("sources") or [])
                if got:
                    self.assertEqual(got, owed)


# --- The payable bridge reads on its own, and the last page fixes (plan block cd7512e) ------------------------------
# Figures recomputed from the raw files by /private/tmp/claude-501/verifier59/recount.py, which never imports bridge:
# 2105 ledger 70,588.66; 30-Sep settlement 44,643.99 + four cut-off rows 928.31 = 45,572.30; entries on 2105 with all
# entries -(70,588.66 + 45,572.30) = -116,160.96 (ledger after, credit 45,572.30), without E10 -125,288.88 (credit
# 54,700.22, difference 9,127.92 = E10 = the 3 processor-only rows); the 24-Sep summary net is 44,884.41 (BS0024 is
# its debit); the five weekend stale authorisations' auth dates are PX20000019/20 Sun 06-Sep, PX20000016 Sat 12-Sep,
# PX20000011 Sat 26-Sep, PX20000023 Sun 27-Sep (7-Sep is a holiday, so 06-Sep groups on 08-Sep); account names from
# gl_opening_balances.csv. The leg-1 gross difference 14,884.40 and the 130 data flags come from verifier54.

BRIDGE_LINES = ("ledger", "entries", "result", "settlement", "timing", "difference")
BRIDGE_FIGURES = {
    "confirmed": {"ledger": D("70588.66"), "result": D("54700.22"), "settlement": D("44643.99"),
                  "timing": D("928.31"), "difference": D("9127.92")},
    "all": {"ledger": D("70588.66"), "result": D("45572.30"), "settlement": D("44643.99"), "timing": D("928.31"),
            "difference": D("0.00")}}
BRIDGE_ENTRIES = {"confirmed": D("-125288.88"), "all": D("-116160.96")}   # debit-positive, as balances.csv
BRIDGE_TITLE = "Mastercard payable 2105 against Mastercard's own files"
BRIDGE_LABELS = {"ledger": r"(?i)^ledger at 30-Sep\b", "entries": r"(?i)^proposed entries on 2105\b",
                 "result": r"(?i)^ledger after the entries\b",
                 # Amended by de0b6cb (material 4): the label names the unpaid days.
                 "settlement": r"(?i)^Mastercard settlements not debited by 30-Sep \(30-Sep\)",
                 "timing": r"(?i)^September transactions Mastercard cleared in October \(timing\)",
                 "difference": r"(?i)^difference\b"}
NET_SUM = ["debit", "credit"]   # a link's "sum" as [added column, subtracted column]: the net debit - credit
BLOCKED_TASKS = 8
T08_NET = "116,160.96"
T08_GROSS = "151,379.59"
WEEKEND_STALE = {"PX20000019": ("2026-09-06", "2026-09-08"), "PX20000020": ("2026-09-06", "2026-09-08"),
                 "PX20000016": ("2026-09-12", "2026-09-14"), "PX20000011": ("2026-09-26", "2026-09-28"),
                 "PX20000023": ("2026-09-27", "2026-09-28")}   # key: (real auth date, the working day it groups on)
NOT_DEBITED = ("BS0024", "2026-09-24", D("44884.41"))
LEG3_ITEMS = {"1110": D("400000.00"), PAYABLE: D("116160.96")}


def _signed(line):
    """A bridge figure debit-positive, as balances.csv: a line marked "side": "credit" is shown positive."""
    return -D(line["usd"]) if line.get("side") == "credit" else D(line["usd"])


def _entry_ids(line):
    link = line.get("link") or {}
    ids = (link if isinstance(link, dict) else {}).get("filter", {}).get("entry_id", [])
    return set(ids if isinstance(ids, list) else [ids])


def _opened(case, link):
    """(total, [(table, row)]) of what a Close link opens, as the page shows it: a link, or a list of links whose rows
    are shown together; each filters its table's rows and sums its "sum" — a column, or NET_SUM's [added,
    subtracted]. Where the opened rows carry source amounts, they add up to that link's total (the page's tie)."""
    total, opened = D("0"), []
    for part in link if isinstance(link, list) else [link]:
        case.assertEqual(part.get("screen"), "Close", part)
        case.assertIn(part.get("table"), sorted(case.data["tables"]), part)
        rows = list(zip(case.data["tables"][part["table"]]["rows"], case.data["page"][part["table"]]["rows"]))
        for column, value in part.get("filter", {}).items():
            wanted = value if isinstance(value, list) else [value]
            rows = [(r, p) for r, p in rows if r.get(column) in wanted]
        spec = part.get("sum")
        case.assertTrue(spec, "a link that sums nothing: %r" % part)
        net = (lambda r: _num(r[spec[0]]) - _num(r[spec[1]])) if isinstance(spec, list) else (lambda r: _num(r[spec]))
        mine = sum((net(r) for r, _p in rows), D("0"))
        amounts = [_num(s["amount"]) for _r, p in rows for s in p.get("sources") or [] if "amount" in s]
        if amounts:
            case.assertEqual(sum(amounts, D("0")), mine, "the page would show a tie error for %r" % part)
        total += mine
        opened += [(part["table"], r) for r, _p in rows]
    return total, opened


class GroupedLeg2NeverPaysAnUndebitedDay(_PlantedPage):
    """Material 4, planted (review 58's plant3): BS0024, the 24-Sep settlement debit, deleted. The Summary counts one day
    with no bank debit; Grouped leg 2's 24-Sep row shows bank 0.00 and a difference of 44,884.41 with its exception —
    the bank column adds an exception's amount only for a debit on no summary day and for a duplicate."""

    @classmethod
    def plant(cls, data_dir):
        fields, rows = g._read_rows(data_dir, g.BANK)
        g._write_rows(data_dir, g.BANK, fields, [r for r in rows if r["line_id"] != NOT_DEBITED[0]])

    def test_undebited_day_shows_no_bank_debit(self):
        unpaid = {f["id"]: f for f in self.data["page"]["overview"]["figures"]}.get("2.unpaired", {})
        self.assertEqual((int(unpaid.get("count", -1)), _num(unpaid.get("usd"))), (1, NOT_DEBITED[2]),
                         "the plant did not take")
        day = [r for r in self.data["page"]["grouped"]["2"] if r["date"] == NOT_DEBITED[1]]
        self.assertEqual(len(day), 1)
        row = day[0]
        self.assertEqual((_num(row["mastercard_net"]), _num(row["bank_debit"])), (NOT_DEBITED[2], D("0.00")))
        self.assertEqual(_num(row["difference"]), _num(row["bank_debit"]) - _num(row["mastercard_net"]))
        self.assertEqual(abs(_num(row["difference"])), NOT_DEBITED[2])
        self.assertEqual(int(row["exceptions"]), 1)


class GroupedLeg3ReconcilesBothRows(_Screens):
    """Material 5: Grouped leg 3 has the columns ledger, compared with, difference, reconciling items, unreconciled;
    both rows reconcile the same way (difference - reconciling items = unreconciled = 0.00, with all entries on 2105);
    the 2105 items say they include E10; the rows carry account names, not code-like names."""

    def rows(self):
        rows = {r.get("account"): r for r in self.block("grouped").get("3", [])}
        self.assertEqual(sorted(rows), sorted(LEG3_ITEMS))
        return rows

    def test_both_rows_unreconciled_zero(self):
        for account, row in self.rows().items():
            with self.subTest(account=account):
                self.assertIn("unreconciled", row)
                difference, items = _num(row["difference"]), _num(row["reconciling_items"])
                self.assertEqual(_num(row["ledger"]) - _num(row["record"]), difference)
                self.assertEqual(difference - items, _num(row["unreconciled"]))
                self.assertEqual(_num(row["unreconciled"]), D("0.00"))
                self.assertEqual(abs(items), LEG3_ITEMS[account])
        self.assertRegex(self.script, r"[\"']unreconciled[\"']\s*,\s*[\"']Unreconciled")

    def test_2105_items_include_e10(self):
        row = {k: v for k, v in self.rows()[PAYABLE].items() if k != "bridge"}
        self.assertIn("E10", json.dumps(row))

    def test_account_names(self):
        _f, opening = g._read_rows(DATA_DIR, GL_OPENING)
        names = {r["account"]: r["account_name"] for r in opening}
        for account, row in self.rows().items():
            self.assertEqual(row.get("name"), names[account], account)


class WeekendStaleAuthorisations(_Screens):
    """Minors: a weekend stale authorisation keeps its real date in the data (the Detailed view's Date column); only
    the grouping maps it to the next working day, so Grouped leg 1 still has 21 September days."""

    def test_real_date_in_the_data(self):
        _f, processor = g._read_rows(DATA_DIR, g.PROCESSOR)
        auth = {p["txn_id"]: p["auth_date"] for p in processor}
        stale = {r["key"]: f["date"] for (r, _p), f in zip(self.exceptions(), self.data["facets"])
                 if r["type"] == "auth_stale"}
        self.assertEqual(len(stale), 22)
        self.assertEqual({k: d for k, d in stale.items() if d != auth[k]}, {})
        self.assertEqual({k: stale[k] for k in WEEKEND_STALE}, {k: v[0] for k, v in WEEKEND_STALE.items()})

    def test_grouped_with_their_type(self):
        # Amended by 795490d: Grouped leg 1 is by type, so a weekend stale authorisation sits in the auth_stale row
        # (was: on the next working day).
        rows = self.block("grouped").get("1", [])
        type_of = {i: r.get("type") for r in rows for i in r.get("ids", [])}
        for key in WEEKEND_STALE:
            self.assertEqual(type_of.get("1|auth_stale|%s" % key), "auth_stale", key)


class LastPageMinors(_Screens):
    """Minors: T08 shows the 2105 net of its entries (116,160.96), not their total debits; T07 is not blocked (blocked
    tasks = 8); the hidden 2105 ledger Summary figure is gone from the data; the leg-1 gross difference (14,884.40) is
    in the overview data, not computed by the page script."""

    def test_t08_shows_the_2105_net(self):
        t08 = {t["task_id"]: t for t in self.block("pending")["tasks"]}["T08"]["text"]
        on_payable = _entries_on_payable(self.data)
        self.assertEqual(format(abs(sum(on_payable.values(), D("0"))), ",.2f"), T08_NET)
        self.assertIn(T08_NET, t08)
        self.assertNotIn(T08_GROSS, t08)

    def test_t07_not_blocked(self):
        pending = self.block("pending")
        self.assertEqual(int(pending["status"]["blocked_tasks"]), BLOCKED_TASKS)
        self.assertRegex(pending["sentence"], r"\b%d of them are blocked\b" % BLOCKED_TASKS)

    def test_2105_ledger_figure_removed(self):
        self.assertNotIn("3.ledger_2105", _figures(self))
        self.assertNotIn("ledger_2105", self.script)

    def test_gross_difference_in_the_data(self):
        def values(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k not in ("figures", "payable_bridge"):
                        yield from values(v)
            elif isinstance(node, list):
                for v in node:
                    yield from values(v)
            elif isinstance(node, str) and re.fullmatch(r"-?\d+\.\d{2}", node):
                yield D(node)
        self.assertIn(LEG1_GROSS, list(values(self.block("overview"))), "the overview carries no gross difference")
        self.assertNotRegex(self.script, r"processor_rows[\"']\)\s*-", "the page script still computes it")


# --- Honest evidence on every entry line, and the closing fixes (plan block de0b6cb) --------------------------------
# Figures recomputed by /private/tmp/claude-501/verifier62/ scripts, which never import bridge: cd9981d run on the case
# data gives proposed_entries.csv sha256 315ec8d5... (41 lines, no gl_opening_balances.csv citation); on the BS0024
# plant Mastercard owes 44,884.41 (24-Sep) + 44,643.99 (30-Sep) + 928.31, so the first column's difference is
# 54,700.22 - 90,456.71 = -35,756.49, of which 9,127.92 is E10 and -44,884.41 is not explained.

ENTRIES_CD9981D_SHA256 = "315ec8d5b4625c84f4a760da3165591c4eef7931fe6c3d6017fe9ccd0adc2a60"
SAME_EVIDENCE = " rows as "   # amended by Freeze fixes: "E01, line 2 (5100): the same 151 rows as line 1" replaces the per-row marker
TIMING = "timing"   # the class of a reconciling item to confirm


def _blocked(data, task):
    """A task is blocked when it lacks something other than a reconciling (timing) item: an entry, a failed check, or
    an exception of another class (de0b6cb, minors: derived from what it lacks, not from its id)."""
    cls = {p["row_id"]: r["cls"] for r, p in zip(data["tables"]["exceptions"]["rows"],
                                                   data["page"]["exceptions"]["rows"])}
    lacks = task.get("lacks", {})
    return bool(lacks.get("entries") or lacks.get("checks")
                or any(cls[i] != TIMING for i in lacks.get("exceptions", [])))


class HonestEntryEvidence(_Screens):
    """Material 1: each entry line's `src` is back to the cd9981d rule, so proposed_entries.csv is byte-identical to
    cd9981d's; no line cites gl_opening_balances.csv unless its entry is built from it. Where several lines of one entry
    open together, the page lists each source row once per entry and says "same evidence as the line above"; the data
    is not changed for display. Replaces test_source_rows_not_repeated_across_one_entrys_lines."""

    def test_proposed_entries_file_is_cd9981ds(self):
        import hashlib
        with open(os.path.join(self.out_dir, "proposed_entries.csv"), "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(), ENTRIES_CD9981D_SHA256)

    def test_no_opening_balance_citation_on_an_entry_line(self):
        built = {e.id for e in self.r.close.entries if any(GL_OPENING in str(s) for s in e.srcs)}
        _f, rows = g._read_rows(self.out_dir, "proposed_entries.csv")
        page = self.data["page"]["proposed_entries"]["rows"]
        citing = sorted({r["entry_id"] for r in rows if GL_OPENING in r["src"]}
                        | {r["entry_id"] for r, p in zip(self.table("proposed_entries"), page)
                           if any(GL_OPENING in s.get("ref", "") for s in p.get("sources") or [])})
        self.assertEqual([e for e in citing if e not in built], [])

    def test_page_sources_are_the_lines_own_src(self):
        for row, p in zip(self.table("proposed_entries"), self.data["page"]["proposed_entries"]["rows"]):
            with self.subTest(entry=row["entry_id"], account=row["account"]):
                self.assertEqual([s["ref"] for s in p.get("sources") or []], _parts(row["src"]))

    def test_repeated_evidence_said_once_per_entry(self):
        self.assertTrue(SAME_EVIDENCE in self.script + json.dumps(self.data["page"]), "no %r on the page" % SAME_EVIDENCE)


class _MissingInputsPage(unittest.TestCase):
    """Material 2: a missing input never crashes the run; account names fall back to the declared names, and the page
    is written."""

    DELETED = ()

    def test_page_written(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory(prefix="bridge-missing-") as tmp:
            data_dir = os.path.join(tmp, "datos")
            shutil.copytree(DATA_DIR, data_dir)
            for name in self.DELETED:
                os.remove(os.path.join(data_dir, name))
            data = g._page_data(g._run_on(data_dir))
        rows = {r.get("account"): r for r in data["page"]["grouped"]["3"]}
        self.assertEqual(sorted(rows), sorted(LEG3_ITEMS))
        for account, row in rows.items():
            self.assertTrue(str(row.get("name", "")).strip(), account)


class OpeningBalancesMissingPage(_MissingInputsPage):
    DELETED = (GL_OPENING,)


class DeletedInputsPage(_MissingInputsPage):
    """The deleted-inputs plant of test_golden.OwnersOfMissingInputs, run through to the page."""
    DELETED = g.OwnersOfMissingInputs.DELETED


class BridgeWordsComputed(_PlantedPage):
    """Material 4, on the BS0024-deleted plant (review 58's plant3): the E10 sentence appears only when the first
    column's difference equals the conditional entries' 2105 net; otherwise "of which X is E10; Y not explained". The
    settlement label names the unpaid days, 24-Sep among them. The 2105 difference is read from one place: Grouped leg
    3's 2105 figures equal the bridge's."""

    @classmethod
    def plant(cls, data_dir):
        GroupedLeg2NeverPaysAnUndebitedDay.plant(data_dir)

    def test_plant_took(self):
        owed = _owed_rows(self.data_dir)
        self.assertIn(NOT_DEBITED[2], [a for r, a in owed if r.startswith(g.MC_SUMMARY)])

    def test_no_false_e10_identity(self):
        bridge = _bridge(self.data)
        confirmed = {b["basis"]: b for b in self.data["page"]["overview"]["payable_bridge"]}["confirmed"]
        gap = D(bridge["confirmed"]["difference"]["usd"])
        e10 = _entries_on_payable(self.data)["E10"]
        # E10 debits 2105, so on the case data the confirmed gap equals +E10; the plant leaves gap - E10 unexplained.
        self.assertNotEqual(gap, e10, "the plant did not take")
        note = str(confirmed.get("note", ""))
        self.assertNotRegex(note, r"= E10\b")
        self.assertIn("of which %s is E10" % format(e10, ",.2f"), note)
        self.assertRegex(note, r"[-−]?%s not explained" % re.escape(format(abs(gap - e10), ",.2f")))

    def test_settlement_label_names_24_sep(self):
        for basis, lines in _bridge(self.data).items():
            with self.subTest(basis=basis):
                self.assertRegex(str(lines["settlement"].get("label", "")),
                                 r"(?i)^Mastercard settlements not debited by 30-Sep \(.*\b24-Sep\b.*\)")
                self.assertRegex(str(lines["settlement"].get("label", "")), r"\(.*\b30-Sep\b.*\)")

    def test_grouped_2105_figures_are_the_bridges(self):
        _check_grouped_2105_is_the_bridge(self, self.data)


def _check_grouped_2105_is_the_bridge(case, data):
    """Grouped leg 3's 2105 row and the bridge give the same figures (debit-positive): ledger, Mastercard's record (the
    two Mastercard lines), the reconciling items (all entries on 2105) and the unreconciled rest (the "all" column's
    difference)."""
    row = [r for r in data["page"]["grouped"]["3"] if r.get("account") == PAYABLE][0]
    every = _bridge(data)["all"]
    case.assertEqual(_num(row["ledger"]), _signed(every["ledger"]))
    case.assertEqual(_num(row["record"]), -(D(every["settlement"]["usd"]) + D(every["timing"]["usd"])))
    case.assertEqual(_num(row["reconciling_items"]), -_signed(every["entries"]))
    case.assertEqual(_num(row["unreconciled"]), -D(every["difference"]["usd"]))
    case.assertEqual(_num(row["difference"]) - _num(row["reconciling_items"]), _num(row["unreconciled"]))


class ClosingFixes(_Screens):
    """Material 4 on the case data, material 5, material 6 and the minors: the E10 sentence takes its row count from
    E10's own sources; T08's link comes from the data and sums to T08's figure; a multi-part click names each part;
    T07 reads "Waits on"; the 2105 difference is read from one place; no filter parsed back from a rendered link; no
    shared mutable default."""

    def test_e10_sentence_counts_e10s_own_rows(self):
        confirmed = {b["basis"]: b for b in self.block("overview")["payable_bridge"]}["confirmed"]
        rows = {p for r in self.table("proposed_entries") if r["entry_id"] == "E10" for p in _parts(r["src"])
                if p.startswith(g.PROCESSOR + ":")}
        self.assertRegex(str(confirmed.get("note", "")), r"= E10: %d processor-only rows" % len(rows))

    def test_t08_link_sums_to_its_figure(self):
        t08 = {t["task_id"]: t for t in self.block("pending")["tasks"]}["T08"]
        link = t08.get("link")
        self.assertTrue(link, "T08 carries no link in the data")
        self.assertEqual((link.get("table"), link.get("filter", {}).get("account"), link.get("sum")),
                         ("proposed_entries", PAYABLE, NET_SUM))
        total, opened = _opened(self, link)
        self.assertIn(format(abs(total), ",.2f"), t08["text"])
        self.assertEqual(format(abs(total), ",.2f"), T08_NET)
        bridge_total, bridge_opened = _opened(self, _bridge(self.data)["all"]["entries"]["link"])
        self.assertEqual((total, sorted((r["entry_id"], r["account"]) for _t, r in opened)),
                         (bridge_total, sorted((r["entry_id"], r["account"]) for _t, r in bridge_opened)))

    def test_multi_part_click_names_each_part(self):
        for words in ("Ledger rows add up to", "Proposed-entry lines on", "that is"):
            self.assertTrue(words in self.script + json.dumps(self.data["page"]), "no %r on the page" % words)

    def test_t07_waits_on(self):
        t07 = {t["task_id"]: t for t in self.block("pending")["tasks"]}["T07"]
        self.assertRegex(t07["text"], r"^Waits on ")
        self.assertNotIn("Lacks", t07["text"])
        self.assertFalse(_blocked(self.data, t07))

    def test_grouped_2105_figures_are_the_bridges(self):
        _check_grouped_2105_is_the_bridge(self, self.data)

    def test_no_filter_read_back_from_a_link(self):
        for path in g.glob_bridge():
            with open(path, encoding="utf-8") as f:
                found = re.search(r".*(\.get\(\s*[\"']filter[\"']|\[\s*[\"']filter[\"']\s*\]).*", f.read())
                self.assertIsNone(found, "%s: %s" % (os.path.basename(path), found and found.group(0).strip()))

    def test_no_shared_mutable_default(self):
        for path in g.glob_bridge():
            if path.endswith(".py"):
                with open(path, encoding="utf-8") as f:
                    found = re.search(r"(?m)^\s+\w+\s*:[^=\n]+=\s*(\[|\{|\(\s*\[).*", f.read())
                    self.assertIsNone(found, "%s: %s" % (os.path.basename(path), found and found.group(0).strip()))


class RealCashDefectBlocksT07(_PlantedPage):
    """Minors: T07 is not blocked because what it lacks is a reconciling item, not because of its id. A real cash
    defect planted on 1110 (test_golden.V5BankLineUnrecorded's BS9001, a bank line with no ledger entry) is T07's too,
    so T07 counts as blocked (blocked tasks = 9)."""

    @classmethod
    def plant(cls, data_dir):
        g.V5BankLineUnrecorded.plant(data_dir)

    def test_t07_blocked(self):
        pending = self.data["page"]["pending"]
        t07 = {t["task_id"]: t for t in pending["tasks"]}["T07"]
        types = {r["type"] for r, p in zip(self.data["tables"]["exceptions"]["rows"],
                                           self.data["page"]["exceptions"]["rows"])
                 if p["row_id"] in t07["lacks"]["exceptions"]}
        self.assertIn("bank_line_unrecorded", types, "the plant did not take")
        self.assertTrue(_blocked(self.data, t07))
        self.assertEqual(int(pending["status"]["blocked_tasks"]), BLOCKED_TASKS + 1)
        self.assertRegex(pending["sentence"], r"\b%d of them are blocked\b" % (BLOCKED_TASKS + 1))


class BridgeBlockHostGuard(_Screens):
    """Freeze fixes, material 1: the page script cannot run in the suite, so guard statically that bridgeBlock never
    meets an undefined host (Grouped leg 3 once threw): it defaults `host`, or every call passes two arguments."""

    def test_bridge_block_has_a_host(self):
        with open(os.path.join(g.REPO_ROOT, "bridge", "template.html"), encoding="utf-8") as f:
            text = f.read()
        defaults = re.search(r"function bridgeBlock\(bridge, host\) \{.*?host = host \|\|", text, re.S)
        calls = re.findall(r"bridgeBlock\(([^()]*(?:\([^()]*\)[^()]*)*)\)", text.replace("function bridgeBlock(", "function _("))
        self.assertTrue(defaults or all("," in c for c in calls), "bridgeBlock called without a host: " + repr(calls))


# --- Last round before freezing: waterfalls, impact per action, ERP file, explanations (plan block dee2151) ---------
# Figures recomputed by /private/tmp/claude-501/verifier66/ scripts, which never import bridge: leg 1 starts at the
# processor's 924,303.45 and lands on Mastercard's 909,419.05 (gross USD; the exceptions' gross by type sums to
# 14,884.40 without the month cut-off rows, which sit in both totals); leg 2 runs 968,096.50 -> 40,616.94 duplicate
# debit -> 1,008,713.44; the payable 70,588.66 -> -116,160.96 -> 44,643.99 + 928.31 -> 0.00 with all entries. Impact
# per task: T07 400,000.00, T05 15,600.17 on leg 1, T09 12,500.00, T11 8,412.30, T06 40,616.94 on leg 2, T02 90,215.88
# on leg 3; entries' 2105 net T08 and T13 -116,160.96, T05 14,671.86, T02 -90,215.88, T06 -40,616.94. The top total,
# each of the 262 linked exceptions once and no entry on top, is 567,345.29.

LEG1_BAR_TYPES = ("processor_duplicate", "sign_flip", "amount_diff", "fx_rate_diff", "month_cutoff", "processor_only",
                  "mastercard_only")
WATERFALL_ENDS = {"1": (MATCHES["1"]["processor_rows"][1], MATCHES["1"]["mastercard_rows"][1]),
                  "2": (LEG2_DAYS[1], LEG2_DAYS[2])}
PAYABLE_LEDGER = D("70588.66")
E10_USD = D("9127.92")
RESOLVES_TOTAL = D("567345.29")
ERP_FILE = "proposed_journal_lines.csv"
ERP_PREFIX = "PROPOSED-"
ERP_SOURCE = "PROPOSED_NOT_APPROVED"
ERP_DATE = "2026-09-30"


def _waterfalls(data):
    found = (data.get("page") or {}).get("overview", {}).get("waterfalls")
    if not isinstance(found, list) or not found:
        raise AssertionError("the Summary carries no waterfalls")
    return found


def _steps(waterfall):
    """start, every bar, end: what the page draws as bars."""
    return [waterfall.get("start") or {}] + list(waterfall.get("bars") or []) + [waterfall.get("end") or {}]


def _bar_total(case, bar):
    """What a bar's click opens, summed as the page sums it (None when it opens nothing): a Close link (or list of
    them) as `_opened`; a Reconciliation link to a table (filtered, its "sum" column, or [added, subtracted]) or to a
    Grouped leg; or "sources" with amounts, as the bridge's owed lines."""
    link = bar.get("link")
    if link:
        parts = link if isinstance(link, list) else [link]
        if all(p.get("screen") == "Close" for p in parts):
            return _opened(case, link)[0]
        case.assertIsInstance(link, dict, "a list of links mixing screens: %r" % link)
        case.assertIn(link.get("screen"), SCREENS, link)
        if "grouped" in link:
            rows = case.data["page"]["grouped"][link["grouped"]]
        else:
            case.assertIn(link.get("table"), sorted(case.data["tables"]), link)
            rows = case.data["tables"][link["table"]]["rows"]
            for column, value in link.get("filter", {}).items():
                wanted = value if isinstance(value, list) else [value]
                rows = [r for r in rows if r.get(column) in wanted]
        spec = link.get("sum")
        case.assertTrue(spec, "a bar link that sums nothing: %r" % link)
        if isinstance(spec, list):
            return sum((_num(r[spec[0]]) - _num(r[spec[1]]) for r in rows), D("0"))
        return sum((_num(r[spec]) for r in rows), D("0"))
    amounts = [s["amount"] for s in bar.get("sources") or [] if "amount" in s]
    return sum((_num(a) for a in amounts), D("0")) if amounts else None


class Waterfalls(_Screens):
    """Plan: a waterfall per pair of records on the Summary, computed in Python into the page data (the script only
    draws inline SVG). Leg 1: processor total -> one bar per difference type -> Mastercard total, to the cent. Leg 2:
    Mastercard settlements -> duplicate debit -> bank debits. Payable 2105 (leg 3): ledger -> proposed entries -> owed
    (settlement, timing) -> difference 0.00 with all entries, 9,127.92 shown as E10 on the confirmed basis. Every bar
    opens the rows that sum to it; every bar has a text label.

    Not fixed by the plan, so allowed here: the bars of one waterfall may open rows that sum to the bar's negative (leg
    1 runs from the processor to Mastercard, while the exceptions' gross is processor minus Mastercard), as long as
    every bar of that waterfall uses the same sign; start and end open rows that sum to them exactly. A bar of 0.00 may
    open nothing (the month cut-off rows are in both leg-1 totals, so their bar is 0.00 on this data)."""

    def by_leg(self):
        found = collections.defaultdict(list)
        for w in _waterfalls(self.data):
            found[str(w.get("leg"))].append(w)
        self.assertEqual(sorted(found), ["1", "2", "3"])
        return found

    def test_each_waterfall_adds_up_to_the_cent(self):
        for w in _waterfalls(self.data):
            with self.subTest(leg=w.get("leg"), basis=w.get("basis")):
                self.assertTrue(w.get("bars"), "a waterfall with no bars")
                start, end = _signed(w["start"]), _signed(w["end"])
                self.assertEqual(start + sum((_signed(b) for b in w["bars"]), D("0")), end)

    def test_leg1_and_leg2_start_and_end_on_the_recomputed_totals(self):
        found = self.by_leg()
        for leg, (start, end) in WATERFALL_ENDS.items():
            with self.subTest(leg=leg):
                self.assertEqual(len(found[leg]), 1)
                w = found[leg][0]
                self.assertEqual((_signed(w["start"]), _signed(w["end"])), (start, end))
        types = [b.get("type") for b in found["1"][0]["bars"]]
        self.assertEqual(sorted(t for t in LEG1_BAR_TYPES if t not in types), [], "leg-1 bar types missing")
        self.assertIn(MATCHES["2"]["duplicate_debits"][1], [abs(_signed(b)) for b in found["2"][0]["bars"]])

    def test_payable_waterfall(self):
        legs = self.by_leg()["3"]
        bridge = _bridge(self.data)
        for w in legs:
            with self.subTest(basis=w.get("basis")):
                self.assertEqual(_signed(w["start"]), PAYABLE_LEDGER)
                self.assertEqual(_signed(w["start"]), _signed(bridge["all"]["ledger"]))
                if w.get("basis") in bridge:
                    self.assertEqual(_signed(w["end"]), D(bridge[w["basis"]]["difference"]["usd"]))
        self.assertIn(D("0.00"), [_signed(w["end"]) for w in legs], "no payable waterfall ends at 0.00 (all entries)")
        text = json.dumps(legs)
        self.assertIn("E10", text)
        self.assertTrue("9127.92" in text or "9,127.92" in text, "the 9,127.92 of E10 is not on the payable waterfall")

    def test_every_bar_opens_rows_that_sum_to_it(self):
        for w in _waterfalls(self.data):
            signs = set()
            for i, bar in enumerate(_steps(w)):
                with self.subTest(leg=w.get("leg"), basis=w.get("basis"), bar=i, label=bar.get("label")):
                    usd = _signed(bar)
                    total = _bar_total(self, bar)
                    if total is None:
                        self.assertEqual(usd, D("0"), "a bar that opens nothing")
                        continue
                    if i in (0, len(_steps(w)) - 1):
                        self.assertEqual(total, usd, "start and end open rows that sum to them")
                    elif usd:
                        self.assertEqual(abs(total), abs(usd))
                        signs.add(total == usd)
            self.assertLessEqual(len(signs), 1, "bars of leg %s open rows with mixed signs" % w.get("leg"))

    def test_every_bar_has_a_label(self):
        for w in _waterfalls(self.data):
            self.assertTrue(str(w.get("title", "")).strip(), "a waterfall with no title")
            for bar in _steps(w):
                self.assertTrue(str(bar.get("label", "")).strip(), "a bar with no text label: %r" % bar)


class PageScriptDrawsAndExplains(_Screens):
    """Plan, static half (the page script cannot run in the suite): the waterfalls are inline SVG drawn by the script,
    no library; the "i" boxes open on click and close on a click outside or on Escape. How it looks is the session's
    Chrome check."""

    def test_draws_svg(self):
        self.assertRegex(self.script, r"createElementNS\(\s*[\"']http://www\.w3\.org/2000/svg[\"']|<svg\b")

    def test_explanations_close_on_escape_and_outside_click(self):
        self.assertRegex(self.script, r"[\"']Escape[\"']")
        self.assertRegex(self.script, r"(document|window|document\.body)\.addEventListener\(\s*[\"']click[\"']")

    def test_resolves_usd_shown(self):
        self.assertIn("Resolves USD", self.script + json.dumps(self.data["page"]))


class Explanations(_Screens):
    """Plan: every Summary figure, bridge line, waterfall (and each of its bars) and screen carries a key of
    policy.GLOSSARY (key -> one or two plain sentences); the page reads the texts as data; the texts live only in
    policy.py. Column headers carry one too in the plan; not pinned (the plan's test list leaves them out)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from bridge import policy
        cls.glossary = getattr(policy, "GLOSSARY", None)

    def keyed(self):
        """[(where, key)] over everything that must carry a glossary key."""
        out = [("figure " + str(f.get("id")), f.get("glossary")) for f in self.block("overview").get("figures", [])]
        for b in self.block("overview").get("payable_bridge", []):
            out += [("bridge %s %s" % (b.get("basis"), x.get("line")), x.get("glossary")) for x in b.get("lines", [])]
        for w in _waterfalls(self.data):
            name = "waterfall %s %s" % (w.get("leg"), w.get("basis") or "")
            out.append((name, w.get("glossary")))
            out += [("%s bar %d" % (name, i), bar.get("glossary")) for i, bar in enumerate(_steps(w))]
        screens = self.block("screens")
        self.assertEqual([s.get("name") for s in screens], list(SCREENS))
        out += [("screen " + str(s.get("name")), s.get("glossary")) for s in screens]
        return out

    def test_glossary_in_policy(self):
        self.assertIsInstance(self.glossary, dict, "policy.py has no GLOSSARY dict")
        for key, text in self.glossary.items():
            self.assertTrue(isinstance(text, str) and text.strip(), key)

    def test_everything_has_a_key_and_the_page_reads_its_text(self):
        self.assertIsInstance(self.glossary, dict, "policy.py has no GLOSSARY dict")
        page = self.block("glossary")
        for where, key in self.keyed():
            with self.subTest(where=where):
                self.assertIn(key, self.glossary)
                self.assertEqual(page.get(key), self.glossary[key])

    def test_texts_live_only_in_policy(self):
        self.assertIsInstance(self.glossary, dict, "policy.py has no GLOSSARY dict")
        folder = os.path.join(g.REPO_ROOT, "bridge")
        others = {}
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if name != "policy.py" and os.path.isfile(path) and name.endswith((".py", ".html")):
                with open(path, encoding="utf-8") as f:
                    others[name] = f.read()
        for key, text in self.glossary.items():
            pieces = [text.strip()] + [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if len(s) >= 40]
            for name, body in others.items():
                with self.subTest(key=key, file=name):
                    self.assertEqual([p for p in pieces if p in body], [])


class ImpactPerAction(_Screens):
    """Plan: each task shows "Resolves USD X": the net of the exceptions it lacks, signed, per leg, plus for entry tasks
    the 2105 net (debit - credit) of its entries; a total on top counts each exception once (none twice when linked to
    two tasks; entries correcting the same exceptions are not added on top); tasks ordered open first, then by the
    absolute USD they resolve. Recomputed here from the checklist-row links (PendingActions.expected), not from the
    task's own lists.

    Shape: task["resolves"] = {"usd": <the X it is ordered by>, "legs": {leg: <net>}, "entries_2105"?: <net>};
    data["page"]["pending"]["resolves_usd"] = <the top total>.

    X for a task that lacks both exceptions and entries was left open here; the clarification b9eef94 settles it (the
    exceptions' net, not plus entries) and a6596cf pins T02, T06 and T05 (FreezeFixes.test_tasks_resolve_their_exceptions_net)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lines, cls.checklist = _checklist_lines()
        cls.task_of_line = {v: k for k, v in cls.lines.items()}

    def expected(self):
        ex, entries, _checks = PendingActions.expected(self)
        net = {p["row_id"]: (r["leg"], D(r["net"])) for r, p in self.exceptions()}
        payable = _entries_on_payable(self.data)
        out = {}
        for task in self.lines:
            legs = collections.defaultdict(lambda: D("0"))
            for i in ex.get(task, ()):
                legs[net[i][0]] += net[i][1]
            out[task] = (dict(legs), entries.get(task, set()),
                         sum((payable.get(e, D("0")) for e in entries.get(task, ())), D("0")))
        union = set().union(*ex.values())
        return out, sum((net[i][1] for i in union), D("0"))

    def test_each_task_resolves(self):
        expected, _total = self.expected()
        for t in self.block("pending")["tasks"]:
            if t["status"] == "Done":
                continue
            legs, entries, e2105 = expected[t["task_id"]]
            with self.subTest(task=t["task_id"]):
                r = t.get("resolves")
                self.assertIsInstance(r, dict, "the task shows no impact")
                got = {k: D(v) for k, v in (r.get("legs") or {}).items() if D(v)}
                self.assertEqual(got, {k: v for k, v in legs.items() if v})
                if entries:
                    self.assertEqual(_num(r.get("entries_2105")), e2105)
                else:
                    self.assertEqual(_num(r.get("entries_2105")), D("0"))
                if not entries:
                    self.assertEqual(D(r["usd"]), sum(legs.values(), D("0")))
                elif not legs:
                    self.assertEqual(D(r["usd"]), e2105)

    def test_case_figures(self):
        expected, total = self.expected()
        self.assertEqual(total, RESOLVES_TOTAL)
        self.assertEqual(expected["T07"][0], {"3": D("400000.00")})
        self.assertEqual(expected["T05"][0], {"1": D("15600.17")})
        self.assertEqual((expected["T08"][2], expected["T13"][2]), (D("-116160.96"), D("-116160.96")))

    def test_top_total_counts_each_exception_once(self):
        _expected, total = self.expected()
        self.assertEqual(_num(self.block("pending").get("resolves_usd")), total)

    def test_ordered_open_first_then_by_absolute_usd(self):
        tasks = self.block("pending")["tasks"]
        done = [t["status"] == "Done" for t in tasks]
        self.assertEqual(done, sorted(done), "open tasks first")
        for t in tasks:
            if t["status"] != "Done":
                self.assertIn("usd", t.get("resolves") or {}, "open task %s shows no impact" % t["task_id"])
        for group in (False, True):
            amounts = [abs(_num((t.get("resolves") or {}).get("usd"))) for t in tasks if (t["status"] == "Done") == group]
            self.assertEqual(amounts, sorted(amounts, reverse=True), "done" if group else "open")


class ErpJournalFile(_Screens):
    """Plan: proposed_journal_lines.csv, the tenth output, in exactly gl_journal_lines.csv's columns and order; one line
    per proposed_entries.csv line, same account, debit and credit, in the same order; je_id "PROPOSED-" + entry id;
    posting_date 2026-09-30; source "PROPOSED_NOT_APPROVED"; account_name from gl_opening_balances.csv; description the
    entry title (an entry reversing in October may say so after it); reference the approval level and status.
    proposed_entries.csv itself stays byte-identical (HonestEntryEvidence.test_proposed_entries_file_is_cd9981ds)."""

    def rows(self):
        path = os.path.join(self.out_dir, ERP_FILE)
        self.assertTrue(os.path.isfile(path), "run.py wrote no %s" % ERP_FILE)
        return g._read_rows(self.out_dir, ERP_FILE)

    def test_header_is_the_ledgers(self):
        fields, _rows = self.rows()
        self.assertEqual(fields, g._read_rows(DATA_DIR, GL_LINES)[0])

    def test_lines_equal_proposed_entries(self):
        _f, rows = self.rows()
        _f, entries = g._read_rows(self.out_dir, "proposed_entries.csv")
        self.assertEqual([(r["je_id"], r["account"], D(r["debit_usd"]), D(r["credit_usd"])) for r in rows],
                         [(ERP_PREFIX + e["entry_id"], e["account"], _num(e["debit"]), _num(e["credit"]))
                          for e in entries])

    def test_marked_as_proposals(self):
        _f, rows = self.rows()
        _f, entries = g._read_rows(self.out_dir, "proposed_entries.csv")
        names = {r["account"]: r["account_name"] for r in g._read_rows(DATA_DIR, GL_OPENING)[1]}
        self.assertEqual(len(rows), len(entries))
        for r, e in zip(rows, entries):
            with self.subTest(je_id=r["je_id"], account=r["account"]):
                self.assertTrue(r["je_id"].startswith(ERP_PREFIX))
                self.assertEqual((r["source"], r["posting_date"]), (ERP_SOURCE, ERP_DATE))
                self.assertEqual(r["account_name"], names[e["account"]])
                self.assertTrue(r["description"].startswith(e["title"]), r["description"])
                self.assertIn(e["approval_level"], r["reference"])
                self.assertIn(e["status"], r["reference"])


class ReadmeHowToRun(unittest.TestCase):
    """Plan: the README tells a finance reader how to run it: install Python 3 (macOS and Windows), the one command, the
    month declared in policy.py (PERIOD_START, PERIOD_END, HOLIDAYS), the ten output files."""

    def test_readme(self):
        with open(os.path.join(g.REPO_ROOT, "README.md"), encoding="utf-8") as f:
            text = f.read()
        for needed in ["Python 3", "python3 run.py --data", "macOS", "Windows", "PERIOD_START", "PERIOD_END",
                       "HOLIDAYS"] + list(g.OUTPUT_FILES):
            with self.subTest(needed=needed):
                self.assertIn(needed, text)


# --- Freeze fixes from the closing review of the last round (plan block a6596cf) -------------------------------------
# Review (kept outside this repository): review-closing-4-2026-10-15.md. Figures recomputed by
# /private/tmp/claude-501/verifier66/split.py (never imports bridge) on the 0e12c26 run: the top total 567,345.29 is
# 400,000.00 funding in transit (T07) + 167,345.29 errors to correct. By exception class the timing part would be
# 458,759.78 (funding 400,000.00, misdated entry 45,331.47, suspense 12,500.00, cut-off 928.31); the plan says the
# timing part is T07's 400,000.00, and that is what is pinned.

RESOLVES_ONCE = {"T02": D("90215.88"), "T06": D("40616.94"), "T05": D("15600.17")}
RESOLVES_TIMING = D("400000.00")
TASK_BUTTON = ("button", {"link", "task"})   # how the page draws a task name: <button class="link task">


def _visible_exception_columns(script):
    """The exceptions table's default column list in the page script (as test_page reads it)."""
    for m in re.finditer(r"\[[^\[\]]*\]", script):
        keys = re.findall(r"[\"'](\w+)[\"']", m.group(0))
        if {"who_fixes", "clara_owner", "action", "net"} <= set(keys) and "gross" not in keys:
            return keys
    return None


def _print_rules(page):
    """[(selectors, declarations)] inside the page's @media print block."""
    at = page.find("@media print")
    if at < 0:
        return []
    start = page.index("{", at) + 1
    depth, i = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(page[i], 0)
        i += 1
    return [([s.strip() for s in sel.split(",")], body) for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", page[start:i - 1])]


def _matches(selector, element):
    """Whether a simple CSS selector's last compound (tag and classes only) matches element = (tag, {classes})."""
    last = re.split(r"[\s>+~]+", selector.strip())[-1]
    tag = re.match(r"^[a-z*]*", last).group(0)
    classes = set(re.findall(r"\.([\w-]+)", last))
    return tag in ("", "*", element[0]) and classes <= element[1] and not re.search(r"[#\[:]", last)


class FreezeFixes(_Screens):
    """Plan block "Freeze fixes from the closing review of the last round" (a6596cf). Pinned: a waterfall bar that links
    on a column has that column among the columns the opened table shows; T02, T06 and T05 resolve the exceptions' net,
    not plus entries; the headline split adds to the top total and its timing part is T07's 400,000.00; the page script
    holds no screen-name list; the README names CUTOFF_DATE; the print rule does not hide task buttons. By hand in
    Chrome: the Summary fits a 1440x813 viewport; a print preview of Pending actions; the footer and the sentence of a
    leg-1 click.

    Shape (names chosen here): a waterfall bar's link to the exceptions table that sums a column the table does not
    show by default carries "show": [<column>], the columns the table adds when opened from it, and the page script
    reads it (`.show`); data["page"]["pending"]["resolves_split"] = {"timing": "<decimal>", "errors": "<decimal>"};
    the task tagged timing carries task["resolves"]["tag"] = "timing"; the page script reads the screens from
    data["page"]["screens"]."""

    def test_bar_shows_the_column_it_sums(self):
        visible = _visible_exception_columns(self.script)
        self.assertTrue(visible, "no default column list for the exceptions table in the page script")
        checked = 0
        for w in _waterfalls(self.data):
            for bar in _steps(w):
                link = bar.get("link")
                if not isinstance(link, dict) or link.get("table") != "exceptions":
                    continue
                spec = link.get("sum")
                summed = spec if isinstance(spec, list) else [spec]
                shown = visible + list(link.get("show") or [])
                with self.subTest(leg=w.get("leg"), bar=bar.get("label")):
                    checked += 1
                    self.assertEqual([c for c in summed if c not in shown], [], "the table opens without the column "
                                     "the bar sums")
                    if link.get("show"):
                        self.assertRegex(self.script, r"\.show\b|\[\s*[\"']show[\"']\s*\]", "the script never reads show")
        self.assertGreater(checked, 0, "no waterfall bar opens the exceptions table")

    def test_tasks_resolve_their_exceptions_net(self):
        tasks = {t["task_id"]: t for t in self.block("pending")["tasks"]}
        for task, usd in RESOLVES_ONCE.items():
            with self.subTest(task=task):
                self.assertEqual(D(tasks[task]["resolves"]["usd"]), usd)

    def test_headline_split(self):
        pending = self.block("pending")
        split = pending.get("resolves_split")
        self.assertIsInstance(split, dict, "the top total carries no timing / errors split")
        self.assertEqual(_num(split.get("timing")) + _num(split.get("errors")), D(pending["resolves_usd"]))
        tasks = {t["task_id"]: t for t in pending["tasks"]}
        self.assertEqual(_num(split.get("timing")), D(tasks["T07"]["resolves"]["usd"]))
        self.assertEqual(_num(split.get("timing")), RESOLVES_TIMING)
        self.assertEqual(tasks["T07"]["resolves"].get("tag"), "timing")

    def test_no_screen_list_in_the_script(self):
        names = "|".join(re.escape(s) for s in SCREENS)
        for m in re.finditer(r"\[[^\[\]]*\]", self.script):
            found = set(re.findall(r"[\"'](%s)[\"']" % names, m.group(0)))
            self.assertLess(len(found), 3, "a screen-name list in the page script: %s" % m.group(0)[:120])
        self.assertRegex(self.script, r"\.screens\b|\[\s*[\"']screens[\"']\s*\]", "the script never reads page.screens")

    def test_readme_names_cutoff_date(self):
        with open(os.path.join(g.REPO_ROOT, "README.md"), encoding="utf-8") as f:
            self.assertIn("CUTOFF_DATE", f.read())

    def test_print_keeps_task_buttons(self):
        rules = _print_rules(self.script)
        self.assertTrue(rules, "the page has no print rules")
        hidden = [s for sels, body in rules if re.search(r"display\s*:\s*none", body) for s in sels
                  if _matches(s, TASK_BUTTON)]
        shown = [s for sels, body in rules if re.search(r"display\s*:\s*(?!none)\w+[^;]*!important", body) for s in sels
                 if _matches(s, TASK_BUTTON)]
        self.assertTrue(not hidden or shown, "printing hides the task buttons: %s" % hidden)


# --- Data quality as a filterable table (plan block a6596cf, bullets added by e8da937) -----------------------------
# Recomputed by /private/tmp/claude-501/verifier66/ on the 0e12c26 run, never importing bridge: the off-by-one between
# a check's count and its src (stale_authorisations 22 vs 23, impossible_dates 3 vs 4, references 105 vs 106) is the
# close_checklist.csv row each failed check cites for its task, not a flagged row. Without it clearing_days_vs_entries
# opens 155 rows, not 156: 151 processor rows of the 24-Sep clearing day and the 4 ledger lines of the 30-Sep one
# (PROC-20260930, posted 1-Oct) — 2 days.

NO_ROW_CHECKS = ("summary_vs_detail", "net_formula", "missing_inputs", "cash_reconciled", "inputs_cover_period",
                 "checklist_tasks_owned")
CASE_FLAGGED = {"clearing_days_vs_entries": (155, 2), "stale_authorisations": (22, None), "impossible_dates": (3, None),
                "references": (105, None)}


def _clearing_days(refs):
    """The processor clearing days a set of source rows covers: a processor row's clearing_date; a ledger line's day in
    its PROC-YYYYMMDD reference (the 30-Sep entry posted on 1-Oct is the 30-Sep clearing day)."""
    day = {"%s:%d" % (g.PROCESSOR, i + 2): r["clearing_date"] for i, r in enumerate(g._read_rows(DATA_DIR, g.PROCESSOR)[1])}
    for i, r in enumerate(g._read_rows(DATA_DIR, GL_LINES)[1]):
        found = re.fullmatch(r"PROC-(\d{4})(\d{2})(\d{2})", r["reference"])
        if found:
            day["%s:%d" % (GL_LINES, i + 2)] = "-".join(found.groups())
    return {day[r] for r in refs if r in day}


def _top_functions(script):
    """{name: body} of the page script's top-level (two-space indented) functions."""
    found = list(re.finditer(r"\n  function (\w+)\s*\(", script))
    return {m.group(1): script[m.start():(found[i + 1].start() if i + 1 < len(found) else len(script))]
            for i, m in enumerate(found)}


def _calls_any(body, names):
    return any(re.search(r"(?<![\w.])%s\(" % n, body.split("{", 1)[-1]) for n in names)


class DataQualityTable(_Screens):
    """Plan bullet "Data quality as a filterable table" (e8da937). Pinned: every check line states its count with a unit,
    and a count in rows equals the rows it opens, a count in days the processor clearing days they cover (_clearing_days); the flagged
    table has one row per flagged source row (the check's own line references, without the close-checklist row it
    cites for its task), each with a check key, a reason and a source; checks with no rows of their own are pass/fail
    lines only; Data quality and Reconciliation each have a copy and a CSV-download control (static). By hand: the
    footer sums the shown rows, the filter by check, and that copy and download act on the rows shown.

    Shape (names chosen here): data["page"]["checks"]["rows"][i]["units"] = [{"count": "<n>", "unit": <text with
    "row" or "day">}, ...], the first count being the check's own; data["page"]["flagged"] = {"rows": [{"check":
    <check name>, "reason": <text>, "ref": "file:line", "amount"?: "<decimal>"}]}. A passing check's rows may be in the
    flagged table or not (the plan does not say whether "statuses" rows, kept out of money, are flagged)."""

    def own_rows(self):
        """{check: [file:line refs]}: its src without the checklist row and without whole files."""
        out = {}
        for c in self.table("checks"):
            out[c["name"]] = [p for p in _parts(c["src"]) if re.fullmatch(r"[\w.]+:\d+", p)
                              and not p.startswith(g.CHECKLIST + ":")]
        return out

    def flagged(self):
        block = self.block("flagged")
        rows = block.get("rows") if isinstance(block, dict) else None
        self.assertIsInstance(rows, list, "no flagged-rows table")
        return rows

    def test_case_counts(self):
        own = self.own_rows()
        for check, (rows, n_days) in CASE_FLAGGED.items():
            self.assertEqual(len(own[check]), rows, check)
            if n_days:
                self.assertEqual(len(_clearing_days(own[check])), n_days, check)

    def test_every_check_line_states_a_unit_that_matches(self):
        own = self.own_rows()
        for c, p in zip(self.table("checks"), self.data["page"]["checks"]["rows"]):
            name = c["name"]
            with self.subTest(check=name):
                units = p.get("units") or []
                if name in NO_ROW_CHECKS:
                    self.assertEqual(units, [], "a check with no rows of its own is a pass/fail line only")
                    continue
                self.assertTrue(units, "the check line states no unit")
                self.assertEqual(int(units[0]["count"]), int(c["count"]))
                for u in units:
                    unit = str(u.get("unit", ""))
                    self.assertRegex(unit, r"\b(rows?|days?)\b")
                    if re.search(r"\brows?\b", unit):
                        self.assertEqual(int(u["count"]), len(own[name]), "rows stated vs rows opened")
                    else:
                        self.assertEqual(int(u["count"]), len(_clearing_days(own[name])), "days stated vs days opened")

    def test_one_flagged_row_per_flagged_source_row(self):
        rows = self.flagged()
        checks = {c["name"]: c for c in self.table("checks")}
        got = collections.Counter((r.get("check"), r.get("ref")) for r in rows)
        self.assertEqual([k for k, n in got.items() if n > 1], [], "a source row listed twice for one check")
        for r in rows:
            self.assertIn(r.get("check"), checks)
            self.assertTrue(str(r.get("reason", "")).strip(), r)
        own = self.own_rows()
        for name, c in checks.items():
            with self.subTest(check=name):
                mine = sorted(ref for check, ref in got if check == name)
                if name in NO_ROW_CHECKS:
                    self.assertEqual(mine, [])
                elif c["passed"] == "false":
                    self.assertEqual(mine, sorted(own[name]))

    def test_copy_and_download_on_both_tables(self):
        functions = _top_functions(self.script)
        copiers = {n for n, b in functions.items() if re.search(r"clipboard|execCommand\(\s*[\"']copy", b)}
        copiers |= {n for n, b in functions.items() if _calls_any(b, copiers)}
        downloaders = {"download"} | {n for n, b in functions.items() if _calls_any(b, ["download"])}
        for panel in ("dataQualityPanel", "reconPanel"):
            with self.subTest(panel=panel):
                self.assertIn(panel, functions)
                self.assertTrue(_calls_any(functions[panel], copiers - {panel}), "no copy control")
                self.assertTrue(_calls_any(functions[panel], downloaders - {panel}), "no CSV download")


# --- Reconciliation reads by type (plan 795490d) -------------------------------------------------------------------
# Recomputed by /private/tmp/claude-501/verifier66/bytype.py from the raw files (never imports bridge; the matching of
# verifier50/recount.py): pairs, processor USD, Mastercard USD per group. Same per-type differences as the closing
# review's leg1.py. The data-issue class has 131 rows in exceptions.csv: 130 on leg 1 (reference_bad 105, auth_stale
# 22, auth_after_clearing 3) and input_missing on leg 3 (the processor invoice).

LEG1_BY_TYPE = {"matched_equal": (2997, D("881142.94"), D("881142.94")),
                "amount_diff": (8, D("6926.00"), D("6178.07")), "sign_flip": (4, D("1270.09"), D("-1270.09")),
                "fx_rate_diff": (95, D("21123.34"), D("20360.62")), "month_cutoff": (4, D("941.33"), D("941.33")),
                "processor_duplicate": (6, D("3640.35"), D("0")), "processor_only": (3, D("9259.40"), D("0")),
                "mastercard_only": (5, D("0"), D("2066.18"))}
DATA_ISSUE = "data_issue"


def _hidden_group(rows, page_rows, hidden):
    """The row ids the bare Detailed view hides: the declared class, narrowed to the declared "types" when given."""
    types = hidden.get("types")
    return {p["row_id"] for r, p in zip(rows, page_rows)
            if r["cls"] == hidden.get("cls") and (types is None or r["type"] in types)}


class ReconciliationByType(_Screens):
    """Plan "Reconciliation reads by type" (795490d). Pinned: Grouped leg 1 has the matched-exactly row plus one row per
    leg-1 type, its columns sum to the two totals; the Detailed default hides exactly the data-issue class and the
    control names its count; the page script orders Detailed by type then absolute net (static); the type is the
    table's first column (test_page.PageScript, amended). By hand: the per-type summary has no inner scroll and a click
    filters; a collapsible header row per type with count and net; the notes columns fit at 1440 px.

    Shape (names chosen here): Grouped leg 1 rows carry "type" ("matched_equal" for the pairs that match exactly,
    with "count" = the pairs); data["page"]["exceptions"]["hidden_by_default"] = {"cls": "data_issue", "count":
    "<n>", "label": <the control's text>}. Data-flag types (no money) have a row of 0.00 in both columns: their rows'
    amounts are already in the matched or difference groups."""

    def leg1(self):
        rows = self.block("grouped").get("1", [])
        by_type = {r.get("type"): r for r in rows}
        self.assertEqual(len(by_type), len(rows), "a type twice, or rows with no type")
        return by_type

    def test_grouped_leg1_rows(self):
        by_type = self.leg1()
        types = {r["type"] for r in self.table("exceptions") if r["leg"] == "1"}
        self.assertEqual(sorted(by_type), sorted(types | {"matched_equal"}))
        matched = by_type["matched_equal"]
        self.assertEqual((int(matched.get("count", -1)), D(matched["processor_usd"]), D(matched["mastercard_usd"])),
                         LEG1_BY_TYPE["matched_equal"])
        for kind, (_n, proc, mc) in LEG1_BY_TYPE.items():
            with self.subTest(type=kind):
                self.assertEqual((_num(by_type[kind]["processor_usd"]), _num(by_type[kind]["mastercard_usd"])),
                                 (proc, mc))
        for kind in types - set(LEG1_BY_TYPE):
            with self.subTest(type=kind):
                self.assertEqual((_num(by_type[kind]["processor_usd"]), _num(by_type[kind]["mastercard_usd"])),
                                 (D("0"), D("0")))

    def test_grouped_leg1_sums_to_the_totals(self):
        rows = list(self.leg1().values())
        self.assertEqual((sum((_num(r["processor_usd"]) for r in rows), D("0")),
                          sum((_num(r["mastercard_usd"]) for r in rows), D("0"))), LEG1_DAY_TOTALS)
        self.assertEqual(sum((_num(r["difference"]) for r in rows), D("0")), LEG1_DAY_TOTALS[0] - LEG1_DAY_TOTALS[1])

    def test_detailed_hides_the_data_issue_class(self):
        # Amended by e43505c (freeze fixes 2): the hidden group is the 130 leg-1 data flags, not the whole class (131):
        # the missing processor invoice stays visible. The group is declared by class and "types"; the control text
        # names the number hidden under the current view, so a "label" in the data is optional.
        hidden = self.block("exceptions").get("hidden_by_default")
        self.assertIsInstance(hidden, dict, "the Detailed view hides nothing by default")
        group = _hidden_group(self.table("exceptions"), self.data["page"]["exceptions"]["rows"], hidden)
        expected = {p["row_id"] for r, p in self.exceptions() if r["cls"] == DATA_ISSUE and r["leg"] == "1"}
        self.assertEqual(len(expected), DATA_FLAGS)
        self.assertEqual(group, expected, "the hidden group is not exactly the leg-1 data flags")
        self.assertEqual((hidden.get("cls"), int(hidden.get("count", -1))), (DATA_ISSUE, DATA_FLAGS))
        if "label" in hidden:
            self.assertIn(str(DATA_FLAGS), str(hidden["label"]), "the control does not name the count")
        self.assertRegex(self.script, r"hidden_by_default")

    def test_detailed_sorted_by_type_then_absolute_net(self):
        sorts = [self.script[m.end():m.end() + 600] for m in re.finditer(r"\.sort\(", self.script)]
        self.assertTrue(any(re.search(r"\btype\b", body) and re.search(r"Math\.abs\([^)]*net", body) for body in sorts),
                        "no sort of the Detailed rows by type then absolute net in the page script")


# --- Freeze fixes 2, from closing review 5 (plan e43505c) ----------------------------------------------------------
# Review (kept outside this repository): review-closing-5-2026-10-15.md, material 1 (a Summary figure said 255
# and opened 125 rows) and minor 3 (copy put date first, internal keys, no notes). Recomputed from the d8aa455 page
# data in Python (never importing bridge): with the flags shown whenever Reconciliation is opened from another screen,
# leg 1 "Exceptions" opens 255 rows, leg-1 "Waiting outside Clara" 251, leg 3 "Exceptions" 6, leg-3 "Waiting" 1.


def _reconciliation_api(script):
    """The text of reconPanel's `apply` (how another screen opens Reconciliation), up to the next member."""
    found = re.search(r"apply\s*:\s*function\s*\([^)]*\)\s*\{(.*?)\n\s*\w+\s*:\s*function", script, re.S)
    return found.group(1) if found else ""


class FiguresOpenTheirRows(_Screens):
    """Plan "A figure opens exactly as many rows as it says" and "Copy rows shown copies what is on screen" (e43505c).
    Pinned: every Summary figure linking to the exceptions table states a count equal to the rows its link shows under
    the hiding rule — flags hidden only on the bare, unfiltered Detailed view, shown whenever Reconciliation is opened
    from another screen, filtered or searched (computed here from the page data; the script half is static: `apply`
    turns the flags on, the hiding test reads the search box); the hidden group is the 130 leg-1 flags
    (ReconciliationByType.test_detailed_hides_the_data_issue_class, amended); copy uses the shown columns, their labels
    and the notes, like the CSV (static). The headline label (bf757d9): the timing part reads "funding in transit (clears 01-Oct)",
    the rest "needs action by Clara", never "errors to correct". Not pinned: the one type order, the minus sign, the Grouped footer, the Data quality "All" footer, the "Missing
    inputs" text — by hand in Chrome."""

    def test_figure_counts_equal_the_rows_they_open(self):
        hidden = self.block("exceptions").get("hidden_by_default") or {}
        group = _hidden_group(self.table("exceptions"), self.data["page"]["exceptions"]["rows"], hidden)
        checked = 0
        for f in self.block("overview").get("figures", []):
            link = f.get("link") or {}
            if link.get("table") != "exceptions" or "count" not in f:
                continue
            with self.subTest(figure=f.get("id")):
                checked += 1
                self.assertTrue(link.get("filter"), "a figure that opens the bare Detailed view")
                rows = self.exceptions()
                for column, value in link["filter"].items():
                    wanted = value if isinstance(value, list) else [value]
                    rows = [(r, p) for r, p in rows if r.get(column) in wanted]
                # Opened from another screen: nothing is hidden. On the bare view these would be hidden:
                flags = [p["row_id"] for _r, p in rows if p["row_id"] in group]
                self.assertEqual(int(f["count"]), len(rows), "%d of them are data flags" % len(flags))
        self.assertGreater(checked, 0)

    def test_opening_from_another_screen_shows_the_flags(self):
        body = _reconciliation_api(self.script)
        self.assertTrue(body, "no apply member on the Reconciliation panel")
        self.assertRegex(body, r"\b\w+\s*=\s*true\b", "opening Reconciliation from another screen leaves the flags hidden")

    def test_search_shows_the_flags(self):
        lines = [l for l in self.script.splitlines() if "hid." in l and "return false" in l]
        self.assertTrue(lines, "no hiding test in the page script")
        self.assertTrue(all(re.search(r"filt\.q\b|\bq\b|bare", l) for l in lines),
                        "the hiding test ignores the search: %s" % lines)

    def test_hiding_reads_the_declared_types(self):
        self.assertRegex(self.script, r"\.types\b", "the page hides by class only")

    def test_copy_uses_the_shown_columns_and_labels(self):
        recon = _top_functions(self.script).get("reconPanel", "")
        handlers = re.split(r"\.addEventListener\(\s*[\"']click[\"']", recon)[1:]
        copying = [h.split("addEventListener")[0] for h in handlers if re.search(r"copyText|clipboard", h.split("addEventListener")[0])]
        found = re.match(r"(.*)", copying[0], re.S) if copying else None
        self.assertTrue(found, "no copy handler on Reconciliation")
        body = found.group(1)
        self.assertNotRegex(body, r"\[\s*[\"']date[\"']\s*\]\s*\.concat", "copy puts the date first")
        self.assertRegex(body, r"(?i)label|head", "copy uses internal keys, not the shown labels")
        self.assertRegex(body, r"(?i)note", "copy leaves out the notes columns")

    def test_headline_labels(self):
        text = self.script + json.dumps(self.data["page"])
        for label in ("needs action by Clara", "funding in transit (clears 01-Oct)"):
            self.assertIn(label, text)
        self.assertNotIn("errors to correct", text)


# --- Named owners from the email thread (plan 7b79b4c) -------------------------------------------------------------
# The role -> person map is read here from treasury_email_thread.txt (FROM: header lines, "Name (Role)"); no name is
# written in the tests. On the case file: Treasury, Finance Ops, Controller and Customer Success. Recomputed from the
# raw checklist: 16 tasks have a named role (Finance Ops 8, Treasury 4, Controller 3, Treasury / AR 1). The plan lists
# 15 and leaves out T02, which is Finance Ops in close_checklist.csv; the rule (the role) is pinned, not the list.
# proposed_journal_lines.csv sha256 a8ccdcc3... on the 073a17e run (verifier66/out3).

EMAIL = "treasury_email_thread.txt"
NAMED_PAIR = re.compile(r"([A-Z][a-z]+(?: [A-Z][a-z]+)+) \(([^)]+)\)")
COMBINED_ROLE = ("Treasury / AR", "Treasury")   # the plan: Treasury / AR -> the Treasury person (she raised the suspense)
NAMED_TASKS = 16
JOURNAL_073A17E_SHA256 = "a8ccdcc36f0b48a78e0dd2aee607e942e479294cdf611c929a46d4e03d3eb07a"


def _email_people(data_dir=None):
    """{role: (person, [line numbers])}: every "Name (Role)" on a FROM: header line of the email file."""
    with open(os.path.join(data_dir or DATA_DIR, EMAIL), encoding="utf-8") as f:
        lines = f.read().splitlines()
    out = {}
    for number, line in enumerate(lines, start=1):
        if line.startswith("FROM:"):
            for person, role in NAMED_PAIR.findall(line):
                out.setdefault(role, (person, []))[1].append(number)
    people = {role: person for role, (person, _l) in out.items()}
    if COMBINED_ROLE[1] in people:
        people[COMBINED_ROLE[0]] = people[COMBINED_ROLE[1]]
    return people, lines


def _email_ref_ok(case, refs, person, role, lines):
    """A src cites the email for the name: a `treasury_email_thread.txt:<fragment>` whose fragment sits on a FROM: line
    naming the person (with the role in parentheses for a role the email states)."""
    cited = [r.split(":", 1)[1] for r in refs if r.startswith(EMAIL + ":")]
    case.assertTrue(cited, "no email citation for %s" % person)
    want = "%s (%s)" % (person, role) if role != COMBINED_ROLE[0] else person
    case.assertTrue(any(c and c in line and want in line and line.startswith("FROM:") for c in cited for line in lines),
                    "the email citation %r does not point at a FROM: line naming %s" % (cited, want))


class NamedOwners(_Screens):
    """Plan "Named owners from the email thread" (7b79b4c). Pinned: the names come from the email's FROM: lines, each
    with its source; exactly the tasks of the named roles carry a name (the role is the rule; 16 on the case data, see
    the note above), no other task does; close_tracker.csv owner_name (its src cites the email line) and exceptions.csv
    clara_owner_name; drafts name a person only where the recipient role has one; the page shows "role — name" with an
    explanation key; proposed_entries.csv (HonestEntryEvidence) and proposed_journal_lines.csv unchanged.

    Shape (names chosen here): task["owner_name"] (absent or blank when none) and task["owner_glossary"] = a GLOSSARY
    key whose text names the email file. By hand: Assigned person defaults to the named owner and a typed value wins."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.people, cls.lines = _email_people()

    def test_email_gives_the_three_roles(self):
        for role in ("Controller", "Treasury", "Finance Ops"):
            self.assertIn(role, self.people)
        self.assertEqual(len(set(self.people[r] for r in ("Controller", "Treasury", "Finance Ops"))), 3)

    def test_tracker_names(self):
        fields, rows = g._read_rows(self.out_dir, "close_tracker.csv")
        self.assertIn("owner_name", fields)
        self.assertEqual(sum(1 for r in rows if r["owner_role"] in self.people), NAMED_TASKS)
        for r in rows:
            with self.subTest(task=r["task_id"]):
                self.assertEqual(r["owner_name"], self.people.get(r["owner_role"], ""))
                if r["owner_name"]:
                    _email_ref_ok(self, _parts(r["src"]), r["owner_name"], r["owner_role"], self.lines)

    def test_exceptions_names(self):
        fields, rows = g._read_rows(self.out_dir, "exceptions.csv")
        self.assertIn("clara_owner_name", fields)
        for r in rows:
            self.assertEqual(r["clara_owner_name"], self.people.get(r["clara_owner"], ""), r["key"])

    def test_pending_tasks_named_with_an_explanation(self):
        from bridge import policy
        glossary = getattr(policy, "GLOSSARY", {})
        for t in self.block("pending")["tasks"]:
            with self.subTest(task=t["task_id"]):
                name = self.people.get(t.get("owner"), "")
                self.assertEqual(t.get("owner_name") or "", name)
                if name:
                    self.assertIn(EMAIL, glossary.get(t.get("owner_glossary"), ""), "no explanation of the name")

    def test_page_shows_role_and_name(self):
        self.assertRegex(self.script, r"owner_name[^;]{0,200}\u2014|\u2014[^;]{0,200}owner_name",
                         "the page script never shows \"role — name\"")

    def test_drafts_name_only_known_people(self):
        everyone = set(self.people.values())
        for d in self.block("pending").get("drafts", []):
            with self.subTest(draft=d.get("id")):
                person = self.people.get(d.get("to"))
                named = {p for p in everyone if p.split()[0] in d.get("text", "")}
                self.assertEqual(named, {person} if person else set())

    def test_journal_file_unchanged(self):
        import hashlib
        with open(os.path.join(self.out_dir, ERP_FILE), "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(), JOURNAL_073A17E_SHA256)
