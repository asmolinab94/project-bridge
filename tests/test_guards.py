"""Structural guards for Project Bridge, each proven to discriminate before it is trusted.

Every guard is a plain function that returns a list of violations (empty means clean). The golden suite
(`test_golden.py`, V10 and V13) applies them to the real `bridge/` package and to the output of `run.py`; this module
only proves that each one fails on a seeded violation and passes on a clean file.

Known blind spots, by construction of a static scan: a float produced at run time (`json.load` without
`parse_float`, `/` on two ints) and a policy value built by arithmetic are not detected.
"""

import ast
import csv
import os
import re
import tempfile
import unittest
from decimal import Decimal, InvalidOperation

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The policy values of spec E1 and plan Contracts that no module other than bridge/policy.py may write.
POLICY_NUMBERS = {Decimal("0.05"), Decimal("5"), Decimal("250"), Decimal("1000"), Decimal("10000"),
                  Decimal("100000")}
POLICY_BARE_NUMBERS = {Decimal("0.05"), Decimal("250"), Decimal("1000"), Decimal("10000"), Decimal("100000")}
DAILY_TOLERANCE = Decimal("1")  # flagged only next to a name containing "tol"
POLICY_DATES = {(2026, 10, 5), (2026, 9, 7), (2026, 10, 12)}
POLICY_DATE_STRINGS = {"%04d-%02d-%02d" % d for d in POLICY_DATES} | {"%04d%02d%02d" % d for d in POLICY_DATES}
ACCOUNT_CODES = {"1110", "1210", "1250", "2105", "2150", "2300", "2900", "3900", "4100", "5100", "6150"}
# Codes declared once in policy.py (plan "Minor repairs"): processor, entry and task statuses, difference classes,
# bank line kinds and difference types. Flagged when a whole string literal outside policy.py equals one.
STATUS_CODES = {"CLEARED", "AUTHORIZED", "DECLINED", "proposed", "proposed-conditional", "Done", "Blocked"}
CLASS_CODES = {"timing", "real_error", "data_issue", "auto_cleared"}
BANK_KIND_CODES = {"settlement", "invoice", "fee", "funding", "receipt", "other"}
TYPE_CODES = {"month_cutoff", "processor_entry_misdated", "funding_in_transit", "bank_not_yet_posted",
              "settlement_not_debited", "suspense_pending_payer", "processor_duplicate", "bank_duplicate_debit",
              "sign_flip", "amount_diff", "fx_rate_diff", "processor_only", "mastercard_only",
              "processor_entry_missing", "invoice_not_accrued", "settlement_amount_diff", "usd_conversion_error",
              "bank_line_unrecorded", "ledger_entry_unmatched", "ledger_amount_diff", "ledger_posted_late",
              "reference_bad", "auth_after_clearing", "auth_stale", "ambiguous_match",
              "input_missing", "account_unmapped", "rounding"}
# Readings after the repair review: reference statuses, match methods and check names are policy values too.
REF_STATUS_CODES = {"exact", "empty", "normalised", "invalid"}
MATCH_METHOD_CODES = {"exact", "normalised", "fuzzy"}
CHECK_NAMES = {"summary_vs_detail", "clearing_days_vs_entries", "settlements_vs_debits", "net_formula", "statuses",
               "stale_authorisations", "impossible_dates", "references", "card_numbers", "missing_inputs",
               "cash_reconciled", "inputs_cover_period"}
# Readings after the second repair review: the owners (and the input senders) are declared once, in policy.py.
OWNER_NAMES = {"Processor", "Accounting", "Treasury", "Mastercard", "Finance Ops"}
CODE_KINDS = (("status", STATUS_CODES), ("class", CLASS_CODES), ("bank kind", BANK_KIND_CODES),
              ("type", TYPE_CODES), ("reference status", REF_STATUS_CODES), ("match method", MATCH_METHOD_CODES),
              ("check name", CHECK_NAMES), ("owner", OWNER_NAMES))
