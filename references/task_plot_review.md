# Task Plot Review

## Evidence Match

- Pass: title and construct match the Tapping Synchronization Task.
- Pass: rows match practice_600 and tempo_450, tempo_600, tempo_750 conditions.
- Pass: phase order matches README and `src/run_trial.py`: Ready -> Sync tapping -> Continuation tapping -> Practice break or Test ITI.
- Pass: timing labels match config: 800 ms ready, 10 beat sync windows, 30 beat continuation windows, 1200 ms practice break, 800 ms test ITI.
- Pass: response mapping shows SPACE as the tap key.
- Pass: tempo-specific sync and continuation durations are shown.
- Pass: no feedback, reward, or accuracy scoring is shown.

## Visual Quality

- Pass: labels and timings are readable.
- Pass: generated timeline content stays below the header band.
- Pass: fixed title and Construct subtitle are centered.
- Pass: top-right TaskBeacon logo lockup is borderless and non-overlapping.
- Pass: no generated title, logo, watermark, people, devices, or decorative scene is present.

## README Embed

- Pass: `README.md` contains `## 2. Task Flow`.
- Pass: the section embeds `![Task Flow](task_flow.png)`.
- Pass: final image is saved as `task_flow.png`; raw timeline is saved as `references/task_plot_timeline_raw.png`.
