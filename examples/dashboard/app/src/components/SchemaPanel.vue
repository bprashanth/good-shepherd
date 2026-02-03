<!-- SchemaPanel.vue

@TODO:
  - This entire component needs a thorough refactor.
  - Find a way to manage large query sizes in JsonViewer.
  - Display the restricted query results info.
  - Merge duplication with ImagePanel (all the getValueByPath logic).
-->

<template>
    <div class="schema-panel">
        <div class="query-section">
            <textarea v-model="query" placeholder="select * from ? where survey->..."></textarea>
            <button @click="runQuery">Run</button>
        </div>
        <div class="schema-display">
            <div v-if="queryResult && Array.isArray(queryResult) && queryResult.length > 100" class="result-notice"
            >
                100/{{ queryResult.length }} results...
            </div>
            <JsonViewer :value="limitedQueryResult" sort theme="dark" @click="handleFieldClick"/>
        </div>
    </div>

    <!-- Query Template Modal -->
    <QueryTemplateModal
      :show="modalState.show"
      :placeholderName="modalState.placeholderName"
      :data="modalState.data"
      :template="modalState.template"
      :values="modalState.values"
      :keyFieldName="modalState.keyFieldName"
      @resolved="handleModalResolved"
      @close="handleModalClose"
    />
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, defineEmits, defineProps, computed, watch } from 'vue';
import alasql from 'alasql';

// https://www.npmjs.com/package/vue3-json-viewer
import { JsonViewer } from 'vue3-json-viewer';
import "vue3-json-viewer/dist/index.css";

import QueryTemplateModal from './QueryTemplateModal.vue';

// const schemaData = schemaDefinitions;
const emit = defineEmits(['field-selected', 'query-result-updated']);

const props = defineProps({
  schema: {
    type: Object,
    required: false
  },
  data: {
    type: Array,
    required: false
  },
  // Template is an object:
  // {
  //   sqlTemplate: 'SELECT * FROM ...',
  //   placeholderName: '...',
  //   data: [...],
  //   targetPanel: 'ImagePanel'
  // }
  template: {
    type: Object,
    required: false,
    default: null
  }
});
console.log("Props from schema panel ", props);

const query = ref('');
// Rather than import from assets like so:
// we keep all the data files in public/data and fetch them in onMounted.
const schemaDefinitions = ref(null);
const queryResult = ref(null);

watch (() => props.template, (newTemplate) => {
  if (newTemplate && newTemplate.sqlTemplate) {
    console.log('SchemaPanel: Auto-executing template: ', newTemplate);
    query.value = newTemplate.sqlTemplate;
    runQuery();
  }
}, { immediate: true });

// HACK: We limit the number of results to 100, because the JsonViewer is slow
// and crashes the browser when there are too many results. It also blocks
// rendering of subsequent queries. We need a long term solution here.
const limitedQueryResult = computed(() => {
    if (!queryResult.value) return null;
    if (Array.isArray(queryResult.value)) {
        return queryResult.value.slice(0, 100);
    }
    return queryResult.value;
});

onMounted(async () => {
    schemaDefinitions.value = props.schema;
    queryResult.value = schemaDefinitions.value;
    console.log("SchemaPanel: onMounted, schemaDefinitions: ", schemaDefinitions.value);
});

// Modal state
const modalState = ref({
  show: false,
  placeholderName: null,
  data: null,
  template: null,
  values: null
});

let modalResolveCallback = null;

// Listen for modal events
onMounted(() => {
  // No longer needed - direct function calls instead of events
});

onBeforeUnmount(() => {
  // No longer needed
});


function handleModalResolved(selection) {
  console.log("SchemaPanel: handleModalResolved: selection ", selection);
  if (modalResolveCallback) {
    modalResolveCallback(selection);
    modalResolveCallback = null;
  }
  modalState.value.show = false;
}

function handleModalClose() {
  modalState.value.show = false;
  modalResolveCallback = null;
}

async function runQuery() {
    console.log('Running query...')
    if (!props.data) {
        queryResult.value = { error: 'Data not loaded yet' };
        return;
    }

    try {
        let finalQuery;

        if (props.template && props.template.sqlTemplate) {
            finalQuery = await resolveTemplateQuery(props.template, props.data);
            if (!finalQuery) {
                throw new Error('Failed to resolve template placeholders');
            }
            query.value = finalQuery;
        } else {
            // This is a raw sql query, so we can just use it
            finalQuery = query.value;
        }

        console.log('Running query: ', finalQuery);
        queryResult.value = alasql(finalQuery, [props.data]); // Use props.data directly

        if (queryResult.value) {
            console.log("SchemaPanel: emitting query-result-updated with: ", queryResult.value)
            emit('query-result-updated', queryResult.value);
        }
    } catch (error) {
        console.error('Query Error:', error);
        queryResult.value = { error: 'Invalid Query: ' + error.message };
    }
}

// New function to handle template resolution
async function resolveTemplateQuery(template, data) {
  console.log("SchemaPanel: resolveTemplateQuery: template ", template, " data ", data);
  // Extract placeholders from template
  const placeholders = template.placeholders || extractPlaceholdersFromLabel(template.label);
  const placeholderPatterns = extractPlaceholderPatterns(template.sqlTemplate);

  if (placeholders.length === 0 && placeholderPatterns.length === 0) {
    // No placeholders - return template as-is
    return template.sqlTemplate;
  }

  // Resolve placeholders
  const resolvedPlaceholders = await resolvePlaceholders(template, data, placeholders, placeholderPatterns);

  if (!resolvedPlaceholders) {
    return null;
  }

  // Replace placeholders in SQL template
  return replacePlaceholdersInQuery(template.sqlTemplate, resolvedPlaceholders);
}

