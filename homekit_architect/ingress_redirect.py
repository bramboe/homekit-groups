#!/usr/bin/env python3
"""Minimal HTTP server that redirects to the HomeKit Architect panel. Used for add-on ingress."""
import http.server
import socketserver
import urllib.parse

PORT = 8099
REDIRECT_PATH = "/config/homekit-architect"


def get_redirect_url(handler):
    """Build absolute URL so redirect works from ingress (and breaks out of iframe if needed)."""
    host = handler.headers.get("Host", "localhost:8123")
    # Ingress often sends X-Forwarded-Proto
    proto = handler.headers.get("X-Forwarded-Proto", "https")
    return f"{proto}://{host}{REDIRECT_PATH}"


class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = get_redirect_url(self)
        # Prefer 302 redirect; some ingress/iframe setups ignore it, so send HTML that redirects top frame
        accept = self.headers.get("Accept", "")
        if "text/html" in accept:
            body = (
                f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                f"<meta http-equiv='refresh' content='0;url={urllib.parse.quote(url, safe=":/")}'>"
                f"<script>window.top.location.href={repr(url)};</script></head>"
                f"<body><p>Redirecting to <a href={repr(url)}>HomeKit Architect</a>...</p></body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    with socketserver.TCPServer(("0.0.0.0", PORT), RedirectHandler) as httpd:
        httpd.serve_forever()
