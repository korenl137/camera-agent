import base64
import os
import re
import urllib.error
import urllib.request

from mcp.server.fastmcp import FastMCP, Image

BASE = os.environ.get("CAM_BASE", "http://127.0.0.1:1984")
DEFAULT_CAMERA = "cam"
CAMERA_NAME = re.compile(r"[A-Za-z0-9_-]{1,32}")
ENV_FILE = os.path.expanduser("~/.config/camera-agent/env")

# MCP clients launch stdio servers with a stripped environment, so read the credentials file directly.
try:
    for line in open(ENV_FILE):
        k, _, v = line.strip().partition("=")
        if k and v:
            os.environ.setdefault(k, v)
except FileNotFoundError:
    pass

mcp = FastMCP("laptop-camera")


def snapshot_url(camera: str = DEFAULT_CAMERA) -> str:
    # the name goes into a query string, so only allow what go2rtc stream names use here
    if not CAMERA_NAME.fullmatch(camera):
        raise ValueError(f"카메라 이름은 영문, 숫자, -, _ 만 쓸 수 있습니다 (최대 32자): {camera!r}")
    return f"{BASE}/api/frame.jpeg?src={camera}"


def fetch_frame(url: str) -> bytes:
    req = urllib.request.Request(url)
    user, password = os.environ.get("CAM_USER"), os.environ.get("CAM_PASSWORD")
    if user and password:
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
    except urllib.error.HTTPError as e:  # subclass of OSError, so it must be caught first
        if e.code == 404:
            raise RuntimeError("go2rtc에 없는 카메라 이름입니다 (go2rtc.yaml의 streams 이름 확인)") from e
        if e.code in (401, 403):
            raise RuntimeError("go2rtc 인증에 실패했습니다 (~/.config/camera-agent/env의 계정 확인)") from e
        raise RuntimeError(f"go2rtc가 오류를 반환했습니다: HTTP {e.code}") from e
    except OSError as e:
        raise RuntimeError(f"go2rtc에 연결할 수 없습니다 (서비스 실행 여부 확인): {e}") from e
    if not data.startswith(b"\xff\xd8"):
        raise RuntimeError("go2rtc가 JPEG가 아닌 응답을 반환했습니다")
    return data


@mcp.tool()
def camera_snapshot(camera: str = DEFAULT_CAMERA) -> Image:
    """카메라에서 현재 장면을 한 장 캡처한다. camera는 go2rtc.yaml의 stream 이름이며 기본값 cam은 노트북 내장 웹캠이다."""
    return Image(data=fetch_frame(snapshot_url(camera)), format="jpeg")


if __name__ == "__main__":
    mcp.run()
