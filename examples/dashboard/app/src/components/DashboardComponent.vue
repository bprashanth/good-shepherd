<template>
  <div class="professor-panel">
    <div class="quarter-panel">
      <!-- Map panel
        Props:
          - queryResult: contains the alasql query from the schema panel.
          - hoveredBoundary: contains the geojson boundary file from the hover / mouseover event of the "connections" panel.
       -->
      <MapComponent
      :queryResult="queryResult"
      :hoveredBoundary="hoveredBoundary"
      :geoJsonData="geoJsonData"
      @template-processed="handleTemplateProcessed('map')"
      :template="templateDispatch.map"/>
    </div>
    <div class="quarter-panel">
      <!-- Tabs: "schema queries" and "find connections" -->
      <div class="tab-bar">

        <button
        class="tab"
        :class="{ active: activeTab === 'schema' }"
        @click="activeTab = 'schema'"
        >
          Query
        </button>
        <button
        class="tab"
        :class="{ active: activeTab === 'connections'}"
        @click="activeTab = 'connections'"
        >
          Find Connections
        </button>

      </div>
      <div class="tab-content">

        <!-- Schema panel: runs the alasql queries
          Props:
            - field-selected: is the field being clicked, used to display images.
            - query-result-update: are the new points coming from the query results, used to update the map.
        -->
        <SchemaPanel
        v-if="activeTab === 'schema'"
        @field-selected="handleField"
        @query-result-updated="handleQuery"
        @template-processed="handleTemplateProcessed('schema')"
        :schema="schema"
        :noteUpdate="noteUpdate"
        :data="data"
        :template="templateDispatch.schema"/>

        <!-- Connections panel: displays the intersections of this study
            It passes out a prop to the map panel for the path to the geojson boundary of the clicked list result.
        -->
        <ConnectionsPanel
        v-if="activeTab === 'connections'"
        @update-hovered-boundary="handleBoundaryUpdate"/>
      </div>

    </div>
    <div class="quarter-panel">
      <ImagePanel
      :field="field"
      :queryResult="queryResult"
      @note-update="handleNoteUpdate"
      @template-processed="handleTemplateProcessed('image')"
      :template="templateDispatch.image"/>
    </div>
    <div class="quarter-panel">
      <SurveyResultPanel
      :queryResult="queryResult"
      @template-processed="handleTemplateProcessed('survey')"
      :template="templateDispatch.survey"/>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, onMounted, onBeforeUnmount } from 'vue';
import MapComponent from "./MapComponent.vue";
import SchemaPanel from "./SchemaPanel.vue";
import ImagePanel from "./ImagePanel.vue";
import SurveyResultPanel from "./SurveyResultPanel.vue";
import ConnectionsPanel from './ConnectionsPanel.vue';

// Handle and process props from other components.
// Eg the projects component opens up this page with each jobs schema and data.
// This "hydration" process happens via props.
const props = defineProps({
  schema: {
    type: Object,
    required: false
  },
  geoJsonData: {
    type: Array,
    required: false
  },
  data: {
    type: Array,
    required: false
  }
});

// Template dispatch state - routes templates to appropriate panels
const templateDispatch = ref({
  map: null,
  survey: null,
  schema: null,
  image: null
})

// This variable controls the active tab in the schema/query panel.
const activeTab = ref('schema');
const field = ref(null);
const fieldQueryResult = ref(null);
const queryResult = ref(props.data);

// hoveredBoundary contains the geojson of the connections panel mouseover
// events. It's emitted as an event in ConnectionsPanel and passed to
// MapComponent.
const hoveredBoundary = ref(null);

// NoteUpdate is an object:
// {
//   notes: [notes added to image],
//   fieldKey: 'key to image field',
//   fieldValue: 'value of image field'
// }
const noteUpdate = ref(null);

onMounted(() => {
  // Listen for template events from DataViewer
  window.addEventListener('template-selected', handleTemplateDispatch);
});

onBeforeUnmount(() => {
  window.removeEventListener('template-selected', handleTemplateDispatch);
});

function handleTemplateDispatch(event) {
  const template = event.detail.template;

  if (template) {
    // ALWAYS route to SchemaPanel first for query execution
    templateDispatch.value.schema = template;
    console.log('DashboardComponent: Routing template to SchemaPanel for execution:', template);
  } else {
    console.warn('DashboardComponent: Invalid template:', template);
  }
}

function handleTemplateProcessed(panelName) {
  console.log('DashboardComponent: Template processed by ${panelName} panel');
  // Clear the template after processing to prevent re-processing.
  templateDispatch.value[panelName] = null;
}

const handleNoteUpdate = (newNoteUpdate) => {
  console.log("DashboardComponent: handleNoteUpdate, newNoteUpdate: ", newNoteUpdate);
  noteUpdate.value = newNoteUpdate;
}

const handleField = ({ field: selectedField, queryResult: result }) => {
  field.value = selectedField;
  fieldQueryResult.value = result;
}

function handleQuery(result) {
  const currentTemplate = templateDispatch.value.schema;

  if (currentTemplate) {
    // Template execution - route to target panel
    templateDispatch.value[currentTemplate.targetPanel] = {
      ...currentTemplate,
      queryResults: result
    };
    templateDispatch.value.schema = null; // Clear after routing
  } else {
    clearAllTemplates();
    queryResult.value = result;
  }
}

function clearAllTemplates() {
  templateDispatch.value = {
    map: null,
    survey: null,
    schema: null,
    image: null
  }
}

const handleBoundaryUpdate = (newBoundary) => {
  hoveredBoundary.value = newBoundary;
  console.log(`Professor panel passing new boundary ${hoveredBoundary.value}`);
};
</script>

<style scoped>

.professor-panel{
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 10px;
  background-color: rgba(39, 37, 37, 0.8);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  width: 90vw;
  height: 90vh;
  padding: 20px;
  color: #e6c4a8;
  position: relative;
}

.quarter-panel {
  padding: 2px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  /* margin: 5px; */
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}

/* Styling for tabbed content in the schema query panel */
.tab-bar {
    position: absolute;
    top: -10px;
    right: 27px;
}

.tab {
    padding: 0.5em 1em;
    cursor: pointer;
    font-family: 'VT323', monospace;
    color: #afaeae;
    background-color: #282C34;
    border: 1px solid #444;
    border-radius: 8px 8px 0 0;
}

.tab.active {
  background-color: #1e1f25;
  font-weight: bold;
}

.tab-content {
  flex-grow: 1;
  width: 100%;
  height: 100%;
}
</style>
