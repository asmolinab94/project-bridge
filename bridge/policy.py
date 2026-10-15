"""The single declaration of every policy value: tolerances, thresholds, calendar, accounts, posting rules, type codes,
class map, check names, bank kinds. No other module writes these values; they import them from here."""

import datetime
import re
from decimal import Decimal
from types import SimpleNamespace

# --- Tolerances and thresholds (USD) -------------------------------------------------------------------------------
CENT = Decimal("0.01")                 # money is shown and converted to the cent
TOL_TXN = Decimal("0.05")                # per transaction: a smaller difference is rounding
TOL_DAY = Decimal("1.00")                # per daily net settlement
EXPLAIN_THRESHOLD = Decimal("250")       # a difference at or above this gross amount requires an explanation
ESCALATE_UNEXPLAINED = Decimal("1000")   # unexplained aggregate above this escalates
ESCALATE_AGE_WD = 5                      # an open money difference older than this many working days escalates
STALE_AUTH_WD = 5                        # an authorisation older than this many working days is stale
APPROVAL_CONTROLLER = Decimal("10000")   # entry total debits at or above this need the Controller
APPROVAL_CFO = Decimal("100000")         # entry total debits at or above this need the CFO

# --- Calendar ------------------------------------------------------------------------------------------------------
CUTOFF_DATE = datetime.date(2026, 10, 5)  # working day 3 of the close; ageing and escalation count to this date
HOLIDAYS = frozenset([datetime.date(2026, 9, 7), datetime.date(2026, 10, 12)])  # US bank holidays in the period
WEEKEND_FROM = 5                          # date.weekday() from this value is a weekend day
PERIOD_START = datetime.date(2026, 9, 1)
PERIOD_END = datetime.date(2026, 9, 30)


def by_period_end(day):
    """On or before the period's last day: the ledger and bank rows that make up the September balances."""
    return day <= PERIOD_END


def in_leg1_period(clearing_date, matched_to_period_row=False):
    """Leg-1 universe: clearing in September, or (Mastercard side only) clearing later but matched to a September
    processor row."""
    if clearing_date is None:
        return False
    if PERIOD_START <= clearing_date <= PERIOD_END:
        return True
    return matched_to_period_row and clearing_date > PERIOD_END


# --- Accounts and posting rules ------------------------------------------------------------------------------------
ACCOUNTS = {
    "bridge_cash": "1110",
    "card_receivable": "1210",
    "mc_receivable": "1250",
    "mc_payable": "2105",
    "accrued_fees": "2150",
    "funding_clearing": "2300",
    "suspense": "2900",
    "interchange_revenue": "4100",
    "network_fees": "5100",
    "bank_charges": "6150",
    "opening_balancing": "3900",
}
ACCOUNT_ORDER = ("bridge_cash", "card_receivable", "mc_receivable", "mc_payable", "accrued_fees", "funding_clearing",
                 "suspense", "interchange_revenue", "network_fees", "bank_charges", "opening_balancing")

# Ledger entry sources, and the reference (strftime pattern over the clearing day) of the processor feed's daily entry.
GL_SOURCES = {"processor": "PROCESSOR_FEED", "bank": "BANK_FEED", "manual": "MANUAL"}
PROCESSOR_ENTRY_REF = "PROC-%Y%m%d"

# Processor feed, per clearing day: (debit account, credit account, processor column summed).
PROCESSOR_POSTING = (
    ("card_receivable", "mc_payable", "amount_usd"),
    ("mc_payable", "interchange_revenue", "interchange_usd"),
    ("network_fees", "mc_payable", "scheme_fee_usd"),
)

# --- Close: proposed entries and tracker -------------------------------------------------------------------------
APPROVAL_LEVELS = ("standard", "controller", "cfo")


def approval_level(total_debits):
    """The approver an entry needs, by its total debits."""
    if total_debits >= APPROVAL_CFO:
        return APPROVAL_LEVELS[2]
    if total_debits >= APPROVAL_CONTROLLER:
        return APPROVAL_LEVELS[1]
    return APPROVAL_LEVELS[0]


DAY_FORMAT = "%d-%b"   # a day in a title, e.g. 30-Sep
ENTRY_STATUSES = ("proposed", "proposed-conditional")
# Processor errors corrected one entry per type, in this order; the first three and the USD conversion error pair a
# processor row with a Mastercard row. A USD conversion error whose fixer is Mastercard gets its own adjustment entry.
CORRECTION_TYPES = ("fx_rate_diff", "sign_flip", "amount_diff", "processor_duplicate", "processor_only",
                    "mastercard_only", "usd_conversion_error")
