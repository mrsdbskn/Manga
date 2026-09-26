<template>
  <div 
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
    @click.self="$emit('close')"
  >
    <div class="glass-card rounded-3xl p-6 sm:p-8 max-w-2xl w-full border border-white/10 shadow-elevation-5 max-h-[90vh] flex flex-col relative overflow-hidden">
      
      <!-- Top Decorative Glow -->
      <div class="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-emerald-400 to-transparent"></div>

      <!-- Modal Header -->
      <div class="flex items-center justify-between pb-4 border-b border-white/10 shrink-0">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shadow-lg shadow-emerald-500/10">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" x2="12" y1="15" y2="3" />
            </svg>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-base sm:text-lg font-bold text-white font-outfit">
                Offline Downloads & Cache
              </h3>
              <span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono font-bold border border-emerald-500/30">
                {{ storageInfo.totalMB }} MB
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-0.5">
              Manage saved manga archives. Clear or re-download updated volumes from R2.
            </p>
          </div>
        </div>

        <button 
          type="button"
          @click="$emit('close')"
          class="p-2 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
        >
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Quick Metrics Bar -->
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 my-4 shrink-0">
        <div class="p-3 rounded-2xl bg-white/[0.04] border border-white/5">
          <div class="text-[11px] text-slate-400 font-medium">Cached Volumes</div>
          <div class="text-lg font-bold text-white font-mono mt-0.5">{{ storageInfo.count }}</div>
        </div>
        <div class="p-3 rounded-2xl bg-white/[0.04] border border-white/5">
          <div class="text-[11px] text-slate-400 font-medium">Storage Used</div>
          <div class="text-lg font-bold text-emerald-400 font-mono mt-0.5">{{ storageInfo.totalMB }} MB</div>
        </div>
        <div class="p-3 rounded-2xl bg-white/[0.04] border border-white/5 col-span-2 sm:col-span-1">
          <div class="text-[11px] text-slate-400 font-medium">Offline Status</div>
          <div class="text-xs font-semibold text-sky-300 mt-1 flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Instant Zero-Lag</span>
          </div>
        </div>
      </div>

      <!-- Cached Volumes List -->
      <div class="flex-1 overflow-y-auto pr-1 space-y-2 custom-scrollbar my-2">
        <template v-if="storageInfo.items && storageInfo.items.length > 0">
          <div 
            v-for="item in storageInfo.items" 
            :key="item.url"
            class="p-3 sm:p-3.5 rounded-2xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/5 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
          >
            <!-- Left Info: Cover & Title -->
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-10 h-14 rounded-lg bg-black/40 border border-white/10 overflow-hidden shrink-0 flex items-center justify-center">
                <img 
                  v-if="resolveCover(item)"
                  :src="resolveCover(item)" 
                  :alt="item.name"
                  class="w-full h-full object-cover"
                />
                <span v-else class="text-xs text-slate-500 font-mono">CBZ</span>
              </div>

              <div class="min-w-0">
                <h4 class="text-xs sm:text-sm font-semibold text-white truncate font-outfit">
                  {{ resolveTitle(item) }}
                </h4>
                <div class="flex items-center gap-2 mt-0.5 text-[11px] text-slate-400">
                  <span class="font-mono text-emerald-400 font-semibold">{{ item.sizeMB }} MB</span>
                  <span>•</span>
                  <span class="truncate max-w-[180px] sm:max-w-xs text-slate-500">{{ item.name }}</span>
                </div>
              </div>
            </div>

            <!-- Right Action Buttons -->
            <div class="flex items-center gap-2 shrink-0 self-end sm:self-center">
              <!-- Re-download / Update from R2 Button -->
              <button 
                type="button"
                @click="onRedownload(item)"
                class="px-3 py-1.5 rounded-full text-xs font-semibold bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 border border-sky-500/20 flex items-center gap-1.5 transition-all md-state-layer"
                title="Purge cached copy & re-download the latest version directly from R2"
              >
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
                </svg>
                <span>Re-download</span>
              </button>

              <!-- Delete Cached Volume Button -->
              <button 
                type="button"
                @click="onDeleteVolume(item)"
                class="p-2 rounded-full hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-colors"
                title="Delete this cached volume from offline storage"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
              </button>
            </div>
          </div>
        </template>

        <!-- Empty State -->
        <div v-else class="text-center py-12 px-4 rounded-2xl bg-white/[0.02] border border-dashed border-white/10">
          <div class="w-12 h-12 rounded-2xl bg-white/[0.04] text-slate-500 flex items-center justify-center mx-auto mb-3">
            <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" x2="12" y1="15" y2="3" />
            </svg>
          </div>
          <h4 class="text-sm font-bold text-white font-outfit">No Offline Volumes Cached</h4>
          <p class="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            When you open manga volumes from the showcase, they are automatically cached here for zero-latency offline reading.
          </p>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="pt-4 border-t border-white/10 flex items-center justify-between shrink-0 gap-3">
        <button 
          v-if="storageInfo.count > 0"
          type="button"
          @click="onClearAll"
          class="px-4 py-2 rounded-full text-xs font-semibold text-rose-400 hover:text-white hover:bg-rose-500/20 border border-rose-500/20 transition-all flex items-center gap-1.5"
        >
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
          <span>Clear All Downloads</span>
        </button>
        <div v-else></div>

        <button 
          type="button"
          @click="$emit('close')"
          class="px-5 py-2 rounded-full text-xs font-semibold bg-white/10 hover:bg-white/20 text-white transition-all"
        >
          Done
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useLibraryStore } from '../../stores/library.js';
import { deleteVolumeFromCache } from '../../utils/cbzLoader.js';

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['close']);

