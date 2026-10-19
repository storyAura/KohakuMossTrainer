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
    shown,
)
from kohakumoss.cli.config.validate import (
    BASES,
    SAMPLE,
    TRAIN,
    compose,
    load_knobs,
    problems,
)

WEBUI_DIR = "configs/user/webui"
TRAIN_LAYERS = ("algo", "data", "vram", "precision", "weights")
CONFIG_SUFFIX = ".json"
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
    return write(root, st, train_path.with_name(f"{train_path.stem}_data.py"))


def config_file(root: Path, path: str) -> Path:
    """A web UI config file: `path` (relative to `root` unless absolute) ending in
    .json; FormError otherwise."""
    target = Path(str(path or "").strip())
    if target.suffix.lower() != CONFIG_SUFFIX:
        raise FormError(f"{path!r}: a config file ends in {CONFIG_SUFFIX}")
    return target if target.is_absolute() else root / target


def list_configs(root: Path, folder: str = WEBUI_DIR) -> list[dict]:
    """[{path, name, updated}] of the .json files in `folder`, newest first."""
    base = Path(folder or WEBUI_DIR)
    base = base if base.is_absolute() else root / base
    if not base.is_dir():
        return []
    files = sorted(base.glob(f"*{CONFIG_SUFFIX}"), key=lambda p: -p.stat().st_mtime)
    return [
        {"path": shown(p, root), "name": p.stem, "updated": p.stat().st_mtime}
        for p in files
    ]


def read_config(root: Path, path: str) -> dict:
    """The JSON object of config file `path`; FormError when it is not one."""
    data = json.loads(config_file(root, path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise FormError(f"{path}: not a JSON object")
    return data


def write_config(root: Path, path: str, data: dict) -> Path:
    """Write `data` to config file `path` (sorted keys; replaced atomically)."""
    target = config_file(root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(target)
    return target