SINGLE_ROW_TYPES = frozenset(["processor_duplicate", "processor_only", "mastercard_only"])  # money sits in one row
# Entries that stay conditional, by the difference type they correct, and the evidence they wait for.
CONDITIONAL_EVIDENCE = {
    "suspense_pending_payer": "Payer confirmation (copy of the transfer message) for the unidentified inward receipt",
    "processor_only": "Processor confirmation that these transactions are valid and not yet settled by Mastercard",
}
# Program invoice line items that vary with volume; every other line item is a fixed programme cost.
COST = SimpleNamespace(fixed="fixed", variable="variable")
VARIABLE_INVOICE_ITEMS = frozenset(["Cross-border assessment adjustment"])
TASK_DONE = "Done"
BLOCKED_OUTSIDE = "outside the checklist"   # blocked_by of a Blocked task with no open dependency on the checklist
TASK_BLOCKED = "Blocked"
# Close checklist tasks the tool completes or evidences: task id -> (role, what the tool provides).
TOOL_EVIDENCE = {
    "T02": ("evidences", "Leg 3 lists the clearing days with a missing or misdated processor entry"),
    "T05": ("prepares", "Leg 1 reconciliation, every difference classified with zero residual"),
    "T06": ("prepares", "Leg 2 reconciliation, Mastercard daily net against the bank debit"),
    "T07": ("prepares", "Cash reconciliation, ledger 1110 against the bank statement"),
    "T08": ("evidences", "Payable 2105 before and after the proposed corrections"),
    "T09": ("evidences", "Suspense item with a conditional clearing entry, waiting for the payer confirmation"),
    "T11": ("evidences", "Proposed accrual entry for the Mastercard program invoice"),
    "T12": ("evidences", "Processor invoice reported as a missing input; nothing estimated"),
    "T13": ("evidences", "Proposed entries with supporting rows and the approval level; posting stays outside"),
}

# --- Inputs --------------------------------------------------------------------------------------------------------
# Loaded attribute -> file name. CSVs first, then the two text inputs.
INPUT_FILES = {
    "processor": "processor_transactions.csv",
    "mc_detail": "mastercard_clearing_detail.csv",
    "mc_summary": "mastercard_daily_settlement_summary.csv",
    "bank": "bridge_account_statement.csv",
    "gl_lines": "gl_journal_lines.csv",
    "gl_opening": "gl_opening_balances.csv",
    "fx": "fx_rates_daily.csv",
    "customers": "customers.csv",
    "checklist": "close_checklist.csv",
    "treasury_email": "treasury_email_thread.txt",
    "invoice_lines": "mastercard_fee_notice.txt",
}
# The key fields of a cited input row, shown inline beside the output row that cites it (attr -> the file's columns).
SOURCE_FIELDS = {
    "processor": ("txn_id", "clearing_date", "amount_usd", "amount_local", "fx_rate"),
    "mc_detail": ("network_ref", "clearing_date", "amount_usd", "amount_local", "fx_rate"),
    "mc_summary": ("settlement_date", "currency", "txn_count", "net_settlement_usd"),
    "bank": ("line_id", "posting_date", "debit_usd", "credit_usd", "narrative"),
    "gl_lines": ("je_id", "posting_date", "debit_usd", "credit_usd", "description"),
    "gl_opening": ("account", "account_name", "opening_balance_usd_dr_positive"),
    "fx": ("date", "currency", "local_per_usd"),
    "customers": ("customer_id", "customer_name", "program_country"),
    "checklist": ("task_id", "task", "owner_role", "status_wd3_0900"),
    "treasury_email": ("date", "subject", "body"),
    "invoice_lines": ("item", "amount_usd"),
}
# Inputs whose first source field is the reference a row is known by, quoted to the other side in a drafted message.
REFERENCE_ATTRS = ("processor", "mc_detail", "bank")
# Dated inputs whose rows must reach the first and the last working day of the period (check inputs_cover_period).
# The one period column of each (attr -> column): the others may start later or end earlier on a correct file.
COVERAGE_COLUMNS = {"processor": "clearing_date", "mc_detail": "clearing_date", "mc_summary": "settlement_date",
                    "bank": "posting_date", "gl_lines": "posting_date", "fx": "date"}
FILE_STATUS = SimpleNamespace(read="read", missing="missing")   # per input file, in the run manifest
EMAIL_DATE_FORMAT = "%a %d %b %Y %H:%M"                          # the DATE header of the treasury e-mails
# Inputs the card-number check reads.
CARD_NUMBER_ATTRS = ("processor", "mc_detail", "bank", "gl_lines", "customers", "treasury_email", "invoice_lines")
PROCESSOR_INVOICE_FILE = "processor_invoice.txt"   # expected from the processor; not part of the case pack
PROCESSOR_INVOICE_LABEL = "processor invoice"

NETWORK_REF = re.compile(r"MC\d{13}")  # a valid Mastercard reference once spaces and hyphens are stripped

