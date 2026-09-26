/**
 * stores/library.js - Pinia store for comics catalog, storyline sagas, search, and active reading session.
 */

import { defineStore } from 'pinia';
import { CANON_SAGAS, getSagaById, getSagaForVolume } from '../utils/sagaData.js';
import {
  unpackCbz,
  loadRemoteCbz,
  revokeAllocatedBlobs,
  deleteVolumeFromCache,
  getCachedVolumesInfo,
  clearVolumeCache,
} from '../utils/cbzLoader.js';
import { parseMangaMetadata } from '../utils/mangaTitle.js';
import { useProgressStore } from './progress.js';

export const useLibraryStore = defineStore('library', {
  state: () => ({
    // Sagas with counts and metadata
    sagas: CANON_SAGAS,
    // Master list of all registered manga volumes
    volumes: [],
    // Currently active saga filter (null or 'all' = all sagas)
    activeSagaFilter: 'all',
    // Search query string
    searchQuery: '',
    // Dashboard layout: 'grid' | 'list'
    viewMode: 'grid',
    // Catalog loading state
    isLoadingCatalog: false,
    catalogError: null,
    r2PublicUrl: 'https://pub-7eec745686a84d72ad6f6712fe54a988.r2.dev',

    // ACTIVE READING SESSION STATE
    isReading: false,
    activeVolume: null,
    activePages: [],
    activeComicInfo: null,
    activeToc: [],
    // Reader unpacking progress
    isUnpacking: false,
    unpackProgress: 0,
    unpackStatusText: '',
    unpackError: null,

    // UI Drawer, Storage and Modal visibility
    historyDrawerOpen: false,
    localDropzoneOpen: false,
    storageModalOpen: false,
    cachedStorageInfo: { count: 0, totalBytes: 0, totalMB: '0.0', items: [] },
  }),

  getters: {
    /**
     * Filtered list of volumes matching active saga and search query.
     */
    filteredVolumes: (state) => {
      let result = [...state.volumes];

      // Filter by Saga
      if (state.activeSagaFilter && state.activeSagaFilter !== 'all') {
        result = result.filter(v => v.sagaId === state.activeSagaFilter);
      }

      // Filter by Search Query
      if (state.searchQuery.trim()) {
        const q = state.searchQuery.toLowerCase().trim();
        result = result.filter(v => {
          const matchTitle = (v.title || '').toLowerCase().includes(q);
          const matchJap = (v.japaneseTitle || '').toLowerCase().includes(q);
          const matchArc = (v.arcName || '').toLowerCase().includes(q);
          const matchSaga = (v.sagaName || '').toLowerCase().includes(q);
          const matchVolNum = `volume ${v.volumeNumber}`.includes(q) || `vol ${v.volumeNumber}`.includes(q) || `v${v.volumeNumber}` === q;
          return matchTitle || matchJap || matchArc || matchSaga || matchVolNum;
        });
      }

      return result;
    },

    /**
     * Group filtered volumes by Saga for segmented dashboard display.
     */
    groupedBySaga: (state) => {
      const groups = [];
      const sagasToInclude = state.activeSagaFilter && state.activeSagaFilter !== 'all'
        ? state.sagas.filter(s => s.id === state.activeSagaFilter)
        : state.sagas;

      for (const saga of sagasToInclude) {
        let vols = state.volumes.filter(v => v.sagaId === saga.id);
        
        // Also apply search query to group
        if (state.searchQuery.trim()) {
          const q = state.searchQuery.toLowerCase().trim();
          vols = vols.filter(v => {
            return (v.title || '').toLowerCase().includes(q) ||
                   (v.arcName || '').toLowerCase().includes(q) ||
                   `vol ${v.volumeNumber}`.includes(q);
          });
        }

        if (vols.length > 0) {
          groups.push({
            saga,
            volumes: vols,
          });
        }
      }

      return groups;
    },

    /**
     * Total available volumes in catalog.
     */
    totalVolumeCount: (state) => state.volumes.length,
  },

  actions: {
    /**
     * Fetches master catalog manifest from public/comics/index.json.
     * Falls back to canonical baseline if the JSON is missing or inaccessible.
     */
    async loadCatalog() {
      this.isLoadingCatalog = true;
      this.catalogError = null;

      try {
        // Resolve path relative to Vite base with cache busting to guarantee fresh catalog
        const response = await fetch(`./comics/index.json?_t=${Date.now()}`, { cache: 'no-cache' });
        if (!response.ok) {
          throw new Error(`Failed to load index.json (HTTP ${response.status})`);
        }
        const data = await response.json();
        
        if (data.volumes && Array.isArray(data.volumes)) {
          this.volumes = data.volumes;
        }
        if (data.r2PublicUrl) {
          this.r2PublicUrl = data.r2PublicUrl;
        }
        if (data.sagas && Array.isArray(data.sagas)) {
          // Merge with detailed local metadata (like badge colors)
          this.sagas = data.sagas.map(s => {
            const local = CANON_SAGAS.find(ls => ls.id === s.id) || {};
            return { ...local, ...s };
          });
        }
      } catch (err) {
        console.warn('Notice: Could not fetch public/comics/index.json, generating canon baseline:', err);
        this.catalogError = err.message;
        this._buildFallbackCatalog();
      } finally {
        this.isLoadingCatalog = false;
      }
    },

    /**
     * Fallback catalog generator when offline or before tools have run.
     */
    _buildFallbackCatalog() {
      const fallbackList = [];
      for (let v = 1; v <= 12; v++) {
        fallbackList.push({
          id: `one-piece-v${v < 10 ? '0' + v : v}`,
          volumeNumber: v,
          title: v === 1 ? 'Romance Dawn' : v === 2 ? "Versus!! Buggy's Pirate Crew" : `Volume ${v}`,
          sagaId: 'east-blue',
          sagaName: 'East Blue Saga',
          arcName: v <= 3 ? 'Romance Dawn Arc' : 'East Blue Arc',
          chapterStart: (v - 1) * 8 + 1,
          chapterEnd: v * 8,
          pageCount: 200,
          coverUrl: `comics/covers/cover-v${v < 10 ? '0' + v : v}.webp`,
          backCoverUrl: `comics/covers/back-cover-v${v < 10 ? '0' + v : v}.webp`,
          spineUrl: `comics/covers/spine-v${v < 10 ? '0' + v : v}.webp`,
          spineColor: '#38bdf8',
          available: v <= 2,
          cbzFile: `One Piece - v${v < 10 ? '0' + v : v} (c${String((v - 1) * 8 + 1).padStart(3, '0')}-${String(v * 8).padStart(3, '0')}).cbz`
        });
      }
      this.volumes = fallbackList;
    },

    /**
     * Resolves the primary download/streaming URL for a given volume.
     */
    _resolveCbzUrl(volume) {
      if (!volume) return '';
      if (volume.cbzUrl) return volume.cbzUrl;
      if (volume.cbzFile && (volume.cbzFile.startsWith('http://') || volume.cbzFile.startsWith('https://'))) {
        return volume.cbzFile;
      }
      if (this.r2PublicUrl && volume.cbzFile) {
        return `${this.r2PublicUrl.replace(/\/+$/, '')}/${encodeURIComponent(volume.cbzFile)}`;
      }
      if (volume.cbzFile) {
        return `./comics/${encodeURIComponent(volume.cbzFile)}`;
      }
      return `./comics/One Piece - v${String(volume.volumeNumber).padStart(2, '0')} (c${String(volume.chapterStart).padStart(3, '0')}-${String(volume.chapterEnd).padStart(3, '0')}).cbz`;
    },

    /**
     * Opens the reader for a specified volume from the catalog.
     * @param {Object} volume - Volume metadata object
     * @param {Object} [options] - Options: { forceRedownload: boolean }
     */
    async openReader(volume, options = {}) {
      if (!volume) return;
      const { forceRedownload = false } = options;

      this.activeVolume = volume;
      this.isUnpacking = true;
      this.unpackError = null;
      this.unpackProgress = 0;
      this.unpackStatusText = forceRedownload 
        ? 'Purging cache & re-downloading fresh volume from R2...' 
        : 'Locating volume archive...';

      try {
        const cbzUrl = this._resolveCbzUrl(volume);

        let result;
        try {
          result = await loadRemoteCbz(cbzUrl, (pct, status) => {
            this.unpackProgress = pct;
            this.unpackStatusText = status;
          }, { forceBypassCache: forceRedownload });
        } catch (streamErr) {
          // If initial URL failed and we haven't tried Cloudflare R2 yet, attempt R2 fallback
          const fallbackR2 = (!cbzUrl.startsWith('http') && this.r2PublicUrl && volume.cbzFile)
            ? `${this.r2PublicUrl.replace(/\/+$/, '')}/${encodeURIComponent(volume.cbzFile)}`
            : null;

          if (fallbackR2 && fallbackR2 !== cbzUrl) {
            console.warn(`Initial stream failed (${streamErr.message}). Retrying via Cloudflare R2: ${fallbackR2}`);
            this.unpackStatusText = 'Connecting to Cloudflare R2 stream...';
            result = await loadRemoteCbz(fallbackR2, (pct, status) => {
              this.unpackProgress = pct;
              this.unpackStatusText = status;
            }, { forceBypassCache: forceRedownload });
          } else {
            throw streamErr;
          }
        }

        this.activePages = result.pages;
        this.activeComicInfo = result.comicInfo;
        this.activeToc = (result.toc && result.toc.length > 0) ? result.toc : (volume.chapters || []);
        this.isReading = true;

        // Resume reading progress
        const progressStore = useProgressStore();
        const progress = progressStore.getProgressForVolume(volume.id);
        if (!progress.lastPage) {
          progressStore.saveProgress(volume.id, 1, result.totalPages, volume.chapterStart, {
            title: volume.title,
            type: 'volume',
            coverUrl: volume.coverUrl,
          });
        }
        // Refresh offline storage inventory
        this.refreshStorageInfo();
      } catch (err) {
        console.error('Failed to open volume archive:', err);
        this.unpackError = `Could not load volume archive: ${err.message}. If this volume has not been packaged yet, drop a local CBZ using the Local Reader.`;
      } finally {
        this.isUnpacking = false;
      }
    },

    /**
     * Purges the cached copy of the active (or passed) volume and re-downloads fresh from Cloudflare R2.
     */
    async redownloadVolume(volume = null) {
      const vol = volume || this.activeVolume;
      if (!vol) return;
      return this.openReader(vol, { forceRedownload: true });
    },

    /**
     * Deletes a specific volume from browser offline storage.
     */
    async deleteCachedVolume(volume) {
      if (!volume) return;
      const url = this._resolveCbzUrl(volume);
      await deleteVolumeFromCache(url);
      await this.refreshStorageInfo();
    },

    /**
     * Clears all cached volume archives from browser CacheStorage.
     */
    async clearAllDownloadedVolumes() {
      await clearVolumeCache();
      await this.refreshStorageInfo();
    },

    /**
     * Refreshes the cached storage metrics (count, bytes, MB).
     */
    async refreshStorageInfo() {
      this.cachedStorageInfo = await getCachedVolumesInfo();
    },

    /**
     * Toggles the offline storage management modal.
     */
    toggleStorageModal() {
      this.storageModalOpen = !this.storageModalOpen;
      if (this.storageModalOpen) {
        this.refreshStorageInfo();
      }
    },

    /**
     * Reads a local user-dragged .cbz or .zip file immediately in memory.
     */
    async openWithLocalFile(file) {
      if (!file) return;

      this.isUnpacking = true;
      this.unpackError = null;
      this.unpackProgress = 0;
      this.unpackStatusText = `Reading ${file.name}...`;

      try {
        const result = await unpackCbz(file, (pct, status) => {
          this.unpackProgress = pct;
          this.unpackStatusText = status;
        });

        // Clean, structured metadata detection using parseMangaMetadata
        const meta = parseMangaMetadata(file.name, result.comicInfo, result.totalPages);
        const itemType = meta.type;
        const title = meta.title;
        const volNum = meta.type === 'volume' ? (meta.number || 1) : 1;
        const chStart = meta.type === 'chapter' ? (meta.number || 1) : 1;
        const chEnd = chStart;

        // Deterministic stable ID so reopening this exact file resumes progress
        const cleanKey = file.name.replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase();
        const stableId = `local-${itemType}-${cleanKey}`;

        const saga = getSagaForVolume(volNum);

        const localVol = {
          id: stableId,
          volumeNumber: volNum,
          type: itemType,
          title: title,
          sagaId: saga.id,
          sagaName: saga.name,
          arcName: result.comicInfo?.arc || saga.name,
          chapterStart: chStart,
          chapterEnd: chEnd,
          pageCount: result.totalPages,
          coverUrl: result.pages[0]?.url || '',
          spineColor: saga.themeColor,
          isLocal: true,
          fileName: file.name,
        };

        this.activeVolume = localVol;
        this.activePages = result.pages;
        this.activeComicInfo = result.comicInfo;
        this.activeToc = result.toc || [];
        this.isReading = true;
        this.localDropzoneOpen = false;

        const progressStore = useProgressStore();
        const existingProgress = progressStore.getProgressForVolume(localVol.id);
        const resumePage = existingProgress?.lastPage || 1;
        progressStore.saveProgress(localVol.id, resumePage, result.totalPages, localVol.chapterStart, {
          title: localVol.title,
          type: localVol.type,
          coverUrl: localVol.coverUrl,
          fileName: file.name,
        });
      } catch (err) {
        console.error('Local CBZ read error:', err);
        this.unpackError = `Error reading file: ${err.message}`;
      } finally {
        this.isUnpacking = false;
      }
    },

    /**
     * Closes the active reader and releases object URLs from memory.
     */
    closeReader() {
      this.isReading = false;
      this.activeVolume = null;
      this.activePages = [];
      this.activeComicInfo = null;
      this.unpackError = null;
      revokeAllocatedBlobs();
    },

    toggleViewMode() {
      this.viewMode = this.viewMode === 'grid' ? 'list' : 'grid';
    },

    setViewMode(mode) {
      if (mode === 'grid' || mode === 'list') {
        this.viewMode = mode;
      }
    },

    setActiveSagaFilter(sagaId) {
      this.activeSagaFilter = sagaId;
    },

    setSearchQuery(q) {
      this.searchQuery = q;
    },

    toggleHistoryDrawer() {
      this.historyDrawerOpen = !this.historyDrawerOpen;
    },

    toggleLocalDropzone() {
      this.localDropzoneOpen = !this.localDropzoneOpen;
    },
  },
});
