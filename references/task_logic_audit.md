# Task Logic Audit

## 1. Paradigm Intent

- Task: Tapping Synchronization Task
- Primary construct: auditory-motor synchronization and beat maintenance
- Manipulated factors:
  - tempo / inter-onset interval (450 ms, 600 ms, 750 ms)
  - block role (practice vs test)
  - synchronization vs continuation phase within each trial
- Dependent measures:
  - tap timing relative to beat onsets during synchronization
  - continuation inter-tap interval stability after the tone sequence stops
  - omission rate / missing taps
  - tap count per phase and per tempo
- Key citations:
  - `W2491302369` - BAASTA battery; provides the closest open-access, high-citation protocol for paced tapping and synchronization-continuation timing.
  - `W2101394262` - H-BAT; supports beat production as a measurable tapping/synchronization construct.
  - `W2013459406` - links beat-movement skill to neural consistency and supports the use of beat-synchronization timing metrics.
  - `W1974407924` - classic sensory-information paper supporting action-event synchrony as an auditory-motor timing task.
  - `W2147682570` - high-impact rhythm-motor coupling paper used as the whitelist-required high-impact citation.

## 2. Block/Trial Workflow

### Block Structure

- Total blocks: 2
- Trials per block:
  - practice block: 1
  - test block: 6
- Randomization/counterbalancing:
  - practice is fixed first
  - test trials are balanced across the three tempi, with two repetitions per tempo
  - the order of the six test trials is deterministically shuffled from the block seed
- Condition generation method:
  - custom generator
  - a single flat weighted condition list cannot preserve both the fixed practice trial and the balanced tempo repetitions in the test block while keeping the practice-first schedule auditable
  - generated condition data shape passed into `run_trial.py`: one per-trial condition token per block, e.g. `practice_600`, `tempo_450`, `tempo_600`, `tempo_750`
- Runtime-generated trial values (if any):
  - beat onset times for each tempo
  - tap timestamps and phase-relative offsets
  - sync-phase metrics and continuation-phase metrics
  - all timing is deterministic from block seed, trial index, and the selected tempo

### Trial State Machine

List each state in order with entry/exit conditions:

1. State name: `instruction`
   - Onset trigger: `instruction_onset`
   - Stimuli shown: Chinese instructions describing the tapping rule, practice trial, and the space key
   - Valid keys: `space`
   - Timeout behavior: waits until space is pressed
   - Next state: practice block

2. State name: `practice_ready`
   - Onset trigger: `practice_ready_onset`
   - Stimuli shown: brief ready screen before the practice trial
   - Valid keys: `space` only to advance if an explicit continue key is used; otherwise timer-driven
   - Timeout behavior: brief timer-driven display
   - Next state: `practice_sync_tapping`

3. State name: `practice_sync_tapping`
   - Onset trigger: `practice_sync_tapping_onset`
   - Stimuli shown: fixation cross while the 600 ms metronome tones play
   - Valid keys: `space`
   - Timeout behavior: phase lasts for the scheduled synchronization window
   - Next state: `practice_continuation_tapping`

4. State name: `practice_continuation_tapping`
   - Onset trigger: `practice_continuation_tapping_onset`
   - Stimuli shown: fixation cross while the participant continues tapping after the tones stop
   - Valid keys: `space`
   - Timeout behavior: phase lasts for the scheduled continuation window
   - Next state: `practice_break`

5. State name: `practice_break`
   - Onset trigger: `practice_break_onset`
   - Stimuli shown: brief transition text indicating that formal trials are about to start
   - Valid keys: `space`
   - Timeout behavior: brief timer-driven display
   - Next state: first test trial

6. State name: `test_ready`
   - Onset trigger: `test_ready_onset`
   - Stimuli shown: brief ready screen before each scored trial
   - Valid keys: `space` only to advance if an explicit continue key is used; otherwise timer-driven
   - Timeout behavior: brief timer-driven display
   - Next state: `sync_tapping`

7. State name: `sync_tapping`
   - Onset trigger: `sync_tapping_onset`
   - Stimuli shown: fixation cross while the tempo-specific metronome tones play
   - Valid keys: `space`
   - Timeout behavior: phase lasts for the scheduled synchronization window
   - Next state: `continuation_tapping`

