# Query Template Dispatch Architecture

## Overview

This document describes the architecture for handling query templates in the dashboard application. The system enables users to select pre-defined query templates that filter data and display results across multiple visualization panels.

## System Components

### 1. Four-Panel Dashboard Layout

The dashboard consists of four quarter panels arranged in a 2x2 grid:

- **MapComponent** (Top-Left): Displays geographic data as markers on a Leaflet map
- **SchemaPanel** (Top-Right): Executes SQL queries and displays results in JSON format
- **ImagePanel** (Bottom-Left): Displays images from query results with annotation capabilities
- **SurveyResultPanel** (Bottom-Right): Renders charts and graphs from query results

### 2. Template Selection Layer

**QueryTemplatePanel** (`src/components/QueryTemplatePanel.vue`)
- Displays a list of available query templates
- Templates can be:
  - Pre-defined in `queryTemplateService.js`
  - User-created and saved to localStorage
- When a template is clicked, emits `template-selected` event with the full template object

**DataViewer** (`src/components/DataViewer.vue`)
- Contains the QueryTemplatePanel in its "insights" tab
- Listens for `template-selected` events from QueryTemplatePanel
- Re-emits as a global `window` event: `template-selected` with `detail.template`

### 3. Template Dispatch Layer

**DashboardComponent** (`src/components/DashboardComponent.vue`)
- Central orchestrator for all four panels
- Maintains `templateDispatch` state object:
  ```javascript
  {
    map: null,
    survey: null,
    schema: null,
    image: null
  }
  ```
- Listens for global `template-selected` events
- Routes templates to appropriate panels based on template metadata

## Template Structure

Templates are JavaScript objects with the following structure:

```javascript
{
  id: "uniqueIdentifier",
  label: "Human-readable description with <placeholder> tags",
  targetPanel: "map" | "survey" | "schema" | "image",
  mode: "replace" | "overlay" | "append",
  sqlTemplate: "SELECT * FROM ? WHERE <placeholder_key> = '<placeholder_value>'",
  placeholders: ["sitename", "username", ...]  // Array of placeholder enum values
}
```

### Template Properties

- **id**: Unique identifier for the template
- **label**: User-facing description (e.g., "Show me <sitename> data")
- **targetPanel**: Which panel should receive the final results
- **mode**: How the panel should handle the results:
  - `replace`: Replace all existing content
  - `overlay`: Add content on top of existing (e.g., map layers)
  - `append`: Append to existing content
- **sqlTemplate**: SQL query template with placeholder patterns like `<sitename_key>` and `<sitename_value>`
- **placeholders**: Array of placeholder types (e.g., `PLACEHOLDER_ENUMS.SITENAME`)

## Event Flow

### Template Selection Flow

```
1. User clicks template in QueryTemplatePanel
   ↓
2. QueryTemplatePanel emits 'template-selected' (component event)
   ↓
3. DataViewer receives event, re-emits as global 'template-selected' (window event)
   ↓
4. DashboardComponent listens for global event via handleTemplateDispatch()
   ↓
5. DashboardComponent routes template to SchemaPanel (ALWAYS routes here first)
   ↓
6. SchemaPanel receives template as prop, auto-executes query
   ↓
7. SchemaPanel resolves placeholders via modal dialogs if needed
   ↓
8. SchemaPanel executes resolved SQL query
   ↓
9. SchemaPanel emits 'query-result-updated' with results
   ↓
10. DashboardComponent.handleQuery() receives results
   ↓
11. DashboardComponent routes results to targetPanel specified in template
   ↓
12. Target panel receives template with queryResults attached
   ↓
13. Target panel renders visualization based on template.mode
   ↓
14. Target panel emits 'template-processed' when done
   ↓
15. DashboardComponent clears template from templateDispatch
```

### Direct Query Flow (Non-Template)

```
1. User types SQL directly in SchemaPanel textarea
   ↓
2. User clicks "Run" button
   ↓
3. SchemaPanel executes query
   ↓
4. SchemaPanel emits 'query-result-updated' with results
   ↓
5. DashboardComponent.handleQuery() receives results
   ↓
6. DashboardComponent broadcasts results to all panels via queryResult prop
   ↓
7. All panels update with new data (no template routing)
```

## Panel Responsibilities

### SchemaPanel

**Role**: Query execution engine for the entire system

**Responsibilities**:
1. Receive templates via `props.template`
2. Watch for template changes and auto-execute queries
3. Resolve placeholders through modal dialogs:
   - Extract placeholders from template label and SQL
   - Show QueryTemplateModal for each placeholder
   - Collect user selections for keys and values
4. Replace placeholders in SQL template with resolved values
5. Execute SQL query using AlasQL
6. Emit `query-result-updated` with results
7. Display results in JSON viewer

**Key Functions**:
- `resolveTemplateQuery()`: Main resolution function
- `resolvePlaceholderKey()`: Shows modal to select field name
- `resolvePlaceholderValue()`: Shows modal to select field value
- `runQuery()`: Executes the final SQL query

### MapComponent

**Role**: Geographic visualization

