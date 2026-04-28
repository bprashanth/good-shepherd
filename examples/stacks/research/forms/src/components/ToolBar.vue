<template>
  <div class="flex items-center justify-between px-4 py-2 bg-gray-950 text-gray-100">
    <div class="text-sm font-semibold">FormViewer</div>

    <div class="flex items-center space-x-2">
      <label class="bg-gray-800 px-2 py-1 rounded cursor-pointer hover:bg-gray-700">
        JSON
        <input type="file" accept=".json" class="hidden" @change="handleJson" />
      </label>
      <label class="bg-gray-800 px-2 py-1 rounded cursor-pointer hover:bg-gray-700">
        Image
        <input type="file" accept="image/*" class="hidden" @change="handleImage" />
      </label>

      <button class="bg-gray-800 px-2 py-1 rounded hover:bg-gray-700" @click="$emit('zoom-out')">
        −
      </button>
      <button class="bg-gray-800 px-2 py-1 rounded hover:bg-gray-700" @click="$emit('zoom-in')">
        +
      </button>

      <button
        class="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
        @click="$emit('visualize')"
      >
        Visualize
      </button>

      <button
        class="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
        @click="$emit('save-json')"
      >
        Save
      </button>
    </div>
  </div>
</template>

<script setup>
const emit = defineEmits([
  'json-loaded',
  'image-loaded',
  'save-json',
  'zoom-in',
  'zoom-out',
  'visualize',
])

function handleJson(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      emit('json-loaded', JSON.parse(reader.result))
    } catch {
      alert('Invalid JSON file')
    }
  }
  reader.readAsText(file)
}

function handleImage(e) {
  const file = e.target.files[0]
  if (!file) return
  emit('image-loaded', URL.createObjectURL(file))
}
</script>
