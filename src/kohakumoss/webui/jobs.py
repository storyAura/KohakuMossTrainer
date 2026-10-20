"""Web UI job manager: one subprocess at a time, its output streamed as log / progress /
status events (server-sent events), cancel by a graceful break then a forced kill.

States: queued -> running -> succeeded | failed | cancelled; running -> cancelling.
"""

import asyncio
import itertools
import json
import os
import re
import signal
import subprocess
import threading
import time
import uuid
from pathlib import Path

MAX_EVENTS = 4000
STDERR_TAIL = 8
GRACEFUL_TIMEOUT_S = 10
TERMINAL = ("succeeded", "failed", "cancelled")
SGR = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
RE_TOTAL = re.compile(r"training from step (\d+) to (\d+)")
RE_STEP = re.compile(r"\bstep (\d+)\b.*?\bloss=([-+\w.]+)")
RE_LR = re.compile(r"\blr=([-+\w.]+)")
RE_BAR = re.compile(r"(\d+)/(\d+) \[")
ERROR_WORDS = ("[error]", "error:", "traceback", "exception")


def _clock(sec: float) -> str:
    sec = max(0, round(sec))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


class Job:
    """One subprocess job: argv, cwd, extra env, events and parsed progress."""

    def __init__(self, kind: str, note: str, argv: list[str], cwd: Path, **extra):
        self.id = "job_" + uuid.uuid4().hex[:6]
        self.kind = kind
        self.note = note
        self.argv = argv
        self.cwd = cwd
        self.env = extra.get("env") or {}
        self.run_dir = extra.get("run_dir") or ""
        self.config = extra.get("config") or ""
        self.group = extra.get("group") or ""
        self.status = "queued"
        self.created_at = time.time()
        self.started_hhmm = ""
        self.started_mono: float | None = None
        self.finished_mono: float | None = None
        self.exit_code: int | None = None
        self.pid: int | None = None
        self.cancel_requested = False
        self.seq = itertools.count(1)
        self.events: list[dict] = []
        self.subscribers: list[asyncio.Queue] = []
        self.progress = {"step": 0, "total": 0, "loss": None, "lr": None}
        self.stderr_tail: list[str] = []

    def summary(self) -> dict:
        """The job as the API returns it."""
        dur = ""
        if self.started_mono is not None:
            end = self.finished_mono or time.monotonic()
            dur = _clock(end - self.started_mono)
        return {
            "job_id": self.id,
            "kind": self.kind,
            "note": self.note,
            "status": self.status,
            "progress": self.progress,
            "started": self.started_hhmm or "-",
            "duration": dur or "-",
            "exit_code": self.exit_code,
            "stderr_tail": self.stderr_tail,
            "argv": self.argv[1:],
            "run_dir": self.run_dir,
            "config": self.config,
        }


def parse_progress(progress: dict, line: str, bars: bool = True) -> bool:
    """Update `progress` from one log line; True when it changed. `bars` False
    ignores tqdm bars (a training run's are the sampler's and the decoder's)."""
    if found := RE_TOTAL.search(line):
        progress["total"] = int(found.group(2))
        return True
    if found := RE_STEP.search(line):
        progress["step"] = int(found.group(1))
        progress["loss"] = _number(found.group(2))
        if lr := RE_LR.search(line):
            progress["lr"] = _number(lr.group(1))
        return True
    if bars and (found := RE_BAR.search(line)):
        progress["step"], progress["total"] = int(found[1]), int(found[2])
        return True
    return False


def line_kind(line: str) -> str:
    """Terminal colour class of a log line: err | warn | ink."""
    low = line.lower()
    if any(w in low for w in ERROR_WORDS):
        return "err"
    return "warn" if "warning" in low else "ink"


