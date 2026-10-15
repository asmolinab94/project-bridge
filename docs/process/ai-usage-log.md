# AI usage log (case deliverable)

> Clara asks for it: the sequence of prompts or a chat export, plus a note on what was verified by hand and what the
> AI got wrong. Filled in while working, not at the end.

## 2026-10-14

- Claude Code downloaded the attachments from the CFO's email, unzipped them and summarised the brief in `CASO.md`.
  Verified by hand: pending.
- Claude Code (main session) read the full PDF brief and confirmed the summary in `CASO.md` matches it. It read the
  data dictionary, the policy, the Treasury thread and the Mastercard notice.
- The project was opened with Andrés's workflow: investigation proposal, project charter with a deliverables board,
  decision log.
- A read-only agent was launched to analyse the 9 CSVs and list every reconciliation difference with its source rows
  and USD amount. Pending: recompute each leg's totals by hand and check a sample of rows.
- The agent delivered its findings (6 min). The main session recomputed, with its own code, each leg's totals, the
  ledger balances at 30-Sep, the bank balance and the missing entry: everything matched.
- **What the AI got wrong or left out**: the agent did not mention account 3900 (opening balancing figure,
  +258,362.63), which is in the opening balances but not in the account map; the independent verification caught it.
  The agent also saved a helper file in a temporary folder although the brief told it to write nothing (outside the
  project, no effect on the data).
- Pending for Andrés: check 2–3 rows by hand (suggested: PX10000177 sign flip; BS0016/BS0018 duplicate; 24-Sep with
  no entry).
- **Andrés's check by hand**: reviewing `mastercard_clearing_detail.csv`, the net did not add up for him as amount −
  interchange − scheme fee. The session checked all 3,365 rows: the net is amount − interchange **+** scheme fee in
  every one (as the data dictionary defines it); the local→USD conversion is exact in every one. The difference
  Andrés saw is twice the scheme fee (6,377.92 in September). No money is missing.
- Andrés defined the approach: a clean input model and gap alerts before reconciling; exception types with owner,
  action and predefined message.
- Andrés proposed the daily summary vs detail control by settlement date. The session ran it: amount and count agree
  on all 23 days; 31-Aug is only in the summary (the detail starts on 1-Sep). Kept as a gap alert.
- Claude Code drafted the scope document (`entrega/01-PRD-lite.md`) with Andrés's approach and decisions. Pending:
  Andrés's review.
- Andrés asked whether the Mastercard invoice creates ledger movements and whether they are itemised. The session
  checked the ledger, the statement and the close checklist: a single bank entry for the total (1-Oct, account 5100,
  default rule), no accrual in September. Two new rules came out of it: type the bank lines and report missing inputs.
- Andrés proposed classifying each invoice line item (fixed/variable, above/below EBITDA) and reconciling the two
  transaction files for missing rows, rate and amount. The AI corrected that nothing on the invoice goes below EBITDA
  and showed the transaction reconciliation already existed in the findings; Andrés's split between amount and rate
  was adopted.
- Andrés asked to check whether Mastercard settles non-effective transactions. The session crossed processor statuses
  against Mastercard and against the ledger: no authorised or declined transaction was settled or posted. Derived
  findings: 20 hanging authorisations, declined rows with a USD amount (a trap for unfiltered sums), 3 impossible
  dates.
- Andrés spotted that the bridge account accumulates a balance. The session quantified it (funding 1.5M vs outflows
  0.92M; 34 working days of coverage at 1-Oct) and proposed framing it as a question to Treasury, not a judgement.
- Andrés proposed that alerts and the agent recommend when to fund. The session computed daily and weekly burn and
  noted that the next day's debit is already known (today's Mastercard settlement). Open questions saved in
  `PREGUNTAS-pendientes.md`.
- Andrés asked to read the policy one item at a time and turn it into rules. The session wrote `REGLAS-politica.md`
  (16 policy rules + 2 posting rules) with the status of each in the data. It also checked that there are no full
  card numbers: clean; it noted that mistyped references would trigger a naive detector. It flagged a policy
  ambiguity: approval by the "net" amount of an entry that always sums to zero.
- **AI correction**: the session had said the 400,000 entry had no CFO approval. On review at Andrés's request: the
  ledger has no preparer or approver fields; who recorded it is known only from the email. The correct statement is
  "there is no evidence of approval", and the finding is that the policy cannot be verified from the extract.
