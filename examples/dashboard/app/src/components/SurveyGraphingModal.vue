<!-- SurveyGraphingModal.vue

A multi-step modal for selecting survey graphing parameters.
Step 1: Select question field (e.g., responses->question)
Step 2: Select question value (e.g., "Was there litter?")
Step 3: Select answer field (e.g., responses->answer)
Step 4: Select timestamp field (e.g., timestamp)

@props:
  - show: boolean to control modal visibility
  - data: the data array to search through
  - template: the template object with sqlTemplate

@emits:
  - close: when modal is closed
  - resolved: when all parameters are selected with the resolved field mappings
-->
<template>
  <div v-if="show" class="modal-overlay" @click.self="closeModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>{{ modalTitle }}</h3>
        <button class="modal-close" @click="closeModal">&times;</button>
      </div>

      <div class="modal-content">
        <!-- Step 1: Select Question Field -->
        <div v-if="step === 1" class="step-content">
          <p>Select the field that contains survey questions:</p>
          <div class="field-suggestions">
            <div
              v-for="field in suggestedQuestionFields"
              :key="field"
              class="suggestion-item"
              @click="selectQuestionField(field)"
            >
              {{ field }} (suggested)
            </div>
          </div>
          <div class="dropdown-container">
            <button class="dropdown-button" @click="toggleQuestionDropdown">
              {{ selectedQuestionField || 'Select question field...' }}
              <span class="dropdown-arrow">▼</span>
            </button>
            <div v-if="showQuestionDropdown" class="dropdown-menu">
              <div
                v-for="field in allQuestionFields"
                :key="field"
                class="dropdown-item"
                @click="selectQuestionField(field)"
              >
                {{ field }}
              </div>
            </div>
          </div>
        </div>

        <!-- Step 2: Select Question Value -->
        <div v-if="step === 2" class="step-content">
          <p>Select which question to graph:</p>
          <div class="value-list">
            <div
              v-for="value in uniqueQuestionValues"
              :key="value"
              class="value-item"
              @click="selectQuestionValue(value)"
            >
              {{ value }}
            </div>
          </div>
        </div>

        <!-- Step 3: Select Answer Field -->
        <div v-if="step === 3" class="step-content">
          <p>Select the field that contains answers:</p>
          <div class="field-suggestions">
            <div
              v-for="field in suggestedAnswerFields"
              :key="field"
              class="suggestion-item"
              @click="selectAnswerField(field)"
            >
              {{ field }} (suggested)
            </div>
          </div>
          <div class="dropdown-container">
            <button class="dropdown-button" @click="toggleAnswerDropdown">
              {{ selectedAnswerField || 'Select answer field...' }}
              <span class="dropdown-arrow">▼</span>
            </button>
            <div v-if="showAnswerDropdown" class="dropdown-menu">
              <div
                v-for="field in allAnswerFields"
                :key="field"
                class="dropdown-item"
                @click="selectAnswerField(field)"
              >
                {{ field }}
              </div>
            </div>
          </div>
        </div>

        <!-- Step 4: Select Timestamp Field -->
        <div v-if="step === 4" class="step-content">
          <p>Select the field that contains timestamps:</p>
          <div class="field-suggestions">
            <div
              v-for="field in suggestedTimestampFields"
              :key="field"
              class="suggestion-item"
              @click="selectTimestampField(field)"
            >
              {{ field }} (suggested)
            </div>
          </div>
          <div class="dropdown-container">
            <button class="dropdown-button" @click="toggleTimestampDropdown">
              {{ selectedTimestampField || 'Select timestamp field...' }}
              <span class="dropdown-arrow">▼</span>
            </button>
            <div v-if="showTimestampDropdown" class="dropdown-menu">
              <div
                v-for="field in allTimestampFields"
                :key="field"
                class="dropdown-item"
                @click="selectTimestampField(field)"
              >
                {{ field }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button v-if="step > 1" @click="goBack" class="back-button">Back</button>
        <button
          v-if="canProceed"
          @click="nextStep"
          class="next-button"
        >
          {{ step === 4 ? 'Generate Graph' : 'Next' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineProps, defineEmits } from 'vue';

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  data: {
    type: Array,
    required: true
  },
  template: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['close', 'resolved']);

const step = ref(1);
const selectedQuestionField = ref(null);
const selectedQuestionValue = ref(null);
const selectedAnswerField = ref(null);
const selectedTimestampField = ref(null);

const showQuestionDropdown = ref(false);
const showAnswerDropdown = ref(false);
const showTimestampDropdown = ref(false);

const modalTitle = computed(() => {
  const titles = {
    1: 'Select Question Field',
    2: 'Select Question Value',
    3: 'Select Answer Field',
    4: 'Select Timestamp Field'
  };
  return titles[step.value];
});

// Get all available fields (including nested ones)
const allFields = computed(() => {
  if (!props.data?.length) return [];

  const fields = [];
  const firstRow = props.data[0];

  for (const [key, value] of Object.entries(firstRow)) {
    if (typeof value === 'object' && value !== null) {
      // Handle arrays of objects (like responses)
      if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'object') {
        // Add fields from the first object in the array
        for (const [nestedKey, nestedValue] of Object.entries(value[0])) {
          if (typeof nestedValue !== 'object' || nestedValue === null) {
            fields.push(`${key}->${nestedKey}`);
          }
        }
      } else if (!Array.isArray(value)) {
        // Handle regular nested objects
        for (const [nestedKey, nestedValue] of Object.entries(value)) {
          if (typeof nestedValue !== 'object' || nestedValue === null) {
            fields.push(`${key}->${nestedKey}`);
          }
        }
      }
    } else {
      fields.push(key);
    }
  }

  return fields.sort();
});

