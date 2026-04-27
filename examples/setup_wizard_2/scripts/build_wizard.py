import argparse
import json
import sys

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Experiment Setup Wizard</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    <style>
        body { margin: 0; font-family: sans-serif; display: flex; height: 100vh; overflow: hidden; }
        .wizard-container { display: flex; width: 100%; height: 100%; }
        .sidebar { width: 40%; padding: 20px; box-sizing: border-box; overflow-y: auto; border-right: 1px solid #ccc; background: #f9f9f9; display: flex; flex-direction: column; }
        .map-container { width: 60%; height: 100%; background: #e5e3df; }
        #map { width: 100%; height: 100%; }
        .card { background: white; border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: none; }
        .card.active { display: block; }
        .btn-group { margin-top: auto; display: flex; justify-content: space-between; }
        button { padding: 10px 20px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 4px; }
        button:disabled { background: #ccc; }
        h2 { margin-top: 0; }
        .variable-tag { background: #e2e6ea; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; margin-right: 4px; display: inline-block; margin-bottom: 4px; }
        .hierarchy-tree { display: flex; flex-direction: column; align-items: center; margin-top: 20px; }
        .tree-node { padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 0.9em; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
        .tree-node.root { background: #e67e22; color: white; }
        .tree-node.level-1 { background: #3498db; color: white; }
        .tree-node.level-2 { background: #2ecc71; color: white; }
        .tree-arrow { font-size: 1.2em; color: #999; margin: 5px 0; }
        .feature-label {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #666;
            border-radius: 4px;
            padding: 2px 5px;
            font-size: 11px;
            font-weight: bold;
            white-space: nowrap;
            color: #333;
        }
    </style>
</head>
<body>
<div class="wizard-container">
    <div class="sidebar">
        <div id="card-container"></div>
        <div class="btn-group">
            <button id="prevBtn" onclick="prevCard()" disabled>Previous</button>
            <span id="step-indicator">1 / 1</span>
            <button id="nextBtn" onclick="nextCard()">Next</button>
        </div>
    </div>
    <div class="map-container">
        <div id="map"></div>
    </div>
</div>
<script>
    const experimentData = __EXPERIMENT_DATA__;
    const geoJsonData = __GEOJSON_DATA__;
    let currentStep = 0;
    let cards = [];
    let map;
    let geoJsonLayer;
    function initMap() {
        map = L.map('map').setView([0, 0], 2);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri'
        }).addTo(map);
        geoJsonLayer = L.geoJSON(geoJsonData, {
            pointToLayer: function (feature, latlng) {
                return L.circleMarker(latlng, {
                    radius: 4,
                    fillColor: "#000",
                    color: "#fff",
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });
            },
            style: function(feature) {
                switch (feature.properties.type) {
                    case 'Polygon': return {color: "#ff7800", weight: 2};
                    case 'LineString': return {color: "#3388ff", weight: 3};
                    default: return {color: "#000"};
                }
            }
        }).addTo(map);
        if (geoJsonLayer.getLayers().length > 0) {
            map.fitBounds(geoJsonLayer.getBounds());
        }
    }
    function createCards() {
        let data = experimentData;
        if (!data.hierarchy && data.properties && data.properties.hierarchy) {
            data = data.properties;
        }
        let treeHTML = '<div class="hierarchy-tree">';
        if (data.hierarchy.block && data.hierarchy.block.features) {
            const blockCount = data.hierarchy.block.features.length;
            treeHTML += `<div class="tree-node root">Sites (${blockCount})</div>`;
            if (blockCount > 0 && data.hierarchy.block.children) {
                const firstBlock = data.hierarchy.block.features[0];
                const children = data.hierarchy.block.children[firstBlock] || [];
                if (children.length > 0) {
                    treeHTML += `<div class="tree-arrow">↓</div><div class="tree-node level-1">Approx. ${children.length} Plots per Site</div>`;
                    if (data.hierarchy.subplot && data.hierarchy.subplot.exists) {
                        treeHTML += `<div class="tree-arrow">↓</div><div class="tree-node level-2">${data.hierarchy.subplot.dimensions}</div>`;
                    }
                }
            }
        }
        treeHTML += '</div>';
        cards.push({
            id: 'overview',
            title: data.metadata ? data.metadata.title : "Experiment Setup",
            content: `
                <h3>Aim</h3>
                <p>${data.metadata ? data.metadata.aim : "No aim defined."}</p>
                <h3>Hierarchy</h3>
                ${treeHTML}
            `,
            features: null
        });
        if (data.hierarchy.block && data.hierarchy.block.exists) {
            cards.push({
                id: 'blocks',
                title: data.hierarchy.block.name_in_protocol || "Sites",
                content: `<p>${data.hierarchy.block.datasheet_description || ""}</p>
                          <h4>Identified Sites:</h4>
                          <ul>${(data.hierarchy.block.features || []).map(f => `<li>${f}</li>`).join('')}</ul>`,
                features: data.hierarchy.block.features,
                role: 'block'
            });
        }
        if (data.hierarchy.plot && data.hierarchy.plot.exists) {
            cards.push({
                id: 'plots',
                title: data.hierarchy.plot.name_in_protocol || "Plots",
                content: `<p><strong>Dimensions:</strong> ${data.hierarchy.plot.dimensions}</p>
                          <p>${data.hierarchy.plot.datasheet_description || ""}</p>
                          <h4>Identified Plots:</h4>
                          <ul>${(data.hierarchy.plot.features || []).map(f => `<li>${f}</li>`).join('')}</ul>
                          <h4>Variables:</h4>
                          <div>${(data.hierarchy.plot.variables || []).map(v => `<span class="variable-tag">${v}</span>`).join('')}</div>
                          <div style="margin-top: 15px;">
                               <input type="file" id="variable-datasheet-upload" style="display:none" onchange="alert('Datasheet attached!')">
                               <button onclick="document.getElementById('variable-datasheet-upload').click()" style="background: #17a2b8;">+ Add Datasheet</button>
                               <input type="file" id="dataset-folder-upload" webkitdirectory directory style="display:none" onchange="alert('Dataset folder attached!')">
                               <button onclick="document.getElementById('dataset-folder-upload').click()" style="background: #6f42c1; margin-left: 10px;">+ Upload Dataset</button>
                          </div>`,
                features: data.hierarchy.plot.features,
                role: 'plot'
            });
        }
        if (cards.length > 0) {
            const last = cards[cards.length - 1];
            last.content += `<div style="margin-top: 20px; text-align: right; border-top: 1px solid #eee; padding-top: 20px;">
                                  <button onclick="window.location.href='../web_2/index.html'" style="background-color: #28a745; font-weight: bold;">Submit</button>
                              </div>`;
        }
        renderCards();
        updateUI();
    }
    function renderCards() {
        const container = document.getElementById('card-container');
        container.innerHTML = '';
        cards.forEach((card, index) => {
            const div = document.createElement('div');
            div.className = `card ${index === 0 ? 'active' : ''}`;
            div.innerHTML = `<h2>${card.title}</h2><div class="card-content">${card.content}</div>`;
            container.appendChild(div);
        });
    }
    const styles = {
        'default': { color: '#999', weight: 1, fillOpacity: 0.1, opacity: 0.4 },
        'block': { color: '#e67e22', weight: 3, fillOpacity: 0.12, opacity: 1 },
        'plot': { color: '#2ecc71', weight: 2, fillOpacity: 0.35, opacity: 1 }
    };
    function highlightFeatures(featureNames, role) {
        let bounds = L.latLngBounds();
        let found = false;
        const isOverview = (featureNames === null);
        geoJsonLayer.eachLayer(layer => {
            const name = layer.feature.properties.name;
            const isActive = isOverview || (featureNames && featureNames.includes(name));
            layer.unbindTooltip();
            if (isActive) {
                const style = isOverview ? (layer.feature.properties.level === 'block' ? styles.block : (layer.feature.properties.level === 'plot' ? styles.plot : styles.default)) : styles[role] || styles.default;
                if (layer.setStyle) layer.setStyle(style);
                layer.bindTooltip(name, {
                    permanent: !isOverview,
                    direction: 'top',
                    className: 'feature-label',
                    offset: [0, -10]
                });
                const layerBounds = layer.getBounds ? layer.getBounds() : L.latLngBounds([layer.getLatLng()]);
                bounds.extend(layerBounds);
                found = true;
            } else {
                if (layer.setStyle) layer.setStyle(styles.default);
            }
        });
        if (found) {
            map.fitBounds(bounds.pad(0.2));
        }
    }
    function updateUI() {
        document.querySelectorAll('.card').forEach((card, index) => {
            card.classList.toggle('active', index === currentStep);
        });
        document.getElementById('prevBtn').disabled = currentStep === 0;
        document.getElementById('nextBtn').disabled = currentStep === cards.length - 1;
        document.getElementById('step-indicator').textContent = `${currentStep + 1} / ${cards.length}`;
        const currentCard = cards[currentStep];
        highlightFeatures(currentCard.features, currentCard.role);
    }
    function nextCard() {
        if (currentStep < cards.length - 1) {
            currentStep++;
            updateUI();
        }
    }
    function prevCard() {
        if (currentStep > 0) {
            currentStep--;
            updateUI();
        }
    }
    initMap();
    createCards();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Build setup_wizard_2 wizard HTML")
    parser.add_argument("experiment_json")
    parser.add_argument("features_geojson")
    args = parser.parse_args()

    experiment_data = json.load(open(args.experiment_json, "r", encoding="utf-8"))
    geojson_data = json.load(open(args.features_geojson, "r", encoding="utf-8"))
    html = HTML_TEMPLATE.replace("__EXPERIMENT_DATA__", json.dumps(experiment_data))
    html = html.replace("__GEOJSON_DATA__", json.dumps(geojson_data))
    sys.stdout.write(html)


if __name__ == "__main__":
    main()