8. State name: `continuation_tapping`
   - Onset trigger: `continuation_tapping_onset`
   - Stimuli shown: fixation cross while the participant keeps tapping after the tones stop
   - Valid keys: `space`
   - Timeout behavior: phase lasts for the scheduled continuation window
   - Next state: `test_iti`

9. State name: `test_iti`
   - Onset trigger: `test_iti_onset`
   - Stimuli shown: brief inter-trial gap / fixation
   - Valid keys: none
   - Timeout behavior: timer-driven
   - Next state: next test trial or goodbye

10. State name: `good_bye`
    - Onset trigger: `good_bye_onset`
    - Stimuli shown: end-of-task summary screen
    - Valid keys: `space`
    - Timeout behavior: waits until space is pressed
    - Next state: experiment end

## 3. Condition Semantics

For each condition token in `task.conditions`:

- Condition ID: `practice_600`
  - Participant-facing meaning: one familiarization trial at the 600 ms tempo
  - Concrete stimulus realization (visual/audio): 1319 Hz tone train with a 600 ms IOI, followed by a continuation window at the same tempo
  - Outcome rules: not included in the scored test summary; used to teach the tapping rule

- Condition ID: `tempo_450`
  - Participant-facing meaning: scored test trial at 450 ms tempo
  - Concrete stimulus realization (visual/audio): 1319 Hz tone train with a 450 ms IOI, then silent continuation at the same tempo
  - Outcome rules: taps are analyzed for synchronization accuracy and continuation stability

- Condition ID: `tempo_600`
  - Participant-facing meaning: scored test trial at 600 ms tempo
  - Concrete stimulus realization (visual/audio): 1319 Hz tone train with a 600 ms IOI, then silent continuation at the same tempo
  - Outcome rules: taps are analyzed for synchronization accuracy and continuation stability

- Condition ID: `tempo_750`
  - Participant-facing meaning: scored test trial at 750 ms tempo
  - Concrete stimulus realization (visual/audio): 1319 Hz tone train with a 750 ms IOI, then silent continuation at the same tempo
  - Outcome rules: taps are analyzed for synchronization accuracy and continuation stability

Also document where participant-facing condition text/stimuli are defined:

- Participant-facing text source (config stimuli / code formatting / generated assets):
  - all participant-facing wording is defined in `config/*.yaml`
  - the metronome tone is a generated reference asset stored in `assets/`
  - `src/run_trial.py` only formats config strings and schedules the generated audio asset
- Why this source is appropriate for auditability:
  - the text is centralized in YAML, and the sound asset is an explicit file that can be inspected and regenerated
  - the same config drives human, QA, and simulation modes
- Localization strategy (how language variants are swapped via config without code edits):
  - participant text is stored in Chinese in the YAML stimulus bank
  - any future language version can replace YAML strings and fonts without touching the trial logic

## 4. Response and Scoring Rules

- Response mapping:
  - `space` key taps are recorded continuously during the tapping windows
  - the instruction and goodbye screens also use `space` to advance
- Response key source (config field vs code constant):
  - config-driven via `task.tap_key` and `task.start_key`
- If code-defined, why config-driven mapping is not sufficient:
  - not applicable; the task should remain config-driven
- Missing-response policy:
  - no penalty screen or forced restart
  - each phase ends on its scheduled deadline even if the participant stops tapping
- Correctness logic:
  - there is no right/wrong answer
  - scoring is timing-based, not accuracy-based
- Reward/penalty updates:
  - none
- Running metrics:
  - mean absolute synchronization asynchrony
  - synchronization tap count
  - continuation tap count
  - continuation inter-tap interval mean and coefficient of variation
  - omission count / tap loss count

## 5. Stimulus Layout Plan

For every screen with multiple simultaneous options/stimuli:

- Screen name: `instruction`
  - Stimulus IDs shown together: `instruction_text`
  - Layout anchors (`pos`): centered
  - Size/spacing (`height`, width, wrap): single centered paragraph with wide wrap width
  - Readability/overlap checks: single text block only
  - Rationale: task rule must be readable before the practice trial

- Screen name: `practice_ready`
  - Stimulus IDs shown together: `practice_ready_text`
  - Layout anchors (`pos`): centered
  - Size/spacing (`height`, width, wrap): short centered line
  - Readability/overlap checks: single text block only
  - Rationale: brief cue that the practice trial is about to start

