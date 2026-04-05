# Assets for Tapping Synchronization Task

This task uses one generated reference audio asset:

- `metronome_tone_1319hz_100ms.wav`: a 1319 Hz metronome tone with a 100 ms duration, generated locally from the tapping battery protocol.

All participant-facing text lives in `config/*.yaml`, and the fixation / ready / goodbye screens use PsychoPy primitives. If the protocol changes, regenerate the tone asset and update `references/stimulus_mapping.md` so the media trace stays auditable.
