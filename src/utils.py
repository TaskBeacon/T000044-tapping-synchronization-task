from __future__ import annotations

import hashlib
import json
import math
import random
from statistics import fmean, pstdev
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
