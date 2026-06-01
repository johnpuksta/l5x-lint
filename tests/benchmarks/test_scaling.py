"""Benchmark tests: verify linear scaling of parse + analyze pipeline.

Loads pre-generated L5X files from tests/data/benchmarks/ and asserts that
the analysis time stays within a reasonable multiple of the measured baseline.
These tests act as regression guards — if scaling breaks, these will catch it.

The benchmark L5X files contain realistic mixed content:
- Controller tags (DINT, BOOL, REAL, STRING, SINT, LINT, arrays, UDTs)
- User-defined data types (MotorParams, AlarmStruct, PIDparams)
- AddOn Instruction definitions with parameters, local tags, RLL routines
- Multiple programs with RLL and ST routines
- RLL rungs with XIC/XIO/OTE/LES/GRT/EQU/MOV/ADD/TON/CTU/COP
- ST statements with assignments, IF/THEN, OR expressions

Generate files: python tests/data/benchmarks/generate.py
Run with: pytest tests/benchmarks/ -v
Run only benchmarks: pytest tests/benchmarks/ -v -m benchmark
Skip benchmarks: pytest -m 'not benchmark'
"""

import time
from pathlib import Path

import pytest

from l5x_lint import domain  # noqa: F401 — ensure domain is loaded before checks
from l5x_lint.infrastructure.adapter import parse_l5x
from l5x_lint.pipeline.analyze import analyze
from returns.result import Success

# Directory containing pre-generated benchmark L5X files
BENCH_DIR = Path(__file__).parent.parent / "data" / "benchmarks"

# Benchmark file configs: (filename, label, baseline_seconds)
# Baselines measured on developer machine; tests assert time < baseline * TIME_MULTIPLIER
TIME_MULTIPLIER = 3.0

BENCHMARKS = [
    ("bench_100kb.L5X", "100KB", 0.80),
    ("bench_500kb.L5X", "500KB", 0.50),
    ("bench_2mb.L5X", "2MB", 2.50),
    ("bench_10mb.L5X", "10MB", 12.0),
    ("bench_50mb.L5X", "50MB", 60.0),
]


def _analyze_file(path: Path):
    """Parse and analyze an L5X file, returning (total_seconds, diagnostics_count)."""
    t0 = time.perf_counter()
    result = parse_l5x(path)
    t1 = time.perf_counter()

    assert isinstance(result, Success), f"Parse failed: {result.failure()}"

    project = result.unwrap()
    ar = analyze(project.controller)
    t2 = time.perf_counter()

    assert isinstance(ar, Success), f"Analyze failed: {ar.failure()}"

    total_s = t2 - t0
    diag_count = len(ar.unwrap().diagnostics)
    return total_s, diag_count


def _file_info(path: Path) -> str:
    """Return a human-readable summary of a benchmark L5X file."""
    result = parse_l5x(path)
    if not isinstance(result, Success):
        return f"(parse error)"
    ctrl = result.unwrap().controller
    n_tags = len(ctrl.tags)
    n_dt = len(ctrl.data_types)
    n_aoi = len(ctrl.aois)
    n_prog = len(ctrl.programs)
    n_routines = sum(len(p.routines) for p in ctrl.programs)
    return f"tags={n_tags} dt={n_dt} aoi={n_aoi} progs={n_prog} routines={n_routines}"


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "filename,label,baseline",
    BENCHMARKS,
    ids=[b[1] for b in BENCHMARKS],
)
def test_scaling(filename, label, baseline):
    """Parse and analyze a benchmark L5X file, asserting time within threshold."""
    path = BENCH_DIR / filename
    assert path.exists(), f"Benchmark file not found: {path}"

    size_mb = path.stat().st_size / (1024 * 1024)
    total_s, diag_count = _analyze_file(path)
    threshold = baseline * TIME_MULTIPLIER

    info = _file_info(path)

    print(f"\n  [{label}] {size_mb:.1f} MB — {info}")
    print(f"    Total: {total_s:.2f} s  (threshold: {threshold:.1f} s)")
    print(f"    Diagnostics: {diag_count}")

    assert total_s < threshold, (
        f"[{label}] Scaling regression: took {total_s:.2f}s, "
        f"expected < {threshold:.1f}s ({TIME_MULTIPLIER}x baseline {baseline:.1f}s). "
        f"File: {size_mb:.1f} MB, {info}"
    )


@pytest.mark.benchmark
def test_scaling_ratio():
    """Verify roughly linear scaling: 10MB should not take >100x the 100KB time."""
    small_path = BENCH_DIR / "bench_100kb.L5X"
    large_path = BENCH_DIR / "bench_10mb.L5X"
    assert small_path.exists() and large_path.exists()

    small_s, _ = _analyze_file(small_path)
    large_s, _ = _analyze_file(large_path)

    ratio = large_s / small_s if small_s > 0 else float("inf")
    # 10MB / 100KB = 100x data. Linear scaling means ~100x time.
    # Allow up to 200x (constant overhead, IO, etc.).
    max_ratio = 200

    small_info = _file_info(small_path)
    large_info = _file_info(large_path)
    print(f"\n  Small: {small_s:.3f}s ({small_info})")
    print(f"  Large: {large_s:.2f}s ({large_info})")
    print(f"  Ratio: {ratio:.1f}x (max: {max_ratio}x)")

    assert ratio < max_ratio, (
        f"Non-linear scaling: 10MB took {ratio:.1f}x the 100KB time "
        f"(threshold: {max_ratio}x). Large: {large_s:.2f}s, Small: {small_s:.3f}s"
    )


@pytest.mark.benchmark
def test_valid_xml_structure():
    """Verify all benchmark files are valid XML with correct structure."""
    import xml.etree.ElementTree as ET

    for filename, label, _ in BENCHMARKS:
        path = BENCH_DIR / filename
        assert path.exists(), f"Benchmark file not found: {path}"

        tree = ET.parse(path)
        root = tree.getroot()
        assert root.tag == "RSLogix5000Content", (
            f"{filename}: unexpected root tag {root.tag}"
        )
        assert root.find("Controller") is not None, f"{filename}: missing Controller"

        ctrl = root.find("Controller")
        assert ctrl.find("DataTypes") is not None, f"{filename}: missing DataTypes"
        assert ctrl.find("Tags") is not None, f"{filename}: missing Tags"
        assert ctrl.find("Programs") is not None, f"{filename}: missing Programs"

        programs = ctrl.find("Programs")
        assert len(list(programs)) > 0, f"{filename}: no programs"

        for prog in programs:
            assert prog.find("Routines") is not None, (
                f"{filename}: {prog.get('Name')} missing Routines"
            )
            routines = prog.find("Routines")
            for routine in routines:
                rtype = routine.get("Type")
                assert rtype in ("RLL", "ST"), (
                    f"{filename}: {routine.get('Name')} unknown type {rtype}"
                )
                if rtype == "RLL":
                    assert routine.find("RLLContent") is not None, (
                        f"{filename}: {routine.get('Name')} missing RLLContent"
                    )
                elif rtype == "ST":
                    assert routine.find("STContent") is not None, (
                        f"{filename}: {routine.get('Name')} missing STContent"
                    )
