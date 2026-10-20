"""Web UI form coercion, config composition and job log parsing (model-free)."""

import json

import pytest

from kohakumoss.cli.config.validate import TRAIN, compose, repo_root
from kohakumoss.webui import forms
from kohakumoss.webui.jobs import line_kind, parse_progress
from kohakumoss.weights.layout import TEXT, VAE
from tests._util.negative import must_fail

LAYERS = {
    "algo": "lora",
    "data": "kohya",
    "vram": "24g",
    "precision": "bf16",
    "weights": "hf",
}


@pytest.mark.parametrize(
    "value, old, want",
    [
        ("2e-4", 1e-4, 2e-4),
        ("50", 100, 50),
        ("1e4", 1000, 10000),
        ("2.5e3", 1000, 2500),
        ("1e-4", 0.01, 1e-4),
        ("true", False, True),
        (False, True, False),
        ("768, 1024", (1024, 1024), (768, 1024)),
        (["a, b", "c"], [], ["a, b", "c"]),
        ([["512", "640"]], [(1024, 1024)], [(512, 640)]),
        ('{"factor": 8}', {}, {"factor": 8}),
        ("", None, None),
        ("int8", None, "int8"),
        (False, None, None),
        (True, None, True),
    ],
)
def test_coerce(value, old, want):
    assert forms.coerce(value, old) == want


def test_own_knobs_keeps_only_changes():
    base = {"LR": 1e-4, "SCHEDULE": {"mode": "cosine", "warmup": 100}, "DIM": 32}
    own = forms.own_knobs(base, {"LR": "1e-4", "SCHEDULE.warmup": "50", "DIM": "16"})
    assert own == {"SCHEDULE": {"mode": "cosine", "warmup": 50}, "DIM": 16}
    assert base["SCHEDULE"]["warmup"] == 100
    must_fail(lambda: _assert_no_error(base, {"NOPE": "1"}), "unknown knob")
    must_fail(lambda: _assert_no_error(base, {"LR": "abc"}), "bad float")


def _assert_no_error(base: dict, values: dict) -> None:
    with pytest.raises(forms.FormError):
        forms.own_knobs(base, values)
    raise AssertionError("FormError raised")


@pytest.mark.parametrize("value", ["2.5", "1e-1", "abc", "inf"])
def test_coerce_int_rejects_non_whole(value):
    with pytest.raises(ValueError):
        forms.coerce(value, 1000)


def test_safe_name():
    assert forms.safe_name("my-lora_v1.2") == "my-lora_v1.2"
    for bad in ("../x", "a/b", "", ".hidden", "x" * 65):
        with pytest.raises(forms.FormError):
            forms.safe_name(bad)


def test_train_starter_layers_and_datasets():
    root = repo_root()
    form = {
        "layers": LAYERS,
        "knobs": {"RUN_NAME": "t1", "LR": "2e-4"},
        "datasets": [{"path": "data/a", "weight": "2"}, {"path": " "}],
        "low_ram": True,
    }
    st, knobs = forms.train_starter(root, form)
    assert [p.stem for p in st.layers[1:]] == [f"{g}_{LAYERS[g]}" for g in LAYERS]
    assert knobs["LR"] == 2e-4 and knobs["BASE_PRECISION"] == "int8"
    assert len(knobs["DATASETS"]) == 1 and knobs["DATASETS"][0]["weight"] == 2.0
    assert knobs["DATASETS"][0]["source"] == "kohya"
    assert knobs == compose(root, TRAIN, st.layers, st.own)
    with pytest.raises(forms.FormError):
        forms.train_starter(root, {**form, "layers": {**LAYERS, "algo": "nope"}})


def test_tag_switches_leave_nl_captions_alone():
    root = repo_root()
    knobs = {"CAPTION.shuffle": False, "CAPTION.tag_dropout": ""}
    form = {"layers": {**LAYERS, "data": "folder_nl"}, "knobs": knobs}
    st, composed = forms.train_starter(root, form)
    assert "CAPTION" not in st.own
    assert composed["CAPTION"] == {"template": "nl"}


def test_encoder_source(tmp_path):
    flat = tmp_path / "flat"
    flat.mkdir()
    te = flat / "qwen3.5_9b_bf16.safetensors"
    te.write_bytes(b"")
    knobs = {
        "WEIGHTS": str(flat),
        "TEXT_ENCODER": str(te),
        "VAE": "",
        "VARIANT": "base",
    }
    assert forms.encoder_source(knobs, TEXT, "TEXT_ENCODER") == str(te)
    assert forms.encoder_source(knobs, VAE, "VAE") == str(flat)
    comfy = tmp_path / "comfy"
    (comfy / "text_encoders").mkdir(parents=True)
    named = comfy / "text_encoders" / "qwen3.5_9b_int8_convrot.safetensors"
    named.write_bytes(b"")
    knobs = {**knobs, "WEIGHTS": str(comfy), "TEXT_ENCODER": "qwen3.5_9b_int8_convrot"}
    assert forms.encoder_source(knobs, TEXT, "TEXT_ENCODER") == str(named)
    missing = {**knobs, "TEXT_ENCODER": "nope"}
    assert forms.encoder_source(missing, TEXT, "TEXT_ENCODER") == str(comfy)


def test_weights_layer_sets_layout():
    root = repo_root()
    _, hf = forms.train_starter(root, {"layers": LAYERS})
    _, comfy = forms.train_starter(root, {"layers": {**LAYERS, "weights": "comfy"}})
    assert hf["WEIGHTS"] == "models/MOSS-Image-Base" and hf["TRANSFORMER"] == ""
    assert comfy["WEIGHTS"] == "ComfyUI/models" and comfy["TRANSFORMER"]


def test_config_file_round_trip(tmp_path):
    data = {"vram": "8g", "LR": "1e-4", "datasets": [{"path": "D:/data/x"}], "DIM": 16}
    path = forms.write_config(tmp_path, "sub/run.json", data)
    assert path == tmp_path / "sub" / "run.json"
    assert not list(tmp_path.rglob("*.tmp"))
    assert forms.read_config(tmp_path, "sub/run.json") == data
    assert list(json.loads(path.read_text(encoding="utf-8"))) == sorted(data)
    listed = forms.list_configs(tmp_path, "sub")
    assert [f["name"] for f in listed] == ["run"]
    assert forms.list_configs(tmp_path, "missing") == []


def test_config_file_rejects(tmp_path):
    with pytest.raises(forms.FormError):
        forms.write_config(tmp_path, "run.py", {})
    (tmp_path / "list.json").write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(forms.FormError):
        forms.read_config(tmp_path, "list.json")


def test_parse_progress():
    p = {"step": 0, "total": 0, "loss": None, "lr": None}
    assert parse_progress(p, "[12:00:00] [entry] [INFO] training from step 1 to 4000")
    assert p["total"] == 4000
    assert parse_progress(p, "[INFO] step 120 [loss=0.0912 grad_norm=0.3 lr=9.5e-05]")
    assert (p["step"], p["loss"], p["lr"]) == (120, 0.0912, 9.5e-05)
    assert parse_progress(p, " 37%|###   | 68/184 [00:12<00:20,  5.1latent/s]")
    assert (p["step"], p["total"]) == (68, 184)
    assert not parse_progress(p, "[INFO] loading weights")


def test_line_kind():
    assert line_kind("Traceback (most recent call last):") == "err"
    assert line_kind("[12:00:00] [x] [WARNING] slow disk") == "warn"
    assert line_kind("[12:00:00] [x] [INFO] step 1") == "ink"
