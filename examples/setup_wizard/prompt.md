You are analyzing an ecological experiment to build a UI Setup Wizard.

TASK:
Analyze the provided Protocol PDF(s) and KML Data to generate a hierarchy configuration for a Setup Wizard.

1. **Metadata:** Extract the experiment Title and Aim (Goal).
2. **Hierarchy:** Map the geometric hierarchy found in the KML (Blocks, Transects, Plots). Use the provided KML Summary as ground truth for feature names and relationships.
3. **Descriptions:** From the Protocol, extract descriptions, dimensions, and variables for each level.

Output ONLY valid JSON matching this schema:
{
  "metadata": {
    "title": "Experiment Title",
    "aim": "The main goal of the experiment..."
  },
  "hierarchy": {
    "block": {
      "exists": true,
      "name_in_protocol": "string",
      "description": "string",
      "datasheet_description": "string",
      "features": ["string"],
      "children": { "BlockName": ["ChildName"] }
    },
    ... (follow the provided schema structure for transect, plot, subplot)
  }
}