- Screen name: `practice_sync_tapping` / `sync_tapping` / `continuation_tapping`
  - Stimulus IDs shown together: `fixation`
  - Layout anchors (`pos`): centered
  - Size/spacing (`height`, width, wrap): large centered fixation cross only
  - Readability/overlap checks: no text overlays during the tapping windows
  - Rationale: keep the auditory pacing cue visually uncluttered

- Screen name: `practice_break`
  - Stimulus IDs shown together: `practice_break_text`
  - Layout anchors (`pos`): centered
  - Size/spacing (`height`, width, wrap): short centered message
  - Readability/overlap checks: single text block only
  - Rationale: marks the transition from practice to scored trials

- Screen name: `test_ready`
  - Stimulus IDs shown together: `test_ready_text`
  - Layout anchors (`pos`): centered
  - Size/spacing (`height`, width, wrap): short centered line
  - Readability/overlap checks: single text block only
  - Rationale: brief cue before each scored trial

- Screen name: `good_bye`
  - Stimulus IDs shown together: `good_bye_text`
  - Layout anchors (`pos`): centered
  - Size/spacing (`height`, width, wrap): multi-line centered summary block
  - Readability/overlap checks: single text block only
  - Rationale: finish screen with summary metrics and exit instruction

## 6. Trigger Plan

Map each phase/state to trigger code and semantics.

- `exp_onset`: experiment start
- `exp_end`: experiment end
- `block_onset`: block start
- `block_end`: block end
- `trial_onset`: trial start
- `instruction_onset`: instruction screen onset
- `practice_ready_onset`: practice ready screen onset
- `practice_sync_tapping_onset`: practice sync-tapping onset
- `practice_continuation_tapping_onset`: practice continuation onset
- `practice_break_onset`: practice transition screen onset
- `test_ready_onset`: scored-trial ready screen onset
- `sync_tapping_onset`: scored synchronization phase onset
- `continuation_tapping_onset`: scored continuation phase onset
- `test_iti_onset`: inter-trial interval onset
- `good_bye_onset`: goodbye screen onset
- `tap_press`: each registered tap during the synchronization or continuation windows

## 7. Architecture Decisions (Auditability)

- `main.py` runtime flow style (simple single flow / helper-heavy / why):
  - simple single flow with a small number of helper functions
  - a custom per-frame loop is needed only for the continuous tap recording window
- `utils.py` used? (yes/no)
  - yes
- If yes, exact purpose (adaptive controller / sequence generation / asset pool / other):
  - deterministic tempo schedule generation
  - tap-timing metric computation
  - summary aggregation for the goodbye screen
- Custom controller used? (yes/no)
  - no adaptive controller
- If yes, why PsyFlow-native path is insufficient:
  - the paradigm requires repeated tap logging within a single window, which is not a single-response choice task
- Legacy/backward-compatibility fallback logic required? (yes/no)
  - no
- If yes, scope and removal plan:
  - not applicable

## 8. Inference Log

List any inferred decisions not directly specified by references:

- Decision: use a keyboard `space` tap as the PsyFlow response proxy for finger tapping
  - Why inference was required: the literature describes a finger tapping or button-press synchronization task, but the local build must run on standard keyboard hardware
  - Citation-supported rationale: the selected papers describe synchronization/production timing rather than the exact hardware implementation

- Decision: represent the practice trial as a 600 ms familiarization trial with the same sync-continuation structure as the scored trials
  - Why inference was required: the open-access battery states that the task is preceded by one practice trial, but does not pin down the exact practice structure in the extracted lines
  - Citation-supported rationale: practice-before-test sequencing is explicitly stated in the tapping battery family and is consistent with the scored tempo ladder

- Decision: generate a local metronome sound asset at 1319 Hz for 100 ms
  - Why inference was required: the exact file format is not prescribed by the references, but the tone frequency and duration are specified
  - Citation-supported rationale: the BAASTA tapping protocol uses a 1319 Hz tone with 100 ms duration, so a generated PCM asset is a faithful implementation choice

## Contract Note

- Participant-facing labels/instructions/options should be config-defined whenever possible.
- `src/run_trial.py` should not hardcode participant-facing text that would require code edits for localization.
