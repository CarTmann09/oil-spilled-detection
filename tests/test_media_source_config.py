from pathlib import Path

import yaml
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def test_mediamtx_exposes_only_loopback_inputs() -> None:
    config = yaml.safe_load((ROOT / "config" / "mediamtx.yml").read_text())
    assert config["rtsp"] is True
    assert config["rtspAddress"] == "127.0.0.1:8554"
    assert config["hls"] is True
    assert config["hlsAddress"] == "127.0.0.1:8888"
    assert config["paths"]["jetty01"]["source"] == "publisher"


def test_example_routes_ai_through_mediamtx() -> None:
    values = dotenv_values(ROOT / ".env.example")
    assert values["MEDIA_SOURCE_MODE"] == "remote"
    assert str(values["MEDIA_SOURCE_URL"]).startswith("https://")
    assert values["VIDEO_SOURCE_TYPE"] == "rtsp"
    assert values["RTSP_URL"] == "rtsp://127.0.0.1:8554/jetty01"
