#!/usr/bin/env python3
"""
3D Library Organizer - Local Live Server & API
Provides instant local file moving, catalog updating, and web gallery serving.
"""

import os
import sys
import json
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import reassign_core


WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 8000))

class LibraryApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WORKSPACE_DIR, **kwargs)

    def end_headers(self):
        # Enable CORS for local file:/// and cross-origin access
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                raw = self.rfile.read(content_length).decode("utf-8")
                return json.loads(raw)
        except Exception as e:
            print(f"[API ERROR] Parsing body: {e}")
        return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            base_exists = os.path.exists(reassign_core.BASE_DIR)
            self.send_json({
                "status": "online",
                "baseDir": reassign_core.BASE_DIR,
                "baseDirExists": base_exists,
                "version": "1.0.0"
            })
            return

        if path == "/api/structure":
            try:
                struct = reassign_core.get_library_structure()
                self.send_json(struct)
            except Exception as e:
                self.send_json({"error": str(e)}, status_code=500)
            return

        # Serve static files as default
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/move-file":
            payload = self.read_json_body()
            source_cat = payload.get("sourceCategory", "")
            source_creator = payload.get("sourceCreator", "")
            file_name = payload.get("fileName", "")
            dest_cat = payload.get("destCategory", "")
            dest_creator = payload.get("destCreator", "")
            new_file_name = payload.get("newFileName", None)
            move_companions = payload.get("moveCompanions", True)
            conflict_action = payload.get("conflictAction", "rename")

            if not (source_cat and source_creator and file_name and dest_cat and dest_creator):
                self.send_json({
                    "success": False,
                    "error": "Missing required fields (sourceCategory, sourceCreator, fileName, destCategory, destCreator)."
                }, status_code=400)
                return

            try:
                res = reassign_core.move_file(
                    source_cat=source_cat,
                    source_creator=source_creator,
                    file_display_name=file_name,
                    dest_cat=dest_cat,
                    dest_creator=dest_creator,
                    new_file_name=new_file_name,
                    move_companions=move_companions,
                    conflict_action=conflict_action
                )
                self.send_json(res)
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status_code=500)
            return

        if path == "/api/batch-move":
            payload = self.read_json_body()
            files_list = payload.get("files", [])
            dest_cat = payload.get("destCategory", "")
            dest_creator = payload.get("destCreator", "")
            move_companions = payload.get("moveCompanions", True)

            if not (files_list and dest_cat and dest_creator):
                self.send_json({
                    "success": False,
                    "error": "Missing required fields (files array, destCategory, destCreator)."
                }, status_code=400)
                return

            results = []
            errors = []
            for item in files_list:
                s_cat = item.get("sourceCategory")
                s_creator = item.get("sourceCreator")
                s_file = item.get("fileName")
                try:
                    r = reassign_core.move_file(
                        source_cat=s_cat,
                        source_creator=s_creator,
                        file_display_name=s_file,
                        dest_cat=dest_cat,
                        dest_creator=dest_creator,
                        move_companions=move_companions
                    )
                    results.append(r)
                except Exception as e:
                    errors.append({"file": s_file, "error": str(e)})

            self.send_json({
                "success": len(errors) == 0,
                "movedCount": len(results),
                "errorCount": len(errors),
                "results": results,
                "errors": errors,
                "destCategory": dest_cat,
                "destCreator": dest_creator
            })
            return

        if path == "/api/move-collection":
            payload = self.read_json_body()
            source_cat = payload.get("sourceCategory", "")
            source_creator = payload.get("sourceCreator", "")
            dest_cat = payload.get("destCategory", "")
            dest_creator = payload.get("destCreator", None)

            if not (source_cat and source_creator and dest_cat):
                self.send_json({
                    "success": False,
                    "error": "Missing required fields (sourceCategory, sourceCreator, destCategory)."
                }, status_code=400)
                return

            try:
                res = reassign_core.move_collection(
                    source_cat=source_cat,
                    creator=source_creator,
                    dest_cat=dest_cat,
                    dest_creator=dest_creator
                )
                self.send_json(res)
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status_code=500)
            return

        if path == "/api/undo":
            try:
                res = reassign_core.undo_last_move()
                self.send_json(res)
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status_code=500)
            return

        self.send_json({"error": "Endpoint not found"}, status_code=404)

def start_server():
    global PORT
    server_address = ("", PORT)
    try:
        httpd = ThreadingHTTPServer(server_address, LibraryApiHandler)
    except OSError:
        PORT = 8055
        server_address = ("", PORT)
        httpd = ThreadingHTTPServer(server_address, LibraryApiHandler)

    print("=" * 65)
    print(f"🚀 3D Printing Library Organizer Server is Running!")
    print(f"📡 Web Gallery:  http://localhost:{PORT}")
    print(f"📂 Storage Root: {reassign_core.BASE_DIR}")
    print("=" * 65)
    print("Press Ctrl+C to stop the server.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    start_server()
