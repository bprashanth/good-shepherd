#!/usr/bin/env python3
import argparse
import datetime as dt
import re
import subprocess
import sys
from dataclasses import dataclass


BUCKET = "fomomon"
ORG = "ncf"


@dataclass(frozen=True)
class SiteConfig:
    canonical_id: str
    source_prefix: str
    selection_mode: str  # "single" or "paired"


SITE_CONFIGS = [
    SiteConfig("H13R1", f"s3://{BUCKET}/{ORG}/archive/2024/2024-H13/R1/", "single"),
    SiteConfig("J12R1", f"s3://{BUCKET}/{ORG}/J12R1/", "paired"),
    SiteConfig("P1R1", f"s3://{BUCKET}/{ORG}/archive/2019/2019-P1R1-Reference/2019_P1R1/", "single"),
    SiteConfig("P1R2", f"s3://{BUCKET}/{ORG}/archive/2019/2019-P1R2-Reference/2019_P1R2/", "single"),
    SiteConfig("P2R1", f"s3://{BUCKET}/{ORG}/archive/2019/2019-P2R1-Reference/2019_P2R1/", "single"),
    SiteConfig("P2R2", f"s3://{BUCKET}/{ORG}/archive/2019/2019-P2R2-Reference/2019_P2R2/", "single"),
    SiteConfig("G14R1-2025", f"s3://{BUCKET}/{ORG}/G14R1-2025/", "paired"),
]

ARCHIVE_DATE_RE = re.compile(r"(?P<year>20\d{2})-(?P<month>\d{2})-")
PAIR_RE = re.compile(
    r".+?_(?P<stamp>20\d{2}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}(?:\.\d+)?)_(?P<kind>portrait|landscape)\.(?P<ext>jpg|jpeg|JPG|JPEG)$"
)


def run_aws(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, capture_output=True)


def list_filenames(prefix: str) -> list[str]:
    result = run_aws(["aws", "s3", "ls", prefix])
    names = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            names.append(parts[-1])
    return names


def object_exists(uri: str) -> bool:
    result = subprocess.run(["aws", "s3", "ls", uri], text=True, capture_output=True)
    return result.returncode == 0 and bool(result.stdout.strip())


def pick_oldest_single(names: list[str]) -> str:
    dated = []
    for name in names:
        match = ARCHIVE_DATE_RE.search(name)
        if match:
            dated.append((int(match.group("year")), int(match.group("month")), name))
    if not dated:
        raise ValueError("No dated image filenames found")
    dated.sort()
    return dated[0][2]


def parse_pair_timestamp(stamp: str) -> dt.datetime:
    return dt.datetime.strptime(stamp, "%Y-%m-%dT%H_%M_%S.%f")


def pick_oldest_pair(names: list[str]) -> tuple[str, str]:
    groups: dict[str, dict[str, str]] = {}
    for name in names:
        match = PAIR_RE.match(name)
        if not match:
            continue
        stamp = match.group("stamp")
        kind = match.group("kind")
        groups.setdefault(stamp, {})[kind] = name

    complete = []
    for stamp, group in groups.items():
        if "portrait" in group and "landscape" in group:
            complete.append((parse_pair_timestamp(stamp), group["portrait"], group["landscape"]))

    if not complete:
        raise ValueError("No complete portrait/landscape image pairs found")

    complete.sort(key=lambda item: item[0])
    _, portrait, landscape = complete[0]
    return portrait, landscape


def maybe_copy(src: str, dest: str, apply: bool) -> None:
    if src == dest:
        print(f"SKIP same source and destination: {src}")
        return

    if object_exists(dest):
        print(f"SKIP destination exists: {dest}")
        return

    cmd = ["aws", "s3", "cp", src, dest]
    if not apply:
        print("DRY-RUN", " ".join(cmd))
        return

    print("COPY", " ".join(cmd))
    subprocess.run(cmd, check=True)


def process_site(site: SiteConfig, apply: bool) -> None:
    names = list_filenames(site.source_prefix)
    dest_prefix = f"s3://{BUCKET}/{ORG}/{site.canonical_id}/"

    print(f"\n[{site.canonical_id}]")
    print(f"source: {site.source_prefix}")
    print(f"dest:   {dest_prefix}")
    print(f"mode:   {site.selection_mode}")

    if site.selection_mode == "single":
        selected = pick_oldest_single(names)
        print(f"selected earliest dated image: {selected}")
        src = f"{site.source_prefix}{selected}"
        dest = f"{dest_prefix}{selected}"
        maybe_copy(src, dest, apply)
        print(f"reference_portrait/reference_landscape -> {site.canonical_id}/{selected}")
        return

    portrait, landscape = pick_oldest_pair(names)
    print(f"selected oldest pair: {portrait} | {landscape}")
    maybe_copy(f"{site.source_prefix}{portrait}", f"{dest_prefix}{portrait}", apply)
    maybe_copy(f"{site.source_prefix}{landscape}", f"{dest_prefix}{landscape}", apply)
    print(f"reference_portrait -> {site.canonical_id}/{portrait}")
    print(f"reference_landscape -> {site.canonical_id}/{landscape}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy oldest reference images into canonical S3 prefixes without overwriting existing objects."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform aws s3 cp operations. Without this flag, print the planned copy commands only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.apply:
        print("Applying copies. Existing destination objects will be skipped.")
    else:
        print("Dry run. No objects will be copied.")
    print("single = one earliest dated archive image reused for portrait+landscape")
    print("paired = earliest complete portrait/landscape timestamp pair")

    for site in SITE_CONFIGS:
        process_site(site, args.apply)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or str(exc), file=sys.stderr)
        sys.exit(exc.returncode)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
