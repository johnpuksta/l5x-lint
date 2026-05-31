"""Benchmark tests: verify linear scaling of parse + analyze pipeline.

Generates L5X files of increasing size and asserts that the analysis time
stays within a reasonable multiple of the measured baseline. These tests
act as regression guards — if scaling breaks, these will catch it.

Run with: pytest tests/benchmarks/ -v
Run only benchmarks: pytest tests/benchmarks/ -v -m benchmark
"""

import time
from pathlib import Path

import pytest

from l5x_lint import domain  # noqa: F401 — ensure domain is loaded before checks
from l5x_lint.infrastructure.adapter import parse_l5x
from l5x_lint.pipeline.analyze import analyze
from returns.result import Success

from .conftest import (
    BASELINE_TIMES,
    BENCHMARK_CONFIGS,
    build_l5x,
    write_l5x_to_temp,
)

# Multiplier for baseline assertions (2-3x observed time)
TIME_MULTIPLIER = 3.0


def _cleanup(path: Path):
    """Remove temp file and parent directory."""
    try:
        if path.exists():
            path.unlink()
        if path.parent.exists():
            path.parent.rmdir()
    except OSError:
        pass


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "label,target_bytes,description",
    BENCHMARK_CONFIGS,
    ids=[c[0] for c in BENCHMARK_CONFIGS],
)
def test_scaling_parse_analyze(label, target_bytes, description):
    """Parse and analyze an L5X file, asserting time within baseline * multiplier."""
    content = build_l5x(target_size_bytes=target_bytes)
    path = write_l5x_to_temp(content)
    actual_size_mb = path.stat().st_size / (1024 * 1024)

    try:
        # Parse
        t0 = time.perf_counter()
        result = parse_l5x(path)
        t1 = time.perf_counter()

        assert isinstance(result, Success), f"Parse failed: {result.failure()}"

        # Analyze
        project = result.unwrap()
        ar = analyze(project.controller)
        t2 = time.perf_counter()

        assert isinstance(ar, Success), f"Analyze failed: {ar.failure()}"

        parse_ms = (t1 - t0) * 1000
        analyze_ms = (t2 - t1) * 1000
        total_s = t2 - t0
        baseline = BASELINE_TIMES[label]
        threshold = baseline * TIME_MULTIPLIER

        result_obj = ar.unwrap()
        diag_count = len(result_obj.diagnostics)

        print(f"\n  [{label}] {actual_size_mb:.1f} MB")
        print(f"    Parse: {parse_ms:.0f} ms")
        print(f"    Analyze: {analyze_ms:.0f} ms")
        print(f"    Total: {total_s:.2f} s  (threshold: {threshold:.1f} s)")
        print(f"    Diagnostics: {diag_count}")

        assert total_s < threshold, (
            f"[{label}] Scaling regression: took {total_s:.2f}s, "
            f"expected < {threshold:.1f}s ({TIME_MULTIPLIER}x baseline {baseline:.1f}s). "
            f"File: {actual_size_mb:.1f} MB"
        )

    finally:
        _cleanup(path)


@pytest.mark.benchmark
def test_scaling_ratio_large_vs_small():
    """Verify that scaling is roughly linear: 10MB should not take >20x the 100KB time."""
    # Small file
    small_content = build_l5x(target_size_bytes=100_000)
    small_path = write_l5x_to_temp(small_content)
    try:
        t0 = time.perf_counter()
        parse_l5x(small_path)
        analyze(parse_l5x(small_path).unwrap().controller)
        small_time = time.perf_counter() - t0
    finally:
        _cleanup(small_path)

    # Large file (10MB)
    large_content = build_l5x(target_size_bytes=10_000_000)
    large_path = write_l5x_to_temp(large_content)
    try:
        t0 = time.perf_counter()
        parse_l5x(large_path)
        analyze(parse_l5x(large_path).unwrap().controller)
        large_time = time.perf_counter() - t0
    finally:
        _cleanup(large_path)

    ratio = large_time / small_time if small_time > 0 else float("inf")
    # 10MB / 100KB = 100x data. Linear scaling means ~100x time.
    # Allow up to 200x (2x overhead from constant factors).
    max_ratio = 200

    print(f"\n  Small: {small_time:.3f}s, Large: {large_time:.2f}s, Ratio: {ratio:.1f}x")

    assert ratio < max_ratio, (
        f"Non-linear scaling: 10MB took {ratio:.1f}x the 100KB time "
        f"(threshold: {max_ratio}x). Large: {large_time:.2f}s, Small: {small_time:.3f}s"
    )


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "label,target_bytes",
    [("medium", 500_000), ("large", 2_000_000)],
    ids=["medium", "large"],
)
def test_scaling_mixed_rll_st(label, target_bytes):
    """Verify scaling with mixed RLL and ST routines (not just pure RLL)."""
    # Build with more ST content than default
    content = build_l5x(
        target_size_bytes=target_bytes,
        num_rll_routines=1,
        num_st_routines=3,
        rungs_per_routine=200,
        st_stmts_per_routine=500,
    )
    path = write_l5x_to_temp(content)
    actual_size_mb = path.stat().st_size / (1024 * 1024)

    try:
        t0 = time.perf_counter()
        result = parse_l5x(path)
        assert isinstance(result, Success)
        project = result.unwrap()
        ar = analyze(project.controller)
        t1 = time.perf_counter()

        assert isinstance(ar, Success)
        total_s = t1 - t0
        baseline = BASELINE_TIMES[label]
        threshold = baseline * TIME_MULTIPLIER

        result_obj = ar.unwrap()

        print(f"\n  [{label}] {actual_size_mb:.1f} MB (mixed RLL+ST)")
        print(f"    Total: {total_s:.2f} s  (threshold: {threshold:.1f} s)")
        print(f"    Diagnostics: {len(result_obj.diagnostics)}")

        assert total_s < threshold, (
            f"[{label}] Mixed RLL+ST scaling regression: took {total_s:.2f}s, "
            f"expected < {threshold:.1f}s"
        )

    finally:
        _cleanup(path)
