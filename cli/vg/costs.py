"""The spend ledger: one JSON line per paid call in VG_HOME/costs.jsonl.

Each line: {"at", "provider", "model", "op", "usd", "ok", ...}. `usd` is the provider's own charge when the
response carries one (OpenRouter's usage.cost), else null. Failed attempts are logged too, because some
providers bill a job that was accepted and then failed or timed out. `vg spend` sums the ledger.
"""

from __future__ import annotations

import datetime as dt
import json

from . import config


def _write(row: dict) -> None:
    row = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **row}
    try:
        path = config.home() / "costs.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(row, default=str) + "\n")
    except OSError:
        pass  # the ledger is a convenience; never fail a render over it


def usage(tool: str, provider: str, usage: dict | None, **fields) -> None:
    """A call that succeeded and reported usage (OpenRouter puts the charge in usage.cost)."""
    cost = (usage or {}).get("cost")
    _write({"provider": provider, "usd": float(cost) if cost is not None else None, "ok": True, **fields})


def record(tool: str, provider: str, usd: float | None = None, **fields) -> None:
    """A call that succeeded but reported no charge (speech, fal jobs)."""
    _write({"provider": provider, "usd": usd, "ok": True, **fields})


def attempt(tool: str, provider: str, **fields) -> None:
    """A call that failed or never answered. It may still have been billed."""
    fields.pop("body", None)  # error bodies can be long; the error is raised to the caller anyway
    _write({"provider": provider, "usd": None, "ok": False, **fields})


def rows() -> list[dict]:
    path = config.home() / "costs.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
