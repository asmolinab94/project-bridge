"""Golden-figure tests for Project Bridge (spec E0): the verified figures, written before the code.

Run from the repo root:  BRIDGE_DATA=<clara_caso_finance/insumos/datos> python3 -m unittest -v

One or more TestCases per row V1-V13 of the spec's *End-to-end verification* table, split by the task (tasks.md) that
turns them green; each docstring names what it guards. Figures are asserted on `bridge.build(BRIDGE_DATA)` through
the plan's Contracts; V10, V11 and V13 run `python3 run.py --data ... --out <tempdir>` in a subprocess. Synthetic
cases copy the data folder to a temp dir, plant or edit a few rows there and build on the copy; the real folder is
never written. Every money comparison is an exact `Decimal` one. Every expected figure was recomputed from the raw
CSVs by an independent throwaway script before it was written down.

Not automated — V14 (I1), manual demo in Chrome with index.html opened as a file: filter by class, country, date and
amount; read each row's source fields inline; assign owner, status and comment, reload and see them; export
CSV.
"""

import csv
import dataclasses
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import ROUND_HALF_UP, Decimal

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tests import test_guards as guards  # noqa: E402

DATA_DIR = os.environ.get("BRIDGE_DATA", "")
RUN_PY = os.path.join(REPO_ROOT, "run.py")

PROCESSOR = "processor_transactions.csv"
MC_DETAIL = "mastercard_clearing_detail.csv"
MC_SUMMARY = "mastercard_daily_settlement_summary.csv"
BANK = "bridge_account_statement.csv"
GL_LINES = "gl_journal_lines.csv"
GL_OPENING = "gl_opening_balances.csv"
INPUT_FILES = [PROCESSOR, MC_DETAIL, MC_SUMMARY, BANK, GL_LINES, GL_OPENING, "fx_rates_daily.csv",
               "customers.csv", "close_checklist.csv", "treasury_email_thread.txt", "mastercard_fee_notice.txt"]
# Plan block "Extras before submission": the run writes nine files, treasury.csv the ninth. Amended by the plan block
# "Last round before freezing" (dee2151): ten files, proposed_journal_lines.csv (the ERP file) the tenth.
OUTPUT_FILES = ["index.html", "exceptions.csv", "proposed_entries.csv", "balances.csv", "cash_recon.csv",
                "close_tracker.csv", "checks.csv", "run_manifest.json", "treasury.csv", "proposed_journal_lines.csv"]
# dee2151: the ERP file has exactly gl_journal_lines.csv's columns, so no src; each of its lines is a proposed_entries.csv
# line (test_screens.ErpJournalFile), which carries the src.
NO_SRC_OUTPUTS = ("proposed_journal_lines.csv",)
ACCOUNTS = ["1110", "1210", "1250", "2105", "2150", "2300", "2900", "4100", "5100", "6150", "3900"]
MONEY_CLASSES = ("timing", "real_error")
SEPTEMBER = (2026, 9)
OCTOBER = (2026, 10)
DECIMAL_TEXT = re.compile(r"^-?\d+(\.\d+)?$")


def D(text):
    return Decimal(text)


# Unexplained aggregate. Andrés decided (2026-10-14, readings after the repair review) that every classified
# difference is explained: policy.UNEXPLAINED_TYPES is empty and the aggregate stays a reported 0.00 on any data.
EXPECTED_UNEXPLAINED_REAL = D("0.00")


def setUpModule():
    if not DATA_DIR:
        raise RuntimeError("BRIDGE_DATA is not set: point it at clara_caso_finance/insumos/datos")
    if not os.path.isdir(DATA_DIR):
        raise RuntimeError("BRIDGE_DATA=%r is not a directory" % DATA_DIR)


# --- Shared fixtures ---------------------------------------------------------------------------------------------

_cache = {}


def _build(data_dir):
    """`bridge.build(data_dir)`, built once per folder; a failure to import or build is re-raised in every case."""
    if data_dir not in _cache:
        try:
            import bridge
            _cache[data_dir] = ("ok", bridge.build(data_dir))
        except Exception as exc:  # noqa: BLE001 - re-raised below, per case
            _cache[data_dir] = ("error", exc)
    status, value = _cache[data_dir]
    if status == "error":
        raise value
    return value


def _result():
    return _build(DATA_DIR)


def _fingerprints():
    found = {}
    for name in sorted(os.listdir(DATA_DIR)):
        path = os.path.join(DATA_DIR, name)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                found[name] = hashlib.sha256(f.read()).hexdigest()
    return found


def _run():
    """Runs run.py once into a temp dir; returns (out_dir, fingerprints before, fingerprints after)."""
    if "run" not in _cache:
        out_dir = tempfile.mkdtemp(prefix="bridge-out-")
        before = _fingerprints()
        proc = subprocess.run([sys.executable, "-E", "-s", RUN_PY, "--data", DATA_DIR, "--out", out_dir],
                              cwd=REPO_ROOT, capture_output=True, text=True, timeout=600)
        _cache["run"] = (proc, out_dir, before, _fingerprints())
    proc, out_dir, before, after = _cache["run"]
    if proc.returncode != 0:
        raise AssertionError("run.py exited %d\nstdout:\n%s\nstderr:\n%s" % (proc.returncode, proc.stdout, proc.stderr))
    return out_dir, before, after


def _run_on(data_dir):
    """Runs run.py on an edited data folder into a new temp dir; returns the output dir."""
    out_dir = tempfile.mkdtemp(prefix="bridge-out-planted-")
    proc = subprocess.run([sys.executable, "-E", "-s", RUN_PY, "--data", data_dir, "--out", out_dir],
                          cwd=REPO_ROOT, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise AssertionError("run.py exited %d\nstderr:\n%s" % (proc.returncode, proc.stderr))
    return out_dir


def _read_rows(data_dir, file_name):
    with open(os.path.join(data_dir, file_name), newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def _lines_of(file_name, column, value, data_dir=None):
    _fields, rows = _read_rows(data_dir or DATA_DIR, file_name)
    return [(file_name, line) for line, row in enumerate(rows, start=2) if row[column] == value]


def _line_of(file_name, column, value, data_dir=None):
    """The (file, line) source of the first raw row whose `column` equals `value`; header = line 1."""
    found = _lines_of(file_name, column, value, data_dir)
    if not found:
        raise AssertionError("%s has no row with %s=%s" % (file_name, column, value))
    return found[0]


def _field(obj, name):
    """Reads a contract field from a dict or an object."""
    return obj[name] if isinstance(obj, dict) else getattr(obj, name)


def _src_list(src):
    """A `src` field holds one (file, line) tuple or a list of them."""
    if src and isinstance(src[0], (list, tuple)):
        return [tuple(s) for s in src]
    return [tuple(src)]


def _month(day):
    return (day.year, day.month)


def _missing_labels(result):
    """The `<what>` of each loaded missing input, as its `missing:<what>` source renders it."""
    return [src[1] for _what, src in result.inputs.missing]


def _rendered_srcs(srcs):
    """A `src` field as the CSV cell must say it: the set of `file:locator` parts."""
    parts = _src_list(srcs) if srcs else []
    if not parts or any(len(s) != 2 for s in parts):
        raise AssertionError("src is not a list of (file, locator) pairs: %r" % (srcs,))
    return sorted({"%s:%s" % s for s in parts})


def _source_problems(result, data_dir):
    """Differences without a real source. Each one cites an input CSV line (int, header excluded) or an input text
    label; `input_missing` cites a loaded missing input instead. A leg-1 difference keyed by a txn_id cites the
    processor line that holds that txn_id."""
    inputs = guards._inputs(data_dir)
    missing = _missing_labels(result)
    _fields, rows = _read_rows(data_dir, PROCESSOR)
    txn_at = {(PROCESSOR, line): row["txn_id"] for line, row in enumerate(rows, start=2)}
    txn_ids = set(txn_at.values())

    def real(src):
        if len(src) != 2 or src[0] not in inputs:
            return False
        kind, locator = inputs[src[0]], src[1]
        if kind[0] == "csv":
            return type(locator) is int and 2 <= locator <= kind[1]
        return isinstance(locator, str) and guards._label_ok(locator, kind[1], kind[2])

    problems = []
    for d in result.recon.differences:
        srcs = _src_list(d.srcs) if d.srcs else []
        if d.type == "input_missing":
            sourced = any(len(s) == 2 and s[0] == "missing" and s[1] in missing for s in srcs)
        else:
            sourced = any(real(s) for s in srcs)
        if not sourced:
            problems.append((d.type, d.key, "no real source", srcs))
        if d.leg == 1 and d.key in txn_ids and not any(txn_at.get(s) == d.key for s in srcs):
            problems.append((d.type, d.key, "no processor line holding the txn_id", srcs))
    return problems


def _floats_in(root):
    """Paths to every float reachable from `root` through dataclasses, plain objects (their vars), dicts (keys and
    values), lists, tuples, sets."""
    found, seen, stack = [], set(), [("result", root)]
    while stack:
        path, node = stack.pop()
        if isinstance(node, float):
            found.append(path)
            continue
        if id(node) in seen:
            continue
        if dataclasses.is_dataclass(node) and not isinstance(node, type):
            seen.add(id(node))
            stack.extend(("%s.%s" % (path, f.name), getattr(node, f.name)) for f in dataclasses.fields(node))
        elif isinstance(node, dict):
            seen.add(id(node))
            for key, value in node.items():
                stack.extend((("%s key %r" % (path, key), key), ("%s[%r]" % (path, key), value)))
        elif isinstance(node, (list, tuple, set, frozenset)):
            seen.add(id(node))
            stack.extend(("%s[%d]" % (path, i), value) for i, value in enumerate(node))
        elif hasattr(node, "__dict__") and not isinstance(node, type) and not callable(node):
            seen.add(id(node))
            stack.extend(("%s.%s" % (path, name), value) for name, value in vars(node).items())
    return found


def _account_deltas(entries):
    deltas = {}
    for entry in entries:
        for account, debit, credit in entry.lines:
            deltas[str(account)] = deltas.get(str(account), D("0")) + debit - credit
    return deltas


def _balances(result=None):
    return {str(k): v for k, v in (result or _result()).close.balances.items()}


def _cleared_net(result):
    return sum((r["net"] for r in result.inputs.processor if r["status"] == "CLEARED"), D("0"))


def _mastercard_september_net(result):
    return sum((r["net_settlement_usd"] for r in result.inputs.mc_detail
                if _month(r["clearing_date"]) == SEPTEMBER), D("0"))


# --- Planting helpers for synthetic cases --------------------------------------------------------------------------

def _write_rows(data_dir, file_name, fields, rows):
    with open(os.path.join(data_dir, file_name), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _edit(data_dir, file_name, key_col, key, **changes):
    fields, rows = _read_rows(data_dir, file_name)
    hits = [r for r in rows if r[key_col] == key]
    assert len(hits) == 1, (file_name, key)
    hits[0].update({k: str(v) for k, v in changes.items()})
    _write_rows(data_dir, file_name, fields, rows)


def _shift_mc(data_dir, network_ref, delta):
    """Moves one Mastercard row's USD amount and net by `delta`, keeping net = amount - interchange + fee."""
    _fields, rows = _read_rows(data_dir, MC_DETAIL)
    row = [r for r in rows if r["network_ref"] == network_ref][0]
    _edit(data_dir, MC_DETAIL, "network_ref", network_ref, amount_usd=D(row["amount_usd"]) + delta,
          net_settlement_usd=D(row["net_settlement_usd"]) + delta)


def _shift_summary(data_dir, settlement_date, delta):
    _fields, rows = _read_rows(data_dir, MC_SUMMARY)
    row = [r for r in rows if r["settlement_date"] == settlement_date][0]
    _edit(data_dir, MC_SUMMARY, "settlement_date", settlement_date,
          net_settlement_usd=D(row["net_settlement_usd"]) + delta)


def _append(data_dir, file_name, new_rows):
    fields, rows = _read_rows(data_dir, file_name)
    _write_rows(data_dir, file_name, fields, rows + [dict(dict.fromkeys(fields, ""), **r) for r in new_rows])


class _Golden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = _result()

    def diffs(self, leg=None, type_=None, result=None):
        return [d for d in (result or self.r).recon.differences
                if (leg is None or d.leg == leg) and (type_ is None or d.type == type_)]


class _Planted:
    """Mixin, listed before `_Golden`: builds on a temp copy of the data folder after `plant(data_dir)` edits it. Not
    a TestCase itself, so unittest never collects it without a `plant`."""

    @classmethod
    def plant(cls, data_dir):
        raise NotImplementedError

    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(prefix="bridge-planted-")
        cls.addClassCleanup(tmp.cleanup)  # runs even when plant or build raises
        cls.data = os.path.join(tmp.name, "datos")
        shutil.copytree(DATA_DIR, cls.data)
        cls.plant(cls.data)
        cls.r = _build(cls.data)

    def test_close_and_checks_complete_on_edited_data(self):
        from bridge import policy
        self.assertTrue(self.r.close.entries)
        self.assertEqual(sorted({c.name for c in self.r.checks}), sorted(policy.CHECKS))


# --- V1 ------------------------------------------------------------------------------------------------------------

class V1LoadTotals(_Golden):
    """V1 / I3, load level (T1): CLEARED rows sum to 912,453.49 net (3,117 rows); Mastercard Sep 896,853.32."""

    def test_processor_cleared_totals(self):
        cleared = [r for r in self.r.inputs.processor if r["status"] == "CLEARED"]
        self.assertEqual(len(cleared), 3117)
        self.assertEqual(_cleared_net(self.r), D("912453.49"))
        self.assertEqual(sum((r["amount_usd"] for r in cleared), D("0")), D("924303.45"))
        self.assertGreater(len(self.r.inputs.processor), 3117)

    def test_unsettled_rows_have_no_clearing_date(self):
        unsettled = [r for r in self.r.inputs.processor if r["status"] in ("AUTHORIZED", "DECLINED")]
        self.assertEqual(len(unsettled), 45)
        self.assertEqual([r["txn_id"] for r in unsettled if r["clearing_date"] is not None], [])

    def test_mastercard_september_totals(self):
        sep = [r for r in self.r.inputs.mc_detail if _month(r["clearing_date"]) == SEPTEMBER]
        self.assertEqual(len(sep), 3109)
        self.assertEqual(_mastercard_september_net(self.r), D("896853.32"))


class V1MatchLevel(_Golden):
    """V1 / I3, match level (T2): every match and every leg-1 money difference points only at CLEARED rows."""

    def test_only_cleared_rows_carry_money(self):
        self.assertTrue(self.r.recon.matches)
        processor = {tuple(r["src"]): r for r in self.r.inputs.processor}
        for match in self.r.recon.matches:
            self.assertEqual(match.processor_row["status"], "CLEARED")
        for d in self.diffs(leg=1):
            if d.cls != "data_issue":
                for src in _src_list(d.srcs):
                    if src in processor:
                        self.assertEqual(processor[src]["status"], "CLEARED", (d.type, d.key))


# --- V2 ------------------------------------------------------------------------------------------------------------

V2_EXPECTED = {"sign_flip": D("2502.45"), "amount_diff": D("737.29"), "fx_rate_diff": D("751.93"),
               "processor_duplicate": D("3593.63"), "processor_only": D("9127.92"),
               "mastercard_only": D("-2041.36"), "month_cutoff": D("928.31")}


class V2Leg1Classes(_Golden):
    """V2 / I4: processor-Mastercard difference explained by class with zero residual (sum 15,600.17); no unmatched
    October Mastercard row leaks into any leg (closing-review reading: every leg, as before 772ab75)."""

    def test_sum_by_type(self):
        self.assertEqual({k: v for k, v in self.r.recon.leg1_by_type.items() if v != 0}, V2_EXPECTED)

    def test_zero_residual(self):
        total = sum(self.r.recon.leg1_by_type.values(), D("0"))
        self.assertEqual(total, D("15600.17"))
        self.assertEqual(_cleared_net(self.r) - _mastercard_september_net(self.r) - total, D("0"))

    def test_by_type_is_the_sum_of_differences(self):
        sums = {}
        for d in self.diffs(leg=1):
            if d.cls != "data_issue":
                sums[d.type] = sums.get(d.type, D("0")) + d.net
        self.assertEqual({k: v for k, v in sums.items() if v != 0}, V2_EXPECTED)

    def test_classes(self):
        for d in self.diffs(leg=1):
            if d.type in V2_EXPECTED:
                self.assertEqual(d.cls, "timing" if d.type == "month_cutoff" else "real_error", d.type)

    def test_fx_rate_differences_have_differing_rates(self):
        rows = {tuple(r["src"]): r for r in self.r.inputs.processor + self.r.inputs.mc_detail}
        found = self.diffs(leg=1, type_="fx_rate_diff")
        self.assertEqual(len(found), 95)
        for d in found:
            rates = {rows[s]["fx_rate"] for s in _src_list(d.srcs) if s in rows}
            self.assertEqual(len(rates), 2, d.key)

    def test_unmatched_october_mastercard_rows_are_out_of_period(self):
        matched = {tuple(m.mc_row["src"]) for m in self.r.recon.matches}
        october = {tuple(r["src"]) for r in self.r.inputs.mc_detail
                   if _month(r["clearing_date"]) == OCTOBER and tuple(r["src"]) not in matched}
        self.assertEqual(len(october), 252)
        leaked = [(d.type, d.key) for d in self.r.recon.differences if october & set(_src_list(d.srcs))]
        self.assertEqual(leaked, [])
        self.assertEqual(_october_leftovers(self.r, DATA_DIR), [])


class V2RoundingTolerance(_Planted, _Golden):
    """V2 / I4, synthetic: a pair 0.05 apart is `rounding` (auto-cleared, not an exception); residual stays zero."""

    @classmethod
    def plant(cls, data_dir):
        _shift_mc(data_dir, "MC5319429567944", D("-0.05"))  # PX10000602

    def test_rounding(self):
        found = [d for d in self.diffs(leg=1) if d.key == "PX10000602"]
        self.assertEqual([(d.type, d.cls, d.net, d.requires_explanation) for d in found],
                         [("rounding", "auto_cleared", D("0.05"), False)])
        self.assertEqual(self.r.recon.leg1_by_type.get("rounding"), D("0.05"))

    def test_residual_still_zero(self):
        total = sum(self.r.recon.leg1_by_type.values(), D("0"))
        self.assertEqual(total, D("15600.22"))
        self.assertEqual(_cleared_net(self.r) - _mastercard_september_net(self.r) - total, D("0"))


class V2SignByAmount(_Planted, _Golden):
    """V2 / I4, synthetic: sign flip is decided by the sign of amount_local, never by txn_type."""

    @classmethod
    def plant(cls, data_dir):
        _edit(data_dir, PROCESSOR, "txn_id", "PX10000606", txn_type="REFUND")       # same signs, other type
        _edit(data_dir, MC_DETAIL, "network_ref", "MC7396063819339", txn_type="PURCHASE")  # PX10000177: opposite signs

    def test_type_change_alone_is_no_difference(self):
        self.assertEqual([d.type for d in self.r.recon.differences if d.key == "PX10000606"], [])

    def test_opposite_signs_same_type_is_sign_flip(self):
        self.assertEqual([d.type for d in self.diffs(leg=1) if d.key == "PX10000177"], ["sign_flip"])
        self.assertEqual({k: v for k, v in self.r.recon.leg1_by_type.items() if v != 0}, V2_EXPECTED)


# --- V3 ------------------------------------------------------------------------------------------------------------

class V3Matching(_Golden):
    """V3 / I5: 3,108 Mastercard rows matched (3,003 exact + 45 normalised + 60 fuzzy); fuzzy matches unique."""

    def test_counts(self):
        matches = self.r.recon.matches
        by_mc = {}
        for m in matches:
            by_mc.setdefault(tuple(m.mc_row["src"]), []).append(m)
        self.assertEqual(len(by_mc), 3108)
        self.assertEqual(len({tuple(m.processor_row["src"]) for m in matches}), 3114)
        methods = {}
        for group in by_mc.values():
            original = min(group, key=lambda m: m.processor_row["txn_id"])
            methods[original.method] = methods.get(original.method, 0) + 1
        self.assertEqual(methods, {"exact": 3003, "normalised": 45, "fuzzy": 60})
        october = [g[0] for g in by_mc.values() if _month(g[0].mc_row["clearing_date"]) == OCTOBER]
        self.assertEqual(len(october), 4)

    def test_fuzzy_matches_are_unique(self):
        matches = self.r.recon.matches
        fuzzy = [m for m in matches if m.method == "fuzzy"]
        mc_uses = {}
        for m in matches:
            key = tuple(m.mc_row["src"])
            mc_uses[key] = mc_uses.get(key, 0) + 1
        for m in fuzzy:
            self.assertEqual(mc_uses[tuple(m.mc_row["src"])], 1, m.mc_row["network_ref"])
        self.assertEqual(len({tuple(m.processor_row["src"]) for m in fuzzy}), len(fuzzy))
        self.assertEqual(self.diffs(type_="ambiguous_match"), [])


class V3AmbiguousFuzzy(_Planted, _Golden):
    """V3 / I5, synthetic: a reference-less row with two equal Mastercard candidates is not matched; one
    `ambiguous_match` flag is raised instead."""

    @classmethod
    def plant(cls, data_dir):
        common = dict(clearing_date="2026-09-15", card_last4="0001", txn_currency="MXN", amount_local="12345.67",
                      fx_rate="18.9930", amount_usd="650.00", interchange_usd="10.08", scheme_fee_usd="0.85")
        _append(data_dir, PROCESSOR, [dict(common, txn_id="PX19999999", network_ref="", card_id="tok_99999",
                                           customer_id="C001", program_country="MX", merchant_name="Planted",
                                           mcc="5411", txn_type="PURCHASE", auth_date="2026-09-14",
                                           status="CLEARED")])
        _append(data_dir, MC_DETAIL, [dict(common, network_ref=ref, settlement_date="2026-09-15",
                                           merchant_descriptor="PLANTED", merchant_country="MX",
                                           txn_type="PURCHASE", net_settlement_usd="640.77")
                                      for ref in ("MC9999999999901", "MC9999999999902")])

    def test_not_matched(self):
        self.assertEqual([m.method for m in self.r.recon.matches if m.processor_row["txn_id"] == "PX19999999"], [])

    def test_one_ambiguous_flag(self):
        found = self.diffs(type_="ambiguous_match")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].cls, "data_issue")
        self.assertEqual(found[0].key, "MC9999999999901")  # the lowest candidate network_ref
        self.assertIn(_line_of(PROCESSOR, "txn_id", "PX19999999", self.data), _src_list(found[0].srcs))

    def test_residual_still_zero(self):
        # The ambiguous rows keep their money: PX19999999 processor_only (+640.77), each Mastercard row
        # mastercard_only (-640.77 twice).
        total = sum(self.r.recon.leg1_by_type.values(), D("0"))
        self.assertEqual(total, D("14959.40"))
        self.assertEqual(_cleared_net(self.r) - _mastercard_september_net(self.r) - total, D("0"))


class V3AmbiguousFuzzyMirrored(_Planted, _Golden):
    """V3 / I5, synthetic: two reference-less processor rows with one equal Mastercard candidate are not matched and
    not duplicates; one `ambiguous_match` flag cites both."""

    @classmethod
    def plant(cls, data_dir):
        common = dict(clearing_date="2026-09-16", card_last4="0002", txn_currency="MXN", amount_local="23456.78",
                      fx_rate="18.9930", amount_usd="1235.00", interchange_usd="19.14", scheme_fee_usd="1.61")
        _append(data_dir, PROCESSOR, [dict(common, txn_id=txn, network_ref="", card_id="tok_99998", customer_id="C001",
                                           program_country="MX", merchant_name="Planted", mcc="5411",
                                           txn_type="PURCHASE", auth_date="2026-09-15", status="CLEARED")
                                      for txn in ("PX19999997", "PX19999998")])
        _append(data_dir, MC_DETAIL, [dict(common, network_ref="MC9999999999903", settlement_date="2026-09-16",
                                           merchant_descriptor="PLANTED", merchant_country="MX", txn_type="PURCHASE",
                                           net_settlement_usd="1217.47")])

    def test_not_matched(self):
        planted = ("PX19999997", "PX19999998")
        self.assertEqual([m.method for m in self.r.recon.matches if m.processor_row["txn_id"] in planted], [])
        self.assertEqual([m.method for m in self.r.recon.matches if m.mc_row["network_ref"] == "MC9999999999903"], [])

    def test_flag_cites_both_and_no_duplicate(self):
        both = {_line_of(PROCESSOR, "txn_id", t, self.data) for t in ("PX19999997", "PX19999998")}
        flags = [d for d in self.diffs(type_="ambiguous_match") if both <= set(_src_list(d.srcs))]
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].key, "MC9999999999903")  # the Mastercard row both candidates share
        self.assertEqual([d.key for d in self.diffs(type_="processor_duplicate")
                          if d.key in ("PX19999997", "PX19999998")], [])

    def test_residual_still_zero(self):
        # The ambiguous rows keep their money: each processor row processor_only (+1,217.47 twice), the Mastercard row
        # mastercard_only (-1,217.47).
        total = sum(self.r.recon.leg1_by_type.values(), D("0"))
        self.assertEqual(total, D("16817.64"))
        self.assertEqual(_cleared_net(self.r) - _mastercard_september_net(self.r) - total, D("0"))