# Bank line typing: first pattern that matches the narrative wins; no match is "other".
BANK_KINDS = ("settlement", "invoice", "fee", "funding", "receipt", "other")
BANK_KIND_PATTERNS = (
    ("invoice", re.compile(r"(?i)\bINTL INV\b")),
    ("settlement", re.compile(r"(?i)\bSETTL")),
    ("fee", re.compile(r"(?i)\bFEES?\b")),
    ("funding", re.compile(r"(?i)\bTREASURY FUNDING\b")),
    ("receipt", re.compile(r"(?i)^INWARD TRF\b")),
)

# --- Difference types ----------------------------------------------------------------------------------------------
_TYPES_BY_CLASS = {
    "timing": ("month_cutoff", "processor_entry_misdated", "funding_in_transit", "bank_not_yet_posted",
               "settlement_not_debited", "suspense_pending_payer"),
    "real_error": ("processor_duplicate", "bank_duplicate_debit", "sign_flip", "amount_diff", "fx_rate_diff",
                   "processor_only", "mastercard_only", "processor_entry_missing", "invoice_not_accrued",
                   "settlement_amount_diff", "usd_conversion_error", "bank_line_unrecorded", "ledger_entry_unmatched",
                   "ledger_amount_diff", "ledger_posted_late"),
    "data_issue": ("reference_bad", "auth_after_clearing", "auth_stale", "ambiguous_match", "input_missing",
                   "account_unmapped"),
    "auto_cleared": ("rounding",),
}
CLASS_OF = {t: cls for cls, types in _TYPES_BY_CLASS.items() for t in types}
DIFF_TYPES = tuple(CLASS_OF)
# Codes by name, so code refers to `policy.TYPE.sign_flip` and never writes the string: one declaration per code.
TYPE = SimpleNamespace(**{t: t for t in DIFF_TYPES})
CLASS = SimpleNamespace(**{c: c for c in _TYPES_BY_CLASS})
KIND = SimpleNamespace(**{k: k for k in BANK_KINDS})

# The types of a matched processor/Mastercard pair that differs (a rounding one clears itself and is not shown).
PAIR_TYPES = ("month_cutoff", "sign_flip", "amount_diff", "fx_rate_diff", "usd_conversion_error", "rounding")

# Classes whose differences are open items: they age, can escalate and need an explanation above the threshold.
OPEN_CLASSES = ("timing", "real_error")

# Explained means classified with an owner, so no type is unexplained; the aggregate stays a reported figure (0.00).
UNEXPLAINED_TYPES = frozenset()
# Explained is not resolved: every real error needs the Controller's action whatever its age.
CONTROLLER_ACTION_TYPES = frozenset(t for t, cls in CLASS_OF.items() if cls == CLASS.real_error)

# Who fixes a difference: whoever can fix its cause (rounding is cleared automatically and has none).
FIXER = SimpleNamespace(processor="Processor", mastercard="Mastercard", finance_ops="Finance Ops", treasury="Treasury")
_LEG1_TYPES = ("fx_rate_diff", "usd_conversion_error", "amount_diff", "sign_flip", "processor_duplicate",
               "processor_only", "mastercard_only", "reference_bad", "auth_after_clearing", "auth_stale",
               "ambiguous_match", "month_cutoff")
_FINANCE_OPS_TYPES = ("bank_line_unrecorded", "ledger_entry_unmatched", "ledger_amount_diff", "ledger_posted_late",
                      "processor_entry_missing", "processor_entry_misdated", "invoice_not_accrued", "account_unmapped",
                      "month_cutoff")
FIXER_OF = dict(
    [(t, FIXER.processor) for t in _LEG1_TYPES if t not in _FINANCE_OPS_TYPES]
    + [(t, FIXER.mastercard) for t in ("settlement_amount_diff", "bank_duplicate_debit")]
    + [(t, FIXER.finance_ops) for t in _FINANCE_OPS_TYPES]
    + [(t, FIXER.treasury) for t in ("funding_in_transit", "bank_not_yet_posted", "settlement_not_debited",
                                     "suspense_pending_payer")])
# Clara owner: the close-checklist task that covers a difference; its owner_role is read from the checklist at run time.
TASK_OF = dict(
    [(t, "T05") for t in _LEG1_TYPES]
    + [(t, "T06") for t in ("settlement_amount_diff", "bank_duplicate_debit", "settlement_not_debited")]
    + [(t, "T07") for t in ("bank_line_unrecorded", "ledger_entry_unmatched", "ledger_amount_diff",
                            "ledger_posted_late", "funding_in_transit", "bank_not_yet_posted", "account_unmapped")]
    + [("suspense_pending_payer", "T09"), ("invoice_not_accrued", "T11"),
       ("processor_entry_missing", "T02"), ("processor_entry_misdated", "T02")])
