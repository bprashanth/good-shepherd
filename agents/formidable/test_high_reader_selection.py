#!/usr/bin/env python3
"""Truth-free fallback selection must ignore small coverage noise."""
import high_worker


class FakeCanonical:
    @staticmethod
    def resolve(document):
        document["resolved"] = True


def document(terra_count, luna_count):
    fields = []
    for index in range(max(terra_count, luna_count)):
        fields.append({
            "readings": [
                {"model": "codex:gpt-5.6-terra",
                 "value": "x" if index < terra_count else None},
                {"model": "codex:gpt-5.6-luna",
                 "value": "x" if index < luna_count else None},
            ],
        })
    return {
        "models": ["codex:gpt-5.6-terra", "codex:gpt-5.6-luna"],
        "pages": [{"metadata_fields": fields, "free_text_regions": [], "tables": []}],
    }


def main_test():
    selected, model, coverage = high_worker._select_complete_reader(
        document(100, 105), FakeCanonical)
    assert model == "codex:gpt-5.6-terra"
    assert selected["models"][0] == model
    assert coverage["codex:gpt-5.6-luna"] == 105

    selected, model, _coverage = high_worker._select_complete_reader(
        document(100, 111), FakeCanonical)
    assert model == "codex:gpt-5.6-luna"
    assert selected["models"][0] == model

    healthy = document(100, 105)
    healthy["models"] = ["codex:agentic-low", *healthy["models"]]
    for item in healthy["pages"][0]["metadata_fields"]:
        item["readings"].insert(0, {
            "model": "codex:agentic-low", "value": "x",
        })
        item["status"] = "agreement"
    evidence = high_worker._primary_routing_evidence(healthy)
    assert evidence["primary_literal_coverage"] == 1.0
    assert evidence["peer_consensus_conflict_fraction"] == 0.0
    assert evidence["strongest_peer_recovery_fraction"] == 0.0

    collapsed = document(100, 120)
    collapsed["models"] = ["codex:agentic-low", *collapsed["models"]]
    for index, item in enumerate(collapsed["pages"][0]["metadata_fields"]):
        item["readings"].insert(0, {
            "model": "codex:agentic-low", "value": "x" if index < 60 else None,
        })
        item["status"] = "peer_consensus_disagreement" if index < 30 else "agreement"
    evidence = high_worker._primary_routing_evidence(collapsed)
    assert evidence["primary_literal_coverage"] == 0.5
    assert evidence["peer_consensus_conflict_fraction"] == 0.25
    assert evidence["strongest_peer_recovery_fraction"] == 1.0

    recovered = document(100, 150)
    recovered["models"] = ["codex:agentic-low", *recovered["models"]]
    for index, item in enumerate(recovered["pages"][0]["metadata_fields"]):
        item["readings"].insert(0, {
            "model": "codex:agentic-low", "value": "x" if index < 125 else None,
        })
        item["status"] = "peer_split"
    evidence = high_worker._primary_routing_evidence(recovered)
    assert evidence["strongest_peer_recovery_fraction"] == 0.2
    assert evidence["strongest_peer_lead_fraction"] == 0.5


if __name__ == "__main__":
    main_test()
