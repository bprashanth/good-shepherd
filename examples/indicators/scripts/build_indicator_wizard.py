import argparse
import json


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Indicator Wizard</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #f5f5f5; }
    header { padding: 16px 24px; background: #1f2937; color: #fff; }
    main { display: flex; gap: 16px; padding: 16px; }
    .panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; flex: 1; min-width: 0; }
    h2 { margin: 0 0 8px 0; font-size: 18px; }
    h3 { margin: 12px 0 6px 0; font-size: 14px; color: #374151; }
    .item { border-top: 1px solid #f0f0f0; padding: 8px 0; }
    .label { font-weight: 600; }
    .muted { color: #6b7280; font-size: 12px; }
    pre { white-space: pre-wrap; background: #f9fafb; padding: 8px; border-radius: 6px; font-size: 12px; }
  </style>
</head>
<body>
  <header>
    <h1>Indicator Wizard</h1>
  </header>
  <main>
    <section class="panel" id="raw-panel">
      <h2>Raw Variables</h2>
      <div id="raw-variables"></div>
    </section>
    <section class="panel" id="computed-panel">
      <h2>Computed Variables</h2>
      <div id="computed-variables"></div>
    </section>
    <section class="panel" id="indicator-panel">
      <h2>Indicators</h2>
      <div id="indicators"></div>
    </section>
  </main>

  <script>
    const variableCatalog = __VARIABLE_CATALOG__;
    const indicatorCodex = __INDICATOR_CODEX__;

    function renderRawVariables() {
      const el = document.getElementById("raw-variables");
      const vars = (variableCatalog && variableCatalog.variables) || [];
      if (!vars.length) {
        el.innerHTML = "<p class='muted'>No variables detected.</p>";
        return;
      }
      el.innerHTML = vars.map(v => `
        <div class="item">
          <div class="label">${escapeHtml(v.name)}</div>
          <div class="muted">${escapeHtml(v.field_name || "")}</div>
          <div class="muted">Source: ${escapeHtml(v.source_form || "")}</div>
          ${v.example_values && v.example_values.length ? `<pre>${escapeHtml(v.example_values.join(", "))}</pre>` : ""}
        </div>
      `).join("");
    }

    function renderComputedVariables() {
      const el = document.getElementById("computed-variables");
      const list = indicatorCodex && indicatorCodex.computed_variables && indicatorCodex.computed_variables.computed_variables;
      if (!list || !list.length) {
        el.innerHTML = "<p class='muted'>No computed variables.</p>";
        return;
      }
      el.innerHTML = list.map(c => `
        <div class="item">
          <div class="label">${escapeHtml(c.name || "")}</div>
          <div class="muted">${escapeHtml(c.description || "")}</div>
          <div class="muted">Intent: ${escapeHtml(c.english_intent || "")}</div>
          ${c.compiled && c.compiled.code ? `<pre>${escapeHtml(c.compiled.language || "")}: ${escapeHtml(c.compiled.code)}</pre>` : ""}
        </div>
      `).join("");
    }

    function renderIndicators() {
      const el = document.getElementById("indicators");
      const list = indicatorCodex && indicatorCodex.indicator_config && indicatorCodex.indicator_config.indicators;
      if (!list || !list.length) {
        el.innerHTML = "<p class='muted'>No indicators.</p>";
        return;
      }
      el.innerHTML = list.map(i => `
        <div class="item">
          <div class="label">${escapeHtml(i.name || "")}</div>
          <div class="muted">${escapeHtml(i.definition || "")}</div>
          ${i.graph_intents && i.graph_intents.length ? `<pre>${escapeHtml(JSON.stringify(i.graph_intents, null, 2))}</pre>` : ""}
        </div>
      `).join("");
    }

    function escapeHtml(value) {
      const div = document.createElement("div");
      div.textContent = value == null ? "" : String(value);
      return div.innerHTML;
    }

    renderRawVariables();
    renderComputedVariables();
    renderIndicators();
  </script>
</body>
</html>
"""


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Build indicator wizard HTML")
    parser.add_argument("--variable-catalog", required=True)
    parser.add_argument("--codex", required=True)
    parser.add_argument("--out-html", required=True)
    parser.add_argument("--out-computed", required=True)
    parser.add_argument("--out-indicators", required=True)
    args = parser.parse_args()

    variable_catalog = load_json(args.variable_catalog)
    codex = load_json(args.codex)

    computed = codex.get("computed_variables", {})
    indicators = codex.get("indicator_config", {})

    with open(args.out_computed, "w", encoding="utf-8") as f:
        json.dump(computed, f, indent=2)

    with open(args.out_indicators, "w", encoding="utf-8") as f:
        json.dump(indicators, f, indent=2)

    html_out = HTML_TEMPLATE
    html_out = html_out.replace(
        "__VARIABLE_CATALOG__", json.dumps(variable_catalog)
    )
    html_out = html_out.replace(
        "__INDICATOR_CODEX__", json.dumps(codex)
    )

    with open(args.out_html, "w", encoding="utf-8") as f:
        f.write(html_out)


if __name__ == "__main__":
    main()
