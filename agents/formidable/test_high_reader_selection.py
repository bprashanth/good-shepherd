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


if __name__ == "__main__":
    main_test()
