#!/usr/bin/env python3
"""
Web UI/server.py

Jprogram form-serving channel (Advisor <-> Owner).

Not a fixed app -- a generic mechanism. Advisor writes/updates the HTML file
under forms/ for whatever task is at hand (batch import today, something else
tomorrow); Owner opens it, hard-refreshes (Ctrl+F5) to pick up the latest
version, fills it in, and submits. The submission is written to
pending_submission.json and Advisor picks it up (a Monitor-based watch on
that file, per the agreed 2026-08-13 design -- no polling from the browser
side, no "done" message needed from Owner).

Stdlib only, same lightweight pattern as QuadRead/server.py -- no framework,
no new dependencies.

API:
  GET  /api/config           -> { creators: [...], styles: [...], topics: [...] }
                                 read from Workspace/Config/*.json, for the
                                 form's dropdowns.
  GET  /api/browse-folder    -> pops a native OS folder-picker dialog
                                 (tkinter, run in a subprocess so it never
                                 touches the server's own thread/event loop)
                                 and returns { "path": "..." } (path is ""
                                 if the user cancelled).
  POST /api/submit           -> body: form JSON. Writes it to
                                 pending_submission.json (atomic replace,
                                 timestamped) and returns {"ok": true}.
Everything else: static files from this folder (forms/, this file's dir).

Run:  python server.py
"""
import json
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
CONFIG_DIR = PROJECT_ROOT.parent / "Workspace" / "Config"
PENDING_SUBMISSION = ROOT / "pending_submission.json"
PORT = 8001


def _load_json_list(path, key):
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data.get(key, [])


def _write_atomic(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


_BROWSE_FOLDER_SCRIPT = (
    "import tkinter, tkinter.filedialog as fd;"
    "r = tkinter.Tk(); r.withdraw(); r.attributes('-topmost', True);"
    "print(fd.askdirectory() or '')"
)


def _browse_folder():
    """
    Pop a native OS folder-picker dialog and return the chosen path ("" if
    cancelled). Runs tkinter in a subprocess -- this server is a
    ThreadingHTTPServer handling the request on a worker thread, and Tk
    is not safe to drive outside a dedicated main-thread event loop, so a
    fresh interpreter process with its own Tk mainloop sidesteps that
    entirely rather than trying to share one with the server.
    """
    completed = subprocess.run(
        [sys.executable, "-c", _BROWSE_FOLDER_SCRIPT],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return completed.stdout.strip()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            payload = {
                "creators": _load_json_list(CONFIG_DIR / "creators.json", "creators"),
                "styles": _load_json_list(CONFIG_DIR / "styles.json", "styles"),
                "topics": _load_json_list(CONFIG_DIR / "topics.json", "topics"),
            }
            self._send_json(200, payload)
            return
        if parsed.path == "/api/browse-folder":
            self._send_json(200, {"path": _browse_folder()})
            return
        # No-cache for HTML so Ctrl+F5 (or even a plain refresh) always gets
        # the current form -- Advisor may rewrite forms/*.html between one
        # request and the next.
        super().do_GET()

    def end_headers(self):
        if self.path.endswith(".html") or self.path == "/":
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/submit":
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError as exc:
            self._send_json(400, {"error": f"invalid JSON: {exc}"})
            return
        record = {"submitted_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "data": data}
        _write_atomic(PENDING_SUBMISSION, json.dumps(record, ensure_ascii=False, indent=2))
        self._send_json(200, {"ok": True})


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Jprogram Web UI: http://localhost:{PORT}")
    print(f"Forms served from: {ROOT / 'forms'}")
    print(f"Submissions written to: {PENDING_SUBMISSION}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
