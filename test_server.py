import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from server import fetch_frame

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
    with pytest.raises(RuntimeError, match="go2rtc"):
        fetch_frame("http://127.0.0.1:1/")
