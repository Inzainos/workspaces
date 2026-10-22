#!/usr/bin/env python3
"""Servidor SPA para el dashboard de Sentinel Omega (puerto 5173)."""
import http.server
import os
import urllib.parse

DIST = "/home/deamon/workspaces/sentinel_omega/infrastructure/dashboard/web/dist"
PORT = 5173

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path)
        clean = parsed.path.lstrip("/")
        full = os.path.join(DIST, clean)
        if os.path.isfile(full):
            return full
        return os.path.join(DIST, "index.html")

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", PORT), SPAHandler)
    print(f"SPA on :{PORT}", flush=True)
    server.serve_forever()