# input_missing: the missing file's sender fixes it, and the task that receives the file covers it.
INPUT_SENDERS = {
    INPUT_FILES["processor"]: (FIXER.processor, "T01"), PROCESSOR_INVOICE_FILE: (FIXER.processor, "T12"),
    INPUT_FILES["mc_detail"]: (FIXER.mastercard, "T04"), INPUT_FILES["mc_summary"]: (FIXER.mastercard, "T04"),
    INPUT_FILES["invoice_lines"]: (FIXER.mastercard, "T04"), INPUT_FILES["fx"]: (FIXER.mastercard, "T04"),
    INPUT_FILES["bank"]: (FIXER.treasury, "T03"), INPUT_FILES["treasury_email"]: (FIXER.treasury, "T03"),
    INPUT_FILES["gl_lines"]: (FIXER.finance_ops, "T02"), INPUT_FILES["gl_opening"]: (FIXER.finance_ops, "T02"),
    INPUT_FILES["customers"]: (FIXER.finance_ops, "T10"), INPUT_FILES["checklist"]: (FIXER.finance_ops, "T21")}
# What the fixer does, one sentence per type (rounding clears itself).
_POSTED_BY_FINANCE_OPS = ("; Finance Ops posts the proposed correction and the feed does not post the resent "
                          "file")
ACTION_OF = {
    "month_cutoff": "Confirm it clears in October; no entry",
    "processor_entry_misdated": "Post the processor entry on its clearing day and reverse the October posting",
    "funding_in_transit": "Confirm the bank credits the transfer in October; no entry",
    "bank_not_yet_posted": "Confirm the bank posts the payment in October; no entry",
    "settlement_not_debited": "Confirm the bank debits the settlement; still open after 5 business days, it escalates "
                              "to the Controller; no entry",
    "suspense_pending_payer": "Get the payer's confirmation, then clear the suspense receipt to the customer",
    "processor_duplicate": "Processor removes the duplicate row and resends the file" + _POSTED_BY_FINANCE_OPS,
    "bank_duplicate_debit": "Post the proposed receivable from Mastercard now; follow the Mastercard credit and clear "
                            "the receivable when it arrives",
    "sign_flip": "Processor corrects the sign and resends the file" + _POSTED_BY_FINANCE_OPS,
    "amount_diff": "Processor corrects the local amount and resends the file" + _POSTED_BY_FINANCE_OPS,
    "fx_rate_diff": "Processor re-rates at Mastercard's rate and resends the file" + _POSTED_BY_FINANCE_OPS,
    "processor_only": "Processor confirms the transactions are valid and waits for Mastercard to settle them; Finance "
                      "Ops posts the proposed conditional entry once the processor confirms",
    "mastercard_only": "Processor explains why Mastercard cleared transactions it never sent; Finance Ops posts the "
                       "proposed correction",
    "processor_entry_missing": "Post the missing processor entry for the clearing day",
    "invoice_not_accrued": "Accrue the Mastercard program invoice",
    "settlement_amount_diff": "Mastercard explains why the settlement differs from its summary and corrects it",
    "usd_conversion_error": "Processor re-converts at Mastercard's rate and resends the file" + _POSTED_BY_FINANCE_OPS,
    "bank_line_unrecorded": "Record the bank movement in the ledger",
    "ledger_entry_unmatched": "Find the bank movement for this entry, or reverse the entry",
    "ledger_amount_diff": "Correct the ledger entry to the amount the bank moved",
    "ledger_posted_late": "Move the posting into September; post the proposed entry and reverse the October one",
    "reference_bad": "Processor resends the rows with a valid Mastercard reference",
    "auth_after_clearing": "Processor corrects the authorisation or clearing date and resends the file",
    "auth_stale": "Processor clears or voids the old authorisation",
    "ambiguous_match": "Processor adds the Mastercard reference so the rows can be matched",
    "input_missing": "Send the missing file; nothing is estimated in its place",
    "account_unmapped": "Map the account in the chart and rerun",
}
# Sentences that differ by fixer for the same type: (type, fixer) -> sentence, used instead of ACTION_OF.
ACTION_BY_FIXER = {
    ("usd_conversion_error", FIXER.mastercard): "Post the proposed adjustment now; Mastercard corrects its conversion "
                                                "and the settlement; Treasury follows the correction and clears the "
                                                "adjustment when it arrives",
}

# --- Treasury view ---------------------------------------------------------------------------------------------------
TREASURY_HORIZON_WD = 5            # the suggested transfer covers this many business days
TREASURY_BUFFER_K = Decimal("2")   # standard deviations of buffer; illustrative, Treasury sets the real target

