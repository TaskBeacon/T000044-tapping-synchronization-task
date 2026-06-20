from __future__ import annotations

import hashlib
import json
import math
import random
from statistics import fmean, pstdev

from psychopy import core
from psyflow import StimUnit, set_trial_context
from psyflow.sim import Observation, get_context
from typing import Any, Iterable

DEFAULT_CONDITIONS = ("practice_600", "tempo_450", "tempo_600", "tempo_750")
DEFAULT_TEMPO_LEVELS_MS = (450, 600, 750)
DEFAULT_PRACTICE_CONDITION = "practice_600"
DEFAULT_PRACTICE_TEMPO_MS = 600
DEFAULT_SYNC_BEATS = 10
DEFAULT_CONTINUATION_BEATS = 30
DEFAULT_TONE_FREQUENCY_HZ = 1319
DEFAULT_TONE_DURATION_S = 0.1
DEFAULT_TAP_KEY = "space"
DEFAULT_START_KEY = "space"


def _get_setting(settings: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(settings, name):
            value = getattr(settings, name)
            if value is not None:
                return value
    return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _seed_blob(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        return repr(value)


def stable_seed(*parts: Any) -> int:
    """Create a deterministic 64-bit seed from arbitrary values."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(_seed_blob(part).encode("utf-8"))
        digest.update(b"\0")
    return int.from_bytes(digest.digest()[:8], "big", signed=False)


def format_duration_ms(ms: Any) -> str:
    try:
        return f"{int(round(float(ms)))} 毫秒"
    except Exception:
        return "未知时长"


def format_duration_s(seconds: Any) -> str:
    try:
        return f"{float(seconds):.2f} 秒"
    except Exception:
        return "未知时长"


def resolve_block_role(block_idx: int) -> str:
    return "practice" if int(block_idx) <= 0 else "test"


def resolve_block_trial_count(settings: Any, block_role: str) -> int:
    role = str(block_role).strip().lower()
    if role == "practice":
        return _as_int(_get_setting(settings, "practice_trials", default=1), 1)
    if role == "test":
        return _as_int(_get_setting(settings, "test_trials", default=6), 6)
    raise ValueError(f"Unsupported block role: {block_role!r}")


def build_block_conditions(
    n_trials: int,
    labels: list[Any],
    *,
    block_role: str,
    seed: int,
    practice_condition: str = DEFAULT_PRACTICE_CONDITION,
    tempo_conditions: Iterable[Any] | None = None,
    **_: Any,
) -> list[str]:
    """Create a practice-first tapping schedule."""
    n = max(0, int(n_trials))
    if n == 0:
        return []

    role = str(block_role).strip().lower()
    label_tokens = [str(label).strip().lower() for label in labels or [] if str(label).strip()]
    rng = random.Random(int(seed))

    if role == "practice":
        if practice_condition in label_tokens:
            return [practice_condition] * n
        return [practice_condition] * n

    tempo_tokens = [str(label).strip().lower() for label in (tempo_conditions or label_tokens) if str(label).strip()]
    tempo_tokens = [token for token in tempo_tokens if token.startswith("tempo_")]
    if not tempo_tokens:
        tempo_tokens = [f"tempo_{ms}" for ms in DEFAULT_TEMPO_LEVELS_MS]

    seq: list[str] = []
    repeats = math.ceil(n / len(tempo_tokens))
    for _ in range(repeats):
        seq.extend(tempo_tokens)
    seq = seq[:n]
    rng.shuffle(seq)
    return seq


def parse_condition(condition: Any) -> dict[str, Any]:
    """Normalize a tapping condition token into a structured dict."""
    if isinstance(condition, dict):
        raw = (
            condition.get("condition")
            or condition.get("condition_id")
            or condition.get("trial_kind")
            or condition.get("label")
        )
    else:
        raw = condition

    token = str(raw or "").strip().lower()
    token = token.replace(" ", "_")
    if not token:
        raise ValueError("Condition token is missing.")

    if token.startswith("practice_"):
        parts = token.split("_", 1)
        tempo_ms = _as_int(parts[1] if len(parts) > 1 else DEFAULT_PRACTICE_TEMPO_MS, DEFAULT_PRACTICE_TEMPO_MS)
        return {
            "condition_id": token,
            "block_role": "practice",
            "trial_kind": token,
            "tempo_ms": tempo_ms,
            "is_practice": True,
        }

    if token.startswith("tempo_"):
        parts = token.split("_", 1)
        tempo_ms = _as_int(parts[1] if len(parts) > 1 else DEFAULT_PRACTICE_TEMPO_MS, DEFAULT_PRACTICE_TEMPO_MS)
        return {
            "condition_id": token,
            "block_role": "test",
            "trial_kind": token,
            "tempo_ms": tempo_ms,
            "is_practice": False,
        }

    raise ValueError(f"Unsupported tapping condition: {condition!r}")


def build_trial_plan(
    *,
    condition: Any,
    block_idx: int,
    trial_index: int,
    overall_seed: int,
    settings: Any,
) -> dict[str, Any]:
    """Resolve all tempo and tap-plan parameters for one trial."""
    parsed = parse_condition(condition)
    block_role = str(parsed["block_role"])
    tempo_ms = _as_int(parsed["tempo_ms"], DEFAULT_PRACTICE_TEMPO_MS)
    if block_role == "practice":
        tempo_ms = _as_int(_get_setting(settings, "practice_tempo_ms", default=tempo_ms), tempo_ms)

    sync_beats = _as_int(_get_setting(settings, "sync_beats", default=DEFAULT_SYNC_BEATS), DEFAULT_SYNC_BEATS)
    continuation_beats = _as_int(
        _get_setting(settings, "continuation_beats", default=DEFAULT_CONTINUATION_BEATS),
        DEFAULT_CONTINUATION_BEATS,
    )
    tone_frequency_hz = _as_int(
        _get_setting(settings, "tone_frequency_hz", default=DEFAULT_TONE_FREQUENCY_HZ),
        DEFAULT_TONE_FREQUENCY_HZ,
    )
    tone_duration_s = _as_float(_get_setting(settings, "tone_duration_s", default=DEFAULT_TONE_DURATION_S), DEFAULT_TONE_DURATION_S)
    tap_key = str(_get_setting(settings, "tap_key", default=DEFAULT_TAP_KEY) or DEFAULT_TAP_KEY).strip().lower()
    start_key = str(_get_setting(settings, "start_key", default=DEFAULT_START_KEY) or DEFAULT_START_KEY).strip().lower()

    tempo_s = float(tempo_ms) / 1000.0
    sync_duration_s = float(sync_beats) * tempo_s
    continuation_duration_s = float(continuation_beats) * tempo_s
    total_phase_duration_s = sync_duration_s + continuation_duration_s

    trial_seed = stable_seed(overall_seed, block_idx, trial_index, parsed["condition_id"])
    sync_beat_times_s = [round(i * tempo_s, 6) for i in range(sync_beats)]
    continuation_beat_times_s = [round(i * tempo_s, 6) for i in range(continuation_beats)]

    return {
        "condition_id": parsed["condition_id"],
        "block_role": block_role,
        "trial_kind": parsed["trial_kind"],
        "tempo_ms": tempo_ms,
        "tempo_s": tempo_s,
        "sync_beats": sync_beats,
        "continuation_beats": continuation_beats,
        "sync_duration_s": sync_duration_s,
        "continuation_duration_s": continuation_duration_s,
        "total_phase_duration_s": total_phase_duration_s,
        "tone_frequency_hz": tone_frequency_hz,
        "tone_duration_s": tone_duration_s,
        "tap_key": tap_key,
        "start_key": start_key,
        "trial_seed": trial_seed,
        "sync_beat_times_s": sync_beat_times_s,
        "continuation_beat_times_s": continuation_beat_times_s,
        "is_practice": bool(parsed["is_practice"]),
    }


def _safe_mean(values: Iterable[float]) -> float:
    clean = [float(value) for value in values if value is not None]
    return float(fmean(clean)) if clean else 0.0


def _safe_cv(values: Iterable[float]) -> float:
    clean = [float(value) for value in values if value is not None]
    if len(clean) < 2:
        return 0.0
    mean = fmean(clean)
    if mean == 0:
        return 0.0
    return float(pstdev(clean) / mean)


def compute_sync_metrics(*, tap_times_s: Iterable[float], beat_times_s: Iterable[float]) -> dict[str, Any]:
    taps = [float(value) for value in tap_times_s if value is not None]
    beats = [float(value) for value in beat_times_s if value is not None]
    paired = min(len(taps), len(beats))
    asynchronies_s = [taps[i] - beats[i] for i in range(paired)]
    mean_async_s = _safe_mean(asynchronies_s)
    mean_abs_async_s = _safe_mean(abs(value) for value in asynchronies_s)
    return {
        "tap_count": len(taps),
        "expected_tap_count": len(beats),
        "paired_tap_count": paired,
        "first_tap_rt_s": taps[0] if taps else None,
        "mean_asynchrony_ms": mean_async_s * 1000.0,
        "mean_abs_asynchrony_ms": mean_abs_async_s * 1000.0,
        "mean_asynchrony_s": mean_async_s,
        "mean_abs_asynchrony_s": mean_abs_async_s,
        "omission_count": max(0, len(beats) - len(taps)),
        "extra_tap_count": max(0, len(taps) - len(beats)),
        "tap_times_s_json": json.dumps([round(value, 6) for value in taps], ensure_ascii=False),
        "beat_times_s_json": json.dumps([round(value, 6) for value in beats], ensure_ascii=False),
        "asynchronies_ms_json": json.dumps([round(value * 1000.0, 3) for value in asynchronies_s], ensure_ascii=False),
    }


def compute_continuation_metrics(*, tap_times_s: Iterable[float], beat_times_s: Iterable[float]) -> dict[str, Any]:
    taps = [float(value) for value in tap_times_s if value is not None]
    beats = [float(value) for value in beat_times_s if value is not None]
    paired = min(len(taps), len(beats))
    asynchronies_s = [taps[i] - beats[i] for i in range(paired)]
    intervals_s = [taps[i] - taps[i - 1] for i in range(1, len(taps))]
    mean_async_s = _safe_mean(asynchronies_s)
    mean_abs_async_s = _safe_mean(abs(value) for value in asynchronies_s)
    mean_iti_s = _safe_mean(intervals_s)
    iti_cv = _safe_cv(intervals_s)
    return {
        "tap_count": len(taps),
        "expected_tap_count": len(beats),
        "paired_tap_count": paired,
        "first_tap_rt_s": taps[0] if taps else None,
        "mean_asynchrony_ms": mean_async_s * 1000.0,
        "mean_abs_asynchrony_ms": mean_abs_async_s * 1000.0,
        "mean_iti_ms": mean_iti_s * 1000.0,
        "iti_cv": iti_cv,
        "mean_asynchrony_s": mean_async_s,
        "mean_abs_asynchrony_s": mean_abs_async_s,
        "mean_iti_s": mean_iti_s,
        "omission_count": max(0, len(beats) - len(taps)),
        "extra_tap_count": max(0, len(taps) - len(beats)),
        "tap_times_s_json": json.dumps([round(value, 6) for value in taps], ensure_ascii=False),
        "beat_times_s_json": json.dumps([round(value, 6) for value in beats], ensure_ascii=False),
        "intervals_s_json": json.dumps([round(value, 6) for value in intervals_s], ensure_ascii=False),
        "asynchronies_ms_json": json.dumps([round(value * 1000.0, 3) for value in asynchronies_s], ensure_ascii=False),
    }


def generate_tap_times(
    *,
    beat_times_s: Iterable[float],
    phase_duration_s: float,
    seed: int,
    mode: str = "sampled",
    phase_kind: str = "sync_tapping",
    is_practice: bool = False,
    bias_s: float | None = None,
    jitter_sd_s: float | None = None,
    omission_rate: float | None = None,
) -> list[float]:
    """Generate deterministic simulated tap times relative to phase onset."""
    duration_s = max(0.0, float(phase_duration_s))
    if duration_s <= 0:
        return []

    rng = random.Random(int(seed))
    mode_token = str(mode or "sampled").strip().lower()
    phase_token = str(phase_kind or "").strip().lower()
    practice = bool(is_practice)
    if bias_s is None:
        if phase_token.endswith("sync_tapping"):
            bias_s = -0.015 if mode_token == "scripted" else -0.020
        else:
            bias_s = -0.004 if mode_token == "scripted" else -0.008
    if jitter_sd_s is None:
        if phase_token.endswith("sync_tapping"):
            jitter_sd_s = 0.006 if mode_token == "scripted" else 0.014
        else:
            jitter_sd_s = 0.008 if mode_token == "scripted" else 0.018
    if omission_rate is None:
        if mode_token == "scripted":
            omission_rate = 0.0
        elif phase_token.endswith("sync_tapping"):
            omission_rate = 0.0 if practice else 0.02
        else:
            omission_rate = 0.0 if practice else 0.04

    beat_list = [float(value) for value in beat_times_s if value is not None]
    if not beat_list:
        return []

    cumulative_drift = 0.0
    taps: list[float] = []
    for index, beat_time in enumerate(beat_list):
        if rng.random() < max(0.0, min(1.0, float(omission_rate))):
            continue

        if phase_token.endswith("continuation_tapping"):
            cumulative_drift += rng.gauss(0.0, float(jitter_sd_s) * 0.18)
        else:
            cumulative_drift = 0.0

        noisy_tap = (
            beat_time
            + float(bias_s)
            + cumulative_drift
            + rng.gauss(0.0, float(jitter_sd_s))
        )
        noisy_tap = max(0.0, min(duration_s - 0.001, noisy_tap))
        taps.append(round(noisy_tap, 6))

    taps.sort()
    return taps



def _phase_trigger(settings: Any, phase_name: str) -> int | None:
    triggers = getattr(settings, "triggers", {}) or {}
    if isinstance(triggers, dict):
        return triggers.get(phase_name)
    if hasattr(triggers, "get"):
        return triggers.get(phase_name)
    return None


def _qa_scale_duration(duration_s: float, win) -> float:
    base = max(0.0, float(duration_s))
    ctx = get_context()
    if ctx is None or not getattr(ctx.config, "enable_scaling", False):
        return base
    frame_time = float(getattr(win, "monitorFramePeriod", 1.0 / 60.0) or (1.0 / 60.0))
    min_frames = int(max(1, getattr(ctx.config, "min_frames", 2)))
    scaled = base * float(getattr(ctx.config, "timing_scale", 1.0))
    return max(scaled, frame_time * min_frames)


def _qa_scale_value(value_s: float, win) -> float:
    return _qa_scale_duration(value_s, win)


def _make_unit(
    *,
    win,
    kb,
    trigger_runtime,
    unit_label: str,
    phase: str,
    trial_id: int | str,
    block_id: str,
    condition_id: str,
    deadline_s: float | None,
    valid_keys: list[str],
    task_factors: dict[str, Any],
    stim_id: str,
):
    unit = StimUnit(unit_label, win, kb, runtime=trigger_runtime)
    set_trial_context(
        unit,
        trial_id=trial_id,
        phase=phase,
        deadline_s=deadline_s,
        valid_keys=valid_keys,
        block_id=block_id,
        condition_id=condition_id,
        task_factors=task_factors,
        stim_id=stim_id,
    )
    return unit


def _phase_mode(ctx: Any | None) -> str:
    if ctx is None:
        return "human"
    mode = str(getattr(ctx, "mode", "human") or "human").strip().lower()
    return mode or "human"


def _phase_context_factors(
    *,
    plan: dict[str, Any],
    phase_name: str,
    phase_kind: str,
    phase_duration_s: float,
    runtime_tempo_s: float,
    beat_times_s: list[float],
    is_practice: bool,
    mode: str,
) -> dict[str, Any]:
    return {
        "phase_kind": phase_kind,
        "phase_name": phase_name,
        "mode": mode,
        "condition_id": plan["condition_id"],
        "block_role": plan["block_role"],
        "trial_kind": plan["trial_kind"],
        "tempo_ms": plan["tempo_ms"],
        "tempo_s_nominal": plan["tempo_s"],
        "tempo_s_runtime": runtime_tempo_s,
        "sync_beats": plan["sync_beats"],
        "continuation_beats": plan["continuation_beats"],
        "phase_duration_s": phase_duration_s,
        "nominal_phase_duration_s": plan["sync_duration_s"] if phase_kind.endswith("sync_tapping") else plan["continuation_duration_s"],
        "is_practice": is_practice,
        "trial_seed": plan["trial_seed"],
        "beat_times_s": beat_times_s,
        "phase_tap_count": len(beat_times_s),
        "tap_key": plan["tap_key"],
        "start_key": plan["start_key"],
        "tone_frequency_hz": plan["tone_frequency_hz"],
        "tone_duration_s": plan["tone_duration_s"],
    }


def _resolve_simulated_taps(
    *,
    ctx: Any | None,
    phase_name: str,
    trial_id: int,
    block_id: str,
    condition_id: str,
    phase_duration_s: float,
    task_factors: dict[str, Any],
    beat_times_s: list[float],
    is_practice: bool,
) -> list[float] | None:
    if ctx is None:
        return None

    responder = getattr(ctx, "responder", None)
    if responder is None:
        mode = "scripted" if _phase_mode(ctx) == "sim" else "sampled"
        seed = stable_seed(ctx.session.seed if getattr(ctx, "session", None) is not None else 0, trial_id, block_id, condition_id, phase_name)
        return generate_tap_times(
            beat_times_s=beat_times_s,
            phase_duration_s=phase_duration_s,
            seed=seed,
            mode=mode,
            phase_kind=phase_name,
            is_practice=is_practice,
        )

    obs = Observation(
        mode=_phase_mode(ctx),
        trial_id=trial_id,
        block_id=block_id,
        phase=phase_name,
        valid_keys=[str(task_factors.get("tap_key", "space"))],
        deadline_s=phase_duration_s,
        response_window_open=True,
        response_window_s=phase_duration_s,
        condition_id=condition_id,
        task_factors=task_factors,
        stim_id=task_factors.get("stim_id"),
        t_phase_onset=0.0,
        t_phase_onset_global=0.0,
    )
    try:
        action = responder.act(obs)
    except TypeError:
        action = responder.act(obs.to_dict())  # type: ignore[arg-type]
    except Exception:
        action = None

    meta = dict(getattr(action, "meta", {}) or {}) if action is not None else {}
    tap_times = meta.get("tap_times_s") or meta.get("tap_times") or meta.get("tap_schedule_s")
    if isinstance(tap_times, list) and tap_times:
        try:
            return [float(value) for value in tap_times]
        except Exception:
            return None

    mode_hint = meta.get("mode")
    if not mode_hint and str(meta.get("source", "")).strip().lower() == "scripted":
        mode_hint = "scripted"
    mode = str(mode_hint or getattr(responder, "mode", _phase_mode(ctx)) or "sampled").strip().lower()
    seed = stable_seed(ctx.session.seed if getattr(ctx, "session", None) is not None else 0, trial_id, block_id, condition_id, phase_name, mode)
    return generate_tap_times(
        beat_times_s=beat_times_s,
        phase_duration_s=phase_duration_s,
        seed=seed,
        mode=mode,
        phase_kind=phase_name,
        is_practice=is_practice,
    )


def _show_text_phase(
    *,
    stim_bank,
    trigger_runtime,
    win,
    kb,
    settings,
    trial_id: int,
    block_id: str,
    condition_id: str,
    phase: str,
    unit_label: str,
    valid_keys: list[str],
    task_factors: dict[str, Any],
    stim_id: str,
    text_id: str,
    text_kwargs: dict[str, Any] | None = None,
    duration_s: float | None = None,
    capture: bool = False,
    terminate_on_response: bool = False,
    response_trigger: int | dict[str, int] | None = None,
    timeout_trigger: int | None = None,
):
    unit = _make_unit(
        win=win,
        kb=kb,
        trigger_runtime=trigger_runtime,
        unit_label=unit_label,
        phase=phase,
        trial_id=trial_id,
        block_id=block_id,
        condition_id=condition_id,
        deadline_s=duration_s,
        valid_keys=valid_keys,
        task_factors=task_factors,
        stim_id=stim_id,
    )
    unit.add_stim(stim_bank.get_and_format(text_id, **(text_kwargs or {})))
    onset_trigger = _phase_trigger(settings, f"{phase}_onset")
    if capture:
        unit.capture_response(
            keys=valid_keys,
            duration=float(duration_s if duration_s is not None else 0.0),
            onset_trigger=onset_trigger,
            response_trigger=response_trigger,
            timeout_trigger=timeout_trigger,
            terminate_on_response=terminate_on_response,
        )
    elif valid_keys:
        unit.wait_and_continue(keys=valid_keys, terminate=terminate_on_response)
    else:
        unit.show(duration=duration_s, onset_trigger=onset_trigger)
    return unit


def _show_fixation_phase(
    *,
    stim_bank,
    trigger_runtime,
    win,
    kb,
    settings,
    trial_id: int,
    block_id: str,
    condition_id: str,
    phase: str,
    unit_label: str,
    duration_s: float,
    task_factors: dict[str, Any],
    stim_id: str,
):
    unit = _make_unit(
        win=win,
        kb=kb,
        trigger_runtime=trigger_runtime,
        unit_label=unit_label,
        phase=phase,
        trial_id=trial_id,
        block_id=block_id,
        condition_id=condition_id,
        deadline_s=duration_s,
        valid_keys=[],
        task_factors=task_factors,
        stim_id=stim_id,
    )
    unit.add_stim(stim_bank.get("fixation"))
    unit.show(duration=duration_s, onset_trigger=_phase_trigger(settings, f"{phase}_onset"))
    return unit


def _run_tapping_phase(
    *,
    stim_bank,
    trigger_runtime,
    win,
    kb,
    settings,
    trial_id: int,
    block_id: str,
    condition_id: str,
    phase: str,
    unit_label: str,
    phase_duration_s: float,
    tap_key: str,
    beat_times_s: list[float],
    task_factors: dict[str, Any],
    stim_id: str,
    phase_kind: str,
    is_practice: bool,
):
    unit = _make_unit(
        win=win,
        kb=kb,
        trigger_runtime=trigger_runtime,
        unit_label=unit_label,
        phase=phase,
        trial_id=trial_id,
        block_id=block_id,
        condition_id=condition_id,
        deadline_s=phase_duration_s,
        valid_keys=[tap_key],
        task_factors=task_factors,
        stim_id=stim_id,
    )
    unit.add_stim(stim_bank.get("fixation"))
    tone_stim = None
    if phase_kind.endswith("sync_tapping"):
        tone_stim = stim_bank.get("metronome_tone")
        unit.add_stim(tone_stim)

    ctx = get_context()
    simulated_taps = _resolve_simulated_taps(
        ctx=ctx,
        phase_name=phase,
        trial_id=trial_id,
        block_id=block_id,
        condition_id=condition_id,
        phase_duration_s=phase_duration_s,
        task_factors={**task_factors, "stim_id": stim_id},
        beat_times_s=beat_times_s,
        is_practice=is_practice,
    )

    phase_clock = core.Clock()
    onset_trigger = _phase_trigger(settings, f"{phase}_onset")
    trigger_runtime.send(onset_trigger)
    win.callOnFlip(kb.clearEvents)
    win.callOnFlip(kb.clock.reset)
    win.callOnFlip(phase_clock.reset)
    if tone_stim is not None and beat_times_s:
        win.callOnFlip(tone_stim.play)
    flip_time = win.flip()

    unit.set_state(
        onset_time=0.0,
        onset_time_global=flip_time,
        flip_time=flip_time,
        duration=phase_duration_s,
        phase_duration_s=phase_duration_s,
        tap_key=tap_key,
        phase_kind=phase_kind,
        is_practice=is_practice,
        beat_times_s_json=json.dumps([round(value, 6) for value in beat_times_s], ensure_ascii=False),
    )

    taps_s: list[float] = []
    tone_times_s: list[float] = []
    next_tone_idx = 0
    next_sim_idx = 0
    first_tap_rt_s: float | None = None
    if tone_stim is not None and beat_times_s:
        tone_times_s.append(float(beat_times_s[0]))
        next_tone_idx = 1

    while True:
        elapsed_s = phase_clock.getTime()
        if elapsed_s >= phase_duration_s:
            break

        if tone_stim is not None:
            while next_tone_idx < len(beat_times_s) and elapsed_s >= beat_times_s[next_tone_idx]:
                tone_stim.play()
                tone_times_s.append(float(beat_times_s[next_tone_idx]))
                next_tone_idx += 1

        fixation = stim_bank.get("fixation")
        fixation.draw()
        win.flip()

        if simulated_taps is None:
            keys = kb.getKeys(keyList=[tap_key], waitRelease=False)
            for key in keys:
                if str(key.name).strip().lower() != tap_key:
                    continue
                rt = float(key.rt) if key.rt is not None else float(phase_clock.getTime())
                taps_s.append(rt)
                if first_tap_rt_s is None:
                    first_tap_rt_s = rt
                trigger_runtime.send(_phase_trigger(settings, "tap_press"))
        else:
            now_s = phase_clock.getTime()
            while next_sim_idx < len(simulated_taps) and now_s >= float(simulated_taps[next_sim_idx]):
                tap_rt = float(simulated_taps[next_sim_idx])
                taps_s.append(tap_rt)
                if first_tap_rt_s is None:
                    first_tap_rt_s = tap_rt
                trigger_runtime.send(_phase_trigger(settings, "tap_press"))
                next_sim_idx += 1

    if simulated_taps is not None:
        while next_sim_idx < len(simulated_taps) and float(simulated_taps[next_sim_idx]) <= phase_duration_s:
            tap_rt = float(simulated_taps[next_sim_idx])
            taps_s.append(tap_rt)
            if first_tap_rt_s is None:
                first_tap_rt_s = tap_rt
            trigger_runtime.send(_phase_trigger(settings, "tap_press"))
            next_sim_idx += 1
    else:
        keys = kb.getKeys(keyList=[tap_key], waitRelease=False)
        for key in keys:
            if str(key.name).strip().lower() != tap_key:
                continue
            rt = float(key.rt) if key.rt is not None else float(phase_clock.getTime())
            taps_s.append(rt)
            if first_tap_rt_s is None:
                first_tap_rt_s = rt
            trigger_runtime.send(_phase_trigger(settings, "tap_press"))

    phase_close_s = float(phase_clock.getTime())
    if phase_kind.endswith("sync_tapping"):
        metrics = compute_sync_metrics(tap_times_s=taps_s, beat_times_s=beat_times_s)
    else:
        metrics = compute_continuation_metrics(tap_times_s=taps_s, beat_times_s=beat_times_s)
    metrics.update(
        {
            "phase_duration_s": phase_duration_s,
            "phase_close_s": phase_close_s,
            "tone_times_s_json": json.dumps([round(value, 6) for value in tone_times_s], ensure_ascii=False),
            "response_received": bool(taps_s),
            "response_label": tap_key if taps_s else None,
            "response_rt_s": first_tap_rt_s,
        }
    )

    unit.set_state(**metrics, close_time=phase_close_s, close_time_global=flip_time + phase_close_s)
    unit.log_unit()
    unit.to_dict()
    return unit, metrics


def summarizeBlock(reducedRows: list[dict[str, Any]], blockId: str) -> dict[str, Any]:
    rows = [row for row in reducedRows if str(row.get("block_id", "")) == str(blockId)]
    return _summarize(rows)


def summarizeOverall(reducedRows: list[dict[str, Any]]) -> dict[str, Any]:
    return _summarize(list(reducedRows))


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "trial_count": 0,
            "practice_trials": 0,
            "test_trials": 0,
            "response_count": 0,
            "tap_count": 0,
            "miss_count": 0,
            "mean_sync_abs_asynchrony_ms": 0.0,
            "mean_sync_asynchrony_ms": 0.0,
            "mean_continuation_abs_asynchrony_ms": 0.0,
            "mean_continuation_iti_ms": 0.0,
            "continuation_iti_cv": 0.0,
            "mean_first_tap_rt_s": 0.0,
            "miss_rate": 0.0,
            "total_elapsed_s": 0.0,
            "total_elapsed_min": 0.0,
        }

    practice_rows = [row for row in rows if str(row.get("block_role", "")).strip().lower() == "practice"]
    test_rows = [row for row in rows if str(row.get("block_role", "")).strip().lower() == "test"]
    scored_rows = test_rows or rows

    sync_abs_values = [float(row.get("sync_mean_abs_asynchrony_ms", 0.0) or 0.0) for row in scored_rows]
    sync_signed_values = [float(row.get("sync_mean_asynchrony_ms", 0.0) or 0.0) for row in scored_rows]
    cont_abs_values = [float(row.get("continuation_mean_abs_asynchrony_ms", 0.0) or 0.0) for row in scored_rows]
    cont_iti_values = [float(row.get("continuation_mean_iti_ms", 0.0) or 0.0) for row in scored_rows]
    cont_cv_values = [float(row.get("continuation_iti_cv", 0.0) or 0.0) for row in scored_rows]
    rt_values = [float(row["response_rt_s"]) for row in scored_rows if row.get("response_rt_s") is not None]

    expected_taps = 0
    observed_taps = 0
    for row in scored_rows:
        expected_taps += int(row.get("expected_tap_count", 0) or 0)
        observed_taps += int(row.get("tap_count", 0) or 0)

    total_elapsed_s = sum(float(row.get("trial_elapsed_s", 0.0) or 0.0) for row in rows)
    miss_count = max(0, expected_taps - observed_taps)

    return {
        "trial_count": len(rows),
        "practice_trials": len(practice_rows),
        "test_trials": len(test_rows),
        "response_count": sum(1 for row in scored_rows if row.get("response_received")),
        "tap_count": observed_taps,
        "miss_count": miss_count,
        "mean_sync_abs_asynchrony_ms": _safe_mean(sync_abs_values),
        "mean_sync_asynchrony_ms": _safe_mean(sync_signed_values),
        "mean_continuation_abs_asynchrony_ms": _safe_mean(cont_abs_values),
        "mean_continuation_iti_ms": _safe_mean(cont_iti_values),
        "continuation_iti_cv": _safe_mean(cont_cv_values),
        "mean_first_tap_rt_s": _safe_mean(rt_values),
        "miss_rate": (miss_count / expected_taps) if expected_taps else 0.0,
        "total_elapsed_s": float(total_elapsed_s),
        "total_elapsed_min": float(total_elapsed_s) / 60.0,
    }


__all__ = [
    "DEFAULT_CONDITIONS",
    "DEFAULT_CONTINUATION_BEATS",
    "DEFAULT_PRACTICE_CONDITION",
    "DEFAULT_PRACTICE_TEMPO_MS",
    "DEFAULT_SYNC_BEATS",
    "DEFAULT_TAP_KEY",
    "DEFAULT_TEMPO_LEVELS_MS",
    "DEFAULT_TONE_DURATION_S",
    "DEFAULT_TONE_FREQUENCY_HZ",
    "DEFAULT_START_KEY",
    "build_block_conditions",
    "build_trial_plan",
    "compute_continuation_metrics",
    "compute_sync_metrics",
    "format_duration_ms",
    "format_duration_s",
    "generate_tap_times",
    "parse_condition",
    "resolve_block_role",
    "resolve_block_trial_count",
    "stable_seed",
    "summarizeBlock",
    "summarizeOverall",
]
