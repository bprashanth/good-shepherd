<template>
  <div class="flex flex-col h-screen bg-gray-900 text-gray-100">
    <!-- Top bar -->
    <ToolBar
      v-if="!showLanding"
      class="border-b border-gray-700"
      @json-loaded="onJsonLoaded"
      @image-loaded="onImageLoaded"
      @save-json="saveJson"
      @zoom-in="zoomIn"
      @zoom-out="zoomOut"
      @visualize="onVisualize"
    />

    <!-- Main content -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Viewer -->
      <div class="flex-1 relative overflow-hidden bg-gray-800">
        <LandingPage
          v-if="showLanding"
          @load-asset-pair="loadAssetPair"
        />
        <FormViewer
          v-else-if="formData && imageUrl"
          :formData="formData"
          :imageUrl="imageUrl"
          :zoom="zoom"
          @select-row="onSelectRow"
          @select-header="onSelectHeader"
          @select-universal="onSelectUniversal"
        />
        <div v-else class="h-full flex items-center justify-center text-gray-500">
          <p>Select an image and JSON to begin.</p>
        </div>
      </div>

      <!-- Side panel -->
      <div v-if="!showLanding" class="w-80 border-l border-gray-700 bg-[#0f141a]">
        <VisualizationPanel v-if="mode === 'visualization'" :formData="formData" />
        <SidePanel
          v-else
          :mode="mode"
          :selectedRow="selectedRow"
          :headers="formData?.header_map || null"
          :universals="formData?.universal_fields || null"
          @update-row="updateRow"
          @update-header="updateHeader"
          @apply-universal="applyUniversalFields"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ToolBar from '@/components/ToolBar.vue'
import FormViewer from '@/components/FormViewer.vue'
import SidePanel from '@/components/SidePanel.vue'
import VisualizationPanel from '@/components/VisualizationPanel.vue'
import LandingPage from '@/components/LandingPage.vue'

/**
 * State
 */
const showLanding = ref(true) // show landing page initially
const formData = ref(null) // loaded output.json (reactive source of truth)
const imageUrl = ref(null) // objectURL for the selected image
const zoom = ref(1) // viewer zoom 0.5–2.0

// selection / mode
const mode = ref(null) // "row" | "header" | "universal" | "visualization" | null
const selectedRow = ref(null) // currently selected row object
const selectedHeaderKey = ref(null) // currently selected header key (string)

/**
 * Toolbar events
 */
function onJsonLoaded(json) {
  formData.value = json
  // clear selection when new JSON is loaded
  mode.value = null
  selectedRow.value = null
  selectedHeaderKey.value = null
}
function onImageLoaded(url) {
  imageUrl.value = url
}

/**
 * Load asset pair from landing page
 * Fetches JSON and loads image, then transitions to form view
 */
async function loadAssetPair({ imageName, jsonName }) {
  try {
    // Fetch and parse JSON
    const jsonResponse = await fetch(`/assets/${jsonName}`)
    if (!jsonResponse.ok) {
      throw new Error(`Failed to load JSON: ${jsonName}`)
    }
    const json = await jsonResponse.json()

    // Load image (use direct URL since it's in public folder)
    const imageUrlValue = `/assets/${imageName}`

    // Set the data and hide landing page
    onJsonLoaded(json)
    onImageLoaded(imageUrlValue)
    showLanding.value = false
  } catch (error) {
    console.error('Error loading asset pair:', error)
    alert(`Failed to load assets: ${error.message}`)
  }
}
function zoomIn() {
  zoom.value = Math.min(2, +(zoom.value + 0.1).toFixed(2))
}
function zoomOut() {
  zoom.value = Math.max(0.5, +(zoom.value - 0.1).toFixed(2))
}
function onVisualize() {
  mode.value = 'visualization'
  selectedRow.value = null
  selectedHeaderKey.value = null
}

/**
 * FormViewer selection events
 */
function onSelectRow(row) {
  mode.value = 'row'
  selectedRow.value = row
  selectedHeaderKey.value = null
}
function onSelectHeader(key) {
  mode.value = 'header'
  selectedHeaderKey.value = key
  selectedRow.value = null
}
function onSelectUniversal() {
  mode.value = 'universal'
  selectedHeaderKey.value = null
  selectedRow.value = null
}

/**
 * Row editing
 * Replaces the row (by group_id) so changes persist in formData and Save JSON exports them.
 */
function updateRow(updatedRow) {
  if (!formData.value || !updatedRow?.system?.group_id) return
  const gid = updatedRow.system.group_id
  const idx = formData.value.rows.findIndex((r) => r.system?.group_id === gid)
  if (idx !== -1) {
    formData.value.rows[idx] = updatedRow
    selectedRow.value = updatedRow // keep panel in sync
  }
}

/**
 * Header editing
 * Handles three editable properties:
 *  - indicator (key rename) - propagate to rows + cells
 *  - field_name - update only header_map[key].field_name
 *  - description - update only header_map[key].description
 */
