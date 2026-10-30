import importlib.util
import os
import stat
from pathlib import Path

from dotenv import dotenv_values

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_env.py"
SPEC = importlib.util.spec_from_file_location("update_env", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_update_env_is_atomic_and_preserves_other_values(tmp_path) -> None:
    env_file = tmp_path / "oil-spill.env"
    env_file.write_text(
        "TELEGRAM_BOT_TOKEN=secret\nVIDEO_SOURCE_TYPE=rtsp\n",
        encoding="utf-8",
    )
    env_file.chmod(0o640)

    MODULE.update_env(
        env_file,
        {
            "VIDEO_SOURCE_TYPE": "file",
            "VIDEO_FILE_PATH": "/opt/oil-spill-monitor/data/tumpahan 2.mp4",
        },
    )

    values = dotenv_values(env_file)
    assert values["TELEGRAM_BOT_TOKEN"] == "secret"
    assert values["VIDEO_SOURCE_TYPE"] == "file"
    assert values["VIDEO_FILE_PATH"] == "/opt/oil-spill-monitor/data/tumpahan 2.mp4"
    if os.name == "posix":
        assert stat.S_IMODE(env_file.stat().st_mode) == 0o640
    assert not env_file.with_name(env_file.name + ".tmp").exists()
