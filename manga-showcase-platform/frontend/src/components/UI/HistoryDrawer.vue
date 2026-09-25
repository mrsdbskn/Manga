<template>
  <div>
    <!-- Backdrop -->
    <transition name="fade">
      <div 
        v-if="isOpen"
        class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
        @click="close"
      ></div>
    </transition>

    <!-- Slide-over Panel -->
    <div 
      class="fixed top-0 bottom-0 right-0 z-50 w-full max-w-md bg-[#14161f] border-l border-white/10 shadow-elevation-5 flex flex-col transition-transform duration-300 ease-out"
      :class="[isOpen ? 'translate-x-0' : 'translate-x-full']"
    >
      <!-- Drawer Header -->
      <div class="p-5 border-b border-white/10 flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 8v4l3 3" />
              <circle cx="12" cy="12" r="9" />
            </svg>
          </div>
          <div>
            <h3 class="text-base font-bold text-white font-outfit">Reading History</h3>
            <p class="text-xs text-slate-400">{{ historySummary }}</p>
          </div>
        </div>

        <button 
          type="button"
          @click="close"
          class="p-2 rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-colors md-state-layer"
          title="Close drawer"
        >
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Drawer Content: List of Recent Reads -->
      <div class="flex-1 overflow-y-auto p-5 space-y-4">
        <!-- Empty State -->
        <div v-if="recentHistory.length === 0" class="h-64 flex flex-col items-center justify-center text-center p-6">
          <div class="w-12 h-12 rounded-full bg-white/[0.04] text-slate-500 flex items-center justify-center mb-3">
            <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
            </svg>
          </div>
          <p class="text-sm font-semibold text-slate-300">No reading history yet</p>
          <p class="text-xs text-slate-500 mt-1">Chapters and volumes you read will be saved here automatically.</p>
        </div>

        <!-- History Items -->
        <div 
          v-for="record in recentHistory" 
          :key="record.volumeId"
          class="glass-card rounded-2xl p-3.5 flex flex-col gap-2.5 border border-white/5 hover:border-white/15 transition-all group relative"
        >
          <!-- Individual Delete Record Button (appears on card) -->
          <button 
            type="button"
            @click.stop="deleteRecord(record.volumeId)"
            class="absolute top-3 right-3 p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
            title="Remove from history"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </button>

          <div class="flex items-center gap-3 pr-7">
            <!-- Cover / Badge Icon -->
            <div 
              class="w-12 h-16 rounded-md overflow-hidden shrink-0 border flex flex-col items-center justify-center relative"
              :class="[
                isChapter(record) 
                  ? 'bg-amber-950/20 border-amber-500/30' 
                  : 'bg-sky-950/20 border-sky-500/30'
              ]"
            >
              <!-- Cover image if available -->
              <img 
                v-if="getItemCover(record)"
                :src="getItemCover(record)" 
                class="w-full h-full object-cover"
                @error="$event.target.style.display='none'"
              />
              <!-- Fallback Badge -->
              <div class="flex flex-col items-center justify-center p-1 text-center">
                <span 
                  class="text-[11px] font-extrabold tracking-wider font-mono"
                  :class="isChapter(record) ? 'text-amber-400' : 'text-sky-400'"
                >
                  {{ isChapter(record) ? 'CH' : 'VOL' }}
                </span>
                <span 
                  v-if="getItemMeta(record).number"
                  class="text-[9px] font-mono text-slate-400"
                >
                  {{ getItemMeta(record).number }}
                </span>
              </div>
            </div>

            <!-- Details -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-1">
                <h4 class="text-xs font-bold text-white truncate" :title="getItemTitle(record)">
                  {{ getItemTitle(record) }}
                </h4>
              </div>

              <div class="flex items-center gap-2 mt-0.5">
                <span 
                  class="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.2 rounded"
                  :class="isChapter(record) ? 'bg-amber-500/10 text-amber-300' : 'bg-sky-500/10 text-sky-300'"
                >
                  {{ isChapter(record) ? 'Chapter' : 'Volume' }}
                </span>
                <span class="text-[11px] text-slate-400">
                  Page {{ record.lastPage }} of {{ record.totalPages }}
                </span>
              </div>

              <!-- Time ago -->
              <p class="text-[10px] font-mono text-slate-500 mt-1">
                {{ formatTime(record.updatedAt) }}
              </p>

              <!-- Progress bar -->
              <div class="mt-2">
                <ProgressBarMD3 :value="record.percentage" :height="4" :showLabel="true" />
              </div>
            </div>
          </div>

          <!-- Bookmarks list if any -->
          <div v-if="record.bookmarks && record.bookmarks.length > 0" class="flex flex-wrap items-center gap-1.5 pt-2 border-t border-white/5">
            <span class="text-[10px] text-slate-500">Bookmarks:</span>
            <span 
              v-for="bm in record.bookmarks" 
              :key="bm"
              class="text-[10px] px-2 py-0.5 rounded bg-amber-400/10 text-amber-300 font-mono"
            >
              P. {{ bm }}
            </span>
          </div>

          <!-- Action Button: Resume or Re-open -->
          <button 
            type="button"
            @click="resumeReading(record)"
            class="w-full py-1.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
            :class="[
              canDirectlyResume(record)
                ? 'bg-white/[0.06] hover:bg-sky-500/20 text-sky-300'
                : 'bg-white/[0.04] hover:bg-white/[0.1] text-slate-300'
            ]"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M5 3l14 9-14 9V3z" />
            </svg>
            <span>{{ getResumeButtonText(record) }}</span>
          </button>
        </div>
      </div>

      <!-- Drawer Footer -->
      <div v-if="recentHistory.length > 0" class="p-4 border-t border-white/10 bg-[#0f1118]">
        <button 
          type="button"
          @click="confirmClearHistory"
          class="w-full py-2 rounded-xl text-xs font-semibold text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 transition-colors"
        >
          Clear Reading History
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useLibraryStore } from '../../stores/library.js';
import { useProgressStore } from '../../stores/progress.js';
import { parseMangaMetadata } from '../../utils/mangaTitle.js';
import ProgressBarMD3 from './ProgressBarMD3.vue';

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['close']);

