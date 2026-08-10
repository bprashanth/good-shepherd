#!/usr/bin/env python3
"""No-AWS invariant: low stays on its original task; high is additive."""
import main


class FakeECS:
    def __init__(self):
        self.calls = []

    def run_task(self, **kwargs):
        self.calls.append(kwargs)
        return {"tasks": [{"taskArn": "test"}]}


def main_test():
    fake = FakeECS()
    original_ecs, original_subnet, original_sg = main._ecs, main._get_subnet, main._sg_id
    try:
        main._ecs = lambda: fake
        main._get_subnet = lambda: "subnet-test"
        main._sg_id = lambda: "sg-test"
        main._launch_fargate("low", "input.pdf", "low.pdf", "user", effort="low")
        main._launch_fargate("high", "input.pdf", "high.pdf", "user", effort="high")
    finally:
        main._ecs, main._get_subnet, main._sg_id = original_ecs, original_subnet, original_sg

    low, high = fake.calls
    assert low["taskDefinition"] == "formidable-worker"
    assert low["overrides"]["containerOverrides"][0]["name"] == "worker"
    assert high["taskDefinition"] == "formidable-high-worker"
    assert high["overrides"]["containerOverrides"][0]["name"] == "high-worker"
    assert main._item_to_job({"job_id": {"S": "legacy"}})["effort"] == "low"
    assert main._item_to_job({"job_id": {"S": "new"}, "effort": {"S": "high"}})["effort"] == "high"


if __name__ == "__main__":
    main_test()
