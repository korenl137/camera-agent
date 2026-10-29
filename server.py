import base64
import os
import urllib.request

from mcp.server.fastmcp import FastMCP, Image

URL = os.environ.get("CAM_URL", "http://127.0.0.1:1984/api/frame.jpeg?src=cam")
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


def fetch_frame(url: str = URL) -> bytes:
    req = urllib.request.Request(url)
    user, password = os.environ.get("CAM_USER"), os.environ.get("CAM_PASSWORD")
    if user and password:
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
    except OSError as e:
        raise RuntimeError(f"go2rtc에 연결할 수 없습니다 (서비스 실행 여부 확인): {e}") from e
    if not data.startswith(b"\xff\xd8"):
        raise RuntimeError("go2rtc가 JPEG가 아닌 응답을 반환했습니다")
    return data


@mcp.tool()
def camera_snapshot() -> Image:
    """노트북 웹캠에서 현재 장면을 한 장 캡처한다."""
    return Image(data=fetch_frame(), format="jpeg")


if __name__ == "__main__":
    mcp.run()
