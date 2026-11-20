"""Explicit offline test of installed Gemini CLI; no packages/provider access.

Run on Linux with GEMINI_CLI_OFFLINE_TEST=1 and native node/gemini on PATH.
The CLI receives a temporary HOME, fake scoped key, and a Node network guard.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from sqlalchemy import select

from src.research_platform.database import Database, ModelUsage, Project, Run
from src.research_platform.ledger import refresh_usage
from src.research_platform.gateway_client import prepare_cli_environment
from src.research_platform.model_gateway import GatewaySettings, create_gateway_app, issue_grant
from src.research_platform.schemas import Budgets

pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or os.getenv("GEMINI_CLI_OFFLINE_TEST") != "1",
    reason="Explicit opt-in installed CLI protocol test",
)

GUARD = r"""
const fs = require('node:fs');
const net = require('node:net');
const http = require('node:http');
const https = require('node:https');
function allow(host, port) {
  if (host === '127.0.0.1' && Number(port) === Number(process.env.GATEWAY_TEST_PORT)) return;
  fs.appendFileSync(process.env.GATEWAY_TEST_BLOCK_LOG, JSON.stringify({host:String(host),port:String(port)})+'\n');
  throw Error('Offline CLI test blocked external network');
}
const originalFetch = globalThis.fetch;
globalThis.fetch = function(input, options) {
  const u = new URL(typeof input === 'string' || input instanceof URL ? input : input.url);
  if (u.protocol === 'data:' || u.protocol === 'file:') return originalFetch.call(this,input,options);
  allow(u.hostname, u.port || (u.protocol === 'https:' ? 443 : 80));
  return originalFetch.call(this,input,options);
};
for (const mod of [http, https]) {
  const original = mod.request;
  mod.request = function(...args) {
    let item=args[0];
    if(typeof item==='string'||item instanceof URL) { const u=new URL(item); allow(u.hostname,u.port||(u.protocol==='https:'?443:80)); }
    else allow(item.hostname||item.host||'localhost',item.port||(mod===https?443:80));
    return original.apply(this,args);
  };
}
const connect=net.Socket.prototype.connect;
net.Socket.prototype.connect=function(...args) {
  let item=Array.isArray(args[0])?args[0][0]:args[0];
  if(typeof item==='object') allow(item.host||item.hostname||'localhost',item.port);
  else allow(typeof args[1]==='string'?args[1]:'localhost',item);
  return connect.apply(this,args);
};
"""


@pytest.mark.parametrize("tool_roundtrip", [False, True])
def test_installed_gemini_cli_uses_fake_scoped_key_and_gateway_sse(tmp_path, tool_roundtrip):
    node, gemini = shutil.which("node"), shutil.which("gemini")
    assert node and gemini, "Use the existing native Node/Gemini installation"
    entry = Path(gemini).resolve()
    package = json.loads((entry.parent.parent / "package.json").read_text())
    assert package["version"] == "0.68.0", "Record and review any CLI version change"
    database = Database(f"sqlite:///{(tmp_path / 'cli.db').as_posix()}")
    database.migrate()
    with database.sessions.begin() as session:
        project = Project(
            title="Offline CLI protocol",
            question="Does the CLI use the local mock gateway?",
            domain="Protocol test",
        )
        session.add(project)
        session.flush()
        run = Run(
            project_id=project.id,
            status="running",
            profile="full_research",
            provider="gemini",
            model="gemini-2.5-flash",
            config={"engine": "original", "budgets": Budgets(max_input_tokens=250000).model_dump()},
        )
        session.add(run)
        session.flush()
        refresh_usage(session, run)
        run_id = run.id
    _, token = issue_grant(
        database, run_id, allowed_models=["gemini-2.5-flash"], max_output_tokens=128
    )
    dispatches = []

    async def fake_provider(request):
        payload = json.loads(request.content)
        has_function_response = any(
            "functionResponse" in part
            for content in payload.get("contents", [])
            for part in content.get("parts", [])
        )
        dispatches.append(
            {
                "method": request.method,
                "path": request.url.path,
                "request_bytes": len(request.content),
                "function_response": has_function_response,
            }
        )
        assert request.headers["x-goog-api-key"] == "fixture-provider-key-never-real"
        body = {
            "candidates": [
                {
                    "content": {"role": "model", "parts": [{"text": "OK"}]},
                    "finishReason": "STOP",
                    "index": 0,
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 1,
                "totalTokenCount": 11,
            },
            "modelVersion": "gemini-2.5-flash",
        }
        if tool_roundtrip and len(dispatches) == 1:
            body["candidates"][0]["content"]["parts"] = [
                {"functionCall": {"name": "list_directory", "args": {"dir_path": "."}}}
            ]
        if request.url.path.endswith("streamGenerateContent"):
            return httpx.Response(
                200,
                content=("data: " + json.dumps(body) + "\n\n").encode(),
                headers={"content-type": "text/event-stream"},
            )
        return httpx.Response(200, json=body)

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(fake_provider))
    app = create_gateway_app(
        database,
        GatewaySettings(enabled=True, provider_key="fixture-provider-key-never-real"),
        client=upstream,
    )
    operations = []

    @app.middleware("http")
    async def record(request, call_next):
        response = await call_next(request)
        operations.append(
            {"method": request.method, "path": request.url.path, "status": response.status_code}
        )
        return response

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started
    home, work = tmp_path / "home", tmp_path / "work"
    home.mkdir()
    work.mkdir()
    scoped = prepare_cli_environment(
        home, f"http://127.0.0.1:{port}/runs/{run_id}", token, allow_loopback_http=True
    )
    guard, blocked = tmp_path / "guard.cjs", tmp_path / "blocked.jsonl"
    guard.write_text(GUARD)
    env = {
        "PATH": str(Path(node).parent) + ":/usr/bin:/bin",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "config"),
        "GEMINI_API_KEY": token,
        "GOOGLE_GEMINI_BASE_URL": f"http://127.0.0.1:{port}/runs/{run_id}",
        "GEMINI_TELEMETRY_ENABLED": "false",
        "NODE_OPTIONS": f"--require={guard}",
        "GATEWAY_TEST_PORT": str(port),
        "GATEWAY_TEST_BLOCK_LOG": str(blocked),
        "LANG": "C.UTF-8",
        **scoped,
    }
    try:
        result = subprocess.run(
            [
                node,
                str(entry),
                "--skip-trust",
                "--prompt",
                "Reply with OK.",
                "--model",
                "gemini-2.5-flash",
                "--output-format",
                "stream-json",
                "--approval-mode",
                "default",
            ],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        safe_output = (result.stdout + result.stderr).replace(token, "[scoped-token]")
        assert result.returncode == 0, safe_output[-4000:] + json.dumps(operations)
        assert '"OK"' in result.stdout or '"content":"OK"' in result.stdout.replace(" ", ""), (
            safe_output[-4000:]
        )
        assert dispatches and len(dispatches) <= 20
        if tool_roundtrip:
            assert any(item["function_response"] for item in dispatches), safe_output[-4000:]
        assert any(item["path"].endswith("streamGenerateContent") for item in dispatches)
        assert not blocked.exists(), blocked.read_text() if blocked.exists() else ""
        with database.sessions() as session:
            usage = list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == run_id)))
            assert len(usage) == len(dispatches)
            assert all(row.status == "completed" and row.estimated_cost is None for row in usage)
        # No credential or prompt bodies in the retained protocol report.
        (tmp_path / "cli-compatibility.json").write_text(
            json.dumps(
                {
                    "version": package["version"],
                    "exit_code": result.returncode,
                    "dispatches": dispatches,
                    "operations": operations,
                    "external_connections": 0,
                },
                indent=2,
            )
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        database.engine.dispose()
