from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from twobrain_rec_server.normalization.media import MAX_OUTPUT_BYTES
from twobrain_rec_server.normalization.service import FFmpegNormalizationPipeline

WORK_BUDGET_BYTES = 6 * 1024 * 1024 * 1024
MEMORY_LIMIT_BYTES = 1024 * 1024 * 1024
ACTIVITY_TIMEOUT_SECONDS = 6 * 60 * 60
EXPECTED_MIN_DURATION_MS = 13_500_000
EXPECTED_MAX_DURATION_MS = 14_400_000


def _read_text(*paths: str) -> str:
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    raise RuntimeError("required cgroup evidence is unavailable")


def _read_int(*paths: str) -> int:
    value = _read_text(*paths)
    if value == "max":
        raise RuntimeError("required cgroup limit is unbounded")
    return int(value)


def _cpu_limit_millicores() -> int:
    cpu_max = Path("/sys/fs/cgroup/cpu.max")
    if cpu_max.is_file():
        quota_raw, period_raw = cpu_max.read_text(encoding="utf-8").split()
        if quota_raw == "max":
            raise RuntimeError("CPU limit is unbounded")
        return round(int(quota_raw) * 1000 / int(period_raw))
    quota = _read_int("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period = _read_int("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    return round(quota * 1000 / period)


def _memory_event_count(event_name: str) -> int:
    events_path = Path("/sys/fs/cgroup/memory.events")
    if not events_path.is_file():
        return 0
    events = dict(
        line.split(maxsplit=1) for line in events_path.read_text(encoding="utf-8").splitlines()
    )
    return int(events.get(event_name, "0"))


def _directory_bytes(directory: Path) -> int:
    total = 0
    for root, directory_names, file_names in os.walk(directory, followlinks=False):
        root_path = Path(root)
        for directory_name in directory_names:
            child = root_path / directory_name
            if child.is_symlink():
                raise RuntimeError("benchmark work volume contains a symlink")
        for file_name in file_names:
            child = root_path / file_name
            if child.is_symlink() or not child.is_file():
                raise RuntimeError("benchmark work volume contains a non-regular file")
            total += child.stat().st_size
    return total


async def _monitor_work_bytes(directory: Path, stop: asyncio.Event) -> int:
    peak = _directory_bytes(directory)
    while not stop.is_set():
        await asyncio.sleep(0.1)
        peak = max(peak, _directory_bytes(directory))
    return max(peak, _directory_bytes(directory))


def _duration_bucket(duration_ms: int) -> str:
    if 13_500_000 <= duration_ms <= EXPECTED_MAX_DURATION_MS:
        return "3h45m_to_4h"
    return "outside_near_limit_bucket"


def _elapsed_bucket(elapsed_seconds: float) -> str:
    if elapsed_seconds < 600:
        return "under_10m"
    if elapsed_seconds < 1_800:
        return "10m_to_30m"
    if elapsed_seconds < 3_600:
        return "30m_to_1h"
    if elapsed_seconds < ACTIVITY_TIMEOUT_SECONDS:
        return "1h_to_6h"
    return "at_or_over_6h"


def _bytes_bucket(value: int, boundaries_mib: tuple[int, ...]) -> str:
    lower = 0
    for upper in boundaries_mib:
        upper_bytes = upper * 1024 * 1024
        if value <= upper_bytes:
            return f"{lower}MiB_to_{upper}MiB"
        lower = upper
    return f"over_{boundaries_mib[-1]}MiB"


async def main() -> None:
    work_directory = Path("/var/lib/twobrain-rec/playback-normalization")
    microphone_path = work_directory / "source-a.wav"
    system_path = work_directory / "source-b.wav"
    output_path = work_directory / "output.m4a"

    if os.geteuid() == 0:
        raise RuntimeError("benchmark must run as the non-root media worker")
    if not microphone_path.is_file() or not system_path.is_file() or output_path.exists():
        raise RuntimeError("benchmark source fixture state is invalid")

    configured_budget = int(os.environ["TWOBRAIN_PLAYBACK_NORMALIZATION_WORK_BUDGET_BYTES"])
    configured_timeout = int(os.environ["TWOBRAIN_PLAYBACK_NORMALIZATION_ACTIVITY_TIMEOUT_SECONDS"])
    source_bytes = microphone_path.stat().st_size + system_path.stat().st_size
    required_bytes = source_bytes + MAX_OUTPUT_BYTES + 256 * 1024 * 1024
    free_bytes = os.statvfs(work_directory).f_bavail * os.statvfs(work_directory).f_frsize

    if configured_budget != WORK_BUDGET_BYTES or configured_timeout != ACTIVITY_TIMEOUT_SECONDS:
        raise RuntimeError("benchmark configuration differs from the production contract")
    if required_bytes > configured_budget or free_bytes < required_bytes:
        raise RuntimeError("near-limit fixture does not fit the bounded work-volume contract")

    cpu_limit_millicores = _cpu_limit_millicores()
    memory_limit_bytes = _read_int(
        "/sys/fs/cgroup/memory.max",
        "/sys/fs/cgroup/memory/memory.limit_in_bytes",
    )
    pids_limit = _read_int(
        "/sys/fs/cgroup/pids.max",
        "/sys/fs/cgroup/pids/pids.max",
    )
    if cpu_limit_millicores != 1000:
        raise RuntimeError("benchmark CPU limit is not exactly one core")
    if memory_limit_bytes != MEMORY_LIMIT_BYTES:
        raise RuntimeError("benchmark memory limit is not exactly one GiB")
    if pids_limit != 128:
        raise RuntimeError("benchmark PID limit is not exactly 128")

    pipeline = FFmpegNormalizationPipeline(
        ffmpeg_path="/usr/bin/ffmpeg",
        ffprobe_path="/usr/bin/ffprobe",
        probe_timeout_seconds=60,
        process_timeout_seconds=ACTIVITY_TIMEOUT_SECONDS,
    )
    stop_monitor = asyncio.Event()
    monitor_task = asyncio.create_task(_monitor_work_bytes(work_directory, stop_monitor))
    started = time.monotonic()
    try:
        result = await pipeline.derive_dual_source(
            microphone_path,
            system_path,
            output_path,
        )
    finally:
        elapsed_seconds = time.monotonic() - started
        stop_monitor.set()
        work_peak_bytes = await monitor_task

    memory_peak_bytes = _read_int(
        "/sys/fs/cgroup/memory.peak",
        "/sys/fs/cgroup/memory/memory.max_usage_in_bytes",
    )
    oom_count = _memory_event_count("oom") + _memory_event_count("oom_kill")

    if result.derivation_kind != "dual_source_mix_transcode":
        raise RuntimeError("production dual-source path was not exercised")
    if not EXPECTED_MIN_DURATION_MS <= result.output_duration_ms <= EXPECTED_MAX_DURATION_MS:
        raise RuntimeError("normalized duration is outside the near-limit bucket")
    if elapsed_seconds >= ACTIVITY_TIMEOUT_SECONDS:
        raise RuntimeError("normalization exceeded the six-hour activity gate")
    if not 0 < result.output_byte_length <= MAX_OUTPUT_BYTES:
        raise RuntimeError("normalized output exceeds its bounded size contract")
    if work_peak_bytes > configured_budget:
        raise RuntimeError("normalization exceeded the six-GiB work budget")
    if memory_peak_bytes > memory_limit_bytes or oom_count:
        raise RuntimeError("normalization exceeded its memory contract")
    if not (
        result.output_sample_rate_hz == 48_000
        and result.output_channel_count == 1
        and result.moov_before_mdat
        and not result.fragmented
        and result.full_decode_passed
    ):
        raise RuntimeError("normalized output failed the canonical profile")

    print("playback_normalization_performance_result=pass")
    print(f"duration_bucket={_duration_bucket(result.output_duration_ms)}")
    print(f"elapsed_bucket={_elapsed_bucket(elapsed_seconds)}")
    print(f"elapsed_seconds={elapsed_seconds:.3f}")
    print(f"source_package_bucket={_bytes_bucket(source_bytes, (4096, 4608, 5120))}")
    print(f"required_capacity_bucket={_bytes_bucket(required_bytes, (5120, 5632, 6144))}")
    print(f"work_peak_bucket={_bytes_bucket(work_peak_bytes, (4608, 5120, 5632, 6144))}")
    print(f"memory_peak_bucket={_bytes_bucket(memory_peak_bytes, (128, 256, 512, 768, 1024))}")
    print(f"output_bucket={_bytes_bucket(result.output_byte_length, (64, 96, 128))}")
    print(f"cpu_limit_millicores={cpu_limit_millicores}")
    print(f"memory_limit_bytes={memory_limit_bytes}")
    print(f"pids_limit={pids_limit}")
    print(f"work_budget_bytes={configured_budget}")
    print(f"activity_timeout_seconds={configured_timeout}")
    print(f"oom_event_count={oom_count}")
    print("canonical_profile=pass")
    print("full_decode=pass")


if __name__ == "__main__":
    asyncio.run(main())
