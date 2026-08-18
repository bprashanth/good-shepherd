#!/usr/bin/env python3
"""API-only canonical extraction: schema, independent readings, disagreement."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import canonical  # noqa: E402
import wide_bench  # noqa: E402


STRUCTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "page": {"type": "integer"},
        "metadata_fields": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"}, "label": {"type": "string"},
                "bbox": {"type": "array", "items": {"type": "number"},
                         "minItems": 4, "maxItems": 4},
            }, "required": ["id", "label", "bbox"], "additionalProperties": False,
        }},
        "tables": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"}, "title": {"type": "string"},
                "bbox": {"type": "array", "items": {"type": "number"},
                         "minItems": 4, "maxItems": 4},
                "estimated_rows": {"type": "integer"},
                "columns": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"}, "label": {"type": "string"},
                        "parent": {"type": ["string", "null"]},
                        "value_kind": {"type": "string"},
                        "x0": {"type": "number"}, "x1": {"type": "number"},
                    },
                    "required": ["id", "label", "parent", "value_kind", "x0", "x1"],
                    "additionalProperties": False,
                }},
            },
            "required": ["id", "title", "bbox", "estimated_rows", "columns"],
            "additionalProperties": False,
        }},
        "free_text_regions": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"}, "label": {"type": "string"},
                "bbox": {"type": "array", "items": {"type": "number"},
                         "minItems": 4, "maxItems": 4},
            }, "required": ["id", "label", "bbox"], "additionalProperties": False,
        }},
    },
    "required": ["page", "metadata_fields", "tables", "free_text_regions"],
    "additionalProperties": False,
}


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "page": {"type": "integer"},
        "metadata": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "field_id": {"type": "string"},
                "value": {"type": ["string", "null"]},
                "confidence": {"type": "number"}, "illegible": {"type": "boolean"},
                "bbox": {"type": "array", "items": {"type": "number"},
                         "minItems": 4, "maxItems": 4},
            }, "required": ["field_id", "value", "confidence", "illegible", "bbox"],
            "additionalProperties": False,
        }},
        "tables": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "table_id": {"type": "string"},
                "rows": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "row_id": {"type": "string"},
                        "bbox": {"type": "array", "items": {"type": "number"},
                                 "minItems": 4, "maxItems": 4},
                        "values": {"type": "array", "items": {"type": ["string", "null"]}},
                        "confidences": {"type": "array", "items": {"type": "number"}},
                        "illegible_columns": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["row_id", "bbox", "values", "confidences",
                                 "illegible_columns"],
                    "additionalProperties": False,
                }},
            }, "required": ["table_id", "rows"], "additionalProperties": False,
        }},
        "free_text": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "region_id": {"type": "string"},
                "value": {"type": ["string", "null"]},
                "confidence": {"type": "number"},
            }, "required": ["region_id", "value", "confidence"],
            "additionalProperties": False,
        }},
    },
    "required": ["page", "metadata", "tables", "free_text"],
    "additionalProperties": False,
}


STRUCTURE_PROMPT = """You are the structure stage of a general paper-form digitizer.
Inspect this ONE full-page overview. Describe the visible form, but do not
transcribe handwritten values yet.

Return every standalone metadata field and every repeated table/list. A
numbered handwritten list is a table. For a table, preserve every physical
column and every level of a spanning header: put the group header in `parent`
and the leaf header in `label`. Never merge distinct subcolumns. Coordinates
are [x0,y0,x1,y1] fractions of the FULL PAGE, all between 0 and 1. Column x0/x1
are also full-page fractions, not fractions of the table. Preserve the full
physical layout: `estimated_rows` is the number of ALL visible data rows,
including unused trailing blank rows. Do not infer the count from handwriting.

Use generic value kinds such as identifier, integer, decimal, date, time,
species, local_name, categorical_code, yes_no, free_text, or unknown. This
stage is sector-agnostic: report what is printed, without inventing domains or
values. Include marginal annotations as free-text regions.
"""


EXTRACT_PROMPT = """You are the visual transcription stage of a general paper-form
digitizer. You receive one full-page overview followed by focused high-resolution
crops of the declared tables, lists, metadata, and notes. Tall table crops are
horizontal bands with the printed header repeated above each band; adjacent
bands may overlap by one row. They show the SAME page; deduplicate by literal
row key and do not duplicate rows or fields across crops.

