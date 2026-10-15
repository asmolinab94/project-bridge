# Charter — Clara Finance Engineer case ("Project Bridge")

<!-- Opened on 2026-10-14 with /base:discover, from Andrés's seed. Drivers and board proposed by the session;
     Andrés corrects them. -->

## Identity

- **name**: Clara Finance Engineer case
- **company**: personal (bundle personal)
- **question or objective**: submit the Clara case on 2026-10-21 — a reconciliation and
  close tool that works, with Andrés's judgement visible in every decision
- **status**: active
- **records**: `project records/projects/clara-caso-finance/`

## Tablero de avance

- **unit**: one case deliverable (what the brief's "What to submit" section asks for, plus the presentation); every row opened on 2026-10-14

| Unit | not started | investigating | scope decided | building | verified | delivered |
|---|---|---|---|---|---|---|
| Data findings: what breaks and by how much | | | x | | | |
| PRD-lite, Part 0 | | | | x | | |
| Reconciliation tool, Part 1 | | | | x | | |
| Close: entries, balances, cash, close tracker, Part 2 | | | | x | | |
| Path-to-production note, Part 3 | | | | x | | |
| AI usage log | | | | x | | |
| presentation materials | | | | x | | |

## Drivers (1-2)

| # | Metric | Baseline | Target | How it is measured | Which decision it serves |
|---|---|---|---|---|---|
| 1 | Submission figures traceable to source rows | 2026-10-14: 0 | 100 % | Every figure shown carries its source row id; a sample is checked by hand before submitting | Whether the tool is ready to submit |
| 2 | Submitted on time and within the requested time | 2026-10-14: nothing submitted | Submitted on 2026-10-21, with actual hours declared | Date of the email to the CFO and hours noted in `registro-ia.md` | What to cut if time runs short |

## Dogfood

- **what it runs on**: the case's synthetic data pack (`insumos/datos/`)
- **what is exercised end-to-end**: open the tool as an analyst, reconcile the three legs, filter exceptions, drill
  down to the source row, export, and see entries and balances before and after
- **environment**: local, on Andrés's machine (the personal bundle declares no test environments)
- **what it reports**: totals per leg and per difference type, which must agree with the verified findings

## Specialists

| Domain | Agent |
|---|---|

## Scope

- **repos it touches**: `project-bridge` (decided in the scope,
  Part 0)
- **out of scope**: data from any employer or client; publishing anything externally without
  asking; sending emails to Clara without Andrés's approval
