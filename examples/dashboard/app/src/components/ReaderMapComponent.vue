<!-- ReaderMapComponent.vue

  - Does essentially the same as MapsComponent.vue, but without the
    ability to draw on the map. In other words, only displays the map.

  @props:
    - geoJsonData: Array - The geoJson data to display on the map.
    - mapId: String - The id of the map element. This is so it doesn't conflict
      with MapComponent.vue.

  @emits: None

  @TODO:
    - Merge this with MapsComponent.vue. There is some problem with
      re-rendering the same vue component in 2 places of the same page.
      Even with unique ids, it doesn't work.
-->
<template>
  <div class="map-container">
    <div :id="mapId" class="map fade-in"></div>
  </div>
</template>

<script setup>
import { onMounted, defineProps, shallowRef, nextTick, watch } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const props = defineProps({
  geoJsonData: {
    type: Array,
    required: true
  },
  mapId: {
    type: String,
    required: true
  }
});

const map = shallowRef(null);
const geoJsonLayer = shallowRef(null);

const initializeMap = () => {
  // Why nextTick?
  // - This component uses props.mapId to create the main div.
  // - This leads to a race condition, where vue needs to retrieve and pass the
  //   mapId to the component, which is then mounted in the DOM, and only once
  //   it's mounted should leaflet try to initialize the map object.
  nextTick(() => {
    map.value = L.map(
      props.mapId,
    {
      attributionControl: false,
      zoomControl: false,
    }).setView([0, 0], 2);

    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
      {
        maxZoom: 19,
        crossOrigin: true,
      }
    ).addTo(map.value);

    renderGeoJson();
  });
};

const renderGeoJson = () => {
  if (!map.value || !props.geoJsonData.length) return;

  // Clear existing geoJSON layer if it exists
  if (geoJsonLayer.value) {
    map.value.removeLayer(geoJsonLayer.value);
  }

  // Create new layer with the geoJSON data
  geoJsonLayer.value = L.geoJSON(props.geoJsonData, {
    pointToLayer: (feature, latlng) => {
      if (feature.properties.style) {
        return L.circleMarker(latlng, feature.properties.style);
      }
      return L.circleMarker(latlng);
    },
    style: (feature) => feature.properties.style
  }).addTo(map.value);

  // Center the map on the geoJSON data
  const bounds = geoJsonLayer.value.getBounds();
  if (bounds.isValid()) {
    console.log('Fitting to bounds:', bounds);
    map.value.fitBounds(bounds, {
      padding: [5, 5],
      maxZoom: 13,
      animate: false
    });
  }
};

// Initialize map on mount
onMounted(() => {
  initializeMap();
});

// Watch for changes in geoJsonData
watch(
  () => props.geoJsonData,
  () => renderGeoJson()
);
</script>

<style scoped>
.map-container {
  height: 100%;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.map {
  width: 80%;
  height: 80%;
  border-radius: 10px;
  opacity: 0;
  border: 1px solid #ccc;
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
</style>
