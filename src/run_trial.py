from __future__ import annotations

import json
import time
from typing import Any

from psychopy import core

from psyflow import StimUnit, next_trial_id, set_trial_context
from psyflow.sim import Observation, get_context

from .utils import (
    build_trial_plan,
    compute_continuation_metrics,
    compute_sync_metrics,
    format_duration_ms,
    generate_tap_times,
    parse_condition,
    stable_seed,
)


def _get_setting(settings: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(settings, name):
            value = getattr(settings, name)
            if value is not None:
                return value
    return default


def _int_setting(settings: Any, *names: str, default: int) -> int:
    try:
        return int(_get_setting(settings, *names, default=default))
    except Exception:
        return int(default)


def _float_setting(settings: Any, *names: str, default: float) -> float:
    try:
        return float(_get_setting(settings, *names, default=default))
    except Exception:
        return float(default)


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


def run_trial(
    win,
    kb,
    settings,
    condition,
    stim_bank,
    trigger_runtime,
    block_id=None,
    block_idx=None,
    block_seed=None,
    block_role=None,
    block_trial_offset=None,
    block_trial_count=None,
):
    """Run one tapping-synchronization trial."""

    trial_id = int(next_trial_id())
    trial_start_perf = time.perf_counter()

    condition_info = parse_condition(condition)
    block_idx_value = int(block_idx if block_idx is not None else 0)
    block_num_value = block_idx_value + 1
    block_id_value = str(block_id) if block_id is not None else f"block_{block_num_value:02d}"
    block_role_value = str(block_role or condition_info["block_role"]).strip().lower()

    overall_seed = _int_setting(settings, "overall_seed", default=42044)
    trial_seed_base = int(block_seed if block_seed is not None else overall_seed)
    plan = build_trial_plan(
        condition=condition,
        block_idx=block_idx_value,
        trial_index=trial_id,
        overall_seed=trial_seed_base,
        settings=settings,
    )

    if block_role_value not in {"practice", "test"}:
        block_role_value = plan["block_role"]

    ready_duration_s = _float_setting(settings, "ready_duration_s", default=0.8)
    break_duration_s = _float_setting(settings, "break_duration_s", default=1.0)
    iti_duration_s = _float_setting(settings, "iti_duration_s", default=0.8)
    start_key = str(plan["start_key"]).strip().lower()
    tap_key = str(plan["tap_key"]).strip().lower()

    runtime_tempo_s = _qa_scale_value(plan["tempo_s"], win)
    sync_duration_runtime_s = runtime_tempo_s * float(plan["sync_beats"])
    continuation_duration_runtime_s = runtime_tempo_s * float(plan["continuation_beats"])
    total_runtime_tapping_s = sync_duration_runtime_s + continuation_duration_runtime_s
    ready_duration_runtime_s = _qa_scale_duration(ready_duration_s, win)
    break_duration_runtime_s = _qa_scale_duration(break_duration_s, win)
    iti_duration_runtime_s = _qa_scale_duration(iti_duration_s, win)

    sync_beat_times_runtime_s = [round(i * runtime_tempo_s, 6) for i in range(plan["sync_beats"])]
    continuation_beat_times_runtime_s = [round(i * runtime_tempo_s, 6) for i in range(plan["continuation_beats"])]

    trial_data: dict[str, Any] = {
        "trial_id": trial_id,
        "block_id": block_id_value,
        "block_idx": block_idx_value,
        "block_role": block_role_value,
        "condition_id": plan["condition_id"],
        "trial_kind": plan["trial_kind"],
        "is_practice": plan["is_practice"],
        "tempo_ms": plan["tempo_ms"],
        "tempo_s_nominal": plan["tempo_s"],
        "tempo_s_runtime": runtime_tempo_s,
        "sync_beats": plan["sync_beats"],
        "continuation_beats": plan["continuation_beats"],
        "sync_duration_s_nominal": plan["sync_duration_s"],
        "sync_duration_s_runtime": sync_duration_runtime_s,
        "continuation_duration_s_nominal": plan["continuation_duration_s"],
        "continuation_duration_s_runtime": continuation_duration_runtime_s,
        "total_tapping_duration_s_nominal": plan["total_phase_duration_s"],
        "total_tapping_duration_s_runtime": total_runtime_tapping_s,
        "tone_frequency_hz": plan["tone_frequency_hz"],
        "tone_duration_s": plan["tone_duration_s"],
        "tap_key": tap_key,
        "start_key": start_key,
        "trial_seed": plan["trial_seed"],
        "overall_seed": overall_seed,
        "block_seed": trial_seed_base,
        "practice_trials": _int_setting(settings, "practice_trials", default=1),
        "test_trials": _int_setting(settings, "test_trials", default=6),
        "ready_duration_s": ready_duration_runtime_s,
        "break_duration_s": break_duration_runtime_s,
        "iti_duration_s": iti_duration_runtime_s,
    }

    ctx = get_context()
    mode = _phase_mode(ctx)

    # Instruction/ready phases are participant-visible and require explicit context.
    if trial_data["is_practice"]:
        ready_phase = "practice_ready"
        ready_text_id = "practice_ready_text"
        ready_stim_id = "practice_ready_text"
    else:
        ready_phase = "test_ready"
        ready_text_id = "test_ready_text"
        ready_stim_id = "test_ready_text"

    ready_factors = {
        "phase_kind": "ready",
        "mode": mode,
        "condition_id": plan["condition_id"],
        "block_role": block_role_value,
        "trial_kind": plan["trial_kind"],
        "tempo_ms": plan["tempo_ms"],
        "tap_key": tap_key,
        "start_key": start_key,
        "trial_seed": plan["trial_seed"],
        "is_practice": plan["is_practice"],
        "phase_duration_s": ready_duration_runtime_s,
    }
    _show_text_phase(
        stim_bank=stim_bank,
        trigger_runtime=trigger_runtime,
        win=win,
        kb=kb,
        settings=settings,
        trial_id=trial_id,
        block_id=block_id_value,
        condition_id=plan["condition_id"],
        phase=ready_phase,
        unit_label=ready_phase,
        valid_keys=[start_key],
        task_factors=ready_factors,
        stim_id=ready_stim_id,
        text_id=ready_text_id,
        text_kwargs={
            "tempo_ms": format_duration_ms(plan["tempo_ms"]),
            "practice_trials": trial_data["practice_trials"],
            "test_trials": trial_data["test_trials"],
            "tap_key": "空格键",
        },
        duration_s=ready_duration_runtime_s,
        capture=True,
        terminate_on_response=True,
    ).to_dict(trial_data)

    # Synchronization window.
    sync_phase = "practice_sync_tapping" if trial_data["is_practice"] else "sync_tapping"
    sync_task_factors = _phase_context_factors(
        plan=plan,
        phase_name=sync_phase,
        phase_kind="sync_tapping",
        phase_duration_s=sync_duration_runtime_s,
        runtime_tempo_s=runtime_tempo_s,
        beat_times_s=sync_beat_times_runtime_s,
        is_practice=trial_data["is_practice"],
        mode=mode,
    )
    sync_task_factors["stim_id"] = "fixation+metronome_tone"
    sync_unit, sync_metrics = _run_tapping_phase(
        stim_bank=stim_bank,
        trigger_runtime=trigger_runtime,
        win=win,
        kb=kb,
        settings=settings,
        trial_id=trial_id,
        block_id=block_id_value,
        condition_id=plan["condition_id"],
        phase=sync_phase,
        unit_label=sync_phase,
        phase_duration_s=sync_duration_runtime_s,
        tap_key=tap_key,
        beat_times_s=sync_beat_times_runtime_s,
        task_factors=sync_task_factors,
        stim_id="fixation+metronome_tone",
        phase_kind="sync_tapping",
        is_practice=trial_data["is_practice"],
    )
    sync_unit.to_dict(trial_data)

    # Continuation window.
    continuation_phase = "practice_continuation_tapping" if trial_data["is_practice"] else "continuation_tapping"
    continuation_task_factors = _phase_context_factors(
        plan=plan,
        phase_name=continuation_phase,
        phase_kind="continuation_tapping",
        phase_duration_s=continuation_duration_runtime_s,
        runtime_tempo_s=runtime_tempo_s,
        beat_times_s=continuation_beat_times_runtime_s,
        is_practice=trial_data["is_practice"],
        mode=mode,
    )
    continuation_task_factors["stim_id"] = "fixation"
    continuation_unit, continuation_metrics = _run_tapping_phase(
        stim_bank=stim_bank,
        trigger_runtime=trigger_runtime,
        win=win,
        kb=kb,
        settings=settings,
        trial_id=trial_id,
        block_id=block_id_value,
        condition_id=plan["condition_id"],
        phase=continuation_phase,
        unit_label=continuation_phase,
        phase_duration_s=continuation_duration_runtime_s,
        tap_key=tap_key,
        beat_times_s=continuation_beat_times_runtime_s,
        task_factors=continuation_task_factors,
        stim_id="fixation",
        phase_kind="continuation_tapping",
        is_practice=trial_data["is_practice"],
    )
    continuation_unit.to_dict(trial_data)

    # Summary fields for downstream QA and goodbye screen.
    response_received = bool(sync_metrics["tap_count"] or continuation_metrics["tap_count"])
    response_rt_candidates = [
        sync_metrics.get("first_tap_rt_s"),
        continuation_metrics.get("first_tap_rt_s"),
    ]
    response_rt_s = next((float(value) for value in response_rt_candidates if value is not None), None)
    trial_data.update(
        {
            "sync_tap_count": sync_metrics["tap_count"],
            "sync_expected_tap_count": sync_metrics["expected_tap_count"],
            "sync_paired_tap_count": sync_metrics["paired_tap_count"],
            "sync_first_tap_rt_s": sync_metrics["first_tap_rt_s"],
            "sync_mean_asynchrony_ms": sync_metrics["mean_asynchrony_ms"],
            "sync_mean_abs_asynchrony_ms": sync_metrics["mean_abs_asynchrony_ms"],
            "sync_omission_count": sync_metrics["omission_count"],
            "sync_extra_tap_count": sync_metrics["extra_tap_count"],
            "sync_tap_times_s_json": sync_metrics["tap_times_s_json"],
            "sync_beat_times_s_json": sync_metrics["beat_times_s_json"],
            "sync_asynchronies_ms_json": sync_metrics["asynchronies_ms_json"],
            "continuation_tap_count": continuation_metrics["tap_count"],
            "continuation_expected_tap_count": continuation_metrics["expected_tap_count"],
            "continuation_paired_tap_count": continuation_metrics["paired_tap_count"],
            "continuation_first_tap_rt_s": continuation_metrics["first_tap_rt_s"],
            "continuation_mean_asynchrony_ms": continuation_metrics["mean_asynchrony_ms"],
            "continuation_mean_abs_asynchrony_ms": continuation_metrics["mean_abs_asynchrony_ms"],
            "continuation_mean_iti_ms": continuation_metrics["mean_iti_ms"],
            "continuation_iti_cv": continuation_metrics["iti_cv"],
            "continuation_omission_count": continuation_metrics["omission_count"],
            "continuation_extra_tap_count": continuation_metrics["extra_tap_count"],
            "continuation_tap_times_s_json": continuation_metrics["tap_times_s_json"],
            "continuation_beat_times_s_json": continuation_metrics["beat_times_s_json"],
            "continuation_intervals_s_json": continuation_metrics["intervals_s_json"],
            "continuation_asynchronies_ms_json": continuation_metrics["asynchronies_ms_json"],
            "tap_count": int(sync_metrics["tap_count"]) + int(continuation_metrics["tap_count"]),
            "expected_tap_count": int(sync_metrics["expected_tap_count"]) + int(continuation_metrics["expected_tap_count"]),
            "miss_count": int(sync_metrics["omission_count"]) + int(continuation_metrics["omission_count"]),
            "response_received": response_received,
            "response_label": tap_key if response_received else None,
            "response_rt_s": response_rt_s,
            "trial_elapsed_s": time.perf_counter() - trial_start_perf,
        }
    )

    if trial_data["is_practice"]:
        break_task_factors = {
            "phase_kind": "practice_break",
            "mode": mode,
            "condition_id": plan["condition_id"],
            "block_role": block_role_value,
            "trial_kind": plan["trial_kind"],
            "tempo_ms": plan["tempo_ms"],
            "tap_key": tap_key,
            "start_key": start_key,
            "trial_seed": plan["trial_seed"],
            "is_practice": True,
            "phase_duration_s": break_duration_runtime_s,
        }
        _show_text_phase(
            stim_bank=stim_bank,
            trigger_runtime=trigger_runtime,
            win=win,
            kb=kb,
            settings=settings,
            trial_id=trial_id,
            block_id=block_id_value,
            condition_id=plan["condition_id"],
            phase="practice_break",
            unit_label="practice_break",
            valid_keys=[start_key],
            task_factors=break_task_factors,
            stim_id="practice_break_text",
            text_id="practice_break_text",
            text_kwargs={
                "practice_trials": trial_data["practice_trials"],
                "test_trials": trial_data["test_trials"],
                "tempo_ms": format_duration_ms(plan["tempo_ms"]),
            },
            duration_s=break_duration_runtime_s,
            capture=True,
            terminate_on_response=True,
        ).to_dict(trial_data)
    else:
        _show_fixation_phase(
            stim_bank=stim_bank,
            trigger_runtime=trigger_runtime,
            win=win,
            kb=kb,
            settings=settings,
            trial_id=trial_id,
            block_id=block_id_value,
            condition_id=plan["condition_id"],
            phase="test_iti",
            unit_label="test_iti",
            duration_s=iti_duration_runtime_s,
            task_factors={
                "phase_kind": "test_iti",
                "mode": mode,
                "condition_id": plan["condition_id"],
                "block_role": block_role_value,
                "trial_kind": plan["trial_kind"],
                "tempo_ms": plan["tempo_ms"],
                "tap_key": tap_key,
                "trial_seed": plan["trial_seed"],
                "is_practice": False,
                "phase_duration_s": iti_duration_runtime_s,
            },
            stim_id="fixation",
        ).to_dict(trial_data)

    trial_data["trial_elapsed_s"] = time.perf_counter() - trial_start_perf
    return trial_data