// Question field suggestions and options
const suggestedQuestionFields = computed(() => {
  return allFields.value.filter(field =>
    field.toLowerCase().includes('question') ||
    field.includes('responses->question')
  );
});

const allQuestionFields = computed(() => allFields.value);

// Answer field suggestions and options
const suggestedAnswerFields = computed(() => {
  return allFields.value.filter(field =>
    field.toLowerCase().includes('answer') ||
    field.includes('responses->answer')
  );
});

const allAnswerFields = computed(() => allFields.value);

// Timestamp field suggestions and options
const suggestedTimestampFields = computed(() => {
  return allFields.value.filter(field =>
    field.toLowerCase().includes('timestamp') ||
    field.toLowerCase().includes('date') ||
    field.toLowerCase().includes('time') ||
    field.toLowerCase().includes('created')
  );
});

const allTimestampFields = computed(() => allFields.value);

// Get unique question values for selected field
const uniqueQuestionValues = computed(() => {
  if (!selectedQuestionField.value || !props.data) return [];

  const values = new Set();
  props.data.forEach(row => {
    const value = getFieldValue(row, selectedQuestionField.value);
    if (Array.isArray(value)) {
      value.forEach(v => {
        if (v !== null && v !== undefined) {
          values.add(String(v));
        }
      });
    } else if (value !== null && value !== undefined) {
      values.add(String(value));
    }
  });

  return Array.from(values).sort();
});

// Helper function to get nested field values
const getFieldValue = (data, key) => {
  if (!key.includes('->')) {
    return data[key];
  }
  const [parentKey, childKey] = key.split('->');

  const parentValue = data[parentKey];
  if (Array.isArray(parentValue)) {
    // For arrays, return all values from the childKey
    return parentValue.map(item => item[childKey]).filter(val => val !== null && val !== undefined);
  } else {
    return parentValue?.[childKey];
  }
};

const canProceed = computed(() => {
  switch (step.value) {
    case 1: return selectedQuestionField.value !== null;
    case 2: return selectedQuestionValue.value !== null;
    case 3: return selectedAnswerField.value !== null;
    case 4: return selectedTimestampField.value !== null;
    default: return false;
  }
});

