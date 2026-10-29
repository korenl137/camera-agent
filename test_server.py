import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import server
from server import fetch_frame, snapshot_url

JPEG = b"\xff\xd8\xff\xe0fake"


def serve(body: bytes, status: int = 200) -> str:
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(status)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_port}/"


def test_returns_jpeg_bytes():
    assert fetch_frame(serve(JPEG)) == JPEG


def test_rejects_non_jpeg():
    with pytest.raises(RuntimeError, match="JPEG"):
        fetch_frame(serve(b"<html>error</html>"))


def test_connection_refused_is_clear_error():
    with pytest.raises(RuntimeError, match="연결할 수 없습니다"):
        fetch_frame("http://127.0.0.1:1/")


def test_unknown_camera_404_is_not_reported_as_connection_error():
    with pytest.raises(RuntimeError, match="없는 카메라"):
        fetch_frame(serve(b"stream not found", status=404))


def test_auth_failure_401_is_clear_error():
    with pytest.raises(RuntimeError, match="인증"):
        fetch_frame(serve(b"", status=401))


def test_other_http_error_keeps_status_code():
    with pytest.raises(RuntimeError, match="HTTP 500"):
        fetch_frame(serve(b"", status=500))


def test_default_camera_keeps_existing_stream_name():
    assert snapshot_url().endswith("/api/frame.jpeg?src=cam")


def test_camera_name_goes_into_url():
    assert snapshot_url("printer").endswith("/api/frame.jpeg?src=printer")


@pytest.mark.parametrize("bad", ["", "a b", "a&src=cam", "cam/../x", "x" * 33, "카메라"])
def test_rejects_unsafe_camera_names(bad):
    with pytest.raises(ValueError):
        snapshot_url(bad)


def test_tool_passes_camera_to_go2rtc(monkeypatch):
    seen = []
    monkeypatch.setattr(server, "fetch_frame", lambda url: seen.append(url) or JPEG)
    server.camera_snapshot("printer")
    server.camera_snapshot()
    assert seen[0].endswith("src=printer") and seen[1].endswith("src=cam")
