# CHANGELOG

All notable development changes for `T000044-tapping-synchronization-task` are documented here.

## [Unreleased] - 2026-04-05

### Added
- Added a Chinese-localized tapping synchronization task with one 600 ms practice trial and six scored test trials distributed across 450 ms, 600 ms, and 750 ms tempi.
- Added a generated 1319 Hz / 100 ms metronome tone asset for the paced tapping windows.
- Added QA and simulation responders that can produce scripted or sampled tap sequences for the sync and continuation phases.

### Changed
- Replaced the temporal-bisection scaffold with a tapping state machine built around instruction, ready, synchronization, continuation, break, ITI, and goodbye phases.
- Updated the configs, trigger names, summary metrics, and responder logic to track beat synchronization timing instead of short-vs-long judgments.
- Kept participant-facing text in YAML and used SimHei throughout the Chinese UI.

### Fixed
- Removed the copied temporal-bisection audio asset and stale choice-screen terminology.
- Aligned the logged trial summary to synchronization asynchrony, continuation ITI mean/CV, omission count, and elapsed time.
