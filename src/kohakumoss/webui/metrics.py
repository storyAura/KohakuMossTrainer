"""Run metrics for the web UI: the run directories that hold a metrics.jsonl, and its
rows read incrementally from a byte offset."""

import json
import math
from pathlib import Path

from kohakumoss.logging.sinks import METRICS


def find_runs(roots: list[Path], depth: int = 3) -> list[Path]:
    """Directories under `roots` (the root itself up to `depth` levels down) that hold
    a metrics.jsonl, newest first."""
    found = set()
    for root in roots:
        for level in range(depth + 1):
            for path in root.glob("/".join(["*"] * level + [METRICS])):
                found.add(path.parent.resolve())
    return sorted(found, key=lambda p: -(p / METRICS).stat().st_mtime)


def _numbers(row: dict) -> dict:
    """The numeric fields of a row; non-finite values as None (JSON has no NaN)."""
    out = {}
    for key, value in row.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        out[key] = value if math.isfinite(value) else None
    return out


def read_rows(path: Path, offset: int) -> tuple[list[dict], int, bool]:
    """(rows, next offset, reset) of metrics file `path` after byte `offset`, whole
    lines only. `reset` is True when the file is shorter than `offset` (a fresh or
    resumed run rewrote it): the rows then start from the beginning."""
    size = path.stat().st_size if path.is_file() else 0
    reset = offset > size
    start = 0 if reset else offset
    if not size:
        return [], 0, reset
    with path.open("rb") as f:
        f.seek(start)
        data = f.read()
    end = data.rfind(b"\n") + 1
    rows = []
    for line in data[:end].splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(_numbers(row))
    return rows, start + end, reset