class JobManager:
    """Serial job queue bound to the server's event loop."""

    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.pending: list[str] = []
        self.loop: asyncio.AbstractEventLoop | None = None
        self.busy = False

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def _publish(self, job: Job, ev: dict) -> None:
        ev = {"seq": next(job.seq), "job_id": job.id, **ev}
        job.events.append(ev)
        if len(job.events) > MAX_EVENTS:
            del job.events[: len(job.events) - MAX_EVENTS]
        for q in list(job.subscribers):
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                pass

    def _publish_threadsafe(self, job: Job, ev: dict) -> None:
        if self.loop:
            self.loop.call_soon_threadsafe(self._publish, job, ev)

    def _set_status(self, job: Job, status: str, **extra) -> None:
        job.status = status
        self._publish(job, {"type": "status", "status": status, **extra})

    def submit(self, job: Job) -> Job:
        """Queue `job` (call on the event loop thread)."""
        self.jobs[job.id] = job
        self.pending.append(job.id)
        self._publish(job, {"type": "status", "status": "queued"})
        if self.loop and not self.busy:
            self.busy = True
            self.loop.create_task(self._worker())
        return job

    async def _worker(self) -> None:
        try:
            while self.pending:
                job = self.jobs[self.pending.pop(0)]
                if job.status == "queued":
                    await self._run(job)
        finally:
            self.busy = False

    def _spawn(self, job: Job) -> subprocess.Popen:
        env = {**os.environ, "NO_COLOR": "1", "PYTHONIOENCODING": "utf-8", **job.env}
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        return subprocess.Popen(
            job.argv,
            cwd=str(job.cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags,
        )

    async def _run(self, job: Job) -> None:
        job.started_hhmm = time.strftime("%H:%M")
        job.started_mono = time.monotonic()
        self._set_status(job, "running")
        try:
            proc = self._spawn(job)
        except OSError as err:
            job.exit_code, job.stderr_tail = -1, [str(err)]
            job.finished_mono = time.monotonic()
            self._set_status(job, "failed", exit_code=-1, stderr_tail=job.stderr_tail)
            return
        job.pid = proc.pid
        self._publish(
            job, {"type": "log", "kind": "dim", "text": f"[job] pid {proc.pid}"}
        )
        reader = threading.Thread(target=self._read, args=(job, proc), daemon=True)
        reader.start()
        code = await asyncio.get_running_loop().run_in_executor(None, proc.wait)
        await asyncio.get_running_loop().run_in_executor(None, reader.join, 5)
        job.exit_code = code
        job.finished_mono = time.monotonic()
        if job.cancel_requested:
            self._set_status(job, "cancelled", exit_code=code)
        elif code == 0:
            self._set_status(job, "succeeded", exit_code=0)
        else:
            self._set_status(job, "failed", exit_code=code, stderr_tail=job.stderr_tail)
        if code != 0:
            self._drop_group(job)

    def _drop_group(self, job: Job) -> None:
        """Cancel the queued jobs of a stopped job's group (data prep -> train)."""
        for jid in list(self.pending):
            if job.group and self.jobs[jid].group == job.group:
                self.cancel(self.jobs[jid])

    def _read(self, job: Job, proc: subprocess.Popen) -> None:
        """Split the output on \\n and \\r (tqdm redraws with \\r)."""
        buf = []
        while ch := proc.stdout.read(1):
            if ch not in "\r\n":
                buf.append(ch)
                continue
            line = SGR.sub("", "".join(buf)).strip()
            buf = []
            if line:
                self._line(job, line)
        if buf:
            self._line(job, SGR.sub("", "".join(buf)).strip())

    def _line(self, job: Job, line: str) -> None:
        kind = line_kind(line)
        if kind == "err":
            job.stderr_tail = (job.stderr_tail + [line])[-STDERR_TAIL:]
        if parse_progress(job.progress, line, bars=job.kind != "train"):
            self._publish_threadsafe(job, {"type": "progress", **job.progress})
        # a tqdm redraw is progress, not a log line
        if kind != "err" and RE_BAR.search(line) and not RE_STEP.search(line):
            return
        self._publish_threadsafe(job, {"type": "log", "kind": kind, "text": line})

    def cancel(self, job: Job) -> None:
        """Drop a queued job; break a running one, killed after GRACEFUL_TIMEOUT_S."""
        if job.status == "queued":
            if job.id in self.pending:
                self.pending.remove(job.id)
            self._set_status(job, "cancelled")
            return
        if job.status != "running" or job.pid is None:
            return
        job.cancel_requested = True
        self._set_status(job, "cancelling")
        try:
            sig = signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGTERM
            os.kill(job.pid, sig)
        except OSError:
            pass
        if self.loop:
            self.loop.create_task(self._force_kill_later(job, job.pid))

    async def _force_kill_later(self, job: Job, pid: int) -> None:
        await asyncio.sleep(GRACEFUL_TIMEOUT_S)
        if job.status != "cancelling":
            return
        self._publish(job, {"type": "log", "kind": "warn", "text": "[job] force kill"})
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

    async def sse_stream(self, job: Job):
        """Replay the job's events, then follow it until a terminal status."""
        q: asyncio.Queue = asyncio.Queue(maxsize=4096)
        job.subscribers.append(q)
        try:
            for ev in list(job.events):
                yield _sse(ev)
            if job.status in TERMINAL:
                return
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield _sse(ev)
                if ev.get("type") == "status" and ev.get("status") in TERMINAL:
                    break
        finally:
            if q in job.subscribers:
                job.subscribers.remove(q)


def _sse(ev: dict) -> str:
    return f"id: {ev['seq']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"


manager = JobManager()
