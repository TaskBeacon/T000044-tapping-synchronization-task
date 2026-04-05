# Stimulus Mapping

## Mapping Table

| Condition | Stage/Phase | Stimulus IDs | Participant-Facing Content | Source Paper ID | Evidence (quote/figure/table) | Implementation Mode | Asset References | Notes |
|---|---|---|---|---|---|---|---|---|
| `all` | `instruction` | `instruction_text` | `你将完成一个节拍同步拍击任务。请在听到每个节拍时按一次空格键，尽量让按键和声音保持一致。先进行 1 次练习，然后完成 6 次正式试次。每个试次都会先出现准备提示，接着播放一段节拍声；节拍声停止后，请继续按相同的节奏拍击。请尽量保持稳定，不要抢拍，也不要漏拍。按空格键开始。` | `W2101394262` | Beat perception/production batteries present the task as a beat-matching tapping exercise with explicit practice-before-test framing. | `psychopy_builtin` | `config/config.yaml::instruction_text` | Task instruction screen. |
| `practice_600` | `practice_ready` | `practice_ready_text` | `练习即将开始。` | `W2491302369` | The tapping battery uses a practice trial before scored performance, so a brief ready screen is a local transition cue. | `psychopy_builtin` | `config/config.yaml::practice_ready_text` | Practice-only readiness cue. |
| `practice_600` | `practice_sync_tapping` | `fixation`, `metronome_tone` | `中心注视点“+” + 1319 Hz 节拍声列（600 ms IOI），按空格键跟拍。` | `W2491302369` | The synchronization-continuation task uses a metronome paced at the target IOI during the synchronization phase. | `generated_reference_asset` | `config/config.yaml::fixation`, `assets/metronome_tone_1319hz_100ms.wav` | Same visual layout as test sync rows. |
| `practice_600` | `practice_continuation_tapping` | `fixation` | `中心注视点“+”，节拍声停止后继续按相同节奏拍击。` | `W2491302369` | Continuation tapping follows the paced sequence once the tones stop. | `psychopy_builtin` | `config/config.yaml::fixation` | Silent continuation phase. |
| `practice_600` | `practice_break` | `practice_break_text` | `练习结束。正式试次即将开始。` | `W2101394262` | A short practice-to-test transition is a task-local separator around the literature-defined tapping trial. | `psychopy_builtin` | `config/config.yaml::practice_break_text` | Practice/test separator. |
| `all` | `test_ready` | `test_ready_text` | `正式试次即将开始。` | `W2101394262` | The scored tapping block is preceded by a brief readiness cue in the local implementation. | `psychopy_builtin` | `config/config.yaml::test_ready_text` | Shared by all scored tempi. |
| `tempo_450` | `sync_tapping` | `fixation`, `metronome_tone` | `中心注视点“+” + 1319 Hz 节拍声列（450 ms IOI），按空格键跟拍。` | `W2491302369` | The battery samples the 450 ms IOI condition during synchronization. | `generated_reference_asset` | `config/config.yaml::fixation`, `assets/metronome_tone_1319hz_100ms.wav` | Tempo-specific sync trial. |
| `tempo_450` | `continuation_tapping` | `fixation` | `中心注视点“+”，节拍声停止后继续按 450 ms 节奏拍击。` | `W2491302369` | The continuation phase preserves the established tempo after the metronome stops. | `psychopy_builtin` | `config/config.yaml::fixation` | Silent continuation at 450 ms IOI. |
| `tempo_600` | `sync_tapping` | `fixation`, `metronome_tone` | `中心注视点“+” + 1319 Hz 节拍声列（600 ms IOI），按空格键跟拍。` | `W2491302369` | The battery samples the 600 ms IOI condition during synchronization. | `generated_reference_asset` | `config/config.yaml::fixation`, `assets/metronome_tone_1319hz_100ms.wav` | Tempo-specific sync trial. |
| `tempo_600` | `continuation_tapping` | `fixation` | `中心注视点“+”，节拍声停止后继续按 600 ms 节奏拍击。` | `W2491302369` | The continuation phase preserves the established tempo after the metronome stops. | `psychopy_builtin` | `config/config.yaml::fixation` | Silent continuation at 600 ms IOI. |
| `tempo_750` | `sync_tapping` | `fixation`, `metronome_tone` | `中心注视点“+” + 1319 Hz 节拍声列（750 ms IOI），按空格键跟拍。` | `W2491302369` | The battery samples the 750 ms IOI condition during synchronization. | `generated_reference_asset` | `config/config.yaml::fixation`, `assets/metronome_tone_1319hz_100ms.wav` | Tempo-specific sync trial. |
| `tempo_750` | `continuation_tapping` | `fixation` | `中心注视点“+”，节拍声停止后继续按 750 ms 节奏拍击。` | `W2491302369` | The continuation phase preserves the established tempo after the metronome stops. | `psychopy_builtin` | `config/config.yaml::fixation` | Silent continuation at 750 ms IOI. |
| `all` | `test_iti` | `fixation` | `中心注视点“+”，作为试次间隔。` | `W1974407924` | Short gaps help separate successive action-event synchrony sequences. | `psychopy_builtin` | `config/config.yaml::fixation` | Fixation-only ITI. |
| `all` | `good_bye` | `good_bye_text` | `任务结束。显示总试次、练习/正式试次数、同步绝对偏差、继续拍击 ITI 均值/变异系数、漏拍率和总用时，按空格退出。` | `W2101394262` | The goodbye screen is a task-local summary/exit screen rather than a literature stimulus. | `psychopy_builtin` | `config/config.yaml::good_bye_text` | Local end-of-task summary. |

Allowed implementation modes:

- `psychopy_builtin`
- `generated_reference_asset`
- `licensed_external_asset`