# --- Pre-check names -----------------------------------------------------------------------------------------------
# Cash reconciliation line kinds, in the order cash_recon.csv writes them.
CASH_LINES = ("ledger_balance", "reconciling_item", "bank_balance", "unreconciled")
# Reconciling item text by which side is on or before 30-Sep ("ledger first" is True when it is the ledger).
TRANSIT_TEXT = {True: "In the ledger, not yet in the bank (%s)", False: "In the bank, not yet in the ledger (%s)"}
CHECKS = ("summary_vs_detail", "clearing_days_vs_entries", "settlements_vs_debits", "net_formula", "statuses",
          "stale_authorisations", "impossible_dates", "references", "card_numbers", "missing_inputs", "cash_reconciled",
          "inputs_cover_period", "checklist_tasks_owned")

# How a Mastercard reference was read, and how a processor row was matched.
REF_STATUSES = ("exact", "empty", "normalised", "invalid")
REF_STATUS = SimpleNamespace(**{s: s for s in REF_STATUSES})
MATCH_METHODS = ("exact", "normalised", "fuzzy")
MATCH = SimpleNamespace(**{m: m for m in MATCH_METHODS})
CHECK = SimpleNamespace(**{c: c for c in CHECKS})   # pre-check names by name

PROCESSOR_STATUSES = ("CLEARED", "AUTHORIZED", "DECLINED")  # only the first carries money
STATUS = SimpleNamespace(**{s: s for s in PROCESSOR_STATUSES})
CARD_NUMBER = re.compile(r"\d{13,19}")   # a full card number, searched after spaces and hyphens are stripped

# --- Pending actions and drafted messages ----------------------------------------------------------------------------
OUTSIDE_FIXERS = (FIXER.mastercard, FIXER.processor)   # a difference they fix waits on someone outside the company
NO_TOOL_EVIDENCE = "No tool evidence; depends on the owner"
# Tasks with no exception of their own that the tool still evidences: the entries they lack (None = every proposed
# entry, awaiting approval; an account = the entries with a line on it, and its roll-forward).
EVIDENCE_ENTRIES = {"T13": None, "T08": ACCOUNTS["mc_payable"]}
# The lines of the Mastercard payable bridge, in the order the Summary draws them.
BRIDGE_LINES = ("ledger", "entries", "result", "settlement", "timing", "difference")
BRIDGE_LINE = SimpleNamespace(**{n: n for n in BRIDGE_LINES})
# What a task lacks, in words, for the types a count and a net would not explain: {usd} (net), {day} (the day after
# the period), {keys}. Other types read as a count of exceptions with their net.
FINDING_WORDS = {
    "funding_in_transit": "{usd} USD funding in transit, a reconciling item to confirm on {day}",
    "input_missing": "{keys} (not received)",
}
# Data quality: the unit a check counts in (singular, plural), rows unless said here; the checks with no rows of their
# own, shown as a pass/fail line only.
CHECK_UNITS = {"clearing_days_vs_entries": ("day", "days"),
               "settlements_vs_debits": ("settlement day or debit", "settlement days or debits")}
ROW_UNIT = ("row", "rows")
CHECKS_WITHOUT_ROWS = ("summary_vs_detail", "net_formula", "missing_inputs", "cash_reconciled", "inputs_cover_period",
                       "checklist_tasks_owned")
# What a failed check means for the result, one sentence per check.
CHECK_MEANING = {
    "summary_vs_detail": "Mastercard's daily summary disagrees with its own clearing detail, so leg 2 compares the "
                         "bank with a summary that may be wrong.",
    "clearing_days_vs_entries": "The ledger lacks or misdates the processor entry of some clearing days, so the "
                                "payable and the processor balances are wrong until the proposed entries are posted.",
    "settlements_vs_debits": "Some settlement days have no bank debit, or a debit has no settlement day, so leg 2 may "
                             "be incomplete.",
    "net_formula": "Some net amounts do not follow the processor's formula, so a leg-1 net difference may come from "
                   "the file and not from Mastercard.",
    "statuses": "Some rows carry a status the tool does not know; they are left out of the reconciliation.",
    "stale_authorisations": "Old authorisations are still open; they carry no money in the result, but the processor "
                            "should clear or void them.",
    "impossible_dates": "Some rows are authorised after they cleared, so their dates cannot be trusted and their age "
                        "may be wrong; they carry no money.",
    "references": "Some processor rows have a missing or malformed Mastercard reference; the tool matches them on "
                  "card, currency, amount and date, and flags a match it cannot make with certainty.",
    "card_numbers": "A full card number appears in an input; remove it from the file before sharing it.",
    "missing_inputs": "An expected file is missing, so whatever depends on it is not computed and nothing is "
                      "estimated in its place.",
    "cash_reconciled": "Ledger and bank differ by an amount the cash reconciliation does not account for.",
    "inputs_cover_period": "An input does not reach the first or last working day of September, so rows at the edge of "
                           "the period may be missing.",
    "checklist_tasks_owned": "A checklist task the tool relies on is missing or has no owner, so some owners shown "
                             "are blank.",
}

