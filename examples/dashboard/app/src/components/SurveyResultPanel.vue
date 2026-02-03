<!-- SurveyResultPanel.vue

@TODO:
  - This entire component needs a thorough refactor.
  - What if the original excel column name contained the Separator? (e.g. "survey->age") - right now we disallow both "." and "->"
-->
<template>
  <div class="survey-result-panel">
    <div class="control-section">
      <select v-model="yAxisField" class="dropdown">
        <option disabled value="">Select Y-Axis</option>
        <option v-for="field in surveyFields" :key="field" :value="field">{{ field }}</option>
      </select>

      <select v-model="xAxisField" class="dropdown">
        <option disabled value="">Select X-Axis</option>
        <option v-for="field in surveyFields" :key="field" :value="field">{{ field }}</option>
      </select>

      <select v-model="zAxisField" class="dropdown">
        <option disabled value="">Select Z-Axis (Optional)</option>
        <!-- Optional Z-Axis: this generates a null in the dropdown -->
        <option v-for="field in numericFields" :key="field" :value="field">{{ field }}</option>
        <option :value="null">None</option>
      </select>

      <button @click="generatePlot" class="plot-button">Plot</button>
    </div>

    <div v-if="queryResult && queryResult.length" class="chart-container">
        <canvas id="surveyChart" class="chart"></canvas>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, nextTick } from 'vue';
import { Chart, registerables } from 'chart.js';
import { onBeforeUnmount } from 'vue';

Chart.register(...registerables);

export default {
    name: 'SurveyResultPanel',
    props: {
        template: Object,
        queryResult: {
            type: Array,
            default: () => [],
        },
    },
    setup(props) {

        onBeforeUnmount(() => {
            if (chartInstance.value) {
                chartInstance.value.destroy();
                chartInstance.value = null;
            }
        });

        const separator = "->";

        const effectiveQueryResult = computed(() => {
          return props.template?.queryResults || props.queryResult || [];
        });

        const surveyFields = computed(() => {
            if (!effectiveQueryResult.value?.length) return [];

            const fields = [];
            const firstRow = effectiveQueryResult.value[0];

            for (const [key, value] of Object.entries(firstRow)) {
                if (typeof value === 'object' && value !== null) {
                    // Handle nested object - add only non-object children
                    for (const [nestedKey, nestedValue] of Object.entries(value)) {
                        if (typeof nestedValue !== 'object' || nestedValue === null) {
                            fields.push(`${key}${separator}${nestedKey}`);
                        }
                    }
                } else {
                    // Add non-object fields directly
                    fields.push(key);
                }
            }

            return fields;
        });

        // Get the value of a field from the query result.
        // Handles the separator for nested fields.
        const getFieldValue = (data, key) => {
            if (!key.includes(separator)) {
                return data[key];
            }
            const [parentKey, childKey] = key.split(separator);
            return data[parentKey]?.[childKey];
        };

        const yAxisField = ref(null);
        const xAxisField = ref(null);
        const zAxisField = ref(null);
        const chartInstance = ref(null);

        watch([xAxisField, yAxisField, zAxisField], () => {
            console.log("Axis selections changed:", xAxisField.value, yAxisField.value, zAxisField.value);
        });

        // Function to determine if a field is numeric.
        // Goes through 10 values of the fieldName in the given dataset.
        // If it encounters numerics all along, assumes it is numeric.
        function isNumericField(fieldName, data) {
            const sampleSize = Math.min(data.length, 10);
            for (let i = 0; i < sampleSize; i++) {
                const value = getFieldValue(data[i], fieldName);
                if (isNaN(Number(value)) || value === '') {
                    return false;
                }
            }
            return true;
        }

        // Computed property to filter numeric fields for the Z-axis
        const numericFields = computed(() => {
            return surveyFields.value.filter(field => isNumericField(field, effectiveQueryResult.value));
        });

        const generatePlot = async () => {
            if (!yAxisField.value || !xAxisField.value) {
                alert("Please select at least two fields to plot");
                return;
            }

            // Wait until the DOM has been updated
            // TODO(prashanth@): sometimes the chart element gets "detached".
            // Figure out why.
            await nextTick();

            const xIsNumeric = isNumericField(
                xAxisField.value, effectiveQueryResult.value);
            const yIsNumeric = isNumericField(
                yAxisField.value, effectiveQueryResult.value);

            const chartData = effectiveQueryResult.value.map(item => {
                return {
                    x: getFieldValue(item, xAxisField.value),
                    y: getFieldValue(item, yAxisField.value),
                    r: zAxisField.value ? getFieldValue(item, zAxisField.value) || 5 : undefined,
                };
            });

            if (chartInstance.value) {
                chartInstance.value.destroy();
            }

            // scatter for 2d, bubble for 3d
            const ctx = document.getElementById("surveyChart").getContext("2d");
            const chartType = zAxisField.value ? "bubble" : "scatter";

            chartInstance.value = new Chart(ctx, {
                type: chartType,
                data: {
                    datasets: [{
                        label: `${yAxisField.value} vs ${xAxisField.value}`,
                        data: chartData,
                        // Transparent bubble
                        backgroundColor: "rgba(0, 123, 255, 0.5)",
                        borderColor: "rgba(0, 123, 255, 1)",
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: xIsNumeric
                        ? { type: 'linear', title: { display: true, text: xAxisField.value } }
                        : { type: 'category', labels: [...new Set(effectiveQueryResult.value.map(item => item[xAxisField.value]))] },
                        y: yIsNumeric
                        ? { type: 'linear', title: { display: true, text: yAxisField.value } }
                        : { type: 'category', labels: [...new Set(effectiveQueryResult.value.map(item => item[yAxisField.value]))] }
                    }
                }
            });
        };

        return {
            surveyFields,
            numericFields,
            yAxisField,
            xAxisField,
            zAxisField,
            generatePlot
        };
    }
}
</script>

<style scoped>
.survey-result-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    box-sizing: border-box;
    padding-bottom: 1em;
    background-color: #333;
    border-radius: 8px;
    overflow: hidden;
    padding: 1em;
}

.control-section {
    display: flex;
    gap: 10px;
    padding: 10px;
    align-items: center;
    background-color: #333;
    border-radius: 8px;
    margin-bottom: 10px;
    flex-shrink: 0;
}

.chart-container {
    flex-grow: 1;
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: center;
}

.dropdown {
    width: 100%;
    padding: 8px;
    font-family: monospace;
    background-color: #333;
    color: #ddd;
    border: 1px solid #555;
    border-radius: 4px;
    outline: none;
    cursor: pointer;
}

.plot-button {
    padding: 10px;
    font-family: monospace;
    cursor: pointer;
    background-color: #317183;
    color: #282C34;
    border: none;
    border-radius: 4px;
    font-weight: bold;
}

.chart {
    width: 100%;
    max-height: 100%;
    background-color: transparent;
    /* margin-top: 1em; */
}

</style>
