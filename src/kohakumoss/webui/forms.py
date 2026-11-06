"""Web UI forms -> kogine configs: preset layers plus the form's knob values, each coerced
to the type of the composed knob it replaces, rendered by the starter writer."""

import copy
import json
import re
from pathlib import Path

from kohakumoss.cli.config import presets
from kohakumoss.cli.config.starter import (
    Starter,
    TrainChoice,
    data_starter,
    merged,
    posix,
    render,
)
from kohakumoss.cli.config.validate import (
    BASES,
    SAMPLE,
    TRAIN,
    compose,
    load_knobs,
    problems,
)
from kohakumoss.weights.layout import TEXT, VAE, component_path

WEBUI_DIR = "configs/user/webui"
TRAIN_LAYERS = ("algo", "data", "vram", "precision")
EXPORT = "scripts/export/export.py"
LOW_RAM = {"BASE_PRECISION": "int8", "SAMPLE_EVERY": 0}
NAME_RE = re.compile(r"[\w.-]{1,64}")
TRUE = ("1", "true", "yes", "on")


class FormError(ValueError):
    """A form value that cannot become its knob."""


def safe_name(name: str) -> str:
    """`name` when it is a plain file stem (letters, digits, `_ . -`), else FormError."""
    if not NAME_RE.fullmatch(name or "") or name.startswith("."):
        raise FormError(f"invalid name {name!r}: use letters, digits, _ . -")
    return name


def integer(text: str) -> int:
    """An int from `text`, scientific notation included ("1e4"); ValueError when the
    value is not a whole number."""
    try:
        return int(text)
    except ValueError:
        number = float(text)
    if not number.is_integer():
        raise ValueError(f"{text} is not a whole number")
    return int(number)


def coerce(value, old):
    """Form `value` as the type of the composed knob value `old`."""
    match old:
        case bool():
            return value if isinstance(value, bool) else str(value).lower() in TRUE
        case int():
            return integer(str(value).strip())
        case float():
            return float(str(value).strip())
        case str():
            return str(value)
        case list() | tuple():
            items = value if isinstance(value, list) else str(value).split(",")
            items = [i.strip() if isinstance(i, str) else i for i in items]
            items = [coerce(i, old[0]) if old else i for i in items if i != ""]
            return tuple(items) if isinstance(old, tuple) else items
        case dict():
            return value if isinstance(value, dict) else json.loads(value or "{}")
        case None:
            text = str(value).strip()
            if not text:
                return None
            try:
                return json.loads(text)
            except ValueError:
                return text
    return value


def dotted(knobs: dict, key: str):
    """Value of `KNOB` or `KNOB.field` (one dict level) in `knobs`; None when absent."""
    top, _, field = key.partition(".")
    value = knobs.get(top)
    return value.get(field) if field and isinstance(value, dict) else value


def own_knobs(base: dict, values: dict, own: dict | None = None) -> dict:
    """`own` plus every form value that differs from the composed `base`; FormError
    names the first unknown knob or uncoercible value."""
    own = dict(own or {})
    for key, value in values.items():
        top, _, field = key.partition(".")
        if top not in base:
            raise FormError(f"unknown knob {top}")
        old = dotted(base, key)
        # a blank form field the composed table does not carry stays out of it
        if field and old is None and (value is None or value is False or value == ""):
            continue
        try:
            new = coerce(value, old)
        except (TypeError, ValueError) as err:
            kind = type(old).__name__
            raise FormError(f"{key}: {value!r} is not a valid {kind}") from err
        if new == old:
            continue
        if field:
            table = copy.deepcopy(own.get(top, base[top]) or {})
            table[field] = new
            own[top] = table
        else:
            own[top] = new
    return own


def json_safe(knobs: dict) -> dict:
    """`knobs` as plain JSON (tuples as lists, other objects as text)."""
    return json.loads(json.dumps(knobs, default=str))


def train_layers(root: Path, picks: dict) -> list[Path]:
    """The train base, then one layer per TRAIN_LAYERS group as picked."""
    try:
        chosen = [presets.layer(root, "moss", g, picks[g]) for g in TRAIN_LAYERS]
    except (KeyError, SystemExit) as err:
        raise FormError(f"layer choice: {err}") from err
    return [root / BASES[TRAIN], *chosen]


def train_base(root: Path, picks: dict) -> tuple[list[Path], dict, dict]:
    """(layers, merged dict knobs, composed knobs) of a layer choice."""
    layers = train_layers(root, picks)
    joined = merged(layers)
    return layers, joined, compose(root, TRAIN, layers, joined)


def dataset_entries(root: Path, picks: dict, rows: list[dict]) -> list[dict]:
    """DATASETS entries: the data layer's template with each row's path and weight."""
    template = load_knobs(presets.layer(root, "moss", "data", picks["data"]))
    entries = []
    for row in rows:
        path = str(row.get("path") or "").strip()
        if not path:
            continue
        entry = {**template["DATASETS"][0], "path": posix(path)}
        weight = float(row.get("weight") or 1.0)
        if weight != 1.0:
            entry["weight"] = weight
        entries.append(entry)
    return entries