# --- V4 ------------------------------------------------------------------------------------------------------------

class V4Leg2(_Golden):
    """V4 / I1: Leg 2's only break is BS0018 (40,616.94, BNK324320124). Third repair review: leg 2 is September's, so
    the 2-Oct settlement (33,163.52, formerly pending) and the 1-Oct day leave the exceptions."""

    def test_only_break_is_the_duplicate_debit(self):
        breaks = [d for d in self.diffs(leg=2) if d.cls == "real_error"]
        self.assertEqual([(d.type, d.key) for d in breaks], [("bank_duplicate_debit", "BS0018")])
        self.assertEqual(abs(breaks[0].gross), D("40616.94"))
        self.assertIn(_line_of(BANK, "line_id", "BS0018"), _src_list(breaks[0].srcs))
        bank = [r for r in self.r.inputs.bank if r["line_id"] == "BS0018"]
        self.assertEqual(bank[0]["bank_reference"], "BNK324320124")

    def test_october_days_leave_leg_2(self):
        self.assertEqual(self.diffs(leg=2, type_="settlement_not_debited"), [])
        october = {_line_of(MC_SUMMARY, "settlement_date", day) for day in ("2026-10-01", "2026-10-02")}
        october.add(_line_of(BANK, "line_id", "BS0033"))  # the debit paying the 1-Oct day
        self.assertEqual([(d.type, d.key) for d in self.diffs(leg=2) if set(_src_list(d.srcs)) & october], [])
        self.assertEqual(sorted((d.type, d.key) for d in self.diffs(leg=2) if d.cls != "auto_cleared"),
                         [("bank_duplicate_debit", "BS0018")])


class V4DailyTolerance(_Planted, _Golden):
    """V4 / I1, synthetic: a daily net 0.80 off its bank debit is within the 1.00 tolerance; 1.20 off is a break."""

    @classmethod
    def plant(cls, data_dir):
        for ref, day, delta in (("MC2827341940727", "2026-09-08", D("0.80")),   # debited by BS0008
                                ("MC7182754365047", "2026-09-09", D("1.20"))):  # debited by BS0009
            _shift_mc(data_dir, ref, delta)
            _shift_summary(data_dir, day, delta)

    def _leg2_srcs(self):
        return [set(_src_list(d.srcs)) for d in self.diffs(leg=2) if d.cls != "auto_cleared"]

    def test_within_tolerance(self):
        watched = {_line_of(BANK, "line_id", "BS0008"), _line_of(MC_SUMMARY, "settlement_date", "2026-09-08")}
        self.assertEqual([s for s in self._leg2_srcs() if s & watched], [])

    def test_beyond_tolerance(self):
        watched = {_line_of(BANK, "line_id", "BS0009"), _line_of(MC_SUMMARY, "settlement_date", "2026-09-09")}
        found = [d for d in self.diffs(leg=2) if d.cls != "auto_cleared" and set(_src_list(d.srcs)) & watched]
        self.assertEqual([(d.type, d.cls, abs(d.gross), d.key) for d in found],
                         [("settlement_amount_diff", "real_error", D("1.20"), "BS0009")])

    def test_break_signed_bank_minus_mastercard(self):
        # Third repair review: bank 1.20 short of the raised Mastercard net -> -1.20.
        found = [(d.key, d.gross, d.net) for d in self.diffs(leg=2, type_="settlement_amount_diff")]
        self.assertEqual(found, [("BS0009", D("-1.20"), D("-1.20"))])

    def test_break_is_explained(self):
        # Readings after the repair review: UNEXPLAINED_TYPES is empty, so neither the break nor the leg-1
        # `unexplained` rows the planted shifts leave (PX10000601, PX10000722) add to the aggregate.
        self.assertEqual(self.r.recon.unexplained_total, EXPECTED_UNEXPLAINED_REAL)


def _settlements_vs_debits(result):
    return [(c.passed, c.count) for c in result.checks if c.name == "settlements_vs_debits"]


class V4Leg2LowerLimit(_Planted, _Golden):
    """Readings after the fourth repair review: leg 2 has a lower limit. A summary day is in leg 2 when its debit
    falls in September or it is a September day awaiting its debit. Planted: a 28-Aug summary day (50,000.00), whose
    debit (next working day 31-Aug) is in August's bank file -> raises nothing. The 31-Aug day, debited 1-Sep by BS0001,
    stays in leg 2 (otherwise BS0001 would be an unpaired September debit)."""

    @classmethod
    def plant(cls, data_dir):
        _append(data_dir, MC_SUMMARY, [dict(settlement_date="2026-08-28", currency="USD", txn_count="0",
                                            net_settlement_usd="50000.00")])

    def test_raises_nothing(self):
        planted = _line_of(MC_SUMMARY, "settlement_date", "2026-08-28", self.data)
        self.assertEqual([(d.type, d.key) for d in self.r.recon.differences if planted in _src_list(d.srcs)], [])
        self.assertEqual(self.diffs(type_="settlement_not_debited"), [])

    def test_leg2_unchanged(self):
        self.assertEqual(sorted((d.type, d.key) for d in self.diffs(leg=2) if d.cls != "auto_cleared"),
                         [("bank_duplicate_debit", "BS0018")])
        self.assertEqual(_settlements_vs_debits(self.r), [(True, 0)])


class V4SettlementNotDebited(_Planted, _Golden):
    """Fourth repair review, minor 1: a September day awaiting its debit. Planted: BS0031 (the 1-Oct debit paying the
    30-Sep day, 44,643.99) deleted, as in a bank file downloaded before 1-Oct -> one `settlement_not_debited` row,
    30-Sep, 44,643.99, timing, 3 working days, not escalating, Treasury fixes, Treasury (T06) answers at Clara."""

    @classmethod
    def plant(cls, data_dir):
        fields, rows = _read_rows(data_dir, BANK)
        _write_rows(data_dir, BANK, fields, [r for r in rows if r["line_id"] != "BS0031"])

    def test_one_row(self):
        found = self.diffs(type_="settlement_not_debited")
        self.assertEqual([(d.leg, d.key, d.gross, d.net, d.cls, d.age_wd, d.escalates, d.who_fixes, d.clara_owner,
                           d.task) for d in found],
                         [(2, "2026-09-30", D("44643.99"), D("44643.99"), "timing", 3, False, "Treasury", "Treasury",
                           "T06")])
        self.assertIn(_line_of(MC_SUMMARY, "settlement_date", "2026-09-30", self.data), _src_list(found[0].srcs))
        self.assertEqual(_task_role("T06", self.data), "Treasury")

    def test_action(self):
        from bridge import policy
        found = self.diffs(type_="settlement_not_debited")
        self.assertEqual([d.action for d in found], [policy.ACTION_OF["settlement_not_debited"]])
        self.assertIn("Confirm the bank debits the settlement", found[0].action)
        self.assertNotIn("next working day", found[0].action.lower())

    def test_check_counts_it(self):
        self.assertEqual(_settlements_vs_debits(self.r), [(False, 1)])

    def test_rest_of_leg2_unchanged(self):
        others = [d for d in self.diffs(leg=2) if d.cls not in ("auto_cleared", "timing")]
        self.assertEqual(sorted((d.type, d.key) for d in others), [("bank_duplicate_debit", "BS0018")])


# --- V5-V9 ---------------------------------------------------------------------------------------------------------

class V5Leg3ProcessorEntries(_Golden):
    """V5 / I1: 24-Sep processor entry missing (net 44,884.41); the 30-Sep one dated 1-Oct (45,331.47)."""

    def test_missing_entry(self):
        found = self.diffs(leg=3, type_="processor_entry_missing")
        self.assertEqual([d.key for d in found], ["PROC-20260924"])
        self.assertEqual(abs(found[0].net), D("44884.41"))
        self.assertTrue(found[0].srcs)

    def test_misdated_entry(self):
        found = self.diffs(leg=3, type_="processor_entry_misdated")
        self.assertEqual([d.key for d in found], ["PROC-20260930"])
        self.assertEqual(abs(found[0].net), D("45331.47"))
        self.assertTrue(set(_lines_of(GL_LINES, "je_id", "PF-20260930")) & set(_src_list(found[0].srcs)))


class _Unpaired:
    """Mixin for the planted unpaired-line cases (plan, readings found during implementation): exactly one difference
    carries `KEY`, with the expected (leg, type, class, abs gross, age, escalates, requires_explanation), it cites the
    planted line; the unexplained aggregate stays 0.00 (every classified difference is explained)."""

    KEY = EXPECTED = SRC_COLUMN = SRC_FILE = GROSS = None

    def test_one_difference_typed_and_aged(self):
        found = [d for d in self.r.recon.differences if d.key == self.KEY]
        self.assertEqual([(d.leg, d.type, d.cls, abs(d.gross), d.age_wd, d.escalates, d.requires_explanation)
                          for d in found], [self.EXPECTED])
        self.assertIn(_line_of(self.SRC_FILE, self.SRC_COLUMN, self.KEY, self.data), _src_list(found[0].srcs))

    def test_explained(self):
        self.assertEqual(self.r.recon.unexplained_total, EXPECTED_UNEXPLAINED_REAL)
        self.assertIs(self.r.recon.unexplained_escalates, False)


class V5BankLineUnrecorded(_Unpaired, _Planted, _Golden):
    """V5 / I1, synthetic: a bridge-account bank line with no ledger entry is `bank_line_unrecorded` (real error,
    keyed by line_id, aged from the bank date: 24-Sep -> 7 working days)."""

    KEY, SRC_FILE, SRC_COLUMN, GROSS = "BS9001", BANK, "line_id", D("1250.00")
    EXPECTED = (3, "bank_line_unrecorded", "real_error", D("1250.00"), 7, True, True)

    @classmethod
    def plant(cls, data_dir):
        _append(data_dir, BANK, [dict(line_id="BS9001", posting_date="2026-09-24", value_date="2026-09-24",
                                      narrative="WIRE OUT REF 90001 VENDOR PAYMENT", bank_reference="WIR90001",
                                      debit_usd="1250.00", running_balance_usd="1467495.90")])


class V5LedgerEntryUnmatched(_Unpaired, _Planted, _Golden):
    """V5 / I1, synthetic: a manual bridge-account ledger entry with no bank line is `ledger_entry_unmatched` (real
    error, keyed by the entry's je_id since the readings after the second repair review, aged from the entry date:
    25-Sep -> 6 working days)."""

    KEY, SRC_FILE, SRC_COLUMN, GROSS = "MJ-90002", GL_LINES, "je_id", D("310.00")
    EXPECTED = (3, "ledger_entry_unmatched", "real_error", D("310.00"), 6, True, True)

    @classmethod
    def plant(cls, data_dir):
        common = dict(je_id="MJ-90002", posting_date="2026-09-25", source="MANUAL", reference="MAN90002",
                      description="Manual: bank charge adjustment")
        _append(data_dir, GL_LINES, [
            dict(common, account="6150", account_name="Bank Charges", debit_usd="310.00", credit_usd="0.0"),
            dict(common, account="1110", account_name="Bridge Account Cash (USD)", debit_usd="0.0",
                 credit_usd="310.00")])


class V4SettlementDebitUnpaired(_Unpaired, _Planted, _Golden):
    """V4 / I1, synthetic: a settlement debit no summary day pairs with (posted on the 7-Sep holiday, recorded in the
    ledger) is `settlement_amount_diff` with the whole debit as gross; aged 20 working days."""

    KEY, SRC_FILE, SRC_COLUMN, GROSS = "BS9003", BANK, "line_id", D("2000.00")
    EXPECTED = (2, "settlement_amount_diff", "real_error", D("2000.00"), 20, True, True)

    @classmethod
    def plant(cls, data_dir):
        _append(data_dir, BANK, [dict(line_id="BS9003", posting_date="2026-09-07", value_date="2026-09-07",
                                      narrative="MC SETTL 0709 USD NET REF 9003", bank_reference="BNK900300003",
                                      debit_usd="2000.00", running_balance_usd="1466745.90")])
        common = dict(je_id="BK-BS9003", posting_date="2026-09-07", source="BANK_FEED", reference="BNK900300003",
                      description="Bank feed: MC SETTL 0709 USD NET REF 9003")
        _append(data_dir, GL_LINES, [
            dict(common, account="2105", account_name="Mastercard Settlement Payable", debit_usd="2000.00",
                 credit_usd="0.0"),
            dict(common, account="1110", account_name="Bridge Account Cash (USD)", debit_usd="0.0",
                 credit_usd="2000.00")])


LEG3_LEFTOVER_TYPES = ("ledger_amount_diff", "bank_line_unrecorded", "ledger_entry_unmatched")


def _cash_check(result):
    found = [c for c in result.checks if c.name == "cash_reconciled"]
    assert len(found) == 1, [c.name for c in result.checks]
    return found[0]


class V5Leg3PairsByAmount(_Golden):
    """V5 / I1, closing-review reading: leg 3 pairs bank lines with ledger entries by reference and amount, one to
    one. On the case data every line pairs; the only pair dated apart is the funding in transit (BS0032, TRF0930)."""

    def test_nothing_left_over(self):
        self.assertEqual([(d.type, d.key) for t in LEG3_LEFTOVER_TYPES for d in self.diffs(type_=t)], [])

    def test_funding_in_transit_unchanged(self):
        found = self.diffs(leg=3, type_="funding_in_transit")
        self.assertEqual([(d.key, abs(d.gross), d.cls) for d in found], [("BS0032", D("400000.00"), "timing")])
        expected = {_line_of(BANK, "line_id", "BS0032")} | set(_lines_of(GL_LINES, "je_id", "TR-20260930"))
        self.assertEqual(expected - set(_src_list(found[0].srcs)), set())


class V5LedgerAmountDiff(_Unpaired, _Planted, _Golden):
    """V5 / I1, synthetic: the ledger posts BS0029 at 53,896.40 instead of 53,986.40 (both lines of BK-BS0029). Same
    reference, different amount: one `ledger_amount_diff` keyed by the bank line, gross 90.00, aged from 30-Sep (3
    working days), unexplained; cash does not tie by 90.00 and the cash check fails."""

    KEY, SRC_FILE, SRC_COLUMN, GROSS = "BS0029", BANK, "line_id", D("90.00")
    EXPECTED = (3, "ledger_amount_diff", "real_error", D("90.00"), 3, False, False)

    @classmethod
    def plant(cls, data_dir):
        fields, rows = _read_rows(data_dir, GL_LINES)
        for row in rows:
            if row["je_id"] == "BK-BS0029":
                row["debit_usd" if row["debit_usd"] != "0.0" else "credit_usd"] = "53896.40"
        _write_rows(data_dir, GL_LINES, fields, rows)

    def test_cites_the_ledger_lines(self):
        found = self.diffs(type_="ledger_amount_diff")
        self.assertEqual(len(found), 1)
        self.assertEqual(set(_lines_of(GL_LINES, "je_id", "BK-BS0029", self.data)) - set(_src_list(found[0].srcs)),
                         set())

    def test_no_other_leftover(self):
        self.assertEqual([(d.type, d.key) for t in ("bank_line_unrecorded", "ledger_entry_unmatched")
                          for d in self.diffs(type_=t)], [])

    def test_type_is_explained(self):
        from bridge import policy
        self.assertNotIn("ledger_amount_diff", policy.UNEXPLAINED_TYPES)
        self.assertEqual(policy.FIXER_OF["ledger_amount_diff"], "Finance Ops")

    def test_signed_ledger_minus_bank(self):
        # Second repair review: ledger (-53,896.40 on 1110) minus bank (-53,986.40) = +90.00, the unreconciled sign.
        self.assertEqual([(d.key, d.gross, d.net) for d in self.diffs(type_="ledger_amount_diff")],
                         [("BS0029", D("90.00"), D("90.00"))])

    def test_cash_does_not_tie(self):
        self.assertEqual(_field(self.r.close.cash_recon, "unreconciled"), D("90.00"))
        check = _cash_check(self.r)
        self.assertEqual((check.passed, check.count), (False, 1))


class V5DuplicateDebitUnrecorded(_Planted, _Golden):
    """V5 / I1, synthetic: the two lines of BK-BS0018 deleted. Two bank lines share BNK324320124 and one ledger entry
    remains, so BS0018 is `bank_line_unrecorded` (40,616.94, 21-Sep: 10 working days) owned like the duplicate, and
    still the leg-2 `bank_duplicate_debit` (plan a83fd8a: both rows stay); its entry claims the debit the bank made (Dr
    1250 / Cr 1110), so cash after all entries is the bank balance plus the funding in transit."""

    @classmethod
    def plant(cls, data_dir):
        fields, rows = _read_rows(data_dir, GL_LINES)
        _write_rows(data_dir, GL_LINES, fields, [r for r in rows if r["je_id"] != "BK-BS0018"])

    def test_bank_line_unrecorded(self):
        found = self.diffs(type_="bank_line_unrecorded")
        self.assertEqual([(d.leg, d.key, d.cls, abs(d.gross), d.age_wd, d.escalates, d.requires_explanation)
                          for d in found], [(3, "BS0018", "real_error", D("40616.94"), 10, True, True)])
        self.assertIn(_line_of(BANK, "line_id", "BS0018", self.data), _src_list(found[0].srcs))
        self.assertEqual(self.r.recon.unexplained_total, EXPECTED_UNEXPLAINED_REAL)

    def test_both_rows_with_the_duplicates_owner(self):
        # Third repair review: the unrecorded half takes the duplicate's fixer (Mastercard), Clara owner (T06's
        # owner_role, Treasury) and action.
        from bridge import policy
        three = ("Mastercard", _task_role("T06", self.data), policy.ACTION_OF["bank_duplicate_debit"])
        found = sorted((d.leg, d.type, d.who_fixes, d.clara_owner, d.action) for d in self.r.recon.differences
                       if d.key == "BS0018")
        self.assertEqual(found, [(2, "bank_duplicate_debit") + three, (3, "bank_line_unrecorded") + three])
        rows = [r for r in _read_rows(_run_on(self.data), "exceptions.csv")[1] if r["key"] == "BS0018"]
        self.assertEqual(sorted((r["type"], r["who_fixes"], r["clara_owner"], r["action"]) for r in rows),
                         [("bank_duplicate_debit",) + three, ("bank_line_unrecorded",) + three])

    def test_entry_claims_the_bank_debit(self):
        found = [e for e in self.r.close.entries
                 if any(str(a) == "1250" and dr == D("40616.94") for a, dr, _c in e.lines)]
        self.assertEqual(len(found), 1)
        self.assertEqual(sorted((str(a), dr, cr) for a, dr, cr in found[0].lines),
                         [("1110", D("0"), D("40616.94")), ("1250", D("40616.94"), D("0"))])

    def test_cash_after_all_is_bank_plus_transit(self):
        cash = self.r.close.cash_recon
        self.assertEqual(_balances(self.r)["1110"]["after_all"], _field(cash, "bank_balance") + D("400000.00"))
        self.assertEqual(_balances(self.r)["1110"]["after_all"], D("1547965.55"))

    def test_cash_does_not_tie(self):
        self.assertEqual(_field(self.r.close.cash_recon, "unreconciled"), D("40616.94"))
        check = _cash_check(self.r)
        self.assertEqual((check.passed, check.count), (False, 1))


