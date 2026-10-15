"""Reading and cleaning (spec E2): every row keeps `src`, amounts are Decimal, dates are `datetime.date`."""

import csv
import datetime
import hashlib
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal

from bridge import policy

ZERO = Decimal(0)
DECIMAL_COLUMNS = frozenset([
    "amount_local", "fx_rate", "amount_usd", "interchange_usd", "scheme_fee_usd", "net_settlement_usd", "debit_usd",
    "credit_usd", "running_balance_usd", "opening_balance_usd_dr_positive", "local_per_usd"])
DATE_COLUMNS = frozenset(["auth_date", "clearing_date", "settlement_date", "posting_date", "value_date", "date",
                          "sent_on"])
CSV_ATTRS = ("processor", "mc_detail", "mc_summary", "bank", "gl_lines", "gl_opening", "fx", "customers", "checklist")

_INVOICE_ITEM = re.compile(r"^\s{2,}(\S.*?)\s{2,}([\d,]+\.\d+)\s*$")
_EMAIL_HEADER = re.compile(r"^(FROM|DATE|SUBJECT):\s*(.*?)\s*$")
_EMAIL_SEPARATOR = re.compile(r"(?m)^---\s*$")


@dataclass
class Inputs:
    processor: list = field(default_factory=list)
    mc_detail: list = field(default_factory=list)
    mc_summary: list = field(default_factory=list)
    bank: list = field(default_factory=list)
    gl_lines: list = field(default_factory=list)
    gl_opening: list = field(default_factory=list)
    fx: list = field(default_factory=list)
    customers: list = field(default_factory=list)
    checklist: list = field(default_factory=list)
    invoice_lines: list = field(default_factory=list)
    treasury_email: list = field(default_factory=list)
    missing: list = field(default_factory=list)       # (what, ("missing", what))
    missing_files: dict = field(default_factory=dict)  # what -> file name
    read_status: dict = field(default_factory=dict)   # file name -> {"rows": n, "dates": {column: (first, last)}}
    fingerprints: dict = field(default_factory=dict)  # file name -> sha256 hex


def _cell(column, text):
    text = text.strip()
    if column in DECIMAL_COLUMNS:
        return Decimal(text) if text else ZERO
    if column in DATE_COLUMNS:
        return datetime.date.fromisoformat(text) if text else None
    return text


def _read_csv(path, file_name, on_raw=None):
    """Typed rows with `src`; `on_raw(typed, raw)` may add fields computed from the untouched cells."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = []
        for line, raw in enumerate(csv.DictReader(f), start=2):
            row = dict({c: _cell(c, v or "") for c, v in raw.items()}, src=(file_name, line))
            if on_raw:
                on_raw(row, raw)
            rows.append(row)
        return rows


def _normalise_ref(raw):
    """(ref_norm, ref_status), decided on the raw cell before any trimming."""
    if policy.NETWORK_REF.fullmatch(raw):
        return raw, policy.REF_STATUS.exact
    if not raw.strip():
        return None, policy.REF_STATUS.empty
    cleaned = re.sub(r"[\s-]", "", raw).upper()
    if policy.NETWORK_REF.fullmatch(cleaned):
        return cleaned, policy.REF_STATUS.normalised
    return None, policy.REF_STATUS.invalid


def _processor_fields(row, raw):
    row["ref_norm"], row["ref_status"] = _normalise_ref(raw["network_ref"])
    row["net"] = row["amount_usd"] - row["interchange_usd"] + row["scheme_fee_usd"]


def _bank_kind(narrative):
    for kind, pattern in policy.BANK_KIND_PATTERNS:
        if pattern.search(narrative):
            return kind
    return policy.KIND.other


def _sent_on(header):
    """The day of an e-mail DATE header, None when it does not read as a date."""
    try:
        return datetime.datetime.strptime(header, policy.EMAIL_DATE_FORMAT).date()
    except ValueError:
        return None


def _parse_emails(text, file_name):
    messages = []
    for block in _EMAIL_SEPARATOR.split(text):
        headers, body = {}, []
        for line in block.strip().splitlines():
            match = _EMAIL_HEADER.match(line) if len(headers) < 3 and not body else None
            if match:
                headers[match.group(1)] = match.group(2)
            elif headers:
                body.append(line)
        if "SUBJECT" in headers:
            date, subject = headers.get("DATE", ""), headers["SUBJECT"]
            messages.append({"date": date, "subject": subject, "body": "\n".join(body).strip(),
                             "from": headers.get("FROM", ""),
                             "sent_on": _sent_on(date), "src": (file_name, "%s %s" % (date, subject))})
    return messages


def _parse_invoice(text, file_name):
    """Line items between the 'Line items' heading and the rule under them; the total is not a line item."""
    lines, in_items = [], False
    for line in text.splitlines():
        if line.strip().lower().startswith("line items"):
            in_items = True
        elif in_items and line.strip().startswith("---"):
            break
        elif in_items:
            match = _INVOICE_ITEM.match(line)
            if match:
                item = match.group(1)
                lines.append({"item": item, "amount_usd": Decimal(match.group(2).replace(",", "")),
                              "src": (file_name, item)})
    return lines


def _read_status(rows):
    """Rows read and, for each date column the rows carry, its first and last date."""
    dates = {}
    for column in sorted(DATE_COLUMNS & set(rows[0] if rows else ())):
        values = [r[column] for r in rows if isinstance(r.get(column), datetime.date)]
        if values:
            dates[column] = (min(values), max(values))
    return {"rows": len(rows), "dates": dates}


def _mark_missing(inputs, what, file_name):
    inputs.missing.append((what, ("missing", what)))
    inputs.missing_files[what] = file_name


def load(data_dir):
    """Reads every input; an absent or unreadable one is listed in `missing` and loads as empty, never estimated."""
    inputs = Inputs()
    for attr, file_name in policy.INPUT_FILES.items():
        path = os.path.join(data_dir, file_name)
        try:
            with open(path, "rb") as f:
                inputs.fingerprints[file_name] = hashlib.sha256(f.read()).hexdigest()
            if attr == "processor":
                rows = _read_csv(path, file_name, _processor_fields)
            elif attr in CSV_ATTRS:
                rows = _read_csv(path, file_name)
            else:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                rows = (_parse_emails if attr == "treasury_email" else _parse_invoice)(text, file_name)
        except (OSError, UnicodeDecodeError, ValueError, ArithmeticError):
            inputs.fingerprints.pop(file_name, None)
            _mark_missing(inputs, "%s (%s)" % (attr, file_name), file_name)
            continue
        setattr(inputs, attr, rows)
        inputs.read_status[file_name] = _read_status(rows)
    for row in inputs.bank:
        row["kind"] = _bank_kind(row["narrative"])
    if not os.path.isfile(os.path.join(data_dir, policy.PROCESSOR_INVOICE_FILE)):
        _mark_missing(inputs, policy.PROCESSOR_INVOICE_LABEL, policy.PROCESSOR_INVOICE_FILE)
    return inputs
