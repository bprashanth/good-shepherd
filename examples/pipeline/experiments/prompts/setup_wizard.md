You are analyzing an ecological experiment to build a UI Setup Wizard.

### FILES PROVIDED:
1. **Protocol PDF(s):** Describes the experimental design, dimensions, and variables.
2. **KML File:** Contains the actual geographic features (Sites, Transects, Plots).

### TASK:
Analyze the documents to answer the following questions and populate the JSON.

**Level 1: Blocks (UI Card 3)**
- Does the experiment use blocks/sites (e.g., "shola patches", "districts")? these are typically larger geometries covering multiple transects/plots
- What are they called in the protocol?
- Extract their names from the top-level folders in the KML.

**Level 2: Transects (UI Card 2)**
- Does the experiment use transects?
- How many plots are along one transect?
- Extract the specific names of transects found in the KML (look for LineStrings).
- Map which Transects belong to which Block.

**Level 3: Plots (UI Card 1)**
- Describe the plot dimensions and variables measured *at the plot level*.
- Extract the names of plots from the KML (look for Polygons).
- Map which Plots belong to which Transect.

**Level 4: Subplots**
- Does the plot contain subplots? (Check PDF diagrams).
- What are the dimensions and variables measured *at the subplot level*?

### OUTPUT SCHEMA:
Output ONLY valid JSON matching this structure:
{
  "block_level": {
    "has_blocks": true,
    "term_used": "Shola Patch",
    "description": "Description from protocol...",
    "features_found": ["Alpha", "Beta", "Gamma"],
    "datasheet_required": true
  },
  "transect_level": {
    "has_transects": true,
    "description": "130m line radiating from edge...",
    "plots_per_transect": 5,
    "features_found": ["A_T1", "A_T2", "B_T1"],
    "hierarchy_map": {
      "Alpha": ["A_T1", "A_T2"],
      "Beta": ["B_T1"]
    }
  },
  "plot_level": {
    "has_plots": true,
    "dimensions": "10x10m",
    "variables": ["DBH", "Canopy Openness"],
    "features_found": ["A_HD-4", "60m 1"],
    "hierarchy_map": {
      "A_T1": ["60m 1", "60m 2"]
    }
  },
  "subplot_level": {
    "has_subplots": true,
    "dimensions": "2x2m",
    "nesting_logic": "4 subplots at corners of the plot",
    "variables": ["Seedling count", "Soil moisture"]
  }
}