# A drafted message is never sent: the person copies it or downloads it. Templates by key: who it goes to, the
# difference types (and, for the conversion error, the fixer) or the failed check it covers, and the words.
DRAFT_NOTICE = "Draft — not sent"
DRAFT_LINE = "- {key}: {type}, {gross} USD, {day}{cited}"   # gross, never net; cited = the other rows' references
DRAFT_DAY_LINE = ("- {day}: the summary shows {s_count} transactions, net {s_net} USD; the clearing detail shows "
                  "{d_count}, net {d_net} USD")
DRAFT_FRAME = "{notice}\nTo: {to}\nSubject: {subject}\n\nHello,\n\n{intro}\n\n{rows}\n\n{ask}\n\nThank you."
DRAFT_TEMPLATES = {
    "mastercard_summary_mismatch": dict(
        to=FIXER.mastercard, check=CHECK.summary_vs_detail, types=(),
        subject="Daily settlement summary does not match the clearing detail",
        intro="The daily settlement summary and the clearing detail we received do not agree:",
        ask="Please confirm which of the two is right and resend the corrected file."),
    "mastercard_charges_unmatched": dict(
        to=FIXER.mastercard, types=("mastercard_only",),
        subject="Charges cleared with no record at the processor",
        intro="These transactions cleared at Mastercard and the processor never sent them to us:",
        ask="Please send the supporting detail for each one."),
    "mastercard_duplicate_debit": dict(
        to=FIXER.mastercard, types=("bank_duplicate_debit",),
        subject="Settlement debited twice",
        intro="Our bank statement shows the same settlement debited twice:",
        ask="Please credit the second debit back, or tell us why it is owed."),
    "mastercard_conversion_error": dict(
        to=FIXER.mastercard, types=("usd_conversion_error",), fixer=FIXER.mastercard,
        subject="USD conversion that does not follow the clearing rate",
        intro="The USD amount of these clearing rows is not their local amount converted at their own rate:",
        ask="Please correct the conversion and the settlement."),
    "processor_resend_duplicates": dict(
        to=FIXER.processor, types=("processor_duplicate",),
        subject="Duplicate rows in the transaction file",
        intro="The file holds the same transaction more than once:",
        ask="Please remove the duplicate rows and resend the file."),
    "processor_sign_flips": dict(
        to=FIXER.processor, types=("sign_flip",),
        subject="Transactions with the wrong sign",
        intro="Mastercard clears these transactions with the opposite sign to the file:",
        ask="Please correct the sign and resend the file."),
    "processor_amount_and_rate": dict(
        to=FIXER.processor, types=("amount_diff", "fx_rate_diff", "usd_conversion_error"), fixer=FIXER.processor,
        subject="Local amount or exchange rate that differs from Mastercard's",
        intro="The local amount, the exchange rate or the USD conversion of these transactions differs from the "
              "clearing:",
        ask="Please re-rate at Mastercard's rate and resend the file."),
    "processor_misdated_clearing": dict(
        to=FIXER.processor, types=("month_cutoff",),
        subject="Transactions cleared in September that Mastercard cleared in October",
        intro="The file dates these transactions in September; Mastercard cleared them in October:",
        ask="Please confirm the clearing date of each one."),
}

# --- Summary waterfalls ----------------------------------------------------------------------------------------------
# The difference types a waterfall draws as steps, in this order. Leg 1 always draws the first seven (a type with no
# row shows 0.00); any other leg-1 or leg-2 type is drawn only when it has rows.
WATERFALL_TYPES = {
    1: ("processor_duplicate", "sign_flip", "amount_diff", "fx_rate_diff", "month_cutoff", "processor_only",
        "mastercard_only", "usd_conversion_error", "rounding"),
    2: ("bank_duplicate_debit", "settlement_amount_diff", "settlement_not_debited", "rounding"),
}
WATERFALL_ALWAYS = WATERFALL_TYPES[1][:7]
# One order of the difference types wherever they are listed: the waterfalls', then the rest as declared.
TYPE_ORDER = tuple(dict.fromkeys(WATERFALL_TYPES[1] + WATERFALL_TYPES[2] + DIFF_TYPES))
# The data flags the Detailed view hides until asked for: leg 1's, which carry no money (a missing input is a cost).
HIDDEN_FLAG_TYPES = tuple(t for t in _LEG1_TYPES if CLASS_OF[t] == CLASS.data_issue)
# How a step reads on the page: a total, an error, a proposed correction, one waiting for evidence, an amount owed, and
# an end that ties (0.00 left, or landing on the other side's total to the cent).
TONE = SimpleNamespace(total="total", wrong="wrong", fix="fix", waiting="waiting", owed="owed", ties="ties")

