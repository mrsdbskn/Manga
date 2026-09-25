<template>
  <div class="w-full py-8 select-none">
    <!-- Shelf Header & Navigation -->
    <div class="flex items-center justify-between mb-6 px-4 max-w-7xl mx-auto">
      <div>
        <h2 class="text-xl sm:text-2xl font-black text-white tracking-tight flex items-center gap-2">
          <span>📚 Grand Line Collector's Shelf</span>
          <span class="text-xs px-2 py-0.5 rounded-full bg-amber-400/20 text-amber-300 font-mono border border-amber-400/30">
            {{ volumes.length }} Volumes
          </span>
        </h2>
        <p class="text-xs text-slate-400 mt-1">
          Click any manga spine to pull it from the shelf • View 3D spine and read directly
        </p>
      </div>

      <!-- Shelf Scroll Controls -->
      <div class="flex items-center gap-2">
        <button
          type="button"
          @click="scrollShelf(-400)"
          class="p-2 rounded-full bg-black/40 hover:bg-black/80 text-white/80 hover:text-white border border-white/10 backdrop-blur-md transition-colors"
          title="Scroll Left"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="m15 18-6-6 6-6"/>
          </svg>
        </button>
        <button
          type="button"
          @click="scrollShelf(400)"
          class="p-2 rounded-full bg-black/40 hover:bg-black/80 text-white/80 hover:text-white border border-white/10 backdrop-blur-md transition-colors"
          title="Scroll Right"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="m9 18 6-6-6-6"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 3D Physical Shelf Track -->
    <div class="relative w-full overflow-hidden px-4 max-w-7xl mx-auto">
      <div 
        ref="shelfScrollRef"
        class="flex items-end gap-2.5 overflow-x-auto pb-8 pt-16 px-6 no-scrollbar scroll-smooth perspective-1000"
      >
        <!-- Individual Manga Book on Shelf -->
        <div
          v-for="vol in volumes"
          :key="vol.id || vol.volumeNumber"
          @click="selectVolume(vol)"
          :class="[
            'relative cursor-pointer transition-all duration-300 group shrink-0',
            selectedVolume?.volumeNumber === vol.volumeNumber ? '-translate-y-8 z-30 scale-105' : 'hover:-translate-y-4 hover:z-20'
          ]"
        >
          <!-- 3D Book Spine -->
          <div
            class="w-[42px] h-[230px] rounded-t-sm flex flex-col justify-between py-3 px-1 text-center shadow-2xl relative overflow-hidden border-t border-r border-white/20 transition-transform"
            :style="{
              backgroundColor: vol.spineColor || '#1e2235',
              boxShadow: selectedVolume?.volumeNumber === vol.volumeNumber
                ? '0 20px 30px -10px rgba(0,0,0,0.8), 0 0 20px ' + (vol.spineColor || '#38bdf8') + '80'
                : 'inset -3px 0 6px rgba(0,0,0,0.5), inset 3px 0 6px rgba(255,255,255,0.15), 4px 6px 15px rgba(0,0,0,0.6)'
            }"
          >
            <!-- Top Spine Jump Logo -->
            <div class="z-10">
              <span class="text-[9px] font-black text-amber-300 tracking-tighter block leading-none">JC</span>
              <div class="w-5 h-[1px] bg-white/40 mx-auto my-1.5"></div>
            </div>

            <!-- Volume Number Emblem -->
            <div class="my-auto z-10 flex flex-col items-center">
              <div class="w-7 h-7 rounded-full bg-black/50 border border-white/20 flex items-center justify-center font-mono font-black text-xs text-white shadow-md">
                {{ vol.volumeNumber }}
              </div>
              <span class="text-[9px] font-black text-white tracking-widest uppercase [writing-mode:vertical-rl] max-h-[110px] overflow-hidden truncate mt-2 drop-shadow">
                ONE PIECE
              </span>
            </div>

            <!-- Bottom Oda Signature -->
            <div class="z-10 text-[8px] text-white/90 font-bold [writing-mode:vertical-rl] mx-auto drop-shadow">
              尾田栄一郎
            </div>

            <!-- Spine Gloss & Book Curvature Reflection -->
            <div class="absolute inset-0 bg-gradient-to-r from-black/40 via-white/15 to-black/30 pointer-events-none"></div>
            <!-- Ribbing Lines -->
            <div class="absolute top-2 left-0 right-0 h-[2px] bg-black/40"></div>
            <div class="absolute bottom-2 left-0 right-0 h-[2px] bg-black/40"></div>
          </div>

          <!-- Top Page Paper Block (Visible when pulled out) -->
          <div
            v-if="selectedVolume?.volumeNumber === vol.volumeNumber"
            class="absolute -top-[12px] left-0 w-[42px] h-[12px] bg-[#f0ebd8] border-t border-l border-r border-[#d4cbaf] shadow-inner"
            style="transform: skewX(-20deg);"
          ></div>

          <!-- Volume Number Footnote Below Shelf -->
          <div class="text-center mt-2">
            <span class="text-[10px] font-mono font-bold text-slate-400 group-hover:text-amber-300 transition-colors">
              v.{{ vol.volumeNumber }}
            </span>
          </div>
        </div>
      </div>

      <!-- Physical Wooden Shelf Plinth -->
      <div class="h-6 w-full bg-gradient-to-b from-[#2a1b12] to-[#170e09] border-t-2 border-[#543623] shadow-2xl rounded-sm relative -mt-4">
        <!-- Wood Grain Accent Line -->
        <div class="h-[1px] w-full bg-amber-900/40"></div>
        <div class="h-2 w-full bg-black/40"></div>
      </div>
    </div>

    <!-- Inspector Modal / Drawer when a volume is selected -->
    <transition name="fade">
      <div 
        v-if="selectedVolume"
        class="max-w-2xl mx-auto mt-8 bg-slate-900/90 backdrop-blur-2xl border border-white/10 rounded-3xl p-6 shadow-2xl flex flex-col sm:flex-row items-center gap-6"
      >
        <!-- 3D Card Miniature -->
        <div class="w-36 shrink-0 aspect-[2/3] rounded-xl overflow-hidden shadow-2xl border border-white/15 relative">
          <img 
            :src="selectedVolume.coverUrl || 'comics/covers/cover-v01.jpg'" 
            :alt="selectedVolume.title"
            class="w-full h-full object-cover"
          />
          <div class="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md text-[10px] font-mono font-bold text-amber-300">
            Vol. {{ selectedVolume.volumeNumber }}
          </div>
        </div>

        <!-- Volume Metadata & Actions -->
        <div class="flex-1 text-center sm:text-left space-y-2">
          <div class="flex items-center justify-center sm:justify-start gap-2">
            <span class="text-xs font-bold px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30">
              {{ selectedVolume.sagaName || 'One Piece' }}
            </span>
            <span class="text-xs text-slate-400 font-mono">
              Chapters {{ selectedVolume.chapterStart }}–{{ selectedVolume.chapterEnd }}
            </span>
          </div>

          <h3 class="text-xl font-black text-white leading-tight font-outfit">
            {{ formatVolumeHeading(selectedVolume) }}
          </h3>

          <p class="text-xs text-slate-300 line-clamp-3 leading-relaxed italic">
            "{{ selectedVolume.summary || 'Eiichiro Oda\'s timeless One Piece journey continues with high-seas adventures and epic battles.' }}"
          </p>

          <div class="pt-2 flex items-center justify-center sm:justify-start gap-3">
            <button
              type="button"
              @click="openVolume(selectedVolume)"
              class="px-5 py-2 rounded-full bg-[#0842a0] hover:bg-[#0b57d0] text-white text-xs font-bold flex items-center gap-2 shadow-lg transition-all"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M5 3l14 9-14 9V3z"/>
              </svg>
              <span>Read Volume {{ selectedVolume.volumeNumber }}</span>
            </button>

            <button
              type="button"
              @click="selectedVolume = null"
              class="px-4 py-2 rounded-full bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white text-xs font-semibold transition-colors"
            >
              Put Back on Shelf
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useLibraryStore } from '../../stores/library.js';

const props = defineProps({
  volumes: {
    type: Array,
    required: true,
  },
});

const libraryStore = useLibraryStore();
const shelfScrollRef = ref(null);
const selectedVolume = ref(null);

function scrollShelf(amount) {
  if (shelfScrollRef.value) {
    shelfScrollRef.value.scrollBy({ left: amount, behavior: 'smooth' });
  }
}

function selectVolume(vol) {
  if (selectedVolume.value?.volumeNumber === vol.volumeNumber) {
    selectedVolume.value = null;
  } else {
    selectedVolume.value = vol;
  }
}

function formatVolumeHeading(vol) {
  if (!vol) return '';
  const vNum = vol.volumeNumber;
  let rawTitle = (vol.title || '').trim();
  rawTitle = rawTitle.replace(/^(?:volume|vol\.?)\s*\d+\s*[:\-–—]\s*/i, '').trim();
  if (!rawTitle || /^(?:volume|vol\.?)\s*\d+$/i.test(rawTitle)) {
    return `Vol. ${vNum}`;
  }
  return `Vol. ${vNum} - ${rawTitle}`;
}

function openVolume(vol) {
  libraryStore.openReader(vol);
}
</script>

<style scoped>
.perspective-1000 {
  perspective: 1000px;
}
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
