"""Tolerant xlsx comparison for the nightly regression suite.

The golden ("standard") xlsx is a human-corrected transcription of a scanned
handwritten field form. Any codex run is a *second* reading of the same messy
handwriting, so exact cell-by-cell equality is meaningless — and the two files
don't even share a sheet layout (the golden uses per-page sheets; codex emits a
single `v2` sheet). So the comparison is deliberately structure-agnostic and
tolerant:

  * All non-empty cells across all sheets are flattened, then split into atomic
    tokens on whitespace/punctuation.
  * Tokens are bucketed into NUMBERS and WORDS.
  * NUMBERS are the reliable signal (a "17" is a "17" regardless of penmanship);
    WORDS are handwritten species/site names with heavy OCR variance, so word
    recall runs perpetually low and is only a lenient gate.
  * Recall is measured against the golden (multiset): "how much of the known-good
    content did this run reproduce". Extra tokens the run added are reported but
    never penalised (so yellow-flag / uncertainty cells don't hurt the score).

The purpose is to catch *regressions* — codex crashing, emptying out, or dropping
whole tables — not to certify transcription accuracy (a human spot-checks the
attached xlsx for that). Thresholds are intentionally loose and overridable via
env so they can be retuned after a few real runs.

Usage (standalone, for local calibration):
    python3 xlsx_diff.py golden.xlsx candidate.xlsx
"""

from __future__ import annotations

import os
import re
from collections import Counter

import openpyxl

# ── Pass thresholds (env-overridable) ──────────────────────────────────────────
# A good real run (agent-vs-human on TreePlots) scored: cell_frac≈0.76,
# num_recall≈0.70, word_recall≈0.47. Defaults sit comfortably below that so a
# healthy run passes but a broken/empty run (codex crash → tiny output) fails.
MIN_CELL_FRAC   = float(os.environ.get("REGRESSION_MIN_CELL_FRAC", "0.50"))
MIN_NUM_RECALL  = float(os.environ.get("REGRESSION_MIN_NUM_RECALL", "0.55"))
MIN_WORD_RECALL = float(os.environ.get("REGRESSION_MIN_WORD_RECALL", "0.30"))

_SPLIT_RE = re.compile(r"[\s,;/|]+")
_NUM_RE   = re.compile(r"-?\d+(?:\.\d+)?")
_STRIP    = " .,:;()%$#*'\"[]"


def _cells(path: str) -> list[str]:
    """Every non-empty cell value across all sheets, as strings."""
    wb = openpyxl.load_workbook(path, data_only=True)
    out: list[str] = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            for c in row:
                if c is not None and str(c).strip():
                    out.append(str(c))
    return out


def _atoms(cells: list[str]) -> tuple[list[float], list[str]]:
    """Split cells into atomic tokens; bucket into (numbers, words)."""
    nums: list[float] = []
    words: list[str] = []
    for cell in cells:
        for tok in _SPLIT_RE.split(str(cell).lower()):
            tok = tok.strip(_STRIP)
            if not tok:
                continue
            if _NUM_RE.fullmatch(tok):
                nums.append(round(float(tok), 2))
            elif len(tok) >= 2:          # drop single stray letters
                words.append(tok)
    return nums, words


def _multiset_recall(golden: list, candidate: list) -> tuple[int, int, float]:
    """Matched-count, golden-total, recall — comparing as multisets."""
    gc, ac = Counter(golden), Counter(candidate)
    matched = sum(min(ac[k], v) for k, v in gc.items())
    total = sum(gc.values())
    return matched, total, (matched / total if total else 1.0)


def compare(golden_path: str, candidate_path: str) -> dict:
    """Compare candidate xlsx against golden. Returns a dict with:
        passed  : bool
        metrics : {...}
        report  : human-readable multi-line str
    """
    g_cells = _cells(golden_path)
    c_cells = _cells(candidate_path)
    g_nums, g_words = _atoms(g_cells)
    c_nums, c_words = _atoms(c_cells)

    cell_frac = (len(c_cells) / len(g_cells)) if g_cells else 1.0
    num_matched, num_total, num_recall   = _multiset_recall(g_nums, c_nums)
    word_matched, word_total, word_recall = _multiset_recall(g_words, c_words)

    checks = {
        "cell_frac":   (cell_frac,   MIN_CELL_FRAC),
        "num_recall":  (num_recall,  MIN_NUM_RECALL),
        "word_recall": (word_recall, MIN_WORD_RECALL),
    }
    failures = [name for name, (val, thr) in checks.items() if val < thr]
    passed = not failures

    # Report: what's missing helps a human decide if a fail is real or drift.
    missing_nums  = sorted((Counter(g_nums)  - Counter(c_nums)).elements())
    missing_words = sorted(set(Counter(g_words) - Counter(c_words)))

    def _pf(name: str) -> str:
        val, thr = checks[name]
        return f"{'PASS' if val >= thr else 'FAIL'}  {name:12s} {val:5.2f}  (min {thr:.2f})"

    lines = [
        f"Regression comparison — {'PASS' if passed else 'FAIL'}",
        "",
        f"  golden cells:    {len(g_cells)}",
        f"  candidate cells: {len(c_cells)}",
        "",
        "  " + _pf("cell_frac"),
        "  " + _pf("num_recall")  + f"   [{num_matched}/{num_total} numbers]",
        "  " + _pf("word_recall") + f"   [{word_matched}/{word_total} words]",
        "",
        f"  missing numbers ({len(missing_nums)}): "
        + ", ".join(str(int(n) if n == int(n) else n) for n in missing_nums[:40])
        + (" …" if len(missing_nums) > 40 else ""),
        f"  missing words   ({len(missing_words)}): "
        + ", ".join(missing_words[:40])
        + (" …" if len(missing_words) > 40 else ""),
    ]
    if failures:
        lines += ["", "  FAILED checks: " + ", ".join(failures)]

    return {
        "passed": passed,
        "metrics": {
            "golden_cells": len(g_cells),
            "candidate_cells": len(c_cells),
            "cell_frac": round(cell_frac, 3),
            "num_recall": round(num_recall, 3),
            "num_matched": num_matched,
            "num_total": num_total,
            "word_recall": round(word_recall, 3),
            "word_matched": word_matched,
            "word_total": word_total,
        },
        "report": "\n".join(lines),
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("usage: python3 xlsx_diff.py <golden.xlsx> <candidate.xlsx>")
        sys.exit(2)
    result = compare(sys.argv[1], sys.argv[2])
    print(result["report"])
    sys.exit(0 if result["passed"] else 1)
