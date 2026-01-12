# Exporting Data for External Apps

This document outlines how to integrate the outputs of this pipeline into an external web application (e.g., a React/PWA frontend).

## 1. Required Files

To build an interactive map with linked controls (e.g., Block -> Transect -> Plot selectors), you need the following two files:

1.  **Logic Layer**: `experiment.json`
2.  **Render Layer**: `features.geojson`

---

## 2. Implementing Logic (Linked Controls)

Use `experiment.json` to drive your application state and UI controls.

### Hierarchy & Relationships
The parent-child relationships are explicitly defined in the `hierarchy` object.

*   **Block -> Transects**:
    *   Path: `hierarchy.block.children`
    *   **Structure**: Object where Keys are **Block Names** and Values are Arrays of **Transect Names**.
    *   *Usage*: When a user selects a Block, look up this key to populate the "Transect" dropdown.

*   **Transect -> Plots**:
    *   Path: `hierarchy.transect.children`
    *   **Structure**: Object where Keys are **Transect Names** and Values are Arrays of **Plot Names**.
    *   *Usage*: When a user selects a Transect, look up this key to populate the "Plot" dropdown/scroller.

### Metadata
*   **Experiment Title**: `metadata.title`
*   **Aim**: `metadata.aim`
*   **Variable Lists**: `hierarchy.plot.variables` (useful for configuring data entry forms).

---

## 3. Implementing Map Rendering

Use `features.geojson` to render the spatial elements.

### Rendering
*   Unlike typical KMLs, this GeoJSON is a flat collection of features.
*   **Geometry**: Standard GeoJSON Polygons and LineStrings.
*   **Styling**: Use the `properties.type` (Polygon vs LineString) or your own logic to style them.

### Linking Logic to Map (Highlighting)
Crucially, the **feature names** in `experiment.json` (keys and values in the `children` objects) map **exacty** to the `properties.name` field in `features.geojson`.

**Algorithm for Highlighting:**
1.  **User Selects a Transect** (e.g., "A_T1") in the UI.
2.  **App Logic**:
    *   Get the list of child Plots from `experiment.json`: `plots = hierarchy.transect.children["A_T1"]`
3.  **Map Update**:
    *   Iterate through your GeoJSON layer.
    *   **Highlight**: If `feature.properties.name` == "A_T1" (The Transect itself).
    *   **Highlight**: If `feature.properties.name` is in `plots` (The child Plots).
    *   **Dim**: All other features.

---

## Summary Data Flow

```mermaid
graph TD
    A[experiment.json] -->|Defines Structure| B[UI Controls]
    B -->|User Selects "Transect A"| C[App State]
    A -->|Lookup Children| C
    
    D[features.geojson] -->|Renders Shapes| E[Map]
    C -->|List of Active Names| E
    E -->|Highlights Matches| User
```
