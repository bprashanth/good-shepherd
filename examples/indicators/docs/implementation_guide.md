# Vue3 Implementation Guide (Indicator Dashboard)

This guide outlines how a Vue3 app can dynamically compute indicators and render charts using:
- `indicator_codebook.json`
- `indicator_dataset.json`

The approach mirrors `examples/indicators/scripts/visualize_indicators.py` but is intended for the web app. The existing component `examples/dashboard/app/src/components/SurveyResultPanel.vue` can serve as a reference for how to drive Chart.js rendering from a dataset.

## Recommended chart library
- **Chart.js** is sufficient for bar/line/scatter and simple boxplots (via a plugin).
- If you need native boxplots/violin/heatmaps, consider **ECharts** or **Plotly**.

For parity with the POC, Chart.js + a boxplot plugin (e.g., `chartjs-chart-box-and-violin-plot`) is enough.

## High-level data flow
1. Load `indicator_codebook.json` and `indicator_dataset.json`.
2. Compute derived fields per record using `computed_variables`.
3. When a user selects an indicator, read its `graph_intents`.
4. Group and aggregate the dataset accordingly.
5. Render the chart type specified.

## Core steps (pseudo-flow)

### 1) Load data
```js
const codebook = await fetch('indicator_codebook.json').then(r => r.json());
const dataset = await fetch('indicator_dataset.json').then(r => r.json());
const records = dataset.records;
```

### 2) Compute derived fields
Each computed variable is applied per record. Use `compiled` when possible; JSONLogic can be evaluated client-side.

```js
import jsonLogic from 'json-logic-js';

function applyComputed(records, computedVars) {
  return records.map(row => {
    const out = { ...row };
    for (const cv of computedVars) {
      if (!cv.compiled) continue;
      if (cv.compiled.language === 'jsonlogic') {
        out[cv.name] = jsonLogic.apply(cv.compiled.code, out);
      } else if (cv.compiled.language === 'js') {
        // For POC this is fine (as simple as possible), in other environments consider evaluating small JS snippets in a sandbox or replace with a safer interpreter
        out[cv.name] = evaluateJsSnippet(cv.compiled.code, out);
      }
    }
    return out;
  });
}
```

### 3) Aggregate for indicator
Use `graph_intents` to decide grouping + aggregation.

```js
function aggregate(records, intent) {
  const { x_axis, y_axis, group_by, aggregation } = intent;
  const groups = new Map();
  for (const row of records) {
    const key = row[group_by];
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row[y_axis]);
  }
  const result = [];
  for (const [key, values] of groups.entries()) {
    const nums = values.map(v => Number(v)).filter(v => !isNaN(v));
    let value = null;
    if (aggregation === 'sum') value = nums.reduce((a,b)=>a+b,0);
    if (aggregation === 'mean') value = nums.length ? nums.reduce((a,b)=>a+b,0)/nums.length : null;
    result.push({ x: key, y: value });
  }
  return result;
}
```

### 4) Render with Chart.js
Use the computed/aggregated data to render a chart. The component can follow the pattern in `SurveyResultPanel.vue`.

```js
const dataPoints = aggregate(computedRecords, intent);
new Chart(ctx, {
  type: intent.chart_type === 'stacked_bar' ? 'bar' : intent.chart_type,
  data: {
    labels: dataPoints.map(d => d.x),
    datasets: [{ data: dataPoints.map(d => d.y) }]
  },
  options: { scales: { x: { stacked: intent.chart_type === 'stacked_bar' }, y: { stacked: intent.chart_type === 'stacked_bar' } } }
});
```

## Example: Resilience.growth (stacked bar)
- `x_axis`: `spp_name_local_name`
- `y_axis`: `native_species_growth`
- `group_by`: `plot_number`
- `aggregation`: `mean`

Flow:
1. Compute `native_species_growth` per record.
2. Group by `spp_name_local_name` + `plot_number`.
3. Aggregate mean DBH per group.
4. Render stacked bar (species on x, plot_number stacked).

## Example: Invasive Recovery (bar)
- `x_axis`: `plot_number`
- `y_axis`: `c_aurantiacum_mature_count`
- `group_by`: `plot_number`
- `aggregation`: `sum`

Flow:
1. Compute `c_aurantiacum_mature_count` per record.
2. Group by plot_number.
3. Sum counts.
4. Render bar chart.

## Notes for implementation
- Use the **canonical field names** from `variables_codebook` when reading dataset columns.
- If a field is missing, mark the indicator as incomplete in the UI.
- For boxplots, use a Chart.js plugin or switch to ECharts/Plotly.