The structure stage's schema is below. Populate it exactly. For every table
row with recorded content, return one values array in the declared column
order and with exactly that many entries. Preserve printed identifiers exactly,
including gaps; never renumber or repair a sequence. Preserve dots, ticks,
tallies, ditto marks, struck cells, multi-value notations, and merged annotation
rows according to what the paper means. A lone dot used as a recorded value is
0; a continuous strike-through means blank; tally marks are counted; checked
boxes are X.

Critical anti-fabrication rule: never copy a neighbouring value or a column's
common value merely to make the table complete. Use null for a visibly blank
cell. If ink is present but unreadable, also use null and list that zero-based
column index in illegible_columns. A low-confidence guess is worse than an
explicit unreadable cell. Printed legends are context for interpreting marks,
not permission to snap ambiguous ink onto a legal value. Honor each column's
declared value_kind: for example, an integer cell must be transcribed as a
numeral rather than an alphabetic lookalike. Resolve an ambiguous glyph using
only a legend visibly printed on this same page; if no such legend applies,
return null and mark the column illegible instead of coercing it.

Before answering, cross-check the nonblank row keys across every table band.
Include the first and last recorded row exactly once, and do not silently drop
a partially filled final row.

Row and field bboxes are full-page fractions. Every row bbox is strictly
`[left, top, right, bottom]`: first/third are horizontal x coordinates and
second/fourth are vertical y coordinates. A table row bbox must be wide and
short, never a tall column or a large page block. row_id is the literal printed or
written row key when one exists; otherwise use a stable y-based label such as
y_0.372. Confidence is visual confidence from 0 to 1, not ecological
plausibility. Do not apply species dictionaries or ecological corrections in
this stage.

