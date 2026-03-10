#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


YEAR_PREFIX = re.compile(r"^\s*(19|20)\d{2}[_-]+")


def normalize_site_id(site_id: str) -> str:
    value = (site_id or "").strip()
    value = YEAR_PREFIX.sub("", value)
    value = value.replace("_", "")
    value = value.replace("-", "")
    return value


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def fetch_sites(script_dir: Path, org: str, out_file: Path) -> None:
    deploy_dir = script_dir.parent / "deploy"
    env = os.environ.copy()
    env["VERIFY_SITES_ORG"] = org
    env["VERIFY_SITES_OUT"] = str(out_file)
    env["VERIFY_SITES_RAW_OUT"] = str(out_file.with_suffix(out_file.suffix + ".raw"))
    shell_script = f"""
set -euo pipefail
source "{deploy_dir / 'config.sh'}"
source "{deploy_dir / 'outputs.env'}"
source "{deploy_dir / 'test-credentials.env'}"

if [ -z "${{COGNITO_POOL_ID:-}}" ] || [ -z "${{COGNITO_CLIENT_ID:-}}" ]; then
  echo "Missing Cognito config." >&2
  echo "Set COGNITO_POOL_ID and COGNITO_CLIENT_ID in the environment, or fix deploy/config.sh auth_config loading." >&2
  exit 1
fi

mkdir -p "$(dirname "$VERIFY_SITES_OUT")"

TOKEN=$(aws cognito-idp initiate-auth \
  --client-id "$COGNITO_CLIENT_ID" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters "USERNAME=${{TEST_USERNAME}},PASSWORD=${{TEST_PASSWORD}}" \
  --region "$AWS_REGION" \
  --query 'AuthenticationResult.IdToken' \
  --output text)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "None" ]; then
  echo "Failed to obtain auth token" >&2
  exit 1
fi

curl -sS -f "${{APIGW_URL}}/api/sites/${{VERIFY_SITES_ORG}}?bucket=fomomon" \
  -H "Authorization: Bearer $TOKEN" \
  > "$VERIFY_SITES_RAW_OUT"

python3 - <<'PY'
import json
import os
import pathlib
import sys

raw_path = pathlib.Path(os.environ["VERIFY_SITES_RAW_OUT"])
out_path = pathlib.Path(os.environ["VERIFY_SITES_OUT"])
raw_text = raw_path.read_text()

try:
    parsed = json.loads(raw_text)
except json.JSONDecodeError as exc:
    preview = raw_text[:1000]
    print(f"/api/sites/{{os.environ['VERIFY_SITES_ORG']}} did not return valid JSON: {{exc}}", file=sys.stderr)
    if preview:
        print("Raw response preview:", file=sys.stderr)
        print(preview, file=sys.stderr)
    else:
        print("Raw response was empty.", file=sys.stderr)
    sys.exit(1)

out_path.write_text(json.dumps(parsed, indent=2) + "\\n")
raw_path.unlink(missing_ok=True)
PY
"""
    subprocess.run(["bash", "-lc", shell_script], check=True, env=env)


def load_db_sites(db_path: Path) -> dict[str, set[str]]:
    rows = json.loads(db_path.read_text())
    by_canonical: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        raw_id = row.get("siteId", "")
        by_canonical[normalize_site_id(raw_id)].add(raw_id)
    return dict(by_canonical)


def load_sites_config(sites_path: Path) -> dict[str, set[str]]:
    payload = json.loads(sites_path.read_text())
    items = payload.get("sites", [])
    by_canonical: dict[str, set[str]] = defaultdict(set)
    for item in items:
        raw_id = item.get("id", "")
        by_canonical[normalize_site_id(raw_id)].add(raw_id)
    return dict(by_canonical)


def format_mapping(title: str, mapping: dict[str, set[str]]) -> list[str]:
    lines = [title]
    if not mapping:
        lines.append("- none")
        return lines
    for canonical in sorted(mapping):
        raw_ids = sorted(mapping[canonical])
        for raw_id in raw_ids:
            alias_marker = " (alias)" if raw_id != canonical else ""
            lines.append(f"- {raw_id} -> {canonical}{alias_marker}")
    return lines


def format_diff(title: str, source: dict[str, set[str]], other: dict[str, set[str]]) -> list[str]:
    lines = [title]
    missing = sorted(set(source) - set(other))
    if not missing:
        lines.append("- none")
        return lines
    for canonical in missing:
        raw_ids = ", ".join(sorted(source[canonical]))
        lines.append(f"- {canonical} (raw ids: {raw_ids})")
    return lines


def write_report(report_path: Path, org: str, db_sites: dict[str, set[str]], sites_config: dict[str, set[str]]) -> None:
    alias_note = [
        f"Site verification report for org={org}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Aliasing / canonicalization rule:",
        "- strip a leading year prefix like 2024_ or 2019-",
        "- remove underscores and dashes",
        "- compare normalized ids after that transformation",
        "",
    ]
    sections = []
    sections.extend(format_mapping("db.json raw site ids -> canonical ids", db_sites))
    sections.append("")
    sections.extend(format_mapping("sites.json raw site ids -> canonical ids", sites_config))
    sections.append("")
    sections.extend(format_diff("Present in db.json but missing from sites.json", db_sites, sites_config))
    sections.append("")
    sections.extend(format_diff("Present in sites.json but missing from db.json", sites_config, db_sites))
    sections.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(alias_note + sections) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch /api/sessions and /api/sites for an org, normalize site ids, and report differences."
    )
    parser.add_argument("--org", required=True, help="Organization id, for example ncf or t4gc")
    parser.add_argument("--db-out", help="Path for the fetched sessions json")
    parser.add_argument("--sites-out", help="Path for the fetched sites json")
    parser.add_argument("--report-out", help="Path for the human-readable diff report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    db_out = Path(args.db_out) if args.db_out else script_dir / "photomon" / f"db.{args.org}.fresh.json"
    sites_out = Path(args.sites_out) if args.sites_out else script_dir / "photomon" / f"sites.{args.org}.fresh.json"
    report_out = Path(args.report_out) if args.report_out else script_dir / "photomon" / f"site_diff.{args.org}.txt"

    get_db = script_dir / "get_db.sh"
    run_command([str(get_db), "--org", args.org, "--out", str(db_out)])
    fetch_sites(script_dir, args.org, sites_out)

    db_sites = load_db_sites(db_out)
    sites_config = load_sites_config(sites_out)
    write_report(report_out, args.org, db_sites, sites_config)

    print(f"Wrote {db_out}")
    print(f"Wrote {sites_out}")
    print(f"Wrote {report_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
