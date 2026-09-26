<template>
  <div 
    class="w-full glass-card rounded-3xl p-4 sm:p-5 flex flex-col md:flex-row items-center gap-5 hover:border-white/20 transition-all duration-200 md-state-layer group"
    :id="`volume-list-item-${volume.volumeNumber}`"
  >
    <!-- LEFT: Mini Isometric 3D Book Render -->
    <div class="perspective-1000 shrink-0 w-24 h-32 flex items-center justify-center relative cursor-pointer" @click="openReader">
      <div 
        class="preserve-3d relative w-20 h-28 transform transition-transform duration-300 group-hover:scale-105 group-hover:rotate-y-[15deg]"
        style="transform: rotateY(25deg) rotateX(4deg);"
      >
        <!-- Mini Front Cover -->
        <div 
          class="absolute inset-0 rounded-r bg-[#1e2235] shadow-elevation-2 overflow-hidden border-r border-t border-b border-white/20"
          style="transform: translateZ(9px);"
        >
          <img 
            v-if="volume.coverUrl && !imageError"
            :src="volume.coverUrl" 
            :alt="volume.title"
            class="w-full h-full object-cover pointer-events-none select-none"
            @error="onImageError"
            loading="lazy"
          />
          <div 
            v-else
            class="w-full h-full flex flex-col items-center justify-center p-1 text-center"
            :style="{ background: `linear-gradient(135deg, #1e2235 0%, ${volume.spineColor || '#3b82f6'} 100%)` }"
          >
            <span class="text-[9px] font-black text-amber-300">JC</span>
            <span class="text-[11px] font-extrabold text-white mt-1">VOL {{ volume.volumeNumber }}</span>
          </div>
          <div class="absolute inset-0 cover-gloss opacity-30"></div>
        </div>

        <!-- Mini Spine -->
        <div 
          class="absolute top-0 bottom-0 w-[18px] overflow-hidden flex flex-col items-center justify-between py-1"
          :style="{
            left: 'calc(50% - 9px)',
            transform: 'rotateY(-90deg) translateZ(40px)',
            backgroundColor: volume.spineColor || '#1e2235',
          }"
        >
          <span class="text-[7px] font-bold text-white font-mono">{{ volume.volumeNumber }}</span>
          <span class="text-[6px] text-white [writing-mode:vertical-rl] font-bold truncate">OP</span>
        </div>

        <!-- Mini Fore-edge pages -->
        <div 
          class="absolute top-0 bottom-0 w-[18px] paper-block-pattern"
          :style="{
            left: 'calc(50% - 9px)',
            transform: 'rotateY(90deg) translateZ(40px)',
          }"
        ></div>
      </div>
    </div>

    <!-- CENTER: Title, Japanese Title, Arc Badge & Summary -->
    <div class="flex-1 min-w-0 text-center md:text-left">
      <div class="flex flex-wrap items-center justify-center md:justify-start gap-2 mb-1.5">
        <span 
          class="text-xs font-bold px-2.5 py-0.5 rounded-full font-mono shadow-sm"
          :style="{
            backgroundColor: `${volume.spineColor || '#38bdf8'}25`,
            color: volume.spineColor || '#38bdf8',
            border: `1px solid ${volume.spineColor || '#38bdf8'}40`
          }"
        >
          Vol. {{ volume.volumeNumber }}
        </span>

        <span class="text-[11px] px-2 py-0.5 rounded-full bg-white/[0.06] text-slate-300 font-medium">
          {{ volume.arcName || volume.sagaName }}
        </span>

        <span v-if="volume.japaneseTitle" class="text-[11px] font-japanese text-slate-400">
          {{ volume.japaneseTitle }}
        </span>
      </div>

      <h3 class="text-base sm:text-lg font-bold text-white font-outfit tracking-tight group-hover:text-[#a8c7fa] transition-colors">
        {{ formattedVolumeTitle }}
      </h3>

      <p class="text-xs text-slate-400 line-clamp-2 mt-1 leading-relaxed max-w-2xl">
        {{ volume.summary || 'Follow Monkey D. Luffy and the Straw Hat Pirates on their legendary quest across the Grand Line.' }}
      </p>

      <div class="flex flex-wrap items-center justify-center md:justify-start gap-3 mt-2 text-[11px] text-slate-400">
        <span class="flex items-center gap-1 font-mono">
          <svg class="w-3 h-3 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
          </svg>
          Ch. {{ volume.chapterStart }} – {{ volume.chapterEnd }}
        </span>

        <span class="text-slate-600">•</span>

        <span class="flex items-center gap-1">
          <svg class="w-3 h-3 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect width="18" height="18" x="3" y="3" rx="2" />
            <path d="M9 3v18" />
          </svg>
          {{ volume.pageCount || 200 }} Pages
        </span>

        <span v-if="volume.releaseDate" class="text-slate-600 hidden sm:inline">•</span>

        <span v-if="volume.releaseDate" class="text-slate-500 hidden sm:inline">
          Released {{ volume.releaseDate }}
        </span>
      </div>
    </div>

    <!-- RIGHT: Progress & Quick-Launch Read Button -->
    <div class="w-full md:w-56 shrink-0 flex flex-col items-center md:items-end gap-2.5 pt-2 md:pt-0 border-t md:border-t-0 border-white/10">
      <!-- Progress Bar -->
      <div class="w-full">
        <div class="flex items-center justify-between text-[11px] mb-1">
          <span class="text-slate-400">Progress</span>
          <span class="font-mono text-slate-300">{{ userProgress.percentage }}%</span>
        </div>
        <ProgressBarMD3 
          :value="userProgress.percentage" 
          :height="6"
          :barColor="volume.spineColor || '#a8c7fa'"
        />
      </div>

      <!-- Action Button -->
      <button 
        type="button"
        @click="openReader"
        :class="[
          'w-full py-2 px-4 rounded-full text-xs font-semibold flex items-center justify-center gap-2 transition-all duration-200 shadow-elevation-1 md-state-layer',
          userProgress.percentage > 0
            ? 'bg-[#a8c7fa]/20 text-[#a8c7fa] hover:bg-[#a8c7fa]/30 border border-[#a8c7fa]/40'
            : 'bg-[#0842a0] text-white hover:bg-[#0b57d0]'
        ]"
      >
        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M5 3l14 9-14 9V3z" />
        </svg>
        <span>{{ userProgress.percentage > 0 ? (userProgress.completed ? 'Re-read Volume' : 'Resume Page ' + userProgress.lastPage) : 'Read Volume' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useLibraryStore } from '../../stores/library.js';
import { useProgressStore } from '../../stores/progress.js';
import ProgressBarMD3 from '../UI/ProgressBarMD3.vue';

const props = defineProps({
  volume: {
    type: Object,
    required: true,
  },
});

const libraryStore = useLibraryStore();
const progressStore = useProgressStore();

const userProgress = computed(() => {
  return progressStore.getProgressForVolume(props.volume.id);
});

const formattedVolumeTitle = computed(() => {
  const vNum = props.volume.volumeNumber;
  let rawTitle = (props.volume.title || '').trim();
  rawTitle = rawTitle.replace(/^(?:volume|vol\.?)\s*\d+\s*[:\-–—]\s*/i, '').trim();
  if (!rawTitle || /^(?:volume|vol\.?)\s*\d+$/i.test(rawTitle)) {
    return `Vol. ${vNum}`;
  }
  return `Vol. ${vNum} - ${rawTitle}`;
});

function openReader() {
  libraryStore.openReader(props.volume);
}

const imageError = ref(false);

function onImageError() {
  imageError.value = true;
}
</script>