class V5InvoiceAlreadyAccrued(_Planted, _Golden):
    """Minor repairs, synthetic: the ledger already accrues the Mastercard program invoice in September (Dr 5100 /
    Cr 2150 8,412.30 on 30-Sep), so nothing is raised and no second accrual is proposed."""

    @classmethod
    def plant(cls, data_dir):
        common = dict(je_id="AC-90012", posting_date="2026-09-30", source="MANUAL", reference="ACR-2609-4471",
                      description="Accrual: Mastercard program invoice 2609-4471")
        _append(data_dir, GL_LINES, [
            dict(common, account="5100", account_name="Network Fees", debit_usd="8412.30", credit_usd="0.0"),
            dict(common, account="2150", account_name="Accrued Network Fees", debit_usd="0.0", credit_usd="8412.30")])

    def test_not_raised(self):
        self.assertEqual(self.diffs(type_="invoice_not_accrued"), [])

    def test_no_second_accrual(self):
        self.assertEqual([e.id for e in self.r.close.entries if any(str(a) == "2150" for a, _dr, _cr in e.lines)], [])
        self.assertEqual(len(self.r.close.entries), 10)
        self.assertEqual((_balances(self.r)["2150"]["before"], _balances(self.r)["2150"]["after_all"]),
                         (D("-8412.30"), D("-8412.30")))


class V5AccountUnmapped(_Planted, _Golden):
    """Minor repairs, synthetic: a ledger entry on accounts outside the eleven (9998 / 9999, 75.00) is one
    `account_unmapped` data-issue flag keyed by its je_id on leg 3, carrying no money, never dropped in silence."""

    @classmethod
    def plant(cls, data_dir):
        common = dict(je_id="MJ-90011", posting_date="2026-09-25", source="MANUAL", reference="MAN90011",
                      description="Manual: reclass to an unmapped account")
        _append(data_dir, GL_LINES, [
            dict(common, account="9998", account_name="Unmapped A", debit_usd="75.00", credit_usd="0.0"),
            dict(common, account="9999", account_name="Unmapped B", debit_usd="0.0", credit_usd="75.00")])

    def test_one_flag(self):
        found = self.diffs(type_="account_unmapped")
        self.assertEqual([(d.leg, d.key, d.cls, d.gross, d.net, d.age_wd, d.escalates) for d in found],
                         [(3, "MJ-90011", "data_issue", D("0.00"), D("0.00"), 0, False)])
        self.assertEqual(set(_lines_of(GL_LINES, "je_id", "MJ-90011", self.data)) - set(_src_list(found[0].srcs)),
                         set())

    def test_case_data_has_none(self):
        self.assertEqual(_Golden.diffs(self, type_="account_unmapped", result=_result()), [])


# --- Readings after the repair review: cut-off, leftovers, cash ---------------------------------------------------

def _edit_entry(data_dir, je_id, **changes):
    """Applies `changes` to every ledger line of one entry; an amount change rewrites whichever side is non-zero."""
    fields, rows = _read_rows(data_dir, GL_LINES)
    hits = [r for r in rows if r["je_id"] == je_id]
    assert hits, je_id
    for r in hits:
        for column, value in changes.items():
            if column == "amount":
                r["debit_usd" if D(r["debit_usd"] or "0") else "credit_usd"] = value
            else:
                r[column] = value
    _write_rows(data_dir, GL_LINES, fields, rows)


def _drop_entry(data_dir, je_id):
    fields, rows = _read_rows(data_dir, GL_LINES)
    _write_rows(data_dir, GL_LINES, fields, [r for r in rows if r["je_id"] != je_id])


def _october_leftovers(result, data_dir):
    """Leg-3 cash leftovers (unrecorded, unmatched, amount difference) that cite only bank or ledger lines dated after
    30-Sep: an October leftover is October's, not a September exception."""
    october = set()
    for file_name in (BANK, GL_LINES):
        _fields, rows = _read_rows(data_dir, file_name)
        october |= {(file_name, line) for line, r in enumerate(rows, start=2) if r["posting_date"] > "2026-09-30"}
    return [(d.type, d.key) for d in result.recon.differences
            if d.type in LEG3_LEFTOVER_TYPES and set(_src_list(d.srcs)) <= october]


CROSSING_TYPES = ("funding_in_transit", "bank_not_yet_posted", "ledger_posted_late")
FUNDING_ROW = ("funding_in_transit", "BS0032", D("400000.00"))


class _CashCase:
    """Mixin for the planted cash cases: the signed reconciling items (ledger's September effect on 1110 minus the
    bank's), the unreconciled figure and the leg-3 leftovers, as (type, key, abs gross). Readings after the second
    repair review: every cut-off-crossing pair also has one exception row (CROSSING, as (type, bank line_id, signed
    gross)) carrying its matched part signed like the item (plan 18b2a25); in every case below the matched part is
    the whole item."""

    ITEMS = UNRECONCILED = LEFTOVERS = CROSSING = None

    def test_items_signed(self):
        items = _field(self.r.close.cash_recon, "reconciling_items")
        self.assertEqual(sorted(_field(i, "amount") for i in items), sorted(self.ITEMS))

    def test_unreconciled(self):
        self.assertEqual(_field(self.r.close.cash_recon, "unreconciled"), self.UNRECONCILED)
        self.assertEqual(_cash_check(self.r).passed, self.UNRECONCILED == 0)

    def test_leftovers(self):
        found = [(d.type, d.key, abs(d.gross)) for t in LEG3_LEFTOVER_TYPES for d in self.diffs(type_=t)]
        self.assertEqual(sorted(found), sorted(self.LEFTOVERS))

    def test_no_october_leftover(self):
        self.assertEqual(_october_leftovers(self.r, self.data), [])

    def test_crossing_rows(self):
        found = [(d.type, d.key, d.gross) for t in CROSSING_TYPES for d in self.diffs(type_=t)]
        self.assertEqual(sorted(found), sorted(self.CROSSING))
        self.assertEqual([(d.type, d.key) for t in CROSSING_TYPES for d in self.diffs(type_=t)
                          if (d.leg, d.net) != (3, d.gross)], [])

    def test_one_row_per_item_same_signed_amount(self):
        rows = [d.gross for t in CROSSING_TYPES for d in self.diffs(type_=t)]
        self.assertEqual(sorted(rows), sorted(self.ITEMS))


class CashCutoffSameMonthSeptember(_CashCase, _Planted, _Golden):
    """In transit only across the cut-off: BK-BS0027 posted 28-Sep, its bank line 29-Sep, both September -> matched,
    no item, cash ties."""

    ITEMS, UNRECONCILED, LEFTOVERS, CROSSING = [D("400000.00")], D("0.00"), [], [FUNDING_ROW]

    @classmethod
    def plant(cls, data_dir):
        _edit_entry(data_dir, "BK-BS0027", posting_date="2026-09-28")


class CashCutoffSameMonthOctober(_CashCase, _Planted, _Golden):
    """In transit only across the cut-off: BK-BS0033 posted 1-Oct, its bank line 2-Oct, both October -> no item."""

    ITEMS, UNRECONCILED, LEFTOVERS, CROSSING = [D("400000.00")], D("0.00"), [], [FUNDING_ROW]

    @classmethod
    def plant(cls, data_dir):
        _edit_entry(data_dir, "BK-BS0033", posting_date="2026-10-01")


class CashCutoffLedgerFirst(_CashCase, _Planted, _Golden):
    """Across the cut-off, ledger first: BS0031's posting (BK-BS0031) on 30-Sep, bank 1-Oct -> item -44,643.99 (the
    ledger's September credit to cash), "in the ledger, not yet in the bank"; ledger 1,503,321.56, cash ties."""

    ITEMS, UNRECONCILED, LEFTOVERS = [D("400000.00"), D("-44643.99")], D("0.00"), []
    # Second repair review: BS0031 is a settlement debit, not funding -> bank_not_yet_posted, signed like its item.
    CROSSING = [FUNDING_ROW, ("bank_not_yet_posted", "BS0031", D("-44643.99"))]

    @classmethod
    def plant(cls, data_dir):
        _edit_entry(data_dir, "BK-BS0031", posting_date="2026-09-30")

    def test_direction(self):
        items = {_field(i, "amount"): _field(i, "description").lower()
                 for i in _field(self.r.close.cash_recon, "reconciling_items")}
        self.assertIn("in the ledger, not yet in the bank", items[D("-44643.99")])
        self.assertEqual(_field(self.r.close.cash_recon, "ledger_balance"), D("1503321.56"))


class CashCutoffBankFirst(_CashCase, _Planted, _Golden):
    """Across the cut-off, bank first: BK-BS0029 posted 1-Oct, its bank line 30-Sep -> item +53,986.40, "in the bank,
    not yet in the ledger"; ledger 1,601,951.95, cash ties."""

    ITEMS, UNRECONCILED, LEFTOVERS = [D("400000.00"), D("53986.40")], D("0.00"), []
    # Second repair review: a September bank movement booked in October is ledger_posted_late, signed like its item.
    CROSSING = [FUNDING_ROW, ("ledger_posted_late", "BS0029", D("53986.40"))]

    @classmethod
    def plant(cls, data_dir):
        _edit_entry(data_dir, "BK-BS0029", posting_date="2026-10-01")

    def test_direction(self):
        items = {_field(i, "amount"): _field(i, "description").lower()
                 for i in _field(self.r.close.cash_recon, "reconciling_items")}
        self.assertIn("in the bank, not yet in the ledger", items[D("53986.40")])
        self.assertEqual(_field(self.r.close.cash_recon, "ledger_balance"), D("1601951.95"))


class OctoberLeftoverRaisesNothing(_CashCase, _Planted, _Golden):
    """Only September leftovers are September exceptions: BK-BS0033 deleted leaves the 2-Oct bank line BS0033 without
    a posting; nothing is raised for it and September cash still ties."""

    ITEMS, UNRECONCILED, LEFTOVERS, CROSSING = [D("400000.00")], D("0.00"), [], [FUNDING_ROW]

    @classmethod
    def plant(cls, data_dir):
        _drop_entry(data_dir, "BK-BS0033")

    def test_nothing_cites_bs0033_on_leg_3(self):
        line = _line_of(BANK, "line_id", "BS0033", self.data)
        self.assertEqual([(d.type, d.key) for d in self.diffs(leg=3) if line in _src_list(d.srcs)], [])


class LeftoversTwoBankLinesOneEntry(_CashCase, _Planted, _Golden):
    """Leftovers pair per reference: BK-BS0018 deleted and BK-BS0016 posted at 40,606.94. BNK324320124 keeps two bank
    lines (BS0016, BS0018) and one entry -> ledger_amount_diff BS0016 10.00 and bank_line_unrecorded BS0018
    40,616.94; together they are the 40,626.94 cash does not tie by."""

    ITEMS, UNRECONCILED, CROSSING = [D("400000.00")], D("40626.94"), [FUNDING_ROW]
    LEFTOVERS = [("ledger_amount_diff", "BS0016", D("10.00")), ("bank_line_unrecorded", "BS0018", D("40616.94"))]

    def test_amount_difference_signed(self):
        # Second repair review: ledger (-40,606.94) minus bank (-40,616.94) = +10.00.
        self.assertEqual([(d.key, d.gross) for d in self.diffs(type_="ledger_amount_diff")], [("BS0016", D("10.00"))])

    @classmethod
    def plant(cls, data_dir):
        _drop_entry(data_dir, "BK-BS0018")
        _edit_entry(data_dir, "BK-BS0016", amount="40606.94")


class LeftoverBankFeedEntry(_Planted, _Golden):
    """Leftovers include bank-feed entries: BK-BS0028 posted twice (copy BK-BS0028X) -> one ledger_entry_unmatched of
    465.00 citing one of the two postings; cash is off by -465.00 and that row says why."""

    @classmethod
    def plant(cls, data_dir):
        fields, rows = _read_rows(data_dir, GL_LINES)
        _write_rows(data_dir, GL_LINES, fields,
                    rows + [dict(r, je_id="BK-BS0028X") for r in rows if r["je_id"] == "BK-BS0028"])

    def test_one_unmatched_entry(self):
        found = self.diffs(type_="ledger_entry_unmatched")
        self.assertEqual([(d.leg, abs(d.gross)) for d in found], [(3, D("465.00"))])
        postings = [set(_lines_of(GL_LINES, "je_id", je, self.data)) for je in ("BK-BS0028", "BK-BS0028X")]
        self.assertTrue(any(p <= set(_src_list(found[0].srcs)) for p in postings))
        # Second repair review: labelled by its je_id; pairing in (date, je_id) order leaves the copy over.
        self.assertEqual(found[0].key, "BK-BS0028X")
        self.assertTrue(postings[1] <= set(_src_list(found[0].srcs)))
        self.assertEqual(self.diffs(type_="bank_line_unrecorded") + self.diffs(type_="ledger_amount_diff"), [])

    def test_cash_off_by_the_duplicate(self):
        self.assertEqual(_field(self.r.close.cash_recon, "unreconciled"), D("-465.00"))


class LeftoverAmountAcrossCutoff(_CashCase, _Planted, _Golden):
    """A ledger_amount_diff pair across the cut-off keeps its in-transit item: the treasury transfer posted at
    399,000.00 on 30-Sep, the bank receives 400,000.00 on 1-Oct (BS0032) -> ledger_amount_diff 1,000.00 and item
    +399,000.00; ledger 1,546,965.55, cash ties."""

    ITEMS, UNRECONCILED = [D("399000.00")], D("0.00")
    LEFTOVERS = [("ledger_amount_diff", "BS0032", D("1000.00"))]
    # Plan 18b2a25: the crossing row carries the matched part (399,000.00) signed like the item, beside the difference
    # row (-1,000.00). Ledger first, the September side is the ledger, so the matched part is the whole item here.
    CROSSING = [("funding_in_transit", "BS0032", D("399000.00"))]

    def test_matched_part_and_difference(self):
        found = sorted((d.type, d.key, d.gross) for t in ("funding_in_transit", "ledger_amount_diff")
                       for d in self.diffs(leg=3, type_=t))
        self.assertEqual(found, [("funding_in_transit", "BS0032", D("399000.00")),
                                 ("ledger_amount_diff", "BS0032", D("-1000.00"))])

    def test_amount_difference_signed(self):
        # Ledger (+399,000.00 on 1110) minus bank (+400,000.00) = -1,000.00.
        self.assertEqual([(d.key, d.gross, d.net) for d in self.diffs(type_="ledger_amount_diff")],
                         [("BS0032", D("-1000.00"), D("-1000.00"))])

    @classmethod
    def plant(cls, data_dir):
        _edit_entry(data_dir, "TR-20260930", amount="399000.00")

    def test_aged_from_the_september_side(self):
        # Third repair review: a crossing pair's ledger_amount_diff is aged from the September side like its crossing
        # row (ledger 30-Sep -> 3 working days to 5-Oct; it was the bank's 1-Oct, 2 working days).
        found = self.diffs(type_="ledger_amount_diff")
        self.assertEqual([(d.origin, d.age_wd, d.escalates, d.requires_explanation) for d in found],
                         [(datetime.date(2026, 9, 30), 3, False, True)])


class BankBalanceByDate(_Planted, _Golden):
    """Minor: the 30-Sep bank balance is the last line by (posting_date, line_id), not file order. BS0001 moved to the
    end of the statement file; the balance is still BS0029's 1,147,965.55 and cash ties."""

    @classmethod
    def plant(cls, data_dir):
        fields, rows = _read_rows(data_dir, BANK)
        _write_rows(data_dir, BANK, fields, rows[1:] + rows[:1])

    def test_bank_balance(self):
        cash = self.r.close.cash_recon
        self.assertEqual(_field(cash, "bank_balance"), D("1147965.55"))
        self.assertEqual(_src_list(_field(cash, "bank_src")), [_line_of(BANK, "line_id", "BS0029", self.data)])
        self.assertEqual(_field(cash, "unreconciled"), D("0.00"))


V6_EXPECTED = {"1110": D("1547965.55"), "1210": D("4245795.36"), "1250": D("0"), "2105": D("70588.66"),
               "2150": D("0"), "2300": D("-6100000.00"), "2900": D("-12500.00"), "4100": D("-13571.56"),
               "5100": D("2894.36"), "6150": D("465.00"), "3900": D("258362.63")}


class V6BalancesBefore(_Golden):
    """V6 / I1: ledger balances at 30-Sep for the eleven accounts, debit positive, each sourced; sum 0."""

    def test_before(self):
        balances = _balances()
        self.assertEqual(sorted(balances), sorted(ACCOUNTS))
        self.assertEqual({k: v["before"] for k, v in balances.items()}, V6_EXPECTED)
        self.assertEqual(sum((v["before"] for v in balances.values()), D("0")), D("0"))

    def test_source_is_the_opening_row(self):
        for account, row in _balances().items():
            self.assertIn(_line_of(GL_OPENING, "account", account), _src_list(row["src"]), account)


class V7AfterAll(_Golden):
    """V7 / I2: balances after confirmed plus conditional entries; unchanged accounts stay; sum 0."""

    CHANGED = {"1210": D("4309799.60"), "1250": D("40616.94"), "2105": D("-45572.30"), "2150": D("-8412.30"),
               "2900": D("0.00"), "4100": D("-14828.29"), "5100": D("11603.17")}

    def test_after_all(self):
        balances = _balances()
        for account in ACCOUNTS:
            self.assertEqual(balances[account]["after_all"], self.CHANGED.get(account, V6_EXPECTED[account]), account)
        self.assertEqual(sum((v["after_all"] for v in balances.values()), D("0")), D("0"))

    def test_after_all_is_before_plus_every_entry(self):
        balances = _balances()
        deltas = _account_deltas(self.r.close.entries)
        for account in ACCOUNTS:
            self.assertEqual(balances[account]["after_all"],
                             balances[account]["before"] + deltas.get(account, D("0")), account)


class V7bAfterConfirmed(_Golden):
    """V7b / I12: a conditional entry never appears in the "confirmed only" column."""

    CHANGED = {"1210": D("4331559.00"), "1250": D("40616.94"), "2105": D("-54700.22"), "2150": D("-8412.30"),
               "2900": D("-12500.00"), "4100": D("-14971.81"), "5100": D("11615.21")}

    def test_after_confirmed(self):
        balances = _balances()
        for account in ACCOUNTS:
            self.assertEqual(balances[account]["after_confirmed"],
                             self.CHANGED.get(account, V6_EXPECTED[account]), account)
        self.assertEqual(sum((v["after_confirmed"] for v in balances.values()), D("0")), D("0"))

    def test_after_confirmed_excludes_conditional_entries(self):
        balances = _balances()
        deltas = _account_deltas([e for e in self.r.close.entries if e.status == "proposed"])
        for account in ACCOUNTS:
            self.assertEqual(balances[account]["after_confirmed"],
                             balances[account]["before"] + deltas.get(account, D("0")), account)

    def test_conditional_entries_carry_their_missing_evidence(self):
        for entry in self.r.close.entries:
            if entry.status == "proposed-conditional":
                self.assertTrue(entry.missing_evidence, entry.id)
            else:
                self.assertIsNone(entry.missing_evidence, entry.id)


def _level(total_debits):
    if total_debits >= D("100000"):
        return "cfo"
    if total_debits >= D("10000"):
        return "controller"
    return "standard"


class V8Entries(_Golden):
    """V8 / I2, I11: every entry balanced, proposed only, approval level by total debits, preparer/approver empty."""

    def find(self, account, debit):
        found = [e for e in self.r.close.entries if any(str(a) == account and dr == debit for a, dr, _cr in e.lines)]
        self.assertEqual(len(found), 1, "entry with Dr %s %s" % (account, debit))
        return found[0]

    def test_closed_list(self):
        # Items 1-5 of spec E4 plus one item-6 entry for each of the six processor error types.
        self.assertEqual(len(self.r.close.entries), 11)
        self.assertEqual(len([e for e in self.r.close.entries if e.status == "proposed-conditional"]), 2)

    def test_every_entry(self):
        for e in self.r.close.entries:
            with self.subTest(entry=e.id):
                for _account, debit, credit in e.lines:
                    self.assertTrue(debit >= 0 and credit >= 0 and (debit == 0) != (credit == 0), (debit, credit))
                debits = sum((dr for _a, dr, _cr in e.lines), D("0"))
                credits = sum((cr for _a, _dr, cr in e.lines), D("0"))
                self.assertEqual(debits, credits)
                self.assertGreater(debits, D("0"))
                self.assertEqual(e.total_debits, debits)
                self.assertIn(e.status, ("proposed", "proposed-conditional"))
                self.assertEqual(e.approval_level, _level(e.total_debits))
                self.assertEqual((e.preparer, e.approver), ("", ""))
                self.assertTrue(e.srcs)

    def test_known_entries(self):
        duplicate = self.find("1250", D("40616.94"))
        self.assertEqual(sorted((str(a), dr, cr) for a, dr, cr in duplicate.lines),
                         [("1250", D("40616.94"), D("0")), ("2105", D("0"), D("40616.94"))])
        self.assertEqual((duplicate.status, duplicate.approval_level), ("proposed", "controller"))
        suspense = self.find("2900", D("12500.00"))
        self.assertEqual(sorted((str(a), dr, cr) for a, dr, cr in suspense.lines),
                         [("1210", D("0"), D("12500.00")), ("2900", D("12500.00"), D("0"))])
        self.assertEqual((suspense.status, suspense.approval_level), ("proposed-conditional", "controller"))
        invoice = [e for e in self.r.close.entries if any(str(a) == "2150" for a, _dr, _cr in e.lines)]
        self.assertEqual(len(invoice), 1)
        self.assertEqual(sum((dr for a, dr, _cr in invoice[0].lines if str(a) == "5100"), D("0")), D("8412.30"))
        self.assertEqual(sum((cr for a, _dr, cr in invoice[0].lines if str(a) == "2150"), D("0")), D("8412.30"))
        self.assertEqual((invoice[0].status, invoice[0].approval_level), ("proposed", "standard"))


