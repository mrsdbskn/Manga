<template>
  <div class="inline-flex p-1 bg-[#14161f]/90 backdrop-blur-md rounded-full border border-white/10 shadow-elevation-1">
    <!-- Grid Mode Button -->
    <button
      type="button"
      @click="setMode('grid')"
      :class="[
        'flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all duration-200 md-state-layer',
        modelValue === 'grid'
          ? 'bg-[#a8c7fa]/20 text-[#a8c7fa] shadow-sm border border-[#a8c7fa]/30'
          : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
      ]"
      title="Grid View (3D Interactive Cards)"
    >
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect width="7" height="7" x="3" y="3" rx="1" />
        <rect width="7" height="7" x="14" y="3" rx="1" />
        <rect width="7" height="7" x="14" y="14" rx="1" />
        <rect width="7" height="7" x="3" y="14" rx="1" />
      </svg>
      <span>3D Grid</span>
    </button>

    <!-- List Mode Button -->
    <button
      type="button"
      @click="setMode('list')"
      :class="[
        'flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all duration-200 md-state-layer',
        modelValue === 'list'
          ? 'bg-[#a8c7fa]/20 text-[#a8c7fa] shadow-sm border border-[#a8c7fa]/30'
          : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
      ]"
      title="List View (Detailed Chapter Breakdown)"
    >
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="8" x2="21" y1="6" y2="6" />
        <line x1="8" x2="21" y1="12" y2="12" />
        <line x1="8" x2="21" y1="18" y2="18" />
        <line x1="3" x2="3.01" y1="6" y2="6" />
        <line x1="3" x2="3.01" y1="12" y2="12" />
        <line x1="3" x2="3.01" y1="18" y2="18" />
      </svg>
      <span>List</span>
    </button>

    <!-- 3D Shelf Mode Button -->
    <button
      type="button"
      @click="setMode('shelf')"
      :class="[
        'flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all duration-200 md-state-layer',
        modelValue === 'shelf'
          ? 'bg-amber-400/20 text-amber-300 shadow-sm border border-amber-400/30'
          : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
      ]"
      title="3D Manga Bookshelf (Spine & Shelf View)"
    >
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
        <path d="M6 6h10"/>
        <path d="M6 10h10"/>
      </svg>
      <span>3D Shelf</span>
    </button>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    default: 'grid',
  },
});

const emit = defineEmits(['update:modelValue']);

function setMode(mode) {
  emit('update:modelValue', mode);
}
</script>
