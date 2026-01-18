# Role
You are an ecological data assistant. You extract computed variables and indicator mappings from indicator documents and raw variable catalogs.

# Instructions
- Use the provided indicator PDF and the raw variable catalog to propose computed variables and indicators.
- Prefer JSONLogic expressions for compiled rules. Use JS only when JSONLogic is insufficient.
- Include evidence references (PDF page/snippet, Excel row/cell, or form field name).
- Output a single JSON object that matches the schema sections below.
- The JSON must be valid and must not include any extra text.

# Strict Output Rules
1. Return ONLY valid, raw JSON.
2. NO markdown code blocks.
3. NO conversational filler.
4. Output must start with '{' and end with '}'.

# Error Handling
If the files are incompatible or missing, output: {"error": "detailed reason"}

## Output Shape (Root)
The output must be a JSON object with exactly two top-level keys:
- "computed_variables": object matching computed_variables.schema.json
- "indicator_config": object matching indicator_config.schema.json

## computed_variables.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Computed Variables",
  "type": "object",
  "description": "User intent and compiled computation rules for derived variables.",
  "properties": {
    "computed_variables": {
      "type": "array",
      "description": "List of derived variables with English intent and compiled rules.",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "description": "Canonical name for the computed variable."
          },
          "description": {
            "type": "string",
            "description": "Short human-readable summary of what is computed."
          },
          "inputs": {
            "type": "array",
            "description": "Names of raw variables required to compute this value.",
            "items": {"type": "string"}
          },
          "english_intent": {
            "type": "string",
            "description": "Plain-English instruction provided or edited by the user."
          },
          "compiled": {
            "type": "object",
            "description": "Machine-readable rule that implements the English intent.",
            "properties": {
              "language": {
                "type": "string",
                "description": "Execution format, e.g., jsonlogic or js."
              },
              "code": {
                "type": "string",
                "description": "Expression or program snippet implementing the computation."
              }
            },
            "additionalProperties": true
          },
          "aggregation": {
            "type": "object",
            "description": "Aggregation level and time handling.",
            "properties": {
              "level": {
                "type": "string",
                "description": "Aggregation level, e.g., plot, subplot, transect."
              },
              "time": {
                "type": "string",
                "description": "Time handling, e.g., per_survey_event.",
                "enum": ["per_survey_event", "rolling", "cumulative", "none"]
              }
            },
            "additionalProperties": true
          },
          "evidence": {
            "type": "array",
            "description": "Optional evidence links supporting this computation.",
            "items": {"$ref": "./evidence.schema.json"}
          },
          "status": {
            "type": "string",
            "description": "Draft or approved state after user review.",
            "enum": ["draft", "approved"]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true
}

## indicator_config.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Indicator Config",
  "type": "object",
  "description": "Indicator definitions and visualization intents.",
  "properties": {
    "indicators": {
      "type": "array",
      "description": "List of indicators with required computed variables.",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "description": "Indicator name (e.g., Invasive Recovery)."
          },
          "definition": {
            "type": "string",
            "description": "Plain-English definition of the indicator."
          },
          "required_computed_variables": {
            "type": "array",
            "description": "Computed variables needed to calculate the indicator.",
            "items": {"type": "string"}
          },
          "graph_intents": {
            "type": "array",
            "description": "Suggested graphs for visual analysis.",
            "items": {"$ref": "./graph_intent.schema.json"}
          },
          "evidence": {
            "type": "array",
            "description": "Optional evidence links supporting this indicator.",
            "items": {"$ref": "./evidence.schema.json"}
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true
}

## graph_intent.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Graph Intent",
  "type": "object",
  "description": "Visualization intent metadata for later chart generation.",
  "properties": {
    "chart_type": {
      "type": "string",
      "description": "Suggested chart type, e.g., line, heatmap, histogram."
    },
    "x_axis": {
      "type": "string",
      "description": "Field name for the x-axis."
    },
    "y_axis": {
      "type": "string",
      "description": "Field name for the y-axis."
    },
    "group_by": {
      "type": "string",
      "description": "Optional grouping field (e.g., plot, transect)."
    },
    "aggregation": {
      "type": "string",
      "description": "Aggregation method, e.g., mean, sum, count."
    }
  },
  "additionalProperties": true
}

## evidence.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Evidence",
  "type": "object",
  "description": "Optional evidence link for traceability.",
  "properties": {
    "source_type": {
      "type": "string",
      "description": "Origin of evidence, e.g., pdf, excel, form."
    },
    "source_ref": {
      "type": "string",
      "description": "Page number, sheet/row, or filename reference."
    },
    "snippet": {
      "type": "string",
      "description": "Short excerpt supporting the computation or indicator."
    }
  },
  "additionalProperties": true
}

