# Tapping Synchronization Task

![Maturity: draft](https://img.shields.io/badge/Maturity-draft-64748b?style=flat-square&labelColor=111827)

| Field | Value |
|---|---|
| Name | Tapping Synchronization Task |
| Version | v0.1.0-dev |
| URL / Repository | E:/Taskbeacon/T000044-tapping-synchronization-task |
| Short Description | Chinese tapping synchronization task with one 600 ms practice trial, six scored test trials, and a metronome beat train at 450/600/750 ms tempi. |
| Created By | TaskBeacon |
| Date Updated | 2026-04-05 |
| PsyFlow Version | 0.1.12 |
| PsychoPy Version | 2025.2.4 |
| Modality | Behavior |
| Language | Chinese |
| Voice Name | zh-CN-YunyangNeural |

## 1. Task Overview

This task measures auditory-motor synchronization with a paced tapping paradigm. Participants first read the Chinese instructions, complete one 600 ms practice trial, and then complete six scored trials distributed across three tempi: 450 ms, 600 ms, and 750 ms. Each trial begins with a ready screen, continues through a beat-synchronized tapping window, and then moves into a silent continuation window where the participant keeps tapping at the remembered tempo.

The implemented protocol uses a single `space` key as the local tapping proxy, a generated 1319 Hz / 100 ms metronome tone, and simple PsychoPy primitives for the fixation and text-only screens. The task is timing-based rather than accuracy-based: the data capture focuses on synchronization asynchrony, continuation inter-tap stability, omission count, and elapsed time.

## 2. Task Flow

![Task Flow](task_flow.png)

### Block-Level Flow

| Step | Description |
|---|---|
| 1. Load mode and config | `main.py` loads `human`, `qa`, or `sim` mode and resolves the matching YAML config. |
| 2. Initialize runtime | Subject info, window, triggers, and the stimulus bank are initialized. |
| 3. Show instructions | The participant reads the Chinese tapping instructions and presses space to begin. |
| 4. Run practice block | The first block runs one 600 ms practice trial with sync tapping, continuation tapping, and a short practice break. |
| 5. Run test block | The second block runs six scored trials balanced across 450 ms, 600 ms, and 750 ms tempi. |
| 6. Finish | The goodbye screen appears with summary metrics, and the data are saved. |

### Trial-Level Flow

| Step | Description |
|---|---|
| Instruction | Explain the tapping rule and start with the space key. |
| Practice ready | A brief ready screen appears before the practice trial. |
| Practice sync tapping | A fixation cross is shown while the 600 ms metronome tone repeats for 10 beats. |
| Practice continuation tapping | The tone stops and the participant continues tapping for 30 beats at the remembered tempo. |
| Practice break | A short transition screen separates practice from the scored trials. |
| Test ready | A brief ready screen appears before each scored trial. |
| Sync tapping | A fixation cross is shown while the tempo-specific metronome tone repeats for 10 beats. |
| Continuation tapping | The tone stops and the participant continues tapping for 30 beats at the remembered tempo. |
| Test ITI | A short fixation-only inter-trial interval separates scored trials. |
| Goodbye | The final screen reports summary metrics and exits on space. |

### Controller Logic

| Component | Description |
|---|---|
| Condition generation | `build_block_conditions()` produces a fixed practice-first schedule: one `practice_600` trial followed by six test trials balanced across `tempo_450`, `tempo_600`, and `tempo_750`. |
| Tempo plan | `build_trial_plan()` resolves the trial tempo, beat count, tone duration, and deterministic trial seed for each trial. |
| Response handling | `space` is the tapping proxy during the synchronization and continuation windows; the instruction and goodbye screens also use space to continue. |
| Timing control | Human mode uses the nominal durations from `config/config.yaml`; QA shortens the same phases with `qa.timing_scale = 0.3`; simulation uses the same state machine with deterministic tap schedules. |
| Summary metrics | The task reports synchronization asynchrony, continuation inter-tap interval mean/CV, omission count, and elapsed time. |
| Triggering | Each participant-visible phase emits a dedicated onset trigger, and every registered tap emits `tap_press`. |

### Other Logic

| Component | Description |
|---|---|
| Metronome tone | A generated 1319 Hz / 100 ms WAV asset drives the paced tapping sequence. |
| Visual layout | Tapping windows use a centered fixation cross only; all text screens are single centered blocks. |
| No reward logic | There are no points, tokens, or correctness feedback in the task. |
| Simulation support | `TaskSamplerResponder` can emit scripted or sampled tap trains for QA and simulation flows. |

## 3. Configuration Summary

All human settings are defined in `config/config.yaml`. QA and smoke-test overrides live in `config/config_qa.yaml`, `config/config_scripted_sim.yaml`, and `config/config_sampler_sim.yaml`.

### a. Subject Info

| Field | Meaning |
|---|---|
| `subject_id` | 3-digit participant identifier used to seed the run. |

### b. Window Settings

| Parameter | Value |
|---|---|
| `size` | `[1280, 720]` |
| `units` | `pix` |
| `screen` | `0` |
| `bg_color` | `black` |
| `fullscreen` | `false` |
| `monitor_width_cm` | `35.5` |
| `monitor_distance_cm` | `60` |

### c. Stimuli

| Name | Type | Description |
|---|---|---|
| `instruction_text` | text | Chinese instructions describing the tap-to-the-beat rule and the practice/test sequence. |
| `practice_ready_text` | text | Ready screen shown before the practice trial. |
| `practice_break_text` | text | Short transition screen between practice and scored trials. |
| `test_ready_text` | text | Ready screen shown before each scored trial. |
| `good_bye_text` | text | End-of-task summary and exit screen. |
| `fixation` | text | Centered plus sign used during tapping and ITI screens. |
| `metronome_tone` | sound | Generated 1319 Hz / 100 ms metronome tone used during synchronization windows. |

### d. Timing

| Phase | Duration |
|---|---|
| Practice ready | `0.8 s` |
| Practice sync tapping | `10 × 600 ms = 6.0 s` |
| Practice continuation tapping | `30 × 600 ms = 18.0 s` |
| Practice break | `1.2 s` |
| Test ready | `0.8 s` |
| Test sync tapping at 450 ms | `10 × 450 ms = 4.5 s` |
| Test continuation tapping at 450 ms | `30 × 450 ms = 13.5 s` |
| Test sync tapping at 600 ms | `10 × 600 ms = 6.0 s` |
| Test continuation tapping at 600 ms | `30 × 600 ms = 18.0 s` |
| Test sync tapping at 750 ms | `10 × 750 ms = 7.5 s` |
| Test continuation tapping at 750 ms | `30 × 750 ms = 22.5 s` |
| Test ITI | `0.8 s` |
| Metronome tone duration | `0.1 s` |

### e. Triggers

| Event | Code |
|---|---:|
| Experiment onset | `1` |
| Experiment end | `2` |
| Block onset | `10` |
| Block end | `11` |
| Trial onset | `20` |
| Instruction onset | `21` |
| Practice ready onset | `22` |
| Practice sync tapping onset | `23` |
| Practice continuation tapping onset | `24` |
| Practice break onset | `25` |
| Test ready onset | `26` |
| Sync tapping onset | `27` |
| Continuation tapping onset | `28` |
| Tap press | `29` |
| Test ITI onset | `30` |
| Goodbye onset | `40` |

### f. Adaptive Controller

| Parameter | Value |
|---|---|
| `condition_generation` | Custom practice-first generator in `src/utils.py`. |
| `practice_trials` | `1` |
| `test_trials` | `6` |
| `sync_beats` | `10` |
| `continuation_beats` | `30` |
| `practice_tempo_ms` | `600` |
| `tempo_levels_ms` | `450`, `600`, `750` |
| `tap_key` | `space` |
| `start_key` | `space` |
| `qa.timing_scale` | `0.3` |
| `sim responder` | `TaskSamplerResponder` with scripted or sampled tap trains. |
| `adaptive staircase` | `None` |

## 4. Methods (for academic publication)

The tapping synchronization task is a paced auditory-motor timing paradigm. Participants hear a metronome tone train and tap a single key in synchrony with the beat. The implementation includes one practice trial at 600 ms IOI followed by six scored trials distributed evenly across 450 ms, 600 ms, and 750 ms tempi. Each trial is divided into a synchronization window, during which tones are audible, and a continuation window, during which tones stop and the participant continues tapping from memory.

The task is intentionally timing-centric rather than accuracy-centric. The saved trial data capture synchronization asynchrony, continuation inter-tap interval mean and variability, omission count, and elapsed time, which makes the paradigm suitable for sensorimotor synchronization studies and beat production research. Participant-facing text remains in YAML, and the metronome tone is generated locally so the task stays auditable and reproducible without external media dependencies.

The runtime supports `human`, `qa`, and `sim` modes with the same state machine. QA shortens the timebase while preserving the phase structure, and simulation modes use deterministic tap schedules so the full pipeline can be validated without manual input.
