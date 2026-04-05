# Source Excerpt (Tapping Synchronization Task)

## Input Files
- README: E:\Taskbeacon\T000044-tapping-synchronization-task\README.md
- Config: E:\Taskbeacon\T000044-tapping-synchronization-task\config\config.yaml
- run_trial: E:\Taskbeacon\T000044-tapping-synchronization-task\src\run_trial.py

## Selected Conditions
- practice_600
- tempo_450
- tempo_600
- tempo_750

## Source Notes
- Practice branch uses `practice_ready`, `practice_sync_tapping`, `practice_continuation_tapping`, and `practice_break`.
- Test branch uses `test_ready`, `sync_tapping`, `continuation_tapping`, and `test_iti`.
- `sync_tapping` shows fixation plus `metronome_tone`; continuation shows fixation only.
- The goodbye screen exists in the controller flow but is excluded from the timeline collection because it is not a per-condition trial phase.
- The selected timelines mirror the README trial-level flow table and the `config.conditions` list.
