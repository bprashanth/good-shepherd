<!-- MapComponent.vue

@TODO:
  - This entire component needs a thorough refactor.
  - Zoom in on the query points
  - Add infocards for each point as a tool tip (map interactivity)
-->
<template>
  <div id="map-container">
    <div id="map"></div>
    <!-- Custom dropdown button -->
    <div id="basemap-dropdown">
      <button @click="toggleDropdown" class="dropdown-toggle">Basemap</button>
      <ul v-show="dropdownOpen" class="dropdown-menu">
        <li @click="switchBasemap('dark')">Dark</li>
        <li @click="switchBasemap('light')">Light</li>
        <li @click="switchBasemap('terrain')">Terrain</li>
      </ul>
    </div>
  </div>
</template>

<script>
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export default {
    name: "MapComponent",
    props: {
        template: {
            type: Object,
            default: null,
        },
        queryResult: {
            type: Array,
            default: () => [],
        },
        hoveredBoundary: {
            type: Object,
            default: null,
        },
        // TODO(prashanth@): remove this prop. It is currently unused and
        // passed as null from the parent.
        geoJsonData: {
            type: Array,
            default: () => [],
        },
    },
    data() {
        return {
            map: null,
            dropdownOpen: false,
            baseLayers: {
                // Stamen man: see docs
                // https://docs.stadiamaps.com/map-styles/stamen-toner/
                light: L.tileLayer(
                "https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}{r}.png",
                { maxZoom: 16 }
                ),
                dark: L.tileLayer(
                "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
                { maxZoom: 16 }
                ),
                terrain: L.tileLayer(
                "https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png",
                { maxZoom: 16 }
                ),
            },
            geoJsonLayers: [],

            // Layer holds the markers for the query result lat/long s
            markerLayer: null,

            // hoverLayer holds the incoming map boundary, from hover on the
            // surf tab.
            hoverLayer: null,
        }
    },

    mounted() {
      // On the use of nextTick:
      // Next tick forces onMounted to run after the DOM has updated (i.e in
      // the next tick after the update). This is necessary because the map
      // component is mounted before DOM is ready (onMounted is always called
      // in parallel with DOM prep and this is usually fine, unless onMounted
      // needs to access the DOM, like we need here for leaflet).
      this.$nextTick(() => {
        this.initializeMap();

        if (this.effectiveQueryResult && this.effectiveQueryResult.length > 0) {
            this.updateMarkers(this.effectiveQueryResult);
        }
      });
    },
    watch: {
        effectiveQueryResult: {
            immediate: true,
            handler(newData) {
                this.updateMarkers(newData);
            }
        },
        hoveredBoundary: {
            immediate: true,
            handler(newBoundary) {
                console.log(`received newBoundary ${newBoundary} on hover`);
                if (this.hoverLayer) {
                    this.map.removeLayer(this.hoverLayer);
                }
                if (newBoundary) {
                    this.hoverLayer = L.geoJSON(newBoundary, {
                        style: { color: "#ff7800", weight: 2, fillOpacity: 0.1 },
                    }).addTo(this.map);
                }
            },
        },
    },
    computed: {
      effectiveQueryResult() {
        return this.template?.queryResults || this.queryResult || [];
      }
    },
    methods: {

        // The next 3 methods are copied from WriterMapComponent.vue
        // TODO: Move them to a shared location.

        /* Flatten a nested json object to a single level.

        * Only unnests objects, not arrays.
        *
        * @param {Object} obj - The object to flatten.
        * @param {string} parentKey - A key used to store data in the result.
        * @param {Object} result - A dict that stores state between invocations.
        *
        * @returns {Object} The flattened object.
        */
        flattenObject(obj, parentKey = '', result = {}) {
          for (const key in obj) {
            const value = obj[key];
            const newKey = parentKey ? `${parentKey}.${key}` : key;

            if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
              this.flattenObject(value, newKey, result);
            } else {
              result[newKey] = value;
            }
          }
          return result;
        },
        /* Detect latitude and longitude keys in a flattened json object.
        *
        * @param {Object} flattenedData - The flattened json object.
        * @returns {Object} An object with the latitude and longitude keys.
        */
        detectLatLong(flattenedData) {
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
        },

        /* Process the joined data into points.
        *
        * - First identify the lat/lon keys in the joined data.
        * - Then extracts the coordinates from the data as an array of points.
        *
        * @param {Array} newData - The joined data.
        * @returns {Array} The points.
        */
        processMapPoints(newData) {
          let latKey = null;
          let lonKey = null;
          const points = [];

          for (const item of newData) {
            const flattened = this.flattenObject(item);

            // Find lat/lon keys if not already found
            if (!latKey || !lonKey) {
              const detectedKeys = this.detectLatLong(flattened);
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
        },

        // End copied methods from WriterMapComponent.vue

        initializeMap() {
            // Initialize the map with a default view first
            this.map = L.map("map", {
                attributionControl: false,
                zoomControl: false,
            });

            // Set a default view to ensure the map is properly initialized
            this.map.setView([0, 0], 2);

            // Add the Esri Gray (Light) basemap
            this.baseLayers.dark.addTo(this.map);

            // Load GeoJSON layers and fit bounds
            this.loadGeoJsonData();
        },
        loadGeoJsonData() {
            // Create a bounds object to track the extent of all layers
            const bounds = L.latLngBounds([]);

            this.geoJsonData.forEach(data => {
                const layer = L.geoJSON(data, {
                    // Points only: defines circle marker styling
                    pointToLayer: (feature, latlng) => {
                        return L.circleMarker(latlng, {
                            radius: 6,
                            fillColor: "#000000",
                            color: "#f7e306",
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 0.8,
                        });
                    },

                    // Non-points only: defines polygons/lines styling
                    style: (feature) => {
                        return feature.geometry.type === 'Point' ? undefined : {
                            color: "#1b5653",
                            weight: 2,
                            fillOpacity: 0.3
                        };
                    },

                    // All features: adds interactivity
                    onEachFeature: (feature, layer) => {
                        // Add popups and tooltips only for points
                        if (
                            feature.geometry.type === 'Point' &&
                            feature.properties?.name) {
                            layer.bindPopup(feature.properties.name);
                            layer.bindTooltip(feature.properties.name, {
                                permanent: false,
                                direction: "top",
                                className: "station-label",
                            });
                        }
                    },
                }).addTo(this.map);

                this.geoJsonLayers.push(layer);

                // Extend the bounds to include this layer
                bounds.extend(layer.getBounds());
            });

            // Fit the map to the bounds with some padding
            if (bounds.isValid()) {
              this.map.fitBounds(bounds, {
                  padding: [50, 50],  // Add 50px padding around the bounds
                maxZoom: 16        // Prevent zooming in too far
                });
            } else {
              this.centerOnQueryResultPoints();
            }
        },

        centerOnQueryResultPoints() {
          if (!this.effectiveQueryResult || !Array.isArray(this.effectiveQueryResult) || this.effectiveQueryResult.length === 0) {
            // Fallback to default world view
            this.map.setView([0, 0], 2);
            return;
          }

          const points = this.processMapPoints(this.effectiveQueryResult);
          if (points.length === 0) {
            // Fallback to default world view
            this.map.setView([0, 0], 2);
            return;
          }

          const bounds = L.latLngBounds(points.map(p => [p.lat, p.lon]));
          this.map.flyToBounds(bounds, {
            padding: [50, 50],
            maxZoom: 13,
            duration: 1,
            easeLinearity: 0.3,
          });
        },

        toggleDropdown() {
            this.dropdownOpen = !this.dropdownOpen;
        },
        switchBasemap(type) {
            Object.values(this.baseLayers).forEach((layer) => {
                if (this.map.hasLayer(layer)) {
                    this.map.removeLayer(layer);
                }
            });
            this.baseLayers[type].addTo(this.map);
            this.dropdownOpen = false;
        },
        updateMarkers(data) {
            if (!data) {
                return
            }
            if (!this.map) {
                return
            }
            const points = this.processMapPoints(data);
            console.log(`MapComponents points ${points.length}, ${Object.keys(points[0])}`);
            if (this.markerLayer) {
                this.map.removeLayer(this.markerLayer);
            }

            this.markerLayer = L.layerGroup();
            points.forEach(point => {
                if (point.lat && point.lon) {
                    const lat = point.lat;
                    const lng = point.lon;
                    const marker = L.circleMarker([lat, lng], {
                        radius: 2,
                        fillColor: "#3388ff",
                        color: "#3388ff",
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.7,
                    }).bindPopup(`Lat: ${lat}, Lng: ${lng}`);

                    this.markerLayer.addLayer(marker);
                }
            });

            this.markerLayer.addTo(this.map);

            // Center on the new points if no geoJsonData bounds were set
            if (!this.geoJsonData || this.geoJsonData.length === 0) {
              this.centerOnQueryResultPoints();
            }
        },
    },
};
</script>

<style scoped>
#map-container {
    position: relative;
    width: 100%;
    height: 100%;
}

#map{
    width: 100%;
    height: 100%;
    border-radius: 8px;
}

.station-label {
    background-color: transparent !important;
    border: none !important;
    color: black;
    font-size: 10px;
    font-weight: bold;
}

#basemap-dropdown {
    position: absolute;
    top: 0px;
    left: 0px;
    z-index: 1000;
}

.dropdown-toggle,
.dropdown-menu li {
  font-size: 14px;
  border-radius: 8px;
}

.dropdown-toggle {
    background: rgba(0, 0, 0, 0.6);
    color: #fff;
    padding: 8px 16px;
    border: none;
    cursor: pointer;
}

.dropdown-menu {
  position: absolute;
  top: 40px;
  left: 0;
  background: rgba(0, 0, 0, 0.8);
  list-style-type: none;
  padding: 0px 0;
  margin: 0;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  color: #fff;
}

.dropdown-menu li {
  padding: 8px 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.dropdown-menu li:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