- Andrés concluded that entries need a creator and an approver for the policy to be verifiable. The AI added the
  nuance that the control probably lives in NetSuite and that roles do not evidence each approval. Kept as a
  requirement.
- Andrés answered questions in the pending-questions file. The AI updated the scope document: pre-checks, policy as
  rules, Treasury view with a funding recommendation, a living scope list, approval risk.
- 2026-10-15: Claude Code drafted the tool's spec and launched two agents in parallel: one reviews the spec critically
  in a context without this conversation (stronger model), the other researches Clara's public visual identity.
- An agent found Clara's public brand guide (2026). The session checked colours and fonts against the site's
  stylesheet and summarised their use in `MARCA-clara.md`; it proposed not using the logo.
- **What the AI got wrong (the spec)**: the critical review, done by another agent without this conversation, found
  that the main session had written two checks that would fail: "balances sum to zero" listing only 7 of the 11
  accounts, and "no card number in the output" without normalising the raw references. Also: an ambiguous 250
  threshold (gross vs net), conditional entries presented as facts, an undefined cut-off date. Every individual
  figure was right. Fixed; two decisions went to Andrés.
- Andrés asked for the before and after balances explained account by account; the session recomputed entry by entry
  and explained them. Andrés chose two "after" columns and approved the spec.
- Andrés asked for everything to be in English, the spec included. The session translated the spec and this log
  without changing their content (the approved Spanish spec stays in git history), and wrote the build plan and task
  list in English.
- An agent was dispatched to build the automated tests before any tool code: it recomputes every verified figure with
  its own script first, and each structural check must be shown failing on a planted violation before it is trusted.
- Andrés asked for the internal project notes in English too, because the logs are evidence of how AI was used. The
  session translated seven notes in place and checked with a script that every figure and id is unchanged (the only
  differences: seven identical "opened" dates merged into one note, and the new decision-log entry). The session
  pushed back on one point: a raw chat export should not be translated, because a translated transcript is no longer
  a record of what happened; it stays in Spanish with an English guide.
- An agent (stronger model, no access to this conversation) built the automated tests before any tool code. It first
  recomputed every verified figure with its own script: all matched, a third independent recomputation. It proved
  each structural check by planting a violation and watching it fail, and it ran the figure tests against a
  throwaway imitation with two planted errors (7 tests went red). The main session re-ran the suite: it fails only
  because the tool does not exist yet, as intended. The agent listed ten details the plan had left open; the session
  wrote its readings into the plan so the implementer does not guess.
- **What the AI missed (the spec)**: the agent noticed the spec escalates only two old items, while the policy says
  every open reconciling item older than 5 business days escalates. The session measured it: about 23 transaction
  differences plus 95 rate rows are older than that at the cut-off date. Taken to Andrés as a decision.
- After Andrés widened the escalation rule, the same test-building agent recomputed the counts on its own: they
  matched the session's exactly. It rewrote the escalation test and showed it fails if escalation is limited to the
  bank and ledger legs, or if data-only flags are allowed to escalate.
- A reviewer agent (stronger model, no access to this conversation, read-only) was launched on the plan, the task list
  and the tests, with one main job: find tests a wrong implementation would still pass.
- **What the AI got wrong (the plan and the tests)**: the reviewer found the plan and tests were not ready to build
  on. Two would have failed a correct tool: the escalation test forbade the policy's second rule (unexplained total
  above 1,000), and the plan defined the cut-off difference in a way that gives 0 instead of 928.31. Several checks
  would have passed a wrong tool: a "take the first candidate" match, an export that writes the same column twice,
  a pre-check module with a single check. It also caught that the plan's web fonts broke the "opens without network"
  rule. The main session fixed the plan and task list; the test-building agent is fixing the tests, with planted
  synthetic cases so each rule has data that can prove it wrong.
- The test-building agent closed every review item. It recomputed the new expected values on its own; one differed
  from the findings file (22 stale authorisations at 5 working days vs "20 older than a week": two different
  measures, not an error). For each new rule it planted the wrong behaviour in a throwaway imitation and confirmed the
  matching test turns red (around twenty planted faults). The main session re-ran the suite (red only for the missing
  tool) and recorded the output formats in the plan. The same reviewer was asked to re-check the fixes.