# "open > 5 working days" written as a literal (> 5, >= 6) compared against a name containing "age" or "wd".
AGE_LIMIT_LITERALS = {5, 6}
AGE_NAME_PARTS = ("age", "wd")


def money_modules(repo_root=REPO_ROOT):
    """The Python modules that touch amounts: every module of bridge/ plus run.py."""
    bridge_dir = os.path.join(repo_root, "bridge")
    paths = []
    if os.path.isdir(bridge_dir):
        paths = sorted(os.path.join(bridge_dir, n) for n in os.listdir(bridge_dir) if n.endswith(".py"))
    run_py = os.path.join(repo_root, "run.py")
    if os.path.isfile(run_py):
        paths.append(run_py)
    return paths


def non_policy_modules(repo_root=REPO_ROOT):
    """Every money module except bridge/policy.py, the single declaration of policy values."""
    policy = os.path.join(repo_root, "bridge", "policy.py")
    return [p for p in money_modules(repo_root) if p != policy]


def _parse(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def float_violations(paths):
    """I6: no `float` in a money module — no float literal and no use of the name `float`."""
    found = []
    for path in paths:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Constant) and type(node.value) is float:
                found.append("%s:%d float literal %r" % (path, node.lineno, node.value))
            elif isinstance(node, ast.Name) and node.id == "float":
                found.append("%s:%d use of float" % (path, node.lineno))
    return found


