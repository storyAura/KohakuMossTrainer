"""Web UI server: config forms, jobs (data preparation, training, sampling, export,
doctor, weights download), run artifacts and the built front end (webui/dist).

    kohakumoss-webui [--host 127.0.0.1] [--port 8787] [--no-browser]
"""

import argparse
import asyncio
import importlib.metadata as metadata
import os
import shutil
import subprocess
import sys
import threading
import uuid
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from kohakumoss.cli.config import presets
from kohakumoss.cli.config.starter import DATA_SCRIPTS
from kohakumoss.cli.config.validate import SAMPLE, TRAIN, repo_root
from kohakumoss.memory.profiles import ORDER as PROFILE_ORDER
from kohakumoss.webui import forms
from kohakumoss.webui.jobs import Job, manager

ROOT = repo_root()
WEIGHT_SETS = {
    "comfy": {
        "repo": "Comfy-Org/MOSS-Image",
        "dest": "ComfyUI/models",
        "files": [
            "diffusion_models/moss_image_base_int8_convrot.safetensors",
            "text_encoders/qwen3.5_9b_int8_convrot.safetensors",
            "vae/flux2-vae_small.safetensors",
        ],
    },
    "hf": {"repo": "OpenMOSS-Team/MOSS-Image-Base", "dest": "models/MOSS-Image-Base"},
}
MIRROR = "https://hf-mirror.com"
DATA_STEPS = dict(zip(("inspect", "text", "latents"), DATA_SCRIPTS))
IMAGES = (".png", ".jpg", ".jpeg", ".webp")
PACKAGES = ("torch", "kohakumoss", "lycoris-lora", "kohaku-engine", "triton-windows")
KOGINE = [sys.executable, "-m", "kohakuengine.cli"]
GPU_QUERY = "name,memory.total,memory.used,driver_version,compute_cap"
ALLOWED: set[Path] = {ROOT.resolve()}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    manager.bind_loop(asyncio.get_running_loop())
    yield


app = FastAPI(title="kohakumoss webui", lifespan=lifespan)


class TrainForm(BaseModel):
    layers: dict = Field(default_factory=dict)
    knobs: dict = Field(default_factory=dict)
    datasets: list[dict] = Field(default_factory=list)
    low_ram: bool = False


class TrainJob(TrainForm):
    prepare: list[str] = Field(default_factory=list)
    train: bool = True
    snapshot: dict = Field(default_factory=dict)


class ScriptForm(BaseModel):
    precision: str = "bf16"
    knobs: dict = Field(default_factory=dict)


class DownloadForm(BaseModel):
    layout: str = "comfy"
    mirror: bool = False


def _form_error(err: forms.FormError) -> HTTPException:
    return HTTPException(422, str(err))


def _run_dir(knobs: dict) -> Path:
    out = Path(knobs["OUTPUT_DIR"]) / (knobs["RUN_NAME"] or "run")
    return (out if out.is_absolute() else ROOT / out).resolve()


def _allowed(path: Path) -> bool:
    path = path.resolve()
    return any(root == path or root in path.parents for root in ALLOWED)


def _weights_ready(layout: dict) -> bool:
    dest = ROOT / layout["dest"]
    files = layout.get("files")
    if files:
        return all((dest / f).is_file() for f in files)
    return (dest / "transformer").is_dir()


