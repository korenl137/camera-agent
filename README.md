# camera-agent

Streams the laptop's built-in webcam with go2rtc and exposes a `camera_snapshot` MCP tool so Claude Code and Codex can look at the current scene.

```
USB webcam → go2rtc (127.0.0.1:1984, user systemd) ─┬─ tailscale serve (tailnet-only HTTP :1984) → browser viewer
                                                    └─ /api/frame.jpeg ← server.py (FastMCP, stdio) ← Claude Code / Codex
```

## Files

| File | Role |
|---|---|
| `go2rtc.yaml` | Stream definition. Credentials come from the environment as `${CAM_USER}` / `${CAM_PASSWORD}` |
| `systemd/go2rtc.service` | User service; link it into `~/.config/systemd/user/` |
| `server.py` | One tool, `camera_snapshot`. Reads credentials directly from `~/.config/camera-agent/env` |
| `test_server.py` | `uv run pytest` |

No secret is stored in this repository. Credentials live in `~/.config/camera-agent/env` (mode 600, `CAM_USER`, `CAM_PASSWORD`).

## Setup (what was done on this machine)

1. Download the official go2rtc release (`AlexxIT/go2rtc`, v1.9.15 linux_amd64), compare its SHA256 with the release digest, and install it to `~/.local/bin/go2rtc`.
2. Create `~/.config/camera-agent/env` (the password came from `secrets.token_urlsafe(24)`).
3. `ln -s ~/Projects/camera-agent/systemd/go2rtc.service ~/.config/systemd/user/ && systemctl --user enable --now go2rtc`
4. `tailscale serve --bg --http=1984 http://127.0.0.1:1984` (run `sudo tailscale set --operator=$USER` once first).
5. `claude mcp add --scope user laptop-camera -- uv --directory ~/Projects/camera-agent run server.py`
   `codex mcp add laptop-camera -- uv --directory ~/Projects/camera-agent run server.py`

## Gotchas

- **`local_auth: true` is required.** go2rtc skips authentication for localhost requests by default, and `tailscale serve` proxies from loopback, so without this setting remote access has no authentication.
- **Do not disable RTSP.** The `ffmpeg:` source goes through go2rtc's internal RTSP module; it is bound to `127.0.0.1:8554` only.
- **Restart the service after changing the password** (`systemctl --user restart go2rtc`). Running agent sessions pick up the new password in a new session.
- `mcp` is pinned below 2 because 2.x renamed FastMCP.
- The camera opens only while a viewer or a snapshot request exists. Closing the lid covers the lens.

## Privacy

A snapshot is taken only when an agent calls the tool, and it is sent to that agent's model provider (Anthropic, OpenAI). Nothing is analyzed continuously or stored. Check that the camera does not point at people.

## Not yet verified

- Whether the service and `tailscale serve` come back after a reboot without a login
- Scene analysis in interactive Codex
- The Tailscale ACL scope (visible only in the admin console)
