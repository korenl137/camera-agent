from pathlib import Path

ROOT = Path(__file__).parent


def test_tracked_code_has_no_camera_device_paths():
    # device paths are per machine and belong in ~/.config/camera-agent/env
    for name in ["go2rtc.yaml", "panel.py", "server.py", "systemd/go2rtc.service"]:
        assert "/dev/" not in (ROOT / name).read_text(encoding="utf-8"), name