def _version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _gpus() -> list[dict]:
    """nvidia-smi rows; empty without an NVIDIA driver."""
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        out = subprocess.run(
            ["nvidia-smi", f"--query-gpu={GPU_QUERY}", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=flags,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    rows = []
    for line in out.stdout.strip().splitlines() if out.returncode == 0 else []:
        name, total, used, driver, cap = (s.strip() for s in line.split(","))
        rows.append(
            {
                "name": name,
                "memory_total_mb": int(float(total)),
                "memory_used_mb": int(float(used)),
                "driver": driver,
                "compute_cap": cap,
            }
        )
    return rows


# ---- diagnostics / catalogue ----


@app.get("/api/v1/environment")
def environment():
    return {
        "gpus": _gpus(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "packages": {name: _version(name) for name in PACKAGES},
        "weights": {
            name: {**layout, "ready": _weights_ready(layout)}
            for name, layout in WEIGHT_SETS.items()
        },
    }


@app.get("/api/v1/capabilities")
def capabilities():
    groups = presets.catalogue(ROOT)
    return {
        "layers": {g: groups["moss"][g] for g in forms.TRAIN_LAYERS},
        "sample_precision": groups["sample"]["precision"],
        "profiles": [*PROFILE_ORDER, "auto"],
        "config_dir": forms.WEBUI_DIR,
    }


@app.post("/api/v1/compose")
def compose_layers(form: TrainForm):
    try:
        *_, knobs = forms.train_base(ROOT, form.layers)
    except forms.FormError as err:
        raise _form_error(err)
    return {"knobs": forms.json_safe(knobs)}


@app.post("/api/v1/config/preview")
def preview(form: TrainForm):
    try:
        st, knobs = forms.train_starter(ROOT, form.model_dump())
    except forms.FormError as err:
        raise _form_error(err)
    path = forms.config_path(ROOT, st.own["RUN_NAME"])
    text = forms.render(st, path, [], ROOT)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "text": text,
        "problems": forms.check(TRAIN, knobs),
    }


# ---- config files (the whole form as flat JSON) ----


@app.get("/api/v1/configs")
def list_configs(folder: str = forms.WEBUI_DIR):
    return {"dir": folder, "files": forms.list_configs(ROOT, folder)}


@app.get("/api/v1/configs/file")
def read_config(path: str):
    try:
        data = forms.read_config(ROOT, path)
    except forms.FormError as err:
        raise _form_error(err)
    except OSError as err:
        raise HTTPException(404, f"{path}: {err.strerror or err}")
    except ValueError as err:
        raise HTTPException(422, f"{path}: invalid JSON ({err})")
    return {"path": path, "data": data}


@app.put("/api/v1/configs/file")
def write_config(path: str, data: dict = Body(...)):
    try:
        target = forms.write_config(ROOT, path, data)
    except forms.FormError as err:
        raise _form_error(err)
    except OSError as err:
        raise HTTPException(422, f"{path}: {err}")
    return {"path": forms.shown(target, ROOT)}


# ---- jobs ----


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def _submit(kind: str, note: str, args: list[str], **extra) -> dict:
    job = manager.submit(Job(kind, note, args, ROOT, **extra))
    return job.summary()


def _write_train(form: TrainForm) -> tuple[Path, dict]:
    """Train config of `form` written to configs/user/webui/; 422 on problems."""
    try:
        st, knobs = forms.train_starter(ROOT, form.model_dump())
    except forms.FormError as err:
        raise _form_error(err)
    found = forms.check(TRAIN, knobs)
    if found:
        raise HTTPException(422, "; ".join(found))
    path = forms.write(ROOT, st, forms.config_path(ROOT, knobs["RUN_NAME"]))
    return path, knobs


@app.post("/api/v1/jobs/train")
async def train_job(req: TrainJob):
    if not req.train and not req.prepare:
        raise HTTPException(422, "nothing to run")
    path, knobs = _write_train(req)
    name, run_dir = knobs["RUN_NAME"], _run_dir(knobs)
    ALLOWED.add(run_dir)
    group = _unique(name)
    jobs = []
    if req.prepare:
        data = forms.write_data(ROOT, path, knobs, "cuda")
        for step in (s for s in DATA_STEPS if s in req.prepare):
            args = KOGINE + forms.command(DATA_STEPS[step], data, ROOT)
            jobs.append(
                _submit(f"data:{step}", name, args, group=group, config=str(data))
            )
    if req.train:
        args = KOGINE + forms.command(TRAIN, path, ROOT)
        extra = {"group": group, "config": str(path), "run_dir": str(run_dir)}
        note = f"{name} - {knobs['ALGO']} - {knobs['STEPS']} steps"
        jobs.append(_submit("train", note, args, **extra))
    saved = ""
    if req.snapshot:
        snapshot = forms.write_config(
            ROOT, f"{forms.WEBUI_DIR}/{name}.json", req.snapshot
        )
        saved = forms.shown(snapshot, ROOT)
    return {"jobs": jobs, "config": path.relative_to(ROOT).as_posix(), "saved": saved}


@app.post("/api/v1/jobs/sample")
async def sample_job(req: ScriptForm):
    try:
        st, knobs = forms.sample_starter(ROOT, req.model_dump())
    except forms.FormError as err:
        raise _form_error(err)
    found = forms.check(SAMPLE, knobs)
    if found:
        raise HTTPException(422, "; ".join(found))
    path = forms.write(ROOT, st, forms.config_path(ROOT, _unique("sample")))
    out = Path(knobs["OUT"])
    run_dir = (out if out.is_absolute() else ROOT / out).resolve()
    ALLOWED.add(run_dir)
    args = KOGINE + forms.command(SAMPLE, path, ROOT)
    return _submit("sample", knobs["OUT"], args, run_dir=str(run_dir), config=str(path))


@app.post("/api/v1/jobs/export")
async def export_job(req: ScriptForm):
    try:
        st, knobs = forms.export_starter(ROOT, req.model_dump())
    except forms.FormError as err:
        raise _form_error(err)
    if not knobs["ADAPTER"] or not knobs["OUT"]:
        raise HTTPException(422, "ADAPTER and OUT are required")
    path = forms.write(ROOT, st, forms.config_path(ROOT, _unique("export")))
    args = KOGINE + forms.command(forms.EXPORT, path, ROOT)
    return _submit(
        "export", f"{knobs['FORMAT']} -> {knobs['OUT']}", args, config=str(path)
    )


@app.post("/api/v1/jobs/doctor")
async def doctor_job():
    return _submit(
        "doctor", "kohakumoss-doctor", [sys.executable, "-m", "kohakumoss.cli.doctor"]
    )


@app.post("/api/v1/jobs/download")
async def download_job(req: DownloadForm):
    hf = shutil.which("hf", path=str(Path(sys.executable).parent)) or shutil.which("hf")
    if hf is None:
        raise HTTPException(422, "the hf command (huggingface_hub) is not installed")
    layout = WEIGHT_SETS.get(req.layout)
    if layout is None:
        raise HTTPException(422, f"unknown weights layout {req.layout!r}")
    repo, dest = layout["repo"], layout["dest"]
    args = [hf, "download", repo, *layout.get("files", []), "--local-dir", dest]
    env = {"HF_ENDPOINT": MIRROR} if req.mirror else {}
    return _submit("download", f"{repo} -> {dest}", args, env=env)


@app.get("/api/v1/jobs")
async def list_jobs():
    ordered = sorted(manager.jobs.values(), key=lambda j: j.created_at, reverse=True)
    return {"jobs": [j.summary() for j in ordered]}


def _job(job_id: str) -> Job:
    job = manager.jobs.get(job_id)
    if job is None:
        raise HTTPException(404, f"unknown job {job_id!r}")
    return job


@app.post("/api/v1/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    job = _job(job_id)
    manager.cancel(job)
    return job.summary()


@app.get("/api/v1/jobs/{job_id}/events")
async def job_events(job_id: str):
    return StreamingResponse(
        manager.sse_stream(_job(job_id)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---- artifacts ----


def _entry(path: Path) -> dict:
    stat = path.stat()
    size = stat.st_size if path.is_file() else 0
    return {
        "path": path.as_posix(),
        "name": path.name,
        "size": size,
        "mtime": stat.st_mtime,
    }


def _newest(paths, limit: int) -> list[dict]:
    found = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
    return [_entry(p) for p in found[:limit]]


@app.get("/api/v1/artifacts")
def artifacts(run: str):
    path = Path(run)
    path = (path if path.is_absolute() else ROOT / path).resolve()
    if not _allowed(path):
        raise HTTPException(403, "not a run directory of this server")
    if not path.is_dir():
        return {"run": path.as_posix(), "images": [], "exports": [], "checkpoints": []}
    images = (p for p in path.rglob("*") if p.suffix.lower() in IMAGES)
    exports = (p for p in (path / "export").glob("*") if p.is_file())
    ckpts = (p for p in (path / "checkpoints").glob("step_*") if p.is_dir())
    return {
        "run": path.as_posix(),
        "images": _newest(images, 48),
        "exports": _newest(exports, 64),
        "checkpoints": _newest(ckpts, 64),
    }


@app.get("/api/v1/file")
def file(path: str):
    target = Path(path).resolve()
    if target.suffix.lower() not in IMAGES or not _allowed(target):
        raise HTTPException(403, "only run images are served")
    if not target.is_file():
        raise HTTPException(404, "no such file")
    return FileResponse(target)


DIST = ROOT / "webui" / "dist"
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="frontend")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="kohakumoss-webui")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(ROOT)
    url = f"http://{args.host}:{args.port}"
    if not DIST.is_dir():
        print("webui/dist not found: build it (cd webui; npm install; npm run build)")
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, [url]).start()
    print(f"KohakuMoss web UI on {url}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
