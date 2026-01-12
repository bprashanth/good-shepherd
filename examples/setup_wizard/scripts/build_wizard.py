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
        <div id="card-container">
            <!-- Cards injected here -->
        </div>
        
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
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);
        
        geoJsonLayer = L.geoJSON(geoJsonData, {
            pointToLayer: function (feature, latlng) {
                // Convert Points to CircleMarkers for better styling
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
                // Initial static style, though highlightFeatures will override immediately
                switch (feature.properties.type) {
                    case 'Polygon': return {color: "#ff7800", weight: 2};
                    case 'LineString': return {color: "#3388ff", weight: 3};
                    default: return {color: "#000"};
                }
            },
            onEachFeature: function (feature, layer) {
                // layer.bindPopup(feature.properties.name); 
                // We use tooltips controlled by highlightFeatures now
            }
        }).addTo(map);
        
        if (geoJsonLayer.getLayers().length > 0) {
            map.fitBounds(geoJsonLayer.getBounds());
        }
    }

    function createCards() {
        // Handle potential nesting: verify if 'hierarchy' exists at root or inside properties
        let data = experimentData;
        
        // If root doesn't have hierarchy but properties does (and it's not just schema defs), switch.
        // But in our case, schema defs are in 'properties', so we prefer root if it has data.
        if (!data.hierarchy && data.properties && data.properties.hierarchy) {
             // This path is likely for pure schema validation output, but our file has data at root.
             data = data.properties;
        }
        
        // 1. Overview Card
        // Generate Tree Diagram
        let treeHTML = '<div class="hierarchy-tree">';
        if (data.hierarchy.block && data.hierarchy.block.features) {
            const blockCount = data.hierarchy.block.features.length;
            treeHTML += `<div class="tree-node root">Blocks (${blockCount})</div>`;
            
            // Assume homogeneous structure, take first block to show depth
            if (blockCount > 0 && data.hierarchy.block.children) {
                 const firstBlock = data.hierarchy.block.features[0];
                 const children = data.hierarchy.block.children[firstBlock] || [];
                 
                 if (children.length > 0) {
                     // Check if children are Transects or Plots
                     // Heuristic: Check if first child is in Transect list
                     let childType = "Children";
                     let grandChildType = null;
                     
                     if (data.hierarchy.transect && data.hierarchy.transect.features && data.hierarchy.transect.features.includes(children[0])) {
                         childType = "Transects";
                         // Check for plots under this transect
                         if (data.hierarchy.transect.children && data.hierarchy.transect.children[children[0]]) {
                             grandChildType = "Plots";
                         }
                     } else if (data.hierarchy.plot && data.hierarchy.plot.features && data.hierarchy.plot.features.includes(children[0])) {
                         childType = "Plots";
                     }
                     
                     
                     treeHTML += `<div class="tree-arrow">↓</div><div class="tree-node level-1">Approx. ${children.length} ${childType} per Block</div>`;
                     
                     if (grandChildType) {
                          // Try to get count from first transect
                          const grandChildren = data.hierarchy.transect.children[children[0]] || [];
                          treeHTML += `<div class="tree-arrow">↓</div><div class="tree-node level-2">Approx. ${grandChildren.length} ${grandChildType} per Transect</div>`;
                     }
                 }
            }
        }
        treeHTML += '</div>';

        // FORCE CORRECT BLOCK NAMES FOR DEBUGGING - The GeoJSON has them, the experiment.json has them.
        // If map doesn't show them, it's likely a mismatch in explicit string value or spaces.
        // Let's ensure the features list in block card uses the exact names from hierarchy.
        
        cards.push({
            id: 'overview',
            title: data.metadata ? data.metadata.title : "Experiment Setup",
            content: `
                <h3>Aim</h3>
                <p>${data.metadata ? data.metadata.aim : "No aim defined."}</p>
                <h3>Hierarchy</h3>
                ${treeHTML}
            `,
            features: null // null implies "Show All"
        });
        
        // 2. Block Level
        if (data.hierarchy.block && data.hierarchy.block.exists) {
             cards.push({
                id: 'blocks',
                title: data.hierarchy.block.name_in_protocol || "Blocks",
                content: `<p>${data.hierarchy.block.datasheet_description || "Upload datasheet for blocks."}</p>
                          <h4>Identified Blocks:</h4>
                          <ul>${(data.hierarchy.block.features || []).map(f => `<li>${f}</li>`).join('')}</ul>`,
                features: data.hierarchy.block.features,
                role: 'block'
             });
        }
        
        // 3. Transect Level
        if (data.hierarchy.transect && data.hierarchy.transect.exists) {
             cards.push({
                id: 'transects',
                title: data.hierarchy.transect.name_in_protocol || "Transects",
                content: `<p>${data.hierarchy.transect.datasheet_description || "Upload datasheet for transects."}</p>
                          <h4>Identified Transects:</h4>
                          <ul>${(data.hierarchy.transect.features || []).map(f => `<li>${f}</li>`).join('')}</ul>`,
                features: data.hierarchy.transect.features,
                role: 'transect'
             });
        }
        
         // 4. Plot Level
        if (data.hierarchy.plot && data.hierarchy.plot.exists) {
             cards.push({
                id: 'plots',
                title: data.hierarchy.plot.name_in_protocol || "Plots",
                content: `<p><strong>Dimensions:</strong> ${data.hierarchy.plot.dimensions}</p>
                          <p>${data.hierarchy.plot.datasheet_description || "Upload datasheet for plots."}</p>
                          <h4>Identified Plots:</h4>
                          <ul>${(data.hierarchy.plot.features || []).map(f => `<li>${f}</li>`).join('')}</ul>
                          <h4>Variables:</h4>
                          <div>${(data.hierarchy.plot.variables || []).map(v => `<span class="variable-tag">${v}</span>`).join('')}</div>`,
                features: data.hierarchy.plot.features,
                role: 'plot'
             });
        }
        
        renderCards();
        updateUI(); // Trigger initial map state
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
    
    // Styles
    const styles = {
        'default': { color: '#999', weight: 1, fillOpacity: 0.1, opacity: 0.4 },
        'block': { color: '#e67e22', weight: 3, fillOpacity: 0.2, opacity: 1 },
        'transect': { color: '#3498db', weight: 4, opacity: 1 },
        'plot': { color: '#2ecc71', weight: 2, fillOpacity: 0.6, opacity: 1 }
    };

    function highlightFeatures(featureNames, role) {
        let bounds = L.latLngBounds();
        let found = false;
        
        // If featureNames is null (Overview), show everything with specific logic
        const isOverview = (featureNames === null);

        geoJsonLayer.eachLayer(layer => {
            const name = layer.feature.properties.name;
            const geomType = layer.feature.geometry.type;
            
            // Determine if this feature is "active" based on the current card
            let isActive = isOverview; 
            if (!isOverview && featureNames && featureNames.includes(name)) {
                isActive = true;
            }
            
            // Cleanup previous tooltips
            layer.unbindTooltip();
            
            if (isActive) {
                // Determine style
                let style = styles['default'];
                
                if (isOverview) {
                    // In overview, match the colors used in the tree
                    // Blocks (Polygons that seem to be parents) -> Orange
                    // Transects -> Blue
                    // Plots -> Green
                    // Since we don't strictly know 'role' per feature here without lookup, we use heuristics or just geom
                    if (geomType === 'Polygon') {
                         // Heuristic: Larger polygons are blocks, smaller are plots.
                         // But better: use the experimentData lists to check role
                         if (experimentData.hierarchy.block.features.includes(name)) style = styles['block'];
                         else if (experimentData.hierarchy.plot.features.includes(name)) style = styles['plot'];
                         else style = { color: '#e67e22', weight: 2, fillOpacity: 0.1 }; // fallback to orange-ish
                    }
                    if (geomType === 'LineString') style = styles['transect'];
                } else {
                    // Active card with specific role
                    if (role) {
                         // Force the style for the current role
                         style = styles[role];
                    } else {
                        // Fallback if role is missing but feature is active
                         style = { color: 'red', weight: 3 }; 
                    }
                }
                
                layer.setStyle(style);
                
                // Add Label
                layer.bindTooltip(name, {
                    permanent: !isOverview, // Permanent labels only when drilling down
                    direction: 'top',
                    className: 'feature-label',
                    offset: [0, -10]
                });
                
                // Calculate bounds
                if (layer.getBounds) bounds.extend(layer.getBounds());
                else if (layer.getLatLng) bounds.extend(layer.getLatLng());
                found = true;
                
                // Ensure active features are on top of dimmed ones
                if (!isOverview && layer.bringToFront) {
                    layer.bringToFront();
                }
                
            } else {
                // Dimmed (Grey)
                layer.setStyle({
                    color: '#ccc',
                    weight: 1,
                    fillOpacity: 0.1,
                    opacity: 0.2
                });
            }
        });
        
        if (found) {
            map.fitBounds(bounds, {padding: [50, 50]});
        } else if (isOverview) {
             // Fit to whole layer
             if (geoJsonLayer.getBounds().isValid()) {
                 map.fitBounds(geoJsonLayer.getBounds());
             }
        }
    }

    function updateUI() {
        document.getElementById('prevBtn').disabled = currentStep === 0;
        document.getElementById('nextBtn').disabled = currentStep === cards.length - 1;
        document.getElementById('step-indicator').innerText = `${currentStep + 1} / ${cards.length}`;
        
        // Hide all cards, show current
        document.querySelectorAll('.card').forEach((el, idx) => {
            el.classList.toggle('active', idx === currentStep);
        });
        
        // Update Map
        const card = cards[currentStep];
        highlightFeatures(card.features, card.role);
    }

    window.nextCard = function() {
        if (currentStep < cards.length - 1) {
            currentStep++;
            updateUI();
        }
    };
    
    window.prevCard = function() {
        if (currentStep > 0) {
            currentStep--;
            updateUI();
        }
    };

    // Initialize
    initMap();
    createCards();

</script>
</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('experiment_json', help='Path to experiment.json')
    parser.add_argument('geojson_file', help='Path to features.geojson')
    args = parser.parse_args()
    
    with open(args.experiment_json) as f:
        exp_data = json.load(f)
        
    with open(args.geojson_file) as f:
        geojson_data = json.load(f)
        
    html = HTML_TEMPLATE.replace('__EXPERIMENT_DATA__', json.dumps(exp_data))
    html = html.replace('__GEOJSON_DATA__', json.dumps(geojson_data))
    
    print(html)

if __name__ == '__main__':
    main()
