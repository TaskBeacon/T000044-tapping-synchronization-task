from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any

from psyflow.sim.contracts import Action, Feedback, Observation, SessionInfo

from src.utils import (
    DEFAULT_PRACTICE_TEMPO_MS,
    DEFAULT_START_KEY,
    DEFAULT_TAP_KEY,
    generate_tap_times,
    stable_seed,
)


def _obs_get(obs: Observation | dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(obs, dict):
        return obs.get(key, default)
    if hasattr(obs, key):
        value = getattr(obs, key)
        if value is not None:
            return value
    return default


def _obs_phase(obs: Observation | dict[str, Any]) -> str:
    phase = _obs_get(obs, "phase", "") or _obs_get(obs, "stage", "")
    return str(phase).strip().lower()


def _obs_keys(obs: Observation | dict[str, Any]) -> list[str]:
    raw = _obs_get(obs, "valid_keys", []) or []
    return [str(key).strip().lower() for key in list(raw)]


def _obs_factors(obs: Observation | dict[str, Any]) -> dict[str, Any]:
    factors = _obs_get(obs, "task_factors", {}) or {}
    if not isinstance(factors, dict):
        return {}
    return dict(factors)


@dataclass
class TaskSamplerResponder:
    """Deterministic tapping sampler for QA and simulation."""

    mode: str = "sampled"
    tap_key: str = DEFAULT_TAP_KEY
    start_key: str = DEFAULT_START_KEY
    continue_rt_s: float = 0.28
    sync_bias_ms: float = -18.0
    continuation_bias_ms: float = -6.0
    sync_jitter_ms: float = 12.0
    continuation_jitter_ms: float = 16.0
    sync_omission_rate: float = 0.0
    continuation_omission_rate: float = 0.04
    practice_sync_omission_rate: float = 0.0
    practice_continuation_omission_rate: float = 0.0
    ready_tap_rt_s: float = 0.22

    def __post_init__(self) -> None:
        self.mode = str(self.mode or "sampled").strip().lower()
        if self.mode not in {"scripted", "sampled"}:
            self.mode = "sampled"
        self.tap_key = str(self.tap_key or DEFAULT_TAP_KEY).strip().lower()
        self.start_key = str(self.start_key or DEFAULT_START_KEY).strip().lower()
        self.continue_rt_s = max(0.0, float(self.continue_rt_s))
        self.ready_tap_rt_s = max(0.0, float(self.ready_tap_rt_s))
        self.sync_bias_ms = float(self.sync_bias_ms)
        self.continuation_bias_ms = float(self.continuation_bias_ms)
        self.sync_jitter_ms = max(0.0, float(self.sync_jitter_ms))
        self.continuation_jitter_ms = max(0.0, float(self.continuation_jitter_ms))
        self.sync_omission_rate = min(1.0, max(0.0, float(self.sync_omission_rate)))
        self.continuation_omission_rate = min(1.0, max(0.0, float(self.continuation_omission_rate)))
        self.practice_sync_omission_rate = min(1.0, max(0.0, float(self.practice_sync_omission_rate)))
        self.practice_continuation_omission_rate = min(1.0, max(0.0, float(self.practice_continuation_omission_rate)))
        self._session: SessionInfo | None = None
        self._rng: Any = None

    def start_session(self, session: SessionInfo, rng: Any) -> None:
        self._session = session
        self._rng = rng

    def end_session(self) -> None:
        self._session = None
        self._rng = None

    def on_feedback(self, fb: Feedback) -> None:
        return None

    def _continue_action(self, valid_keys: list[str], phase: str) -> Action:
        key = self.start_key if self.start_key in valid_keys else (self.tap_key if self.tap_key in valid_keys else valid_keys[0])
        return Action(
            key=key,
            rt_s=self.continue_rt_s if phase not in {"instruction", "good_bye", "goodbye"} else self.ready_tap_rt_s,
            meta={"source": "task_sampler", "phase": phase, "kind": "continue"},
        )

    def _tapping_action(self, valid_keys: list[str], phase: str, factors: dict[str, Any]) -> Action:
        tempo_ms = float(factors.get("tempo_ms", DEFAULT_PRACTICE_TEMPO_MS))
        tempo_s = tempo_ms / 1000.0
        phase_duration_s = float(
            factors.get(
                "phase_duration_s",
                factors.get("sync_duration_s", factors.get("continuation_duration_s", tempo_s)),
            )
        )
        beat_times_s = factors.get("beat_times_s")
        if not isinstance(beat_times_s, list) or not beat_times_s:
            count = int(factors.get("phase_tap_count", factors.get("sync_beats", factors.get("continuation_beats", 0))))
            beat_times_s = [round(i * tempo_s, 6) for i in range(count)]
        is_practice = bool(factors.get("is_practice", False))
        phase_kind = str(factors.get("phase_kind", phase)).strip().lower()

        if phase_kind.endswith("sync_tapping"):
            bias_s = self.sync_bias_ms / 1000.0
            jitter_s = self.sync_jitter_ms / 1000.0
            omission_rate = self.practice_sync_omission_rate if is_practice else self.sync_omission_rate
        else:
            bias_s = self.continuation_bias_ms / 1000.0
            jitter_s = self.continuation_jitter_ms / 1000.0
            omission_rate = self.practice_continuation_omission_rate if is_practice else self.continuation_omission_rate

        seed = stable_seed(
            self._session.seed if self._session is not None else 0,
            self._session.participant_id if self._session is not None else "session",
            factors.get("trial_seed", 0),
            factors.get("block_id", ""),
            factors.get("condition_id", ""),
            phase,
        )
        tap_times_s = generate_tap_times(
            beat_times_s=beat_times_s,
            phase_duration_s=phase_duration_s,
            seed=seed,
            mode=self.mode,
            phase_kind=phase_kind,
            is_practice=is_practice,
            bias_s=bias_s,
            jitter_sd_s=jitter_s,
            omission_rate=omission_rate,
        )
        key = self.tap_key if self.tap_key in valid_keys else (valid_keys[0] if valid_keys else None)
        first_rt = tap_times_s[0] if tap_times_s else self.ready_tap_rt_s
        return Action(
            key=key,
            rt_s=first_rt,
            meta={
                "source": "task_sampler",
                "phase": phase,
                "kind": "tap_series",
                "mode": self.mode,
                "tempo_ms": tempo_ms,
                "phase_duration_s": phase_duration_s,
                "phase_kind": phase_kind,
                "is_practice": is_practice,
                "beat_times_s": beat_times_s,
                "tap_times_s": tap_times_s,
                "tap_count": len(tap_times_s),
                "expected_tap_count": len(beat_times_s),
                "first_tap_rt_s": first_rt,
            },
        )

    def act(self, obs: Observation | dict[str, Any]) -> Action:
        valid_keys = _obs_keys(obs)
        phase = _obs_phase(obs)
        factors = _obs_factors(obs)

        if not valid_keys:
            return Action(key=None, rt_s=None, meta={"source": "task_sampler", "phase": phase, "kind": "no_valid_keys"})

        if phase in {"instruction", "good_bye", "goodbye"} or phase.endswith("ready") or phase.endswith("break") or phase.endswith("iti"):
            return self._continue_action(valid_keys, phase)

        if phase.endswith("sync_tapping") or phase.endswith("continuation_tapping"):
            return self._tapping_action(valid_keys, phase, factors)

        return Action(
            key=valid_keys[0],
            rt_s=self.ready_tap_rt_s,
            meta={"source": "task_sampler", "phase": phase, "kind": "fallback"},
        )


__all__ = ["TaskSamplerResponder"]
