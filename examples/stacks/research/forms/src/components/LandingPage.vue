<template>
  <div class="flex flex-col items-center justify-center h-full bg-gray-900 text-gray-100 p-8">
    <h1 class="text-3xl font-bold mb-8 text-gray-100">Review DataSheets</h1>

    <div class="w-full max-w-2xl space-y-4">
      <div
        v-for="(pair, index) in assetPairs"
        :key="index"
        class="w-full px-6 py-4 bg-gray-800 hover:bg-gray-700 border-2 border-gray-700 hover:border-gray-600 rounded-xl transition-all duration-200 flex items-center justify-between group relative"
      >
        <button
          @click="loadAssetPair(pair.imageName, pair.jsonName)"
          class="flex-1 text-left flex items-center justify-between"
        >
          <span class="text-lg font-medium text-gray-100 group-hover:text-white">
            {{ pair.label }}
          </span>
          <svg
            class="w-5 h-5 text-gray-400 group-hover:text-gray-300 transition-colors ml-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>

        <!-- Owner Dropdown Sub-button -->
        <div class="ml-4" @click.stop>
          <select
            v-model="pair.owner"
            @change="onOwnerChange(pair, pair.owner)"
            class="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-gray-500 transition-colors"
          >
            <option value="" disabled>Owner</option>
            <option v-for="owner in owners" :key="owner" :value="owner">
              {{ owner }}
            </option>
          </select>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['load-asset-pair'])

const owners = ['harsha', 'prashanth', 'guru']

const assetPairs = ref([
  {
    label: 'At1, Ald1',
    imageName: 'IMG-20250924-WA0001.jpg',
    jsonName: 'cloud_IMG-20250924-WA0001_classified.json',
    owner: '',
  },
  {
    label: 'At1, Ahd1',
    imageName: 'segmented_000.jpg',
    jsonName: 'cloud_segmented_000_classified.json',
    owner: '',
  },
  {
    label: 'At1, Avhd1',
    imageName: 'segmented_002.png',
    jsonName: 'cloud_segmented_002_classified.json',
    owner: '',
  },
])

function loadAssetPair(imageName, jsonName) {
  emit('load-asset-pair', { imageName, jsonName })
}

function onOwnerChange(pair, owner) {
  // Owner change handler - can be extended if needed
  console.log(`Owner changed for ${pair.label} to ${owner}`)
}
</script>

