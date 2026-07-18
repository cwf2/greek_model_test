"""
Local web app for reviewing/editing data/spotchecks/spotcheck_sample.csv by hand.

    python3 spotcheck_review.py

Serves a single-page app at http://localhost:8770 that shows one row at a
time (all three models' tags side by side), lets you edit human_judgement
and notes, and saves each edit straight back to the CSV on disk.
"""
import argparse
import csv
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(REPO_ROOT, "spotcheck_review")
DEFAULT_CSV = os.path.join(REPO_ROOT, "data", "spotchecks", "spotcheck_sample.csv")

STATIC_FILES = {
    "/": ("index.html", "text/html"),
    "/index.html": ("index.html", "text/html"),
    "/app.js": ("app.js", "application/javascript"),
    "/style.css": ("style.css", "text/css"),
}


def load_rows(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    return fieldnames, rows


def save_rows(csv_path, fieldnames, rows):
    tmp_path = csv_path + ".tmp"
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, csv_path)


def make_handler(csv_path):
    # No in-memory row cache: every request re-reads the CSV from disk and
    # every save writes straight back. This is deliberate, not an oversight
    # — a stale in-memory copy here previously clobbered edits made outside
    # the app (or by a second server instance) whenever *any* save fired,
    # because saving rewrote the whole file from memory. Re-reading a
    # 162-row CSV per request is effectively free, so there's no reason to
    # risk that class of bug for the sake of caching.

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # keep the terminal quiet

        def _send_json(self, obj, status=200):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/api/rows":
                fieldnames, rows = load_rows(csv_path)
                self._send_json({"fieldnames": fieldnames, "rows": rows})
                return
            entry = STATIC_FILES.get(self.path)
            if entry:
                fname, ctype = entry
                fpath = os.path.join(STATIC_DIR, fname)
                with open(fpath, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", f"{ctype}; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            if not self.path.startswith("/api/rows/"):
                self.send_response(404)
                self.end_headers()
                return

            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")

            # Re-read fresh so a save never clobbers edits made elsewhere
            # (another server instance, a script, manual editing) since this
            # request started.
            fieldnames, rows = load_rows(csv_path)
            try:
                idx = int(self.path.rsplit("/", 1)[-1])
                assert 0 <= idx < len(rows)
            except (ValueError, AssertionError):
                self._send_json({"error": "bad row index"}, status=400)
                return

            row = rows[idx]
            for key in ("human_judgement", "notes"):
                if key in body:
                    row[key] = body[key]

            save_rows(csv_path, fieldnames, rows)
            self._send_json({"ok": True, "row": row})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=DEFAULT_CSV, help="path to spotcheck CSV")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        sys.exit(f"CSV not found: {args.csv}")

    handler = make_handler(args.csv)
    server = ThreadingHTTPServer(("localhost", args.port), handler)
    url = f"http://localhost:{args.port}/"
    print(f"Serving {args.csv}")
    print(f"Open {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
