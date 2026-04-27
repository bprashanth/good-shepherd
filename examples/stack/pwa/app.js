let map;
let plotContext;
let surveyTargets = [];
let currentTargetIndex = 0;
let pendingFile = null;

let adultLayer;
let subplotLayer;
let centerLayer;
let currentHighlightLayer;

let submissionState = {};

const OUTPUT_MANIFEST = {
    stage: "site_assessment",
    selected_plot_source: "../setup_wizard/output/selected_plot.json",
    uploads: [],
    advisory_events: []
};

document.addEventListener('DOMContentLoaded', async () => {
    initMap();
    await loadPlotContext();
    renderTargets();
    updateTargetDisplay();
    updateMapStyles();
});

function initMap() {
    map = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView([10.3541666665775, 76.97916666650352], 20);

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri'
    }).addTo(map);

    L.control.attribution({ position: 'bottomright' }).addTo(map);
}

async function loadPlotContext() {
    const response = await fetch('input/selected_plot.json');
    plotContext = await response.json();

    document.getElementById('plot-display').innerText = plotContext.plot_label || 'Plot 1';
    surveyTargets = plotContext.survey_targets.map((target) => ({
        ...target,
        submitted: false
    }));
    submissionState = Object.fromEntries(surveyTargets.map((target) => [target.id, false]));
}

function polygonStyle(color, fillOpacity = 0.14, weight = 2) {
    return {
        color,
        weight,
        opacity: 1,
        fillOpacity
    };
}

function renderTargets() {
    adultLayer = L.geoJSON(plotContext.adult_tree_plot.geometry, {
        style: () => polygonStyle('#2f81f7', 0.08, 2)
    }).addTo(map);

    subplotLayer = L.geoJSON({
        type: 'FeatureCollection',
        features: plotContext.quadrats.map((quadrat) => ({
            type: 'Feature',
            properties: { id: quadrat.id, label: quadrat.label },
            geometry: quadrat.geometry
        }))
    }, {
        style: (feature) => getTargetStyle(feature.properties.id),
        onEachFeature: (feature, layer) => {
            layer.bindTooltip(feature.properties.label, {
                permanent: false,
                className: 'custom-tooltip',
                direction: 'center'
            });
        }
    }).addTo(map);

    centerLayer = L.circleMarker([
        plotContext.center.coordinates[1],
        plotContext.center.coordinates[0]
    ], getCenterStyle()).addTo(map).bindTooltip('Center', {
        permanent: false,
        className: 'custom-tooltip',
        direction: 'top'
    });

    map.fitBounds(adultLayer.getBounds(), { padding: [24, 24], maxZoom: 21 });
    map.setZoom(Math.max(map.getZoom(), 20));
}

function getCurrentTarget() {
    return surveyTargets[currentTargetIndex];
}

function getTargetGeometry(targetId) {
    if (targetId === 'center') {
        return {
            type: 'Point',
            coordinates: plotContext.center.coordinates
        };
    }
    const quadrat = plotContext.quadrats.find((item) => item.id === targetId);
    return quadrat ? quadrat.geometry : null;
}

function getTargetStyle(targetId) {
    const active = getCurrentTarget().id === targetId;
    const submitted = submissionState[targetId];
    const color = submitted ? '#238636' : '#da3633';

    return polygonStyle(color, active ? 0.48 : 0.18, active ? 4 : 2);
}

function getCenterStyle() {
    const target = getCurrentTarget();
    const submitted = submissionState.center;
    const active = target.id === 'center';
    return {
        radius: active ? 6 : 4,
        fillColor: submitted ? '#238636' : '#da3633',
        color: '#ffffff',
        weight: active ? 2 : 1.5,
        opacity: 1,
        fillOpacity: active ? 0.8 : 0.68
    };
}

function updateMapStyles() {
    subplotLayer.setStyle((feature) => getTargetStyle(feature.properties.id));
    centerLayer.setStyle(getCenterStyle());

    if (currentHighlightLayer) {
        map.removeLayer(currentHighlightLayer);
        currentHighlightLayer = null;
    }

    const currentTarget = getCurrentTarget();
    const geometry = getTargetGeometry(currentTarget.id);

    if (geometry.type === 'Polygon') {
        currentHighlightLayer = L.geoJSON(geometry, {
            style: () => ({
                color: '#ffffff',
                weight: 1.5,
                opacity: 0.72,
                fillOpacity: 0
            })
        }).addTo(map);
        map.fitBounds(currentHighlightLayer.getBounds(), { padding: [90, 90], maxZoom: 21 });
    } else {
        const latlng = [geometry.coordinates[1], geometry.coordinates[0]];
        currentHighlightLayer = L.circleMarker(latlng, {
            radius: 10,
            color: '#ffffff',
            weight: 1.5,
            fillOpacity: 0
        }).addTo(map);
        map.setView(latlng, 21);
    }
}

function updateTargetDisplay() {
    const target = getCurrentTarget();
    document.getElementById('target-display').innerText = target.label;
}

function cycleTarget(direction = 1, event) {
    if (event) event.stopPropagation();
    if (!surveyTargets.length) return;

    currentTargetIndex = (currentTargetIndex + direction + surveyTargets.length) % surveyTargets.length;
    updateTargetDisplay();
    updateMapStyles();
}

function triggerUpload() {
    document.getElementById('fileInput').click();
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    pendingFile = file;
    const currentTarget = getCurrentTarget();
    document.getElementById('modalMeta').innerText = `${plotContext.plot_label || 'Plot 1'} • ${currentTarget.label}`;

    const reader = new FileReader();
    reader.onload = function (e) {
        document.getElementById('imagePreviewContainer').innerHTML = `<img src="${e.target.result}">`;
        document.getElementById('previewModal').classList.add('active');
    };
    reader.readAsDataURL(file);
    event.target.value = '';
}

function closeModal() {
    document.getElementById('previewModal').classList.remove('active');
    pendingFile = null;
}

function showAdvisory(message) {
    const banner = document.getElementById('advisoryBanner');
    banner.hidden = false;
    banner.innerText = message;
}

function hideAdvisory() {
    const banner = document.getElementById('advisoryBanner');
    banner.hidden = true;
    banner.innerText = '';
}

function submitFile() {
    if (!pendingFile) return;

    const currentTarget = getCurrentTarget();
    submissionState[currentTarget.id] = true;
    currentTarget.submitted = true;

    const advisoryTriggered = pendingFile.name.toLowerCase().includes('lantana');
    OUTPUT_MANIFEST.uploads.push({
        plot_id: plotContext.plot_id,
        plot_label: plotContext.plot_label || 'Plot 1',
        target_id: currentTarget.id,
        target_label: currentTarget.label,
        filename: pendingFile.name,
        advisory_triggered: advisoryTriggered
    });

    if (advisoryTriggered) {
        const message = 'This is lantana. Cut at the base, remove flowering material, and revisit the patch after regrowth.';
        OUTPUT_MANIFEST.advisory_events.push({
            target_id: currentTarget.id,
            filename: pendingFile.name,
            advisory: message
        });
        showAdvisory(message);
    } else {
        hideAdvisory();
    }

    closeModal();
    updateMapStyles();
}
