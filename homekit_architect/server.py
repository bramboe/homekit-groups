#!/usr/bin/env python3
"""
Minimal HTTP server for the add-on configuration page (ingress).
Serves a UI to reinstall the integration and open the integration panel.
Listens on port 8099 for Home Assistant ingress.
"""
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

LISTEN_PORT = 8099
SOURCE = "/usr/share/homekit_architect/homekit_architect"
CONFIG_DIRS = ["/config", "/homeassistant"]


def find_config():
    for d in CONFIG_DIRS:
        if os.path.isdir(d) and os.access(d, os.W_OK):
            return d
    return os.environ.get("CONFIG", "/config")


def run_install():
    config = find_config()
    target = os.path.join(config, "custom_components", "homekit_architect")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.exists(target):
        import shutil
        shutil.rmtree(target)
    subprocess.run(
        ["cp", "-r", SOURCE, target],
        check=True,
        capture_output=True,
        text=True,
    )
    return target


def get_status():
    config = find_config()
    target = os.path.join(config, "custom_components", "homekit_architect")
    installed = os.path.isdir(target) and os.path.isfile(
        os.path.join(target, "manifest.json")
    )
    return {
        "config_dir": config,
        "target": target,
        "installed": installed,
        "source_exists": os.path.isdir(SOURCE),
    }


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HomeKit Entity Architect – Add-on</title>
  <style>
    :root { --ha-card-background: #1c1c1c; --primary: #03a9f4; --error: #f44336; --success: #4caf50; }
    * { box-sizing: border-box; }
    body { font-family: Roboto, sans-serif; margin: 0; padding: 24px; background: #111; color: #e0e0e0; max-width: 640px; margin-left: auto; margin-right: auto; }
    h1 { font-size: 22px; margin: 0 0 8px 0; }
    .card { background: var(--ha-card-background); border-radius: 8px; padding: 20px; margin-bottom: 16px; }
    p { margin: 0 0 12px 0; color: #b0b0b0; font-size: 14px; }
    .status { font-size: 13px; padding: 12px; border-radius: 6px; margin: 12px 0; background: rgba(0,0,0,0.2); }
    .status.ok { border-left: 4px solid var(--success); }
    .status.warn { border-left: 4px solid #ff9800; }
    .status.err { border-left: 4px solid var(--error); }
    .btn { display: inline-block; padding: 10px 20px; border-radius: 6px; border: none; font-size: 14px; cursor: pointer; text-decoration: none; margin-right: 8px; margin-top: 8px; }
    .btn-primary { background: var(--primary); color: #fff; }
    .btn-primary:hover { opacity: 0.9; }
    .btn-secondary { background: #333; color: #e0e0e0; }
    .msg { margin-top: 12px; padding: 10px; border-radius: 6px; }
    .msg.success { background: rgba(76,175,80,0.2); color: var(--success); }
    .msg.error { background: rgba(244,67,54,0.2); color: var(--error); }
    code { font-size: 12px; background: #333; padding: 2px 6px; border-radius: 4px; }
    a { color: var(--primary); }
  </style>
</head>
<body>
  <div class="card">
    <h1>HomeKit Entity Architect</h1>
    <p>Add-on configuration. Use this page to reinstall the integration or open the main configuration panel.</p>
    <div id="status" class="status"></div>
    <div id="message"></div>
    <button id="reinstall" class="btn btn-primary">Reinstall integration</button>
    <a href="/config/homekit-architect" class="btn btn-secondary">Open configuration panel</a>
  </div>
  <script>
    const statusEl = document.getElementById('status');
    const messageEl = document.getElementById('message');
    const reinstallBtn = document.getElementById('reinstall');
    // Ingress serves at e.g. /api/hassio_ingress/XXX/ – use relative URLs so fetch hits the add-on
    const base = document.location.pathname.replace(/\/?$/, '/');

    function setMessage(text, type) {
      messageEl.innerHTML = text ? '<div class="msg ' + type + '">' + text + '</div>' : '';
    }

    function loadStatus() {
      fetch(base + 'status').then(r => r.json()).then(d => {
        if (d.installed) {
          statusEl.className = 'status ok';
          statusEl.innerHTML = 'Integration installed at <code>' + d.target + '</code>';
        } else if (d.source_exists) {
          statusEl.className = 'status warn';
          statusEl.innerHTML = 'Integration not installed. Click "Reinstall integration" to install to <code>' + d.target + '</code>';
        } else {
          statusEl.className = 'status err';
          statusEl.innerHTML = 'Source not found. Rebuild the add-on.';
        }
      }).catch(() => {
        statusEl.className = 'status err';
        statusEl.textContent = 'Could not load status.';
      });
    }

    reinstallBtn.addEventListener('click', function() {
      reinstallBtn.disabled = true;
      setMessage('', '');
      fetch(base + 'reinstall', { method: 'POST' })
        .then(r => r.json())
        .then(d => {
          if (d.ok) {
            setMessage(d.message || 'Integration reinstalled. Restart Home Assistant to load changes.', 'success');
            loadStatus();
          } else {
            setMessage(d.error || 'Reinstall failed.', 'error');
          }
        })
        .catch(() => setMessage('Request failed.', 'error'))
        .finally(() => { reinstallBtn.disabled = false; });
    });

    loadStatus();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stderr.write("[server] " + format % args + "\n")

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/" or path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return
        if path == "/status" or path == "/status/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(get_status()).encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/reinstall" or path == "/reinstall/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                target = run_install()
                self.wfile.write(
                    json.dumps(
                        {"ok": True, "message": f"Integration installed to {target}. Restart Home Assistant to load changes."}
                    ).encode("utf-8")
                )
            except Exception as e:
                self.wfile.write(
                    json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
                )
            return
        self.send_response(404)
        self.end_headers()


def main():
    server = HTTPServer(("0.0.0.0", LISTEN_PORT), Handler)
    sys.stderr.write(f"[HomeKit Entity Architect] Config server listening on port {LISTEN_PORT} (ingress)\n")
    server.serve_forever()


if __name__ == "__main__":
    main()
