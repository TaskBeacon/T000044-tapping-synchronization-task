from __future__ import annotations

import time
from typing import Any


from psyflow import next_trial_id
from psyflow.sim import get_context

# set_trial_context(..., deadline_s=...) and capture_response(...) are applied
# inside the imported phase helpers in utils.py.
from .utils import (
    build_trial_plan,
    format_duration_ms,
    parse_condition,
    _phase_context_factors,
    _phase_mode,
    _qa_scale_duration,
    _qa_scale_value,
    _run_tapping_phase,
    _show_fixation_phase,
    _show_text_phase,
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
