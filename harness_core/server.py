"""Loopback dashboard, isolated activity host and raw-response capture."""
from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
from urllib.parse import unquote, urlsplit

from .activities import activity_key, public_activity, read_asset, render
from .engine import require
from .store import Invalid, atomic_json, read_json, safe_path

WEB = Path(__file__).resolve().parents[1] / "web"


def make_server(harness, port=8780, *, runtime=None, jupyter_python=None):
    token = secrets.token_urlsafe(32)
    runtime = Path(runtime or WEB.parent / ".runtime")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def origin(self):
            return "http://" + self.headers.get("Host", "")

        def check_host(self):
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            require(self.headers.get("Host") in allowed, "This is a local single-user service")

        def reply(self, data, status=200, mime="application/json; charset=utf-8", *, asset=False, surface=False, attachment=False):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if asset:
                self.send_header("Access-Control-Allow-Origin", "*")
            if attachment:
                self.send_header("Content-Disposition", "attachment")
            if surface:
                self.send_header("Content-Security-Policy", "sandbox allow-scripts allow-downloads; default-src 'none'; script-src " + self.origin()
                    + " 'unsafe-inline' 'unsafe-eval'; style-src " + self.origin()
                    + " 'unsafe-inline'; img-src " + self.origin() + " data: blob:; media-src " + self.origin()
                    + " data: blob:; font-src " + self.origin() + " data:; connect-src 'none'; form-action 'none'; frame-src 'none'")
            else:
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def body(self):
            require(self.headers.get("X-Harness-Token") == token, "Reload the dashboard before saving")
            require(self.headers.get("Origin") in {None, self.origin()}, "Foreign-origin writes are not allowed")
            size = int(self.headers.get("Content-Length", "0"))
            require(0 < size <= 24 * 1024 * 1024, "Invalid request size (maximum 24 MiB)")
            require(self.headers.get("Content-Type", "").startswith("application/json"), "Use application/json")
            value = json.loads(self.rfile.read(size))
            require(isinstance(value, dict), "Request must be an object")
            return value

        def parts(self):
            return [unquote(part) for part in urlsplit(self.path).path.split("/") if part]

        def do_GET(self):
            try:
                self.check_host()
                parts = self.parts()
                if parts == ["api", "workspace"]:
                    return self.reply({**harness.overview(), "token": token})
                if len(parts) == 3 and parts[:2] == ["api", "courses"]:
                    state = harness.state(parts[2])
                    return self.reply({"summary": harness.summary(state), "goal": state["goal"],
                        "graph": state["graph"], "learner": state["learner"], "reviews": state["reviews"],
                        "plan": state["plan"], "checkpoint": state["checkpoint"], "resources": state["resources"],
                        "activities": [public_activity(a) for a in state["activities"].values()],
                        "pending": [{k: v for k, v in s.items() if k != "artifacts"} for s in state["pending"]],
                        "assessments": list(state["assessments"].values())})
                if len(parts) == 5 and parts[:2] == ["api", "activity"]:
                    course, aid, version = parts[2:]
                    key = aid + "@" + version
                    state = harness.state(course)
                    require(key in state["activities"], "Unknown activity version")
                    path = safe_path(harness.store.root(course), f"drafts/browser/{aid}/{version}.json")
                    draft = read_json(path) if path.exists() else {"answer": "", "assistance": "unknown", "state": {}, "revision": 0}
                    submissions = [s for s in state["submissions"].values() if s["activity"] == key]
                    return self.reply({"activity": public_activity(state["activities"][key]), "draft": draft,
                        "course": {"id": course, "title": state["goal"]["title"], "fictional": state["course"]["fictional"]},
                        "submissions": [{k: v for k, v in s.items() if k != "artifacts"} for s in submissions],
                        "assessments": [state["assessments"][s["id"]] for s in submissions if s["id"] in state["assessments"]]})
                if len(parts) >= 6 and parts[0] in {"surface", "download"}:
                    course, aid, version = parts[1:4]
                    relative = "/".join(parts[4:])
                    return self.asset(course, aid, version, relative, download=parts[0] == "download")
                # Entrypoints normally have one file segment, so accept that route too.
                if len(parts) == 5 and parts[0] in {"surface", "download"}:
                    return self.asset(parts[1], parts[2], parts[3], parts[4], download=parts[0] == "download")
                filename = "activity.html" if len(parts) == 4 and parts[0] == "activity" else (
                    "index.html" if not parts or (len(parts) == 2 and parts[0] == "course") else "/".join(parts))
                require(filename in {"index.html", "activity.html", "app.js", "activity.js", "styles.css", "bridge.js", "theme.js"}, "Page not found")
                data = (WEB / filename).read_bytes()
                return self.reply(data, mime=mimetypes.guess_type(filename)[0] or "text/plain", asset=filename == "bridge.js")
            except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
                self.reply({"error": str(exc)}, 404)

        def asset(self, course, aid, version, relative, *, download=False):
            if download:
                data, mime = read_asset(harness, course, aid + "@" + version, relative), None
            else:
                data, mime = render(harness, course, aid + "@" + version, relative)
            self.reply(data, mime=mime or mimetypes.guess_type(relative)[0] or "application/octet-stream", asset=True, surface=not download, attachment=download)

        def do_POST(self):
            try:
                self.check_host()
                p = self.body()
                parts = self.parts()
                if parts == ["api", "courses"]:
                    result = harness.create(p["id"], p["title"], p["goal"])
                    harness._snapshot(p["id"])
                    return self.reply(result, 201)
                if len(parts) == 4 and parts[:2] == ["api", "courses"] and parts[3] == "status":
                    return self.reply(harness.record(parts[2], "status", p))
                if len(parts) == 6 and parts[:2] == ["api", "activity"]:
                    course, aid, version, action = parts[2:]
                    key = aid + "@" + version
                    require(key in harness.state(course)["activities"], "Unknown activity version")
                    if action == "draft":
                        require(isinstance(p.get("answer"), str) and len(p["answer"]) <= 100000, "Invalid draft")
                        require(p.get("assistance") in {"unknown", "unassisted", "assisted"}, "Choose assistance status")
                        require(isinstance(p.get("state", {}), dict), "Activity state must be an object")
                        with harness.store.locked(course):
                            path = safe_path(harness.store.root(course), f"drafts/browser/{aid}/{version}.json")
                            previous = read_json(path) if path.exists() else {"revision": 0}
                            require(p.get("revision") == previous["revision"], "Draft changed in another tab; copy your answer before reloading")
                            p["revision"] = previous["revision"] + 1
                            atomic_json(path, p)
                        return self.reply(p)
                    if action == "submit":
                        result = harness.submit(course, key, p.get("answer"), p.get("assistance"), client_id=p.get("client_id"), artifact_data=p.get("artifacts", []))
                        return self.reply({"id": result["id"], "message": "Saved. Return to your agent conversation for feedback.",
                            "return_prompt": f"I finished {key} in {course}. Resume the course and inspect submission {result['id']} before giving feedback."}, 201)
                    if action == "help":
                        return self.reply(harness.record(course, "observation", {"activity": key, "kind": "help", "role": "observer", "text": p.get("text")}))
                    if action == "notebook":
                        from .workbench import open_notebook
                        return self.reply(open_notebook(harness, course, key, runtime, python=jupyter_python, ai=p.get("ai") is True))
                raise Invalid("Unknown operation")
            except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
                self.reply({"error": str(exc)}, 409 if "changed" in str(exc) else 400)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def serve(harness, port=8780, *, runtime=None, jupyter_python=None):
    server = make_server(harness, port, runtime=runtime, jupyter_python=jupyter_python)
    print(f"Learning dashboard: http://127.0.0.1:{server.server_port}\nCourses: {harness.store.courses}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
