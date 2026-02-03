<!--MapsComponent.vue

  - Figure out the lat/lon columns from the joined data
  - Display the joined data as markers on the map
  - Allow the user to edit layers, emit these to the parent on "save"
  - Re-render previously saved geoJson data

  @props:
    - joinedData: Array - The joined data to display on the map
    - geoJsonData: Array - The geoJson data to display on the map. Pass this back from the parent to maintain state across mounts of this component.

  @emits:
    - geoJsonData: Array - The geoJson data to display on the map. Pass this back from the parent to maintain state across mounts of this component.
-->
<template>

  <!-- Progress bar overlay
    - This is the progress bar that displays map save progress.
    - It is increased in length as captureProgress is increased in js.
    -->
  <div v-if="isCapturing" class="progress-overlay">
    <div class="progress-bar-container">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: captureProgress + '%'}"/>
      </div>
    </div>
  </div>

  <div class="map-container">
    <div id="map" class="map fade-in"></div>
  </div>
</template>

<script setup>

import { onMounted, watch, defineProps, ref, shallowRef, defineEmits } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw';
import 'leaflet-draw/dist/leaflet.draw.css';
// This import is needed to enable dragging of restored geoJson shapes.
// It is what enables PathDrag to work.
import 'leaflet-path-drag';

const props = defineProps({
  joinedData: {
    type: Array,
    required: true
  },
  geoJsonData: {
    type: Array,
    required: true
  }
});

// Event used to emit the geoJsonData to the parent.
const emit = defineEmits(['geoJsonData']);

// It is important that the leaflet elements are shallowRef. Vue's reactivity
// system does not work with leaflet's update/rendering system. For example,
// vue can handle pushing new markers or replacing the entire map, but leaflet
// must handle metadata updates to the layers themselves.

// Base map and markers, initialized in onMounted, populated by the watcher.
const map = shallowRef(null);
const markers = shallowRef([]);

// drawnItems is the container (FeatureGroup) for all drawn shapes.
// Every shape or circlemarker edited onto the map by the user is added as a
// new layer on the map through it.
const drawnItems = shallowRef(null);

// Pending data is stored by the watch handler when it's received before the
// map is initialized, and processed from onMounted.
const pendingData = ref(null);

const isCapturing = ref(false);
const captureProgress = ref(0);

/* Flatten a nested json object to a single level.

 * Only unnests objects, not arrays.
 *
 * @param {Object} obj - The object to flatten.
 * @param {string} parentKey - A key used to store data in the result dict.
 * @param {Object} result - A dict that stores state between invocations.
 *
 * @returns {Object} The flattened object.
 */
function flattenObject(obj, parentKey = '', result = {}) {
  for (const key in obj) {
    const value = obj[key];
    const newKey = parentKey ? `${parentKey}.${key}` : key;

    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      flattenObject(value, newKey, result);
    } else {
      result[newKey] = value;
    }
  }
  return result;
}

/* Detect latitude and longitude keys in a flattened json object.
 *
 * @param {Object} flattenedData - The flattened json object.
 * @returns {Object} An object with the latitude and longitude keys.
 */
function detectLatLong(flattenedData) {
  const latKeys = ['lat', 'latitude', 'lt'];
  const longKeys = ['long', 'longitude', 'lon', 'lng', 'ln'];

  for (const key in flattenedData) {
    if (latKeys.some(k => key.toLowerCase().includes(k))) {
      for (const otherKey in flattenedData) {
        if (longKeys.some(k => otherKey.toLowerCase().includes(k))) {
          return { latKey: key, lonKey: otherKey };
        }
      }
    }
  }
}

/* Process the joined data into points.
 *
 * - First identify the lat/lon keys in the joined data.
 * - Then extracts the coordinates from the data as an array of points.
 *
 * @param {Array} newData - The joined data.
 * @returns {Array} The points.
 */
function processMapPoints(newData) {
  let latKey = null;
  let lonKey = null;
  const points = [];

  for (const item of newData) {
    const flattened = flattenObject(item);

    // Find lat/lon keys if not already found
    if (!latKey || !lonKey) {
      const detectedKeys = detectLatLong(flattened);
      if (!detectedKeys) continue;
      ({ latKey, lonKey } = detectedKeys);
    }

    // Extract coordinates
    if (latKey in flattened && lonKey in flattened) {
      const lat = parseFloat(flattened[latKey]);
      const lon = parseFloat(flattened[lonKey]);
      points.push({ lat, lon });
    }
  }

  return points;
}

// Create styled markers for the map points.
function createMarkers(points) {
  const markersLayer = L.layerGroup();

  points.forEach(({ lat, lon }) => {
    const marker = L.circleMarker([lat, lon], {
      radius: 2,
      fillColor: "#3388ff",
      color: "#49AED6",
      weight: 1,
      opacity: 1,
      fillOpacity: 0.7,
    });
    markersLayer.addLayer(marker);
    markers.value.push(marker);
  });

  return markersLayer;
}

// Reset the marker layer on the map.
function clearExistingMarkers() {
  markers.value.forEach(marker => map.value.removeLayer(marker));
  markers.value = [];
}

