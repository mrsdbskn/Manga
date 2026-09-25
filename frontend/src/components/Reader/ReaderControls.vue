<template>
  <!-- Floating MD3 HUD -->
  <header 
    class="fixed top-0 left-0 right-0 z-50 transition-all duration-300 pointer-events-none"
    :class="[isVisible ? 'translate-y-0 opacity-100' : '-translate-y-full opacity-0']"
  >
    <div class="max-w-6xl mx-auto px-4 py-3 pointer-events-auto">
      <div class="glass-nav rounded-2xl px-4 py-2.5 flex items-center justify-between shadow-elevation-3 border border-white/10">
        
        <!-- Left: Back Button & Volume Title -->
        <div class="flex items-center gap-3 min-w-0">
          <button 
            type="button"
            @click="$emit('exit')"
            class="p-2 rounded-full hover:bg-white/10 text-slate-300 hover:text-white transition-colors md-state-layer shrink-0"
            title="Back to Manga Showcase"
          >
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="m15 18-6-6 6-6" />
            </svg>
          </button>

          <div class="min-w-0">
            <h2 class="text-xs sm:text-sm font-bold text-white truncate max-w-[200px] sm:max-w-xs">
              {{ title || 'One Piece' }}
            </h2>
            <p class="text-[10px] sm:text-[11px] text-sky-300 truncate">
              {{ subtitle || 'Manga Reader' }}
            </p>
          </div>
        </div>

        <!-- Center: Jump Controls & Page Pill -->
        <div class="flex items-center gap-2 sm:gap-4">
          <!-- Page Pill -->
          <div class="px-3 py-1 rounded-full bg-black/40 border border-white/10 text-xs font-mono text-slate-200 flex items-center gap-1.5 shadow-sm">
            <span>Page</span>
            <input 
              type="number" 
              :value="currentPage" 
              @change="onPageInputChange"
              :min="1" 
              :max="totalPages"
              class="w-10 bg-transparent text-center text-sky-300 font-bold focus:outline-none focus:ring-1 focus:ring-sky-400 rounded"
            />
            <span class="text-slate-500">/</span>
            <span>{{ totalPages }}</span>
          </div>

          <!-- Page Slider (Hidden on tiny screens) -->
          <div class="hidden md:flex items-center gap-2 w-32 lg:w-48">
            <input 
              type="range"
              :min="1"
              :max="totalPages"
              :value="currentPage"
              @input="onSliderInput"
              class="w-full accent-sky-400 h-1.5 bg-white/20 rounded-lg cursor-pointer"
            />
          </div>
        </div>

        <!-- Right: Mode Switcher, Fullscreen, Bookmark, Shortcuts -->
        <div class="flex items-center gap-1 sm:gap-2 shrink-0">
          <!-- Dual Engine Mode Toggle -->
          <button 
            type="button"
            @click="toggleMode"
            :class="[
              'px-2.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all md-state-layer border',
              currentMode === 'flipbook'
                ? 'bg-[#a8c7fa]/20 text-[#a8c7fa] border-[#a8c7fa]/30'
                : 'bg-[#d0bcff]/20 text-[#d0bcff] border-[#d0bcff]/30'
            ]"
            :title="currentMode === 'flipbook' ? 'Switch to Vertical Webtoon Mode' : 'Switch to 3D FlipBook Mode'"
          >
            <span v-if="currentMode === 'flipbook'" class="flex items-center gap-1">
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
              <span class="hidden sm:inline">3D Flip</span>
            </span>
            <span v-else class="flex items-center gap-1">
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2v20" />
                <path d="m17 17-5 5-5-5" />
                <path d="m17 7-5-5-5 5" />
              </svg>
              <span class="hidden sm:inline">Webtoon</span>
            </span>
          </button>

          <!-- Bookmark Toggle -->
          <button 
            type="button"
            @click="$emit('toggle-bookmark')"
            :class="[
              'p-2 rounded-full transition-colors md-state-layer',
              isBookmarked ? 'text-amber-400 bg-amber-400/20' : 'text-slate-400 hover:text-white hover:bg-white/10'
            ]"
            :title="isBookmarked ? 'Remove Bookmark' : 'Bookmark this page'"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" :fill="isBookmarked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
              <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" />
            </svg>
          </button>

          <!-- Fullscreen Toggle -->
          <button 
            type="button"
            @click="toggleFullscreen"
            class="p-2 rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-colors md-state-layer"
            :title="isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'"
          >
            <svg v-if="!isFullscreen" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
            </svg>
            <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  title: String,
  subtitle: String,
  currentPage: {
    type: Number,
    default: 1,
  },
  totalPages: {
    type: Number,
    default: 1,
  },
  currentMode: {
    type: String,
    default: 'flipbook',
  },
  isBookmarked: {
    type: Boolean,
    default: false,
  },
  isVisible: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits([
  'exit',
  'jump-page',
  'update:currentMode',
  'toggle-bookmark',
]);

const isFullscreen = ref(false);

function toggleMode() {
  const nextMode = props.currentMode === 'flipbook' ? 'webtoon' : 'flipbook';
  emit('update:currentMode', nextMode);
}

function onPageInputChange(e) {
  const val = parseInt(e.target.value);
  if (!isNaN(val)) {
    emit('jump-page', Math.max(1, Math.min(props.totalPages, val)));
  }
}

function onSliderInput(e) {
  emit('jump-page', parseInt(e.target.value));
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
    isFullscreen.value = true;
  } else {
    document.exitFullscreen().catch(() => {});
    isFullscreen.value = false;
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement;
}

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange);
});

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange);
});
</script>
