#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shlex
import stat
import sys
from pathlib import Path

ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def update_env(path: Path, updates: dict[str, str]) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Environment file tidak ditemukan: {path}")
    original_stat = path.stat()
    lines = path.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in updates:
            output.append(f"{key}={shlex.quote(updates[key])}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}={shlex.quote(value)}")

    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text("\n".join(output) + "\n", encoding="utf-8")
    os.chmod(temporary, stat.S_IMODE(original_stat.st_mode))
    if os.name == "posix":
        os.chown(temporary, original_stat.st_uid, original_stat.st_gid)
    os.replace(temporary, path)


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("Penggunaan: update_env.py ENV_FILE KEY=VALUE [KEY=VALUE ...]")
    path = Path(sys.argv[1])
    updates: dict[str, str] = {}
    for item in sys.argv[2:]:
        if "=" not in item:
            raise SystemExit(f"Update tidak valid: {item}")
        key, value = item.split("=", 1)
        if not ENV_KEY_PATTERN.fullmatch(key):
            raise SystemExit(f"Nama environment tidak valid: {key}")
        updates[key] = value
    update_env(path, updates)


if __name__ == "__main__":
    main()