class V8bRequiresExplanation(_Golden):
    """V8b / I1: PX10002115 requires explanation on gross 253.05 although its net is 249.45."""

    def test_px10002115(self):
        found = [d for d in self.diffs(leg=1) if d.key == "PX10002115"]
        self.assertEqual(len(found), 1)
        d = found[0]
        self.assertEqual((d.type, d.gross, d.net, d.requires_explanation), ("amount_diff", D("253.05"), D("249.45"), True))
        self.assertIn(_line_of(PROCESSOR, "txn_id", "PX10002115"), _src_list(d.srcs))

    def test_threshold_is_on_gross(self):
        for d in self.diffs(leg=1):
            if d.cls in MONEY_CLASSES:
                self.assertEqual(d.requires_explanation, abs(d.gross) >= D("250"), d.key)


class V8cEscalation(_Golden):
    """V8c: escalation rules of spec E1/E3 at the cut-off 2026-10-05 — by age (> 5 working days) for every money
    difference on all legs, and separately by the unexplained aggregate (> 1,000). No invariant of I1-I12 covers
    escalation; the spec lists I7 for this row only because the values come from policy."""

    # type: (escalating, total) among leg-1 money differences
    LEG1 = {"sign_flip": (3, 4), "amount_diff": (8, 8), "processor_duplicate": (5, 6), "processor_only": (3, 3),
            "mastercard_only": (4, 5), "fx_rate_diff": (95, 95), "month_cutoff": (0, 4)}
    ESCALATING = {"bank_duplicate_debit": 10, "suspense_pending_payer": 8, "processor_entry_missing": 7}
    # settlement_not_debited left the case data with the third repair review (leg 2 is September's).
    NOT_ESCALATING = ["processor_entry_misdated", "funding_in_transit", "invoice_not_accrued"]

    def test_leg1_counts_by_type(self):
        counts = {}
        for d in self.diffs(leg=1):
            if d.cls in MONEY_CLASSES:
                escalating, total = counts.get(d.type, (0, 0))
                counts[d.type] = (escalating + int(d.escalates), total + 1)
        self.assertEqual(counts, self.LEG1)

    def test_named_items_escalate_with_their_age(self):
        for type_, age in self.ESCALATING.items():
            with self.subTest(type=type_):
                self.assertEqual([(d.age_wd, d.escalates) for d in self.diffs(type_=type_)], [(age, True)])
        self.assertEqual(abs(self.diffs(type_="suspense_pending_payer")[0].gross), D("12500.00"))

    def test_named_items_do_not_escalate(self):
        for type_ in self.NOT_ESCALATING:
            with self.subTest(type=type_):
                found = self.diffs(type_=type_)
                self.assertTrue(found)
                self.assertEqual([d.escalates for d in found], [False] * len(found))

    def test_escalation_is_age_over_five_for_money_differences(self):
        for d in self.r.recon.differences:
            if d.cls in MONEY_CLASSES:
                self.assertEqual(d.escalates, d.age_wd > 5, (d.type, d.key, d.age_wd))

    def test_age_skips_the_september_7_holiday(self):
        # PX10000177 clears 2026-09-02: 22 working days to 2026-10-05 with 7-Sep off, 23 without.
        self.assertEqual([d.age_wd for d in self.diffs(leg=1) if d.key == "PX10000177"], [22])

    def test_unexplained_aggregate(self):
        from bridge import policy
        listed = sum((abs(d.gross) for d in self.r.recon.differences if d.type in policy.UNEXPLAINED_TYPES), D("0"))
        self.assertEqual(self.r.recon.unexplained_total, EXPECTED_UNEXPLAINED_REAL)
        self.assertEqual(listed, EXPECTED_UNEXPLAINED_REAL)
        self.assertIs(self.r.recon.unexplained_escalates, EXPECTED_UNEXPLAINED_REAL > D("1000"))


class V8cControllerAction(_Golden):
    """V8c: every real error (processor-only and Mastercard-only among them) is flagged for the Controller's action,
    whatever its age (Andrés, 2026-10-14, readings after the repair review)."""

    def test_flagged_types(self):
        flagged = {}
        for d in self.r.recon.differences:
            if d.controller_action:
                flagged[d.type] = flagged.get(d.type, 0) + 1
        self.assertEqual(flagged, {"sign_flip": 4, "amount_diff": 8, "fx_rate_diff": 95, "processor_duplicate": 6,
                                   "processor_only": 3, "mastercard_only": 5, "bank_duplicate_debit": 1,
                                   "processor_entry_missing": 1, "invoice_not_accrued": 1})

    def test_regardless_of_age(self):
        found = self.diffs(type_="mastercard_only") + self.diffs(type_="processor_only")
        self.assertEqual([d.key for d in found if not d.controller_action], [])
        self.assertTrue([d for d in found if d.age_wd <= 5])


class V8cUnexplainedAggregate(_Planted, _Golden):
    """V8c / I4, synthetic: a matched pair whose USD differs with the same local amount and rate is
    `usd_conversion_error` (renamed from `unexplained` after the second repair review; real error, counted in
    leg1_by_type, residual still zero); 0.06 is not rounding. Explained since the readings after the repair review:
    the aggregate stays 0.00. Only Mastercard's amount_usd was shifted, so only Mastercard's own local amount / rate
    (fx_rate is local per USD) disagrees: owner Mastercard."""

    @classmethod
    def plant(cls, data_dir):
        _shift_mc(data_dir, "MC2827341940727", D("1200.00"))  # PX10000601: same local amount and rate, USD differs
        _shift_mc(data_dir, "MC2604007494015", D("-0.06"))    # PX10000604: just beyond the 0.05 tolerance

    def test_typed_unexplained(self):
        found = [d for d in self.diffs(leg=1) if d.key == "PX10000601"]
        self.assertEqual([(d.type, d.cls, d.gross, d.net, d.requires_explanation) for d in found],
                         [("usd_conversion_error", "real_error", D("-1200.00"), D("-1200.00"), True)])
        self.assertEqual(self.r.recon.leg1_by_type.get("usd_conversion_error"), D("-1199.94"))
        self.assertNotIn("unexplained", self.r.recon.leg1_by_type)

    def test_owner_is_the_side_whose_conversion_is_off(self):
        found = [(d.key, d.who_fixes) for d in self.diffs(leg=1) if d.key == "PX10000601"]
        self.assertEqual(found, [("PX10000601", "Mastercard")])

    def test_residual_still_zero(self):
        total = sum(self.r.recon.leg1_by_type.values(), D("0"))
        self.assertEqual(total, D("14400.23"))
        self.assertEqual(_cleared_net(self.r) - _mastercard_september_net(self.r) - total, D("0"))

    def test_aggregate_stays_zero(self):
        self.assertEqual(self.r.recon.unexplained_total, EXPECTED_UNEXPLAINED_REAL)
        self.assertIs(self.r.recon.unexplained_escalates, False)

    def test_beyond_tolerance_is_not_rounding(self):
        found = [d for d in self.diffs(leg=1) if d.key == "PX10000604"]
        self.assertEqual([(d.type, d.gross) for d in found], [("usd_conversion_error", D("0.06"))])


UNEXPLAINED_TYPES = set()  # readings after the repair review (Andrés, 2026-10-14)
REAL_ERROR_TYPES = ("processor_duplicate", "bank_duplicate_debit", "sign_flip", "amount_diff", "fx_rate_diff",
                    "processor_only", "mastercard_only", "processor_entry_missing", "invoice_not_accrued",
                    "settlement_amount_diff", "usd_conversion_error", "bank_line_unrecorded", "ledger_entry_unmatched",
                    "ledger_amount_diff", "ledger_posted_late")
# Readings after the third repair review: two owners and an action per difference (Andrés, 2026-10-14). Who fixes
# (policy.FIXER_OF) is whoever can fix the cause; "Accounting" is gone. input_missing is fixed by the missing file's
# sender (INPUT_FIXERS); rounding has none.
FIXERS = dict(
    [(t, "Processor") for t in ("fx_rate_diff", "usd_conversion_error", "amount_diff", "sign_flip",
                                "processor_duplicate", "processor_only", "mastercard_only", "reference_bad",
                                "auth_after_clearing", "auth_stale", "ambiguous_match")]
    + [(t, "Mastercard") for t in ("settlement_amount_diff", "bank_duplicate_debit")]
    + [(t, "Finance Ops") for t in ("bank_line_unrecorded", "ledger_entry_unmatched", "ledger_amount_diff",
                                    "ledger_posted_late", "processor_entry_missing", "processor_entry_misdated",
                                    "invoice_not_accrued", "account_unmapped", "month_cutoff")]
    + [(t, "Treasury") for t in ("funding_in_transit", "bank_not_yet_posted", "settlement_not_debited",
                                 "suspense_pending_payer")])
FOUR_FIXERS = {"Processor", "Mastercard", "Finance Ops", "Treasury"}
# The sender of each input, "as before"; ledger files move from Accounting (gone) to Finance Ops (reading).
INPUT_FIXERS = {"processor_transactions.csv": "Processor", "processor_invoice.txt": "Processor",
                "mastercard_clearing_detail.csv": "Mastercard", "mastercard_daily_settlement_summary.csv": "Mastercard",
                "mastercard_fee_notice.txt": "Mastercard", "fx_rates_daily.csv": "Mastercard",
                "bridge_account_statement.csv": "Treasury", "gl_journal_lines.csv": "Finance Ops",
                "gl_opening_balances.csv": "Finance Ops", "customers.csv": "Finance Ops",
                "close_checklist.csv": "Finance Ops", "treasury_email_thread.txt": "Treasury"}
CHECKLIST = "close_checklist.csv"
LEG1_TYPES = ("fx_rate_diff", "usd_conversion_error", "amount_diff", "sign_flip", "processor_duplicate",
              "processor_only", "mastercard_only", "reference_bad", "auth_after_clearing", "auth_stale",
              "ambiguous_match")
# Clara owner: the owner_role of the close-checklist task that covers the difference (type -> task, plan 606f6ce).
TASK_OF = dict([(t, "T05") for t in LEG1_TYPES + ("month_cutoff",)]
               + [(t, "T06") for t in ("settlement_amount_diff", "bank_duplicate_debit", "settlement_not_debited")]
               + [(t, "T07") for t in ("bank_line_unrecorded", "ledger_entry_unmatched", "ledger_amount_diff",
                                       "ledger_posted_late", "funding_in_transit", "bank_not_yet_posted",
                                       "account_unmapped")]
               + [("suspense_pending_payer", "T09"), ("invoice_not_accrued", "T11"),
                  ("processor_entry_missing", "T02"), ("processor_entry_misdated", "T02")])
INPUT_TASK = {"processor_transactions.csv": "T01", "bridge_account_statement.csv": "T03",
              "mastercard_clearing_detail.csv": "T04", "mastercard_daily_settlement_summary.csv": "T04",
              "mastercard_fee_notice.txt": "T04", "fx_rates_daily.csv": "T04", "gl_journal_lines.csv": "T02",
              "gl_opening_balances.csv": "T02", "processor_invoice.txt": "T12", "customers.csv": "T10",
              "treasury_email_thread.txt": "T03", "close_checklist.csv": "T21"}
# Example sentences the plan quotes verbatim (policy.ACTION_OF). Fourth repair review: the duplicate-debit sentence
# as Andrés approved it (2026-10-15); the fx_rate_diff example ("...; post the proposed correction") is superseded by
# the rule that Finance Ops posts the proposed correction (ActionSentences).
ACTION_EXAMPLES = {
    "month_cutoff": "Confirm it clears in October; no entry",
    "bank_duplicate_debit": "Post the proposed receivable from Mastercard now; follow the Mastercard credit and clear "
                            "the receivable when it arrives"}
# Readings after the fifth repair review: the processor types with a resend and a proposed entry end on one feed
# clause, which belongs to Finance Ops; the processor-correction types themselves are read from
# policy.CORRECTION_TYPES, not copied here. The USD conversion sentence depends on its fixer (amendment a030dcc), so
# it is asserted on the planted difference rows (USD_ACTION), not on one policy.ACTION_OF string. The Mastercard
# sentence is the one plan block "Extras before submission" quotes (Andrés, 2026-10-15: Mastercard's own conversion
# error is adjusted and followed), superseding a030dcc's "no entry".
RESEND_ENTRY_TYPES = ("fx_rate_diff", "sign_flip", "amount_diff", "processor_duplicate")
FEED_CLAUSE = "; Finance Ops posts the proposed correction and the feed does not post the resent file"
OLD_FEED_CLAUSE = "must not post the resent file again"
USD_ACTION = {
    "Processor": "Processor re-converts at Mastercard's rate and resends the file; Finance Ops posts the proposed "
                 "correction and the feed does not post the resent file",
    "Mastercard": "Post the proposed adjustment now; Mastercard corrects its conversion and the settlement; Treasury "
                  "follows the correction and clears the adjustment when it arrives"}
PLAN_ACTIONS = {
    "settlement_not_debited": "Confirm the bank debits the settlement; still open after 5 business days, it escalates "
                              "to the Controller; no entry"}


def _missing_file(d):
    """The input file an `input_missing` difference is about, read from its key and sources."""
    text = " ".join([str(d.key)] + ["%s:%s" % tuple(s) for s in _src_list(d.srcs)]).lower()
    if "processor invoice" in text or "processor_invoice" in text:
        return "processor_invoice.txt"
    found = [f for f in INPUT_FIXERS if f in text and f != CHECKLIST]
    if not found and CHECKLIST in str(d.key).lower():
        found = [CHECKLIST]
    if len(found) != 1:
        raise AssertionError("cannot tell which input %r is about: %r" % (d.key, found))
    return found[0]


def _conversion_off(row):
    """A row's amount_usd differs from its own amount_local converted at its own fx_rate (local per 1 USD)."""
    return (row["amount_local"] / row["fx_rate"]).quantize(D("0.01"), ROUND_HALF_UP) != row["amount_usd"]


def _duplicate_half(d, result):
    return d.type == "bank_line_unrecorded" and d.key in {x.key for x in result.recon.differences
                                                          if x.type == "bank_duplicate_debit"}


def _expected_fixer(d, result):
    """Who fixes `d` under the readings after the third repair review, derived from the plan, not from code."""
    if d.type == "input_missing":
        return INPUT_FIXERS[_missing_file(d)]
    if _duplicate_half(d, result):
        return FIXERS["bank_duplicate_debit"]
    if d.type == "usd_conversion_error":
        by_src = {tuple(r["src"]): r for r in result.inputs.processor + result.inputs.mc_detail}
        cited = [by_src[s] for s in _src_list(d.srcs) if s in by_src]
        processor = [r for r in cited if r["src"][0] == PROCESSOR]
        mastercard = [r for r in cited if r["src"][0] == MC_DETAIL]
        assert len(processor) == 1 and len(mastercard) == 1, d.srcs
        return "Mastercard" if _conversion_off(mastercard[0]) and not _conversion_off(processor[0]) else "Processor"
    return FIXERS[d.type]


def _expected_task(d, result):
    if d.type == "input_missing":
        return INPUT_TASK[_missing_file(d)]
    return TASK_OF["bank_duplicate_debit" if _duplicate_half(d, result) else d.type]


def _task_role(task, data_dir=None):
    _fields, rows = _read_rows(data_dir or DATA_DIR, CHECKLIST)
    return [r["owner_role"] for r in rows if r["task_id"] == task][0]


# plan.md "Type codes": every type and its class, declared once in policy.DIFF_TYPES / policy.CLASS_OF.
PLAN_CLASS_OF = dict(
    [(t, "timing") for t in ("month_cutoff", "processor_entry_misdated", "funding_in_transit", "bank_not_yet_posted",
                             "settlement_not_debited", "suspense_pending_payer")]
    + [(t, "real_error") for t in REAL_ERROR_TYPES]
    + [(t, "data_issue") for t in ("reference_bad", "auth_after_clearing", "auth_stale", "ambiguous_match",
                                   "input_missing", "account_unmapped")]
    + [("rounding", "auto_cleared")])


class PolicyTypeCodes(unittest.TestCase):
    """Plan "Type codes" and the review readings: the type list, the class of each type, the unexplained set and the
    controller-action set, as policy declares them."""

    def test_type_codes_and_classes(self):
        from bridge import policy
        self.assertEqual(sorted(policy.DIFF_TYPES), sorted(PLAN_CLASS_OF))
        self.assertEqual(dict(policy.CLASS_OF), PLAN_CLASS_OF)

    def test_unexplained_types(self):
        from bridge import policy
        self.assertEqual(set(policy.UNEXPLAINED_TYPES), UNEXPLAINED_TYPES)

    def test_controller_action_types(self):
        from bridge import policy
        self.assertEqual(set(policy.CONTROLLER_ACTION_TYPES), set(REAL_ERROR_TYPES))

    def test_fixer_of_every_type(self):
        # Third repair review: policy.FIXER_OF replaces OWNER_OF.
        from bridge import policy
        self.assertEqual(set(FIXERS), set(PLAN_CLASS_OF) - {"rounding", "input_missing"})
        self.assertEqual({t: policy.FIXER_OF[t] for t in FIXERS}, FIXERS)
        self.assertFalse(policy.FIXER_OF.get("rounding"))

    def test_four_fixers_no_accounting(self):
        # input_missing, if declared in FIXER_OF at all, is fixed per input (INPUT_FIXERS), not per type.
        from bridge import policy
        fixers = {f for t, f in policy.FIXER_OF.items() if t not in ("rounding", "input_missing")}
        self.assertEqual(fixers, FOUR_FIXERS)
        self.assertNotIn("Accounting", fixers)

    def test_action_of_every_type(self):
        from bridge import policy
        self.assertEqual([t for t in PLAN_CLASS_OF if t != "rounding"
                          if not str(policy.ACTION_OF.get(t) or "").strip()], [])
        self.assertFalse(policy.ACTION_OF.get("rounding"))
        self.assertEqual({t: policy.ACTION_OF[t] for t in ACTION_EXAMPLES}, ACTION_EXAMPLES)

    def test_unexplained_code_gone(self):
        from bridge import policy
        self.assertNotIn("unexplained", policy.DIFF_TYPES)
        self.assertNotIn("unexplained", policy.CLASS_OF)
        self.assertNotIn("unexplained", policy.FIXER_OF)
        self.assertFalse(hasattr(policy.TYPE, "unexplained"))
        self.assertEqual(policy.CLASS_OF["usd_conversion_error"], "real_error")

    def test_owner_alias_gone(self):
        # Fourth repair review minor: the OWNER_OF alias goes; tests read FIXER_OF.
        from bridge import policy
        self.assertFalse(hasattr(policy, "OWNER_OF"))

    def test_leg1_type_list_written_once(self):
        # Fifth repair review: the leg-1 list is not written again inside the fixer or task map; month cut-off, the
        # leg-1 type another owner fixes, is listed with that owner.
        from bridge import policy
        allowed = {t for t in policy._LEG1_TYPES if policy.FIXER_OF[t] != "Processor"}
        self.assertEqual(allowed, {"month_cutoff"})
        self.assertEqual(guards.overlapping_list_violations(os.path.join(REPO_ROOT, "bridge", "policy.py"),
                                                            "_LEG1_TYPES", ("FIXER_OF", "TASK_OF"), allowed), [])

    def test_cash_check_constant_gone(self):
        # Second repair review minors: policy.CASH_CHECK goes; code uses policy.CHECK.cash_reconciled.
        from bridge import policy
        self.assertFalse(hasattr(policy, "CASH_CHECK"))
        self.assertEqual(policy.CHECK.cash_reconciled, "cash_reconciled")


