#!/usr/bin/env python3
"""
Run Good Shepherd example stacks: localhost services for PWAs, wizards, forms,
compute server, Alienwise, etc. Default: research (new + ingested) + rewild.

Hub landing pages (research/web, web_2, rewild/web) use file:// — open the paths
printed at startup in your browser; do not serve those HTML trees over localhost
for the hub itself.

Run from repo root:
  ./.venv/bin/python examples/stacks/run_stacks.py

Ctrl+C stops all child processes; next run frees ports before restart.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Repo root: examples/stacks/run_stacks.py -> parents[2]
ROOT = Path(__file__).resolve().parent.parent.parent
RESEARCH = ROOT / "examples" / "stacks" / "research"
REWILD = ROOT / "examples" / "stacks" / "rewild"
COMMUNITY = ROOT / "examples" / "stacks" / "community"


def _file_uri(path: Path) -> str:
    """Stable file:// URL for a path under the repo (use for static hub pages)."""
    return path.resolve().as_uri()


def _die(msg: str, code: int = 1) -> None:
    print(f"[bootstrap] ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def _python() -> Path:
    venv = ROOT / ".venv" / "bin" / "python"
    if venv.is_file():
        return venv
    return Path(sys.executable)


def _free_port(port: int) -> None:
    """Best-effort: stop any process listening on TCP `port` (Linux fuser / lsof)."""
    try:
        subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f":{port}"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return
    for line in out.strip().splitlines():
        try:
            pid = int(line.strip())
        except ValueError:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _validate_research() -> None:
    required = [
        RESEARCH / "alienwise" / "alienwise_viewer.html",
        RESEARCH / "indicators" / "scripts" / "compute_server.py",
        RESEARCH / "web" / "index.html",
        RESEARCH / "pwa" / "index.html",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        _die(
            "Research stack is incomplete (expected in-repo components). Missing:\n  "
            + "\n  ".join(missing)
        )


def _validate_rewild() -> None:
    required = [
        REWILD / "web" / "index.html",
        REWILD / "setup_wizard" / "wizard.html",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        _die("Rewild stack is incomplete. Missing:\n  " + "\n  ".join(missing))


def _validate_community() -> None:
    if not (COMMUNITY / "README.md").is_file():
        _die("Community stack path missing: examples/stacks/community/")


ProcessSpec = tuple[str, int, list[str], str, dict | None]

_RESEARCH: list[ProcessSpec] = [
    (
        "research/pwa",
        8001,
        [
            str(_python()),
            "-m",
            "http.server",
            "8001",
            "--bind",
            "0.0.0.0",
            "--directory",
            str(RESEARCH / "pwa"),
        ],
        str(ROOT),
        None,
    ),
    (
        "research/setup_wizard",
        8002,
        [
            str(_python()),
            "-m",
            "http.server",
            "8002",
            "--bind",
            "0.0.0.0",
            "--directory",
            str(RESEARCH / "setup_wizard"),
        ],
        str(ROOT),
        None,
    ),
    (
        "research/setup_wizard_2",
        8004,
        [
            str(_python()),
            "-m",
            "http.server",
            "8004",
            "--bind",
            "0.0.0.0",
            "--directory",
            str(RESEARCH / "setup_wizard_2"),
        ],
        str(ROOT),
        None,
    ),
    (
        "research/indicators_2",
        8005,
        [
            str(_python()),
            "-m",
            "http.server",
            "8005",
            "--bind",
            "0.0.0.0",
            "--directory",
            str(RESEARCH / "indicators_2"),
        ],
        str(ROOT),
        None,
    ),
    (
        "research/forms",
        5173,
        ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"],
        str(RESEARCH / "forms"),
        None,
    ),
    (
        "research/indicators_server",
        8765,
        [str(_python()), "scripts/compute_server.py"],
        str(RESEARCH / "indicators"),
        None,
    ),
    (
        "research/alienwise",
        8080,
        [
            str(_python()),
            "-m",
            "http.server",
            "8080",
            "--bind",
            "0.0.0.0",
            "--directory",
            str(RESEARCH / "alienwise"),
        ],
        str(ROOT),
        None,
    ),
]

_REWILD: list[ProcessSpec] = [
    (
        "rewild/setup_wizard",
        8031,
        [
            str(_python()),
            "-m",
            "http.server",
            "8031",
            "--bind",
            "0.0.0.0",
            "--directory",
            str(REWILD / "setup_wizard"),
        ],
        str(ROOT),
        None,
    ),
    (
        "rewild/pwa",
        8032,
        [
            str(_python()),
            "-m",
            "http.server",
            "8032",
            "--bind",
            "0.0.0.0",
            "--directory",
            str(REWILD / "pwa"),
        ],
        str(ROOT),
        None,
    ),
    (
        "rewild/plantwise",
        8033,
        [
            str(_python()),
            "-m",
            "http.server",
            "8033",
            "--bind",
            "0.0.0.0",
            "--directory",
            str(REWILD / "plantwise"),
        ],
        str(ROOT),
        None,
    ),
    (
        "rewild/indicators",
        8034,
        [
            str(_python()),
            "-m",
            "http.server",
            "8034",
            "--bind",
            "0.0.0.0",
            "--directory",
            str(REWILD / "indicators"),
        ],
        str(ROOT),
        None,
    ),
]


def _dedupe_by_port(specs: list[ProcessSpec]) -> list[ProcessSpec]:
    seen: set[int] = set()
    out: list[ProcessSpec] = []
    for s in specs:
        port = s[1]
        if port in seen:
            continue
        seen.add(port)
        out.append(s)
    return out


def _collect_specs(stacks: set[str]) -> list[ProcessSpec]:
    out: list[ProcessSpec] = []
    if "research" in stacks:
        out.extend(_RESEARCH)
    if "rewild" in stacks:
        out.extend(_REWILD)
    return _dedupe_by_port(out)


def _log(msg: str) -> None:
    print(f"[bootstrap] {msg}", flush=True)


def _spawn(name: str, port: int, argv: list[str], cwd: str, env: dict | None) -> subprocess.Popen:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    _log(f"starting {name} (port {port}): {cwd}: {' '.join(argv)}")
    return subprocess.Popen(
        argv,
        cwd=cwd,
        env=merged,
        stdin=subprocess.DEVNULL,
    )



def _print_url_summary(stacks: set[str]) -> None:
    """Print file:// landing pages + localhost services started by this script."""
    print("", flush=True)
    print("Landing pages (open via file:// — relative links to setup_wizard, indicators, etc. stay on file:):", flush=True)
    if "research" in stacks:
        print(f"  • Research hub: {_file_uri(RESEARCH / 'web' / 'index.html')}")
        print(f"  • Ingest hub: {_file_uri(RESEARCH / 'web_2' / 'index.html')}")
    if "rewild" in stacks:
        print(f"  • Rewild hub: {_file_uri(REWILD / 'web' / 'index.html')}")
    svc: list[str] = []
    if "research" in stacks:
        svc.extend(
            [
                "  • PWA: http://127.0.0.1:8001/",
                "  • Setup wizard (standalone): http://127.0.0.1:8002/",
                "  • Setup wizard 2: http://127.0.0.1:8004/",
                "  • Indicators_2 viewer tree: http://127.0.0.1:8005/",
                "  • Forms: http://127.0.0.1:5173/",
                "  • Indicators API (compute): http://127.0.0.1:8765/",
                "  • Alienwise: http://127.0.0.1:8080/",
            ]
        )
    if "rewild" in stacks:
        svc.extend(
            [
                "  • Rewild setup wizard: http://127.0.0.1:8031/",
                "  • Rewild PWA: http://127.0.0.1:8032/",
                "  • Plantwise: http://127.0.0.1:8033/",
                "  • Rewild indicators UI: http://127.0.0.1:8034/",
            ]
        )
    if svc:
        print("", flush=True)
        print("Nearby services started here (still need http:, e.g. PWA/forms/compute):", flush=True)
        for line in svc:
            print(line, flush=True)
    print("", flush=True)


def _community_notice() -> None:
    _log(
        "community: Docker (Frappe + OpenClaw) is not started by this script. "
        "Use examples/stacks/community/README.md, frappe/docker/, and assistant/docker-compose.yml."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stack",
        action="append",
        dest="stacks",
        choices=["research", "rewild", "community"],
        metavar="NAME",
        help="Stack to run (repeatable). Default: research rewild (not community).",
    )
    args = parser.parse_args()
    if args.stacks:
        stacks: set[str] = set(args.stacks)
    else:
        stacks = {"research", "rewild"}

    if "research" in stacks:
        _validate_research()
    if "rewild" in stacks:
        _validate_rewild()
    if "community" in stacks:
        _validate_community()
        _community_notice()

    specs = _collect_specs(stacks)
    ports = sorted({s[1] for s in specs})
    _log("freeing ports (if in use): " + ", ".join(str(p) for p in ports))
    for p in ports:
        _free_port(p)
    time.sleep(0.3)

    procs: list[subprocess.Popen] = []
    for name, port, argv, cwd, extra_env in specs:
        if not Path(cwd).is_dir():
            for ps in procs:
                if ps.poll() is None:
                    ps.terminate()
            _die(f"missing working directory: {cwd}")
        procs.append(_spawn(name, port, argv, cwd, extra_env))
        time.sleep(0.15)

    if not procs:
        _log("no processes to supervise (select at least one stack with services). Exiting.")
        return

    def shutdown(*_: object) -> None:
        _log("shutting down…")
        for p in procs:
            if p.poll() is None:
                p.terminate()
        deadline = time.time() + 5
        for p in procs:
            while p.poll() is None and time.time() < deadline:
                time.sleep(0.1)
        for p in procs:
            if p.poll() is None:
                try:
                    p.kill()
                except OSError:
                    pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    _log("all services started.")
    _print_url_summary(stacks)
    _log("Press Ctrl+C to stop.")
    while True:
        for p in procs:
            code = p.poll()
            if code is not None:
                _log(f"process exited unexpectedly with {code}, stopping all")
                shutdown()
        time.sleep(0.4)


if __name__ == "__main__":
    main()
