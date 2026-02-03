<!-- QueryTemplatePanel.vue

 * This component displays a list of query templates.
 * It emits a 'template-selected' event when a template is clicked.
 * It is up to the parent component to handle the 'template-selected' event and
 * re-emit it as necessary (eg: as a global event).
 *
 * @props: None
 *
 * @emits:
 *  - template-selected: the query template selected
 *
 * Example usage:
 * <QueryTemplatePanel @template-selected="handleTemplateSelected" />
 *
 * In the parent component (DataViewer.vue):
 * const handleTemplateSelected = (template) => {
 *   window.dispatchEvent(new CustomEvent('template-selected', {
 *     detail: { query: template }
 *   }));
 * }
-->

<template>
  <div class="query-template-panel">
    <!-- Query Creator -->
     <div class="custom-query-form">
       <div class="custom-query-input-container">
         <input class="custom-query-input" v-model="customSql" placeholder="Write a query.."/>
         <input class="custom-query-input" v-model="customLabel" placeholder="Describe the query in simple words.."/>
       </div>
       <button class="template-button" @click="saveCustomQuery">SAVE</button>
     </div>

    <!-- Query templates -->
    <div class="template-item"
    v-for="template in combinedTemplates"
    :key="template.label"
    @click="handleClick(template)">
      {{ template.label }}
      <button class="template-button" @click="onDeleteUserQuery(template.label, $event)">DEL</button>
    </div>
  </div>
</template>

<script setup>
import { defineEmits, ref, onMounted, computed } from 'vue';
import { saveUserQuery, getUserQueries, defaultTemplates, deleteUserQuery } from '../services/queryTemplateService';

const userTemplates = ref([]);
const customSql = ref('');
const customLabel = ref('');

const emit = defineEmits(['template-selected']);

/*
 * The templates to display in the UI.
 */
const combinedTemplates = computed(() => [
  ...userTemplates.value,
  ...defaultTemplates
]);

/*
 * Emit the clicked template to the parent.
 *
 * @param template: the NLQ template the user clicks on.
 */
function handleClick(template) {
  // Add default targetPanel and mode if not present
  const templateWithDefaults = {
    ...template,
    targetPanel: template.targetPanel || 'schema',
    mode: template.mode || 'replace'
  };
  emit('template-selected', templateWithDefaults);
}

/*
 * Save a custom query to the user's query templates (local storage).
 *
 * @param customSql: the SQL query to save.
 * @param customLabel: the description of the query to save.
 */
function saveCustomQuery() {
  if (customSql.value.trim() && customLabel.value.trim()) {
    const newTemplate = {
      label: customLabel.value.trim(),
      sqlTemplate: customSql.value.trim()
    };
    saveUserQuery(newTemplate);
    userTemplates.value.push(newTemplate);
    customSql.value = '';
    customLabel.value = '';
  }
}

/*
 * Delete a user query from the UI AND local storage.
 *
 * @param label: the label of the query to delete.
 * @param event: the event that triggered the deletion.
 */
function  onDeleteUserQuery(label, event) {
  event.stopPropagation();
  deleteUserQuery(label);
  userTemplates.value = userTemplates.value.filter(t=> t.label !== label);
}

onMounted(() => {
  // Populate all the saved user queries so the "computed" runs and shows them
  // in the UI.
  userTemplates.value = getUserQueries();
});
</script>

<style scoped>
.query-template-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  color: white;
  font-family: monospace;
  height: 100%;
  justify-content: flex-start;
}

.custom-query-input-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.custom-query-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.custom-query-input {
  background-color: #222;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  color: #fff;
  font-size: 10px;
  font-family: monospace;
  align-items: flex-end;
}

.custom-query-button {
  background-color: #317183;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  color: #fff;
  font-weight: bold;
  cursor: pointer;
  align-self: flex-end;
  font-size: 10px;
  /* height: 100%; */
}

.template-item {
  background-color: #3b3b3b;
  padding: 10px;
  margin: 2px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.template-item:hover {
  background-color: #4e4e4e;
}

.template-item:has(.template-button:hover) {
  background-color: #3b3b3b
}

.template-button {
  background-color: black;
  border: 1px solid #848484;
  border-radius: 2px;
  padding: 2px 4px;
  cursor: pointer;
  font-size: 8px;
  color: #848484;
  transition: background-color 0.2s ease;
  align-self: flex-end;
}

.template-button:hover {
  background-color: #848484;
  color: #000000;
}

</style>