<template>
  <div 
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md transition-opacity duration-300"
    @click.self="close"
  >
    <!-- Modal Card -->
    <div 
      class="glass-card rounded-3xl p-6 sm:p-8 max-w-lg w-full border border-white/15 shadow-elevation-4 relative overflow-hidden"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
    >
      <!-- Close Button -->
      <button 
        type="button"
        @click="close"
        class="absolute top-4 right-4 p-2 rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-colors md-state-layer"
      >
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>

      <!-- Header -->
      <div class="text-center mb-6">
        <div class="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center mx-auto mb-3 shadow-inner">
          <svg class="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" x2="12" y1="3" y2="15" />
          </svg>
        </div>
        <h3 class="text-xl font-bold text-white font-outfit">Instant Local Reader</h3>
        <p class="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
          Read any .cbz or .zip directly in your browser. Files remain strictly local in your RAM — zero uploads.
        </p>
      </div>

      <!-- Drop Target Area -->
      <div 
        :class="[
          'border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-200 cursor-pointer relative',
          isDragging 
            ? 'border-sky-400 bg-sky-500/10 scale-[1.02]' 
            : 'border-white/15 hover:border-white/30 bg-black/20'
        ]"
        @click="triggerFileInput"
      >
        <input 
          ref="fileInputRef" 
          type="file" 
          accept=".cbz,.zip" 
          class="hidden" 
          @change="onFileSelected"
        />

        <div class="flex flex-col items-center">
          <svg 
            class="w-10 h-10 mb-3 transition-colors duration-200"
            :class="[isDragging ? 'text-sky-300 animate-bounce' : 'text-slate-500']"
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            stroke-width="1.5"
          >
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
            <path d="m10 13 2-2 2 2" />
            <path d="M12 11v6" />
          </svg>

          <span class="text-sm font-semibold text-white">
            {{ isDragging ? 'Drop CBZ Archive Here!' : 'Drop manga archive here, or browse' }}
          </span>

          <span class="text-[11px] text-slate-400 mt-1">
            Supports .cbz & .zip (with ComicInfo.xml metadata)
          </span>

          <button 
            type="button"
            class="mt-4 px-4 py-1.5 rounded-full text-xs font-semibold bg-[#a8c7fa]/20 text-[#a8c7fa] hover:bg-[#a8c7fa]/30 border border-[#a8c7fa]/40 transition-colors"
          >
            Select from Device
          </button>
        </div>
      </div>

      <!-- Privacy notice badge -->
      <div class="mt-4 flex items-center justify-center gap-1.5 text-[10px] text-slate-500 text-center">
        <svg class="w-3.5 h-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
        <span>100% Client-Side In-Memory Execution • Zero Data leaves your device</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useLibraryStore } from '../../stores/library.js';

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['close']);

const libraryStore = useLibraryStore();
const fileInputRef = ref(null);
const isDragging = ref(false);

function close() {
  emit('close');
}

function triggerFileInput() {
  fileInputRef.value?.click();
}

function onFileSelected(e) {
  const file = e.target.files?.[0];
  if (file) {
    handleFile(file);
  }
}

function onDrop(e) {
  isDragging.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (file) {
    handleFile(file);
  }
}

function handleFile(file) {
  const name = file.name.toLowerCase();
  if (name.endsWith('.cbz') || name.endsWith('.zip')) {
    libraryStore.openWithLocalFile(file);
    close();
  } else {
    alert('Please select a valid .cbz or .zip comic archive.');
  }
}
</script>
