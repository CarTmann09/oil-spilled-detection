from __future__ import annotations

import shutil
from pathlib import Path

import psutil


def read_cpu_temperature() -> float | None:
    path = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        return round(float(path.read_text(encoding="utf-8").strip()) / 1000, 1)
    except (OSError, ValueError):
        return None


def system_metrics(data_path: Path) -> dict[str, float | None]:
    disk = shutil.disk_usage(data_path)
    memory = psutil.virtual_memory()
    return {
        "cpuPercent": round(psutil.cpu_percent(interval=None), 1),
        "memoryPercent": round(memory.percent, 1),
        "diskPercent": round((disk.used / disk.total) * 100, 1),
        "diskFreeGb": round(disk.free / (1024**3), 2),
        "temperatureC": read_cpu_temperature(),
    }
