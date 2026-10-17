# Data dictionary and transformation contract

The published source CSV schema is preserved in the runtime provenance record. Raw files are read as data only; no upstream notebooks/scripts execute.

| Canonical table | Grain / key | Principal fields |
|---|---|---|
| fighters | one source fighter / `fighter_id` | name, source URL; ID is the source URL identifier, not the name |
| events | one source event / `event_id` | event name, day-resolution date, location, source URL |
| fights | one eligible bout / `fight_id` | event ID, ordered competitor IDs, normalized division, scheduled/completed rounds, binary result, method, final-round elapsed seconds, total duration, source URL |
| rounds | competitor × bout × round | significant strikes/takedowns and distance/clinch/ground landed/attempted, knockdowns, submission attempts, control seconds, round exposure |
| stats | competitor × bout | totals of the preserved round fields; missing if any constituent optional field is missing |
| exclusions | one rejected input fight row | source fight ID, event, bout and explicit reason |
| features | one bout before its date | earlier-date A−B predictors, eligibility, target, event date, context |

Source mappings: `SIG.STR.` → `sig_landed/sig_attempted`; `TD` → `td_landed/td_attempted`; `KD` → knockdowns; `SUB.ATT` → submission attempts; `CTRL` → control seconds. `DISTANCE/CLINCH/GROUND` are recorded **strike counts**, not measured time in combat states.

All action counts must be nonnegative integers and landed ≤ attempted. Final-round time is parsed from `mm:ss` with seconds <60 and duration `(completed_rounds−1)*300 + finish_time >0`. For standard formats each completed earlier round contributes 300 seconds. Control cannot exceed observed round exposure. Every retained bout requires exactly two unique competitor records in every completed round. Fighter/event references and dates must join unambiguously.

Missing tokens, including `---`, remain missing. Essential strike/takedown pairs are required; a bout missing them is excluded because metric exposure cannot be reconstructed reliably. Optional control is not zero-filled. At zero attempts, a success/defense ratio is unobserved. For submission/control rates, only minutes with that metric observed enter the denominator.

The importer conservatively excludes all copies of ambiguous duplicate IDs or duplicate event/bout keys and all fighters whose names cannot map unambiguously to a source identity. Same-event rematches cannot be disambiguated in the round archive and are excluded. Fight history uses retained binary bouts only, not a fighter's full professional record. Source names are used once to resolve source IDs; persistent primary keys are IDs.

The minimum empirical-history rule is two earlier retained bouts for each fighter. Last division is normalized to merge title and non-title appearances. Current height, reach, date-of-birth and stance were not supplied in the selected identity CSV, so they are not fabricated or used as predictors.

Round-level optional fields are retained at source resolution. No event timing sequence, hidden coaching strategy, judges' score model, physiological exposure or Markov transitions are reconstructed from aggregate strikes.
