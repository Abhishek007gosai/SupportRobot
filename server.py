"""Tiny web server so Render / Koyeb health checks pass."""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import config


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


def start_web_server():
    server = HTTPServer(("0.0.0.0", config.PORT), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