def _as_decimal(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _call_name(node):
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _names_in(node):
    """Lower-cased variable and attribute names used directly in an expression (not inside calls)."""
    if isinstance(node, ast.Name):
        return [node.id.lower()]
    if isinstance(node, ast.Attribute):
        return [node.attr.lower()]
    if isinstance(node, (ast.BinOp, ast.UnaryOp)):
        return [n for child in ast.iter_child_nodes(node) for n in _names_in(child)]
    return []


def _constants_in(node):
    return [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and not isinstance(n.value, bool)]


def _is_one(value):
    return isinstance(value, (int, float, str)) and _as_decimal(value) == DAILY_TOLERANCE


def policy_literal_violations(paths):
    """I7: no tolerance, threshold, cut-off date, holiday, account code, status, class, bank kind or type code written
    outside bridge/policy.py."""
    found = []
    for path in paths:
        for node in ast.walk(_parse(path)):
            where = "%s:%d" % (path, getattr(node, "lineno", 0))
            if isinstance(node, ast.Constant) and not isinstance(node.value, bool):
                value = node.value
                if isinstance(value, (int, float)) and _as_decimal(value) in POLICY_BARE_NUMBERS:
                    found.append("%s policy number %r" % (where, value))
                elif isinstance(value, int) and str(value) in ACCOUNT_CODES:
                    found.append("%s account code %r" % (where, value))
                elif isinstance(value, str):
                    text = value.strip()
                    if text in POLICY_DATE_STRINGS:
                        found.append("%s policy date %r" % (where, value))
                    elif text in ACCOUNT_CODES:
                        found.append("%s account code %r" % (where, value))
                    elif _as_decimal(text) in POLICY_BARE_NUMBERS:
                        found.append("%s policy number as text %r" % (where, value))
                    else:
                        found += ["%s %s code %r" % (where, kind, value) for kind, codes in CODE_KINDS
                                  if value in codes][:1]
            elif isinstance(node, ast.Call):
                name = _call_name(node)
                args = [a.value for a in node.args if isinstance(a, ast.Constant)]
                if name == "Decimal" and len(args) == 1 and _as_decimal(args[0]) in POLICY_NUMBERS:
                    found.append("%s policy number Decimal(%r)" % (where, args[0]))
                elif name in ("date", "datetime") and len(args) >= 3 and tuple(args[:3]) in POLICY_DATES:
                    found.append("%s policy date %s%r" % (where, name, tuple(args[:3])))
            if isinstance(node, ast.Compare):
                operands = [node.left] + node.comparators
                names = [n for o in operands for n in _names_in(o)]
                if any(part in n for n in names for part in AGE_NAME_PARTS):
                    for operand in operands:
                        if isinstance(operand, ast.Constant) and type(operand.value) is int \
                                and operand.value in AGE_LIMIT_LITERALS:
                            found.append("%s working-day limit compared as literal %d" % (where, operand.value))
                if any("tol" in n for n in names) and any(_is_one(c) for o in operands for c in _constants_in(o)):
                    found.append("%s daily tolerance compared as literal 1" % where)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [n for t in targets for n in _names_in(t)]
                if node.value is not None and any("tol" in n for n in names) \
                        and any(_is_one(c) for c in _constants_in(node.value)):
                    found.append("%s daily tolerance assigned as literal 1" % where)
    return found


# A Mastercard reference, raw or normalised: "MC" + 13 digits, optionally split by spaces or hyphens, any case.
_MC_REF = re.compile(r"(?i)MC[\s-]*(?:\d[\s-]?){12}\d(?!\d)")
# Hex digests (SHA-256 fingerprints, git commits) can hold long digit runs that are not card numbers.
_HEX_TOKEN = re.compile(r"(?i)(?<![0-9a-z])(?=[0-9a-f]*[a-f])[0-9a-f]{32,64}(?![0-9a-z])")
# Card numbers written in groups: 4-4-4-1..7 with one repeated separator, or the 4-6-5 layout.
_GROUPED_PAN = re.compile(r"(?<!\d)(?:\d{4}([ -])\d{4}\1\d{4}\1\d{1,7}|\d{4}([ -])\d{6}\2\d{5})(?!\d)")
_PAN = re.compile(r"(?<!\d)\d{13,19}(?!\d)")


def pan_violations(out_dir):
    """I10: after normalising MC references and grouped card numbers, no 13-19 digit string remains in any output."""
    found = []
    for root, _dirs, names in os.walk(out_dir):
        for name in sorted(names):
            path = os.path.join(root, name)
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            masked = _HEX_TOKEN.sub("<hex>", _MC_REF.sub("<mc_ref>", text))
            masked = _GROUPED_PAN.sub(lambda m: re.sub(r"[ -]", "", m.group()), masked)
            for match in _PAN.finditer(masked):
                found.append("%s: %s" % (path, match.group()))
    return found


SRC_SEPARATOR = ";"


_MESSAGE_FIELD = re.compile(r"^(DATE|SUBJECT):\s*(.*?)\s*$", re.M)


def _text_labels(text):
    """Accepted labels of a text input: any verbatim non-blank line fragment, or "<date> <subject>" of an email
    message, with the date as written or as ISO yyyy-mm-dd."""
    messages, current = [], {}
    for field, value in _MESSAGE_FIELD.findall(text):
        current[field] = value
        if field == "SUBJECT":
            messages.append(current)
            current = {}
    return messages


def _iso(raw_date):
    match = re.search(r"(\d{1,2}) (\w{3}) (\d{4})", raw_date)
    if not match:
        return None
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    if match.group(2) not in months:
        return None
    return "%s-%02d-%02d" % (match.group(3), months.index(match.group(2)) + 1, int(match.group(1)))


def _label_ok(label, text, messages):
    if len(label) >= 3 and label in text:
        return True
    for message in messages:
        subject, raw = message.get("SUBJECT", ""), message.get("DATE", "")
        if subject and subject in label and (raw and raw in label or (_iso(raw) or "\0") in label):
            return True
    return False


def _inputs(data_dir):
    """{file_name: ("csv", last valid line) | ("txt", text, messages)} for the input files (header = line 1)."""
    found = {}
    for name in os.listdir(data_dir):
        path = os.path.join(data_dir, name)
        if name.endswith(".csv"):
            with open(path, newline="", encoding="utf-8") as f:
                found[name] = ("csv", sum(1 for _ in csv.reader(f)))
        elif name.endswith(".txt"):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            found[name] = ("txt", text, _text_labels(text))
    return found


# The only output whose rows may cite a whole file or a line range: a check that passed, or one computed over a file.
WHOLE_FILE_OUTPUTS = ("checks.csv",)


def src_problem(src, inputs, missing=(), whole_file=False):
    """Why one `src` cell is not a real source, or None. A cell holds sources joined by ';', each one
    `<input file>:<line>` (CSV line within the file), `<input file>:<label>` (text input: a verbatim fragment, or an
    email's date and subject) or `missing:<what>` with `<what>` one of `missing` (the loaded inputs.missing labels).
    With `whole_file`, also `<input file>:*` and `<input file>:<a>-<b>`."""
    parts = [p.strip() for p in (src or "").split(SRC_SEPARATOR)]
    if not any(parts):
        return "empty src"
    for part in parts:
        file_name, sep, locator = part.partition(":")
        file_name, locator = file_name.strip(), locator.strip()
        if not sep or not locator:
            return "not file:locator %r" % part
        if file_name == "missing":
            if locator not in missing:
                return "not a missing input %r" % part
            continue
        if file_name not in inputs:
            return "not an input file %r" % part
        if locator == "*" and whole_file:
            continue
        kind = inputs[file_name]
        if kind[0] == "csv":
            bounds = re.fullmatch(r"(\d+)(?:-(\d+))?" if whole_file else r"(\d+)()", locator)
            first, last = (int(bounds.group(1)), int(bounds.group(2) or bounds.group(1))) if bounds else (0, 0)
            if not (bounds and 2 <= first <= last <= kind[1]):
                return "line out of range %r" % part
        elif not _label_ok(locator, kind[1], kind[2]):
            return "label not found in the text input %r" % part
    return None


def src_violations(out_dir, data_dir, missing=()):
    """I1: every output CSV has a `src` column and every row a src that names a real input row or a missing input
    (one of `missing`); whole files and ranges only in WHOLE_FILE_OUTPUTS."""
    found = []
    line_counts = _inputs(data_dir)
    for root, _dirs, names in os.walk(out_dir):
        for name in sorted(n for n in names if n.endswith(".csv")):
            path = os.path.join(root, name)
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if "src" not in (reader.fieldnames or []):
                    found.append("%s: no src column" % path)
                    continue
                for row in reader:
                    problem = src_problem(row.get("src"), line_counts, missing, name in WHOLE_FILE_OUTPUTS)
                    if problem:
                        found.append("%s:%d %s" % (path, reader.line_num, problem))
    return found


_ANYWHERE = [re.compile(r"(?i)https?://(?!www\.w3\.org/)"),
             re.compile(r"""(?:["'`(]|=\s*)//[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+""")]  # protocol-relative //host
_IN_TAGS = [re.compile(r"(?i)<link\b[^>]*\bhref\s*=(?!\s*[\"']?(?:data:|#))"),
            re.compile(r"(?i)<[a-z][^>]*\s(?:src|srcset)\s*=(?!\s*[\"']?data:)"),
            re.compile(r"(?i)<object\b[^>]*\sdata\s*=(?!\s*[\"']?data:)"),
            re.compile(r"(?i)<form\b[^>]*\saction\s*=")]  # any action, relative too: the page never submits
# image-set() also takes bare strings: flag the first quoted one that is not a data: URI (url() groups are skipped
# here and judged by the url() pattern).
_IMAGE_SET = re.compile(r"""(?i)image-set\((?:[^()"']|\([^()]*\)|"\s*data:[^"]*"|'\s*data:[^']*')*["'](?!\s*data:)""")
_IN_CSS = [re.compile(r"url\((?!\s*[\"']?(?:data:|#))\s*[^)\s]"), re.compile(r"@import\b"), _IMAGE_SET]
_IN_SCRIPT = [re.compile(r"""\bfetch\(\s*["'`]\s*(?:https?:)?//""")]
_SCRIPT = re.compile(r"(?is)(<script\b[^>]*>)(.*?)(</script\s*>)")
_STYLE_BLOCK = re.compile(r"(?is)<style\b[^>]*>(.*?)</style\s*>")
_STYLE_ATTR = re.compile(r"""(?is)\sstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""")


def external_ref_violations(html_path):
    """I1 support (spec E5, index.html opens without network): no http(s) or protocol-relative URL anywhere; no
    external <link>, src=, srcset=, <object data=> or <form action=> in a tag; no url(), image-set() string or @import
    in CSS; no fetch of a URL in a script. XML namespaces under www.w3.org are names, not fetches, and are allowed."""
    with open(html_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    scripts = [m.group(2) for m in _SCRIPT.finditer(text)]
    markup = _SCRIPT.sub(lambda m: m.group(1) + m.group(3), text)
    css = [m.group(1) for m in _STYLE_BLOCK.finditer(markup)]
    css += [a or b for a, b in _STYLE_ATTR.findall(_STYLE_BLOCK.sub("", markup))]
    zones = [(_ANYWHERE, [text]), (_IN_TAGS, [_STYLE_BLOCK.sub("<style></style>", markup)]), (_IN_CSS, css),
             (_IN_SCRIPT, scripts)]
    return ["%s: %s" % (html_path, m.group()) for patterns, chunks in zones for pattern in patterns
            for chunk in chunks for m in pattern.finditer(chunk)]


# Readings after the fifth repair review: a type list is written once (the leg-1 types were written twice, as the
# Processor list of FIXER_OF and as the leg-1 task list). The guard compares only the lists that must not overlap: the
# leg-1 list against each list literal inside the owner maps; a type a map lists with another owner is `allowed`.
def overlapping_list_violations(path, base, maps, allowed=frozenset()):
    """String-list literals inside the assignments to `maps` that share a member, other than `allowed`, with the
    literal assigned to `base`: the base list written again instead of referenced."""
    tree = _parse(path)
    assigned = {t.id: node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                for t in node.targets if isinstance(t, ast.Name)}

    def literals(node):
        return [(n.lineno, frozenset(e.value for e in n.elts)) for n in ast.walk(node)
                if isinstance(n, (ast.Tuple, ast.List, ast.Set)) and n.elts
                and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in n.elts)]

    if base not in assigned or not literals(assigned[base]):
        return ["%s: no list literal assigned to %s" % (os.path.basename(path), base)]
    base_members = set().union(*(m for _l, m in literals(assigned[base])))
    found = ["%s: %s is not assigned" % (os.path.basename(path), name) for name in maps if name not in assigned]
    for name in maps:
        for line, members in literals(assigned.get(name, ast.Tuple(elts=[]))):
            shared = sorted((members & base_members) - set(allowed))
            if shared:
                found.append("%s:%d (%s) repeats %s members %s" % (os.path.basename(path), line, name, base, shared))
    return found


# --- Self-tests: each guard red on a seeded violation, green on a clean file -------------------------------------

CLEAN_MODULE = '''
from decimal import Decimal
from bridge import policy

def classify(gross, age_wd, rows, day):
    head = rows[:5]
    weekend = day.weekday() >= 5
    many = len(rows) >= 6
    unit = Decimal("1")
    if abs(gross) >= policy.EXPLAIN_THRESHOLD and age_wd > policy.ESCALATE_AGE_WD:
        return Decimal("0.01"), head, policy.ACCOUNTS["payable"], weekend, many, unit
    return Decimal(0) * Decimal(1), len(rows) > 1, abs(gross) <= policy.TOL_DAY
'''


class _TempDir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, text, directory=None):
        path = os.path.join(directory or self.dir, name)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path