**Responsibilities**:
1. Receive `props.template` with `queryResults` attached
2. Receive `props.queryResult` for direct queries
3. Use computed `effectiveQueryResult` that prioritizes template results:
   ```javascript
   effectiveQueryResult() {
     return this.template?.queryResults || this.queryResult || [];
   }
   ```
4. Extract latitude/longitude from results
5. Render markers on Leaflet map
6. Handle `mode: "overlay"` for adding layers without clearing existing markers
7. Emit `template-processed` when visualization is complete

### ImagePanel

**Role**: Image display and annotation

**Responsibilities**:
1. Receive `props.template` with `queryResults`
2. Receive `props.queryResult` for direct queries
3. Extract image URLs from query results
4. Display images in grid or carousel
5. Support image annotation (notes, markers)
6. Handle `mode: "replace"` to swap image set
7. Emit `template-processed` when done

### SurveyResultPanel

**Role**: Chart and graph visualization

**Responsibilities**:
1. Receive `props.template` with `queryResults`
2. Receive `props.queryResult` for direct queries
3. Extract chart data from results
4. Render Chart.js visualizations (scatter, bubble, etc.)
5. Support user selection of X/Y/Z axes
6. Handle `mode: "replace"` to swap chart data
7. Emit `template-processed` when done

## Placeholder Resolution System

### Placeholder Enums

Placeholders are defined as enums in `queryTemplateService.js`:

```javascript
export const PLACEHOLDER_ENUMS = {
  SITENAME: 'sitename',
  USERNAME: 'username',
  TIMESTAMP: 'timestamp',
  SPECIES: 'species',
  // ... more enums
};
```

### Placeholder Patterns

Each placeholder has associated field name patterns for auto-suggestion:

```javascript
export const PLACEHOLDER_PATTERNS = {
  SITENAME: ['sitename', 'site', 'siteid', 'site_id', ...],
  USERNAME: ['username', 'user', 'userid', 'user_id', ...],
  // ... more patterns
};
```

### Resolution Process

1. **Extract Placeholders**: From template label (`<sitename>`) and SQL template (`<sitename_key>`, `<sitename_value>`)
2. **Resolve Keys**: For each `<placeholder_key>` pattern:
   - Show QueryTemplateModal with field suggestions based on PLACEHOLDER_PATTERNS
   - User selects actual field name from data
3. **Resolve Values**: For each `<placeholder_value>` pattern:
   - Show QueryTemplateModal with unique values from selected key
   - User selects desired value
4. **Replace in SQL**: Substitute resolved values into SQL template
5. **Execute Query**: Run final SQL with AlasQL

## Data Flow Patterns

### Pattern 1: Template with Single Target Panel

**Example**: "Show me <sitename> data" → SchemaPanel

```
Template → SchemaPanel (execute) → SchemaPanel (display)
```

### Pattern 2: Template with Different Target Panel

**Example**: "Show all sites on map" → MapComponent

```
Template → SchemaPanel (execute) → MapComponent (display)
```

### Pattern 3: Template with Overlay Mode

**Example**: "Add survey sites to map" → MapComponent with overlay

```
Template → SchemaPanel (execute) → MapComponent (add layer, keep existing)
```

### Pattern 4: Direct Query (No Template)

**Example**: User types "SELECT * FROM ? WHERE siteId = 'huli'"

```
Direct SQL → SchemaPanel (execute) → All Panels (broadcast)
```

## Handling Complex Queries

### Multi-Panel Queries

For queries like "filter the data on this condition, then display this graph and this map":

**Approach 1: Composite Templates** (Recommended)
- Create a template that specifies multiple target panels:
  ```javascript
  {
    id: "multiPanelQuery",
    label: "Show filtered data, graph, and map",
    targetPanels: ["schema", "survey", "map"],  // Array instead of single
    mode: "replace",
    sqlTemplate: "SELECT * FROM ? WHERE ...",
    // ...
  }
  ```
- DashboardComponent routes to SchemaPanel first
- After execution, DashboardComponent routes results to all panels in `targetPanels` array
- Each panel receives the same template with `queryResults` attached
- Each panel renders according to its own visualization logic

**Approach 2: Template Chaining**
- Create a sequence of templates that execute in order
- First template filters data and routes to SchemaPanel
- Subsequent templates use previous results as input
- Requires template dependency tracking

### Multi-Graph Queries

For queries like "show these 4 indicator graphs":

**Approach 1: Single Template, Multiple Visualizations**
- Template targets SurveyResultPanel
- Template includes metadata for multiple chart configurations:
  ```javascript
  {
    id: "fourIndicatorGraphs",
    label: "Show 4 indicator graphs",
    targetPanel: "survey",
    mode: "replace",
    sqlTemplate: "SELECT indicator1, indicator2, indicator3, indicator4, ... FROM ?",
    chartConfigs: [
      { x: "date", y: "indicator1", type: "line" },
      { x: "date", y: "indicator2", type: "bar" },
      { x: "date", y: "indicator3", type: "scatter" },
      { x: "date", y: "indicator4", type: "line" }
    ]
  }
  ```
