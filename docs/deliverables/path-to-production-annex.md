# Project Bridge — path to production, annex

*Detail behind `03-path-to-production.md`. Figures from the tool's run on the case data pack.*

## A. Customers were billed on processor errors

September statements went out (`close_checklist.csv`, T24, Done) from a receivable built on the processor feed. So
refunds were billed as purchases (USD 2,540.18, 4 customers), duplicates billed twice (USD 3,640.35), a stale BRL rate
overcharged 14 customers (USD 762.72), and five Mastercard-only transactions were never billed (USD 2,066.18)
(`proposed_entries.csv`, 1210 lines of E06, E07, E09, E11). The entries fix the ledger, not the customer. Next step,
outside this tool: Billing, T24's owner, issues credit notes and re-bills from the same exception rows, which carry
the customer.

## B. The USD 400,000 prefunding is in transit, and how we know

The ledger shows USD 400,000 more cash in the bridge account (1110) than the bank on 30 Sep. Three sources agree that
the difference is timing, not an error: the Controller's manual entry TR-20260930 (30 Sep, 1110 against Treasury
Funding Clearing 2300, reference TRF0930); her email of 30 Sep 17:30 ("sending USD 400,000 of prefunding today but
the bank will credit it on 1 Oct"); and the bank credit BS0032 on 1 Oct for exactly USD 400,000 with the same
reference. The tool therefore treats it as a reconciling item that clears on 1 Oct (T07). Three caveats:

1. **We see the money arrive, not leave.** The treasury account's statement is not an input, so the 30 Sep outflow
   is unverified. T17 (2300 against the treasury ledger) closes that.
2. **The entry sits in bank cash.** Booking a transfer the bank has not received into 1110 overstates the bridge
   account's balance at month end. A cash-in-transit account, cleared on 1 Oct, keeps 1110 equal to the bank. The
   amount is right; the account is the Controller's call.
3. **October can double-count it.** The email says the bank feed "should skip it when it lands". If the feed books
   BS0032 anyway, October's 1110 carries the USD 400,000 twice. Through 2 Oct the feed has not booked it; check again
   in the October close.

The Controller booked this entry herself, and the journal extract does not say who created or approved it
(`gl_journal_lines.csv`, TR-20260930): the NetSuite requirement in the note exists for entries like this one.

## C. Controller and Treasury detail

- **Why the payable was a debit.** A missing 24-Sep processor entry (USD 44,884.41 to the payable), a 30-Sep one
  posted in October (USD 45,331.47) and a duplicate bank debit (USD 40,616.94) left the payable at a debit of
  USD 70,588.66 (`proposed_entries.csv`, E01–E03; `balances.csv`, 2105).
- **Itemised Mastercard invoice (E05).** Four lines to 5100 and the total, USD 8,412.30, to 2150, reversed on 1-Oct.
  We propose the cross-border assessment in its own sub-account as a variable cost; the chart of
  accounts has none, so it sits on 5100 with the three fixed programme fees until the Controller opens one.
- **Treasury view** (`treasury.csv`). Daily balance from the statement; the duplicate debit is left out of the Mastercard debits and their average; average daily
  Mastercard debit USD 43,973.93; days of coverage 26.11 at 30 Sep. Suggested weekly transfer USD 255,875.54 = five
  days' average debit plus two standard deviations × √5. The two-deviation buffer is illustrative; Treasury sets the
  real target.
- **Items open over 5 business days:** 121 rows, 118 of them for the processor to fix (`exceptions.csv`).

## D. Known gaps, in full

1. **Analyst notes are lost on rerun.** Assigned person, status and comment live in one browser, keyed to source
   line numbers; a corrected file orphans them, and nobody else sees them. Fix: a shared table keyed by business
   reference (e.g. PX10000849, BS0018), with author and time.
2. **No run-to-run comparison.** Each run stands alone. Fix: keep every run and show new, resolved, changed and
   still-open items with age — what makes a daily reconciliation worth reading.
3. **Pre-checks warn instead of block,** and the manifest lacks who ran and reviewed it.
4. **The conversation lives outside the tool.** Much of September's evidence is in email: the Mastercard ticket, the
   payer of the USD 12,500, the prefunding, the unaccrued invoice. Today the tool drafts the message and a person
   sends it, then reads the reply and updates the status by hand. Fix: connect email and Slack. Send each drafted
   message from the exception it belongs to, read the replies in that thread, attach them as evidence, and propose
   the status change ("Mastercard confirmed the duplicate on MCS-88213: mark T06 ready for the credit entry"). The
   owner accepts or rejects each proposal; a reply never closes an item or posts an entry by itself, because the
   Controller's rule is that nothing reaches the ledger without her approval, and because an email is untrusted
   input: anyone can write "this is resolved". The tracker then shows who was asked, when, and what they answered,
   and the age of each item counts from the last unanswered message.
