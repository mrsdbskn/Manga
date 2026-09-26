<template>
  <!-- Floating MD3 HUD -->
  <header 
    class="fixed top-0 left-0 right-0 z-50 transition-all duration-300 pointer-events-none"
    :class="[isVisible ? 'translate-y-0 opacity-100' : '-translate-y-full opacity-0']"
  >
    <div class="max-w-6xl mx-auto px-4 py-3 pointer-events-auto">
      <div class="glass-nav rounded-2xl px-4 py-2.5 flex items-center justify-between shadow-elevation-3 border border-white/10 relative">
        
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
            <h2 class="text-xs sm:text-sm font-bold text-white truncate max-w-[160px] sm:max-w-xs">
              {{ title || 'One Piece' }}
            </h2>
            <p class="text-[10px] sm:text-[11px] text-sky-300 truncate">
              {{ currentChapterTitle || subtitle || 'Manga Reader' }}
            </p>
          </div>
        </div>

        <!-- Center: Jump Controls & Page Pill -->
        <div class="flex items-center gap-2 sm:gap-3">
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

          <!-- Page Slider (Hidden on small screens) -->
          <div class="hidden lg:flex items-center gap-2 w-28 xl:w-36">
            <input 
              type="range"
              :min="1"
              :max="totalPages"
              :value="currentPage"
              @input="onSliderInput"
              class="w-full accent-sky-400 h-1.5 bg-white/20 rounded-lg cursor-pointer"
            />
          </div>

          <!-- Chapter Table of Contents (TOC) Dropdown Trigger -->
          <div class="relative" v-if="hasChapters">
            <button
              type="button"
              @click="toggleTocMenu"
              class="px-2.5 py-1 rounded-full bg-sky-500/20 text-sky-300 hover:bg-sky-500/30 border border-sky-500/30 text-xs font-medium flex items-center gap-1 transition-all md-state-layer"
              title="Table of Contents: Jump to Chapter"
            >
              <span>📑</span>
              <span class="hidden sm:inline">Chapters</span>
              <svg class="w-3 h-3 transition-transform" :class="tocOpen ? 'rotate-180' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="m6 9 6 6 6-6"/>
              </svg>
            </button>

            <!-- Floating Chapter TOC Menu -->
            <div 
              v-if="tocOpen" 
              class="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-72 max-h-80 overflow-y-auto bg-slate-900/95 backdrop-blur-xl border border-sky-500/20 rounded-2xl shadow-2xl p-2 z-50 space-y-1 custom-scrollbar animate-in fade-in zoom-in-95 duration-150"
            >
              <div class="px-3 py-1.5 text-[11px] font-bold text-sky-400 uppercase tracking-wider border-b border-white/10 flex justify-between items-center">
                <span>Volume Chapters</span>
                <span class="text-[10px] text-slate-400">{{ libraryStore.activeToc.length }} chapters</span>
              </div>
              <button
                v-for="ch in libraryStore.activeToc"
                :key="ch.chapterNumber"
                type="button"
                @click="jumpToChapter(ch)"
                :class="[
                  'w-full text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between transition-colors',
                  isChapterActive(ch)
                    ? 'bg-sky-500/30 text-sky-200 font-bold border border-sky-500/30'
                    : 'text-slate-300 hover:bg-white/10 hover:text-white'
                ]"
              >
                <div class="truncate pr-2">
                  <div class="font-medium text-white">{{ ch.title || `Chapter ${ch.chapterNumber}` }}</div>
                  <div class="text-[10px] text-slate-400">Chapter {{ ch.chapterNumber }}</div>
                </div>
                <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-black/40 text-sky-300 shrink-0">
                  p.{{ ch.startPage }}
                </span>
              </button>
            </div>
          </div>
        </div>

        <!-- Right: Mode Switcher, Audio, Fullscreen, Bookmark -->
        <div class="flex items-center gap-1 sm:gap-1.5 shrink-0">
          
          <!-- Audio Ambience & SFX Menu Trigger -->
          <div class="relative">
            <button
              type="button"
              @click="toggleAudioMenu"
              :class="[
                'p-2 rounded-full transition-colors md-state-layer',
                audioSettings.ambientMode !== 'off' || audioSettings.sfxEnabled
                  ? 'text-sky-400 bg-sky-400/20'
                  : 'text-slate-400 hover:text-white hover:bg-white/10'
              ]"
              title="Reading Audio & Ambient Soundscapes"
            >
              <svg v-if="audioSettings.ambientMode !== 'off' || audioSettings.sfxEnabled" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
              </svg>
              <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                <line x1="23" y1="9" x2="17" y2="15"/>
                <line x1="17" y1="9" x2="23" y2="15"/>
              </svg>
            </button>

            <!-- Audio Settings Popup -->
            <div 
              v-if="audioMenuOpen" 
              class="absolute right-0 top-full mt-2 w-64 bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-3 z-50 space-y-3 animate-in fade-in zoom-in-95 duration-150"
            >
              <div class="text-xs font-bold text-white flex items-center justify-between border-b border-white/10 pb-2">
                <span>🎧 Sound Atmosphere</span>
                <button @click="audioMenuOpen = false" class="text-slate-400 hover:text-white text-xs">✕</button>
              </div>

              <!-- Page Turn SFX -->
              <div class="flex items-center justify-between text-xs text-slate-300">
                <span>Page-Turn Flutter</span>
                <button 
                  type="button" 
                  @click="onToggleSfx"
                  :class="audioSettings.sfxEnabled ? 'bg-sky-500 text-white' : 'bg-white/10 text-slate-400'"
                  class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors"
                >
                  {{ audioSettings.sfxEnabled ? 'On' : 'Mute' }}
                </button>
              </div>

              <!-- Ambient Soundscape Selector -->
              <div class="space-y-1.5">
                <div class="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">Grand Line Ambience</div>
                <div class="grid grid-cols-2 gap-1.5 text-xs">
                  <button 
                    v-for="mode in ambientModes" 
                    :key="mode.id"
                    type="button"
                    @click="onSelectAmbient(mode.id)"
                    :class="[
                      'px-2 py-1.5 rounded-xl border text-left flex items-center gap-1.5 transition-all',
                      audioSettings.ambientMode === mode.id
                        ? 'bg-sky-500/20 border-sky-400 text-sky-300 font-bold'
                        : 'bg-black/20 border-white/10 text-slate-300 hover:bg-white/10'
                    ]"
                  >
                    <span>{{ mode.icon }}</span>
                    <span class="truncate">{{ mode.label }}</span>
                  </button>
                </div>
              </div>

              <!-- Ambient Volume Slider -->
              <div v-if="audioSettings.ambientMode !== 'off'" class="space-y-1 pt-1 border-t border-white/10">
                <div class="flex justify-between text-[11px] text-slate-400">
                  <span>Volume</span>
                  <span>{{ Math.round(audioSettings.ambientVolume * 100) }}%</span>
                </div>
                <input 
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  :value="audioSettings.ambientVolume"
                  @input="onAmbientVolumeChange"
                  class="w-full accent-sky-400 h-1 bg-white/20 rounded cursor-pointer"
                />
              </div>
            </div>
          </div>

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

          <!-- Reading Direction Toggle (Only shown in FlipBook mode) -->
          <button 
            v-if="currentMode === 'flipbook'"
            type="button"
            @click="toggleDirection"
            :class="[
              'px-2.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all md-state-layer border',
              readingDirection === 'rtl'
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
            ]"
            :title="readingDirection === 'rtl' ? 'Current: Authentic Manga RTL (Right page 1st). Click for Western LTR' : 'Current: Western LTR (Left page 1st). Click for Manga RTL'"
          >
            <span v-if="readingDirection === 'rtl'" class="flex items-center gap-1">
              <span>🇯🇵</span>
              <span class="font-bold">RTL</span>
            </span>
            <span v-else class="flex items-center gap-1">
              <span>📖</span>
              <span class="font-bold">LTR</span>
            </span>
          </button>

          <!-- Dual Spread vs Single Page Toggle (FlipBook Mode) -->
          <button 
            v-if="currentMode === 'flipbook'"
            type="button"
            @click="$emit('toggle-spread-mode')"
            :class="[
              'px-2.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all md-state-layer border',
              spreadMode === 'dual'
                ? 'bg-sky-500/20 text-sky-300 border-sky-500/30'
                : 'bg-white/10 text-slate-300 border-white/10'
            ]"
            :title="spreadMode === 'dual' ? 'Spread Layout: Dual Facing Pages (Both visible). Click for Single Page' : 'Spread Layout: Single Page. Click for Dual Facing Pages'"
          >
            <span>📖</span>
            <span class="font-bold hidden sm:inline">{{ spreadMode === 'dual' ? 'Both Pages' : '1-Page' }}</span>
            <span class="font-bold sm:hidden">{{ spreadMode === 'dual' ? '2P' : '1P' }}</span>
          </button>

          <!-- Screen Orientation / Virtual 90° Landscape Rotation Toggle -->
          <button 
            v-if="currentMode === 'flipbook'"
            type="button"
            @click="$emit('toggle-rotation')"
            :class="[
              'p-2 rounded-full transition-colors md-state-layer border',
              isRotated
                ? 'bg-amber-400/20 text-amber-300 border-amber-400/30'
                : 'text-slate-400 hover:text-white hover:bg-white/10 border-transparent'
            ]"
            :title="isRotated ? 'Screen Orientation: 90° Landscape Active. Click to reset to Vertical' : 'Rotate Screen 90° (Landscape View for phones)'"
          >
            <svg class="w-4 h-4 transform transition-transform" :class="isRotated ? 'rotate-90 text-amber-400' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
              <path d="M12 18h.01"/>
            </svg>
          </button>

          <!-- Zoom Magnifier Trigger -->
          <button 
            v-if="currentMode === 'flipbook'"
            type="button"
            @click="$emit('toggle-zoom')"
            class="p-2 rounded-full hover:bg-white/10 text-slate-400 hover:text-sky-300 transition-colors md-state-layer"
            title="Zoom & Pan Inspector (Z / Double-tap)"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              <line x1="11" y1="8" x2="11" y2="14"/>
              <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
          </button>

          <!-- Keyboard Shortcuts Cheatsheet Trigger -->
          <button 
            type="button"
            @click="shortcutsOpen = true"
            class="p-2 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors md-state-layer hidden sm:flex items-center justify-center"
            title="Keyboard Shortcuts & Gestures (?)"
          >
            <span class="text-xs font-mono font-bold">?</span>
          </button>

          <!-- Re-download / Update Volume from R2 -->
          <button 
            type="button"
            @click="onRedownloadVolume"
            class="p-2 rounded-full hover:bg-white/10 text-slate-400 hover:text-sky-300 transition-colors md-state-layer"
            title="Re-download Volume (Purge offline cache & fetch latest version from R2)"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
            </svg>
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

    <!-- Keyboard Shortcuts Cheatsheet Modal -->
    <KeyboardShortcutsModal :isOpen="shortcutsOpen" @close="shortcutsOpen = false" />
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useLibraryStore } from '../../stores/library.js';
import KeyboardShortcutsModal from '../UI/KeyboardShortcutsModal.vue';
import {
  playPageFlipSound,
  setAmbientMode,
  setAmbientVolume,
  toggleSfx,
  getAudioSettings,
} from '../../utils/audioEngine.js';

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
  readingDirection: {
    type: String,
    default: 'rtl',
  },
  spreadMode: {
    type: String,
    default: 'dual',
  },
  isRotated: {
    type: Boolean,
    default: false,
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
  'update:readingDirection',
  'update:spreadMode',
  'toggle-spread-mode',
  'toggle-rotation',
  'toggle-zoom',
  'toggle-bookmark',
]);

