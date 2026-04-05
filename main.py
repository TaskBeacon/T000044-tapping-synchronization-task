from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

import pandas as pd
from psychopy import core

from psyflow import (
    BlockUnit,
    StimBank,
    StimUnit,
    SubInfo,
    TaskRunOptions,
    TaskSettings,
    context_from_config,
    initialize_exp,
    initialize_triggers,
    load_config,
    parse_task_run_options,
    reset_trial_counter,
    runtime_context,
    set_trial_context,
)

from src import build_block_conditions, resolve_block_role, resolve_block_trial_count, run_trial, summarizeOverall


MODES = ("human", "qa", "sim")
DEFAULT_CONFIG_BY_MODE = {
    "human": "config/config.yaml",
    "qa": "config/config_qa.yaml",
    "sim": "config/config_scripted_sim.yaml",
}


def _parse_args(task_root: Path) -> TaskRunOptions:
    return parse_task_run_options(
        task_root=task_root,
        description="Run Tapping Synchronization Task in human/qa/sim mode.",
        default_config_by_mode=DEFAULT_CONFIG_BY_MODE,
        modes=MODES,
    )


def _resolve_block_seed(settings: TaskSettings, block_idx: int) -> int:
    block_seed = getattr(settings, "block_seed", None)
    if isinstance(block_seed, list) and block_idx < len(block_seed):
        candidate = block_seed[block_idx]
        if candidate is not None:
            try:
                return int(candidate)
            except Exception:
                pass
    try:
        return int(getattr(settings, "overall_seed", 42044))
    except Exception:
        return block_idx + 1


def _block_spec(settings: TaskSettings, block_idx: int) -> tuple[str, int]:
    block_role = resolve_block_role(block_idx)
    block_trials = resolve_block_trial_count(settings, block_role)
    return block_role, block_trials


def _show_instruction_screen(win, kb, stim_bank, trigger_runtime, *, settings: TaskSettings):
    unit = StimUnit("instruction", win, kb, runtime=trigger_runtime)
    set_trial_context(
        unit,
        trial_id="instruction",
        phase="instruction",
        deadline_s=None,
        valid_keys=["space"],
        block_id="instruction",
        condition_id="instruction",
        task_factors={
            "phase": "instruction",
            "practice_trials": getattr(settings, "practice_trials", 1),
            "test_trials": getattr(settings, "test_trials", 6),
            "tap_key": "space",
        },
        stim_id="instruction_text",
    )
    unit.add_stim(
        stim_bank.get_and_format(
            "instruction_text",
            practice_trials=getattr(settings, "practice_trials", 1),
            test_trials=getattr(settings, "test_trials", 6),
            tap_key="空格键",
        )
    )
    unit.wait_and_continue(keys=["space"], min_wait=0.0, terminate=False)


def _show_goodbye_screen(win, kb, stim_bank, trigger_runtime, *, summary: dict[str, Any]):
    unit = StimUnit("good_bye", win, kb, runtime=trigger_runtime)
    set_trial_context(
        unit,
        trial_id="good_bye",
        phase="good_bye",
        deadline_s=None,
        valid_keys=["space"],
        block_id="good_bye",
        condition_id="good_bye",
        task_factors={
            "phase": "good_bye",
            "trial_count": summary["trial_count"],
            "practice_trials": summary["practice_trials"],
            "test_trials": summary["test_trials"],
            "mean_sync_abs_asynchrony_ms": summary["mean_sync_abs_asynchrony_ms"],
            "mean_continuation_iti_ms": summary["mean_continuation_iti_ms"],
            "continuation_iti_cv": summary["continuation_iti_cv"],
            "miss_rate": summary["miss_rate"],
            "total_elapsed_min": summary["total_elapsed_min"],
        },
        stim_id="good_bye_text",
    )
    unit.add_stim(
        stim_bank.get_and_format(
            "good_bye_text",
            trial_count=summary["trial_count"],
            practice_trials=summary["practice_trials"],
            test_trials=summary["test_trials"],
            mean_sync_abs_asynchrony_ms=summary["mean_sync_abs_asynchrony_ms"],
            mean_continuation_iti_ms=summary["mean_continuation_iti_ms"],
            continuation_iti_cv=summary["continuation_iti_cv"],
            miss_rate=summary["miss_rate"],
            total_elapsed_min=summary["total_elapsed_min"],
        )
    )
    unit.wait_and_continue(keys=["space"], min_wait=0.0, terminate=False)