DECLARED PAGE SCHEMA:
{schema}
"""


def render_page_inputs(form_dir: Path, page: int) -> tuple[Path, list[Path]]:
    output = form_dir / "canonical_tiles"
    output.mkdir(exist_ok=True)
    pdf = form_dir / "input.pdf"
    overview = output / f"page_{page}_overview.png"
    if not overview.exists():
        subprocess.run([sys.executable, str(wide_bench.RENDER), str(pdf), "--page", str(page),
                        "--zoom", "3", "--out", str(overview)], check=True, capture_output=True)
    tiles = []
    regions = [(0, 0, .56, .56), (.44, 0, 1, .56),
               (0, .44, .56, 1), (.44, .44, 1, 1)]
    for index, region in enumerate(regions):
        path = output / f"page_{page}_q{index}.png"
        if not path.exists():
            box = ",".join(str(value) for value in region)
            subprocess.run([sys.executable, str(wide_bench.RENDER), str(pdf), "--page", str(page),
                            "--bbox", box, "--zoom", "8", "--out", str(path)],
                           check=True, capture_output=True)
        tiles.append(path)
    return overview, tiles


def _table_band_boxes(table: dict, *, rows_per_band: int = 12,
                      overlap: int = 1) -> list[tuple[list[float], list[float]]]:
    """Return (header, data) page-coordinate boxes for a tall ruled table."""
    rows = max(0, int(table.get("estimated_rows") or 0))
    if rows <= 20:
        return []
    x0, y0, x1, y1 = (float(value) for value in table["bbox"])
    header_rows = 2 if any(column.get("parent") for column in
                           table.get("columns") or []) else 1
    row_height = (y1 - y0) / max(1, rows + header_rows)
    data_top = y0 + header_rows * row_height
    header = [x0, y0, x1, data_top]
    result = []
    step = max(1, rows_per_band - overlap)
    for start in range(0, rows, step):
        end = min(rows, start + rows_per_band)
        result.append((header, [x0, data_top + start * row_height,
                                x1, data_top + end * row_height]))
        if end == rows:
            break
    return result


def render_declared_crops(form_dir: Path, page: int, structure: dict,
                          *, limit: int = 8) -> list[Path]:
    """Render schema-derived evidence regions at high zoom, sector-agnostically."""
    output = form_dir / "canonical_tiles"
    regions = []
    # Repeated data gets priority because small table handwriting is the main
    # fixed-tile failure. Notes come next. Metadata fields are combined into a
    # single envelope so headers do not consume the entire image budget.
    tables = [item for item in structure.get("tables") or [] if item.get("bbox")]
    for item in tables:
        bands = _table_band_boxes(item)
        if bands:
            regions.extend(("table_band", pair) for pair in bands)
        else:
            regions.append(("table", item["bbox"]))
    for item in structure.get("free_text_regions") or []:
        if item.get("bbox"):
            regions.append(("text", item["bbox"]))
    metadata = [item.get("bbox") for item in structure.get("metadata_fields") or []
                if item.get("bbox")]
    if metadata:
        regions.append(("metadata", [
            min(box[0] for box in metadata), min(box[1] for box in metadata),
            max(box[2] for box in metadata), max(box[3] for box in metadata),
        ]))

    def padded(raw_box):
        try:
            x0, y0, x1, y1 = (float(value) for value in raw_box)
        except (TypeError, ValueError):
            return None
        pad = .012
        box = [max(0, x0 - pad), max(0, y0 - pad),
               min(1, x1 + pad), min(1, y1 + pad)]
        if box[2] <= box[0] or box[3] <= box[1]:
            return None
        return box

    def render(box, destination):
        subprocess.run([
            sys.executable, str(wide_bench.RENDER), str(form_dir / "input.pdf"),
            "--page", str(page), "--bbox", ",".join(str(value) for value in box),
            "--zoom", "10", "--out", str(destination),
        ], check=True, capture_output=True)

    paths = []
    for index, (kind, raw_box) in enumerate(regions[:limit]):
        path = output / f"page_{page}_declared_{index}_{kind}.png"
        if kind == "table_band":
            header_box, data_box = raw_box
            header_box, data_box = padded(header_box), padded(data_box)
            if header_box is None or data_box is None:
                continue
            if not path.exists():
                with tempfile.TemporaryDirectory(prefix="formidable-band-") as temporary:
                    header_path = Path(temporary) / "header.png"
                    data_path = Path(temporary) / "data.png"
                    render(header_box, header_path)
                    render(data_box, data_path)
                    header = Image.open(header_path).convert("RGB")
                    data = Image.open(data_path).convert("RGB")
                    width = max(header.width, data.width)
                    stacked = Image.new("RGB", (width, header.height + data.height), "white")
                    stacked.paste(header, (0, 0))
                    stacked.paste(data, (0, header.height))
                    stacked.save(path)
        else:
            box = padded(raw_box)
            if box is None:
                continue
            if not path.exists():
                render(box, path)
        paths.append(path)
    return paths


def gemini_json(model: str, prompt: str, images: list[Path], schema: dict,
                *, thinking: str = "minimal") -> tuple[dict, dict]:
    parts = [{"text": prompt}]
    for image in images:
        parts.append({"inline_data": {"mime_type": "image/png", "data": wide_bench._b64(image)}})
    generation = {
        "temperature": 0,
        "thinkingConfig": {"thinkingLevel": thinking},
        "responseMimeType": "application/json",
        "responseJsonSchema": schema,
        "maxOutputTokens": 32768,
    }
    payload = {"contents": [{"role": "user", "parts": parts}],
               "generationConfig": generation}
    key = wide_bench._key("gemini")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    t0 = time.time()
    try:
        response = wide_bench._post(url, payload, {}, timeout=900)
    except urllib.error.HTTPError as error:
        body = error.read()
        # Some generateContent revisions use responseSchema rather than the
        # JSON-Schema field. Retry once without weakening JSON enforcement.
        if error.code != 400:
            raise
        generation["responseSchema"] = generation.pop("responseJsonSchema")
        try:
            response = wide_bench._post(url, payload, {}, timeout=900)
        except urllib.error.HTTPError as second:
            raise RuntimeError(f"Gemini structured output rejected: {body[:300]!r}; "
                               f"fallback: {second.read()[:300]!r}") from second
    text = "".join(part.get("text", "")
                   for part in response["candidates"][0]["content"]["parts"])
    usage = response.get("usageMetadata", {})
    meta = {
        "model": model,
        "in_tok": usage.get("promptTokenCount"),
        "out_tok": usage.get("candidatesTokenCount"),
        "thinking_tok": usage.get("thoughtsTokenCount", 0),
        "cost_usd": wide_bench._gemini_cost(model, usage),
        "latency_s": round(time.time() - t0, 1),
    }
    return json.loads(text), meta


def openrouter_json(model: str, prompt: str, images: list[Path], schema: dict,
                    *, thinking: str = "minimal") -> tuple[dict, dict]:
    """Structured vision through OpenRouter, preserving the same JSON contract."""
    content = [{"type": "text", "text": prompt}]
    for image in images:
        content.append({"type": "image_url", "image_url": {
            "url": f"data:image/png;base64,{wide_bench._b64(image)}"}})
    payload = {
        "model": model,
        "temperature": 0,
        # The largest observed completion across 204 all-form benchmark calls
        # is 12,522 tokens. A 16,384 cap keeps 30% headroom while avoiding a
        # provider-side credit reservation for twice the demonstrated need.
        "max_tokens": 16384,
        "messages": [{"role": "user", "content": content}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "formidable_extraction", "strict": True, "schema": schema}},
        "reasoning": {"effort": thinking},
        "usage": {"include": True},
    }
    headers = {"Authorization": f"Bearer {wide_bench._key('openrouter')}",
               "HTTP-Referer": "https://fomoscribe.netlify.app",
               "X-Title": "Formidable high extraction"}
    started = time.time()
    retry_delays = (0, 2, 5, 10)
    for attempt, delay in enumerate(retry_delays, start=1):
        if delay:
            time.sleep(delay)
        try:
            response = wide_bench._post(
                "https://openrouter.ai/api/v1/chat/completions", payload, headers, timeout=900)
            message = response["choices"][0]["message"]["content"]
            if isinstance(message, list):
                message = "".join(part.get("text", "") for part in message
                                  if isinstance(part, dict))
            parsed = json.loads(message)
        except urllib.error.HTTPError as error:
            body = error.read()[:500]
            retryable = error.code in {408, 409, 429} or error.code >= 500
            if retryable and attempt < len(retry_delays):
                continue
            raise RuntimeError(
                f"OpenRouter {model} failed with HTTP {error.code}: {body!r}") from error
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if attempt < len(retry_delays):
                continue
            raise RuntimeError(
                f"OpenRouter {model} network failure after {attempt} attempts: {error}") from error
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            if attempt < len(retry_delays):
                continue
            raise RuntimeError(
                f"OpenRouter {model} returned invalid structured output after "
                f"{attempt} attempts: {error}") from error

        usage = response.get("usage") or {}
        return parsed, {
            "provider": "openrouter", "model": model,
            "in_tok": usage.get("prompt_tokens"), "out_tok": usage.get("completion_tokens"),
            "thinking_tok": usage.get("reasoning_tokens", 0),
            "cost_usd": usage.get("cost"), "latency_s": round(time.time() - started, 1),
            "attempts": attempt,
        }
    raise AssertionError("unreachable")


def codex_json(model: str, prompt: str, images: list[Path], schema: dict,
               *, thinking: str = "minimal") -> tuple[dict, dict]:
    """Strict structured vision through the authenticated Codex CLI.

    This uses the production Codex subscription credential, not an API key or
    a local model. Each call is ephemeral and read-only; the only persisted
    value is the validated final JSON response.
    """
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="formidable-codex-") as temporary:
        root = Path(temporary)
        schema_path = root / "schema.json"
        output_path = root / "output.json"
        schema_path.write_text(json.dumps(schema))
        command = [
            os.environ.get("FORMIDABLE_CODEX_BIN", "codex"),
            "exec", "--ephemeral", "--ignore-user-config",
            "--skip-git-repo-check", "--sandbox", "read-only",
            "--model", model, "--output-schema", str(schema_path),
            "--output-last-message", str(output_path),
        ]
        for image in images:
            command.extend(["--image", str(image.resolve())])
        command.append("-")
        retries = max(0, int(os.environ.get("FORMIDABLE_CODEX_TRANSIENT_RETRIES", "2")))
        result = None
        for attempt in range(1, retries + 2):
            output_path.unlink(missing_ok=True)
            try:
                result = subprocess.run(
                    command, input=prompt, text=True, capture_output=True,
                    timeout=900, check=False)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError(f"Codex {model} timed out after 900 seconds") from error
            if result.returncode == 0 and output_path.exists():
                break
            detail = (result.stderr or result.stdout)[-1000:]
            transient = any(marker in detail.casefold() for marker in (
                "at capacity", "rate limit", "too many requests", "temporarily unavailable"))
            if not transient or attempt > retries:
                raise RuntimeError(f"Codex {model} failed rc={result.returncode}: {detail}")
            time.sleep(min(45, 15 * attempt))
        assert result is not None
        try:
            parsed = json.loads(output_path.read_text())
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Codex {model} returned invalid JSON") from error
        match = re.search(r"tokens used\s+([\d,]+)", result.stdout + result.stderr)
        return parsed, {
            "provider": "codex_subscription", "model": model,
            "in_tok": None, "out_tok": None,
            "total_tok": int(match.group(1).replace(",", "")) if match else None,
            "thinking_tok": None, "cost_usd": None,
            "latency_s": round(time.time() - started, 1),
            "attempts": attempt,
        }


def claude_json(model: str, prompt: str, images: list[Path], schema: dict,
                *, thinking: str = "minimal") -> tuple[dict, dict]:
    """Strict structured vision through Claude Code's OAuth credential.

    Replacing Claude Code's large default system prompt is material here: the
    generic coding-agent preamble cost roughly 40k cached tokens in a two-field
    image probe. The reader gets only the Read tool, the named evidence images,
    and the literal-transcription contract.
    """
    del thinking  # Claude Code chooses the configured model's reasoning policy.
    started = time.time()
    image_list = "\n".join(f"- {image.resolve()}" for image in images)
    reader_prompt = (
        f"{prompt}\n\nUse the Read tool to inspect every evidence image below before "
        f"answering. Return only facts visible in those pixels.\n{image_list}"
    )
    command = [
        "claude", "-p", "--model", model,
        "--output-format", "json", "--json-schema", json.dumps(schema),
        "--permission-mode", "dontAsk", "--tools", "Read",
        "--allowedTools", "Read", "--no-session-persistence",
        "--system-prompt",
        ("You are a literal visual form reader. Use Read only for the named "
         "images. Preserve printed structure, handwriting, blanks, ditto marks, "
         "and uncertainty. Never repair values with domain knowledge."),
        reader_prompt,
    ]
    try:
        result = subprocess.run(command, text=True, capture_output=True,
                                timeout=900, check=False)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Claude {model} timed out after 900 seconds") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout)[-1000:]
        raise RuntimeError(f"Claude {model} failed rc={result.returncode}: {detail}")
    try:
        envelope = json.loads(result.stdout)
        parsed = envelope.get("structured_output")
        if not isinstance(parsed, dict):
            parsed = json.loads(envelope["result"])
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise RuntimeError(f"Claude {model} returned invalid structured JSON") from error
    usage = envelope.get("usage") or {}
    return parsed, {
        "provider": "claude_subscription", "model": model,
        "in_tok": usage.get("input_tokens"),
        "out_tok": usage.get("output_tokens"),
        "cache_creation_tok": usage.get("cache_creation_input_tokens"),
        "cache_read_tok": usage.get("cache_read_input_tokens"),
        "thinking_tok": None, "cost_usd": envelope.get("total_cost_usd"),
        "latency_s": round(time.time() - started, 1),
    }


def provider_json(model_spec: str, prompt: str, images: list[Path], schema: dict,
                  *, thinking: str = "minimal") -> tuple[dict, dict]:
    if model_spec.startswith("openrouter:"):
        return openrouter_json(model_spec.split(":", 1)[1], prompt, images, schema,
                               thinking=thinking)
    if model_spec.startswith("codex:"):
        return codex_json(model_spec.split(":", 1)[1], prompt, images, schema,
                          thinking=thinking)
    if model_spec.startswith("claude:"):
        return claude_json(model_spec.split(":", 1)[1], prompt, images, schema,
                           thinking=thinking)
    return gemini_json(model_spec, prompt, images, schema, thinking=thinking)


def model_filename(model_spec: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", model_spec).strip("_")


def _horizontal_rules(gray: np.ndarray) -> list[float]:
    """Find long ruled lines as normalized y positions without OpenCV.

    Local contrast handles uneven phone lighting. A long-window opening keeps
    printed rules while rejecting handwriting, whose strokes rarely remain
    horizontal over a material fraction of a table's width.
    """
    if gray.size == 0 or min(gray.shape) < 10:
        return []
    image = Image.fromarray(gray.astype(np.uint8), mode="L")
    radius = max(4, min(gray.shape) // 90)
    local_mean = np.asarray(image.filter(ImageFilter.BoxBlur(radius)), dtype=np.int16)
    source = gray.astype(np.int16)
    ink = ((local_mean - source) >= 5) & (source < 252)
    span = ink.shape[1]
    window = max(15, span // 20)
    cumulative = np.pad(np.cumsum(ink, axis=1, dtype=np.int32), ((0, 0), (1, 0)))
    sums = cumulative[:, window:] - cumulative[:, :-window]
    profile = (sums >= 0.75 * window).mean(axis=1)
    if profile.max(initial=0) <= 0:
        return []
    threshold = max(0.03, 0.2 * float(profile.max()))
    candidates = [
        index for index, value in enumerate(profile)
        if value >= threshold
        and value >= profile[max(0, index - 2):min(len(profile), index + 3)].max()
    ]
    peaks: list[int] = []
    for index in candidates:
        if not peaks or index - peaks[-1] >= 3:
            peaks.append(index)
        elif profile[index] > profile[peaks[-1]]:
            peaks[-1] = index

    normalized = [value / gray.shape[0] for value in peaks]
    deduped: list[float] = []
    # At 3x rendering, anti-aliased or overwritten rules can produce parallel
    # detections about 1% of a compact table apart. Real adjacent rows in the
    # benchmark are at least ~1.7% apart.
    for value in normalized:
        if not deduped or value - deduped[-1] > 0.012:
            deduped.append(value)
        else:
            deduped[-1] = (deduped[-1] + value) / 2
    return deduped


def refine_structure_geometry(raw: dict, overview: Path) -> list[dict]:
    """Raise model row counts when physical rules prove blank rows exist.

    This is deliberately one-way: geometry may restore omitted blank layout,
    but it never deletes a model-declared row. The first rule reveals whether
    the model's crop included the header top; only then are header intervals
    subtracted from the physical interval count.
    """
    image = Image.open(overview).convert("L")
    page = np.asarray(image)
    height, width = page.shape
    refinements = []
    for table in raw.get("tables") or []:
        try:
            x0, y0, x1, y1 = (float(value) for value in table.get("bbox") or [])
        except (TypeError, ValueError):
            continue
        # A tiny outward pad keeps a border centered exactly on a declared
        # boundary from being lost to Python's exclusive crop end.
        left, right = sorted((max(0, min(width, round(x0 * width) - 2)),
                              max(0, min(width, round(x1 * width) + 2))))
        top, bottom = sorted((max(0, min(height, round(y0 * height) - 2)),
                              max(0, min(height, round(y1 * height) + 2))))
        if right - left < 40 or bottom - top < 40:
            continue
        rules = _horizontal_rules(page[top:bottom, left:right])
        if len(rules) < 4:
            continue
        includes_header_top = rules[0] <= 0.015
        header_rows = 0
        if includes_header_top:
            header_rows = 2 if any(column.get("parent") for column in
                                   table.get("columns") or []) else 1
        physical_rows = max(0, len(rules) - 1 - header_rows)
        declared_rows = max(0, int(table.get("estimated_rows") or 0))
        if physical_rows >= declared_rows and physical_rows <= 200:
            table["_geometry_verified_rows"] = physical_rows
        # Require a material and plausible increase; a single spurious line
        # must not create an extra review row.
        if physical_rows > declared_rows and physical_rows <= 200:
            table["estimated_rows"] = physical_rows
            refinements.append({
                "table_id": table.get("id"), "declared_rows": declared_rows,
                "physical_rows": physical_rows, "rules": len(rules),
            })
    return refinements


def _read_structure(form_dir, output, page_number, schema_model, *, reuse=False):
    overview, tiles = render_page_inputs(form_dir, page_number)
    model_file = model_filename(schema_model)
    raw_path = output / f"page_{page_number}__structure__{model_file}.json"
    meta_path = output / f"page_{page_number}__structure__{model_file}.meta.json"
    if reuse and raw_path.exists() and meta_path.exists():
        return overview, tiles, json.loads(raw_path.read_text()), json.loads(meta_path.read_text())
    raw, meta = provider_json(schema_model, STRUCTURE_PROMPT, [overview], STRUCTURE_SCHEMA)
    raw_path.write_text(json.dumps(raw, indent=2))
    meta_path.write_text(json.dumps(meta, indent=2))
    return overview, tiles, raw, meta


def prepare_structures(form_dir: Path, schema_model: str, tag: str,
                       page_numbers: list[int] | None = None, *, reuse=False) -> dict:
    """Run/cache only the sector-agnostic page-structure stage for routing."""
    output = form_dir / "canonical_outputs" / tag
    output.mkdir(parents=True, exist_ok=True)
    page_count = fitz.open(form_dir / "input.pdf").page_count
    selected_pages = page_numbers or list(range(1, page_count + 1))
    calls = []
    for page_number in selected_pages:
        if not 1 <= page_number <= page_count:
            raise ValueError(f"page {page_number} outside 1..{page_count}")
        overview, _tiles, raw, meta = _read_structure(
            form_dir, output, page_number, schema_model, reuse=reuse)
        geometry = refine_structure_geometry(raw, overview)
        calls.append({"stage": "structure", "page": page_number,
                      "geometry_refinements": geometry, **meta})
        print(f"page {page_number}/{page_count}: structure has "
              f"{len(raw.get('tables') or [])} tables", flush=True)
    report = {
        "form": form_dir.name, "tag": tag, "schema_model": schema_model,
        "pages": selected_pages, "calls": calls,
        "cost_usd": round(sum(call.get("cost_usd") or 0 for call in calls), 5),
        "latency_s": round(sum(call.get("latency_s") or 0 for call in calls), 1),
    }
    (output / "structure_run.json").write_text(json.dumps(report, indent=2))
    return report


def run(form_dir: Path, schema_model: str, models: list[str], tag: str,
        page_numbers: list[int] | None = None, *, reuse_structure=False,
        reuse_existing=False, progress_callback=None) -> dict:
    output = form_dir / "canonical_outputs" / tag
    output.mkdir(parents=True, exist_ok=True)
    page_count = fitz.open(form_dir / "input.pdf").page_count
    pages, calls = [], []
    selected_pages = page_numbers or list(range(1, page_count + 1))
    for page_number in selected_pages:
        if not 1 <= page_number <= page_count:
            raise ValueError(f"page {page_number} outside 1..{page_count}")
        overview, tiles, raw_structure, meta = _read_structure(
            form_dir, output, page_number, schema_model,
            reuse=reuse_structure or reuse_existing)
        geometry = refine_structure_geometry(raw_structure, overview)
        calls.append({"stage": "structure", "page": page_number,
                      "geometry_refinements": geometry, **meta})
        page = canonical.normalize_structure(raw_structure, page_number)
        declared = {key: value for key, value in page.items() if key != "rows"}
        prompt = EXTRACT_PROMPT.format(schema=json.dumps(declared, ensure_ascii=False))
        focused = render_declared_crops(form_dir, page_number, raw_structure)
        evidence_images = [overview, *(focused or tiles)]
        # Literal readers are intentionally independent. Run them concurrently
        # once the shared sector-agnostic schema exists, then attach responses
        # in declared primary/peer order so provenance remains deterministic.
        def read_model(model):
            raw_path = output / f"page_{page_number}__extract__{model_filename(model)}.json"
            meta_path = output / f"page_{page_number}__extract__{model_filename(model)}.meta.json"
            if reuse_existing and raw_path.exists():
                raw = json.loads(raw_path.read_text())
                meta = (json.loads(meta_path.read_text()) if meta_path.exists() else {
                    "provider": "cached_evidence", "model": model,
                    "cost_usd": 0, "latency_s": 0, "attempts": 0,
                })
                return raw, meta
            raw, meta = provider_json(model, prompt, evidence_images, EXTRACTION_SCHEMA)
            raw_path.write_text(json.dumps(raw, indent=2))
            meta_path.write_text(json.dumps(meta, indent=2))
            return raw, meta

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as executor:
            futures = [executor.submit(read_model, model) for model in models]
            responses = [future.result() for future in futures]
        for model, (raw, meta) in zip(models, responses):
            calls.append({"stage": "extract", "page": page_number, **meta})
            canonical.attach_extraction(page, raw, model)
        pages.append(page)
        print(f"page {page_number}/{page_count}: {len(page['tables'])} tables, "
              f"{sum(len(t['rows']) for t in page['tables'])} aligned rows", flush=True)
        if progress_callback:
            progress_callback(page_number, len(selected_pages))

    document = canonical.new_document(str(form_dir / "input.pdf"), pages, models)
    canonical.resolve(document)
    errors = canonical.validate(document)
    stats = disagreement_stats(document)
    report = {
        "form": form_dir.name,
        "tag": tag,
        "schema_model": schema_model,
        "models": models,
        "calls": calls,
        "cost_usd": round(sum(call.get("cost_usd") or 0 for call in calls), 5),
        "latency_s": round(sum(call.get("latency_s") or 0 for call in calls), 1),
        "validation_errors": errors,
        "disagreement": stats,
    }
    document["run"] = report
    canonical.write_xlsx(document, output / "output.xlsx")
    canonical.dump(document, output / "canonical.json")
    (output / "run.json").write_text(json.dumps(report, indent=2))
    return report


def rebuild(form_dir: Path, tag: str) -> dict:
    """Reassemble saved provider JSON after local canonicalization changes."""
    output = form_dir / "canonical_outputs" / tag
    report = json.loads((output / "run.json").read_text())
    pages = []
    structure_files = sorted(
        (path for path in output.glob("page_*__structure__*.json")
         if not path.name.endswith(".meta.json")),
        key=lambda path: int(path.name.split("_")[1]))
    for structure_file in structure_files:
        page_number = int(structure_file.name.split("_")[1])
        raw_structure = json.loads(structure_file.read_text())
        overview, _tiles = render_page_inputs(form_dir, page_number)
        geometry = refine_structure_geometry(raw_structure, overview)
        for call in report.get("calls") or []:
            if call.get("stage") == "structure" and call.get("page") == page_number:
                call["geometry_refinements"] = geometry
        page = canonical.normalize_structure(raw_structure, page_number)
        for model in report["models"]:
            raw = json.loads((output / f"page_{page_number}__extract__{model_filename(model)}.json").read_text())
            canonical.attach_extraction(page, raw, model)
        pages.append(page)
    document = canonical.new_document(str(form_dir / "input.pdf"), pages, report["models"])
    canonical.resolve(document)
    report["validation_errors"] = canonical.validate(document)
    report["disagreement"] = disagreement_stats(document)
    document["run"] = report
    canonical.write_xlsx(document, output / "output.xlsx")
    canonical.dump(document, output / "canonical.json")
    (output / "run.json").write_text(json.dumps(report, indent=2))
    return report


def disagreement_stats(document):
    cells = []
    for page in document["pages"]:
        cells.extend(page["metadata_fields"])
        cells.extend(page["free_text_regions"])
        for table in page["tables"]:
            for row in table["rows"]:
                cells.extend(row["cells"])
    statuses = ("agreement", "majority_after_reread", "disagreement",
                "unresolved_after_reread", "blank_or_illegible",
                "structural_anomaly")
    counts = {status: sum(cell.get("status") == status for cell in cells)
              for status in statuses}
    counts["total"] = len(cells)
    counts["review_fraction"] = round(
        (counts["majority_after_reread"] + counts["disagreement"]
         + counts["unresolved_after_reread"]
         + counts["structural_anomaly"]
         + counts["blank_or_illegible"]) / len(cells), 4
    ) if cells else 0.0
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--form", required=True)
    parser.add_argument("--schema-model", default="gemini-3.5-flash")
    parser.add_argument("--models", default="gemini-3.6-flash,gemini-3.5-flash",
                        help="comma-separated readers; first is the immutable primary")
    parser.add_argument("--tag", default="canonical_v1")
    parser.add_argument("--pages", default="", help="comma-separated 1-based pages; default all")
    parser.add_argument("--rebuild", action="store_true",
                        help="reassemble saved raw JSON without new API calls")
    parser.add_argument("--structure-only", action="store_true",
                        help="cache generic structure for routing; do not transcribe values")
    parser.add_argument("--reuse-structure", action="store_true",
                        help="reuse structure JSON+metadata cached by --structure-only")
    args = parser.parse_args()
    pages = [int(value) for value in args.pages.split(",") if value.strip()]
    form_dir = Path(args.form).resolve()
    if args.rebuild:
        result = rebuild(form_dir, args.tag)
    elif args.structure_only:
        result = prepare_structures(form_dir, args.schema_model, args.tag,
                                    pages or None, reuse=args.reuse_structure)
    else:
        result = run(form_dir, args.schema_model,
                     [model.strip() for model in args.models.split(",") if model.strip()],
                     args.tag, pages or None, reuse_structure=args.reuse_structure)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
