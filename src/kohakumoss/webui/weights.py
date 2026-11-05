"""Weight folders on this machine for the WEIGHTS picker: HF model dirs (transformer/)
and ComfyUI models folders (diffusion_models/) under the repo's models/ and next to the
repo, and the component files of a ComfyUI folder for the TRANSFORMER / TEXT_ENCODER /
VAE pickers. See docs/guides/webui.md#weights-picker."""

from pathlib import Path

OWN = ("models", "models/*")
BESIDE = ("*/models", "*/ComfyUI/models")
MOSS_GLOB = "moss_image*.safetensors"
PARTS = ("diffusion_models", "text_encoders", "vae")


def kind_of(path: Path) -> str:
    """'hf' (transformer/), 'comfy' (diffusion_models/) or '' for any other folder."""
    if (path / "transformer").is_dir():
        return "hf"
    if (path / "diffusion_models").is_dir():
        return "comfy"
    return ""


def has_moss(path: Path) -> bool:
    """A ComfyUI folder holds a MOSS-Image DiT file (directly or one level down)."""
    models = path / "diffusion_models"
    return any(models.glob(MOSS_GLOB)) or any(models.glob(f"*/{MOSS_GLOB}"))


def shown(path: Path, root: Path) -> str:
    """`path` relative to `root` when inside it, else absolute; forward slashes."""
    return (
        path.relative_to(root).as_posix() if root in path.parents else path.as_posix()
    )


def find(root: Path) -> list[dict]:
    """Weight folders matching OWN under `root` and BESIDE under its parent: path, kind
    and whether a MOSS-Image DiT is there (HF dirs count as MOSS); MOSS folders first,
    the repository's own before the ones beside it.
    """
    root = root.absolute()
    seen: dict[Path, str] = {}
    globs = [(root, g) for g in OWN] + [(root.parent, g) for g in BESIDE]
    for base, pattern in globs:
        for path in base.glob(pattern):
            if path not in seen and path.is_dir() and (kind := kind_of(path)):
                seen[path] = kind
    found = [
        {"path": shown(p, root), "kind": k, "moss": k == "hf" or has_moss(p)}
        for p, k in seen.items()
    ]
    return sorted(
        found, key=lambda w: (not w["moss"], Path(w["path"]).is_absolute(), w["path"])
    )


def files(path: Path) -> dict[str, list[str]]:
    """The .safetensors file names directly in each PARTS folder of a ComfyUI models
    folder, MOSS files first (empty lists for any other folder)."""
    if kind_of(path) != "comfy":
        return {part: [] for part in PARTS}
    return {
        part: sorted(
            (f.name for f in (path / part).glob("*.safetensors")),
            key=lambda n: ("moss" not in n.lower(), n),
        )
        for part in PARTS
    }
