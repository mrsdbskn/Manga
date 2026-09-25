/**
 * stores/library.js - Pinia store for comics catalog, storyline sagas, search, and active reading session.
 */

import { defineStore } from 'pinia';
import { CANON_SAGAS, getSagaById, getSagaForVolume } from '../utils/sagaData.js';
import { unpackCbz, loadRemoteCbz, revokeAllocatedBlobs } from '../utils/cbzLoader.js';
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

    // ACTIVE READING SESSION STATE
    isReading: false,
    activeVolume: null,
    activePages: [],
    activeComicInfo: null,
    // Reader unpacking progress
    isUnpacking: false,
    unpackProgress: 0,
    unpackStatusText: '',
    unpackError: null,

    // UI Drawer and Modal visibility
    historyDrawerOpen: false,
    localDropzoneOpen: false,
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
        // Resolve path relative to Vite base
        const response = await fetch('./comics/index.json');
        if (!response.ok) {
          throw new Error(`Failed to load index.json (HTTP ${response.status})`);
        }
        const data = await response.json();
        
        if (data.volumes && Array.isArray(data.volumes)) {
          this.volumes = data.volumes;
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
          spineColor: '#38bdf8',
          available: v <= 2,
          cbzFile: `One Piece - v${v < 10 ? '0' + v : v} (c${String((v - 1) * 8 + 1).padStart(3, '0')}-${String(v * 8).padStart(3, '0')}).cbz`
        });
      }
      this.volumes = fallbackList;
    },

    /**
     * Opens the reader for a specified volume from the catalog.
     */
    async openReader(volume) {
      if (!volume) return;

      this.activeVolume = volume;
      this.isUnpacking = true;
      this.unpackError = null;
      this.unpackProgress = 0;
      this.unpackStatusText = 'Locating volume archive...';

      try {
        let cbzUrl = null;
        if (volume.cbzFile) {
          cbzUrl = `./comics/${encodeURIComponent(volume.cbzFile)}`;
        } else {
          cbzUrl = `./comics/One Piece - v${String(volume.volumeNumber).padStart(2, '0')} (c${String(volume.chapterStart).padStart(3, '0')}-${String(volume.chapterEnd).padStart(3, '0')}).cbz`;
        }

        const result = await loadRemoteCbz(cbzUrl, (pct, status) => {
          this.unpackProgress = pct;
          this.unpackStatusText = status;
        });

        this.activePages = result.pages;
        this.activeComicInfo = result.comicInfo;
        this.isReading = true;

        // Resume reading progress
        const progressStore = useProgressStore();
        const progress = progressStore.getProgressForVolume(volume.id);
        if (!progress.lastPage) {
          progressStore.saveProgress(volume.id, 1, result.totalPages, volume.chapterStart);
        }
      } catch (err) {
        console.error('Failed to open volume archive:', err);
        this.unpackError = `Could not load volume archive: ${err.message}. If this volume has not been packaged yet, drop a local CBZ using the Local Reader.`;
      } finally {
        this.isUnpacking = false;
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

        // Determine volume metadata from ComicInfo or filename
        let volNum = 1;
        let title = file.name.replace(/\.[^/.]+$/, "");
        
        if (result.comicInfo) {
          if (result.comicInfo.volume) volNum = parseInt(result.comicInfo.volume) || 1;
          if (result.comicInfo.title) title = result.comicInfo.title;
        }

        const saga = getSagaForVolume(volNum);

        const localVol = {
          id: `local-${Date.now()}`,
          volumeNumber: volNum,
          title: title,
          sagaId: saga.id,
          sagaName: saga.name,
          arcName: result.comicInfo?.arc || saga.name,
          chapterStart: parseInt(result.comicInfo?.startChapter) || 1,
          chapterEnd: parseInt(result.comicInfo?.endChapter) || 1,
          pageCount: result.totalPages,
          coverUrl: result.pages[0]?.url || '',
          spineColor: saga.themeColor,
          isLocal: true,
          fileName: file.name,
        };

        this.activeVolume = localVol;
        this.activePages = result.pages;
        this.activeComicInfo = result.comicInfo;
        this.isReading = true;
        this.localDropzoneOpen = false;

        const progressStore = useProgressStore();
        progressStore.saveProgress(localVol.id, 1, result.totalPages, localVol.chapterStart);
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