# --- ERP file: the proposed entries in the ledger's own columns, ready to import, never posted ----------------------
ERP_FILE = "proposed_journal_lines.csv"
GL_LINE_COLUMNS = ("je_id", "posting_date", "source", "account", "account_name", "debit_usd", "credit_usd",
                   "description", "reference")
ERP_JE_PREFIX = "PROPOSED-"
ERP_SOURCE = "PROPOSED_NOT_APPROVED"
ERP_REFERENCE = "approval {level}; status {status}"

# --- Named owners: who the email thread names in a checklist role -----------------------------------------------------
# Every "Name (Role)" on a FROM: header line of the treasury e-mails names the person in that role; the role stays the
# owner of record and the name is who to contact. A combined role takes the person of the role named here; a role the
# e-mails never state gets no name (nothing is invented). Customer Success names no task, only a drafted message.
NAMED_PAIR = re.compile(r"([A-Z][a-z]+(?: [A-Z][a-z]+)+) \(([^)]+)\)")
COMBINED_ROLES = {"Treasury / AR": "Treasury"}   # she raised the suspense item (24 Sep)


def people(emails):
    """{role: (person, the verbatim "Name (Role)" fragment it is read from)}, from the e-mails' FROM: lines."""
    found = {}
    for message in emails:
        for person, role in NAMED_PAIR.findall(message.get("from", "")):
            found.setdefault(role, (person, "%s (%s)" % (person, role)))
    found.update({combined: found[role] for combined, role in COMBINED_ROLES.items() if role in found})
    return found


