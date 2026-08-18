#!/usr/bin/env python3
"""Static release invariants that require no AWS credentials or network."""
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEPLOY = ROOT / "deploy"


def text(path: Path) -> str:
    return path.read_text()


def main_test():
    dockerfile = text(ROOT / "Dockerfile.high")
    assert "--from=pipeline" not in dockerfile
    assert "COPY high_pipeline ./high_pipeline" in dockerfile

    low_push = text(DEPLOY / "push.sh")
    assert "push_secrets.sh" not in low_push
    assert "FARGATE_TASK_HIGH=${HIGH_FARGATE_TASK_DEF}" in low_push
    assert low_push.count("--platform linux/amd64") >= 3
    assert '"cpuArchitecture":"X86_64"' in low_push

    high_push = text(DEPLOY / "push_high.sh")
    assert "FORMID_REPO" not in high_push
    assert "HIGH_SKIP_HANDLER" in high_push
    assert "--platform linux/arm64" in high_push

    credentials = text(DEPLOY / "deploy_credentials.sh")
    assert "verify_prod.sh" in credentials and "verify_high.sh" in credentials
    assert "rollback_secret.sh" in credentials

    low = text(DEPLOY / "deploy_low.sh")
    assert "assert_high_unchanged" in low
    assert "verify_prod.sh" in low and "verify_high.sh" in low

    high = text(DEPLOY / "deploy_high.sh")
    assert "assert_low_unchanged" in high
    assert "verify_prod.sh" in high and "verify_high.sh" in high

    all_tiers = text(DEPLOY / "deploy_all.sh")
    assert "HIGH_SKIP_HANDLER=1" in all_tiers
    assert "verify_prod.sh" in all_tiers and "verify_high.sh" in all_tiers


if __name__ == "__main__":
    main_test()
