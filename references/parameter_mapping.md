# Parameter Mapping

## Mapping Table

| Parameter ID | Config Path | Implemented Value | Source Paper ID | Evidence (quote/figure/table) | Decision Type | Notes |
|---|---|---|---|---|---|---|
| `phase_order` | `task.phase_order` | `['instruction', 'practice_ready', 'practice_sync_tapping', 'practice_continuation_tapping', 'practice_break', 'test_ready', 'sync_tapping', 'continuation_tapping', 'test_iti', 'good_bye']` | `W2491302369` | The BAASTA synchronization-continuation tapping protocol uses a practice-before-test workflow with paced tapping followed by continuation. | `adapted` | Adds task-local ready, break, ITI, and goodbye screens around the literature-defined tapping trial. |
| `conditions` | `task.conditions` | `['practice_600', 'tempo_450', 'tempo_600', 'tempo_750']` | `W2491302369` | The cited tapping battery samples three tempi and separates a practice trial from the scored set. | `adapted` | Practice is split out as its own condition token for auditable scheduling. |
| `practice_trials` | `task.practice_trials` | `1` | `W2491302369` | The protocol begins with one practice trial before the scored tempo set. | `direct` | One familiarization trial is retained. |
| `test_trials` | `task.test_trials` | `6` | `W2491302369` | The scored synchronization-continuation task is repeated twice at each of the three tempi. | `direct` | 3 tempi x 2 repetitions. |
| `practice_tempo_ms` | `task.practice_tempo_ms` | `600` | `W2491302369` | The local practice trial uses the middle tempo from the three-tempo ladder. | `adapted` | Central tempo chosen for familiarization. |
| `tempo_levels_ms` | `task.tempo_levels_ms` | `[450, 600, 750]` | `W2491302369` | The battery uses the 450 ms, 600 ms, and 750 ms IOI set. | `direct` | Scored tempi. |
| `sync_beats` | `task.sync_beats` | `10` | `W2491302369` | The synchronization phase presents 10 tones before continuation begins. | `direct` | Ten-beat pacing window. |
| `continuation_beats` | `task.continuation_beats` | `30` | `W2491302369` | The continuation phase extends for 30 IOIs after the metronome stops. | `direct` | Thirty IOIs are used for free continuation tapping. |
| `tone_frequency_hz` | `task.tone_frequency_hz` | `1319` | `W2491302369` | The metronome tone is specified at 1319 Hz in the open-access tapping battery. | `direct` | Generated audio asset matches the cited frequency. |
| `tone_duration_s` | `task.tone_duration_s` | `0.1` | `W2491302369` | The cited tapping protocols use a short metronome tone; the local PCM asset implements that as a 100 ms click. | `inferred` | Exact WAV encoding is a local asset choice. |
| `tap_key` | `task.tap_key` | `space` | `W1974407924` | The literature task is a finger-tapping synchronization paradigm; the local build uses the space bar as the keyboard proxy. | `inferred` | Hardware proxy for a tap response. |
| `start_key` | `task.start_key` | `space` | `W2101394262` | The same keyboard key is reused for start/advance screens to keep the deployment simple and auditable. | `inferred` | Shares the tapping proxy for instruction and goodbye screens. |
| `ready_duration_s` | `task.ready_duration_s` | `0.8` | `W1974407924` | Brief separators between action-event synchrony epochs are a local usability choice. | `inferred` | Short ready screen before practice/test trials. |
| `break_duration_s` | `task.break_duration_s` | `1.2` | `W2491302369` | A short pause separates the practice block from the scored block; the exact pause length is local. | `inferred` | Transition screen after practice. |
| `iti_duration_s` | `task.iti_duration_s` | `0.8` | `W1974407924` | Short inter-trial gaps help keep successive tapping sequences distinct. | `inferred` | Fixation-only ITI. |

Decision type values:

- `direct`
- `adapted`
- `inferred`
