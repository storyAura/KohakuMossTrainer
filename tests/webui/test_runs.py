"""Watching a run from its files: metric rows past a byte offset, the total from
log.txt, the run listing (model-free)."""

import json
from pathlib import Path

from kohakumoss.webui import runs
from tests._util.negative import must_fail


def _row(step: int, loss: float) -> str:
    return (
        json.dumps({"step": step, "time": 1.0 + step, "loss": loss, "lr": 1e-4}) + "\n"
    )


def _run(tmp_path: Path, rows: str, log: str = "") -> Path:
    run = tmp_path / "runs" / "moss" / "a"
    run.mkdir(parents=True)
    (run / runs.METRICS).write_text(rows, encoding="utf-8")
    (run / runs.LOG).write_text(log, encoding="utf-8")
    return run


def test_rows_after_offset_and_partial_line(tmp_path):
    run = _run(tmp_path, _row(1, 0.5) + _row(2, 0.4) + '{"step": 3')
    first = runs.rows_after(run, 0)
    assert [r["step"] for r in first["rows"]] == [1, 2]
    assert not first["reset"]
    with (run / runs.METRICS).open("a", encoding="utf-8") as f:
        f.write(', "loss": 0.3}\n')
    second = runs.rows_after(run, first["offset"])
    assert [r["step"] for r in second["rows"]] == [3]
    assert runs.rows_after(run, second["offset"])["rows"] == []


def test_rows_after_resets_on_a_fresh_file(tmp_path):
    run = _run(tmp_path, _row(1, 0.5) + _row(2, 0.4))
    offset = runs.rows_after(run, 0)["offset"]
    (run / runs.METRICS).write_text(_row(1, 0.9), encoding="utf-8")
    again = runs.rows_after(run, offset)
    assert again["reset"] and [r["loss"] for r in again["rows"]] == [0.9]


def test_rows_after_keeps_every_numeric_metric(tmp_path):
    line = {"step": 1, "loss": 0.5, "grad_norm": 0.01, "note": "x"}
    run = _run(tmp_path, json.dumps(line) + "\n")
    assert runs.rows_after(run, 0)["rows"] == [
        {"step": 1, "loss": 0.5, "grad_norm": 0.01}
    ]


def _rows_ignoring_offset(run, offset):
    """The broken variant: every call returns every row."""
    return runs.rows_after(run, 0)


def test_rows_after_negative(tmp_path):
    run = _run(tmp_path, _row(1, 0.5))

    def check(read):
        offset = read(run, 0)["offset"]
        assert read(run, offset)["rows"] == []

    check(runs.rows_after)
    must_fail(lambda: check(_rows_ignoring_offset), "rows re-read from byte 0")


def test_total_steps_takes_the_last_start_incrementally(tmp_path):
    run = _run(tmp_path, _row(1, 0.5), "x\ntraining from step 0 to 1000\n")
    assert runs.total_steps(run) == 1000
    with (run / runs.LOG).open("a", encoding="utf-8") as f:
        f.write("resume\ntraining from step 500 to 2000\n")
    assert runs.total_steps(run) == 2000
    (run / runs.LOG).write_text("fresh\n", encoding="utf-8")
    assert runs.total_steps(run) == 0


def test_find_lists_runs_newest_first(tmp_path):
    _run(tmp_path, _row(7, 0.25), "training from step 0 to 100\n")
    found = runs.find([tmp_path / "runs"], tmp_path.resolve())
    assert [r["run"] for r in found] == ["runs/moss/a"]
    assert found[0]["step"] == 7 and found[0]["total"] == 100 and found[0]["live"]