const libraryStore = useLibraryStore();
const isFullscreen = ref(false);
const tocOpen = ref(false);
const audioMenuOpen = ref(false);
const shortcutsOpen = ref(false);

const audioSettings = ref(getAudioSettings());

const ambientModes = [
  { id: 'ocean', label: 'Sea Waves', icon: '🌊' },
  { id: 'rain', label: 'Deck Rain', icon: '🌧️' },
  { id: 'wind', label: 'Ocean Wind', icon: '💨' },
  { id: 'off', label: 'Silence', icon: '🔇' },
];

const hasChapters = computed(() => {
  return libraryStore.activeToc && libraryStore.activeToc.length > 0;
});

const currentChapterTitle = computed(() => {
  if (!libraryStore.activeToc || libraryStore.activeToc.length === 0) return null;
  const current = libraryStore.activeToc.find(
    ch => props.currentPage >= ch.startPage && props.currentPage <= ch.endPage
  );
  return current ? current.title : null;
});

function isChapterActive(ch) {
  return props.currentPage >= ch.startPage && props.currentPage <= ch.endPage;
}

function toggleTocMenu() {
  tocOpen.value = !tocOpen.value;
  if (tocOpen.value) audioMenuOpen.value = false;
}

function toggleAudioMenu() {
  audioMenuOpen.value = !audioMenuOpen.value;
  if (audioMenuOpen.value) tocOpen.value = false;
}