class ActionSentences(unittest.TestCase):
    """Readings after the fourth repair review: each action sentence matches what the tool proposes."""

    def action(self, type_):
        from bridge import policy
        return policy.ACTION_OF[type_]

    def test_processor_entry_posted_by_finance_ops(self):
        # Finance Ops posts the proposed correction, never the processor (no subject switch to a bare "post").
        from bridge import policy
        self.assertTrue(policy.CORRECTION_TYPES)
        for t in [t for t in policy.CORRECTION_TYPES if t != "usd_conversion_error"]:  # per fixer: planted rows
            with self.subTest(type=t):
                self.assertIn("Finance Ops posts", self.action(t))
                self.assertRegex(self.action(t), r"\bproposed\b")
                self.assertNotRegex(self.action(t), r"(?i)[;,]\s*(then\s+)?post the proposed")

    def test_processor_only_names_its_conditional_entry(self):
        self.assertRegex(self.action("processor_only"), r"(?i)\bconditional\b")

    def test_usd_conversion_error_is_corrected(self):
        # Fifth repair review: the USD conversion error is corrected like the other processor errors.
        from bridge import policy
        self.assertIn("usd_conversion_error", policy.CORRECTION_TYPES)

    def test_resend_with_entry_ends_on_the_feed_clause(self):
        # Fifth repair review: Finance Ops posts the correction and the feed does not post the resent file.
        for t in RESEND_ENTRY_TYPES:
            with self.subTest(type=t):
                self.assertRegex(self.action(t), r"(?i)\bresends?\b.*\bfile\b")
                self.assertTrue(self.action(t).endswith(FEED_CLAUSE), self.action(t))
                self.assertEqual(self.action(t).count(FEED_CLAUSE), 1)

    def test_feed_clause_only_where_an_entry_corrects(self):
        from bridge import policy
        self.assertNotRegex(self.action("auth_after_clearing"), r"(?i)\bfeed\b")
        self.assertEqual([t for t, s in policy.ACTION_OF.items() if s and OLD_FEED_CLAUSE in s], [])
        self.assertEqual(sorted(t for t, s in policy.ACTION_OF.items() if t != "usd_conversion_error"
                                and s and re.search(r"(?i)\bfeed\b", str(s))), sorted(RESEND_ENTRY_TYPES))
        for fixer, sentence in USD_ACTION.items():
            with self.subTest(fixer=fixer):
                self.assertEqual(sentence.endswith(FEED_CLAUSE), fixer == "Processor")

    def test_plan_sentences_word_for_word(self):
        for t, sentence in PLAN_ACTIONS.items():
            with self.subTest(type=t):
                self.assertEqual(self.action(t), sentence)

    def test_usd_conversion_does_not_restate_the_fixer(self):
        # The fifth repair review's sentences name their fixer; the "whoever" wording stays gone.
        self.assertNotRegex(str(self.action("usd_conversion_error")), r"(?i)\bwhoever\b")

    def test_input_missing(self):
        self.assertIn("Send the missing file", self.action("input_missing"))
        self.assertNotRegex(self.action("input_missing"), r"(?i)\bagain\b")

    def test_settlement_not_debited(self):
        self.assertIn("Confirm the bank debits the settlement", self.action("settlement_not_debited"))
        self.assertNotIn("next working day", self.action("settlement_not_debited").lower())


class DataIssueFlags(_Golden):
    """Spec E3 data-issue flags (tasks T2): counts on this data; each carries no money, no age, never escalates, and
    sits on leg 1 (input_missing on leg 3)."""

    EXPECTED = {"reference_bad": 105, "auth_after_clearing": 3, "auth_stale": 22}

    def test_counts(self):
        for type_, count in self.EXPECTED.items():
            with self.subTest(type=type_):
                found = self.diffs(type_=type_)
                self.assertEqual(len(found), count)
                self.assertEqual({d.cls for d in found}, {"data_issue"})

    def test_auth_after_clearing_rows(self):
        self.assertEqual(sorted(d.key for d in self.diffs(type_="auth_after_clearing")),
                         ["PX10002962", "PX10002963", "PX10003116"])

    def test_data_issue_flags_carry_no_money(self):
        flags = [d for d in self.r.recon.differences if d.cls == "data_issue"]
        self.assertTrue(flags)
        for d in flags:
            self.assertEqual((d.gross, d.net, d.age_wd, d.escalates, d.leg),
                             (D("0.00"), D("0.00"), 0, False, 3 if d.type == "input_missing" else 1), (d.type, d.key))


class V9CashRecon(_Golden):
    """V9 / I1: ledger 1,547,965.55 - 400,000.00 in transit (BS0032) = bank 1,147,965.55."""

    def test_cash(self):
        cash = self.r.close.cash_recon
        ledger = _field(cash, "ledger_balance")
        bank = _field(cash, "bank_balance")
        items = _field(cash, "reconciling_items")
        self.assertEqual((ledger, bank), (D("1547965.55"), D("1147965.55")))
        self.assertEqual(len(items), 1)
        # Readings after the repair review: signed, the ledger's September effect minus the bank's (+400,000.00).
        self.assertEqual(_field(items[0], "amount"), D("400000.00"))
        self.assertIn("in the ledger, not yet in the bank", _field(items[0], "description").lower())
        self.assertEqual(ledger - _field(items[0], "amount"), bank)
        self.assertIn(_line_of(BANK, "line_id", "BS0032"), _src_list(_field(items[0], "src")))

    def test_ties_and_check_cites_both_sides(self):
        cash = self.r.close.cash_recon
        self.assertEqual(_field(cash, "unreconciled"), D("0.00"))
        check = _cash_check(self.r)
        self.assertEqual((check.passed, check.count), (True, 0))
        sides = set(_src_list(_field(cash, "ledger_src"))) | set(_src_list(_field(cash, "bank_src")))
        self.assertTrue(sides)
        self.assertEqual(sides - set(_src_list(check.srcs)), set())


# --- Pre-checks (E6) -----------------------------------------------------------------------------------------------

class PreChecks(_Golden):
    """E6 / I9 (tasks T4): every check in policy.CHECKS returns its expected result and count on this data."""

    # name: (passed, count)
    # summary_vs_detail amended by the repairs block (material 7): 31-Aug, which has no detail rows, lies outside the
    # detail file's settlement dates and is skipped as a coverage note.
    EXPECTED = {"summary_vs_detail": (True, 0),
                "clearing_days_vs_entries": (False, 2),  # 24-Sep missing, 30-Sep posted 1-Oct
                "settlements_vs_debits": (True, 0),      # the 2-Oct settlement is October's (third repair review)
                "net_formula": (True, 0),
                "statuses": (True, 45),                  # 25 AUTHORIZED + 20 DECLINED kept out of money
                "stale_authorisations": (False, 22),
                "impossible_dates": (False, 3),
                "references": (False, 105),              # 60 empty + 45 mistyped on CLEARED rows
                "card_numbers": (True, 0),
                "missing_inputs": (False, 1),            # processor invoice
                "cash_reconciled": (True, 0),            # ledger - reconciling items - bank = 0.00
                "inputs_cover_period": (True, 0),        # every dated file reaches 1-Sep and 30-Sep
                "checklist_tasks_owned": (True, 0)}      # every mapped task present with an owner_role

    def test_declared_names(self):
        from bridge import policy
        self.assertEqual(sorted(policy.CHECKS), sorted(self.EXPECTED))

    def test_each_check(self):
        by_name = {}
        for check in self.r.checks:
            by_name.setdefault(check.name, []).append(check)
        for name, (passed, count) in self.EXPECTED.items():
            with self.subTest(check=name):
                self.assertEqual(len(by_name.get(name, [])), 1)
                check = by_name[name][0]
                self.assertIsInstance(check.passed, bool)
                self.assertEqual((check.passed, check.count), (passed, count))


# Closing-review reading: a check with a reconciliation counterpart counts the counterpart's differences.
CHECK_COUNTERPARTS = {"clearing_days_vs_entries": ("processor_entry_missing", "processor_entry_misdated"),
                      "settlements_vs_debits": ("settlement_not_debited", "settlement_amount_diff"),
                      "stale_authorisations": ("auth_stale",), "impossible_dates": ("auth_after_clearing",),
                      "references": ("reference_bad",)}


class _ChecksFromRecon:
    """Mixin: each check with a counterpart counts exactly its counterpart's differences, and auth_after_clearing is
    flagged on every processor row with both dates and the authorisation after the clearing."""

    def test_counts_equal_counterparts(self):
        checks = {c.name: c for c in self.r.checks}
        for name, types in CHECK_COUNTERPARTS.items():
            with self.subTest(check=name):
                self.assertEqual(checks[name].count, sum(len(self.diffs(type_=t)) for t in types))

    def test_auth_after_clearing_on_every_dated_row(self):
        _fields, rows = _read_rows(self.data, PROCESSOR)
        raw = {r["txn_id"] for r in rows
               if r["auth_date"] and r["clearing_date"] and r["auth_date"] > r["clearing_date"]}
        self.assertEqual({d.key for d in self.diffs(type_="auth_after_clearing")}, raw)


class PreChecksFromRecon(_ChecksFromRecon, _Golden):
    """E6, closing-review reading, case data: the derived counts (2, 0, 22, 3, 105); settlements_vs_debits went from 1
    to 0 when leg 2 became September's (third repair review)."""

    data = DATA_DIR

    def test_case_counts(self):
        checks = {c.name: c.count for c in self.r.checks}
        self.assertEqual({n: checks[n] for n in CHECK_COUNTERPARTS},
                         {"clearing_days_vs_entries": 2, "settlements_vs_debits": 0, "stale_authorisations": 22,
                          "impossible_dates": 3, "references": 105})


class PreChecksFromReconPlanted(_ChecksFromRecon, _Planted, _Golden):
    """E6, closing-review reading, synthetic: edits where the old check code and the reconciliation disagreed.
    PX10000000 moved to 1-Oct, authorised 2-Oct, reference emptied (outside the leg-1 universe: auth after clearing,
    bad reference); one line of the 15-Sep processor entry posted on 16-Sep; an unpaired settlement debit on the 7-Sep
    holiday (BS9003, recorded in the ledger)."""

    @classmethod
    def plant(cls, data_dir):
        _edit(data_dir, PROCESSOR, "txn_id", "PX10000000", clearing_date="2026-10-01", auth_date="2026-10-02",
              network_ref="")
        fields, rows = _read_rows(data_dir, GL_LINES)
        entry = [r for r in rows if r["reference"] == "PROC-20260915"]
        assert len(entry) > 1, len(entry)
        entry[1]["posting_date"] = "2026-09-16"
        _write_rows(data_dir, GL_LINES, fields, rows)
        V4SettlementDebitUnpaired.plant(data_dir)

    def test_impossible_dates_include_the_october_row(self):
        checks = {c.name: c for c in self.r.checks}
        self.assertEqual((checks["impossible_dates"].passed, checks["impossible_dates"].count), (False, 4))
        self.assertIn("PX10000000", {d.key for d in self.diffs(type_="auth_after_clearing")})


# --- V10-V13 -------------------------------------------------------------------------------------------------------

class V10Structure(unittest.TestCase):
    """V10 / I1, I6, I7: every output CSV row sourced; no float in money modules; policy values only in policy.py;
    index.html self-contained."""

    def test_output_files_and_src(self):
        out_dir, _before, _after = _run()
        self.assertEqual(sorted(n for n in OUTPUT_FILES if not os.path.isfile(os.path.join(out_dir, n))), [])
        self.assertEqual(len(OUTPUT_FILES), 10)
        # Amended by dee2151: the ERP file is exempt from the src column, and only it (NO_SRC_OUTPUTS).
        found = guards.src_violations(out_dir, DATA_DIR, _missing_labels(_result()))
        self.assertEqual([v for v in found if v != "%s: no src column" % os.path.join(out_dir, NO_SRC_OUTPUTS[0])], [])

    def test_no_float(self):
        modules = guards.money_modules()
        self.assertIn("policy.py", [os.path.basename(p) for p in modules])
        self.assertEqual(guards.float_violations(modules), [])

    def test_policy_literals_only_in_policy(self):
        modules = guards.non_policy_modules()
        self.assertTrue(modules)
        self.assertEqual(guards.policy_literal_violations(modules), [])

    def test_page_has_no_external_reference(self):
        out_dir, _before, _after = _run()
        self.assertEqual(guards.external_ref_violations(os.path.join(out_dir, "index.html")), [])


ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")


def _leaves(node):
    if isinstance(node, dict):
        return [x for v in node.values() for x in _leaves(v)]
    if isinstance(node, list):
        return [x for v in node for x in _leaves(v)]
    return [node]


def _as_decimal(value):
    if isinstance(value, bool) or not isinstance(value, (int, str, Decimal)):  # floats were parsed as Decimal
        return None
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001 - not a number
        return None


def _decimal_cell(test, text):
    """A written amount: plain decimal text, zero written 0.00."""
    test.assertRegex(text, DECIMAL_TEXT)
    if Decimal(text) == 0:
        test.assertEqual(text, "0.00")
    return Decimal(text)


def _bool_cell(test, text):
    test.assertIn(text, ("true", "false"))
    return text == "true"


class V10SourcesInMemory(_Golden):
    """V10 / I1, I6 in memory: every difference has a real source, leg-1 txn keys point at their own processor line,
    and build()'s result holds no float anywhere."""

    def test_every_difference_has_a_real_source(self):
        self.assertTrue(self.r.recon.differences)
        self.assertEqual(_source_problems(self.r, DATA_DIR), [])

    def test_owner_in_memory(self):
        from bridge import policy
        # Third repair review: who_fixes, clara_owner and action replace owner.
        from bridge import policy
        shown = [d for d in self.r.recon.differences if d.cls != "auto_cleared"]
        self.assertEqual([(d.type, d.key, d.who_fixes) for d in shown if d.who_fixes != _expected_fixer(d, self.r)], [])
        self.assertEqual([(d.type, d.key, d.clara_owner) for d in shown
                          if d.clara_owner != _task_role(_expected_task(d, self.r))], [])
        self.assertEqual([(d.type, d.key) for d in shown if d.action != policy.ACTION_OF[d.type]], [])
        self.assertEqual([d.type for d in shown if hasattr(d, "owner")], [])

    def test_no_float_in_result(self):
        self.assertEqual(_floats_in(self.r), [])


ENTRY_COLUMNS = ["entry_id", "title", "account", "debit", "credit", "status", "approval_level", "missing_evidence",
                 "preparer", "approver", "src"]


class V10ReadBack(unittest.TestCase):
    """V10 / I1, I2, I12: balances.csv and proposed_entries.csv say exactly what the in-memory result says; entries
    carry their title and missing evidence, cash_recon.csv its `unreconciled` line (closing-review readings)."""

    @classmethod
    def setUpClass(cls):
        cls.r = _result()
        cls.out_dir = _run()[0]

    def rows(self, name):
        return _read_rows(self.out_dir, name)[1]

    def test_balances(self):
        rows = {r["account"]: r for r in self.rows("balances.csv")}
        balances = _balances(self.r)
        self.assertEqual(sorted(rows), sorted(balances))
        for account, values in balances.items():
            for column in ("before", "after_confirmed", "after_all"):
                with self.subTest(account=account, column=column):
                    self.assertEqual(_decimal_cell(self, rows[account][column]), values[column])

    def test_entries(self):
        fields, rows = _read_rows(self.out_dir, "proposed_entries.csv")
        self.assertEqual(fields, ENTRY_COLUMNS)
        by_entry = {}
        for row in rows:
            by_entry.setdefault(row["entry_id"], []).append(row)
        self.assertEqual(sorted(by_entry), sorted(str(e.id) for e in self.r.close.entries))
        for entry in self.r.close.entries:
            with self.subTest(entry=entry.id):
                lines = by_entry[str(entry.id)]
                written = sorted((r["account"], _decimal_cell(self, r["debit"]), _decimal_cell(self, r["credit"]))
                                 for r in lines)
                self.assertEqual(written, sorted((str(a), dr, cr) for a, dr, cr in entry.lines))
                self.assertEqual({(r["status"], r["approval_level"]) for r in lines},
                                 {(entry.status, entry.approval_level)})
                self.assertEqual({(r["preparer"], r["approver"]) for r in lines}, {("", "")})
                self.assertTrue(entry.title)
                self.assertEqual({(r["title"], r["missing_evidence"]) for r in lines},
                                 {(entry.title, entry.missing_evidence or "")})
                if entry.status == "proposed-conditional":
                    self.assertTrue(lines[0]["missing_evidence"].strip())
        self.assertIn("proposed-conditional", {r["status"] for r in rows})

    def test_exceptions(self):
        from bridge import policy
        fields = _read_rows(self.out_dir, "exceptions.csv")[0]
        # Third repair review: who_fixes, clara_owner and action replace owner.
        self.assertNotIn("owner", fields)
        self.assertEqual({"who_fixes", "clara_owner", "action"} - set(fields), set())
        written = sorted((int(r["leg"]), r["type"], r["cls"], r["key"], _decimal_cell(self, r["gross"]),
                          _decimal_cell(self, r["net"]), int(r["age_wd"]), _bool_cell(self, r["requires_explanation"]),
                          _bool_cell(self, r["escalates"]), _bool_cell(self, r["controller_action"]), r["who_fixes"],
                          r["clara_owner"], r["action"], sorted({p.strip() for p in r["src"].split(guards.SRC_SEPARATOR)}))
                         for r in self.rows("exceptions.csv"))
        expected = sorted((d.leg, d.type, d.cls, str(d.key), d.gross, d.net, d.age_wd, d.requires_explanation,
                           d.escalates, d.controller_action, _expected_fixer(d, self.r),
                           _task_role(_expected_task(d, self.r)), policy.ACTION_OF[d.type], _rendered_srcs(d.srcs))
                          for d in self.r.recon.differences if d.cls != "auto_cleared")
        self.assertEqual(written, expected)

    def test_checks(self):
        written = sorted((r["name"], _bool_cell(self, r["passed"]), int(r["count"])) for r in self.rows("checks.csv"))
        self.assertEqual(written, sorted((c.name, c.passed, c.count) for c in self.r.checks))

    def test_cash_recon(self):
        rows = self.rows("cash_recon.csv")
        cash = self.r.close.cash_recon
        by_line = {}
        for row in rows:
            by_line.setdefault(row["line"], []).append(_decimal_cell(self, row["amount"]))
        self.assertEqual(by_line.get("ledger_balance"), [_field(cash, "ledger_balance")])
        self.assertEqual(by_line.get("bank_balance"), [_field(cash, "bank_balance")])
        self.assertEqual(sorted(by_line.get("reconciling_item", [])),
                         sorted(_field(i, "amount") for i in _field(cash, "reconciling_items")))
        self.assertEqual(by_line.get("unreconciled"), [_field(cash, "unreconciled")])
        self.assertEqual(by_line["unreconciled"], [D("0.00")])


def _page_text(out_dir):
    with open(os.path.join(out_dir, "index.html"), encoding="utf-8") as f:
        return f.read()


def _page_data(out_dir):
    """The JSON blob index.html carries in its `bridge-data` script."""
    found = re.search(r'<script[^>]*id="bridge-data"[^>]*>(.*?)</script>', _page_text(out_dir), re.S)
    if not found:
        raise AssertionError("index.html has no bridge-data script")
    return json.loads(found.group(1))


def _row_id(leg, type_, key, src_parts):
    return (str(leg), type_, str(key), tuple(sorted(src_parts)))


DATE_30_SEP = re.compile(r"\b30[\s-]?sep|\bsep\w*\.?\s+30\b|2026-09-30|\b30/09\b")
DATE_1_OCT = re.compile(r"\b0?1[\s-]?oct|\boct\w*\.?\s+0?1\b|2026-10-01|\b01/10\b")
E02_LINES = [("1210", D("45899.81"), D("0")), ("2105", D("0"), D("45331.47")), ("4100", D("0"), D("760.81")),
             ("5100", D("192.47"), D("0"))]  # PF-20260930 lines, posted on 1-Oct, moved to 30-Sep


class EntriesSayWhatTheyAre(unittest.TestCase):
    """Closing-review reading: the misdated PROC-20260930 entry says both actions (post on 30-Sep, reverse the 1-Oct
    posting); the page's entries table carries title and missing evidence."""

    @classmethod
    def setUpClass(cls):
        cls.r = _result()
        cls.out_dir = _run()[0]

    def test_misdated_entry_title(self):
        found = [e for e in self.r.close.entries if sorted((str(a), dr, cr) for a, dr, cr in e.lines) == E02_LINES]
        self.assertEqual(len(found), 1)
        title = found[0].title.lower()
        self.assertRegex(title, r"\bpost")
        self.assertIn("revers", title)
        self.assertRegex(title, DATE_30_SEP)
        self.assertRegex(title, DATE_1_OCT)

    def test_page_entries_table(self):
        table = _page_data(self.out_dir)["tables"]["proposed_entries"]
        self.assertEqual(table["columns"], ENTRY_COLUMNS)
        titles = {r["entry_id"]: (r["title"], r["missing_evidence"]) for r in table["rows"]}
        self.assertEqual(titles, {str(e.id): (e.title, e.missing_evidence or "") for e in self.r.close.entries})


class ExceptionsPageColumns(unittest.TestCase):
    """Closing-review reading, static half: the exceptions table shows `controller_action` as "Controller action" and
    `requires_explanation` as "Needs explanation", each with a filter. Whether the columns render and the filters
    narrow the rows is V14, the Chrome demo."""

    FIELDS = ("controller_action", "requires_explanation")

    @classmethod
    def setUpClass(cls):
        cls.out_dir = _run()[0]
        cls.page = _page_text(cls.out_dir)

    def test_labels(self):
        for label in ("Controller action", "Needs explanation"):
            self.assertIn(label, self.page)

    def test_rows_carry_the_fields(self):
        rows = _page_data(self.out_dir)["tables"]["exceptions"]["rows"]
        self.assertTrue(rows)
        for field in self.FIELDS:
            self.assertEqual({r[field] for r in rows} - {"true", "false"}, set(), field)
        self.assertEqual([r["key"] for r in rows if not (r.get("who_fixes") and r.get("clara_owner")
                                                         and r.get("action"))], [])
        self.assertIn("true", {r["controller_action"] for r in rows})

    def test_exceptions_columns_list_both(self):
        # Every full column list of the exceptions table in the page script (the one naming age_wd and gross) names
        # both fields; the visible list of the amended page plan leaves them to the filters and the CSV.
        lists = [m.group(0) for m in re.finditer(r"\[[^\[\]]*\]", self.page)
                 if '"age_wd"' in m.group(0) and '"gross"' in m.group(0)]
        # No such literal is fine: the export may read the CSV's own columns (CsvOutputsUnchanged in test_page.py).
        for found in lists:
            for field in self.FIELDS:
                self.assertIn('"%s"' % field, found)

    def test_filter_bound_to_each(self):
        state = re.search(r"var filt\s*=\s*\{[^}]*\}", self.page)
        self.assertTrue(state, "no filter state in the page script")
        for field in self.FIELDS:
            with self.subTest(field=field):
                self.assertRegex(state.group(0), r"\b%s\s*:" % field)
                self.assertRegex(self.page, r"filt(\.%s\b|\[\s*[\"']%s[\"']\s*\])" % (field, field))
                self.assertRegex(self.page, r"sel\(\s*[\"']%s[\"']|[\"']f-%s[\"']" % (field, field))


