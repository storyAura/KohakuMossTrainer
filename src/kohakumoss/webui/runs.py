"""Training runs on disk, whoever started them: the run directories under the allowed
roots that hold a metrics.jsonl, their progress (last row, the total from log.txt) and
the metric rows past a byte offset. See docs/guides/webui.md#watching-a-run."""

import json
import re
import time
from pathlib import Path

METRICS = "metrics.jsonl"
LOG = "log.txt"
RE_TOTAL = re.compile(r"training from step (\d+) to (\d+)")
LIVE_S = 120
TAIL_BYTES = 8192
DEPTHS = ("*", "*/*", "*/*/*")
FIELDS = ("step", "time", "loss", "lr")

_totals: dict[str, tuple[int, int]] = {}


def total_steps(run: Path) -> int:
    """The last `training from step a to b` b in `run`/log.txt (0 when absent); the
    scan resumes where the previous call stopped."""
    path = run / LOG
    key = str(path)
    offset, total = _totals.get(key, (0, 0))
    try:
        size = path.stat().st_size
    except OSError:
        return 0
    if size < offset:
        offset, total = 0, 0
    with path.open("rb") as f:
        f.seek(offset)
        chunk = f.read()
    end = chunk.rfind(b"\n") + 1
    for found in RE_TOTAL.finditer(chunk[:end].decode("utf-8", "replace")):
        total = int(found.group(2))
    _totals[key] = (offset + end, total)
    return total


def _last_row(path: Path) -> dict:
    """The last complete JSON row of `path` (empty when none)."""
    with path.open("rb") as f:
        f.seek(max(0, path.stat().st_size - TAIL_BYTES))
        lines = f.read().splitlines()
    for line in reversed(lines):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {}


def summary(run: Path, root: Path) -> dict:
    """A run as the API lists it: path (relative to `root` when inside it), last step,
    loss, total, mtime and whether a row landed in the last LIVE_S seconds."""
    path = run / METRICS
    mtime = path.stat().st_mtime
    row = _last_row(path)
    shown = run.relative_to(root).as_posix() if root in run.parents else run.as_posix()
    return {
        "run": shown,
        "step": int(row.get("step", 0) or 0),
        "loss": row.get("loss"),
        "total": total_steps(run),
        "updated": mtime,
        "live": time.time() - mtime < LIVE_S,
    }


def find(roots: list[Path], root: Path, limit: int = 30) -> list[dict]:
    """Runs (directories with a metrics.jsonl) up to three levels under each of
    `roots`, newest first."""
    seen: set[Path] = set()
    for base in roots:
        for depth in DEPTHS:
            seen.update(p.parent.resolve() for p in base.glob(f"{depth}/{METRICS}"))
    runs = sorted(seen, key=lambda r: (r / METRICS).stat().st_mtime, reverse=True)
    return [summary(r, root) for r in runs[:limit]]


def rows_after(run: Path, offset: int) -> dict:
    """The metric rows (FIELDS only) of the complete lines past byte `offset`, the new
    offset, and `reset` when the file is shorter than `offset` (a fresh run moved the
    old one aside; the rows then start from byte 0)."""
    path = run / METRICS
    size = path.stat().st_size
    reset = size < offset
    start = 0 if reset else offset
    with path.open("rb") as f:
        f.seek(start)
        chunk = f.read()
    end = chunk.rfind(b"\n") + 1
    rows = []
    for line in chunk[:end].splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        rows.append({k: row.get(k) for k in FIELDS})
    return {"rows": rows, "offset": start + end, "reset": reset}