function jumpToChapter(ch) {
  emit('jump-page', ch.startPage);
  tocOpen.value = false;
  playPageFlipSound();
}

function onToggleSfx() {
  const next = !audioSettings.value.sfxEnabled;
  toggleSfx(next);
  audioSettings.value.sfxEnabled = next;
  if (next) playPageFlipSound();
}

function onSelectAmbient(mode) {
  setAmbientMode(mode);
  audioSettings.value.ambientMode = mode;
}

function onAmbientVolumeChange(e) {
  const vol = parseFloat(e.target.value);
  setAmbientVolume(vol);
  audioSettings.value.ambientVolume = vol;
}

function toggleMode() {
  const nextMode = props.currentMode === 'flipbook' ? 'webtoon' : 'flipbook';
  emit('update:currentMode', nextMode);
}

function toggleDirection() {
  const nextDir = props.readingDirection === 'rtl' ? 'ltr' : 'rtl';
  emit('update:readingDirection', nextDir);
}

async function onRedownloadVolume() {
  const ok = confirm(`Re-download this volume from Cloudflare R2? This will replace your local cached copy with the latest update.`);
  if (ok) {
    await libraryStore.redownloadVolume();
  }
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

function onDocumentClick(e) {
  if (!e.target.closest('.glass-nav')) {
    tocOpen.value = false;
    audioMenuOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange);
  document.addEventListener('click', onDocumentClick);
  // Reconnect audio ambience if saved as active
  if (audioSettings.value.ambientMode !== 'off') {
    // Requires user interaction policy: will start upon first click
    const startAudioOnce = () => {
      setAmbientMode(audioSettings.value.ambientMode);
      window.removeEventListener('click', startAudioOnce);
    };
    window.addEventListener('click', startAudioOnce, { once: true });
  }
});

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange);
  document.removeEventListener('click', onDocumentClick);
  setAmbientMode('off');
});
</script>
