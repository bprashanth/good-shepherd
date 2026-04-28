<template>
  <div class="p-4 text-sm h-full overflow-y-auto bg-gray-900 text-gray-100">
    <div class="mb-4">
      <h2 class="font-semibold mb-2">Data Visualization</h2>
      <button
        v-if="!isLoading && !visualizations.length"
        class="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
        @click="generateVisualizations"
        :disabled="!formData"
      >
        Generate Visualizations
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="text-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto mb-2"></div>
      <p class="text-gray-400">Generating visualizations...</p>
    </div>

    <!-- Error state -->
    <div v-if="error" class="text-red-400 p-3 bg-red-900/20 rounded mb-4">
      {{ error }}
    </div>

    <!-- Visualizations -->
    <div v-if="visualizations.length" class="space-y-4">
      <div
        v-for="(viz, index) in visualizations"
        :key="index"
        class="border border-gray-700 rounded p-3 bg-gray-800"
      >
        <h3 class="font-medium mb-2">Visualization {{ index + 1 }}</h3>
        <div :id="`viz-${index}`" class="w-full"></div>
      </div>
    </div>

    <!-- No data state -->
    <div v-if="!formData" class="text-gray-500 text-center py-8">
      Load form data to generate visualizations
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, toRaw } from 'vue'
import vegaEmbed from 'vega-embed'
import OpenAI from 'openai'

const props = defineProps({
  formData: Object,
})

const isLoading = ref(false)
const error = ref(null)
const visualizations = ref([])

let openai = null

// Initialize OpenAI client
async function initOpenAI() {
  if (!openai) {
    const apiKey = import.meta.env.VITE_OPEN_AI_API_KEY
    if (!apiKey || apiKey === 'your_api_key_here') {
      throw new Error('OpenAI API key not configured. Please set VITE_OPEN_AI_API_KEY in .env file')
    }
    openai = new OpenAI({
      apiKey: apiKey,
      dangerouslyAllowBrowser: true,
    })
  }
  return openai
}

async function generateVisualizations() {
  if (!props.formData) return

  isLoading.value = true
  error.value = null
  visualizations.value = []

  try {
    const client = await initOpenAI()

    // Prepare data summary for the prompt
    const dataSummary = {
      headers: Object.keys(props.formData.header_map || {}),
      rowCount: props.formData.rows?.length || 0,
      universalFields: Object.keys(props.formData.universal_fields || {}),
      sampleRows: props.formData.rows?.slice(0, 3) || [],
    }

    const prompt = `You are a data visualization expert. Given the following form data structure, generate 1-3 Vega-Lite visualizations that would be most insightful for this dataset.

Data Summary:
- Headers: ${dataSummary.headers.join(', ')}
- Number of rows: ${dataSummary.rowCount}
- Universal fields: ${dataSummary.universalFields.join(', ')}
- Sample data: ${JSON.stringify(dataSummary.sampleRows, null, 2)}

CRITICAL REQUIREMENTS:
1. Return ONLY a valid JSON array of Vega-Lite specifications
2. Do NOT include any markdown, code blocks, or explanatory text
3. Each specification must be a plain JSON object
4. Use only standard Vega-Lite properties (no custom functions or complex objects)

Example format:
[
  {
    "title": "Chart Title",
    "mark": "bar",
    "encoding": {
      "x": {"field": "fieldName", "type": "nominal"},
      "y": {"field": "value", "type": "quantitative"}
    }
  }
]

Guidelines:
- Choose appropriate chart types (bar, line, scatter, histogram, etc.)
- Use meaningful field names from the data
- Include descriptive titles
- Keep specifications simple and standard
- Return ONLY the JSON array`

    const response = await client.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.3,
    })

    const content = response.choices[0].message.content.trim()

    // Log the full response for debugging
    console.log('Full AI response:', content)

    // Try to parse the response as JSON
    let vizSpecs
    try {
      vizSpecs = JSON.parse(content)
    } catch (parseError) {
      // If parsing fails, try to extract JSON from markdown code blocks
      const jsonMatch = content.match(/```(?:json)?\s*(\[.*?\])\s*```/s)
      if (jsonMatch) {
        vizSpecs = JSON.parse(jsonMatch[1])
      } else {
        throw new Error('Could not parse visualization specifications from response' + parseError)
      }
    }

    if (!Array.isArray(vizSpecs)) {
      throw new Error('Response is not an array of visualizations')
    }

    // Transform form data for visualization
    const transformedData = transformFormData(props.formData)

    // Process each visualization spec
    for (let i = 0; i < vizSpecs.length; i++) {
      const spec = vizSpecs[i]

      // Create visualization spec with data
      const cleanSpec = {
        title: spec.title || `Visualization ${i + 1}`,
        mark: spec.mark,
        encoding: spec.encoding,
        data: { values: transformedData },
      }

      visualizations.value.push(cleanSpec)
    }

    // Render visualizations after DOM update
    await nextTick()
    await renderVisualizations()
  } catch (err) {
    error.value = err.message
    console.error('Error generating visualizations:', err)
  } finally {
    isLoading.value = false
  }
}

// Removes the system field from the rows
function transformFormData(formData) {
  // Remove system field from rows
  return (formData.rows || []).map((row) => {
    // eslint-disable-next-line no-unused-vars
    const { system, ...data } = row
    return data
  })
}

async function renderVisualizations() {
  for (let i = 0; i < visualizations.value.length; i++) {
    const container = document.getElementById(`viz-${i}`)

    const safeSpec = JSON.parse(JSON.stringify(toRaw(visualizations.value[i])))

    if (container) {
      try {
        // Try with SVG renderer first

        await vegaEmbed(container, safeSpec, {
          actions: false,
          renderer: 'svg',
        })
      } catch (err) {
        console.error(`Error rendering visualization ${i} with SVG:`, err)

        try {
          // Try with canvas renderer as fallback
          await vegaEmbed(container, safeSpec, {
            actions: false,
            renderer: 'canvas',
          })
        } catch (canvasErr) {
          console.error(`Error rendering visualization ${i} with canvas:`, canvasErr)
          container.innerHTML = `<div class="text-red-400 p-2 bg-red-900/20 rounded">
            <div class="font-semibold">Error rendering visualization ${i + 1}</div>
            <div class="text-sm">${err.message}</div>
            <details class="mt-2">
              <summary class="cursor-pointer text-xs">Technical details</summary>
              <pre class="text-xs mt-1 overflow-auto">${JSON.stringify(safeSpec, null, 2)}</pre>
            </details>
          </div>`
        }
      }
    }
  }
}

// Watch for formData changes to clear visualizations
watch(
  () => props.formData,
  () => {
    visualizations.value = []
    error.value = null
  },
)
</script>
