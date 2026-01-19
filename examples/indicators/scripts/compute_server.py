import json
import os
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"
STANDARDS_DIR = BASE_DIR / "standards"


def sanitize_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def build_prompt(request_payload: dict) -> str:
    schema = (STANDARDS_DIR / "computed_variables.schema.json").read_text(encoding="utf-8")
    request_text = json.dumps(request_payload, indent=2)
    return (
        "# Role\n"
        "You generate a computed variable formula from plain English intent.\n\n"
        "# Instructions\n"
        "- Use the request JSON below as the sole source of truth.\n"
        "- The output must use the exact computed_variable_name from the request.\n"
        "- The output english_intent must match the request english_intent.\n"
        "- Use the request inputs list as the computed variable inputs.\n"
        "- Prefer JSONLogic if possible. Use JS only when needed.\n"
        "- Output must be valid JSON and nothing else.\n\n"
        "# Strict Output Rules\n"
        "1. Return ONLY valid, raw JSON.\n"
        "2. NO markdown code blocks.\n"
        "3. NO conversational filler.\n"
        "4. Output must start with '{' and end with '}'.\n\n"
        "# Request JSON\n"
        f"{request_text}\n\n"
        "# Output Schema\n"
        f"{schema}\n\n"
        "# Notes\n"
        "Return only one computed variable in computed_variables[].\n"
        "If you cannot produce a formula, return compiled.code as \"UNKNOWN\" and status \"draft\".\n"
    )


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, {"ok": True})

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/compute":
            self._send(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length) or b"{}"
            payload = json.loads(raw_body)
        except Exception:
            try:
                body_preview = raw_body.decode("utf-8", errors="replace")
            except Exception:
                body_preview = "<unreadable>"
            print("Invalid JSON payload:", body_preview)
            self._send(400, {"error": "invalid json", "raw_body": body_preview})
            return

        print("Compute request payload:", json.dumps(payload, indent=2))

        prompt = build_prompt(payload)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            prompt_path = tmpdir_path / "prompt.md"
            request_path = tmpdir_path / "request.json"
            prompt_path.write_text(prompt, encoding="utf-8")
            request_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            try:
                result = subprocess.run(
                    [str(SCRIPTS_DIR / "run_agent.sh"), str(prompt_path), str(request_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                self._send(500, {"error": exc.stderr.strip() or "agent failed", "stdout": exc.stdout.strip()})
                return

        try:
            text = sanitize_json(result.stdout)
            data = json.loads(text)
        except Exception:
            self._send(500, {"error": "agent returned invalid json", "stdout": result.stdout.strip()})
            return

        print("Compute response:", json.dumps(data, indent=2))
        self._send(200, data)


def main():
    host = os.environ.get("INDICATOR_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("INDICATOR_SERVER_PORT", "8765"))
    server = HTTPServer((host, port), Handler)
    print(f"Indicator compute server running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