function updateHeader({ key, field, value }) {
  if (!formData.value?.header_map) return
  const headerMap = formData.value.header_map
  const headerEntry = headerMap[key]
  if (!headerEntry) return

  if (field === 'indicator') {
    const newKey = value.trim()
    if (!newKey || newKey === key) return

    // move sub-dict to new key
    headerMap[newKey] = { ...headerEntry }
    delete headerMap[key]

    // rename keys in rows
    for (const row of formData.value.rows || []) {
      if (Object.prototype.hasOwnProperty.call(row, key)) {
        row[newKey] = row[key]
        delete row[key]
      }
      // update cell.header too
      for (const cellId in row.system?.cells || {}) {
        const cell = row.system.cells[cellId]
        if (cell.header === key) cell.header = newKey
      }
    }
  } else if (field === 'field_name' || field === 'description') {
    headerEntry[field] = value
  }
}

/**
 * Apply universal fields to all rows
 * Called when user clicks "Save Universal Fields" button
 * Updates universal_fields structure and merges valid fields into rows
 */
function applyUniversalFields(localUniversals) {
  if (!formData.value?.universal_fields || !localUniversals) return

  // First, update the universal_fields structure with local changes
  for (const [originalKey, uf] of Object.entries(localUniversals)) {
    const newKey = uf._editKey

    // Handle key rename
    if (newKey !== originalKey) {
      const universalFields = formData.value.universal_fields
      universalFields[newKey] = { ...universalFields[originalKey] }
      delete universalFields[originalKey]
    }

    // Update the universal field with new values
    const targetKey = newKey !== originalKey ? newKey : originalKey
    if (formData.value.universal_fields[targetKey]) {
      formData.value.universal_fields[targetKey].value = uf.value
      formData.value.universal_fields[targetKey].system.valid = uf.system.valid
    }
  }

  // Now apply to rows
  if (!formData.value?.rows) return

  // Get all universal field keys (both valid and invalid) - exclude 'system' key
  const allUniversalKeys = Object.keys(formData.value.universal_fields).filter(
    (key) => key !== 'system',
  )

  // Get valid universal fields
  const validUniversals = Object.fromEntries(
    Object.entries(formData.value.universal_fields).filter(
      ([key, v]) => key !== 'system' && v?.system?.valid !== false,
    ),
  )

  // Update each row - only touch universal field keys, preserve everything else
  formData.value.rows.forEach((row) => {
    // Remove ALL universal fields first (including invalid ones) - but NOT 'system'
    // Use __fieldname__ convention to avoid conflicts with regular row data
    allUniversalKeys.forEach((key) => {
      const universalKey = `__${key}__`
      delete row[universalKey]
    })

    // Add only valid universal fields
    Object.entries(validUniversals).forEach(([key, uf]) => {
      const universalKey = `__${key}__`
      row[universalKey] = uf.value
    })
  })
}

/**
 * Save JSON
 *  - Create a deep copy
 *  - Gather only valid universal fields
 *  - Merge those k/v into each row (flat)
 *  - Download the updated JSON
 */
function saveJson() {
  if (!formData.value) {
    console.warn('saveJson called but formData is null')
    return
  }

  try {
    // Use JSON.parse(JSON.stringify()) instead of structuredClone to handle non-serializable data
    // This will automatically strip out any non-serializable objects
    const cloned = JSON.parse(JSON.stringify(formData.value))

    const validUniversals = Object.fromEntries(
      Object.entries(cloned.universal_fields || {}).filter(([, v]) => v?.system?.valid !== false),
    )

    const flatUniversals = {}
    for (const [k, v] of Object.entries(validUniversals)) {
      flatUniversals[k] = v?.value ?? null
    }

    cloned.rows = (cloned.rows || []).map((row) => {
      // Remove system field and any non-serializable data, then merge universal fields
      // eslint-disable-next-line no-unused-vars
      const { system, ...rowData } = row
      return {
        ...flatUniversals,
        ...rowData,
      }
    })

    // Log the forms array to console
    console.log('Forms array (rows):', cloned.rows)
    console.log('Forms array length:', cloned.rows.length)
    console.log('Forms array (JSON):', JSON.stringify(cloned.rows, null, 2))

    const jsonString = JSON.stringify(cloned, null, 2)
    const blob = new Blob([jsonString], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'updated_output.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    console.log('JSON file downloaded successfully')
  } catch (error) {
    console.error('Error saving JSON:', error)
    alert('Failed to save JSON. Check console for details.')
    return // Don't navigate away if save failed
  }

  // Always return to landing page after saving - reset all state
  // Set showLanding first to ensure landing page shows and FormViewer unmounts
  showLanding.value = true

  // Use setTimeout to ensure FormViewer is unmounted before clearing data
  setTimeout(() => {
    formData.value = null
    imageUrl.value = null
    mode.value = null
    selectedRow.value = null
    selectedHeaderKey.value = null
    zoom.value = 1
    console.log('Save completed, returning to landing page. showLanding:', showLanding.value)
  }, 0)
}
</script>
