"""Camera control panel: V4L2 sliders + presets for cam1, and a proxied MJPEG view (one login for everything)."""
import base64, fcntl, hmac, json, os, struct, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEV = "/dev/v4l/by-id/usb-SYX-230524-J_HD_Camera-video-index0"
GO2RTC = os.environ.get("CAM_BASE", "http://127.0.0.1:1984")
PORT = int(os.environ.get("PANEL_PORT", "8765"))
USER, PASSWORD = os.environ.get("CAM_USER", ""), os.environ.get("CAM_PASSWORD", "")
HTML = os.path.join(os.path.dirname(__file__), "static", "panel.html")

QUERY, GET, SET, NEXT = 0xC0445624, 0xC008561B, 0xC008561C, 0x80000000
# Order matters: the mode switch comes before the value it unlocks.
PRESETS = {
    "default": {"Brightness": 0, "Contrast": 0, "Saturation": 80, "Hue": 0, "Gamma": 84, "Gain": 1, "Sharpness": 2,
                "Backlight Compensation": 0, "White Balance, Automatic": 1, "Auto Exposure": 3},
    "sharp": {"Sharpness": 5, "Gamma": 110, "Backlight Compensation": 64},
    "backlight": {"Backlight Compensation": 128, "Gamma": 120, "Brightness": 10},
    "night": {"Auto Exposure": 3, "Gain": 8, "Brightness": 30, "Gamma": 140, "Contrast": 20, "Sharpness": 4},
}


def controls():
    """Read every control from the device: name -> {id, type, min, max, step, value}."""
    fd, out, i = os.open(DEV, os.O_RDWR), {}, NEXT
    try:
        while True:
            b = bytearray(68); struct.pack_into("I", b, 0, i)
            try: fcntl.ioctl(fd, QUERY, b)
            except OSError: break
            cid, typ = struct.unpack_from("II", b, 0)
            i = cid | NEXT
            if typ == 6: continue  # control-class header
            name = bytes(b[8:40]).split(b"\0")[0].decode()
            mn, mx, st = struct.unpack_from("iii", b, 40)
            g = bytearray(8); struct.pack_into("I", g, 0, cid); fcntl.ioctl(fd, GET, g)
            out[name] = dict(id=cid, type=typ, min=mn, max=mx, step=st or 1, value=struct.unpack_from("i", g, 4)[0])
    finally:
        os.close(fd)
    return out


def apply(values):
    """Validate against the device's own min/max, then write. Unknown names or out-of-range values are rejected."""
    known = controls()
    for n, v in values.items():
        if n not in known or not isinstance(v, int) or not known[n]["min"] <= v <= known[n]["max"]:
            raise ValueError(f"invalid control {n!r}={v!r}")
    fd = os.open(DEV, os.O_RDWR)
    try:
        for n, v in values.items():
            g = bytearray(8); struct.pack_into("Ii", g, 0, known[n]["id"], v); fcntl.ioctl(fd, SET, g)
    finally:
        os.close(fd)


class H(BaseHTTPRequestHandler):
    def authed(self):
        want = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
        if USER and PASSWORD and hmac.compare_digest(self.headers.get("Authorization", ""), want):
            return True
        self.send_response(401); self.send_header("WWW-Authenticate", 'Basic realm="camera"'); self.end_headers()
        return False

    def send(self, code, body, ctype="application/json"):
        body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        if not self.authed(): return
        if self.path == "/":
            self.send(200, open(HTML, "rb").read(), "text/html; charset=utf-8")
        elif self.path == "/api/controls":
            self.send(200, {"controls": controls(), "presets": list(PRESETS)})
        elif self.path == "/video":  # go2rtc credentials stay on the server
            req = urllib.request.Request(f"{GO2RTC}/api/stream.mjpeg?src=cam1")
            req.add_header("Authorization", "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode())
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    self.send_response(200); self.send_header("Content-Type", r.headers["Content-Type"]); self.end_headers()
                    while chunk := r.read(65536): self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError): pass
            except OSError as e: self.send(502, {"error": str(e)})
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):
        if not self.authed(): return
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/api/set": apply(data)
            elif self.path == "/api/preset": apply(PRESETS[data["name"]])
            else: return self.send(404, {"error": "not found"})
            self.send(200, {"controls": controls()})
        except (ValueError, KeyError, TypeError, OSError) as e:
            self.send(400, {"error": str(e)})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
