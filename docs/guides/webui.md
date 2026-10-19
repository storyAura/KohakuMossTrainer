# Web UI

A local browser front end over the same scripts and configs the command line uses: every
form becomes a kogine config file, every action a queued job running `kogine run ...`.

```bash
kohakumoss-webui                      # http://127.0.0.1:8787, opens the browser
kohakumoss-webui --port 9000 --no-browser
```

The `webui` extra (FastAPI + uvicorn) is part of the `cuda` / `xpu` install sets;
otherwise `uv pip install -e ".[webui]"`. The built front end (`webui/dist`) is checked
in; `cd webui && npm install && npm run build` rebuilds it after editing `webui/src`.

## Pages

| page | does | command-line equivalent |
| --- | --- | --- |
| 训练 (train) | config file bar; algo / data / VRAM / precision / weights layers, knob overrides, datasets; data preparation; train | `kohakumoss-config new train`, `scripts/data/*.py`, `scripts/train/moss.py` |
| 出图 / 导出 (tools) | sampling with adapters; exporting a checkpoint | `scripts/sample/sample.py`, `scripts/export/export.py` |
| 队列 (queue) | every job, its progress, stop | - |
| 产物 (artifacts) | images, `export/` files and `checkpoints/` of a run directory | - |
| 模型 (models) | whether the ComfyUI files (`ComfyUI/models`) or the HF folder (`models/MOSS-Image-Base`) are there; download either | `hf download ...` ([weights.md](weights.md)) |
| 环境 (environment) | GPUs, package versions, the doctor | `kohakumoss-doctor` |

## How a form becomes a run

1. The train page picks one layer per group under `configs/moss/` (`algo`, `data`,
   `vram`, `precision`, `weights`) on top of `configs/moss/_base/base_lora.py`, in that
   order. Changing a layer re-reads the composed knobs into
   the form; fields edited by hand keep their value.
2. On submit the server coerces every field to the type of the knob it replaces, keeps
   the ones that differ from the composed layers, and writes
   `configs/user/webui/<RUN_NAME>.py` (plus `<RUN_NAME>_data.py` for the data scripts
   and `<RUN_NAME>.json`, the form as a [config file](#config-files)). "查看配置" shows
   the `.py` file before anything runs.
3. The composed knobs go through the train script's own checks
   (`kohakumoss.training.knobs.validate`, the same as `kohakumoss-config check`); any
   problem, a missing path included, rejects the submit with the message.
4. Jobs run one at a time in the order submitted. "训练前自动准备数据" queues
   `inspect_data` -> `cache_text` -> `cache_latents` -> train as one group; a step that
   fails cancels the rest of its group. The caches only encode missing entries, so
   repeating the preparation is cheap.

Number fields take scientific notation (`1e-4`, and `1e4` for whole-number knobs such
as `STEPS`; a fractional value there is rejected). `TARGET_AREA` also takes `W,H`
(`1536,1536`, or `1536x1536`), sent as the product W x H; a square area shows as `W,W`.

"省内存模式" sets `BASE_PRECISION="int8"` and `SAMPLE_EVERY=0`, the start menu's low-RAM
option.

## Config files

The whole train form saves to one JSON file, after kohya_ss's "Load/Save Config file":
a flat object with one key per form entry, sorted:

```json
{
  "DIM": 32,
  "LR": "1e-4",
  "SAMPLE_PROMPTS": ["a lighthouse on a rocky coast at sunset"],
  "SCHEDULE.warmup": 100,
  "TARGET_AREA": "1024,1024",
  "algo": "lora",
  "data": "kohya",
  "datasets": [{"path": "datasets/my_style", "weight": "1"}],
  "low_ram": false,
  "precision": "bf16",
  "prepare": true,
  "version": 1,
  "vram": "8g",
  "weights": "comfy"
}
```

- Keys: the layer groups (`algo`, `data`, `vram`, `precision`, `weights`), the knob names
  the form shows (`KNOB` or `KNOB.field`), `datasets`, `low_ram`, `prepare`, `version`.
  Values are the form's: numbers as numbers, line lists as arrays, JSON fields as
  objects, anything else as typed (`"1e-4"`, `"1024,1024"`).
- Opening a file sets its layers first, then every knob the file names; a knob it does
  not name takes its value from those layers. Unknown keys are ignored and listed in
  the notice, so a file from an older or newer UI still opens.
- 打开 / 保存 read and write a path on the training machine (relative to the repository;
  default folder `configs/user/webui/`; saving to a new path is "save as"). 导出 / 导入
  download or upload the file through the browser, for a machine the browser is not on.
- Starting a run also saves `configs/user/webui/<RUN_NAME>.json`.

## Progress and logs

The server reads the job's output: the `training from step S to N` line gives the
total, each console step line (`step N [loss=... lr=...]`, every `LOG_EVERY` steps) the
progress and the loss curve, a tqdm `n/total [` bar the progress of the cache passes.
The curve's smooth line is an EMA (0.9) of the logged losses. Sample images are read
from `<OUTPUT_DIR>/<RUN_NAME>/samples/` every 20 s while training runs.

## Limits

- The job list lives in the server process; restarting it forgets the jobs (the
  configs, checkpoints and exports stay on disk).
- One GPU: the form has no device / parallel choice; multi-GPU runs (Linux) use
  `kohakumoss-config new train --gpus N` and the command line.
- Stop on Windows ends the process tree (no graceful SIGTERM there); resume with
  `RESUME = latest`.
- The server listens on 127.0.0.1 and serves only image files under the repository or a
  run directory it started.
