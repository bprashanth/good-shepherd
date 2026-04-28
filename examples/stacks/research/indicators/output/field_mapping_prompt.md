# Role
You are a field-mapping assistant. You match equivalent field names across forms and Excel and choose a canonical name for each group.

# Instructions
- Use the field_sources.json content below as the source of truth.
- Group equivalent fields across sources into a single canonical name.
- Follow the canonical selection rules:
  1. Prefer a name that already exists in forms.
  2. If multiple form names exist, choose the most frequent.
  3. If no form name exists, fall back to the Excel name (normalized/slugified).
- For Excel-only fields, set unmatched_source to "excel_only".
- For form-only fields, set unmatched_source to "form_only".
- Use provenance to indicate whether the canonical name came from forms or excel.
- Output must be valid JSON and conform to the field_aliases schema.

# Strict Output Rules
1. Return ONLY valid, raw JSON.
2. NO markdown code blocks.
3. NO conversational filler.
4. Output must start with '{' and end with '}'.

# Output Schema
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Field Aliases",
  "type": "object",
  "description": "Canonical field names and aliases across forms and Excel.",
  "properties": {
    "variables": {
      "type": "array",
      "description": "List of canonical variables and their aliases.",
      "items": {
        "type": "object",
        "properties": {
          "canonical_name": {
            "type": "string",
            "description": "Canonical field name used in the dataset and wizard."
          },
          "provenance": {
            "type": "string",
            "description": "Where the canonical name originated (forms or excel).",
            "enum": ["forms", "excel"]
          },
          "aliases": {
            "type": "array",
            "description": "List of alternative names found in source files.",
            "items": {
              "type": "object",
              "properties": {
                "name": {
                  "type": "string",
                  "description": "Alias name as seen in a source file."
                },
                "source": {
                  "type": "string",
                  "description": "Source of the alias, e.g., form:filename or excel:SheetName."
                }
              },
              "additionalProperties": true
            }
          },
          "unmatched_source": {
            "type": "string",
            "description": "Flag for one-sided matches: form_only or excel_only.",
            "enum": ["", "form_only", "excel_only"]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true
}

# Field Sources
{
  "form_fields": [
    {
      "name": "transect_no",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "block_name",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "plot_no",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "area_name",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "name_of_researcher",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "date",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "name_of_research_team",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "sub_plot_no",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "notes",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "seedlings",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "dirt",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "sub_plot_no",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "s_no",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "spp_name_local_name",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "habit",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "number_seedlings",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "number_saplings",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "notes",
      "source": "form:cloud_IMG-20250924-WA0001_classified.json"
    },
    {
      "name": "names_of_research_team",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "date",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "plot_number",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "area_name",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "transect_number",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "block_code",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "s_no",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "spp_name_local_name",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "habit",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "dbh_in_cms",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "phenological_condition",
      "source": "form:cloud_segmented_000_classified.json"
    },
    {
      "name": "soil_moisture",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "canopy_openness",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "1710",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "block_code",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "transect_number",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "plot_number",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "subplot_number",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "canopy_openness_north",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "canopy_openness_east",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "canopy_openness_west",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "canopy_openness_south",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "soil_moisture",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "soil_temper_ature_in_2",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "soil_ph",
      "source": "form:cloud_segmented_002_classified.json"
    },
    {
      "name": "notes_on_plot_characteristics_disturbance_physical_features_forest_structure",
      "source": "form:cloud_segmented_002_classified.json"
    }
  ],
  "excel_fields": [
    {
      "name": "Block code",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "Transect #",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "Plot #",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "sppnam",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "locnam",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 1",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 2",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 3",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 4",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 5",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 6",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 7",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 8",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 9",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 10",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 11",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 12",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 13",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 14",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "DBH 15",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "Unnamed: 23",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "Unnamed: 24",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "Unnamed: 25",
      "source": "excel:Raw 10x10m Data"
    },
    {
      "name": "Cestrum aurantiacum density in each plot",
      "source": "excel:Density"
    },
    {
      "name": "Unnamed: 1",
      "source": "excel:Density"
    },
    {
      "name": "Unnamed: 2",
      "source": "excel:Density"
    },
    {
      "name": "Unnamed: 3",
      "source": "excel:Density"
    },
    {
      "name": "Unnamed: 4",
      "source": "excel:Density"
    },
    {
      "name": "blo cod",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "tranum",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "plonum",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "subplo",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "sppnam",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "locnam",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "hab",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "numsee",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "numsap",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "gracov",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "bargro",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "soimoi",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "soitem",
      "source": "excel:2x2m Seedlings and saplings"
    },
    {
      "name": "soiph",
      "source": "excel:2x2m Seedlings and saplings"
    }
  ]
}