class FloatGuardSelfTest(_TempDir):
    """I6: the float guard flags each seeded float and passes Decimal-only code."""

    def test_flags_each_seeded_violation(self):
        seeds = ["x = 0.05\n", "y = float(row['amount_usd'])\n", "def f(a: float):\n    return a\n",
                 "ok = isinstance(v, float)\n"]
        for i, seed in enumerate(seeds):
            with self.subTest(seed=seed):
                self.assertTrue(float_violations([self.write("seed%d.py" % i, seed)]))

    def test_passes_clean_module(self):
        self.assertEqual(float_violations([self.write("clean.py", CLEAN_MODULE)]), [])


class PolicyLiteralGuardSelfTest(_TempDir):
    """I7: the policy-literal guard flags each seeded tolerance, threshold, date, account code, status, class, bank
    kind and type code."""

    def test_flags_each_seeded_code(self):
        seeds = ['ok = p["status"] == "CLEARED"\n', 'conditional = "proposed-conditional"\n',
                 'done = row["status_wd3_0900"] != "Done"\n', 'flag = d.cls == "data_issue"\n',
                 'money = cls in ("timing", "real_error")\n', 'paid = b["kind"] == "settlement"\n',
                 'kind = "other"\n', 'dupes = found.get("processor_only", [])\n',
                 'diff = _difference(3, "account_unmapped", 0, 0, [], key)\n',
                 'bad = p["ref_status"] != "exact"\n', 'return None, "empty"\n', 'return None, "invalid"\n',
                 'm = Match(p, m, "normalised")\n', 'm = Match(ps[0], ms[0], "fuzzy")\n',
                 'CHECKS = {"summary_vs_detail": run_summary}\n', 'name = "cash_reconciled"\n',
                 'name = "inputs_cover_period"\n', 'kind = "ledger_posted_late"\n', 'owner = "Treasury"\n',
                 'OWNER = {"fx": "Mastercard"}\n', 'who = "Finance Ops"\n']
        for i, seed in enumerate(seeds):
            with self.subTest(seed=seed):
                self.assertTrue(policy_literal_violations([self.write("code%d.py" % i, seed)]))

    def test_codes_inside_longer_text_pass(self):
        seeds = ['"""Rows CLEARED in September; data_issue flags carry no money."""\n',
                 'name = "proposed_entries"\n', 'msg = "settlement days and debits that do not pair"\n']
        for i, seed in enumerate(seeds):
            with self.subTest(seed=seed):
                self.assertEqual(policy_literal_violations([self.write("text%d.py" % i, seed)]), [])

    def test_flags_each_seeded_violation(self):
        seeds = ['TOL = Decimal("0.05")\n', "DAY_TOL = Decimal('1.00')\n", "big = gross >= 250\n",
                 "esc = unexplained > 1000\n", "lvl = total >= 10000\n", "cfo = total >= 100000\n",
                 "CUT = date(2026, 10, 5)\n", "H = datetime.date(2026, 9, 7)\n", "H2 = '2026-10-12'\n",
                 "old = age_wd > 5\n", "old = age_wd >= 6\n", "old = d.age >= 6\n", "late = wd_count > 5\n",
                 "t = 0.05\n", "acct = '2105'\n", "acct = 1210\n", "lim = '250'\n", "DAY_TOL = '1.00'\n",
                 "ok = gap_tol >= Decimal('1')\n", "cfo = Decimal(LIMITS.get('x', '100000'))\n"]
        for i, seed in enumerate(seeds):
            with self.subTest(seed=seed):
                self.assertTrue(policy_literal_violations([self.write("seed%d.py" % i, seed)]))

    def test_passes_clean_module(self):
        self.assertEqual(policy_literal_violations([self.write("clean.py", CLEAN_MODULE)]), [])


