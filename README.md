# camera-agent

Streams a USB webcam with go2rtc and exposes a `camera_snapshot` MCP tool so Claude Code and Codex can look at the current scene.

```
USB webcam → go2rtc (127.0.0.1:1984, user systemd) ─┬─ tailscale serve (tailnet-only HTTP :1984) → browser viewer
                                                    └─ /api/frame.jpeg ← server.py (FastMCP, stdio) ← Claude Code / Codex
```

## Files

| File | Role |
|---|---|
| `go2rtc.yaml` | go2rtc server settings (no devices). Credentials come from the environment as `${CAM_USER}` / `${CAM_PASSWORD}` |
| `cameras.example.yaml` | Template for this machine's streams, copied to `~/.config/camera-agent/cameras.yaml` (not tracked) |
| `systemd/go2rtc.service` | User service; link it into `~/.config/systemd/user/`. Reads both `go2rtc.yaml` and the local `cameras.yaml` |
| `server.py` | One tool, `camera_snapshot(camera="cam1")`. Reads credentials directly from `~/.config/camera-agent/env` |
| `panel.py`, `static/panel.html` | Control panel (port 8765): live view of `cam1`, V4L2 sliders and presets (`default`, `sharp`, `backlight`, `night`). Same login as go2rtc; values are checked against the device's own min/max |
| `systemd/camera-panel.service` | User service for the panel; link it like `go2rtc.service` |
| `test_server.py` | `uv run pytest` |

No secret or device path is stored in this repository. Per-machine settings live in `~/.config/camera-agent/`:

- `env` (mode 600): `CAM_USER`, `CAM_PASSWORD`, and one `CAMn_DEVICE=/dev/v4l/by-id/...` line per camera. `CAM1_DEVICE` is also used by the control panel.
- `cameras.yaml`: the go2rtc streams (copy from `cameras.example.yaml`). Stream names are referenced by `camera_snapshot`.

## Setup (what was done on this machine)

1. Download the official go2rtc release (`AlexxIT/go2rtc`, v1.9.15 linux_amd64), compare its SHA256 with the release digest, and install it to `~/.local/bin/go2rtc`.
2. Create `~/.config/camera-agent/env` (the password came from `secrets.token_urlsafe(24)`), add the `CAMn_DEVICE` lines, and copy `cameras.example.yaml` to `~/.config/camera-agent/cameras.yaml` and edit it for the cameras plugged into this machine.
3. `ln -s ~/Projects/camera-agent/systemd/go2rtc.service ~/.config/systemd/user/ && systemctl --user enable --now go2rtc`
4. `tailscale serve --bg --http=1984 http://127.0.0.1:1984` (run `sudo tailscale set --operator=$USER` once first).
5. `claude mcp add --scope user laptop-camera -- uv --directory ~/Projects/camera-agent run server.py`
   `codex mcp add laptop-camera -- uv --directory ~/Projects/camera-agent run server.py`

## Adding a camera

`camera_snapshot` takes a `camera` argument that is the go2rtc stream name (letters, digits, `-`, `_`, up to 32 characters); the default is `cam1`. To add a camera: add its device to `~/.config/camera-agent/env` (`CAM3_DEVICE=/dev/v4l/by-id/...`), add a line under `streams:` in `~/.config/camera-agent/cameras.yaml` (for example `cam3: ffmpeg:device?video=${CAM3_DEVICE}&input_format=mjpeg&video_size=1280x720&framerate=30#video=mjpeg`, or `printer: rtsp://user:pass@host:8554/cam`), restart the service, and call the tool with `camera="cam3"`. The MCP registration does not change. An unknown name returns a clear error instead of a connection error. Agent sessions that were already running keep the old tool schema (no `camera` argument) until restarted. `CAM_BASE` overrides the go2rtc address (default `http://127.0.0.1:1984`); the earlier `CAM_URL` override was removed.

## Control panel

`tailscale serve --bg --http=8765 http://127.0.0.1:8765` publishes it on the tailnet; it is protected by the same Basic auth as go2rtc. Control values live on the device and reset when the camera is replugged. `cam1` outputs MJPEG (`#video=mjpeg`): the h264 output made `frame.jpeg` take ~1.7 s and the MJPEG endpoint returned nothing. The panel reads the device from `CAM1_DEVICE` and refuses to start without it. A preset skips any control the device does not have, and any value outside the device's min/max, and lists them in the response's `skipped` field; the rest of the preset still applies. `/api/set` still rejects both cases with an error. The panel uses V4L2 ioctls, so it runs only on Linux.

## Gotchas

- **Two cameras on one USB 2.0 hub can fail.** They fail with `No space left on device` (USB bandwidth); put them on separate root ports to run both.

- **`local_auth: true` is required.** go2rtc skips authentication for localhost requests by default, and `tailscale serve` proxies from loopback, so without this setting remote access has no authentication.
- **Do not disable RTSP.** The `ffmpeg:` source goes through go2rtc's internal RTSP module; it is bound to `127.0.0.1:8554` only.
- **No `cameras.yaml` means go2rtc is skipped.** The unit has `ConditionPathExists`, so it does not restart-loop. `systemctl --user status go2rtc` shows the failed condition. Create the file and start the service.
- **Restart the service after changing the password** (`systemctl --user restart go2rtc`). Running agent sessions pick up the new password in a new session.
- `mcp` is pinned below 2 because 2.x renamed FastMCP.
- The camera opens only while a viewer or a snapshot request exists. Closing the lid covers the lens.

## Privacy

A snapshot is taken only when an agent calls the tool, and it is sent to that agent's model provider (Anthropic, OpenAI). Nothing is analyzed continuously or stored. Check that the camera does not point at people.

## Not yet verified

- Whether the service and `tailscale serve` come back after a reboot without a login
- Scene analysis in interactive Codex
- The Tailscale ACL scope (visible only in the admin console)