class FacetsFromTheDifference(_Golden):
    """Closing-review reading: each difference has `origin`, the date ageing counts from, and the page date facet is
    that date; country is the cited processor row's program_country on leg 1, the merchant country (said to be so)
    for mastercard_only, and empty on legs 2 and 3."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        data = _page_data(_run()[0])
        cls.facets = {}
        for row, facet in zip(data["tables"]["exceptions"]["rows"], data["facets"]):
            parts = [p for p in row["src"].split(guards.SRC_SEPARATOR) if p]
            cls.facets.setdefault(_row_id(row["leg"], row["type"], row["key"], parts), []).append(facet)
        cls.shown = [d for d in cls.r.recon.differences if d.cls != "auto_cleared"]

    def facet(self, d):
        found = self.facets.get(_row_id(d.leg, d.type, d.key, _rendered_srcs(d.srcs)), [])
        self.assertTrue(found, (d.type, d.key))
        return found[0]

    def test_origin_is_the_ageing_date(self):
        from bridge import recon
        self.assertEqual([(d.type, d.key) for d in self.r.recon.differences if not hasattr(d, "origin")], [])
        self.assertEqual([(d.type, d.key, d.origin) for d in self.r.recon.differences if d.cls in MONEY_CLASSES
                          and not (isinstance(d.origin, datetime.date) and d.age_wd == recon.age_wd(d.origin))], [])
        misdated = self.diffs(type_="processor_entry_misdated")
        self.assertEqual([d.origin for d in misdated], [datetime.date(2026, 9, 30)])

    def test_date_facet_is_origin(self):
        for d in self.shown:
            origin = getattr(d, "origin", None)
            self.assertEqual(self.facet(d)["date"], origin.isoformat() if origin else "", (d.type, d.key))
        self.assertEqual([self.facet(d)["date"] for d in self.diffs(type_="processor_entry_misdated")],
                         ["2026-09-30"])

    def test_country_empty_on_legs_2_and_3(self):
        self.assertEqual([(d.type, d.key, self.facet(d)["country"]) for d in self.shown
                          if d.leg in (2, 3) and self.facet(d)["country"]], [])
        self.assertEqual([self.facet(d)["country"] for d in self.diffs(type_="processor_entry_missing")], [""])

    def test_country_of_processor_rows(self):
        processor = {tuple(r["src"]): r for r in self.r.inputs.processor}
        for d in self.diffs(leg=1):
            cited = [processor[s] for s in _src_list(d.srcs) if s in processor]
            if d.cls == "auto_cleared" or not cited:
                continue
            own = [r for r in cited if r["txn_id"] == d.key] or cited
            self.assertEqual(self.facet(d)["country"], own[0]["program_country"], (d.type, d.key))

    def test_mastercard_only_is_merchant_country(self):
        mastercard = {tuple(r["src"]): r for r in self.r.inputs.mc_detail}
        found = self.diffs(type_="mastercard_only")
        self.assertEqual(len(found), 5)
        for d in found:
            facet = self.facet(d)
            row = mastercard[_src_list(d.srcs)[0]]
            self.assertIn(row["merchant_country"], facet["country"], d.key)
            self.assertIn("merchant", json.dumps(facet).lower(), d.key)


class CloseTracker(unittest.TestCase):
    """Minor repairs: a Blocked task with no open dependency is blocked from outside the checklist (T09); the tool
    prepares the three reconciliations (T05-T07), a person signs them."""

    @classmethod
    def setUpClass(cls):
        cls.r = _result()
        cls.rows = {r["task_id"]: r for r in cls.r.close.tracker}

    def test_blocked_outside_the_checklist(self):
        from bridge import policy
        self.assertIn("outside the checklist", str(policy.BLOCKED_OUTSIDE))
        self.assertEqual(self.rows["T09"]["blocked_by"], policy.BLOCKED_OUTSIDE)
        written = {r["task_id"]: r for r in _read_rows(_run()[0], "close_tracker.csv")[1]}
        self.assertIn("outside the checklist", written["T09"]["blocked_by"])

    def test_reconciliations_are_prepared(self):
        for task in ("T05", "T06", "T07"):
            self.assertTrue(self.rows[task]["tool_evidence"].startswith("prepares"), self.rows[task]["tool_evidence"])


THOUSANDS = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")


def _money_text(value):
    """An amount as plain two-decimal text, the way every CSV and the blob write it."""
    return format(value.quantize(D("0.01")), "f")


class PlainDecimalsInFiles(unittest.TestCase):
    """Closing-review reading: thousands separators appear on the page only; every CSV keeps plain decimals."""

    def test_no_thousands_separator_in_csvs(self):
        out_dir = _run()[0]
        found = []
        for name in OUTPUT_FILES:
            if name.endswith(".csv"):
                for line, row in enumerate(_read_rows(out_dir, name)[1], start=2):
                    found += [(name, line, k, v) for k, v in row.items() if v and THOUSANDS.match(v.strip())]
        self.assertEqual(found, [])


def _page_script(out_dir):
    """The page's own script, without the JSON blob."""
    return re.sub(r'(<script[^>]*id="bridge-data"[^>]*>).*?(</script>)', r"\1\2", _page_text(out_dir), flags=re.S)


class PageDisplayFormat(unittest.TestCase):
    """Closing-review reading, static half: amounts are shown with thousands separators by a display function. (The
    figure-table half moved to test_page.py with the plan block "Page: a summary by category on every tab".)"""

    @classmethod
    def setUpClass(cls):
        cls.script = _page_script(_run()[0])

    def test_display_format_with_separators(self):
        name = _display_function(self.script)
        self.assertTrue(name, "no display function adding thousands separators")
        self.assertGreaterEqual(len(re.findall(r"\b%s\(" % name, self.script)), 3, name)


GROUPING = r"toLocaleString\(|Intl\.NumberFormat|\\B\(\?=\(\\d\{3\}\)\+"


def _display_function(script):
    """The name of the page function that adds thousands separators, or None."""
    for m in re.finditer(r"function\s+(\w+)\s*\([^)]*\)\s*\{", script):
        if re.search(GROUPING, script[m.end():m.end() + 600]):
            return m.group(1)
    return None


class PageMinors(unittest.TestCase):
    """Readings after the repair review, minors, static half: the page shows the facet's country basis (the merchant
    country is labelled as such), and the summary cards and the leg-1-by-type table use the display format. How they
    read on screen is V14, the Chrome demo."""

    @classmethod
    def setUpClass(cls):
        cls.script = _page_script(_run()[0])

    def test_who_fixes_labels(self):
        # Third repair review: "Who fixes", "Clara owner", "What to do"; the editable note is "Assigned person".
        for label in ("Who fixes", "Clara owner", "What to do", "Assigned person"):
            self.assertIn('"%s"' % label, self.script)

    def test_country_basis_shown(self):
        self.assertIn("country_basis", self.script)
        self.assertIn("merchant country", self.script.lower())

    def test_summary_uses_the_display_format(self):
        name = _display_function(self.script)
        self.assertTrue(name, "no display function adding thousands separators")
        for figure in (r"totals\.leg1_difference_usd", r"totals\.unexplained_total_usd", r"totals\.leg1_by_type\["):
            with self.subTest(figure=figure):
                self.assertRegex(self.script, r"\b%s\(\s*%s" % (name, figure))


class V11InputsUntouched(unittest.TestCase):
    """V11 / I8: input fingerprints are equal before and after the run, and the manifest records them."""

    def test_fingerprints(self):
        out_dir, before, after = _run()
        self.assertEqual(before, after)
        with open(os.path.join(out_dir, "run_manifest.json"), encoding="utf-8") as f:
            manifest_text = json.dumps(json.load(f))
        for name in INPUT_FILES:
            self.assertIn(before[name], manifest_text, name)

    def test_manifest_version_and_totals(self):
        out_dir, _before, _after = _run()
        with open(os.path.join(out_dir, "run_manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f, parse_float=Decimal)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()

        def strings(node):
            if isinstance(node, dict):
                return [s for v in node.values() for s in strings(v)]
            if isinstance(node, list):
                return [s for v in node for s in strings(v)]
            return [node] if isinstance(node, str) else []

        versions = [m.group(1) for m in (re.match(r"^([0-9a-f]{7,40})(-dirty)?$", s) for s in strings(manifest)) if m]
        self.assertTrue([v for v in versions if head.startswith(v)], "no code version matching HEAD %s" % head)
        totals = manifest.get("totals")
        self.assertTrue(totals)
        self.assertIn(D("15600.17"), [_as_decimal(v) for v in _leaves(totals)])
        stamps = [s for s in strings(manifest) if ISO_DATETIME.match(s)]
        self.assertTrue(stamps, "no ISO 8601 date-time in the manifest")
        for stamp in stamps:
            datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))

    def test_dirty_suffix(self):
        with tempfile.TemporaryDirectory(prefix="bridge-dirty-") as tmp:
            copy = os.path.join(tmp, "repo")
            shutil.copytree(REPO_ROOT, copy, ignore=shutil.ignore_patterns("__pycache__"))
            with open(os.path.join(copy, "specs", "project-bridge", "tasks.md"), "a", encoding="utf-8") as f:
                f.write("\n")
            run_py = RUN_PY if os.path.relpath(RUN_PY, REPO_ROOT).startswith("..") \
                else os.path.join(copy, os.path.relpath(RUN_PY, REPO_ROOT))
            out_dir = os.path.join(tmp, "out")
            os.mkdir(out_dir)
            proc = subprocess.run([sys.executable, "-E", "-s", run_py, "--data", DATA_DIR, "--out", out_dir],
                                  cwd=copy, capture_output=True, text=True, timeout=600)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(os.path.join(out_dir, "run_manifest.json"), encoding="utf-8") as f:
                text = f.read()
            self.assertRegex(text, r'"[0-9a-f]{7,40}-dirty"')

    def test_load_fingerprints(self):
        fingerprints = _result().inputs.fingerprints
        current = _fingerprints()
        self.assertEqual(sorted(set(INPUT_FILES) - set(fingerprints)), [])
        for name, digest in fingerprints.items():
            self.assertEqual(digest, current[name], name)


class V12MissingInputLoad(_Golden):
    """V12 / I9, load level (T1): the processor invoice is listed as a missing input with a `missing` source."""

    def test_reported_missing(self):
        found = [(what, src) for what, src in self.r.inputs.missing
                 if "processor" in what.lower() and "invoice" in what.lower()]
        self.assertEqual(len(found), 1)
        self.assertEqual(len(self.r.inputs.missing), 1, self.r.inputs.missing)
        for what, src in self.r.inputs.missing:
            self.assertEqual(tuple(src), ("missing", what))


class V12ChecksReportMissing(_Golden):
    """V12 / I9, checks (T4): the missing-inputs check fails and points at the missing source."""

    def test_missing_inputs_check(self):
        found = [c for c in self.r.checks if c.name == "missing_inputs"]
        self.assertEqual(len(found), 1)
        self.assertIs(found[0].passed, False)
        self.assertTrue([s for s in _src_list(found[0].srcs) if s[0] == "missing"])


class V12NeverEstimated(_Golden):
    """V12 / I9, close (T3): no proposed entry draws an amount from a missing input."""

    def test_never_estimated(self):
        self.assertTrue(self.r.close.entries)
        for entry in self.r.close.entries:
            self.assertFalse([s for s in _src_list(entry.srcs) if s[0] == "missing"], entry.id)


class V13NoCardNumbers(unittest.TestCase):
    """V13 / I10: no 13-19 digit string outside MC references in the outputs, after normalising the raw ones."""

    def test_outputs(self):
        out_dir, _before, _after = _run()
        self.assertEqual(guards.pan_violations(out_dir), [])



# --- Readings after the second repair review (plan block of 5b82dfc) ----------------------------------------------

def _case_entry_ids():
    return [e.id for e in _result().close.entries]


class CrossingCaseData(_Golden):
    """Case data under the second repair review: the only cut-off-crossing pair is TRF0930 (ledger 30-Sep, bank 1-Oct,
    a funding line) -> one `funding_in_transit` row, signed +400,000.00 like its item, owner Treasury; no
    `ledger_posted_late` or `bank_not_yet_posted`; the close stays E01-E11 and cash ties."""

    def test_one_funding_row(self):
        found = [(d.type, d.key, d.cls, d.gross, d.net, d.who_fixes) for t in CROSSING_TYPES
                 for d in self.diffs(type_=t)]
        self.assertEqual(found, [("funding_in_transit", "BS0032", "timing", D("400000.00"), D("400000.00"),
                                  "Treasury")])

    def test_close_unchanged(self):
        self.assertEqual(len(self.r.close.entries), 11)
        self.assertEqual(_field(self.r.close.cash_recon, "unreconciled"), D("0.00"))


class _CrossingRow:
    """Mixin: the planted cut-off-crossing row ROW = (type, bank line_id, class, signed gross, owner,
    controller_action, origin, age_wd, escalates, requires_explanation), citing the bank line and the ledger entry
    JE; a ledger_posted_late row yields one September entry ENTRY (third repair review), any other none."""

    ROW = JE = ENTRY = None

    def test_row(self):
        type_, key = self.ROW[:2]
        found = [(d.type, d.key, d.cls, d.gross, d.who_fixes, d.controller_action, d.origin, d.age_wd, d.escalates,
                  d.requires_explanation) for d in self.diffs(leg=3, type_=type_)]
        self.assertEqual(found, [self.ROW])
        srcs = set(_src_list(self.diffs(type_=type_)[0].srcs))
        self.assertIn(_line_of(BANK, "line_id", key, self.data), srcs)
        self.assertEqual(set(_lines_of(GL_LINES, "je_id", self.JE, self.data)) - srcs, set())

    def test_entries(self):
        # Third repair review: a ledger_posted_late row yields a September entry (ENTRY: the October entry's lines,
        # mirrored onto 30-Sep, titled to reverse that je_id in October), id after the last; other rows yield none.
        ids = _case_entry_ids()
        if self.ROW[0] != "ledger_posted_late":
            self.assertEqual([e.id for e in self.r.close.entries], ids)
            return
        self.assertEqual([e.id for e in self.r.close.entries], ids + ["E%02d" % (len(ids) + 1)])
        entry = self.r.close.entries[-1]
        self.assertEqual(sorted((str(a), dr, cr) for a, dr, cr in entry.lines), sorted(self.ENTRY))
        self.assertIn(self.JE, entry.title)
        self.assertRegex(entry.title, r"(?i)revers")
        self.assertTrue(getattr(entry, "date", None) == SEP_30 or DATE_30_SEP.search(entry.title.lower()),
                        entry.title)

    def test_after_corrections_restore_september(self):
        # The entry moves the late posting back into September, so every "after" balance equals the case data's.
        if self.ROW[0] != "ledger_posted_late":
            return
        case, planted = _balances(_result()), _balances(self.r)
        for column in ("after_confirmed", "after_all"):
            self.assertEqual({a: b[column] for a, b in planted.items()}, {a: b[column] for a, b in case.items()})

    def test_row_in_exceptions_csv(self):
        rows = [r for r in _read_rows(_run_on(self.data), "exceptions.csv")[1] if r["type"] == self.ROW[0]]
        self.assertEqual([(r["key"], D(r["gross"]), r["who_fixes"]) for r in rows],
                         [(self.ROW[1], self.ROW[3], self.ROW[4])])


SEP_30 = datetime.date(2026, 9, 30)


class CrossingBankFirst(_CrossingRow, _Planted, _Golden):
    """Bank first: BK-BS0029 booked 1-Oct, its bank line 30-Sep -> `ledger_posted_late` BS0029, real error, owner
    Accounting, Controller action, +53,986.40 (the item), aged from 30-Sep: 3 working days, needs explanation."""

    JE = "BK-BS0029"
    ROW = ("ledger_posted_late", "BS0029", "real_error", D("53986.40"), "Finance Ops", True, SEP_30, 3, False, True)
    ENTRY = [("2105", D("53986.40"), D("0")), ("1110", D("0"), D("53986.40"))]

    @classmethod
    def plant(cls, data_dir):
        _edit_entry(data_dir, "BK-BS0029", posting_date="2026-10-01")


class CrossingFeeBookedLate(_CashCase, _CrossingRow, _Planted, _Golden):
    """Bank first: the 465.00 fee (BS0028, 30-Sep) booked on 1-Oct -> one `ledger_posted_late` row +465.00; item
    +465.00, ledger 1,548,430.55, cash ties."""

    JE = "BK-BS0028"
    ROW = ("ledger_posted_late", "BS0028", "real_error", D("465.00"), "Finance Ops", True, SEP_30, 3, False, True)
    ENTRY = [("6150", D("465.00"), D("0")), ("1110", D("0"), D("465.00"))]  # the plan's planted entry
    ITEMS, UNRECONCILED, LEFTOVERS = [D("400000.00"), D("465.00")], D("0.00"), []
    CROSSING = [FUNDING_ROW, ("ledger_posted_late", "BS0028", D("465.00"))]

    @classmethod
    def plant(cls, data_dir):
        _edit_entry(data_dir, "BK-BS0028", posting_date="2026-10-01")

    def test_ledger(self):
        self.assertEqual(_field(self.r.close.cash_recon, "ledger_balance"), D("1548430.55"))


class CrossingLedgerFirstNotFunding(_CrossingRow, _Planted, _Golden):
    """Ledger first, not funding: BK-BS0031 posted 30-Sep, its bank line (a Mastercard settlement debit) 1-Oct ->
    `bank_not_yet_posted` BS0031, timing, owner Treasury, -44,643.99 (the item), aged from 30-Sep; never
    `funding_in_transit`."""

    JE = "BK-BS0031"
    ROW = ("bank_not_yet_posted", "BS0031", "timing", D("-44643.99"), "Treasury", False, SEP_30, 3, False, True)

    @classmethod
    def plant(cls, data_dir):
        _edit_entry(data_dir, "BK-BS0031", posting_date="2026-09-30")

    def test_not_funding(self):
        self.assertEqual([d.key for d in self.diffs(type_="funding_in_transit")], ["BS0032"])


class CrossingBankFirstAmountDiffers(_Planted, _Golden):
    """Bank first with a different amount (plan 18b2a25): bank 53,986.40 on 30-Sep, BK-BS0029 booked 1-Oct at
    53,000.00. The crossing row carries the matched part signed like the item: `ledger_posted_late` BS0029 +53,000.00.
    The difference row, ledger minus bank, is `ledger_amount_diff` BS0029 +986.40 (-53,000.00 - -53,986.40). The two
    add up to the item, +53,986.40. Ledger 1,601,951.95, cash ties."""

    @classmethod
    def plant(cls, data_dir):
        _edit_entry(data_dir, "BK-BS0029", posting_date="2026-10-01", amount="53000.00")

    def test_rows(self):
        found = sorted((d.type, d.key, d.gross, d.net) for t in CROSSING_TYPES + ("ledger_amount_diff",)
                       for d in self.diffs(leg=3, type_=t) if d.key == "BS0029")
        self.assertEqual(found, [("ledger_amount_diff", "BS0029", D("986.40"), D("986.40")),
                                 ("ledger_posted_late", "BS0029", D("53000.00"), D("53000.00"))])
        self.assertEqual([d.key for d in self.diffs(type_="bank_not_yet_posted")], [])

    def test_rows_add_up_to_the_item(self):
        cash = self.r.close.cash_recon
        items = sorted(_field(i, "amount") for i in _field(cash, "reconciling_items"))
        self.assertEqual(items, [D("53986.40"), D("400000.00")])
        rows = sum((d.gross for t in ("ledger_posted_late", "ledger_amount_diff") for d in self.diffs(type_=t)
                    if d.key == "BS0029"), D("0"))
        self.assertEqual(rows, D("53986.40"))
        self.assertEqual((_field(cash, "ledger_balance"), _field(cash, "unreconciled")), (D("1601951.95"), D("0.00")))


# --- Owners: whoever can fix the cause ---------------------------------------------------------------------------

class OwnersCaseData(unittest.TestCase):
    """Third repair review: on the case data every exceptions.csv row's who_fixes is the plan's mapping, its
    clara_owner the owner_role of its checklist task (cited in src) and its action policy.ACTION_OF's; the missing
    processor invoice is the processor's to fix and T12's; no "Accounting" text remains."""

    @classmethod
    def setUpClass(cls):
        cls.r = _result()
        cls.out_dir = _run()[0]
        cls.rows = _read_rows(cls.out_dir, "exceptions.csv")[1]

    def test_every_row(self):
        wrong = [(r["type"], r["key"], r["who_fixes"]) for r in self.rows
                 if r["type"] != "input_missing" and r["who_fixes"] != FIXERS.get(r["type"])]
        self.assertEqual(wrong, [])

    def test_missing_processor_invoice(self):
        self.assertEqual([(r["who_fixes"], r["clara_owner"]) for r in self.rows if r["type"] == "input_missing"],
                         [("Processor", _task_role("T12"))])

    def test_clara_owner_cited_to_its_task(self):
        wrong = []
        for d in self.r.recon.differences:
            if d.cls == "auto_cleared":
                continue
            task = _expected_task(d, self.r)
            if d.clara_owner != _task_role(task) or _line_of(CHECKLIST, "task_id", task) not in _src_list(d.srcs):
                wrong.append((d.type, d.key, task, d.clara_owner))
        self.assertEqual(wrong, [])

    def test_no_accounting_text(self):
        with open(os.path.join(self.out_dir, "exceptions.csv"), encoding="utf-8") as f:
            self.assertNotIn("Accounting", f.read())
        self.assertNotIn("Accounting", _page_script(self.out_dir))
        self.assertEqual({r["who_fixes"] for r in self.rows} - FOUR_FIXERS, set())


