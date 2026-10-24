import base64
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

from harness_core.server import make_server
from support import Fixture


class ServerTests(Fixture):
    def setUp(self):
        super().setUp()
        self.activity_key = self.activity(activity_id="hosted", suffix=".html", source="<!doctype html><h1>Fictional isolated activity</h1>", private_evaluation="PRIVATE-EXPECTED-ANSWER")
        self.server = make_server(self.h, 0, runtime=self.root / "runtime")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.addCleanup(self.stop)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.opener = build_opener(ProxyHandler({}))
        self.token = self.get("/api/workspace")[0]["token"]

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)

    def get(self, path):
        with self.opener.open(self.base + path) as response:
            data = response.read()
            return (json.loads(data) if response.headers.get_content_type() == "application/json" else data), response.headers

    def post(self, path, data, *, token=None, origin=None):
        request = Request(self.base + path, data=json.dumps(data).encode(), headers={"Content-Type": "application/json",
            "X-Harness-Token": token if token is not None else self.token, "Origin": origin or self.base})
        with self.opener.open(request) as response:
            return json.loads(response.read())

    def test_host_serves_dashboard_and_isolated_surface(self):
        page, _ = self.get("/")
        self.assertIn(b"Fieldnotes", page)
        surface, headers = self.get("/surface/fictional/hosted/v001/task.html")
        self.assertIn(b"/bridge.js", surface)
        self.assertIn("sandbox", headers["Content-Security-Policy"])
        public, _ = self.get("/api/activity/fictional/hosted/v001")
        self.assertNotIn("PRIVATE-EXPECTED-ANSWER", json.dumps(public))
        workspace, _ = self.get("/api/workspace")
        detail, _ = self.get("/api/courses/fictional")
        self.assertNotIn("PRIVATE-EXPECTED-ANSWER", json.dumps(workspace))
        self.assertNotIn("PRIVATE-EXPECTED-ANSWER", json.dumps(detail))
        self.assertIn("PRIVATE-EXPECTED-ANSWER", json.dumps(self.h.resume("fictional")))

    def test_draft_restore_is_not_evidence_and_stale_tab_cannot_overwrite(self):
        before = len(self.h.store.events("fictional"))
        payload = {"answer": "A literal unsent draft", "assistance": "unknown", "state": {"step": 2}, "revision": 0}
        saved = self.post("/api/activity/fictional/hosted/v001/draft", payload)
        self.assertEqual(saved["revision"], 1)
        public, _ = self.get("/api/activity/fictional/hosted/v001")
        self.assertEqual(public["draft"]["state"], {"step": 2})
        self.assertEqual(len(self.h.store.events("fictional")), before)
        with self.assertRaises(HTTPError) as error:
            self.post("/api/activity/fictional/hosted/v001/draft", payload)
        self.assertEqual(error.exception.code, 409)

    def test_foreign_origins_invalid_token_and_host_are_rejected(self):
        payload = {"answer": "Fictional answer", "assistance": [], "client_id": "browser-retry"}
        for kwargs in [{"token": "wrong"}, {"origin": "http://foreign.example"}, {"origin": "null"}]:
            with self.assertRaises(HTTPError):
                self.post("/api/activity/fictional/hosted/v001/submit", payload, **kwargs)
        request = Request(self.base + "/api/workspace", headers={"Host": "foreign.example"})
        with self.assertRaises(HTTPError):
            self.opener.open(request)

    def test_browser_submission_retries_and_attachment_capture(self):
        payload = {"answer": "Fictional literal response", "assistance": ["unknown"], "client_id": "browser-retry",
            "artifacts": [{"name": "recording.wav", "base64": base64.b64encode(b"fictional-audio-bytes").decode()}]}
        first = self.post("/api/activity/fictional/hosted/v001/submit", payload)
        retry = self.post("/api/activity/fictional/hosted/v001/submit", payload)
        self.assertEqual(first["id"], retry["id"])
        self.assertIn("Return to your agent", first["message"])
        pending = self.h.state("fictional")["pending"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["artifacts"][0]["name"], "recording.wav")

    def test_new_answer_supersedes_pending_queue_but_not_raw_history(self):
        first = self.submit(self.activity_key)
        second = self.submit(self.activity_key, answer="A revised literal answer")
        self.assertEqual([p["id"] for p in self.h.state("fictional")["pending"]], [second["id"]])
        self.assess(second)
        self.assertEqual(self.h.state("fictional")["pending"], [])
        self.assertIn(first["id"], self.h.state("fictional")["submissions"])

    def test_download_is_attachment_and_unpublished_assets_are_inaccessible(self):
        _, headers = self.get("/download/fictional/hosted/v001/task.html")
        self.assertEqual(headers["Content-Disposition"], "attachment")
        for path in ["/surface/fictional/hosted/v001/../../../course.json", "/surface/fictional/hosted/v001/course.json", "/evidence/events"]:
            with self.assertRaises(HTTPError):
                self.get(path)
