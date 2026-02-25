#!/usr/bin/env python3
"""Minimal HTTP server that redirects to the HomeKit Architect panel. Used for add-on ingress."""
import http.server
import socketserver

PORT = 8099
REDIRECT_PATH = "/config/homekit-architect"


class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", REDIRECT_PATH)
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    with socketserver.TCPServer(("0.0.0.0", PORT), RedirectHandler) as httpd:
        httpd.serve_forever()
