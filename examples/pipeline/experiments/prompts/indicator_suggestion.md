VARIABLES:
{variables_json}

FEATURE HIERARCHY:
{feature_hierarchy_json}

TASK: Suggest indicators/metrics for each feature type. Include:
1. Protocol-specified indicators (if any)
2. Suggested aggregations based on variable types and feature hierarchy
3. English descriptions of how to calculate each indicator

For each indicator, provide:
- ID, name, feature_type
- English description of calculation (not a formula, just description)
- Source variables
- Whether it's from protocol or suggested

Output ONLY valid JSON matching this schema:
{indicator_schema}

