"""SplatWalk dev server.

  python serve.py            -> http://localhost:8080  (desktop testing; localhost counts as secure for WebXR)
  python serve.py --https    -> https://<your-lan-ip>:8443 for the Quest browser (self-signed cert, accept the warning once)

The https mode needs a cert.pem / key.pem next to this file. Create one with:
  openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 3650 -subj "/CN=splatwalk"
(Git for Windows ships openssl: "C:\\Program Files\\Git\\usr\\bin\\openssl.exe")
"""
import http.server
import os
import socket
import ssl
import sys
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
HTTPS = "--https" in sys.argv
PORT = 8443 if HTTPS else 8080
ENTRY = next((f for f in sorted(os.listdir(ROOT), reverse=True) if f.startswith("SplatWalk_v") and f.endswith(".html")), "")


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".json": "application/json",
        ".ply": "application/octet-stream",
        ".spz": "application/octet-stream",
        ".splat": "application/octet-stream",
        ".ksplat": "application/octet-stream",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


if __name__ == "__main__":
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    scheme = "http"
    if HTTPS:
        cert, key = os.path.join(ROOT, "cert.pem"), os.path.join(ROOT, "key.pem")
        if not (os.path.exists(cert) and os.path.exists(key)):
            print("cert.pem / key.pem not found. See the docstring at the top of serve.py.")
            sys.exit(1)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        scheme = "https"
    local = f"{scheme}://localhost:{PORT}/{ENTRY}"
    print(f"SplatWalk serving {ROOT}")
    print(f"  desktop: {local}")
    print(f"  quest:   {scheme}://{lan_ip()}:{PORT}/{ENTRY}   (https only; or use adb reverse, see README)")
    if "--no-open" not in sys.argv:
        webbrowser.open(local)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