class PanGuardSelfTest(_TempDir):
    """I10: the card-number guard flags a 13-19 digit string, plain or grouped, and passes MC references."""

    def test_flags_each_seeded_violation(self):
        seeds = ["src,card\nprocessor_transactions.csv:2,4111111111111111\n",
                 "<td>MC5500000000000004123</td>",
                 '{"pan": "5105105105105100"}',
                 "<td>4111 1111 1111 1111</td>",
                 "card 3782-822463-10005"]
        for i, seed in enumerate(seeds):
            with self.subTest(seed=seed):
                with tempfile.TemporaryDirectory() as out:
                    self.write("seed%d.csv" % i, seed, out)
                    self.assertTrue(pan_violations(out))

    def test_passes_clean_file(self):
        digest = "abc1234567890123456" + "d" * 45
        self.write("clean.html", "MC1191505112675 MC 6609039090951 MC-1772217037112 mc6658295420110 "
                                 " MC9439855834584  BNK324320124 2026-09-01 2026-09-02 44884.41 4645 %s" % digest)
        self.assertEqual(pan_violations(self.dir), [])


class SrcGuardSelfTest(_TempDir):
    """I1: the source guard accepts only real input rows or declared missing inputs as `src`; whole files and line
    ranges only in checks.csv."""

    MISSING = ("processor invoice",)

    def setUp(self):
        super().setUp()
        self.data = os.path.join(self.dir, "data")
        self.out = os.path.join(self.dir, "out")
        os.mkdir(self.data)
        os.mkdir(self.out)
        self.write("processor_transactions.csv", "txn_id\nPX1\nPX2\n", self.data)
        self.write("mastercard_fee_notice.txt", "  Network access fee        3,250.00\nTotal due 8,412.30\n", self.data)
        self.write("treasury_email_thread.txt", "FROM: A\nDATE: Mon 21 Sep 2026 09:42\nSUBJECT: Duplicate debits\n"
                                                "\nbody\n---\nDATE: Wed 30 Sep 2026 17:30\nSUBJECT: Prefunding\n", self.data)

    def test_flags_each_seeded_violation(self):
        seeds = ["  ", "x", "processor_transactions.csv:4", "processor_transactions.csv:1",
                 "processor_transactions.csv:two", "other.csv:2", "processor_transactions.csv:2;x",
                 "processor_transactions.csv:2-4", "processor_transactions.csv:3-2",
                 "mastercard_fee_notice.txt:Nonexistent fee", "treasury_email_thread.txt:Mon 21 Sep 2026 09:42 Wrong",
                 "treasury_email_thread.txt:Tue 22 Sep 2026 Prefunding", "processor_transactions.csv:*",
                 "processor_transactions.csv:2-3", "missing:anything", "missing:processor invoice;missing:x"]
        for i, seed in enumerate(seeds):
            with self.subTest(seed=seed):
                with tempfile.TemporaryDirectory() as out:
                    self.write("exceptions.csv", 'key,src\nPX1,"%s"\n' % seed, out)
                    self.assertTrue(src_violations(out, self.data, self.MISSING))

    def test_flags_bad_whole_file_sources_in_checks(self):
        for seed in ("processor_transactions.csv:2-4", "other.csv:*", "missing:anything"):
            with self.subTest(seed=seed):
                with tempfile.TemporaryDirectory() as out:
                    self.write("checks.csv", 'name,src\nreferences,"%s"\n' % seed, out)
                    self.assertTrue(src_violations(out, self.data, self.MISSING))

    def test_flags_missing_src_column(self):
        self.write("balances.csv", "account,before\n1110,1547965.55\n", self.out)
        self.assertTrue(src_violations(self.out, self.data))

    def test_passes_clean_file(self):
        self.write("exceptions.csv", "key,src\nPX1,processor_transactions.csv:2\n"
                                     "PX2,processor_transactions.csv:2; processor_transactions.csv:3\n"
                                     "INV,mastercard_fee_notice.txt:Total due\n"
                                     "FEE,mastercard_fee_notice.txt:Network access fee\n"
                                     "EM1,treasury_email_thread.txt:Mon 21 Sep 2026 09:42 Duplicate debits\n"
                                     "EM2,treasury_email_thread.txt:2026-09-30 Prefunding\n"
                                     "T12,missing:processor invoice\n",
                   self.out)
        self.write("checks.csv", "name,src\nstatuses,processor_transactions.csv:*\n"
                                 "references,processor_transactions.csv:2-3\n", self.out)
        self.assertEqual(src_violations(self.out, self.data, self.MISSING), [])


