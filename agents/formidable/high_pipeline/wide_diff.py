#!/usr/bin/env python3
"""Precision/F1 extension over xlsx_diff's recall-only scoring.

xlsx_diff (the nightly regression scorer) measures RECALL of golden tokens and
never penalises invented cells — cheap models over-produce (qwen3-vl-8b hit
cell_frac 1.11) and recall can't see it. This sibling scorer reuses the exact
same tokenisation (_cells/_atoms) so recall numbers stay comparable to
FINDINGS_treeplots.md, and adds:

  num_precision / word_precision : matched / candidate_total (multiset)
  num_f1 / word_f1               : harmonic mean of recall & precision

Usage:
    python3 wide_diff.py golden.xlsx candidate.xlsx
"""
import sys
from collections import Counter
from pathlib import Path

GSHEP = Path.home() / "src/github.com/bprashanth/good-shepherd/agents/formidable"
sys.path.insert(0, str(GSHEP))
import xlsx_diff  # noqa: E402


_SPLIT_RE = xlsx_diff._SPLIT_RE
_STRIP = xlsx_diff._STRIP


def _codes(cells: list[str]) -> list[str]:
    """Single-letter tokens — which xlsx_diff deliberately discards.

    xlsx_diff drops tokens shorter than 2 chars as "single stray letters", a
    sound call for the original tree-plot sheets where they were OCR noise. In
    this domain they are THE DATA: phenology scores (N/M/F/Y), germination
    codes (L/D/R/S/C/N), habit (T/S/C), survival (A/B/D). Measured on the
    partner's own forms, that rule left 70% of the pencil phenology sheet and
    59% of the seed/seedling sheet completely unscored, and biased what
    remained toward numbers.

    Kept as a SEPARATE bucket so num_*/word_* stay byte-comparable with every
    number already reported.
    """
    out = []
    for cell in cells:
        for tok in _SPLIT_RE.split(str(cell).lower()):
            tok = tok.strip(_STRIP)
            if len(tok) == 1 and tok.isalpha():
                out.append(tok)
    return out


def _semantic_codes(cells: list[str]) -> list[str]:
    """Code tokens with visibly equivalent checked marks canonicalised to X.

    Raw metrics remain unchanged. This companion metric prevents an evaluator
    from declaring ``✓`` wrong merely because a golden author typed ``X`` for
    the same visible mark (or vice versa).
    """
    translated = [str(cell).replace("✓", "X").replace("✔", "X").replace("☑", "X")
                  for cell in cells]
    return _codes(translated)


def _prf(golden: list, candidate: list) -> dict:
    gc, ac = Counter(golden), Counter(candidate)
    matched = sum(min(ac[k], v) for k, v in gc.items())
    g_total, c_total = sum(gc.values()), sum(ac.values())
    recall = matched / g_total if g_total else 1.0
    precision = matched / c_total if c_total else 1.0
    f1 = (2 * recall * precision / (recall + precision)) if (recall + precision) else 0.0
    return {"matched": matched, "golden_total": g_total, "cand_total": c_total,
            "recall": round(recall, 3), "precision": round(precision, 3),
            "f1": round(f1, 3)}


def compare(golden_path: str, candidate_path: str) -> dict:
    """xlsx_diff.compare() result, augmented with precision/F1 metrics."""
    base = xlsx_diff.compare(golden_path, candidate_path)
    g_cells, c_cells = xlsx_diff._cells(golden_path), xlsx_diff._cells(candidate_path)
    g_nums, g_words = xlsx_diff._atoms(g_cells)
    c_nums, c_words = xlsx_diff._atoms(c_cells)
    num, word = _prf(g_nums, c_nums), _prf(g_words, c_words)
    code = _prf(_codes(g_cells), _codes(c_cells))
    semantic_code = _prf(_semantic_codes(g_cells), _semantic_codes(c_cells))
    # combined view over everything a transcriber must get right
    allg = g_nums + g_words + _codes(g_cells)
    allc = c_nums + c_words + _codes(c_cells)
    tot = _prf([str(x) for x in allg], [str(x) for x in allc])
    semantic_all = _prf(
        [str(x) for x in g_nums + g_words + _semantic_codes(g_cells)],
        [str(x) for x in c_nums + c_words + _semantic_codes(c_cells)])
    base["metrics"].update({
        "num_precision": num["precision"], "num_f1": num["f1"],
        "word_precision": word["precision"], "word_f1": word["f1"],
        "code_recall": code["recall"], "code_precision": code["precision"],
        "code_f1": code["f1"], "code_total": code["golden_total"],
        "all_recall": tot["recall"], "all_precision": tot["precision"],
        "all_f1": tot["f1"], "all_total": tot["golden_total"],
        "semantic_code_recall": semantic_code["recall"],
        "semantic_code_precision": semantic_code["precision"],
        "semantic_code_f1": semantic_code["f1"],
        "semantic_all_recall": semantic_all["recall"],
        "semantic_all_precision": semantic_all["precision"],
        "semantic_all_f1": semantic_all["f1"],
    })
    return base


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python3 wide_diff.py <golden.xlsx> <candidate.xlsx>")
        sys.exit(2)
    r = compare(sys.argv[1], sys.argv[2])
    print(r["report"])
    m = r["metrics"]
    print(f"\n  num  P {m['num_precision']:.2f}  F1 {m['num_f1']:.2f}"
          f"\n  word P {m['word_precision']:.2f}  F1 {m['word_f1']:.2f}")
