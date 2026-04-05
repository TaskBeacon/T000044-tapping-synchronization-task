# Task Plot Audit

- generated_at: 2026-04-05T22:29:37+08:00
- mode: existing
- task_path: E:\Taskbeacon\T000044-tapping-synchronization-task

## 1. Inputs and provenance

- E:\Taskbeacon\T000044-tapping-synchronization-task\README.md
- E:\Taskbeacon\T000044-tapping-synchronization-task\config\config.yaml
- E:\Taskbeacon\T000044-tapping-synchronization-task\src\run_trial.py

## 2. Evidence extracted from README

- Instruction phase tells the participant to read the tapping instructions and press space to begin.
- Practice block contains one 600 ms practice trial with sync tapping, continuation tapping, and a short practice break.
- Test block contains six scored trials balanced across 450 ms, 600 ms, and 750 ms tempi.
- Trial flow ends with a goodbye screen that reports summary metrics and exits on space.

## 3. Evidence extracted from config/source

- `config.conditions` lists `practice_600`, `tempo_450`, `tempo_600`, and `tempo_750`.
- `practice_tempo_ms` is 600 ms and `tempo_levels_ms` are 450, 600, and 750 ms.
- `run_trial.py` branches to `practice_ready`, `practice_sync_tapping`, `practice_continuation_tapping`, `practice_break`, `test_ready`, `sync_tapping`, `continuation_tapping`, `test_iti`, and the goodbye summary flow.
- `sync_tapping` phases add fixation plus the metronome tone; continuation phases show fixation only; `test_iti` is fixation-only.
- Practice and test branch on `trial_data["is_practice"]`, so the practice timeline is distinct from the scored tempo timelines.

## 4. Mapping to task_plot_spec

- root_key: `task_plot_spec`
- spec_version: `0.2`
- one timeline per selected condition
- four timelines rendered to cover one practice timeline plus three scored tempo variants
- phase labels were shortened for readability in the participant-visible screen mockups while preserving the underlying stimulus mapping

## 5. Style decision and rationale

- Kept the task-flow figure as a multi-timeline collection because the task has one practice block and three scored tempo conditions.
- Tuned the layout manually after the first render: disabled auto width, narrowed the canvas, lowered the slope angle, and shortened a few card text summaries to stop the phase cards from colliding.
- Final figure keeps the sync cue content correct (`+` and `1319 Hz tone`) and leaves each timeline readable without incorrect ratio or scale.

## 6. Rendering parameters and constraints

- output_file: `task_flow.png`
- dpi: `300`
- max_conditions: `4`
- screens_per_timeline: `4`
- auto_width: `false`
- width_in: `6.4`
- screen_overlap_ratio: `0.04`
- screen_slope: `0.04`
- screen_slope_deg: `12.0`
- validator_warnings: none

## 7. Output files and checksums

- E:\Taskbeacon\T000044-tapping-synchronization-task\references\task_plot_spec.yaml: sha256=7CBF3ECDF0F56BBD57433B9791A1EAE45907619442602ACA58E97464F3621D66
- E:\Taskbeacon\T000044-tapping-synchronization-task\references\task_plot_spec.json: sha256=D73DF91EBD7C88B8E447806C958908671C38A3785C09DD8B20A243FDDE12BE7E
- E:\Taskbeacon\T000044-tapping-synchronization-task\references\task_plot_source_excerpt.md: sha256=424F2830D72E038CE6B0715283E4FFAE60E78746D963305E93349CAACD108A44
- E:\Taskbeacon\T000044-tapping-synchronization-task\task_flow.png: sha256=AA6766C027DD4F61B56FB16662DDFF77DC89DBB067DBB34DE396146C4C54F9AF

## 8. Inferred/uncertain items

- Goodbye is documented in README and source but not included in the timeline collection because it is a terminal non-condition screen.
- Legend entries are preserved in the spec for traceability, but the current renderer does not draw a separate visible legend block.
- No unresolved stimulus placeholders remained in the final render.