- SurveyResultPanel receives template with `chartConfigs`
- SurveyResultPanel renders multiple charts in a grid layout
- Each chart uses the same query results but different axis configurations

**Approach 2: Dynamic Panel Splitting**
- SurveyResultPanel supports sub-panel rendering
- Template specifies number of sub-panels and configurations
- SurveyResultPanel creates internal grid of chart components
- Each sub-panel renders independently

**Approach 3: Template Array**
- DashboardComponent supports array of templates
- Each template targets SurveyResultPanel with different chart config
- DashboardComponent routes all templates to SchemaPanel sequentially
- Results are accumulated and distributed to multiple chart instances
- Requires SurveyResultPanel to support multiple chart instances

## State Management

### Template Dispatch State

Located in `DashboardComponent`:

```javascript
const templateDispatch = ref({
  map: null,      // Template object or null
  survey: null,   // Template object or null
  schema: null,   // Template object or null
  image: null     // Template object or null
});
```

**State Transitions**:
1. Template selected → `templateDispatch.schema = template`
2. Query executed → `templateDispatch[targetPanel] = { ...template, queryResults }`
3. Panel processes → `templateDispatch[panel] = null`

### Query Result State

Located in `DashboardComponent`:

```javascript
const queryResult = ref(props.data);  // Broadcast to all panels
```

**Usage**:
- Set when direct query is executed (non-template)
- Broadcast to all panels via props
- Panels use `effectiveQueryResult` computed to prioritize template results

## Key Design Decisions

### 1. SchemaPanel as Central Query Engine

**Decision**: All queries (template and direct) execute in SchemaPanel

**Rationale**:
- Single source of truth for query execution
- Consistent error handling
- Reuses existing AlasQL integration
- Simplifies query result management

**Trade-offs**:
- SchemaPanel must handle both template and direct queries
- Requires prop watching for auto-execution
- Creates dependency: all panels depend on SchemaPanel

### 2. Template Routing Through DashboardComponent

**Decision**: DashboardComponent routes templates, not direct panel-to-panel communication

**Rationale**:
- Centralized control flow
- Easy to add logging/debugging
- Prevents tight coupling between panels
- Enables future features (template queuing, cancellation)

**Trade-offs**:
- Additional layer of indirection
- DashboardComponent must understand template structure

### 3. Template Results Override Direct Query Results

**Decision**: Panels prioritize `template.queryResults` over `queryResult` prop

**Rationale**:
- Clear precedence: template queries are intentional
- Prevents stale data from blocking template results
- Allows templates to override previous queries

**Trade-offs**:
- Requires manual clearing of templates
- Can block direct query results if template is stale

### 4. Placeholder Resolution via Modals

**Decision**: User interaction required for placeholder resolution

**Rationale**:
- Handles ambiguous field names
- Provides user control over query parameters
- Supports complex data structures with nested fields

**Trade-offs**:
- Requires user interaction (not fully automated)
- Can interrupt workflow with multiple modals

## Future Enhancements

### 1. Template Composition
- Allow templates to reference other templates
- Support template inheritance
- Enable template parameterization

### 2. Query Result Caching
- Cache query results by template ID
- Invalidate cache on data updates
- Support result sharing between templates

### 3. Async Template Execution
- Support long-running queries
- Show progress indicators
- Allow query cancellation

### 4. Template Validation
- Validate SQL templates before execution
- Check placeholder completeness
- Verify target panel compatibility

### 5. Template Versioning
- Support multiple versions of same template
- Track template usage statistics
- Enable A/B testing of templates

## Implementation Notes

### Adding a New Panel

1. Add panel component to DashboardComponent template
2. Add entry to `templateDispatch` state
3. Pass `template` prop to new panel
4. Implement `effectiveQueryResult` computed in panel
5. Handle `mode` prop (replace/overlay/append)
6. Emit `template-processed` when done

### Adding a New Template

1. Define template in `queryTemplateService.js`
2. Use `PLACEHOLDER_ENUMS` for placeholders
3. Specify `targetPanel` and `mode`
4. Define `sqlTemplate` with placeholder patterns
5. Add to `defaultTemplates` array

### Adding a New Placeholder Type

1. Add enum to `PLACEHOLDER_ENUMS`
2. Add patterns to `PLACEHOLDER_PATTERNS`
3. Update QueryTemplateModal to handle new type
4. Use in template definitions

## Troubleshooting

### Template Not Executing
- Check: Is template routed to SchemaPanel?
- Check: Does template have `sqlTemplate`?
- Check: Are placeholders resolved?

### Results Not Appearing in Target Panel
- Check: Is `targetPanel` correct?
- Check: Does panel have `effectiveQueryResult` computed?
- Check: Is template cleared after processing?

### Modal Not Showing
- Check: Is `modalState.show` set to true?
- Check: Is QueryTemplateModal in SchemaPanel template?
- Check: Are placeholder patterns defined?

### Stale Template Blocking Results
- Check: Is `template-processed` event emitted?
- Check: Does DashboardComponent clear template?
- Check: Does panel prioritize template results correctly?

