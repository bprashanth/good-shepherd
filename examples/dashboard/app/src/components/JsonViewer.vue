<!-- JsonViewer.vue
  - Computes the joined data using the parentFieldsWithJoins and fullData
  - Displays the joined data

  @props:
    - fullData: Object - The full data from the excel file
    - parentTab: String - The name of the parent tab
    - parentFieldsWithJoins: Array - parent fields + joined child fields (i.e
       fields that have been dropped on them). The joined child fields can currently only contain "id" fields.

  @emits:
    - joinedData: Array - The joined data (parent + child fields) filtered to
      the map bounds.

  @TODO:
  - Decouple joining logic from the json viewer.
  - Display stats on data in json viewer panel.
-->
<template>
  <div class="json-viewport">
    <json-viewer
    v-if="props.fullData && props.parentTab"
    :value="joinedData[0]"
    theme="dark"
    sort
    />
    <div class="joined-data-stats">
      <div>
        <span>Objects: {{ joinedData.length }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { JsonViewer } from 'vue3-json-viewer';
import 'vue3-json-viewer/dist/index.css';
import { defineProps, computed, defineEmits } from 'vue';

const props = defineProps({
  fullData: Object,
  parentTab: String,
  parentFieldsWithJoins: Array,
  savedGeoJsonData: Array,
});

const emit = defineEmits(['joinedData']);

const joinedData = computed(() => {
  if(!props.fullData || !props.parentTab || !props.parentFieldsWithJoins) {
    return [];
  }
  console.log('Running join on', props.parentFieldsWithJoins);
  // Create a deep copy of the parent data.
  // TODO: can we use structuredClone here since fullData is a JSON object?
  const result = JSON.parse(JSON.stringify(props.fullData[props.parentTab]));

  result.forEach(parentRecord => {
    props.parentFieldsWithJoins.forEach(({name: parentField, joins}) => {
      joins.forEach(joinSpec => {
        const [childTab, childField] = joinSpec.split('.');
        const childData = props.fullData[childTab];

        if (!childData) return;

        // Find all matching child records
        const matches = childData.filter(childRecord =>
          childRecord[childField] === parentRecord[parentField]
        );

        // Create the new field name for the joined data.
        const joinedFieldName = `${childTab}.${childField}`;

        if (matches.length === 0) {
          parentRecord[joinedFieldName] = null;
        } else if (matches.length === 1) {
          parentRecord[joinedFieldName] = matches[0];
        } else {
          parentRecord[joinedFieldName] = matches;
        }
      });
    });
  });
  const filteredData = filterMapPoints(result, props.savedGeoJsonData);
  emit('joinedData', filteredData);
  return filteredData;
});


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
  // No lat/lon keys found.
  console.error('No lat/lon keys found in flattened joined data.');
  return undefined;
}

/* Process the joined data into points.
 *
 * - First identify the lat/lon keys in the joined data.
 * - Then extracts the coordinates from the data as an array of points.
 *
 * @param {Array} joinedData - The joined data.
 * @returns {Array} The points in the format
 *  { lat: number, lon: number, parent: Object }
 */
function processMapPoints(joinedData) {
  if (!joinedData.length) return [];

  // Detect keys once using first item
  const flattened = flattenObject(joinedData[0]);
  console.log('JsonViewer: Flattened joined data[0].length ', flattened.length);

  const detectedKeys = detectLatLong(flattened);
  if (!detectedKeys) return [];
  const { latKey, lonKey } = detectedKeys;
  console.log('JsonViewer: Detected lat/lon keys:', latKey, lonKey);

  return joinedData
    .map(item => {
      const flattened = flattenObject(item);
      if (!(latKey in flattened) || !(lonKey in flattened)) return null;

      const lat = parseFloat(flattened[latKey]);
      const lon = parseFloat(flattened[lonKey]);
      if (isNaN(lat) || isNaN(lon)) return null;

      return { lat, lon, parent: item };
    })
    .filter(point => point !== null);
}

/* Filter the joined data to points that fall within the saved GeoJSON data.
 *
 * @param {Array} joinedData - The joined data.
 * @param {Array} savedGeoJsonData - The saved GeoJSON data. This is expected
 * as an array of Features, eg:
 * {
 *   type: 'Feature',
 *   properties: {…},
 *   geometry: {
 *     type: 'Polygon',
 *     coordinates: [[lat, lon], [lat, lon], [lat, lon]]
 *   }
 * }
 *
 * @returns {Array} The filtered data (joined data within the geojson rects).
 */
function filterMapPoints(joinedData, savedGeoJsonData) {
  if (!savedGeoJsonData || savedGeoJsonData.length === 0) {
    return joinedData;
  }

  const boundingPolygons = savedGeoJsonData.filter(feature =>
    feature?.geometry?.type === 'Polygon' ||
    feature?.geometry?.type === 'Rectangle'
  );

  if (boundingPolygons.length === 0) {
    return joinedData;
  }

  console.log('JsonViewer: Bounding polygons', boundingPolygons.length);

  const points = processMapPoints(joinedData);
  const filteredPoints = points.filter(point => {
    const lat = point.lat;
    const lon = point.lon;
    return boundingPolygons.some(polygon => {
      return isPointInPolygon([lat, lon], polygon.geometry.coordinates[0]);
    });
  });

  return filteredPoints.map(point => point.parent);
}

/* Determine if a point is within a polygon.
 *
 * @param {Array} point - The point to check, [lat, lon]
 * @param {Array} polygon - The polygon to check against, [[lat, lon], ...]
 * @returns {boolean} True if the point is within the polygon, false otherwise.
 */
function isPointInPolygon(point, polygon) {
  const [lat, lon] = point;
  let inside = false;

  for (let i=0, j=polygon.length -1; i < polygon.length; j = i++) {
    const xi = polygon[i][0], yi = polygon[i][1];
    const xj = polygon[j][0], yj = polygon[j][1];

    const intersect = ((yi > lat) !== (yj > lat)) &&
      (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi);

    if (intersect) inside = !inside;
  }

  return inside;
}

</script>

<style scoped>

.json-viewport {
  width: 100%;
  height: 100%;
  overflow: auto;
}

.joined-data-stats {
  display: flex;
  flex-direction: column;
  color: #cfcfcf;
  font-family: monospace;
  font-size: 10px;
  padding: 20px;
}

/* JsonViewer styling
 * div.json-viewport (this code)
 * div.jv-container.jv-dark (background)
 * div.jv-code
 * span.jv-item,jv-string (text coloring)
*/
:deep(.jv-container) {
  font-size: 10px;
  font-weight: 600;
  text-align: left;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  background: rgb(21, 21, 21, 1.0);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  font-family: monospace;
  border-radius: 10px;
}

:deep(.jv-code) {
  padding: 10px;
}

</style>