# --- Explanations: the text behind every "i" on the page, by key; the page reads them as data ------------------------
SCREENS = ("Summary", "Data quality", "Reconciliation", "Pending actions", "Close")
GLOSSARY = {
    "screen.Summary": "The month at a glance: each pair of records compared, how the totals walk from one side to the "
                      "other, and the Mastercard payable against what Mastercard says is owed.",
    "screen.Data quality": "Checks run on the input files before any figure is trusted, and which files were read, "
                           "with the first and last date each one covers.",
    "screen.Reconciliation": "Every difference found between two records, one row each, with its type, who fixes it "
                             "and what to do. Grouped adds them up by day or by account.",
    "screen.Pending actions": "The close checklist, task by task: what the tool found that each task still needs, "
                              "how much money closing it resolves, and messages drafted for whoever must act.",
    "screen.Close": "Proposed journal entries, account balances before and after them, the cash reconciliation and "
                    "the Treasury view. Click a line to see the input rows behind it.",
    # Summary figures (one text per figure name; the same name on two legs means the same thing)
    "figure.processor_rows": "Cleared processor transactions of the month and their USD amount, from "
                             "processor_transactions.csv.",
    "figure.mastercard_rows": "Mastercard clearing rows of the month, plus the ones cleared early in the next month "
                              "that match a processor row of the month, from mastercard_clearing_detail.csv.",
    "figure.matched_equal": "Processor and Mastercard rows paired by reference that agree to the cent; nothing to do.",
    "figure.matched_diff": "Pairs that differ: sign, local amount, FX rate, USD conversion or clearing month. Net is "
                           "processor minus Mastercard.",
    "figure.processor_duplicate": "Processor rows that repeat a transaction already in the file; Mastercard cleared "
                                  "it once.",
    "figure.processor_only": "Processor rows with no Mastercard row: sent to us as cleared, never settled by "
                             "Mastercard.",
    "figure.mastercard_only": "Mastercard rows with no processor row: charged to us, never reported by the processor.",
    "figure.settlement_days": "Mastercard's daily settlement summary, settlement days 31-Aug to 30-Sep, with their net "
                              "amount; each is debited by the bank on the next working day.",
    "figure.paired": "Settlement days with a bank debit on the expected day.",
    "figure.unpaired": "Settlement days with no bank debit yet; the amount is still owed to Mastercard.",
    "figure.duplicate_debits": "Bank debits that repeat a settlement reference already debited: money paid twice.",
    "figure.ledger_1110": "Balance of the bridge cash account 1110 in the ledger at the period end.",
    "figure.bank_balance": "Closing balance on the bridge account's bank statement at the period end.",
    "figure.reconciling_items": "Movements on one side only because of timing across the period end; they clear "
                                "next month.",
    "figure.unreconciled": "Ledger minus reconciling items minus bank. It must be 0.00; anything else is a cash "
                           "error.",
    "figure.exceptions": "Every difference on this pair of records, real errors, timing and data issues, with its net "
                         "amount.",
    "figure.escalates": "Open money differences older than the escalation limit in working days; they go to the "
                        "Controller.",
    "figure.waiting_outside": "Differences only Mastercard or the processor can fix; drafted messages wait on Pending "
                              "actions.",
    # The payable bridge
    "bridge.ledger": "The 2105 balance in the ledger at the period end. A payable should be a credit; a debit means "
                     "entries are missing or wrong.",
    "bridge.entries": "What the proposed entries move on 2105, debit minus credit.",
    "bridge.result": "The 2105 balance once the proposed entries are posted, shown as a credit.",
    "bridge.settlement": "Mastercard settlement days of the month the bank had not yet debited at the period end, from "
                         "Mastercard's daily summary.",
    "bridge.timing": "Transactions of the month that Mastercard cleared the next month; Mastercard's own file says "
                     "they are owed.",
    "bridge.difference": "Ledger after the entries minus what Mastercard's files say is owed. 0.00 means the payable "
                         "is right.",
    # Waterfalls and their steps
    "waterfall.1": "How the processor's total for the month becomes Mastercard's. Each step is the gross USD of one "
                   "kind of difference; a click opens its rows, whose gross is processor minus Mastercard.",
    "waterfall.2": "How Mastercard's settlement total becomes what the bank actually debited.",
    "waterfall.3": "How the 2105 payable in the ledger, once corrected, reaches what Mastercard says is owed.",
    "waterfall.bank_debits": "Settlement debits on the bank statement for the month's settlement days, duplicates "
                             "included.",
    "waterfall.entries_confirmed": "The 2105 lines of the proposed entries that need no further evidence.",
    "waterfall.entries_waiting": "The 2105 lines of entries that wait for evidence. Until it arrives, this amount is "
                                 "the payable's difference.",
    "type.processor_duplicate": "The processor sent the same transaction twice; the extra row is removed.",
    "type.sign_flip": "The processor shows a sale as a refund or the reverse; Mastercard has the opposite sign.",
    "type.amount_diff": "The local-currency amount differs between processor and Mastercard.",
    "type.fx_rate_diff": "The processor converted to USD at a rate other than Mastercard's.",
    "type.usd_conversion_error": "The USD amount is not the local amount converted at the row's own rate.",
    "type.month_cutoff": "Transactions of the month that Mastercard cleared the next month. They are in both totals, "
                         "so they move this walk by 0.00; they are owed as timing on 2105.",
    "type.processor_only": "Transactions only the processor has; their entry waits for the processor's confirmation.",
    "type.mastercard_only": "Transactions only Mastercard has; the processor must explain them.",
    "type.rounding": "Differences within the rounding tolerance; cleared automatically.",
    "type.bank_duplicate_debit": "The bank debited the same settlement twice; the second debit is recovered from "
                                 "Mastercard.",
    "type.settlement_amount_diff": "The bank debited an amount other than Mastercard's settlement net.",
    "type.settlement_not_debited": "Settlement days the bank has not debited yet.",
    # Pending actions
    "pending.resolves": "Net USD of the differences a task closes, by pair of records. A task with only proposed "
                        "entries shows what they move on 2105. The total counts each difference once.",
    # Column headers
    "column.date": "The date the difference counts from: the transaction, settlement or posting day.",
    "column.type": "What kind of difference it is.",
    "column.cls": "Real error, timing difference, or data issue (carries no money).",
    "column.gross": "Size of the difference before fees, in USD.",
    "column.net": "Size of the difference after interchange and scheme fees, in USD.",
    "column.age_wd": "Working days from the difference's date to the close cut-off.",
    "column.escalates": "Yes when an open money difference is older than the escalation limit.",
    "column.who_fixes": "Whoever can fix the cause: processor, Mastercard, Finance Ops or Treasury.",
    "column.clara_owner": "The role that owns the close-checklist task covering this difference, and the person the "
                          "e-mail thread names in that role, where it does.",
    "owner.named": "The name comes from a FROM: line of treasury_email_thread.txt that states the person and the role, "
                   "such as \"Lucia Ferreira (Treasury)\". The role stays the owner of record; the name is who to "
                   "contact. A role the e-mails never state has no name. Treasury / AR shows the Treasury person; the "
                   "e-mails name no AR person.",
    "column.action": "What the person who fixes it has to do.",
    "column.src": "The input file and line this row comes from. Open it to see the row itself.",
    "column.count": "How many rows.",
    "column.debit": "Debit amount of the line, USD.",
    "column.credit": "Credit amount of the line, USD.",
    "column.status": "Proposed, or proposed on a condition: evidence still missing.",
    "column.approval_level": "Who must approve the entry, by its total debits.",
    "column.before": "Ledger balance at the period end, debit positive.",
    "column.after_confirmed": "Balance after the entries that need no further evidence.",
    "column.after_all": "Balance after every proposed entry.",
    "column.amount": "The line's amount, USD; positive when it makes the ledger exceed the bank.",
    "column.passed": "Whether the check passed.",
    "column.detail": "What the check found, in short.",
    "column.balance": "Bank balance at the end of the day.",
    "column.mc_debits": "Mastercard settlement debits that day, duplicates left out.",
    "column.days_of_coverage": "Closing balance divided by the average daily Mastercard debit.",
}
