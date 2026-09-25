<template>
  <div class="w-full flex items-center gap-2">
    <div 
      class="flex-1 bg-[#14161f] rounded-full overflow-hidden relative"
      :style="{ height: `${height}px` }"
    >
      <!-- Background track -->
      <div class="absolute inset-0 bg-white/[0.06] rounded-full"></div>
      
      <!-- Progress fill with tonal gradient -->
      <div 
        class="h-full rounded-full transition-all duration-300 ease-out relative"
        :style="{
          width: `${clampedValue}%`,
          backgroundColor: barColor || '#a8c7fa',
          boxShadow: clampedValue > 0 ? `0 0 10px ${barColor || '#a8c7fa'}60` : 'none'
        }"
      >
        <!-- Shimmer light effect -->
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse"></div>
      </div>
    </div>
    
    <span v-if="showLabel" class="text-[11px] font-medium text-slate-400 min-w-[32px] text-right">
      {{ clampedValue }}%
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  value: {
    type: Number,
    default: 0,
  },
  height: {
    type: Number,
    default: 6,
  },
  barColor: {
    type: String,
    default: '#a8c7fa',
  },
  showLabel: {
    type: Boolean,
    default: false,
  },
});

const clampedValue = computed(() => {
  return Math.min(100, Math.max(0, Math.round(props.value || 0)));
});
</script>