def run(options: TaskRunOptions):
    task_root = Path(__file__).resolve().parent
    cfg = load_config(str(options.config_path))
    mode = options.mode

    ctx = None
    output_dir = None
    if mode in ("qa", "sim"):
        ctx = context_from_config(task_dir=task_root, config=cfg, mode=mode)
        output_dir = ctx.output_dir

    if mode == "qa":
        participant_id = "qa"
    elif mode == "sim":
        participant_id = "sim001"
        if ctx is not None and getattr(ctx, "session", None) is not None:
            participant_id = str(ctx.session.participant_id or "sim001")
    else:
        participant_id = "human"

    runtime_scope = runtime_context(ctx) if ctx is not None else None
    if runtime_scope is None:
        _run_impl(mode=mode, output_dir=output_dir, cfg=cfg, participant_id=participant_id)
    else:
        with runtime_scope:
            _run_impl(mode=mode, output_dir=output_dir, cfg=cfg, participant_id=participant_id)


def _run_impl(*, mode: str, output_dir: Path | None, cfg: dict, participant_id: str):
    task_root = Path(__file__).resolve().parent

    if mode == "qa":
        subject_data = {"subject_id": "101"}
    elif mode == "sim":
        subject_data = {"subject_id": participant_id}
    else:
        subform = SubInfo(cfg["subform_config"])
        subject_data = subform.collect()

    settings = TaskSettings.from_dict(cfg["task_config"])
    if mode in ("qa", "sim") and output_dir is not None:
        settings.save_path = str(output_dir)

    settings.add_subinfo(subject_data)
    settings.triggers = cfg["trigger_config"]

    if mode == "qa" and output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        settings.res_file = str(output_dir / "qa_trace.csv")
        settings.log_file = str(output_dir / "qa_psychopy.log")
        settings.json_file = str(output_dir / "qa_settings.json")

    settings.save_to_json()

    if mode in ("qa", "sim"):
        trigger_runtime = initialize_triggers(mock=True)
    else:
        trigger_runtime = initialize_triggers(cfg)

    win, kb = initialize_exp(settings)
    reset_trial_counter()

    stim_bank = StimBank(win, cfg["stim_config"]).preload_all()

    trigger_runtime.send(settings.triggers.get("exp_onset"))
    _show_instruction_screen(win, kb, stim_bank, trigger_runtime, settings=settings)

    all_rows: list[dict[str, Any]] = []
    block_specs: list[tuple[str, int]] = []
    for block_idx in range(int(getattr(settings, "total_blocks", 2) or 2)):
        block_specs.append(_block_spec(settings, block_idx))

    block_trial_offset = 0
    for block_idx, (block_role, block_trials) in enumerate(block_specs):
        block_seed = _resolve_block_seed(settings, block_idx)
        block_id = f"block_{block_idx:02d}_{block_role}"
        block = (
            BlockUnit(
                block_id=block_id,
                block_idx=block_idx,
                settings=settings,
                window=win,
                keyboard=kb,
                n_trials=block_trials,
            )
            .generate_conditions(
                func=build_block_conditions,
                block_role=block_role,
                seed=block_seed,
                practice_condition="practice_600",
                tempo_conditions=["tempo_450", "tempo_600", "tempo_750"],
            )
            .on_start(lambda b, _settings=settings: trigger_runtime.send(_settings.triggers.get("block_onset")))
            .on_end(lambda b, _settings=settings: trigger_runtime.send(_settings.triggers.get("block_end")))
            .run_trial(
                partial(
                    run_trial,
                    stim_bank=stim_bank,
                    trigger_runtime=trigger_runtime,
                    block_id=block_id,
                    block_idx=block_idx,
                    block_seed=block_seed,
                    block_role=block_role,
                    block_trial_offset=block_trial_offset,
                    block_trial_count=block_trials,
                )
            )
            .to_dict(all_rows)
        )
        _ = block.get_all_data()
        block_trial_offset += block_trials

    overall_metrics = summarizeOverall(all_rows)
    _show_goodbye_screen(win, kb, stim_bank, trigger_runtime, summary=overall_metrics)

    trigger_runtime.send(settings.triggers.get("exp_end"))

    df = pd.DataFrame(all_rows)
    df.to_csv(settings.res_file, index=False)

    if hasattr(trigger_runtime, "close"):
        try:
            trigger_runtime.close()
        except Exception:
            pass
    core.quit()


def main() -> None:
    task_root = Path(__file__).resolve().parent
    options = _parse_args(task_root)
    run(options)


if __name__ == "__main__":
    main()
