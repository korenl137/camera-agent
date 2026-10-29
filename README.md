# camera-agent

노트북 내장 웹캠을 go2rtc로 스트리밍하고, `camera_snapshot` MCP 도구로 Claude Code와 Codex가 현재 장면을 볼 수 있게 한다.

```
USB 웹캠 → go2rtc (127.0.0.1:1984, user systemd) ─┬─ tailscale serve (tailnet 전용 HTTP :1984) → 브라우저 시청
                                                  └─ /api/frame.jpeg ← server.py (FastMCP, stdio) ← Claude Code / Codex
```

## 구성 파일

| 파일 | 역할 |
|---|---|
| `go2rtc.yaml` | 스트림 정의. 계정은 `${CAM_USER}`/`${CAM_PASSWORD}`로 환경에서 읽음 |
| `systemd/go2rtc.service` | 사용자 서비스. `~/.config/systemd/user/`에 링크 |
| `server.py` | `camera_snapshot` 도구 하나. 계정은 `~/.config/camera-agent/env`에서 직접 읽음 |
| `test_server.py` | `uv run pytest` |

비밀번호는 저장소에 없다: `~/.config/camera-agent/env` (권한 600, `CAM_USER`, `CAM_PASSWORD`).

## 설치 (이 기기에서 한 일)

1. go2rtc 공식 릴리스(`AlexxIT/go2rtc`, v1.9.15 linux_amd64)를 받아 SHA256을 릴리스 digest와 대조하고 `~/.local/bin/go2rtc`에 설치.
2. `~/.config/camera-agent/env` 작성 (비밀번호는 `secrets.token_urlsafe(24)`).
3. `ln -s ~/Projects/camera-agent/systemd/go2rtc.service ~/.config/systemd/user/ && systemctl --user enable --now go2rtc`
4. `tailscale serve --bg --http=1984 http://127.0.0.1:1984` (최초 1회 `sudo tailscale set --operator=$USER`)
5. `claude mcp add --scope user laptop-camera -- uv --directory ~/Projects/camera-agent run server.py`
   `codex mcp add laptop-camera -- uv --directory ~/Projects/camera-agent run server.py`

## 알아둘 점

- **`local_auth: true`가 필수다.** go2rtc는 기본으로 localhost 요청의 인증을 건너뛰는데, `tailscale serve`가 loopback에서 프록시하므로 이 설정이 없으면 원격 접속에 인증이 없다.
- **RTSP를 끄면 안 된다.** `ffmpeg:` 소스는 go2rtc 내부 RTSP를 거친다. `127.0.0.1:8554`로만 연다.
- **비밀번호를 바꾸면 서비스를 재시작한다** (`systemctl --user restart go2rtc`). 열려 있는 에이전트 세션은 새 세션부터 반영된다.
- `mcp`는 2.x에서 FastMCP 이름이 바뀌어 `<2`로 고정했다.
- 카메라는 시청자나 스냅샷 요청이 있을 때만 열린다. 덮개를 닫으면 렌즈가 가려진다.

## 프라이버시

스냅샷은 에이전트가 도구를 호출할 때만 찍혀 해당 모델 제공자(Anthropic, OpenAI)로 전송된다. 상시 분석이나 저장은 하지 않는다. 카메라가 향한 곳에 사람이 찍히는지 확인할 것.

## 미검증

- 재부팅 후 로그인 없이 서비스와 `tailscale serve`가 올라오는지
- Codex 대화형 환경에서의 장면 분석
- Tailscale ACL의 접근 범위 (관리 콘솔에서만 확인 가능)