// Event handlers
function selectQuestionField(field) {
  selectedQuestionField.value = field;
  showQuestionDropdown.value = false;
  if (step.value === 1) nextStep();
}

function selectQuestionValue(value) {
  selectedQuestionValue.value = value;
  nextStep();
}

function selectAnswerField(field) {
  selectedAnswerField.value = field;
  showAnswerDropdown.value = false;
  if (step.value === 3) nextStep();
}

function selectTimestampField(field) {
  selectedTimestampField.value = field;
  showTimestampDropdown.value = false;
  if (step.value === 4) nextStep();
}

function toggleQuestionDropdown() {
  showQuestionDropdown.value = !showQuestionDropdown.value;
}

function toggleAnswerDropdown() {
  showAnswerDropdown.value = !showAnswerDropdown.value;
}

function toggleTimestampDropdown() {
  showTimestampDropdown.value = !showTimestampDropdown.value;
}

function nextStep() {
  if (step.value === 4) {
    resolveSurveyGraphing();
  } else {
    step.value++;
  }
}

function goBack() {
  step.value--;
}

function resolveSurveyGraphing() {
  const fieldMappings = {
    questionField: selectedQuestionField.value,
    questionValue: selectedQuestionValue.value,
    answerField: selectedAnswerField.value,
    timestampField: selectedTimestampField.value
  };

  emit('resolved', fieldMappings);
  closeModal();
}

function closeModal() {
  step.value = 1;
  selectedQuestionField.value = null;
  selectedQuestionValue.value = null;
  selectedAnswerField.value = null;
  selectedTimestampField.value = null;
  showQuestionDropdown.value = false;
  showAnswerDropdown.value = false;
  showTimestampDropdown.value = false;
  emit('close');
}

// Reset when modal opens
watch(() => props.show, (newShow) => {
  if (newShow) {
    step.value = 1;
    selectedQuestionField.value = null;
    selectedQuestionValue.value = null;
    selectedAnswerField.value = null;
    selectedTimestampField.value = null;
    showQuestionDropdown.value = false;
    showAnswerDropdown.value = false;
    showTimestampDropdown.value = false;
  }
});
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-card {
  background-color: #333;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #555;
}

.modal-header h3 {
  margin: 0;
  color: #fff;
  font-family: monospace;
}

.modal-close {
  background: none;
  border: none;
  color: #fff;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  padding: 20px;
  flex-grow: 1;
  overflow-y: auto;
}

.step-content {
  min-height: 200px;
}

.field-suggestions {
  margin-bottom: 15px;
}

.suggestion-item {
  background-color: #444;
  padding: 10px;
  margin: 5px 0;
  border-radius: 4px;
  cursor: pointer;
  color: #fff;
  font-family: monospace;
  border: 2px solid #317183;
}

.suggestion-item:hover {
  background-color: #555;
}

.dropdown-container {
  position: relative;
  margin-bottom: 15px;
}

.dropdown-button {
  width: 100%;
  padding: 10px;
  background-color: #444;
  color: #fff;
  border: 1px solid #555;
  border-radius: 4px;
  cursor: pointer;
  font-family: monospace;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dropdown-arrow {
  transition: transform 0.2s;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background-color: #444;
  border: 1px solid #555;
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 10;
}

.dropdown-item {
  padding: 10px;
  cursor: pointer;
  color: #fff;
  font-family: monospace;
  border-bottom: 1px solid #555;
}

.dropdown-item:hover {
  background-color: #555;
}

.value-list {
  max-height: 300px;
  overflow-y: auto;
}

.value-item {
  background-color: #444;
  padding: 10px;
  margin: 5px 0;
  border-radius: 4px;
  cursor: pointer;
  color: #fff;
  font-family: monospace;
}

.value-item:hover {
  background-color: #555;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #555;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.back-button, .next-button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: monospace;
  font-weight: bold;
}

.back-button {
  background-color: #666;
  color: #fff;
}

.next-button {
  background-color: #317183;
  color: #282C34;
}

.next-button:disabled {
  background-color: #555;
  cursor: not-allowed;
}
</style>


