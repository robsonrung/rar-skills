"""Local, isolated execution lanes for concurrent Cline-backed seats.

Lanes intentionally contain paths and provider metadata only. Credentials stay
inside Cline's authenticated state directory and are never read or copied by
this module. A bounded file-lock pool protects a shared provider credential
from accidental fan-out beyond its configured concurrency.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


BUILTIN_LANE_NAMES = frozenset({"kimi", "glm"})


class LaneConfigError(ValueError):
    """A lane cannot be used without risking a shared Cline state."""


class LaneCapacityError(RuntimeError):
    """All configured slots for a credential pool are currently occupied."""


@dataclass(frozen=True)
class ClineLane:
    name: str
    provider: str
    model: str | None
    data_dir: str
    credential_pool: str
    max_concurrency: int
    lock_dir: str


def default_lane_root() -> Path:
    """Cline-owned state location used by the zero-config Kimi/GLM lanes."""
    return Path.home() / ".cline" / "lanes"


def default_lock_dir() -> Path:
    """Machine-local locks need no user configuration or repo-local state."""
    return Path(tempfile.gettempdir()) / "rar-skills-cline-lanes"


def _providers_configured(data_dir: Path) -> bool:
    # Cline 3.0 places the state beneath data/, while earlier releases used the
    # provided directory directly. Accept both layouts so a version upgrade
    # cannot make an already-authenticated lane appear empty.
    return any(
        candidate.is_file()
        for candidate in (
            data_dir / "settings" / "providers.json",
            data_dir / "data" / "settings" / "providers.json",
        )
    )


def _last_used_provider(data_dir: Path) -> str | None:
    for providers_path in (
        data_dir / "settings" / "providers.json",
        data_dir / "data" / "settings" / "providers.json",
    ):
        try:
            payload = json.loads(providers_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        provider = payload.get("lastUsedProvider") if isinstance(payload, dict) else None
        if isinstance(provider, str) and provider.strip():
            return provider.strip()
    return None


def _builtin_lane(name: str) -> ClineLane:
    if name not in BUILTIN_LANE_NAMES:
        available = ", ".join(sorted(BUILTIN_LANE_NAMES))
        raise LaneConfigError(
            f"Cline lane {name!r} has no built-in profile (available: {available}). "
            "Pass --lane-file for a custom lane."
        )
    data_dir = default_lane_root() / name
    if not _providers_configured(data_dir):
        raise LaneConfigError(
            f"Built-in Cline lane {name!r} has no authenticated state under {data_dir}. "
            f"Run `cline auth --data-dir {data_dir}` once to provision it."
        )
    provider = _last_used_provider(data_dir)
    if not provider:
        raise LaneConfigError(
            f"Built-in Cline lane {name!r} has no lastUsedProvider in {data_dir}. "
            f"Run `cline auth --data-dir {data_dir}` and select a provider."
        )
    # Each built-in lane owns a distinct Cline state directory. Lanes that
    # selected the same provider share this two-slot pool, enough for the
    # Kimi+GLM pair while preventing unbounded fan-out. A custom --lane-file
    # can lower the limit for a particularly rate-limited credential.
    return ClineLane(
        name=name,
        provider=provider,
        model=None,
        data_dir=str(data_dir),
        credential_pool=f"builtin:{provider}",
        max_concurrency=2,
        lock_dir=str(default_lock_dir()),
    )


def load_lane(name: str, explicit_path: str | None = None) -> ClineLane:
    if explicit_path is None:
        return _builtin_lane(name)
    path = Path(explicit_path).expanduser()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LaneConfigError(f"Cannot read Cline lane file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise LaneConfigError(f"Cline lane file {path} is not valid JSON: {exc.msg}") from exc

    lanes = payload.get("lanes") if isinstance(payload, dict) else None
    config = lanes.get(name) if isinstance(lanes, dict) else None
    if not isinstance(config, dict):
        raise LaneConfigError(f"Cline lane {name!r} is not defined in {path}.")

    provider = config.get("provider")
    model = config.get("model")
    data_dir = config.get("data_dir")
    credential_pool = config.get("credential_pool")
    max_concurrency = config.get("max_concurrency")
    if not all(isinstance(value, str) and value.strip() for value in (provider, model, data_dir, credential_pool)):
        raise LaneConfigError(
            f"Cline lane {name!r} requires non-empty provider, model, data_dir, and credential_pool."
        )
    if not isinstance(max_concurrency, int) or isinstance(max_concurrency, bool) or max_concurrency < 1:
        raise LaneConfigError(f"Cline lane {name!r} requires max_concurrency >= 1.")

    resolved_data_dir = Path(data_dir).expanduser()
    if not resolved_data_dir.is_absolute():
        raise LaneConfigError(f"Cline lane {name!r} data_dir must be absolute: {data_dir!r}.")
    if not _providers_configured(resolved_data_dir):
        raise LaneConfigError(
            f"Cline lane {name!r} has no authenticated providers state under {resolved_data_dir}. "
            "Provision it with `cline auth` before using the lane."
        )

    lock_dir = config.get("lock_dir") or str(default_lock_dir())
    if not isinstance(lock_dir, str) or not lock_dir.strip():
        raise LaneConfigError(f"Cline lane {name!r} lock_dir must be a non-empty path.")
    return ClineLane(
        name=name,
        provider=provider.strip(),
        model=model.strip(),
        data_dir=str(resolved_data_dir),
        credential_pool=credential_pool.strip(),
        max_concurrency=max_concurrency,
        lock_dir=str(Path(lock_dir).expanduser()),
    )


def apply_lane(lane: ClineLane, provider: str | None, model: str | None, data_dir: str | None) -> tuple[str, str, str]:
    """Return lane-owned arguments, rejecting ambiguous caller overrides."""
    expected_data_dir = str(Path(lane.data_dir).expanduser())
    if provider and provider != lane.provider:
        raise LaneConfigError(
            f"Cline lane {lane.name!r} fixes provider={lane.provider!r}; received {provider!r}."
        )
    if lane.model and model and model != lane.model:
        raise LaneConfigError(
            f"Cline lane {lane.name!r} fixes model={lane.model!r}; received {model!r}."
        )
    if data_dir and str(Path(data_dir).expanduser()) != expected_data_dir:
        raise LaneConfigError(
            f"Cline lane {lane.name!r} fixes data_dir={expected_data_dir!r}; received {data_dir!r}."
        )
    resolved_model = lane.model or model
    if not resolved_model:
        raise LaneConfigError(
            f"Cline lane {lane.name!r} needs a runner default or explicit --model."
        )
    return lane.provider, resolved_model, expected_data_dir


def _pool_lock_path(lock_dir: Path, pool: str, slot: int) -> Path:
    digest = hashlib.sha256(pool.encode("utf-8")).hexdigest()
    return lock_dir / f"{digest}-{slot}.lock"


@contextmanager
def acquire_lane_slot(lane: ClineLane, wait_timeout: float) -> Iterator[int]:
    """Acquire one bounded cross-process slot for a lane's credential pool."""
    lock_dir = Path(lane.lock_dir)
    lock_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    deadline = time.monotonic() + max(0, wait_timeout)
    handles = []
    try:
        while True:
            for slot in range(lane.max_concurrency):
                handle = open(_pool_lock_path(lock_dir, lane.credential_pool, slot), "a+", encoding="utf-8")
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    handle.close()
                    continue
                handles.append(handle)
                yield slot
                return
            if time.monotonic() >= deadline:
                raise LaneCapacityError(
                    f"Cline credential pool {lane.credential_pool!r} reached its "
                    f"max_concurrency={lane.max_concurrency}."
                )
            time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
    finally:
        for handle in handles:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