const libraryStore = useLibraryStore();
const progressStore = useProgressStore();

const recentHistory = computed(() => {
  return progressStore.recentHistory;
});

const historySummary = computed(() => {
  const list = recentHistory.value;
  if (list.length === 0) return '0 items logged';
  
  let chapters = 0;
  let volumes = 0;
  list.forEach(r => {
    if (isChapter(r)) chapters++;
    else volumes++;
  });

  const parts = [];
  if (chapters > 0) parts.push(`${chapters} chapter${chapters > 1 ? 's' : ''}`);
  if (volumes > 0) parts.push(`${volumes} volume${volumes > 1 ? 's' : ''}`);
  return `${parts.join(', ')} logged`;
});

function getVolume(volumeId) {
  return libraryStore.volumes.find(v => v.id === volumeId);
}

function getItemMeta(record) {
  const vol = getVolume(record.volumeId);
  const raw = record.title || vol?.title || record.fileName || record.volumeId;
  return parseMangaMetadata(raw, null, record.totalPages);
}

function isChapter(record) {
  if (record.type === 'chapter') return true;
  if (record.type === 'volume') return false;
  return getItemMeta(record).type === 'chapter';
}

function getItemTitle(record) {
  // If record already has a clean title, return it
  if (record.title && !record.title.startsWith('local-')) {
    return record.title;
  }
  const vol = getVolume(record.volumeId);
  if (vol && vol.title) return vol.title;
  
  return getItemMeta(record).title;
}

function getItemCover(record) {
  const vol = getVolume(record.volumeId);
  if (vol?.coverUrl) return vol.coverUrl;
  return record.coverUrl || null;
}

function canDirectlyResume(record) {
  if (getVolume(record.volumeId)) return true;
  return libraryStore.activeVolume && libraryStore.activeVolume.id === record.volumeId;
}

function getResumeButtonText(record) {
  if (canDirectlyResume(record)) {
    return `Resume from Page ${record.lastPage}`;
  }
  return `Re-open File (Page ${record.lastPage})`;
}

function close() {
  emit('close');
}

function resumeReading(record) {
  const vol = getVolume(record.volumeId);
  if (vol) {
    libraryStore.openReader(vol);
    close();
    return;
  }

  // If it is the current active local volume
  if (libraryStore.activeVolume && libraryStore.activeVolume.id === record.volumeId) {
    libraryStore.isReading = true;
    close();
    return;
  }

  // If local file needs to be re-opened from disk
  libraryStore.toggleLocalDropzone();
  close();
}

function deleteRecord(volumeId) {
  progressStore.deleteRecord(volumeId);
}

function confirmClearHistory() {
  if (confirm('Are you sure you want to clear your reading progress history?')) {
    progressStore.clearAllHistory();
  }
}

function formatTime(timestamp) {
  if (!timestamp) return '';
  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
</script>