- Third round of test fixes and Andrés's decision on Controller action folded in by the test-building agent; every
  new rule shown to fail against planted wrong behaviour (76 tests on the imitation). Its two totals for the
  aggregate rule: 0.00 as decided, 11,325.58 had processor-only and Mastercard-only counted as unexplained.
- **What the AI got wrong (the main session)**: while committing a plan change, the session used a command that
  stages every modified file, and it swept a half-finished test file from the other agent into that commit (one
  guard self-test failing in that commit alone). The agent noticed and reported it; its next commit fixed the file.
  The session now stages only the file it changed.
- A new reviewer agent (stronger model, fresh context, read-only) re-checked the plan and tests. It recomputed every
  figure the tests assert on its own, and all of them matched. Its verdict was still **not ready**.
- **What the AI got wrong (the plan and the tests, third review)**: the suite could never turn fully green, because a
  shared base test was itself collected and always errored. The plan had no type for "bank debited a different amount
  than Mastercard's daily net", and the test accepted any type there. Two plan paragraphs defined the unexplained
  total differently, and one of them would have failed a correct tool. The source-line guard accepted "whole file" on
  every row, so "every number traceable" was not really being tested. Four plan sentences could each be read two
  reasonable ways, and each reading changes a count the tests assert (for example, whether to trim spaces around a
  reference before judging it exact: 3,003 or 3,014 exact matches). The main session wrote one-line readings into
  the plan for each. A new test-building agent is fixing the tests.
- The test-fixing agent closed every item, each shown to catch a planted wrong behaviour, and added a test that pins
  the list of difference types to the plan's. Andrés decided that a bank debit differing from Mastercard's daily net
  counts as unexplained («Si porfa» [Yes please]).
- A second short review (new agent, fresh context, read-only) checked only what changed. Its verdict was not ready,
  but only for wording. **What the AI got wrong**: when the session fixed the plan, it rewrote one paragraph on the
  unexplained total but left an older paragraph that still contradicted it, and an old definition of the reference
  check that gives 60 instead of 105. The reviewer also found six tests weaker than the plan they enforce (for
  example, the "lowest reference" rule was accepted either way). The session fixed the plan; the test agent is
  tightening the tests.
- The test agent tightened the six weak tests, each shown to catch its planted wrong behaviour; the session re-ran the
  suite (red only for the missing tool).
- **What the AI got wrong (the main session, process)**: it dispatched the test-fixing agent and the short reviewer
  without first running the brief validator, which the workflow requires before every dispatch. The work itself was
  in scope; the records were incomplete. The session found it when validating the next brief, repaired both records
  and noted the repair in each.
- Implementation started: an agent on a lighter model builds task 1 (the policy constants and the data loader)
  against the tests, without being allowed to edit them.