const libraryStore = useLibraryStore();

const storageInfo = computed(() => libraryStore.cachedStorageInfo || { count: 0, totalBytes: 0, totalMB: '0.0', items: [] });

function findMatchingVolume(item) {
  if (!libraryStore.volumes || libraryStore.volumes.length === 0) return null;
  const rawDecoded = decodeURIComponent(item.name || '').toLowerCase();
  return libraryStore.volumes.find(v => {
    if (v.cbzFile && rawDecoded.includes(v.cbzFile.toLowerCase())) return true;
    if (v.fileName && rawDecoded.includes(v.fileName.toLowerCase())) return true;
    if (v.id && item.url.includes(v.id)) return true;
    return false;
  });
}

function resolveTitle(item) {
  const vol = findMatchingVolume(item);
  if (vol) return vol.title || `Volume ${vol.volumeNumber}`;
  return item.name.replace(/\.cbz$/i, '').replace(/_/g, ' ');
}

function resolveCover(item) {
  const vol = findMatchingVolume(item);
  return vol?.coverUrl || null;
}

async function onRedownload(item) {
  const vol = findMatchingVolume(item);
  if (vol) {
    emit('close');
    await libraryStore.redownloadVolume(vol);
  } else {
    // If not directly mapped, bypass cache on URL and reload info
    const ok = confirm(`Re-download latest version of ${item.name}?`);
    if (ok) {
      emit('close');
      await libraryStore.openReader({
        id: item.name,
        title: item.name,
        cbzFile: item.name,
      }, { forceRedownload: true });
    }
  }
}

async function onDeleteVolume(item) {
  const ok = confirm(`Remove "${item.name}" from offline storage?`);
  if (!ok) return;
  const vol = findMatchingVolume(item);
  if (vol) {
    await libraryStore.deleteCachedVolume(vol);
  } else {
    await deleteVolumeFromCache(item.url);
    await libraryStore.refreshStorageInfo();
  }
}

async function onClearAll() {
  const ok = confirm(`Are you sure you want to clear all ${storageInfo.value.count} downloaded manga volumes? You can re-download them anytime.`);
  if (!ok) return;
  await libraryStore.clearAllDownloadedVolumes();
}
</script>