# Raw Variable Catalog
Below is the extracted raw variable catalog. Use these names as inputs to computed variables.
{
  "variables": [
    {
      "name": "transect_no",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "transect_no",
      "unit": "",
      "example_values": [
        "I"
      ],
      "confidence": null
    },
    {
      "name": "block_name",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "block_name",
      "unit": "",
      "example_values": [
        "1"
      ],
      "confidence": null
    },
    {
      "name": "plot_no",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "plot_no",
      "unit": "",
      "example_values": [
        "2"
      ],
      "confidence": null
    },
    {
      "name": "area_name",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "area_name",
      "unit": "",
      "example_values": [
        "BKM"
      ],
      "confidence": null
    },
    {
      "name": "name_of_researcher",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "name_of_researcher",
      "unit": "",
      "example_values": [
        "Caropy Cover"
      ],
      "confidence": null
    },
    {
      "name": "date",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "date",
      "unit": "",
      "example_values": [
        "19/02/2025"
      ],
      "confidence": null
    },
    {
      "name": "name_of_research_team",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "name_of_research_team",
      "unit": "",
      "example_values": [
        "Ak, HA, Kk, MK, PK"
      ],
      "confidence": null
    },
    {
      "name": "sub_plot_no",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "sub_plot_no",
      "unit": "",
      "example_values": [
        "1"
      ],
      "confidence": null
    },
    {
      "name": "notes",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "notes",
      "unit": "",
      "example_values": [
        "12"
      ],
      "confidence": null
    },
    {
      "name": "seedlings",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "seedlings",
      "unit": "",
      "example_values": [
        "Subplor:"
      ],
      "confidence": null
    },
    {
      "name": "dirt",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "dirt",
      "unit": "",
      "example_values": [
        "#:1"
      ],
      "confidence": null
    },
    {
      "name": "sub_plot_no",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "Sub plot no.",
      "unit": "",
      "example_values": [
        "1",
        "2",
        "3",
        "4."
      ],
      "confidence": null
    },
    {
      "name": "s_no",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "S.No",
      "unit": "",
      "example_values": [
        "1.",
        "2.",
        "3",
        "4",
        "5."
      ],
      "confidence": null
    },
    {
      "name": "spp_name_local_name",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "SPP Name/Local Name",
      "unit": "",
      "example_values": [
        "cadelei",
        "Perthin",
        "1carm",
        "Kage kisloar",
        "kisloar"
      ],
      "confidence": null
    },
    {
      "name": "habit",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "Habit",
      "unit": "",
      "example_values": [
        "T",
        "T",
        "7",
        "T",
        "I"
      ],
      "confidence": null
    },
    {
      "name": "number_seedlings",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "#Seedlings",
      "unit": "",
      "example_values": [
        "1",
        "\"",
        "11",
        "11",
        "1"
      ],
      "confidence": null
    },
    {
      "name": "number_saplings",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "#Saplings",
      "unit": "",
      "example_values": [
        "E",
        "I",
        "H",
        "1 ,",
        "11"
      ],
      "confidence": null
    },
    {
      "name": "notes",
      "source_form": "cloud_IMG-20250924-WA0001_classified.json",
      "field_name": "Notes",
      "unit": "",
      "example_values": [
        "was",
        "5% Kare",
        "10%",
        "usess",
        "10%"
      ],
      "confidence": null
    },
    {
      "name": "names_of_research_team",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "names_of_research_team",
      "unit": "",
      "example_values": [
        "AK,HA ,Kk, MIC, PK"
      ],
      "confidence": null
    },
    {
      "name": "date",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "date",
      "unit": "",
      "example_values": [
        "19/02/2025"
      ],
      "confidence": null
    },
    {
      "name": "plot_number",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "plot_number",
      "unit": "",
      "example_values": [
        "2"
      ],
      "confidence": null
    },
    {
      "name": "area_name",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "area_name",
      "unit": "",
      "example_values": [
        "BKM"
      ],
      "confidence": null
    },
    {
      "name": "transect_number",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "transect_number",
      "unit": "",
      "example_values": [
        "1"
      ],
      "confidence": null
    },
    {
      "name": "block_code",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "block_code",
      "unit": "",
      "example_values": [
        "I"
      ],
      "confidence": null
    },
    {
      "name": "s_no",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "S.No",
      "unit": "",
      "example_values": [
        "1.",
        "2.",
        "3.",
        "4",
        "5"
      ],
      "confidence": null
    },
    {
      "name": "spp_name_local_name",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "SPP Name/Local Name",
      "unit": "",
      "example_values": [
        "Kobumn",
        "lage",
        "come",
        "Kinker",
        "kisler"
      ],
      "confidence": null
    },
    {
      "name": "habit",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "Habit",
      "unit": "",
      "example_values": [
        "1",
        "I",
        "T",
        "T",
        "I"
      ],
      "confidence": null
    },
    {
      "name": "dbh_in_cms",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "DBH in cms",
      "unit": "",
      "example_values": [
        "23",
        "4.2+ 3.4+2.5",
        "3",
        "3.6+1.8",
        "2"
      ],
      "confidence": null
    },
    {
      "name": "phenological_condition",
      "source_form": "cloud_segmented_000_classified.json",
      "field_name": "Phenological condition",
      "unit": "",
      "example_values": [
        "Fruiting"
      ],
      "confidence": null
    },
    {
      "name": "soil_moisture",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "soil_moisture",
      "unit": "",
      "example_values": [
        "Dry+ =1, Dry- =2, Nor =3, Wet- =4, Wet+ =5"
      ],
      "confidence": null
    },
    {
      "name": "canopy_openness",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "canopy_openness",
      "unit": "",
      "example_values": [
        "Number of dots out of 96 imaginary dots that are not covered by the canopy; Taken only at the centre of the plot"
      ],
      "confidence": null
    },
    {
      "name": "1710",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "1710",
      "unit": "",
      "example_values": [
        "10.1230 >30"
      ],
      "confidence": null
    },
    {
      "name": "block_code",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Block Code",
      "unit": "",
      "example_values": [
        "I",
        "1"
      ],
      "confidence": null
    },
    {
      "name": "transect_number",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Transect #",
      "unit": "",
      "example_values": [
        "1",
        "I"
      ],
      "confidence": null
    },
    {
      "name": "plot_number",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Plot #",
      "unit": "",
      "example_values": [
        "1",
        "2",
        "3",
        "4",
        "5"
      ],
      "confidence": null
    },
    {
      "name": "subplot_number",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Subplot #",
      "unit": "",
      "example_values": [
        "0",
        "1",
        "2",
        "3",
        "4"
      ],
      "confidence": null
    },
    {
      "name": "canopy_openness_north",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Canopy Openness North",
      "unit": "",
      "example_values": [
        "09",
        "Aug=",
        "B",
        "Aug",
        "15"
      ],
      "confidence": null
    },
    {
      "name": "canopy_openness_east",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Canopy Openness East",
      "unit": "",
      "example_values": [
        "#11",
        "7.25",
        "92.4",
        "4",
        "4.25"
      ],
      "confidence": null
    },
    {
      "name": "canopy_openness_west",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Canopy Openness West",
      "unit": "",
      "example_values": [
        "35",
        "0%",
        "3",
        "2%",
        "13"
      ],
      "confidence": null
    },
    {
      "name": "canopy_openness_south",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Canopy Openness South",
      "unit": "",
      "example_values": [
        "04",
        "4",
        "7",
        "03"
      ],
      "confidence": null
    },
    {
      "name": "soil_moisture",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Soil Moisture",
      "unit": "",
      "example_values": [
        "3",
        "3 3",
        "3",
        "4",
        "3"
      ],
      "confidence": null
    },
    {
      "name": "soil_temper_ature_in_2",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Soil Temper ature in 2.",
      "unit": "",
      "example_values": [
        "19",
        "19",
        "23",
        "20 21",
        "23"
      ],
      "confidence": null
    },
    {
      "name": "soil_ph",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Soil pH",
      "unit": "",
      "example_values": [
        "7",
        "2",
        "7",
        "7",
        "7"
      ],
      "confidence": null
    },
    {
      "name": "notes_on_plot_characteristics_disturbance_physical_features_forest_structure",
      "source_form": "cloud_segmented_002_classified.json",
      "field_name": "Notes on Plot characteristics - Disturbance, Physical features, Forest structure",
      "unit": "",
      "example_values": [
        "Litter is high; Dry; her cestrum; few >C.A; undustory, regin Shurs, (aropy present: South in open company to North. No dury present",
        "Litter is high; Dry; her cestrum;",
        "few >C.A; undustory,",
        "regin Shurs,",
        "(aropy present: South in open company"
      ],
      "confidence": null
    }
  ]
}