- Task 2 (the three-leg reconciliation) built by a lighter-model agent; the session re-ran its tests (green except
  the parts that need later tasks). The agent reported that a bank line with no ledger entry, or a manual ledger
  entry with no bank line, was silently ignored because the plan had no type for it. The spec says those lines are
  compared, so this was a gap the plan, the tests and three reviews had all missed. The session added two types to
  the plan (counted as unexplained, the same reasoning as Andrés's earlier decision on bank debits); the test agent
  is adding planted cases for them, and the reconciliation will be updated after task 3.
- Tasks 3, 4 and 5 (close entries and balances, pre-checks, output files) built by lighter-model agents, one brief
  each, never allowed to edit the tests. After each, the session re-ran the tests itself. With the output files in
  place the full suite (108 tests) passes. Decisions the agents took where the plan was silent are listed in their
  reports and go to the independent review; the close tracker's wording is their judgement and goes to Andrés.
- Task 5 was split in two because one brief could not hold it: output files first, then the full page.
- The full page (filters, drill-down to the source row, saved notes, export, Clara's look with the official fonts
  embedded) built by a lighter-model agent; the session re-ran the tests and looked at the screenshots.
- A closing reviewer (stronger model, fresh context, read-only) checked the whole implementation. The figures are
  right on the case data, but its verdict was **not ready**. **What the AI got wrong (implementation)**: leg 3 ties a
  bank line to the ledger by reference only, so a ledger posting with the wrong amount (planted: 90.00 off) leaves
  cash unreconciled with no warning; a damaged input file is treated as empty and the tool then proposes entries from
  that absence (planted: a 911,666.68 entry), which breaks the "never estimate a missing input" rule; the page hides
  each entry's description and missing evidence, and the Controller-action flag Andrés asked to show; the country
  and date filters can hide real breaks; and the same rule is written in two modules. Every one of these passed the
  tests, three reviews of the plan and tests included: the tests checked the figures on the real data, not what
  the tool does when the data is wrong. Repairs go to new briefs with tests first.
- Repair planning after the closing review. The session wrote into the plan how each repair must behave and checked
  it against the case data before asking anything: deriving the pre-checks from the reconciliation keeps their
  counts (2, 1, 22, 3, 105), and the two planted ledger errors surface with exact amounts (90.00 and 40,616.94).
  Two accounting choices went to Andrés instead of being taken by the AI: a ledger posting whose amount differs from
  its bank line counts as unexplained, and a duplicate bank debit the ledger never recorded is proposed as Dr 1250 /
  Cr 1110 rather than Dr 1250 / Cr 2105. **What Andrés caught**: the bank file is the statement of the bridge account
  only, not all of Clara's bank movements; the README now says the tool reconciles that one account and nothing else.
- A test-building agent (stronger model) is writing the planted tests for the repairs before any code changes.
- Repairs built tests-first. A stronger-model agent wrote planted tests for every repair (red against the unrepaired
  code, each shown to catch a planted wrong behaviour, figures recomputed by a script that does not use the tool's
  code); a lighter-model agent then repaired the code in five briefs, never allowed to edit the tests. After each
  brief the session re-ran the suite and checked the tests were untouched. Where the plan was silent, the agents
  reported their choices; the session settled the technical ones in the plan and kept the accounting ones for
  Andrés. Result: 160 tests green; the page now shows every figure with the table of its source rows, a sum row that
  ties to the total and a CSV download. A fresh-context reviewer is checking the repairs before Andrés's demo.
- A fresh-context reviewer checked the repairs: right on the case data, not ready on edited data (the bank-ledger
  pairing mishandled the month cut-off and some leftovers). **What Andrés corrected**: the AI had sent several
  difference types to "unexplained"; Andrés pointed out each has a clear cause and an owner who must fix it (unrecorded
  movements and unsupported postings to Accounting/Treasury, debit differences to Mastercard, transaction differences
  to the processor and Mastercard). The AI challenged it once (the escalation rule could never fire) and conceded:
  the age rule still escalates anything owned and unresolved. Tests for the new reading are written; the code repair
  is next.
- Repair rounds two to four (2026-10-14/15), same loop each time: the session writes the plan readings, a
  stronger-model agent writes planted tests first, a lighter-model agent repairs the code without touching the tests,
  the session re-runs the suite and the real data (cash 0.00, 11 entries every round), and a fresh-context reviewer
  re-plants the previous review's cases. Each review found the next layer: month-end bank-first postings that tied
  cash with no exception row; a file-coverage alarm that fired on correct files and stayed silent on unreadable
  ones; an action sentence that contradicted the tool's own entry. **What Andrés corrected**: (a) "keep realistic
  cases, aim at the 95%" — he asked for a timeline of what can really go wrong with the files before more scenarios
  were added, and one reviewer case was dropped as too rare; (b) the owner is whoever can fix the cause, not an owner
  for the sake of it — then (c) two owners: who fixes it (possibly the processor or Mastercard) and who at Clara
  answers for it, taken from the close checklist Clara already keeps; (d) the leg-1 "unexplained" type is explained
  by the policy (Mastercard's rate is the reference). **What the AI got wrong and the human or the review caught**:
  the AI's first owner table was filler ("Finance Ops" for half the rows); the AI recommended keeping it and had to
  retract; the AI wrote a duplicate-debit action that contradicted its own proposed entry (caught by review); the AI
  first said a subscription key could not be used, then verified it in the official docs before answering the
  second time.

- **2026-10-15 — Agent spec interview, scope answers.** The AI session proposed options with a recommendation and the
  strongest counter-argument for each open point (what the agent reads, how citations show, whether it writes, order
  of work). Andrés chose: reads outputs and raw inputs read-only, clickable citations, no writes in this version, agent
  built last after the tool, the production note and the presentation. Andrés also decided the agent is optional:
  the session raised that the deadline risk sat on the unfinished core, and he reordered the work around it.

- **2026-10-15 — Fourth repair round: tests first, then code.** An Opus agent wrote 27 new tests from the plan block
  (commit 9e5d114); 31 were red on the old code, each for a stated reason. A Sonnet agent then changed only the code
  (commit 90c7a00). The session checked by hand: tests untouched by the code commit, 333/333 green, cash unreconciled
  0.00, 11 proposed entries, eight output files. It also planted a renamed checklist task (T05 → T05A) on a copy of
  the data and opened the page in Chrome: the red "figures are not reliable" warning shows, and failed pre-checks go
  from 6 to 7, the new one naming T05. A fresh Opus reviewer that did not take part in the work was dispatched next.

- **2026-10-15 (night) — Fifth repair round, drafts, page redesign started.** Andrés approved the work order; the session ran it. (1) Fifth repair round, tests first (Opus, commits 883ec8e and 386d086) then code
  (Sonnet, 2797636): a USD conversion error made by the processor now gets a proposed correction; the action
  sentences say who posts what. The test-writing agent caught that the session's own plan sentence for an unpaid
  settlement contradicted the case policy (escalation goes to the Controller after 5 business days, not to
  Mastercard); the session amended the plan (a030dcc) before any code was written. Session check: tests untouched by
  the code commit, 351/351 green, cash unreconciled 0.00, 11 entries. (2) Drafts by Opus agents of the
  path-to-production note, a one-page PRD, and the presentation pack; the drafting agents found that the original PRD
  claimed the tool records preparer and approver (both columns are empty by design) and that two decided features
  (itemised invoice accrual, Treasury view) are not built. A fresh reviewer checks the drafts. (3) Page redesign per
  Andrés: a summary by category on each tab and all rows in one table, no side panel (plan 986bc7e); tests first.

- **2026-10-15/16 — Page redesign built; extras planned.** Tests first (Opus, 3b66755 + 3fc5b35: the session asked
  the test agent to drop a meaningless cash total of 3,095,931.10 before any code), then code (Opus, 1053476). The
  session verified: tests untouched, 369/369 green, and checked the page in Chrome at laptop width (filtering by a
  type gave 95 rows summing to 751.93, equal to the summary). Andrés answered the open points: build the itemised
  invoice and the Treasury view; adjust a Mastercard-owned conversion error and follow the correction (overriding
  the session's "no entry"). Plan a21a330 written for that round.

- **2026-10-15 (day) — Last build rounds before the freeze, and two freezes.** Every change ran the same loop: the
  session wrote a plan block; an Opus agent wrote tests from it (the verifier) before any code; a second agent wrote
  only the code, with the tests untouched; a fresh Opus reviewer that took no part in the work judged the result and
  checked the page in Chrome. Four closing reviews ran (4 to 7). Built this way, from what Andrés asked for after
  looking at the page: waterfalls instead of a pie, the USD each action resolves (counted once), an import file for
  the ERP with every id marked `PROPOSED-`, Data quality as a filterable table, the Reconciliation read by type, the
  headline label "needs action by Clara", and the owners' names taken from the email thread. Suite at the freeze:
  534 tests green; the two entry files fingerprinted (sha256) and unchanged since.
  **What the AI got wrong, and what caught it**:
  (a) the test-writing agent got a sign wrong in one expected figure; it was caught only because the code was right
  and the test failed against it — a reviewer recomputed by hand and confirmed the code (the case data gives
  +9,127.92, not −9,127.92). A passing suite is not proof; a failing one can be the test's fault. 
  (b) the session counted 15 tasks with a named owner; the test-writing agent counted 16 from the file (a quoted comma
  had hidden task T02 from the session's quick parse). The plan was corrected before any code.
  (c) the session itself introduced a regression: hiding the 130 data flags by default on the Reconciliation table
  broke the page's main promise, that "a figure opens the rows that make it up" (Summary figures opened fewer rows
  than they stated). Closing review 5 caught it; a fix round made each figure open exactly the rows it counts, and
  review 6 checked every figure in Chrome.
  (d) review 7 found that blanking an "Assigned person" brought the default name back; one-line fix.
  **What Andrés verified by hand**: he read the page and asked for each change above. Still pending from him: blank
  an Assigned person and reload; check three rows by hand before the presentation; real hours.

- **2026-10-15 (session 2) — Path-to-production note closed to 2 pages; page restyle reopened.** The session updated
  the note with what was built and added the "day-zero close" proposal (two agents, not built; the improvement loop
  proposes each rule with its test and the Controller approves it — Andrés's idea, the session's condition). Checking
  every figure against the frozen run, the session found two errors already in the draft: it said 6 pre-checks fail
  (5 do) and that the demo ships an API key (no agent is built). The note had grown to ~1,900 words against the case's
  1–2 pages; Andrés chose to move the detail to an annex (`entrega/03-annex.md`); the session measured the result
  printed (A4, 11 pt): 2 pages. Andrés found the page "muy plano" (very flat) and asked for a modern style "taking
  [another company] as an example"; the session pushed back on borrowing another company's brand in a submission, and
  he chose the feel only, with an own palette. Restyle runs style-only, with the outputs other than the page required
  byte-identical to the frozen run.

- **2026-10-15 (session 2) — PRD and presentation updated, then reviewed.** The session updated the PRD and the presentation documents; an Opus agent recomputed every figure from the raw files with its own script (it also found stronger evidence for
  the missing 24-Sep entry: Mastercard settled that day and the bank paid it, so only the payable entry was missing).
  A fresh Opus reviewer then checked all eight written deliverables against the frozen run. **What the AI got wrong,
  and the review caught**: the "one-page" PRD was one and a half pages before this session and still over by two
  lines after the first cut; the long PRD said 34 days of cash cover (the tool says 26.11) and that the tool records
  preparer and approver (it leaves them empty by design); the note said two processor entries were missing (one was
  missing, one posted a day late) and described the login-based approval as if built; the annex misdescribed what the Treasury balance excludes. All fixed the same day.

- **2026-10-15 (session 3) — Presentation documents updated.** The presentation documents were updated.

- **2026-10-15 (session 3) — Brief re-read, email drafted, package started.** Re-reading the case brief, the session flagged where the plan had drifted from it. Andrés chose to declare real hours. The session drafted the email to the CFO
  (`entrega/email-to-cfo-DRAFT.md`, not sent) and copied the frozen run's CSVs into `entrega/package/outputs/` (the
  two entry files' SHA-256 match the freeze). A first wording of the email said the payable was wrong "mainly"
  because of the missing 24-Sep journal; the session corrected it before showing it, since that journal is one of
  three causes of similar size.

- **2026-10-15 (session 3) — Hours measured, clean repository, Gmail draft.** The session measured time from the
  session transcripts: 107 messages from Andrés across 11 working windows, about 9 hours of his attention (8.6 counting
  windows of messages less than 30 minutes apart, 9.7 counting each gap up to 15 minutes); 64 agent runs. (The agent figures first given
  here, 19.3 agent-hours and 14.8 hours of wall-clock, counted each agent from its first to its last message, idle
  stretches included; Andrés questioned them, and the corrected figures are in the next entry but one.) It prepared a clean copy of the
  repository for publication (fresh history, local paths replaced), re-ran the 534 tests and compared the eight CSVs
  byte for byte with the frozen run: identical. It drafted the reply to the CFO in Gmail (not sent).

- **2026-10-15 (session 3) — Published to the wrong GitHub account, then corrected.** The AI published the clean
  repository to the terminal's active GitHub account without asking which one was personal; it was the wrong GitHub account.
  Andrés caught it within minutes; the session made that copy private and republished on his personal account,
  https://github.com/asmolinab94/project-bridge. Re-measured his active time more strictly (only the time between
  the AI's last reply and his next message, capped): about 4 hours. The earlier 9-hour figure counted time spent
  waiting on agents.

- **2026-10-15 (session 3) — Agent time re-measured after Andrés questioned it.** Andrés did not believe 15 hours of
  continuous agent work, and he was right: the measure ran from each agent's first to its last message, including
  long idle stretches when an agent was resumed later. Counting only stretches where an agent was actually working
  (no gap over 5 minutes between its messages): 8.8 agent-hours, and some agent working during 8.0 clock hours (3.5
  the night of 14 Oct, 4.5 on 15 Oct). Declared figures: about 8 hours of agents working and about 4 hours of Andrés's
  own attention (measured 3.5 to 4.6, before any reading done outside the chat).
