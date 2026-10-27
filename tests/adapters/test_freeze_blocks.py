"""FREEZE_BLOCKS: the frozen-block patterns cover exactly layers.0 .. layers.N-1, and the
knob check rejects counts outside [0, depth)."""

import re

import pytest

from kohakumoss.adapters.build.config import config_from_knobs
from kohakumoss.adapters.build.presets import frozen_blocks
from kohakumoss.training.knobs import freeze_problems
from kohakumoss.types.arch import PRESETS
from tests._util.negative import must_fail

pytestmark = pytest.mark.cpu
DEPTH = PRESETS["base"].depth
PATHS = [f"layers.{i}.proj.{leaf}" for i in range(DEPTH) for leaf in ("q", "ffn_down")]


def _frozen(patterns: list[str], count: int) -> None:
    compiled = [re.compile(p) for p in patterns]
    for path in PATHS + [f"{p}.weight" for p in PATHS]:
        block = int(path.split(".")[1])
        hit = any(c.match(path) for c in compiled)
        assert hit == (block < count), (path, hit)
    assert not any(c.match("text_embedder.blocks.0.qkv") for c in compiled)


@pytest.mark.parametrize("count", [0, 1, 2, 11, 20, DEPTH - 1])
def test_frozen_blocks_cover_the_first_n(count):
    _frozen(frozen_blocks(count), count)


def test_a_pattern_without_the_block_dot_is_caught():
    broken = [r"layers\.(0|1)"]
    must_fail(lambda: _frozen(broken, 2), "layers.1 also matching layers.12")


def test_the_knob_reaches_the_adapter_config():
    assert config_from_knobs({"FREEZE_BLOCKS": 20}).freeze_blocks == 20
    assert config_from_knobs({}).freeze_blocks == 0


def _problems(n, **extra) -> list[str]:
    return freeze_problems({"VARIANT": "base", "FREEZE_BLOCKS": n, **extra})


def test_freeze_problems():
    assert _problems(0) == [] and _problems(20) == [] and _problems(DEPTH - 1) == []
    for bad in (-1, DEPTH, 1.5, True, "20"):
        assert _problems(bad), bad
    assert _problems(10, ARCH_OVERRIDES={"depth": 8})
    must_fail(lambda: _frozen(frozen_blocks(DEPTH - 1), DEPTH), "a short pattern")