def train_starter(root: Path, form: dict) -> tuple[Starter, dict]:
    """(starter, composed knobs) of a train form {layers, knobs, datasets, low_ram}."""
    picks = form.get("layers") or {}
    layers, joined, base = train_base(root, picks)
    own = own_knobs(base, form.get("knobs") or {}, joined)
    entries = dataset_entries(root, picks, form.get("datasets") or [])
    if entries:
        own["DATASETS"] = entries
    if form.get("low_ram"):
        own.update(LOW_RAM)
    name = safe_name(own.get("RUN_NAME") or base["RUN_NAME"] or "run")
    own["RUN_NAME"] = name
    title = f"{name}: written by the web UI. Drives {TRAIN}."
    return Starter(TRAIN, title, layers, own), compose(root, TRAIN, layers, own)


def script_starter(
    root: Path, script: str, layers: list[Path], values: dict, title: str
) -> tuple[Starter, dict]:
    """(starter, composed knobs) of a one-script form over `layers`."""
    own = own_knobs(compose(root, script, layers, {}), values)
    return Starter(script, f"{title} Drives {script}.", layers, own), compose(
        root, script, layers, own
    )


def sample_starter(root: Path, form: dict) -> tuple[Starter, dict]:
    """Sample form {precision, knobs} over the sample base and precision layer."""
    try:
        prec = presets.layer(root, "sample", "precision", form.get("precision", "bf16"))
    except SystemExit as err:
        raise FormError(str(err)) from err
    layers = [root / BASES[SAMPLE], prec]
    return script_starter(root, SAMPLE, layers, form.get("knobs") or {}, "Web UI.")


def export_starter(root: Path, form: dict) -> tuple[Starter, dict]:
    """Export form {knobs} over the export script's defaults."""
    return script_starter(root, EXPORT, [], form.get("knobs") or {}, "Web UI.")


def check(script: str, knobs: dict) -> list[str]:
    """The script's knob problems for composed `knobs`."""
    return problems(script, knobs)


def config_path(root: Path, name: str) -> Path:
    """The web UI config file of run `name`."""
    return root / WEBUI_DIR / f"{safe_name(name)}.py"


def command(script: str, path: Path, root: Path) -> list[str]:
    """kogine arguments that run `script` with config `path` (cwd = `root`)."""
    return ["run", script, "--config", Path(path).relative_to(root).as_posix()]


def write(root: Path, st: Starter, path: Path) -> Path:
    """Render starter `st` to `path` (the run command in its docstring)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = "kogine " + " ".join(command(st.script, path, root))
    path.write_text(render(st, path, [cmd], root), encoding="utf-8")
    return path


def write_data(root: Path, train_path: Path, knobs: dict, device: str) -> Path:
    """The data-preparation config beside train config `train_path`."""
    choice = TrainChoice(weights=knobs["WEIGHTS"], data="", device=device)
    st = data_starter(choice, train_path)
    for kwargs, component, knob in (
        ("TEXT_ENCODER_KWARGS", TEXT, "TEXT_ENCODER"),
        ("IMAGE_ENCODER_KWARGS", VAE, "VAE"),
    ):
        # absolute, symlinks kept unresolved
        source = Path(encoder_source(knobs, component, knob)).absolute().as_posix()
        st.own[kwargs] = {**st.own[kwargs], "path": source}
    return write(root, st, train_path.with_name(f"{train_path.stem}_data.py"))


def encoder_source(knobs: dict, component: str, knob: str) -> str:
    """What a cache pass's encoder loads: the file the train knob `knob` (TEXT_ENCODER /
    VAE) names, resolved as training resolves it; WEIGHTS when the knob is unset or
    names no file."""
    if not knobs.get(knob):
        return knobs["WEIGHTS"]
    try:
        found = component_path(
            knobs["WEIGHTS"], component, knobs[knob], knobs.get("VARIANT", "base")
        )
    except FileNotFoundError:
        return knobs["WEIGHTS"]
    return str(found)


def save_form(root: Path, name: str, form: dict) -> Path:
    """The form JSON beside its config, so a preset reloads into the form."""
    path = root / WEBUI_DIR / f"{safe_name(name)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(form, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def saved_forms(root: Path) -> list[dict]:
    """[{name, updated}] of the saved forms, newest first."""
    folder = root / WEBUI_DIR
    files = sorted(folder.glob("*.json"), key=lambda p: -p.stat().st_mtime)
    return [{"name": p.stem, "updated": p.stat().st_mtime} for p in files]


def load_form(root: Path, name: str) -> dict:
    """A saved form by name."""
    path = root / WEBUI_DIR / f"{safe_name(name)}.json"
    return json.loads(path.read_text(encoding="utf-8"))