class ExternalRefGuardSelfTest(_TempDir):
    """I1 support: the page guard flags any external reference and passes a self-contained page."""

    def test_flags_each_seeded_violation(self):
        seeds = ['<a href="https://clara.com">x</a>', "<p>see http://example.com</p>",
                 '<link rel="stylesheet" href="style.css">', '<script src="app.js"></script>',
                 '<img src="logo.png">', "<style>@font-face{src:url(fonts/dm.woff2)}</style>",
                 '<style>@import "theme.css";</style>', '<img srcset="logo@2x.png 2x">',
                 "<script>fetch('http://api.example.com/x')</script>", "<script>fetch('//cdn.example.com/a.js')</script>",
                 '<a href="//cdn.example.com/x">x</a>', '<div style="background:url(bg.png)">x</div>',
                 '<object data="report.pdf"></object>', "<OBJECT type='image/svg+xml' data=logo.svg></OBJECT>",
                 '<form action="submit">', '<form method="post" action="/api/save"></form>',
                 '<style>.h{background-image:image-set("hero.png" 1x, "hero@2x.png" 2x)}</style>',
                 "<div style=\"background:-webkit-image-set('a.avif' type('image/avif'))\">x</div>",
                 '<style>.h{background:image-set(url(data:image/png;base64,AA) 1x, "b.png" 2x)}</style>']
        for i, seed in enumerate(seeds):
            with self.subTest(seed=seed):
                self.assertTrue(external_ref_violations(self.write("seed%d.html" % i, seed)))

    def test_passes_clean_page(self):
        page = ('<html><head><style>@font-face{font-family:x;src:url(data:font/woff2;base64,AAAA)}</style></head>'
                '<body><svg xmlns="http://www.w3.org/2000/svg"></svg><img src="data:image/png;base64,AA">'
                '<object data="data:image/svg+xml;base64,AA"></object><div data-src="x" data-action="y">x</div>'
                '<style>.h{background:image-set(url(data:image/png;base64,AA) 1x, "data:image/png;base64,BB" 2x)}'
                '</style>'
                "<script>const src = row.src; if (a<b) { let src = 1; } // see notes.txt\n"
                "const link = URL.createObjectURL(blob); const u = new URL(location.href); el.url(x);"
                "</script><p>Case study url(not css)</p></body></html>")
        self.assertEqual(external_ref_violations(self.write("index.html", page)), [])


