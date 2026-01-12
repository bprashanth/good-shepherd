
// State
let transects = [];
let plots = {}; // Map<TransectName, PlotData[]>
let transactionFeatures = {}; // Map<TransectName, Feature>
let plotFeatures = {}; // Map<PlotName, Feature>

// Submission State
let plotData = {}; // Map<PlotName, boolean> (true = submitted)

let currentTransectIndex = -1;
let currentPlotIndex = -1;
let currentTransectName = null;

// Map Components
let map;
let geoJsonLayer;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    initMap();
    await loadData();
});

function initMap() {
    // Center initially on roughly India or placeholder, will auto-fit
    map = L.map('map', {
        zoomControl: false, // Clean UI
        attributionControl: false
    }).setView([20, 78], 5); // India center roughly

    // Esri World Imagery (Terrain/Satellite)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri'
    }).addTo(map);

    // Add Attribution manually in a cleaner way if needed, or re-enable control with better styling
    L.control.attribution({ position: 'bottomright' }).addTo(map);
}

async function loadData() {
    try {
        const hRes = await fetch('experiment.json');
        const experiment = await hRes.json();

        // Parse Hierarchy
        // We need to extract Transect Names and their Plots
        // Look into experiment.hierarchy
        // We can assume the structure matches the one in setup_wizard

        // Parse Hierarchy
        // Valid hierarchy contains 'block', 'transect' etc.
        // Hierarchy at root is likely the data. Hierarchy inside 'properties' is likely schema.
        let hierarchy = experiment.hierarchy;

        if (!hierarchy && experiment.properties && experiment.properties.hierarchy) {
            hierarchy = experiment.properties.hierarchy;
        }

        // 1. Get Transect List
        if (hierarchy.transect && hierarchy.transect.features) {
            transects = hierarchy.transect.features;
        }

        // 2. Build Plot Map
        // The children map is inside the parent level. 
        // e.g. hierarchy.transect.children = { "T1": ["P1", "P2"] }
        // BUT wait, in the provided wizard.html, hierarchy.transect.children map seems to be Transect -> Plots.

        if (hierarchy.transect && hierarchy.transect.children) {
            plots = hierarchy.transect.children;
        }

        const gRes = await fetch('features.geojson');
        const geoJson = await gRes.json();

        // Add to Map and Index Features
        geoJsonLayer = L.geoJSON(geoJson, {
            style: getFeatureStyle,
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
            onEachFeature: (feature, layer) => {
                // Index features for quick access
                if (feature.properties && feature.properties.name) {
                    const name = feature.properties.name;
                    const type = feature.geometry.type;

                    if (transects.includes(name)) {
                        transactionFeatures[name] = feature;
                    }
                    // For plots, we check if they are in any of the plot lists
                    // Just store all polygons that aren't blocks? 
                    // Better: check if hierarchy.plot.features includes it
                    if (hierarchy.plot && hierarchy.plot.features && hierarchy.plot.features.includes(name)) {
                        plotFeatures[name] = feature;
                        // Initialize state
                        plotData[name] = false;
                    }
                }

                // Bind Tooltips
                layer.bindTooltip(feature.properties.name, {
                    permanent: false,
                    className: 'custom-tooltip',
                    direction: 'center'
                });
            }
        }).addTo(map);

        if (transects.length > 0) {
            map.fitBounds(geoJsonLayer.getBounds());

            // Mock User Location (Near A_T1 start)
            if (transactionFeatures['A_T1']) {
                const geom = transactionFeatures['A_T1'].geometry;
                let startPoint = null;
                // Assuming LineString
                if (geom.type === 'LineString') {
                    startPoint = geom.coordinates[0]; // [Lng, Lat] usually in GeoJSON
                }

                if (startPoint) {
                    // GeoJSON is Lng,Lat. Leaflet wants Lat,Lng
                    const userLatLng = [startPoint[1], startPoint[0]];

                    // Add User Marker (Use a high z-index pane or bring to front)
                    const userMarker = L.circleMarker(userLatLng, {
                        radius: 8, // Larger
                        fillColor: "#ffd700", // Gold
                        color: "#000000", // Black stroke for contrast
                        weight: 2,
                        opacity: 1,
                        fillOpacity: 1,
                        pane: 'markerPane' // Ensure on top of vectors
                    }).addTo(map).bindPopup("Current Location").openPopup();

                    // console.log("Added user marker at", userLatLng);
                }
            }
        }

    } catch (e) {
        console.error("Failed to load data", e);
        alert("Error loading experiment data. Check console.");
    }
}