class OwnersOfMissingInputs(_Planted, _Golden):
    """`input_missing` is fixed by the missing file's sender and owned at Clara by the task that receives the file.
    Deleted: the bank statement (Treasury; T03), the opening balances (Finance Ops; T02), the rates and the Mastercard
    fee notice (Mastercard; T04), the customer master (Finance Ops; T10); the processor invoice stays missing
    (Processor; T12)."""

    DELETED = ("bridge_account_statement.csv", "gl_opening_balances.csv", "fx_rates_daily.csv",
               "mastercard_fee_notice.txt", "customers.csv")

    @classmethod
    def plant(cls, data_dir):
        for name in cls.DELETED:
            os.remove(os.path.join(data_dir, name))

    def test_owner_per_input(self):
        found = sorted((_missing_file(d), d.who_fixes, d.clara_owner) for d in self.diffs(type_="input_missing"))
        expected = sorted((f, INPUT_FIXERS[f], _task_role(INPUT_TASK[f], self.data))
                          for f in self.DELETED + ("processor_invoice.txt",))
        self.assertEqual(found, expected)


class ClaraOwnerFromChecklist(_Planted, _Golden):
    """Third repair review: clara_owner is read from close_checklist.csv at run time, never typed in code. T05's
    owner_role changed to "Payments Ops" in a copy -> every leg-1 row and month_cutoff follow it and cite T05's row;
    leg-2 rows keep T06's Treasury."""

    @classmethod
    def plant(cls, data_dir):
        _edit(data_dir, CHECKLIST, "task_id", "T05", owner_role="Payments Ops")

    def test_leg1_follows(self):
        t05 = _line_of(CHECKLIST, "task_id", "T05", self.data)
        found = [d for d in self.r.recon.differences if d.leg == 1 and d.cls != "auto_cleared"]
        self.assertTrue(found)
        self.assertEqual({d.clara_owner for d in found + self.diffs(type_="month_cutoff")}, {"Payments Ops"})
        self.assertEqual([(d.type, d.key) for d in found if t05 not in _src_list(d.srcs)], [])

    def test_other_tasks_unchanged(self):
        self.assertEqual({d.clara_owner for d in self.diffs(leg=2) if d.cls != "auto_cleared"}, {"Treasury"})


class ClaraOwnerChecklistUnreadable(_Planted, _Golden):
    """Third repair review: if the checklist cannot be read, clara_owner is empty and input_missing says why (fixed
    by Finance Ops, the checklist's sender)."""

    @classmethod
    def plant(cls, data_dir):
        os.remove(os.path.join(data_dir, CHECKLIST))

    def test_empty_owner(self):
        shown = [d for d in self.r.recon.differences if d.cls != "auto_cleared"]
        self.assertEqual({d.clara_owner for d in shown}, {""})
        self.assertIn((CHECKLIST, "Finance Ops"),
                      [(_missing_file(d), d.who_fixes) for d in self.diffs(type_="input_missing")])


def _names_on_page(data):
    """Every value of the page's `names` data block, flattened, with the key that holds it."""
    found, stack = [], [(k, v) for k, v in data["names"].items()]
    while stack:
        key, node = stack.pop()
        if isinstance(node, dict):
            stack += [(key, v) for v in node.values()]
        elif isinstance(node, (list, tuple)):
            stack += [(key, v) for v in node]
        else:
            found.append((key, node))
    return found


class _ChecklistTaskMissing:
    """Readings after the fourth repair review: a blank Clara owner is never silent. Pre-check
    `checklist_tasks_owned`: every task of the type -> task map exists in close_checklist.csv with a non-empty
    owner_role; it fails naming the missing task (count 1 here) and the page shows the not-reliable banner while it
    fails (the check's name reaches the page as data and the page script reads it)."""

    TASK = None

    def check(self):
        found = [c for c in self.r.checks if c.name == "checklist_tasks_owned"]
        self.assertEqual(len(found), 1)
        return found[0]

    def test_fails_naming_the_task(self):
        check = self.check()
        self.assertEqual((check.passed, check.count), (False, 1))
        said = " ".join([check.detail] + ["%s:%s" % tuple(s) for s in _src_list(check.srcs)])
        self.assertRegex(said, r"\b%s\b" % self.TASK)

    def test_page_warns(self):
        out_dir = _run_on(self.data)
        checks = {r["name"]: r["passed"] for r in _page_data(out_dir)["tables"]["checks"]["rows"]}
        self.assertEqual(checks.get("checklist_tasks_owned"), "false")
        keys = {k for k, v in _names_on_page(_page_data(out_dir)) if v == "checklist_tasks_owned"}
        self.assertTrue(keys, "the check's name does not reach the page's names block")
        script = _page_script(out_dir)
        self.assertTrue([k for k in keys if re.search(r"names\.%s\b|names\[\s*[\"']%s[\"']\s*\]" % (k, k), script)],
                        "the page script never reads names.%s" % sorted(keys))
        self.assertRegex(script, r"(?i)not reliable")


class ChecklistTaskRenamed(_ChecklistTaskMissing, _Planted, _Golden):
    """Planted: T05 renamed T05A (a task inserted and the ids renumbered) -> fails naming T05."""

    TASK = "T05"

    @classmethod
    def plant(cls, data_dir):
        _edit(data_dir, CHECKLIST, "task_id", "T05", task_id="T05A")


class ChecklistOwnerBlank(_ChecklistTaskMissing, _Planted, _Golden):
    """Planted: T06's owner_role left empty -> fails naming T06."""

    TASK = "T06"

    @classmethod
    def plant(cls, data_dir):
        _edit(data_dir, CHECKLIST, "task_id", "T06", owner_role="")


class ChecklistTasksOwnedCaseData(unittest.TestCase):
    """Case data: `checklist_tasks_owned` passes and its name reaches the page's names block."""

    def test_passes_and_named_on_page(self):
        found = [(c.passed, c.count) for c in _result().checks if c.name == "checklist_tasks_owned"]
        self.assertEqual(found, [(True, 0)])
        self.assertIn("checklist_tasks_owned", [v for _k, v in _names_on_page(_page_data(_run()[0]))])


class EntriesDoNotCiteTheChecklist(_Golden):
    """Fourth repair review minor: proposed entries do not cite the close-checklist row; exception rows still do."""

    def test_entries(self):
        self.assertTrue(self.r.close.entries)
        self.assertEqual([(e.title, tuple(s)) for e in self.r.close.entries for s in e.srcs
                          if tuple(s)[:1] == (CHECKLIST,)], [])

    def test_exception_rows_still_cite_it(self):
        shown = [d for d in self.r.recon.differences if d.cls != "auto_cleared" and d.task]
        self.assertTrue(shown)
        self.assertEqual([(d.type, d.key) for d in shown
                          if _line_of(CHECKLIST, "task_id", d.task) not in _src_list(d.srcs)], [])


class OwnersOfUsdConversion(_Planted, _Golden):
    """Second repair review: `usd_conversion_error` is the processor's unless only Mastercard's own amount_usd
    disagrees with its local amount at its own rate. PX10000700: the processor's amount_usd +1,200.00 (Mastercard
    agrees with itself) -> Processor, gross +1,200.00. PX10000601: processor +300.00 and Mastercard +1,200.00 (both
    off) -> Processor, gross -900.00."""

    @classmethod
    def plant(cls, data_dir):
        for txn, delta in (("PX10000700", D("1200.00")), ("PX10000601", D("300.00"))):
            _fields, rows = _read_rows(data_dir, PROCESSOR)
            row = [r for r in rows if r["txn_id"] == txn][0]
            _edit(data_dir, PROCESSOR, "txn_id", txn, amount_usd=D(row["amount_usd"]) + delta)
        _shift_mc(data_dir, "MC2827341940727", D("1200.00"))

    def test_owner_processor(self):
        found = sorted((d.key, d.type, d.gross, d.who_fixes) for d in self.diffs(leg=1)
                       if d.key in ("PX10000700", "PX10000601"))
        self.assertEqual(found, [("PX10000601", "usd_conversion_error", D("-900.00"), "Processor"),
                                 ("PX10000700", "usd_conversion_error", D("1200.00"), "Processor")])

    def test_residual_still_zero(self):
        total = sum(self.r.recon.leg1_by_type.values(), D("0"))
        self.assertEqual(_cleared_net(self.r) - _mastercard_september_net(self.r) - total, D("0"))


OWNER_FIELDS = ("owner", "who_fixes", "clara_owner", "action")


class OwnerSetOnce(unittest.TestCase):
    """Second repair review: the owner is set in one place, when the row is built; no module assigns `.owner` to a
    difference afterwards (the duplicate debit's unrecorded half takes the duplicate's owner at construction)."""

    def test_no_owner_overwrite(self):
        import ast
        found = []
        for path in sorted(glob_bridge()):
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), path)
            for node in ast.walk(tree):
                targets = node.targets if isinstance(node, ast.Assign) else (
                    [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else [])
                found += ["%s:%d" % (os.path.basename(path), node.lineno) for t in targets
                          if isinstance(t, ast.Attribute) and t.attr in OWNER_FIELDS]
                if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == "setattr":
                    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) \
                            and node.args[1].value in OWNER_FIELDS:
                        found.append("%s:%d setattr" % (os.path.basename(path), node.lineno))
        self.assertEqual(found, [])


def glob_bridge():
    folder = os.path.join(REPO_ROOT, "bridge")
    return [os.path.join(folder, n) for n in os.listdir(folder) if n.endswith(".py")]


# --- No "unexplained" type -------------------------------------------------------------------------------------------

SUMMARY_SENTENCE = "Every difference has a type, who fixes it, a Clara owner and an action"


class NoUnexplainedText(unittest.TestCase):
    """Second repair review: no type, label or page text says "unexplained" except the aggregate figure; the page
    states the summary sentence beside it (since the fourth repair review: SUMMARY_SENTENCE)."""

    @classmethod
    def setUpClass(cls):
        out_dir = _run()[0]
        cls.script = _page_script(out_dir)
        cls.data = _page_data(out_dir)

    def test_page_text(self):
        # Any "unexplained" not part of an identifier must sit right after the aggregate figure (its card label).
        stray = [m.start() for m in re.finditer(r"(?i)(?<![\w.])unexplained(?!_)", self.script)
                 if "unexplained_total_usd" not in self.script[max(0, m.start() - 200):m.start()]]
        self.assertEqual([self.script[i - 40:i + 40] for i in stray], [])

    def test_sentence(self):
        self.assertIn(SUMMARY_SENTENCE, self.script)
        at = self.script.find(SUMMARY_SENTENCE)
        self.assertIn("unexplained_total_usd", self.script[max(0, at - 600):at + 600])

    def test_no_data_label(self):
        # The summary labels of every tab replace the figure labels (plan block "Page: a summary by category").
        # Narrowed by the repairs block (minors): a page block with no summary (overview, pending, grouped) has none.
        # Narrowed again by the last round: page.screens is a list, not a block, and carries no summary.
        labels = ([s["label"] for block in self.data["page"].values() if isinstance(block, dict)
                   for s in block.get("summary", [])]
                  + [r["type"] for r in self.data["tables"]["exceptions"]["rows"]])
        self.assertEqual([x for x in labels if "unexplained" in x.lower()], [])


# --- Per-file read status ----------------------------------------------------------------------------------------

DATED_FILES = {PROCESSOR: ("auth_date", "clearing_date"), MC_DETAIL: ("clearing_date", "settlement_date"),
               MC_SUMMARY: ("settlement_date",), BANK: ("posting_date", "value_date"), GL_LINES: ("posting_date",),
               "fx_rates_daily.csv": ("date",)}
CSV_INPUTS = [f for f in INPUT_FILES if f.endswith(".csv")]


def _manifest(out_dir):
    with open(os.path.join(out_dir, "run_manifest.json"), encoding="utf-8") as f:
        return json.load(f)


def _file_status(manifest, file_name):
    """[(top-level key, node)] for each manifest node describing `file_name`: a dict whose key is the file name and
    whose value is a dict, or a dict holding the file name as a value."""
    found, stack = [], [(k, v) for k, v in manifest.items()]
    while stack:
        top, node = stack.pop()
        if isinstance(node, dict):
            if isinstance(node.get(file_name), dict):
                found.append((top, node[file_name]))
            if file_name in node.values():
                found.append((top, node))
            stack += [(top, v) for v in node.values()]
        elif isinstance(node, list):
            stack += [(top, v) for v in node]
    return found


def _scalars(node):
    return {str(v) for v in _leaves(node)} if isinstance(node, (dict, list)) else {str(node)}


def _date_ranges(data_dir, file_name):
    """(first, last) per date column of a raw CSV, as ISO text."""
    _fields, rows = _read_rows(data_dir, file_name)
    out = []
    for column in DATED_FILES[file_name]:
        values = [r[column] for r in rows if r[column]]
        out.append((min(values), max(values)))
    return out


class _ReadStatus:
    """Mixin: run_manifest.json reports, per input CSV, the rows read and, for dated files, the first and last date
    (one of the file's date columns)."""

    def check_status(self, manifest, data_dir):
        for name in CSV_INPUTS:
            with self.subTest(file=name):
                nodes = _file_status(manifest, name)
                self.assertTrue(nodes, "no read status for %s" % name)
                values = set().union(*(_scalars(n) for _top, n in nodes))
                self.assertIn(str(len(_read_rows(data_dir, name)[1])), values)
                if name in DATED_FILES:
                    self.assertTrue([r for r in _date_ranges(data_dir, name) if set(r) <= values],
                                    (name, _date_ranges(data_dir, name)))


class FileReadStatus(_ReadStatus, unittest.TestCase):
    """Case data: every file read, the read status in run_manifest.json and in the page's blob, the page shows it
    and the pre-check `inputs_cover_period` passes."""

    @classmethod
    def setUpClass(cls):
        cls.out_dir = _run()[0]
        cls.manifest = _manifest(cls.out_dir)

    def test_manifest(self):
        self.check_status(self.manifest, DATA_DIR)

    def test_text_inputs_listed(self):
        for name in ("treasury_email_thread.txt", "mastercard_fee_notice.txt"):
            self.assertTrue(_file_status(self.manifest, name), name)

    def test_page_shows_it(self):
        tops = {top for top, _n in _file_status(self.manifest, BANK)}
        script = _page_script(self.out_dir)
        self.assertTrue([t for t in tops if re.search(r"(\.%s\b|\[\s*[\"']%s[\"']\s*\])" % (t, t), script)],
                        "the page script never reads %s" % sorted(tops))
        self.assertEqual(_page_data(self.out_dir)["manifest"], self.manifest)

    def test_page_warns_when_unreliable(self):
        self.assertRegex(_page_script(self.out_dir), r"(?i)not reliable")


class _CoverPeriod(_ReadStatus):
    """Mixin for a planted file that does not cover September: `inputs_cover_period` fails once, citing only FILE;
    the manifest shows the file's read status; results are still produced."""

    FILE = LAST = None

    def test_check_fails_naming_the_file(self):
        found = [c for c in self.r.checks if c.name == "inputs_cover_period"]
        self.assertEqual([(c.passed, c.count) for c in found], [(False, 1)])
        self.assertEqual({s[0] for s in _src_list(found[0].srcs)}, {self.FILE})

    def test_status(self):
        out_dir = _run_on(self.data)
        manifest = _manifest(out_dir)
        self.check_status(manifest, self.data)
        self.assertIn(self.LAST, set().union(*(_scalars(n) for _t, n in _file_status(manifest, self.FILE))))
        checks = {r["name"]: r["passed"] for r in _page_data(out_dir)["tables"]["checks"]["rows"]}
        self.assertEqual(checks.get("inputs_cover_period"), "false")


class CoverPeriodTruncated(_CoverPeriod, _Planted, _Golden):
    """A truncated file: the bank statement's last week (26-Sep to 2-Oct) dropped; it now ends on 25-Sep."""

    FILE, LAST = BANK, "2026-09-25"

    @classmethod
    def plant(cls, data_dir):
        fields, rows = _read_rows(data_dir, BANK)
        _write_rows(data_dir, BANK, fields, [r for r in rows if r["posting_date"] <= "2026-09-25"])


class CoverPeriodWrongMonth(_CoverPeriod, _Planted, _Golden):
    """A wrong-month file: every date of the Mastercard daily summary moved back one month (31-Aug -> 31-Jul ...
    2-Oct -> 2-Sep), so it never reaches 30-Sep."""

    FILE, LAST = MC_SUMMARY, "2026-09-02"

    @classmethod
    def plant(cls, data_dir):
        fields, rows = _read_rows(data_dir, MC_SUMMARY)
        for r in rows:
            day = datetime.date.fromisoformat(r["settlement_date"])
            r["settlement_date"] = (day.replace(month=day.month - 1)).isoformat()
        _write_rows(data_dir, MC_SUMMARY, fields, rows)


# --- Minors ------------------------------------------------------------------------------------------------------

class SecondReviewPageMinors(unittest.TestCase):
    """Repair review minors, static half: the "exceptions with notes" download heads the user's note
    `assigned_person` (third repair review, replacing `owner_note`), never an `owner` column."""

    @classmethod
    def setUpClass(cls):
        cls.script = _page_script(_run()[0])

    def test_download_headers(self):
        self.assertIn('"assigned_person"', self.script)
        notes_heads = [m.group(0) for m in re.finditer(r"\[[^\[\]]*\]", self.script)
                       if '"comment"' in m.group(0) and '"status"' in m.group(0)]
        self.assertTrue(notes_heads, "no notes download header in the page script")
        self.assertEqual([h for h in notes_heads if '"owner"' in h], [])


class ManifestFieldNames(unittest.TestCase):
    """Second repair review minors: no run_manifest.json field is named after a pre-check."""

    def test_no_check_name_as_key(self):
        from bridge import policy
        keys, stack = [], [_manifest(_run()[0])]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                keys += list(node)
                stack += list(node.values())
            elif isinstance(node, list):
                stack += node
        self.assertEqual([k for k in keys if k in policy.CHECKS], [])


class CardNumberCheckSources(_Golden):
    """Second repair review minors: the card-number check cites every file it reads, the two text inputs included."""

    READ = {PROCESSOR, MC_DETAIL, BANK, GL_LINES, "customers.csv", "treasury_email_thread.txt",
            "mastercard_fee_notice.txt"}

    def test_sources(self):
        found = [c for c in self.r.checks if c.name == "card_numbers"]
        self.assertEqual(len(found), 1)
        self.assertEqual(self.READ - {s[0] for s in _src_list(found[0].srcs)}, set())


class SuspenseRepeatedReference(_Planted, _Golden):
    """Second repair review minors: the suspense lookup keeps every bank line of a repeated reference. A second inward
    receipt BS9022 with BS0022's reference INW55821 -> the suspense row cites both bank lines."""

    @classmethod
    def plant(cls, data_dir):
        _append(data_dir, BANK, [dict(line_id="BS9022", posting_date="2026-09-23", value_date="2026-09-23",
                                      narrative="INWARD TRF REF 55821 ADJ SANTANDER ORIG UNK",
                                      bank_reference="INW55821", credit_usd="12500.0",
                                      running_balance_usd="1160465.55")])

    def test_both_lines_cited(self):
        found = self.diffs(type_="suspense_pending_payer")
        self.assertEqual(len(found), 1)
        lines = {_line_of(BANK, "line_id", k, self.data) for k in ("BS0022", "BS9022")}
        self.assertEqual(lines - set(_src_list(found[0].srcs)), set())


class LineWidth(unittest.TestCase):
    """Second repair review minors: lines stay within the file's width (120 characters) in bridge/ and run.py."""

    def test_width(self):
        long = []
        for path in sorted(glob_bridge()) + [RUN_PY]:
            with open(path, encoding="utf-8") as f:
                long += ["%s:%d" % (os.path.basename(path), i) for i, line in enumerate(f, 1)
                         if len(line.rstrip("\n")) > 120]
        self.assertEqual(long, [])


# --- Readings after the third repair review (plan block of 606f6ce) -----------------------------------------------

def _next_working_day(day):
    day += datetime.timedelta(days=1)
    while day.weekday() >= 5 or day in (datetime.date(2026, 9, 7), datetime.date(2026, 10, 12)):
        day += datetime.timedelta(days=1)
    return day


class CoverOnlyThePeriodColumn(_Planted, _Golden):
    """Third repair review: coverage reads one period column per file (processor and Mastercard detail
    clearing_date, summary settlement_date, bank and ledger posting_date, rates date). Other date columns may start
    later or end earlier on correct files: Mastercard detail settled the next working day (first settlement 2-Sep),
    bank value dates one working day after posting, and no processor authorisation after 29-Sep. The check passes."""

    @classmethod
    def plant(cls, data_dir):
        later = lambda text: _next_working_day(datetime.date.fromisoformat(text)).isoformat()  # noqa: E731
        fields, rows = _read_rows(data_dir, MC_DETAIL)
        for r in rows:
            r["settlement_date"] = later(r["settlement_date"])
        _write_rows(data_dir, MC_DETAIL, fields, rows)
        fields, rows = _read_rows(data_dir, BANK)
        for r in rows:
            r["value_date"] = later(r["value_date"])
        _write_rows(data_dir, BANK, fields, rows)
        fields, rows = _read_rows(data_dir, PROCESSOR)
        for r in rows:
            if r["auth_date"] and r["auth_date"] > "2026-09-29":
                r["auth_date"] = "2026-09-29"
        _write_rows(data_dir, PROCESSOR, fields, rows)

    def test_passes(self):
        found = [(c.passed, c.count) for c in self.r.checks if c.name == "inputs_cover_period"]
        self.assertEqual(found, [(True, 0)])