/* Center the map view to fit the points.
 *
 * - Figure out the bounds of the points and zoom the map to fit them.
 *
 * @param {Array} points - The points to fit on the map.
 */
function centerMapView(points) {
  if (points.length === 0) {
    console.warn('No valid points found to display on the map.');
    return;
  }

  const bounds = L.latLngBounds(points.map(p => [p.lat, p.lon]));
  map.value.flyToBounds(bounds, {
    padding: [50, 50],
    maxZoom: 13,
    duration: 1,
    easeLinearity: 0.3,
  });
}

/* Main watch handler, triggered whenever the joinedData prop changes.
 *
 * Both watch and onMounted trigger the same set of functions. Watch triggers
 * them whenever there's a data change, onMounted triggers them when the
 * component is mounted.
 *
 * The second statement is a small lie. There is a race condition between watch * and onMounted. If the data is received in the watch while the map is being
 * initialized, it is not processed. Instead, the data is stored in pendingData
 * and processed from onMounted.
 */
watch(
  () => props.joinedData,
  (newData) => {
    if (!newData.length) return;

    if (!map.value) {
      // While nextTick would be a simpler way to handle this race, storing the
      // data in a member is more robust.
      pendingData.value = newData;
      return;
    }

    try {
      // Clear old markers
      clearExistingMarkers();

      // Process the data into points
      const points = processMapPoints(newData);

      // Add the points to the map
      const markersLayer = createMarkers(points);
      markersLayer.addTo(map.value);

      // Re-center the map on the points
      centerMapView(points);
    } catch (error) {
      console.error('Error updating map:', error);
    }
  },
  { immediate: true }
);

/* Initialize the map.
 *
 * - Create the map element.
 * - Initialize the draw controls (for "writers" only).
 * - Add a feature group container layer.
 * - Set the view to the center of the world.
 */
const initializeMap = () => {
  map.value = L.map(
    'map',
    {
      attributionControl: false,
      // zoomControl: false,
    }).setView([0, 0], 2);

  L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      crossOrigin: true,
    }
  ).addTo(map.value);

  // Add the feature group container to the map.
  // The feature group will contains layers.
  // Each drawing is a layer.
  // So the drawnItems will be populated with:
  // - writers: the drawn shapes (ignores the geoJsonData prop)
  // - readers: the restored shapes from the geoJsonData prop (no drawn shapes)
  drawnItems.value = new L.featureGroup();
  drawnItems.value.addTo(map.value);
  initializeWriterTools();
}

/* Initialize all the utils needed to draw on the map.
 *
 * This function is only meant for "writers" of the map.
 *
 * - Draw controls themselves.
 * - Container (feature group) for the drawn layers.
 * - Listener for the draw:created event.
 * - A save button that emits the drawn layers as geoJson to the parent.
 */
const initializeWriterTools = () => {
  const drawControl = new L.Control.Draw({
    position: 'topright',
    edit: {
      featureGroup: drawnItems.value,
      remove: true,
    },
    draw: {
      polygon: false,
      polyline: false,
      circle: false,
      marker: false,
      rectangle: {
        shapeOptions: {
          color: '#3388ff',
          weight: 2
        },
      },
    },
  });
  map.value.addControl(drawControl);

  const saveControl = L.Control.extend({
    options: {
      position: 'topright',
    },
    onAdd: function() {
      const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
      const button = L.DomUtil.create('a', '', container);
      button.innerHTML = '💾';
      button.title = 'Save Changes';
      button.style.fontSize = '20px';
      button.style.textAlign = 'center';
      button.style.cursor = 'pointer';

      // When the save button is clicked, serialize the drawn layers to geoJson
      // and emit them to the parent.
      L.DomEvent.on(button, 'click', captureMap);

      return container;
    }
  });
  map.value.addControl(new saveControl());

  // The draw:created event is triggered when a drawing is completed, i.e
  // the user clicks the mouse button to complete a polygon.
  // Each shape is a different layer, which we cache in the drawnItems feature
  // group. We also emit the geoJson data to the parent for storing/broadcasting
  // to other "readers" of the map on "save".
  map.value.on('draw:created', (e) => {
    const layer = e.layer;
    // Writers emit drawnItems when the save button is clicked.
    drawnItems.value.addLayer(layer);
  });
};

/* Capture the map.
 *
 * - Show a progress bar.
 * - Capture the drawn layers as geoJson.
 *
 * This function uses promises/async to ensure the progress bar is updated.
 * This is important because without feedback, the user will navigate away from * the component, cancelling the capture.
 *
 * @emits {Object} geoJsonData - The geoJson data and image.
 */
