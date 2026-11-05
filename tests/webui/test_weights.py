"""The WEIGHTS picker's folder scan (model-free)."""

from pathlib import Path

from kohakumoss.webui import weights
from tests._util.negative import must_fail


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "models" / "MOSS-Image-Base" / "transformer").mkdir(parents=True)
    (root / "models" / "notes").mkdir()
    comfy = tmp_path / "ComfyUI-aki" / "ComfyUI" / "models" / "diffusion_models"
    comfy.mkdir(parents=True)
    (comfy / "moss_image_base_int8_convrot.safetensors").write_bytes(b"")
    (tmp_path / "other" / "models" / "diffusion_models").mkdir(parents=True)
    return root


def check_find(find, root: Path) -> None:
    found = find(root)
    paths = [w["path"] for w in found]
    assert paths[0] == "models/MOSS-Image-Base", paths
    assert any(p.endswith("ComfyUI-aki/ComfyUI/models") for p in paths), paths
    assert not any(p.endswith("notes") for p in paths), paths
    assert [w["moss"] for w in found] == [True, True, False], found


def _no_moss_check(root: Path) -> list[dict]:
    """The broken variant: every ComfyUI folder counts as holding MOSS."""
    return [{**w, "moss": True} for w in weights.find(root)]


def test_find_weight_folders(tmp_path):
    root = _tree(tmp_path)
    check_find(weights.find, root)
    must_fail(lambda: check_find(_no_moss_check, root), "MOSS flag ignores the files")


def test_files_lists_comfy_parts_moss_first(tmp_path):
    root = _tree(tmp_path)
    comfy = tmp_path / "ComfyUI-aki" / "ComfyUI" / "models"
    (comfy / "text_encoders").mkdir()
    for name in (
        "qwen_3_4b.safetensors",
        "moss_image_qwen35_9b_bf16.safetensors",
        "a.txt",
    ):
        (comfy / "text_encoders" / name).write_bytes(b"")
    got = weights.files(comfy)
    assert got["text_encoders"] == [
        "moss_image_qwen35_9b_bf16.safetensors",
        "qwen_3_4b.safetensors",
    ]
    assert got["vae"] == [] and got["diffusion_models"] == [
        "moss_image_base_int8_convrot.safetensors"
    ]
    assert weights.files(root / "models" / "MOSS-Image-Base") == {
        part: [] for part in weights.PARTS
    }
