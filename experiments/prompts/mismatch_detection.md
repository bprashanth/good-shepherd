PROTOCOL:
[Files provided as attachments]

KML FEATURES:
{features_json}

VARIABLES:
{variables_json}

TASK: Compare protocol requirements with KML features and variables. Identify:
1. Missing features (protocol expects but KML doesn't have)
2. Extra features (KML has but protocol doesn't mention)
3. Feature count mismatches
4. Variables without corresponding features
5. Features without variables (when protocol doesn't specify)

For each mismatch, provide:
- Type of mismatch
- Severity (error, warning, info)
- Feature type or variable affected
- Protocol expectations vs KML reality
- Clear message and recommendation

Output ONLY valid JSON matching this schema:
{mismatch_schema}