class CoverPeriodUnreadable(_Planted, _Golden):
    """Third repair review: a dated file that could not be read fails the coverage check (one bank amount typed
    "30O000.0" leaves the whole statement unread); the page's notice says "missing or unreadable"."""

    @classmethod
    def plant(cls, data_dir):
        _edit(data_dir, BANK, "line_id", "BS0005", debit_usd="30O000.0")

    def test_unread(self):
        self.assertEqual(self.r.inputs.bank, [])

    def test_check_fails_naming_the_file(self):
        found = [c for c in self.r.checks if c.name == "inputs_cover_period"]
        self.assertEqual([(c.passed, c.count) for c in found], [(False, 1)])
        self.assertEqual({s[0] for s in _src_list(found[0].srcs)}, {BANK})

    def test_page_notice(self):
        out_dir = _run_on(self.data)
        self.assertRegex(_page_script(out_dir), r"(?i)missing or unreadable")
        checks = {r["name"]: r["passed"] for r in _page_data(out_dir)["tables"]["checks"]["rows"]}
        self.assertEqual(checks.get("inputs_cover_period"), "false")


def _email_day(text):
    """A date in an e-mail header ("Fri 2 Oct 2026 12:10") or ISO text, else None."""
    found = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if found:
        return datetime.date(*map(int, found.groups()))
    found = re.search(r"\b(\d{1,2}) ([A-Z][a-z]{2}) (\d{4})\b", text)
    if found:
        return datetime.datetime.strptime(" ".join(found.groups()), "%d %b %Y").date()
    return None


class ThirdReviewFileStatus(unittest.TestCase):
    """Third repair review minors: the treasury e-mail's dates sort as dates (first 21-Sep, last 2-Oct, not text
    order); the processor invoice appears in the input-files status as missing."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = _manifest(_run()[0])

    def test_email_dates_sorted(self):
        nodes = _file_status(self.manifest, "treasury_email_thread.txt")
        self.assertTrue(nodes)
        days = [d for _t, n in nodes for d in (_email_day(str(v)) for v in _leaves(n)) if d]
        days = list(dict.fromkeys(days))
        self.assertEqual(days, [datetime.date(2026, 9, 21), datetime.date(2026, 10, 2)])

    def test_processor_invoice_listed_missing(self):
        nodes = _file_status(self.manifest, "processor_invoice.txt")
        self.assertTrue(nodes, "the processor invoice is not in the input-files status")
        values = set().union(*(_scalars(n) for _t, n in nodes))
        self.assertTrue([v for v in values if "missing" in v.lower()], values)


class TemplateLiterals(unittest.TestCase):
    """Third repair review minors: month names and check names reach the page as data, never as literals in
    bridge/template.html."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO_ROOT, "bridge", "template.html"), encoding="utf-8") as f:
            cls.template = f.read()

    def test_no_month_names(self):
        months = r"(?i)\b(january|february|march|april|june|july|august|september|october|november|december|" \
                 r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b"
        self.assertEqual([m.group(0) for m in re.finditer(months, self.template)], [])

    def test_no_check_names(self):
        from bridge import policy
        self.assertEqual([c for c in policy.CHECKS if re.search(r"[\"']%s[\"']" % c, self.template)], [])


# --- Readings after the fifth repair review (plan block of 40f6c5b) -----------------------------------------------

class UsdConversionCorrected(_Planted, _Golden):
    """Fifth repair review: `usd_conversion_error` (Processor) is corrected like the other processor errors.
    Planted: PX10000700's processor amount_usd +1,200.00 (1,165.75 -> 2,365.75; Mastercard keeps 1,165.75, same
    local amount, rate and fees) -> the case entries E01-E11 unchanged, plus one proposed entry E12 of 1,200.00
    reversing what the feed overstated (Dr 2105 / Cr 1210), balanced, citing the processor row."""

    @classmethod
    def plant(cls, data_dir):
        _fields, rows = _read_rows(data_dir, PROCESSOR)
        row = [r for r in rows if r["txn_id"] == "PX10000700"][0]
        _edit(data_dir, PROCESSOR, "txn_id", "PX10000700", amount_usd=D(row["amount_usd"]) + D("1200.00"))

    def new_entries(self):
        case = {e.id for e in _result().close.entries}
        return [e for e in self.r.close.entries if e.id not in case]

    def test_row(self):
        found = [(d.type, d.gross, d.who_fixes) for d in self.diffs(leg=1) if d.key == "PX10000700"]
        self.assertEqual(found, [("usd_conversion_error", D("1200.00"), "Processor")])

    def test_case_entries_unchanged(self):
        case = [(e.id, e.title, sorted(e.lines)) for e in _result().close.entries]
        self.assertEqual([e.id for e in _result().close.entries], ["E%02d" % i for i in range(1, 12)])
        self.assertEqual([(e.id, e.title, sorted(e.lines)) for e in self.r.close.entries][:len(case)], case)

    def test_one_correction_entry(self):
        found = self.new_entries()
        self.assertEqual([e.id for e in found], ["E12"])
        entry = found[0]
        self.assertEqual(sorted((str(a), dr, cr) for a, dr, cr in entry.lines),
                         [("1210", D("0"), D("1200.00")), ("2105", D("1200.00"), D("0"))])
        self.assertEqual((entry.total_debits, entry.status, entry.approval_level),
                         (D("1200.00"), "proposed", _level(D("1200.00"))))
        self.assertEqual(sum((dr for _a, dr, _cr in entry.lines), D("0")),
                         sum((cr for _a, _dr, cr in entry.lines), D("0")))
        self.assertIn(_line_of(PROCESSOR, "txn_id", "PX10000700", self.data), [tuple(s) for s in entry.srcs])

    def test_action_sentence(self):
        found = [d.action for d in self.diffs(leg=1) if d.key == "PX10000700"]
        self.assertEqual(found, [USD_ACTION["Processor"]])
        self.assertTrue(found[0].endswith(FEED_CLAUSE))
        self.assertEqual(found[0].count(FEED_CLAUSE), 1)


class UsdConversionMastercard(_Planted, _Golden):
    """Plan block "Extras before submission" (supersedes amendment a030dcc): a USD conversion error that is Mastercard's
    own gets a proposed adjustment shaped like the duplicate debit's, and Mastercard's sentence, without the feed
    clause. Planted: Mastercard's amount_usd for MC2827341940727 (PX10000601) +1,200.00, same local amount and rate ->
    fixer Mastercard, gross -1,200.00. Clara settles Mastercard's net, 1,200.00 more than the processor feed (and the
    ledger) hold, so the difference is a receivable from Mastercard against the Mastercard payable: Dr 1250 / Cr 2105
    1,200.00, status proposed, citing the Mastercard row. The case entries E01-E11 stay; the adjustment is E12."""

    @classmethod
    def plant(cls, data_dir):
        _shift_mc(data_dir, "MC2827341940727", D("1200.00"))

    def new_entries(self):
        case = {e.id for e in _result().close.entries}
        return [e for e in self.r.close.entries if e.id not in case]

    def test_row(self):
        found = [(d.type, d.gross, d.who_fixes, d.action) for d in self.diffs(leg=1) if d.key == "PX10000601"]
        self.assertEqual(found, [("usd_conversion_error", D("-1200.00"), "Mastercard", USD_ACTION["Mastercard"])])
        self.assertNotIn(FEED_CLAUSE, found[0][3])
        self.assertNotRegex(found[0][3], r"(?i)\bfeed\b")

    def test_case_entries_unchanged(self):
        case = [(e.id, e.title, sorted(e.lines)) for e in _result().close.entries]
        self.assertEqual([e.id for e in _result().close.entries], ["E%02d" % i for i in range(1, 12)])
        self.assertEqual([(e.id, e.title, sorted(e.lines)) for e in self.r.close.entries][:len(case)], case)

    def test_one_adjustment_entry(self):
        found = self.new_entries()
        self.assertEqual([e.id for e in found], ["E12"])
        entry = found[0]
        self.assertEqual(sorted((str(a), dr, cr) for a, dr, cr in entry.lines),
                         [("1250", D("1200.00"), D("0")), ("2105", D("0"), D("1200.00"))])
        self.assertEqual((entry.total_debits, entry.status, entry.missing_evidence, entry.approval_level),
                         (D("1200.00"), "proposed", None, _level(D("1200.00"))))
        self.assertEqual(sum((dr for _a, dr, _cr in entry.lines), D("0")),
                         sum((cr for _a, _dr, cr in entry.lines), D("0")))
        self.assertIn(_line_of(MC_DETAIL, "network_ref", "MC2827341940727", self.data), [tuple(s) for s in entry.srcs])


class UsdConversionCaseData(_Golden):
    """Fifth repair review: the case data has no USD conversion error, so it gets no entry; the close stays E01-E11."""

    def test_no_entry(self):
        self.assertEqual(self.diffs(type_="usd_conversion_error"), [])
        self.assertEqual([e.id for e in self.r.close.entries], ["E%02d" % i for i in range(1, 12)])
        self.assertEqual([e.title for e in self.r.close.entries if re.search(r"(?i)usd conversion", e.title)], [])


class ChecklistTaskDeleted(_ChecklistTaskMissing, _Planted, _Golden):
    """Fifth repair review minor: T12 (a task used only for a missing file, the processor invoice) deleted -> fails
    naming T12."""

    TASK = "T12"

    @classmethod
    def plant(cls, data_dir):
        fields, rows = _read_rows(data_dir, CHECKLIST)
        _write_rows(data_dir, CHECKLIST, fields, [r for r in rows if r["task_id"] != "T12"])


class MonthCutoffFixer(_Golden):
    """Fifth repair review: month cut-off is Finance Ops' in one place; every other leg-1 type stays the Processor's,
    in policy and on the case rows."""

    def test_policy(self):
        from bridge import policy
        self.assertEqual(policy.FIXER_OF["month_cutoff"], "Finance Ops")
        self.assertEqual({t: policy.FIXER_OF[t] for t in LEG1_TYPES}, {t: "Processor" for t in LEG1_TYPES})

    def test_case_rows(self):
        found = self.diffs(leg=1, type_="month_cutoff")
        self.assertTrue(found)
        self.assertEqual({d.who_fixes for d in found}, {"Finance Ops"})
        others = {d.who_fixes for d in self.diffs(leg=1) if d.type in LEG1_TYPES and d.type != "usd_conversion_error"}
        self.assertEqual(others, {"Processor"})



# --- Plan block "Extras before submission" (Andrés, 2026-10-15) ------------------------------------------------------

# The program invoice's line items as mastercard_fee_notice.txt prints them, with the 2026-10-14 classification
# (cross-border adjustment variable; network access, licensing and brand fee fixed). The chart in the data has no
# sub-account for the cross-border adjustment, so the plan puts every line on 5100 and names the item in the title.
INVOICE = "mastercard_fee_notice.txt"
INVOICE_ITEMS = {"Network access fee": (D("3250.00"), "fixed"), "BIN sponsorship & licensing": (D("2000.00"), "fixed"),
                 "Cross-border assessment adjustment": (D("1862.30"), "variable"),
                 "Brand & program fee": (D("1300.00"), "fixed")}
CROSS_BORDER = "Cross-border assessment adjustment"
E05_LINES = sorted([("5100", amount, D("0")) for amount, _cls in INVOICE_ITEMS.values()]
                   + [("2150", D("0"), D("8412.30"))])


class InvoiceItemised(_Golden):
    """Plan block "Extras before submission", E8: the program-invoice accrual E05 is one debit per invoice line item
    and one credit of the total to 2150, still proposed, same id; every debit on 5100 (no cross-border sub-account in
    the chart) with the cross-border line item named in the title; each debit tagged variable or fixed; no account
    outside policy.ACCOUNTS."""

    def entry(self):
        found = [e for e in self.r.close.entries if e.id == "E05"]
        self.assertEqual(len(found), 1)
        return found[0]

    def test_lines_and_total(self):
        entry = self.entry()
        self.assertEqual(sorted((str(a), dr, cr) for a, dr, cr in entry.lines), E05_LINES)
        self.assertEqual(sum(amount for amount, _cls in INVOICE_ITEMS.values()), D("8412.30"))
        self.assertEqual((entry.total_debits, entry.status, entry.missing_evidence, entry.approval_level),
                         (D("8412.30"), "proposed", None, "standard"))

    def test_title_names_the_cross_border_item(self):
        self.assertIn(CROSS_BORDER.lower(), self.entry().title.lower())

    def test_cites_every_invoice_row(self):
        srcs = [tuple(s) for s in self.entry().srcs]
        for item in INVOICE_ITEMS:
            self.assertIn((INVOICE, item), srcs, item)

    def test_debits_tagged_variable_or_fixed(self):
        entry = self.entry()
        tags = {}
        for i, (account, debit, _credit) in enumerate(entry.lines):
            if debit:
                tags[debit] = str(entry.line_tags.get(i, ""))
        for item, (amount, cls) in INVOICE_ITEMS.items():
            with self.subTest(item=item):
                other = "fixed" if cls == "variable" else "variable"
                self.assertRegex(tags.get(amount, ""), r"(?i)\b%s\b" % cls)
                self.assertNotRegex(tags.get(amount, ""), r"(?i)\b%s\b" % other)

    def test_no_account_outside_policy(self):
        from bridge import policy
        used = {str(a) for e in self.r.close.entries for a, _dr, _cr in e.lines}
        self.assertEqual(used - set(policy.ACCOUNTS.values()), set())

    def test_close_otherwise_unchanged(self):
        self.assertEqual([e.id for e in self.r.close.entries], ["E%02d" % i for i in range(1, 12)])


class InvoiceLinesCiteTheirRow(unittest.TestCase):
    """Plan block "Extras before submission", E8: each debit line of E05 cites its own invoice row — in
    proposed_entries.csv (one row per entry line) the invoice part of its src is that line item and no other."""

    def test_each_debit_row(self):
        _fields, rows = _read_rows(_run()[0], "proposed_entries.csv")
        e05 = [r for r in rows if r["entry_id"] == "E05" and _decimal_cell(self, r["debit"])]
        cited = {}
        for r in e05:
            parts = {p.strip() for p in r["src"].split(guards.SRC_SEPARATOR)}
            cited[_decimal_cell(self, r["debit"])] = sorted(p for p in parts if p.startswith(INVOICE + ":"))
        self.assertEqual(cited, {amount: ["%s:%s" % (INVOICE, item)] for item, (amount, _c) in INVOICE_ITEMS.items()})


# Treasury view (E9), from bridge_account_statement.csv alone, recomputed by a throwaway script. Closing balance per
# calendar day of September: the running balance of the day's last line, carried over days without movements; the
# line that sets it.
TREASURY_CLOSE = [
    ("01", "803756.82", "BS0002"), ("02", "766028.43", "BS0003"), ("03", "725797.06", "BS0004"),
    ("04", "689190.24", "BS0005"), ("05", "689190.24", "BS0005"), ("06", "689190.24", "BS0005"),
    ("07", "689190.24", "BS0005"), ("08", "940914.32", "BS0007"), ("09", "904570.24", "BS0008"),
    ("10", "858866.84", "BS0009"), ("11", "824835.30", "BS0010"), ("12", "824835.30", "BS0010"),
    ("13", "824835.30", "BS0010"), ("14", "1106908.31", "BS0012"), ("15", "1065792.36", "BS0013"),
    ("16", "1021594.02", "BS0014"), ("17", "968918.46", "BS0015"), ("18", "928301.52", "BS0016"),
    ("19", "928301.52", "BS0016"), ("20", "928301.52", "BS0016"), ("21", "1146282.55", "BS0019"),
    ("22", "1104689.40", "BS0020"), ("23", "1078997.92", "BS0022"), ("24", "1031463.88", "BS0023"),
    ("25", "986579.47", "BS0024"), ("26", "986579.47", "BS0024"), ("27", "986579.47", "BS0024"),
    ("28", "1243080.18", "BS0026"), ("29", "1202416.95", "BS0027"), ("30", "1147965.55", "BS0029")]
# Mastercard debits per day (settlement lines; the 30-Sep bank fee is not Mastercard's). The duplicate debit BS0018
# (40,616.94) is left out, so 21-Sep carries BS0017 (41,402.03) alone (Andrés, decision log 2026-10-14).
TREASURY_MC_DEBITS = {"01": "71243.18", "02": "37728.39", "03": "40231.37", "04": "36606.82", "08": "48275.92",
                      "09": "36344.08", "10": "45703.40", "11": "34031.54", "14": "42926.99", "15": "41115.95",
                      "16": "44198.34", "17": "52675.56", "18": "40616.94", "21": "41402.03", "22": "41593.15",
                      "23": "38191.48", "24": "47534.04", "25": "44884.41", "28": "43499.29", "29": "40663.23",
                      "30": "53986.40"}
SEPTEMBER_BUSINESS_DAYS = 21   # 22 weekdays less the 7-Sep holiday; every one has a Mastercard debit
# The settled readings (decision log 2026-10-14: average 43,973.93, standard deviation 8,051): the duplicate left out,
# the sample deviation over the 21 business days, k = 2. Recomputed by a throwaway script from the bank statement.
TREASURY_MC_TOTAL = D("923452.51")
TREASURY_SAMPLE_SD = D("8051.1627282287027203032402870434781666752330450456")
TREASURY_BUFFER_K = 2
TREASURY_SUMMARY = {"closing_balance": D("1147965.55"), "average_debit": D("43973.93"), "std_debit": D("8051.16"),
                    "coverage_30_sep": D("26.11"), "transfer": D("255875.54")}
TREASURY_COLUMNS = ["date", "balance", "mc_debits", "days_of_coverage", "src"]


def _shown_as(text, exact):
    """Whether decimal text says `exact` at the text's own number of decimals (half-up)."""
    if not DECIMAL_TEXT.match(text or ""):
        return False
    shown = D(text)
    return shown == exact.quantize(D(1).scaleb(shown.as_tuple().exponent), ROUND_HALF_UP)


def _treasury_averages():
    """The average daily debit: exact, and to the cent (either may divide the balance)."""
    exact = TREASURY_MC_TOTAL / SEPTEMBER_BUSINESS_DAYS
    return [exact, exact.quantize(D("0.01"), ROUND_HALF_UP)]


class TreasuryView(unittest.TestCase):
    """Plan block "Extras before submission", E9: bridge/treasury.py writes treasury.csv (date, balance, mc_debits,
    days_of_coverage, src) from the bank statement alone — one row per calendar day of September, the balance equal to
    the statement's running balance on each day with movements, the Mastercard debits per day, days of coverage =
    balance / average daily debit over September's business days."""

    @classmethod
    def setUpClass(cls):
        cls.out_dir = _run()[0]

    def rows(self):
        path = os.path.join(self.out_dir, "treasury.csv")
        self.assertTrue(os.path.isfile(path), "run.py wrote no treasury.csv")
        fields, rows = _read_rows(self.out_dir, "treasury.csv")
        self.assertEqual(fields, TREASURY_COLUMNS)
        return rows

    def test_module(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO_ROOT, "bridge", "treasury.py")))
        self.assertIn("treasury.py", [os.path.basename(p) for p in guards.money_modules()])

    def test_one_row_per_september_day(self):
        self.assertEqual([r["date"] for r in self.rows()], ["2026-09-%s" % day for day, _b, _l in TREASURY_CLOSE])

    def test_daily_balance_is_the_running_balance(self):
        self.assertEqual([(r["date"], _decimal_cell(self, r["balance"])) for r in self.rows()],
                         [("2026-09-" + day, D(balance)) for day, balance, _line in TREASURY_CLOSE])

    def test_balance_cites_its_bank_line(self):
        for row, (day, _balance, line_id) in zip(self.rows(), TREASURY_CLOSE):
            with self.subTest(day=day):
                parts = {p.strip() for p in row["src"].split(guards.SRC_SEPARATOR) if p.strip()}
                self.assertIn("%s:%d" % _line_of(BANK, "line_id", line_id), parts)
                self.assertEqual([p for p in parts if not p.startswith(BANK + ":")], [], "not from the statement")

    def test_mastercard_debits_per_day(self):
        rows = self.rows()
        self.assertEqual([(r["date"], D(r["mc_debits"] or "0")) for r in rows],
                         [("2026-09-" + day, D(TREASURY_MC_DEBITS.get(day, "0"))) for day, _b, _l in TREASURY_CLOSE])
        self.assertEqual(sum((D(r["mc_debits"] or "0") for r in rows), D("0")), TREASURY_MC_TOTAL)

    def test_21_sep_leaves_the_duplicate_out(self):
        row = [r for r in self.rows() if r["date"] == "2026-09-21"]
        self.assertEqual([D(r["mc_debits"]) for r in row], [D("41402.03")])

    def test_days_of_coverage(self):
        rows = self.rows()
        for row in rows:
            with self.subTest(day=row["date"]):
                balance = D(row["balance"])
                self.assertTrue(any(_shown_as(row["days_of_coverage"], balance / avg) for avg in _treasury_averages()),
                                row["days_of_coverage"])
        # 30-Sep, recomputed: 1,147,965.55 / 43,973.93 = 26.1056.
        self.assertEqual(D(rows[-1]["balance"]), D("1147965.55"))
        self.assertTrue(_shown_as(rows[-1]["days_of_coverage"], D("26.1056")))

    def test_buffer_k_is_two(self):
        from bridge import policy
        self.assertEqual(policy.TREASURY_BUFFER_K, TREASURY_BUFFER_K)
        self.assertEqual(policy.TREASURY_HORIZON_WD, 5)

if __name__ == "__main__":
    unittest.main()
