"""Offline contract tests for the portable task CLI; no app runtime or GPU."""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, urlsplit


SCRIPTS = Path(__file__).resolve().parents[1] / "agent-skills/short-drama-factory/scripts"
spec = importlib.util.spec_from_file_location("factory_api", SCRIPTS / "factory_api.py")
factory = importlib.util.module_from_spec(spec)
sys.modules["factory_api"] = factory
spec.loader.exec_module(factory)
spec = importlib.util.spec_from_file_location("sdf_cli", SCRIPTS / "sdf.py")
sdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdf)


class TaskCLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.context = self.root / "connection.json"
        self.calls = []
        self.protocol = 1
        self.application_root = str(self.root)
        self.job_status = "done"
        self.legacy = False
        self.failure = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.do_GET()

            def do_GET(self):
                owner.calls.append((self.command, self.path, dict(self.headers)))
                parsed = urlsplit(self.path)
                path = parsed.path
                status = 200
                if path == "/api/health":
                    value = {"application_root": owner.application_root, "protocol_version": owner.protocol,
                             "app_version": "3.7.0", "private_token": "health-secret-never-save"}
                elif path == "/api/doctor":
                    value = {"ready": False, "missing": ["model"], "read_only": True}
                elif path == "/api/capabilities":
                    value = {"protocol_version": 1, "workflows": ["T2VA"]}
                elif path == "/api/jobs/page":
                    value = {"items": [], "query": parse_qs(parsed.query)}
                elif path.endswith("/events"):
                    value = {"events": [], "after": parse_qs(parsed.query).get("after")}
                elif path == "/api/jobs/old":
                    if owner.failure:
                        status, value = owner.failure
                    elif owner.legacy:
                        status, value = 404, {"detail": "Not Found"}
                    else:
                        value = {"id": "old", "project_id": "", "kind": "image", "status": owner.job_status}
                elif path == "/api/jobs/missing":
                    status, value = 404, {"code": "job_not_found", "message": "任务不存在", "retryable": False}
                elif path == "/api/jobs":
                    value = [{"id": "old", "project_id": "", "kind": "environment", "status": "done"}] if owner.legacy else []
                elif path == "/api/structured-error":
                    status, value = 422, {"code": "invalid_request", "message": "缺少字段", "field": "input",
                                          "uid": "shot-1", "retryable": False, "next_actions": ["补齐 input"],
                                          "details": [{"field": "input", "type": "missing", "message": "必填",
                                                       "input": "never-echo-secret", "ctx": {"api_key": "secret"}}],
                                          "input": "never-echo-secret", "private_token": "secret"}
                elif path == "/api/legacy-error":
                    status, value = 400, {"error": "never-echo-secret", "detail": [{"input": "never-echo-secret"}]}
                elif path == "/api/headers":
                    value = {"idempotency_key": self.headers.get("Idempotency-Key")}
                else:
                    status, value = 404, {"detail": "Not Found"}
                payload = json.dumps(value).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temporary.cleanup()

    def run_cli(self, *arguments, base_url=True):
        options = ["--context", str(self.context)]
        if base_url:
            options += ["--base-url", self.url]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = sdf.main(options + list(arguments))
        return code, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_connect_binds_only_verified_identity_and_no_secrets(self):
        code, output = self.run_cli("connect", "--app", str(self.root))
        self.assertEqual(code, 0)
        self.assertTrue(output[0]["connected"])
        context = json.loads(self.context.read_text(encoding="utf-8"))
        self.assertEqual(context["base_url"], self.url)
        self.assertEqual(context["protocol_version"], 1)
        self.assertNotIn("secret", self.context.read_text(encoding="utf-8"))
        before = self.context.read_bytes()
        self.application_root = str(self.root / "different")
        code, output = self.run_cli("connect", "--app", str(self.root))
        self.assertEqual((code, output[0]["code"]), (1, "instance_mismatch"))
        self.assertEqual(self.context.read_bytes(), before)

    def test_unsupported_protocol_and_saved_context_identity_checked(self):
        self.protocol = 99
        code, output = self.run_cli("connect", "--app", str(self.root))
        self.assertEqual((code, output[0]["code"]), (1, "unsupported_protocol"))
        self.assertFalse(self.context.exists())
        self.protocol = 1
        self.run_cli("connect", "--app", str(self.root))
        code, output = self.run_cli("doctor", base_url=False)
        self.assertEqual((code, output[0]["read_only"]), (0, True))
        self.application_root = str(self.root / "another")
        code, output = self.run_cli("capabilities", base_url=False)
        self.assertEqual((code, output[0]["code"]), (1, "instance_mismatch"))
        self.assertFalse(any(method != "GET" for method, _, _ in self.calls))

    def test_read_commands_and_exact_non_project_job_watch(self):
        for command in ("doctor", "capabilities"):
            self.assertEqual(self.run_cli(command)[0], 0)
        code, output = self.run_cli("job", "get", "old")
        self.assertEqual((code, output[0]["kind"]), (0, "image"))
        code, output = self.run_cli("job", "watch", "old")
        self.assertEqual((code, output[0]["job_status"]), (0, "done"))
        self.assertFalse(any(path == "/api/jobs" or path.startswith("/api/project/") for _, path, _ in self.calls))
        self.job_status = "running"
        self.assertEqual(self.run_cli("job", "watch", "old", "--seconds", "0.01")[0], 3)

    def test_pagination_and_event_cursor_are_forwarded(self):
        code, output = self.run_cli("job", "list", "--project", "project-1", "--status", "queued",
                                    "--limit", "17", "--before", "cursor:value")
        self.assertEqual(code, 0)
        self.assertEqual(output[0]["query"], {"project_id": ["project-1"], "status": ["queued"],
                                            "limit": ["17"], "before": ["cursor:value"]})
        code, output = self.run_cli("job", "events", "old", "--after", "12")
        self.assertEqual((code, output[0]["after"]), (0, ["12"]))

    def test_missing_job_is_unknown_and_only_404_uses_legacy_fallback(self):
        self.assertEqual(self.run_cli("job", "get", "missing")[0], 4)
        self.assertFalse(any(path == "/api/jobs" for _, path, _ in self.calls))
        self.legacy = True
        self.assertEqual(self.run_cli("job", "get", "old")[0], 0)
        self.assertTrue(any(path == "/api/jobs" for _, path, _ in self.calls))
        self.calls.clear()
        self.failure = (503, {"code": "unavailable", "message": "temporarily unavailable"})
        self.assertEqual(self.run_cli("job", "get", "old")[0], 1)
        self.assertEqual(len(self.calls), 1)

    def test_safe_structured_errors_and_request_headers(self):
        client = factory.Client(self.url)
        with self.assertRaises(factory.APIError) as caught:
            client.request("POST", "/api/structured-error", {})
        error = caught.exception
        self.assertEqual(error.http_status, 422)
        self.assertEqual(error.payload["code"], "invalid_request")
        self.assertEqual(error.payload["details"], [{"field": "input", "type": "missing", "message": "必填"}])
        self.assertEqual(error.payload["next_actions"], ["补齐 input"])
        self.assertNotIn("secret", json.dumps(error.payload))
        with self.assertRaises(factory.APIError) as caught:
            client.request("GET", "/api/legacy-error")
        self.assertNotIn("secret", json.dumps(caught.exception.payload))
        self.assertEqual(client.request("POST", "/api/headers", {}, headers={"Idempotency-Key": "test-1"}),
                         {"idempotency_key": "test-1"})

    def test_argument_errors_are_json_and_copied_scripts_need_no_repository(self):
        code, output = self.run_cli("job", "list", "--limit", "0")
        self.assertEqual((code, output[0]["code"]), (1, "invalid_arguments"))
        portable = self.root / "portable"
        portable.mkdir()
        for name in ("sdf.py", "factory_api.py"):
            shutil.copyfile(SCRIPTS / name, portable / name)
        result = subprocess.run([sys.executable, str(portable / "sdf.py"), "--base-url", self.url,
                                 "job", "watch", "old"], cwd=self.root, text=True, encoding="utf-8",
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["job_status"], "done")

    def test_copied_cli_works_with_isolated_interpreter_and_sibling_import(self):
        portable = self.root / "independent-skill"
        portable.mkdir()
        for name in ("sdf.py", "factory_api.py"):
            shutil.copyfile(SCRIPTS / name, portable / name)
        # The caller's directory must never supply the companion module.
        (self.root / "factory_api.py").write_text(
            "raise RuntimeError('untrusted working-directory module imported')\n", encoding="utf-8")
        command = [sys.executable, "-I", str(portable / "sdf.py")]
        options = {"cwd": self.root, "text": True, "encoding": "utf-8", "capture_output": True,
                   "timeout": 10, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        help_result = subprocess.run(command + ["--help"], **options)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("deliver", help_result.stdout)
        self.assertEqual(self.calls, [])
        result = subprocess.run(command + ["--base-url", self.url, "job", "get", "old"], **options)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["id"], "old")
        self.assertEqual([path for _, path, _ in self.calls], ["/api/jobs/old"])


if __name__ == "__main__":
    unittest.main()