// Helper functions for placeholder resolution
function extractPlaceholdersFromLabel(label) {
  const placeholderRegex = /<(\w+)>/g;
  const placeholders = [];
  let match;

  while ((match = placeholderRegex.exec(label)) !== null) {
    placeholders.push(match[1]);
  }

  return placeholders;
}

function extractPlaceholderPatterns(sqlTemplate) {
  const patternRegex = /<(\w+_key|\w+_value)>/g;
  const patterns = [];
  let match;

  while ((match = patternRegex.exec(sqlTemplate)) !== null) {
    patterns.push(match[1]);
  }

  return patterns;
}

async function resolvePlaceholders(template, data, placeholders, placeholderPatterns) {
  const resolved = {};

  // Resolve placeholders from label
  for (const placeholder of placeholders) {
    const keyPattern = `${placeholder}_key`;
    const valuePattern = `${placeholder}_value`;

    // Check if this placeholder needs key resolution
    if (placeholderPatterns.includes(keyPattern)) {
      const key = await resolvePlaceholderKey(placeholder, data);
      if (!key) return null;
      resolved[keyPattern] = key;
    }

    // Check if this placeholder needs value resolution
    if (placeholderPatterns.includes(valuePattern)) {
      const value = await resolvePlaceholderValue(placeholder, data, resolved[keyPattern]);
      if (!value) return null;
      resolved[valuePattern] = value;
    }
  }

  // Resolve embedded unknowns (like timestamp_key)
  for (const pattern of placeholderPatterns) {
    if (!resolved[pattern] && pattern.endsWith('_key')) {
      const placeholderName = pattern.replace('_key', '');
      const key = await resolvePlaceholderKey(placeholderName, data);
      if (!key) return null;
      resolved[pattern] = key;
    }
    // TODO: Handle _value patterns for embedded unknowns
  }

  return resolved;
}

/**
 * Resolves a placeholder to a specific key in the given data.
 *
 * @param placeholderName - The name of the placeholder to resolve, e.g.
 *  "timestamp" (NB: the caller must strip the _key suffix)
 * @param data - The data to resolve the placeholder from, e.g. the list of raw
 *  json data objects.
 * @returns A promise that resolves to the resolved key, eg "date" for
 *  "timestamp"
 */
async function resolvePlaceholderKey(placeholderName, data) {
  return new Promise((resolve) => {
    // Show modal to choose a key
    modalState.value = {
      show: true,
      placeholderName,
      data,
      template: null,
      values: null
    };
    console.log("SchemaPanel: resolvePlaceholderKey: placeholder ", placeholderName, "  ", data, " modalState: ", modalState.value);
    // Store callback with the key result. This callback is invoked with the
    // selection object emitted by the QueryTemplateModal through
    // handleModalResolved.
    modalResolveCallback = (selection) => resolve(selection.key);
  });
}

/**
 * Resolves a placeholder to a specific value in the given data.
 *
 * @param placeholderName - The name of the placeholder to resolve, e.g.
 *  "timestamp" (NB: the caller must strip the _value suffix)
 * @param data - The data to resolve the placeholder from, e.g. the list of raw
 *  json data objects.
 * @param key - The key to resolve the placeholder from, e.g. "date" for
 *  "timestamp" will pass a list of all available dates and ask the user to
 *  choose a value. If the key is not found, the promise will resolve to null.
 * @returns A promise that resolves to the resolved value, eg "2025-01-01".
 */
async function resolvePlaceholderValue(placeholderName, data, key) {
  return new Promise((resolve) => {
    // Get unique values for the key
    const values = getUniqueValuesForKey(data, key);
    modalState.value = {
      show: true,
      placeholderName,
      data,
      template: null,
      keyFieldName: key,
      values
    };
    console.log("SchemaPanel: resolvePlaceholderValue: placeholder ", placeholderName, " key ", key, " modalState: ", modalState.value);
    modalResolveCallback = (selection) => resolve(selection.value);
  });
}

function getUniqueValuesForKey(data, key) {
  if (!data || data.length === 0) return [];

  const values = new Set();
  data.forEach(row => {
    if (row[key] !== undefined && row[key] !== null) {
      values.add(String(row[key]));
    }
  });

  return Array.from(values).sort();
}

function replacePlaceholdersInQuery(sqlTemplate, resolvedPlaceholders) {
  let finalQuery = sqlTemplate;

  for (const [pattern, value] of Object.entries(resolvedPlaceholders)) {
    finalQuery = finalQuery.replace(new RegExp(`<${pattern}>`, 'g'), value);
  }

  return finalQuery;
}


const handleFieldClick = (event) => {
    const target = event.target;
    if (!target) {
        console.log("No target event for click.")
        return
    }
    emit('field-selected', {
        field: target,
        queryResult: queryResult.value === schemaDefinitions.value ? null : queryResult.value
    })
};
</script>


<style scoped>
.schema-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    background-color: #282C34;
    border-radius: 8px;
}

textarea {
    width: 100%;
    resize: none;
    padding: 8px;
    font-family: monospace;
    background-color: #333;
    color: #ddd;
    border: 1px solid #555;
    border-radius: 4px;
}

button {
    padding: 6px 12px;
    cursor: pointer;
    background-color: #317183;
    color: #282C34;
    border: none;
    border-radius: 4px;
    font-weight: bold;
}

.query-section {
    display: flex;
    gap: 10px;
    padding: 10px;
}

.schema-display {
    overflow-y: auto;
    text-align: left;
}

.result-notice {
    padding: 8px;
    color: #317183;
    font-family: monospace;
    font-weight: bold;
    text-align: right;
}
</style>
