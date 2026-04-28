# KML Feature Extraction Rules

This document defines the heuristics used to identify and categorize spatial features from KML files into the ecological hierarchy (Block > Transect > Plot).

## 1. Feature Identification & Hierarchy

The system identifies hierarchical levels (Blocks, Transects, Plots) and filters noise based strictly on **geometric relationships** and specific naming patterns. KML folder structure is ignored.

### Core Logic (Nesting & Containment)

1.  **Blocks (Level 1)**:
    *   **Definition**: Any **Polygon** that is a *Root* (i.e., not contained within any other Polygon).
    *   **Role**: The top-level container for the site.
2.  **Plots (Level 3)**:
    *   **Definition**: Any **Polygon** that is a *Child* (i.e., contained within another Polygon).
    *   **Role**: Represents the smallest sampling unit. The containing polygon is its parent Block.
3.  **Transects (Level 2)**:
    *   **Definition**: Any **LineString**.
    *   **Role**: Linear sampling feature.
    *   **Association**: Assigned to a Block if it intersects that Block.
4.  **Plot-Transect Association**:
    *   If a Plot intersects (or is very close to) a Transect within the same Block, it becomes a child of that Transect.
    *   Otherwise, it remains a direct child of the Block.

### Feature Filtering (Noise Reduction)

To ensure clean data extraction, the system ignores:
*   **Unnamed Features**: Features named "Unnamed" or `None`.
*   **Distance Markers**: LineStrings with names starting with digits+m (e.g., "60m 1").

## 2. Output Structure (for `kml_summary.json`)

The Python parser should produce a summary JSON that strictly maps the geometric findings:

```json
{
  "hierarchy": {
    "blocks": [
      {
        "name": "Block 1",
        "geometry_type": "Polygon",
        "contains": ["Transect A", "Transect B"]
      }
    ],
    "transects": [
      {
        "name": "Transect A",
        "geometry_type": "LineString",
        "contains": ["Plot 1", "Plot 2"]
      }
    ],
    "plots": [
      {
        "name": "Plot 1",
        "geometry_type": "Polygon"
      }
    ]
  },
  "orphans": []
}
```
