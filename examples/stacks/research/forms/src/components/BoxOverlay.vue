<template>
  <div
    class="absolute rounded-sm transition-all duration-150"
    :class="[borderClass, selected && 'selectedGlow']"
    :style="{
      left: `${bbox.Left * 100}%`,
      top: `${bbox.Top * 100}%`,
      width: `${bbox.Width * 100}%`,
      height: `${bbox.Height * 100}%`,
    }"
    @click.stop="emit('click')"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <!-- Hover reveal: strong translucent backdrop + prominent text -->
    <div
      v-if="hovered"
      class="absolute inset-0 bg-black/80 flex items-center justify-center px-1 text-center"
    >
      <span class="text-[0.7rem] font-semibold tracking-tight text-yellow-300 drop-shadow">
        {{ text }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  bbox: { type: Object, required: true },
  confidence: { type: Number, default: 100 },
  text: { type: String, default: '' },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['click'])

const hovered = ref(false)

// Only draw border if there is text AND confidence is orange/red (< 85)
const drawBorder = computed(() => !!props.text && props.confidence < 85)

const borderClass = computed(() => {
  if (!drawBorder.value) return 'border border-transparent'
  if (props.confidence < 70) return 'border border-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]'
  if (props.confidence < 85)
    return 'border border-orange-400 shadow-[0_0_6px_rgba(251,146,60,0.55)]'
  return 'border border-transparent'
})
</script>

<style scoped>
/* Thicker golden glow for selected row */
.selectedGlow {
  box-shadow:
    0 0 0 2px rgba(250, 204, 21, 0.95),
    0 0 12px 4px rgba(250, 204, 21, 0.65),
    0 0 28px 10px rgba(250, 204, 21, 0.35);
  border-color: rgba(250, 204, 21, 0.95) !important; /* force gold edge */
}
</style>
