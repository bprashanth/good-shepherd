# Plot Picker PWA

A mobile-friendly web application for selecting experimental plots and verifying data collection in the field.

## 1. How to Run

Because the application loads logical definitions and map features from external JSON files, it must be served over HTTP to avoid browser security restrictions (CORS) associated with the `file://` protocol.

### Using Python (Recommended)
You can start a simple local server using Python:

```bash
cd examples/pwa
python3 -m http.server
```

Then open **[http://localhost:8000](http://localhost:8000)** on your device or simulator.

### Mobile Testing
To test on a phone on the same Wi-Fi network:
1.  Run the server as above on your computer.
2.  Find your computer's local IP address (e.g., `ifconfig` or `ipconfig`).
3.  On your phone, visit `http://YOUR_IP_ADDRESS:8000`.

---

## 2. Architecture & Interactions

The app is built as a static site with no backend logic required beyond serving files.

*   **`index.html`**: The skeleton of the application. It contains the layout for the map viewport, the bottom control bar, and the logic-less modal for image previews. It handles user input events (clicks on selectors).
    
*   **`app.js`**: The core logic engine.
    *   **Initializes Leaflet Map**: Loads the Esri World Imagery basemap.
    *   **Parses `experiment.json`**: It reads the `hierarchy` object to build the list of **Transects** and their mapping to **Plots**. This drives the state of the "Up" button selectors.
    *   **Parses `features.geojson`**: It renders the map visual elements. Crucially, it matches the `properties.name` of each feature to the names found in `experiment.json` to enable highlighting and state changes.
    *   **State Management**: It tracks which Plot is currently selected, applies the "Glow" effect, and manages the transitions from "Red" (Pending) to "Green" (Submitted) when the user uploads a file.

*   **`experiment.json`**: The source of truth for the experiment structure. It dictates *what* choices are available in the UI.
    
*   **`features.geojson`**: The source of truth for the map. It dictates *where* the choices are displayed.

---

## 3. Handling Data Updates

If the experiment design changes (e.g., new transects added) or the spatial data is refined:

1.  **Regenerate Data**: Run the project ecosystem scripts (e.g., `build_wizard.py` or similar pipeline tools) to produce updated `experiment.json` and `features.geojson` files.
2.  **Copy Files**: Simply replace the files in this directory:
    *   `cp /path/to/new/experiment.json examples/pwa/`
    *   `cp /path/to/new/features.geojson examples/pwa/`
3.  **Refresh**: Reload the browser. The `app.js` logic is dynamic and will automatically adapt to the new list of transects and plots defined in the JSON files, provided the names in `experiment.json` match `features.geojson`.
