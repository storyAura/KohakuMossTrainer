"""Web UI metrics: run discovery and the incremental metrics.jsonl reader."""

from kohakumoss.logging.sinks import METRICS
from kohakumoss.webui.metrics import find_runs, read_rows


def test_read_rows_incremental(tmp_path):
    path = tmp_path / METRICS
    path.write_text(
        '{"step": 10, "loss": 0.5, "lr": 1e-4, "tag": "x", "ok": true}\n'
        '{"step": 20, "loss": NaN}\n'
        '{"step": 30, "lo',
        encoding="utf-8",
    )
    rows, offset, reset = read_rows(path, 0)
    assert rows == [{"step": 10, "loss": 0.5, "lr": 1e-4}, {"step": 20, "loss": None}]
    assert not reset
    with path.open("a", encoding="utf-8") as f:
        f.write('ss": 0.25}\n')
    rows, offset2, _ = read_rows(path, offset)
    assert rows == [{"step": 30, "loss": 0.25}]
    assert read_rows(path, offset2) == ([], offset2, False)


def test_read_rows_reset_and_missing(tmp_path):
    path = tmp_path / METRICS
    path.write_text('{"step": 1, "loss": 1.0}\n', encoding="utf-8")
    rows, offset, reset = read_rows(path, 10_000)
    assert reset and rows == [{"step": 1, "loss": 1.0}]
    assert read_rows(tmp_path / "none.jsonl", 0) == ([], 0, False)
    assert read_rows(tmp_path / "none.jsonl", 5) == ([], 0, True)


def test_find_runs(tmp_path):
    for name in ("moss/a", "moss/b", "deep/x/y/z/w"):
        (tmp_path / name).mkdir(parents=True)
        (tmp_path / name / METRICS).write_text("", encoding="utf-8")
    found = {
        p.relative_to(tmp_path.resolve()).as_posix() for p in find_runs([tmp_path])
    }
    assert found == {"moss/a", "moss/b"}