class OverlappingListGuardSelfTest(_TempDir):
    """Fifth repair review: the guard flags the base list written again inside an owner map (also with one member
    dropped, as the Processor list dropped month_cutoff) and passes a map that references it, with the one type
    another owner fixes allowed."""

    BASE = '_L = ("a", "b", "c", "cut")\n'
    MAP = "M = dict([(t, 1) for t in %s] + [(t, 2) for t in (\"x\", \"cut\")])\n"

    def test_flags_each_seeded_violation(self):
        seeds = [self.BASE + self.MAP % '("a", "b", "c")', self.BASE + self.MAP % '["c"]',
                 self.BASE + "M = dict([(t, 1) for t in _L] + [(t, 2) for t in {\"b\", \"x\"}])\n"]
        for i, seed in enumerate(seeds):
            with self.subTest(seed=seed):
                self.assertTrue(overlapping_list_violations(self.write("seed%d.py" % i, seed), "_L", ("M",), {"cut"}))

    def test_flags_missing_names(self):
        path = self.write("missing.py", self.BASE)
        self.assertTrue(overlapping_list_violations(path, "_L", ("M",)))
        self.assertTrue(overlapping_list_violations(path, "_X", ()))

    def test_passes_clean_module(self):
        clean = self.BASE + self.MAP % '[t for t in _L if t != "cut"]' + 'C = ("a", "b", "c", "q")\n'
        self.assertEqual(overlapping_list_violations(self.write("clean.py", clean), "_L", ("M",), {"cut"}), [])


if __name__ == "__main__":
    unittest.main()