const captureMap = async () => {
  try {
    console.log('MapComponent: Starting capture process');

    // Show the progress bar
    isCapturing.value = true;
    captureProgress.value = 10;

    // Allow the DOM to update immediately
    // How does this work?
    // SetTimeout is a "javascript thing", and updating the UI is a "browser
    // thing". The browser typically prioritizes script execution, but when
    // it encounters a setTimeout, it stashes it on the "script stack" and uses
    // the opportunity to clear the "rendering stack". This only works because
    // the setTimeout function doesn't guarantee the time - only that at least
    // that much time has passed.
    // This behavior is part of the html spec - a mechanism to prevent
    // starvation of the UI thread:
    // https://html.spec.whatwg.org/multipage/timers-and-user-prompts.html
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Defer recording the layers
    const layers = await new Promise((resolve) => setTimeout(() => {
      const tempLayers = [];
      drawnItems.value.eachLayer((layer) => {
        tempLayers.push(toGeoJson(layer));
        if (captureProgress.value < 90) {
          captureProgress.value += 10;
        }
      });
      resolve(tempLayers);
    }, 100));
    // Cleanup the progress bar
    captureProgress.value = 100;
    setTimeout(() => {
      isCapturing.value = false;
      captureProgress.value = 0;
    }, 300);

    // Emit the GeoJSON data to the parent
    emit('geoJsonData', layers);
  } catch (error) {
    console.error('Error saving map:', error);

    // Cleanup on error
    isCapturing.value = false;
    captureProgress.value = 0;
  }
};
/* Convert a leaflet layer to geoJson.
 *
 * - Add style properties to the geoJson object for circle markers.
 *
 * @param {L.Layer} layer - The leaflet layer to convert to geoJson.
 * @returns {Object} The geoJson object.
 */
const toGeoJson = (layer) => {
    const geoJson = layer.toGeoJSON();

    // Most shapes, rectangles etc, are converted to geoJson as Polygon
    // objects. These have embedded style properties.
    // CircleMarkers are converted to geoJson as Point objects. These don't
    // have style properties, so add them here.
    if (layer instanceof L.CircleMarker) {
      geoJson.properties.style = {
        radius: layer.options.radius,
        color: layer.options.color,
        weight: layer.options.weight,
        opacity: layer.options.opacity,
        fillOpacity: layer.options.fillOpacity,
        fillColor: layer.options.fillColor,
      };
    }
    return geoJson;
}

/* Update the map layers with the geoJson data.
 *
 * This function assumes that all drawn layers are stored in the passed in
 * geoJsonArray, and that this layer DOES NOT contain any base points data -
 * i.e the data is only the drawn shapes, not from the joined datasets.
 *
 * - Clear the existing drawn layers (not including the joined "points" data).
 * - Add the new drawn layers.
 *
 * A note on geoJson <-> leaflet serialization:
 * - This process is not perfect. The geoJson data is not always serialized
 *   exactly as the user drew it. For example, the geoJson data does not
 *   contain the style properties, or the exact draw controls.
 *
 * @param {Array} geoJsonArray - The geoJson data to add to the map.
 */
const restoreMapLayers = (geoJsonArray) => {
  // Clear all layers in the feature group before trying to restore them.
  drawnItems.value.clearLayers();
  geoJsonArray.forEach((geoJson) => {
    const layer = L.geoJSON(geoJson, {
      pointToLayer: (feature, latlng) => {
        if (feature.properties.style) {
          return L.circleMarker(latlng, feature.properties.style);
        }
        return L.circleMarker(latlng);
      },
      style: (feature) => feature.properties.style
    });

    layer.eachLayer((subLayer) => {
      // Only enable dragging if the layer supports it
      if (typeof L.Handler.PathDrag !== 'undefined') {
        subLayer.options.draggable = true;
        new L.Handler.PathDrag(subLayer).enable();
      }
      drawnItems.value.addLayer(subLayer);
    });
  });
};

// Handle pending data in onMounted
onMounted(() => {
  console.log('MapComponent: onMounted');
  initializeMap();

  // Process pending data stored by the watch handler.
  if (pendingData.value) {
    const newData = pendingData.value;
    pendingData.value = null;

    // TODO: This is a duplicate of the code in the watch handler.
    const points = processMapPoints(newData);
    const markersLayer = createMarkers(points);
    markersLayer.addTo(map.value);
    centerMapView(points);
  }

  // Re-render geoJsonData (shapes drawn on a previous render of the map)
  restoreMapLayers(props.geoJsonData);
});

</script>

<style scoped>

/* Map styling
 * - most of the map styling is handled by leaflet.
 * - the fade-in animation is not strictly necessary, just a nice touch
 *
 * Progress bar styling
 * This occurs in 4 classes:
 * - overlay: blurs the map to indicate a non-interactive state
 * - container: positions the bar at the bottom right corner of the map
 * - bar: circular borders and sizing for the bar itself
 * - fill: filling for the bar itself
 */
.map-container {
  height: 100%;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.map {
  height: 50vh;
  width: 90%;
  overflow: hidden;
  border-radius: 10px;
  opacity: 0;
}

.fade-in {
  animation: fadeIn 0.5s ease-in forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.progress-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
}

/* Centered container for the progress bar */
.progress-bar-container {
  width: 20%;
  position: absolute;
  bottom: 10%;
  right: 6%;
}

.progress-bar {
  height: 8px;
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background-color: #F3B214;
  border-radius: 4px;
  transition: width 0.2s ease;
}

</style>
