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
    header { padding: 16px 24px; background: #1f2937; color: #fff; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    main { display: flex; gap: 16px; padding: 16px; }
    .panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; flex: 1; min-width: 0; }
    h2 { margin: 0 0 8px 0; font-size: 18px; }
    h3 { margin: 12px 0 6px 0; font-size: 14px; color: #374151; }
    .item { border-top: 1px solid #f0f0f0; padding: 8px 0; }
    .label { font-weight: 600; }
    .muted { color: #6b7280; font-size: 12px; }
    pre { white-space: pre-wrap; background: #f9fafb; padding: 8px; border-radius: 6px; font-size: 12px; }
    .add-form { border: 1px dashed #d1d5db; padding: 8px; border-radius: 6px; margin-bottom: 8px; }
    .add-form input { width: 100%; margin: 4px 0; padding: 6px; border: 1px solid #e5e7eb; border-radius: 4px; font-size: 12px; }
    .add-form button { margin-top: 4px; padding: 6px 10px; font-size: 12px; background: #111827; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
    .inline-btn { margin-left: 6px; padding: 2px 6px; font-size: 11px; border: 1px solid #d1d5db; border-radius: 999px; background: #f3f4f6; cursor: pointer; }
    .evidence { display: none; margin-top: 6px; background: #f9fafb; border: 1px solid #e5e7eb; padding: 6px; border-radius: 6px; font-size: 12px; }
    .modal-backdrop { position: fixed; inset: 0; background: rgba(17, 24, 39, 0.55); display: none; align-items: center; justify-content: center; z-index: 10; }
    .modal { background: #fff; border-radius: 10px; padding: 16px; width: 420px; max-width: 90vw; box-shadow: 0 12px 24px rgba(0,0,0,0.2); }
    .modal h3 { margin-top: 0; }
    .modal input { width: 100%; margin: 4px 0 8px 0; padding: 6px; border: 1px solid #e5e7eb; border-radius: 4px; font-size: 12px; }
    .modal .btn-row { display: flex; justify-content: flex-end; gap: 8px; }
    .modal button { padding: 6px 10px; font-size: 12px; border: none; border-radius: 4px; cursor: pointer; }
    .btn-secondary { background: #e5e7eb; }
    .btn-primary { background: #111827; color: #fff; }
    .header-btn { margin-left: 0; background: #111827; color: #fff; border: 1px solid #374151; }
  </style>
</head>
<body>
  <header>
    <h1>Indicator Wizard</h1>
    <button id="download-codebook" class="inline-btn header-btn">Download codebook</button>
  </header>
  <main id="wizard-main">
    <section class="panel" id="raw-panel">
      <h2>Raw Variables <a class="inline-btn" href="indicator_field_mapping.html">Trace mapping</a></h2>
      <div id="raw-variables"></div>
    </section>
    <section class="panel" id="computed-panel">
      <h2>Computed Variables</h2>
      <form class="add-form" id="add-computed-form">
        <input type="text" id="computed-name" placeholder="Name" required />
        <input type="text" id="computed-desc" placeholder="Description or intent" required />
        <input type="text" id="computed-inputs" placeholder="Inputs (comma-separated)" />
        <input type="text" id="computed-formula" placeholder="Formula (optional)" />
        <button type="submit">Add computed variable</button>
        <button type="button" class="inline-btn" id="generate-formula">Generate formula</button>
      </form>
      <div id="computed-variables"></div>
    </section>
    <section class="panel" id="indicator-panel">
      <h2>Indicators</h2>
      <form class="add-form" id="add-indicator-form">
        <input type="text" id="indicator-name" placeholder="Indicator name" required />
        <input type="text" id="indicator-def" placeholder="Definition" required />
        <input type="text" id="indicator-reqs" placeholder="Required computed variables (comma-separated)" />
        <button type="submit">Add indicator</button>
      </form>
      <div id="indicators"></div>
    </section>
  </main>

  <div class="modal-backdrop" id="indicator-modal">
    <div class="modal">
      <h3>Edit Indicator</h3>
      <input type="text" id="edit-indicator-name" placeholder="Indicator name" />
      <input type="text" id="edit-indicator-def" placeholder="Definition" />
      <input type="text" id="edit-indicator-reqs" placeholder="Required computed variables (comma-separated)" />
      <input type="text" id="edit-indicator-chart" placeholder="Chart type" />
      <input type="text" id="edit-indicator-x" placeholder="X axis" />
      <input type="text" id="edit-indicator-y" placeholder="Y axis" />
      <input type="text" id="edit-indicator-group" placeholder="Group by" />
      <input type="text" id="edit-indicator-agg" placeholder="Aggregation" />
      <div class="btn-row">
        <button class="btn-secondary" id="cancel-indicator-edit">Cancel</button>
        <button class="btn-primary" id="save-indicator-edit">Save</button>
      </div>
    </div>
  </div>

  <script>
    const variableCatalog = __VARIABLE_CATALOG__;
    const indicatorCodex = __INDICATOR_CODEX__;
    const variablesCodebook = __VARIABLES_CODEBOOK__;

    const rawList = (variableCatalog && variableCatalog.variables) || [];
    const computedList = (indicatorCodex && indicatorCodex.computed_variables && indicatorCodex.computed_variables.computed_variables) || [];
    const indicatorList = (indicatorCodex && indicatorCodex.indicator_config && indicatorCodex.indicator_config.indicators) || [];

    function renderRawVariables() {
      const el = document.getElementById("raw-variables");
      if (!rawList.length) {
        el.innerHTML = "<p class='muted'>No variables detected.</p>";
        return;
      }
      el.innerHTML = rawList.map(v => `
        <div class="item" data-raw-name="${escapeAttr(v.name)}">
          <div class="label">${escapeHtml(v.name)}</div>
          <div class="muted">${escapeHtml(v.field_name || "")}</div>
          <div class="muted">Source: ${escapeHtml(v.source_form || "")}</div>
          ${v.example_values && v.example_values.length ? `<pre>${escapeHtml(v.example_values.join(", "))}</pre>` : ""}
        </div>
      `).join("");
    }

    function renderComputedVariables() {
      const el = document.getElementById("computed-variables");
      if (!computedList.length) {
        el.innerHTML = "<p class='muted'>No computed variables.</p>";
        return;
      }
      el.innerHTML = computedList.map(c => `
        <div class="item" data-computed-name="${escapeAttr(c.name || "")}">
          <div class="label">${escapeHtml(c.name || "")}</div>
          <div class="muted">${escapeHtml(c.description || "")}</div>
          <div class="muted">Intent: ${escapeHtml(c.english_intent || "")}</div>
          ${c.compiled && c.compiled.code ? `<pre>${escapeHtml(c.compiled.language || "")}: ${escapeHtml(formatCode(c.compiled.code))}</pre>` : ""}
        </div>
      `).join("");
    }


    function renderIndicators() {
      const el = document.getElementById("indicators");
      if (!indicatorList.length) {
        el.innerHTML = "<p class='muted'>No indicators.</p>";
        return;
      }
      el.innerHTML = indicatorList.map((i, idx) => `
        <div class="item" data-indicator-name="${escapeAttr(i.name || "")}">
          <div class="label">
            ${escapeHtml(i.name || "")}
            <button class="inline-btn" data-evidence-btn="${idx}">i</button>
            <button class="inline-btn" data-edit-btn="${idx}">Edit</button>
          </div>
          <div class="muted">${escapeHtml(i.definition || "")}</div>
          ${i.graph_intents && i.graph_intents.length ? `<pre>${escapeHtml(JSON.stringify(i.graph_intents, null, 2))}</pre>` : ""}
          <div class="evidence" data-evidence="${idx}">
            ${renderEvidence(i.evidence)}
          </div>
        </div>
      `).join("");

      indicatorList.forEach((_, idx) => {
        const btn = document.querySelector(`[data-evidence-btn="${idx}"]`);
        const box = document.querySelector(`[data-evidence="${idx}"]`);
        if (!btn || !box) return;
        btn.addEventListener("click", () => {
          box.style.display = box.style.display === "block" ? "none" : "block";
        });
      });

      indicatorList.forEach((indicator, idx) => {
        const btn = document.querySelector(`[data-edit-btn="${idx}"]`);
        if (!btn) return;
        btn.addEventListener("click", () => openIndicatorModal(indicator, idx));
      });
    }

    function escapeHtml(value) {
      const div = document.createElement("div");
      div.textContent = value == null ? "" : String(value);
      return div.innerHTML;
    }

    function escapeAttr(value) {
      return escapeHtml(value).replace(/\"/g, "&quot;");
    }

    function openIndicatorModal(indicator, idx) {
      const modal = document.getElementById("indicator-modal");
      modal.dataset.index = String(idx);
      document.getElementById("edit-indicator-name").value = indicator.name || "";
      document.getElementById("edit-indicator-def").value = indicator.definition || "";
      document.getElementById("edit-indicator-reqs").value = (indicator.required_computed_variables || []).join(", ");
      const graph = (indicator.graph_intents && indicator.graph_intents[0]) || {};
      document.getElementById("edit-indicator-chart").value = graph.chart_type || "";
      document.getElementById("edit-indicator-x").value = graph.x_axis || "";
      document.getElementById("edit-indicator-y").value = graph.y_axis || "";
      document.getElementById("edit-indicator-group").value = graph.group_by || "";
      document.getElementById("edit-indicator-agg").value = graph.aggregation || "";
      modal.style.display = "flex";
    }

    function closeIndicatorModal() {
      const modal = document.getElementById("indicator-modal");
      modal.style.display = "none";
    }

    function wireIndicatorModal() {
      document.getElementById("cancel-indicator-edit").addEventListener("click", closeIndicatorModal);
      document.getElementById("save-indicator-edit").addEventListener("click", () => {
        const modal = document.getElementById("indicator-modal");
        const idx = Number(modal.dataset.index || -1);
        if (idx < 0) return;
        const updated = {
          name: document.getElementById("edit-indicator-name").value.trim(),
          definition: document.getElementById("edit-indicator-def").value.trim(),
          required_computed_variables: document.getElementById("edit-indicator-reqs").value
            .split(",").map(v => v.trim()).filter(Boolean),
          graph_intents: [{
            chart_type: document.getElementById("edit-indicator-chart").value.trim(),
            x_axis: document.getElementById("edit-indicator-x").value.trim(),
            y_axis: document.getElementById("edit-indicator-y").value.trim(),
            group_by: document.getElementById("edit-indicator-group").value.trim(),
            aggregation: document.getElementById("edit-indicator-agg").value.trim()
          }]
        };
        indicatorList[idx] = Object.assign(indicatorList[idx] || {}, updated);
        closeIndicatorModal();
        renderIndicators();
      });
    }

    function renderEvidence(evidence) {
      if (!evidence || !evidence.length) {
        return "<span class='muted'>No evidence provided.</span>";
      }
      return evidence.map(ev => `
        <div>
          <div><strong>${escapeHtml(ev.source_type || "")}</strong> ${escapeHtml(ev.source_ref || "")}</div>
          <div class="muted">${escapeHtml(ev.snippet || "")}</div>
        </div>
      `).join("");
    }

    function formatCode(code) {
      if (code && typeof code === "object") {
        return JSON.stringify(code, null, 2);
      }
      return String(code || "");
    }

    function wireAddForms() {
      const computedForm = document.getElementById("add-computed-form");
      const indicatorForm = document.getElementById("add-indicator-form");

      computedForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const name = document.getElementById("computed-name").value.trim();
        const desc = document.getElementById("computed-desc").value.trim();
        const inputs = document.getElementById("computed-inputs").value.trim();
        const formula = document.getElementById("computed-formula").value.trim();
        if (!name || !desc) return;
        computedList.push({
          name,
          description: desc,
          english_intent: desc,
          inputs: inputs ? inputs.split(",").map(v => v.trim()).filter(Boolean) : [],
          compiled: formula ? { language: "jsonlogic", code: formula } : {}
        });
        computedForm.reset();
        renderComputedVariables();
      });

      indicatorForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const name = document.getElementById("indicator-name").value.trim();
        const definition = document.getElementById("indicator-def").value.trim();
        const reqs = document.getElementById("indicator-reqs").value.trim();
        if (!name || !definition) return;
        const required = reqs ? reqs.split(",").map(v => v.trim()).filter(Boolean) : [];
        indicatorList.push({
          name,
          definition,
          required_computed_variables: required
        });
        indicatorForm.reset();
        renderIndicators();
      });

      document.getElementById("generate-formula").addEventListener("click", async () => {
        const name = document.getElementById("computed-name").value.trim();
        const intent = document.getElementById("computed-desc").value.trim();
        const inputs = document.getElementById("computed-inputs").value.trim()
          .split(",").map(v => v.trim()).filter(Boolean);
        if (!name || !intent) return;
        const payload = {
          computed_variable_name: name,
          english_intent: intent,
          inputs,
          language_preference: "jsonlogic"
        };
        const formulaField = document.getElementById("computed-formula");
        formulaField.value = "Generating...";
        try {
          const response = await fetch("http://localhost:8765/compute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          const result = await response.json();
          console.log("Compute response:", result);
          if (!response.ok) {
            formulaField.value = result.error || "Failed to generate formula.";
            return;
          }
          const computed = result.computed_variables && result.computed_variables[0];
          if (computed && computed.compiled && computed.compiled.code) {
            formulaField.value = computed.compiled.code;
          } else {
            formulaField.value = "";
          }
        } catch (err) {
          formulaField.value = "Compute server unavailable.";
        }
      });
    }

    renderRawVariables();
    renderComputedVariables();
    renderIndicators();
    wireAddForms();
    wireIndicatorModal();

    document.getElementById("download-codebook").addEventListener("click", () => {
      const codebook = {
        version: "v1",
        generated_at: new Date().toISOString(),
        variables_codebook: variablesCodebook,
        variable_catalog: variableCatalog,
        computed_variables: { computed_variables: computedList },
        indicator_config: { indicators: indicatorList }
      };
      const blob = new Blob([JSON.stringify(codebook, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "indicator_codebook.json";
      link.click();
      URL.revokeObjectURL(link.href);
    });
  </script>
</body>
</html>
"""

MAPPING_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Field Mapping</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #f5f5f5; }
    header { padding: 16px 24px; background: #1f2937; color: #fff; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    main { padding: 16px; display: grid; gap: 16px; }
    .panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }
    .mapping-table { display: grid; grid-template-columns: 1fr 2fr 2fr; gap: 8px; font-weight: 600; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }
    .mapping-row { display: grid; grid-template-columns: 1fr 2fr 2fr; gap: 8px; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
    .mapping-row--unmatched { border: 1px solid #fca5a5; border-radius: 6px; padding: 8px; }
    .mapping-cell { font-size: 12px; color: #111827; }
    h2 { margin: 0 0 8px 0; font-size: 18px; }
    .item { border-top: 1px solid #f0f0f0; padding: 8px 0; }
    .label { font-weight: 600; }
    .muted { color: #6b7280; font-size: 12px; }
    .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
    a { color: #e5e7eb; text-decoration: none; font-size: 12px; }
  </style>
</head>
<body>
  <header>
    <h1>Field Mapping</h1>
    <a href="indicator_wizard.html">Back to wizard</a>
  </header>
  <main>
    <section class="panel">
      <h2>Field Mapping</h2>
      <div class="mapping-table">
        <div class="mapping-header">Canonical Name</div>
        <div class="mapping-header">Aliases</div>
        <div class="mapping-header">Sources</div>
      </div>
      <div id="mapping-rows"></div>
    </section>
  </main>
  <script>
    const variablesCodebook = __VARIABLES_CODEBOOK__;
    const variables = (variablesCodebook && variablesCodebook.variables) || [];

    const mappingRows = document.getElementById("mapping-rows");
    mappingRows.innerHTML = variables.map(entry => {
      const aliases = (entry.aliases || []).map(a => a.name).join(", ");
      const sources = (entry.aliases || []).map(a => a.source).join(", ");
      const highlight = entry.unmatched_source ? " mapping-row--unmatched" : "";
      return `
        <div class="mapping-row${highlight}">
          <div class="mapping-cell">${escapeHtml(entry.canonical_name || "")}</div>
          <div class="mapping-cell">${escapeHtml(aliases)}</div>
          <div class="mapping-cell">${escapeHtml(sources)}</div>
        </div>
      `;
    }).join("");

    function escapeHtml(value) {
      const div = document.createElement("div");
      div.textContent = value == null ? "" : String(value);
      return div.innerHTML;
    }
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
    parser.add_argument("--variables-codebook", required=True)
    parser.add_argument("--out-html", required=True)
    parser.add_argument("--out-computed", required=True)
    parser.add_argument("--out-indicators", required=True)
    parser.add_argument("--out-mapping", required=True)
    args = parser.parse_args()

    variable_catalog = load_json(args.variable_catalog)
    codex = load_json(args.codex)
    variables_codebook = load_json(args.variables_codebook)

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
    html_out = html_out.replace(
        "__VARIABLES_CODEBOOK__", json.dumps(variables_codebook)
    )

    with open(args.out_html, "w", encoding="utf-8") as f:
        f.write(html_out)

    mapping_out = MAPPING_TEMPLATE.replace(
        "__VARIABLES_CODEBOOK__", json.dumps(variables_codebook)
    )
    with open(args.out_mapping, "w", encoding="utf-8") as f:
        f.write(mapping_out)


if __name__ == "__main__":
    main()