// Styling Logic
function getFeatureStyle(feature) {
    const name = feature.properties.name;
    const type = feature.geometry.type;

    // Default Style (Dimmed)
    // Red/Green logic applies to PLOTS
    // Blue for TRANSECTS

    // Check if it's a plot
    if (plotFeatures[name]) {
        // It's a plot
        const isDone = plotData[name];
        const isSelected = (currentTransectName && plots[currentTransectName] && plots[currentTransectName][currentPlotIndex] === name);

        // Base Color
        const color = isDone ? '#238636' : '#da3633'; // Green : Red

        if (isSelected) {
            return {
                color: color,
                weight: 4,
                opacity: 1,
                fillOpacity: 0.6,
                // "Glow" simulated by weight/opacity or handled in CSS class if we used SVG classes (Leaflet paths use SVG)
                // We can add a classname via onEachFeature but style function returns path options.
                // We'll stick to bold weight.
            };
        } else {
            // Not selected plot
            // If we are looking at its transect, show it decently.
            // If we are looking at another transect, dim it?
            // User Requirement: "show the map at the center... cycle through all plots in t1 visually, then go to t2"
            // Implies we probably just show everything but highlight current.
            return {
                color: color,
                weight: 1,
                opacity: 0.6,
                fillOpacity: 0.2
            };
        }
    }

    // Transects (LineString usually)
    if (transactionFeatures[name]) {
        const isSelected = (currentTransectName === name);
        if (isSelected) {
            return { color: '#2f81f7', weight: 5, opacity: 1 };
        } else {
            return { color: '#2f81f7', weight: 2, opacity: 0.3 };
        }
    }

    // Blocks/Other
    return { color: '#888', weight: 1, opacity: 0.1, fillOpacity: 0.05 };
}

function updateMapStyles() {
    geoJsonLayer.setStyle(getFeatureStyle);

    // Force specific layers to front
    geoJsonLayer.eachLayer(layer => {
        const name = layer.feature.properties.name;
        // If selected plot or transect, bring to front
        if (name === currentTransectName) layer.bringToFront();
        if (currentTransectName && plots[currentTransectName] && plots[currentTransectName][currentPlotIndex] === name) {
            layer.bringToFront();
            layer.openTooltip();
        } else {
            layer.closeTooltip();
        }
    });
}

// Interaction Logic
function cycleTransect(direction = 1, event) {
    if (event) event.stopPropagation();
    if (transects.length === 0) return;

    currentTransectIndex = (currentTransectIndex + direction + transects.length) % transects.length;
    currentTransectName = transects[currentTransectIndex];

    // Update Display
    document.getElementById('transect-display').innerText = currentTransectName;

    // Reset Plot Selection
    currentPlotIndex = -1;
    document.getElementById('plot-display').innerText = "Select"; // or "-"

    // Highlight and Zoom
    updateMapStyles();

    // Zoom to specific feature
    zoomToFeature(currentTransectName);
}

function cyclePlot(direction = 1, event) {
    if (event) event.stopPropagation();
    if (!currentTransectName) {
        // If no transect selected, maybe select first?
        cycleTransect(1);
        return;
    }

    const plotList = plots[currentTransectName] || [];
    if (plotList.length === 0) {
        alert("No plots in this transect");
        return;
    }

    currentPlotIndex = (currentPlotIndex + direction + plotList.length) % plotList.length;
    const currentPlotName = plotList[currentPlotIndex];

    document.getElementById('plot-display').innerText = currentPlotName;

    updateMapStyles();
    zoomToFeature(currentPlotName);
}

function zoomToFeature(name) {
    let targetLayer = null;
    geoJsonLayer.eachLayer(layer => {
        if (layer.feature.properties.name === name) {
            targetLayer = layer;
        }
    });

    if (targetLayer) {
        map.fitBounds(targetLayer.getBounds(), { padding: [50, 50], maxZoom: 19 });
    }
}

// File Upload Logic
function triggerUpload() {
    // Only allow if a plot is selected?
    if (currentPlotIndex === -1 || !currentTransectName) {
        alert("Please select a plot first.");
        return;
    }
    document.getElementById('fileInput').click();
}

let pendingFile = null;

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        pendingFile = file;

        const reader = new FileReader();
        reader.onload = function (e) {
            const container = document.getElementById('imagePreviewContainer');
            container.innerHTML = `<img src="${e.target.result}">`;
            document.getElementById('previewModal').classList.add('active');
        };
        reader.readAsDataURL(file);
    }
    // Reset input
    event.target.value = '';
}

function closeModal() {
    document.getElementById('previewModal').classList.remove('active');
    pendingFile = null;
}

function submitFile() {
    if (!pendingFile) return;

    // Mark current plot as DONE
    const currentPlotName = plots[currentTransectName][currentPlotIndex];
    plotData[currentPlotName] = true;

    console.log(`Submitted data for ${currentPlotName}`);

    closeModal();
    updateMapStyles(); // Will turn green
}
