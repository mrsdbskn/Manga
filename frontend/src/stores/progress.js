/**
 * stores/progress.js - Persistent reading progress store backed by localStorage.
 * Automatically saves last-read page, chapter, completion percentage, bookmarks,
 * and user reading mode preference across sessions.
 */

import { defineStore } from 'pinia';

const STORAGE_KEY = 'manga_showcase_reading_progress';
const PREF_KEY = 'manga_showcase_reader_pref';
const DIRECTION_KEY = 'manga_showcase_reading_direction';
const SPREAD_KEY = 'manga_showcase_spread_mode';
const ROTATION_KEY = 'manga_showcase_screen_rotation';

export const useProgressStore = defineStore('progress', {
  state: () => ({
    // Records keyed by volumeId (e.g. 'one-piece-v01')
    records: JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'),
    // Preferred reading engine: 'flipbook' (3D StPageFlip) | 'webtoon' (Vertical scroll)
    readMode: localStorage.getItem(PREF_KEY) || 'flipbook',
    // Reading direction: 'rtl' (Authentic Manga Right-to-Left, default) | 'ltr' (Western Left-to-Right)
    readingDirection: localStorage.getItem(DIRECTION_KEY) || 'rtl',
    // Spread mode: 'dual' (always show both facing pages side-by-side) | 'single' (1 page)
    spreadMode: localStorage.getItem(SPREAD_KEY) || 'dual',
    // Virtual 90° landscape rotation mode for phone reading
    isRotatedLandscape: localStorage.getItem(ROTATION_KEY) === 'true',
  }),

  getters: {
    /**
     * Returns a sorted list of recently read volume IDs, ordered by most recently updated.
     */
    recentHistory: (state) => {
      return Object.values(state.records).sort((a, b) => b.updatedAt - a.updatedAt);
    },

    /**
     * Returns the single most recently read volume record for quick resume.
     */
    mostRecentVolume: (state) => {
      const history = Object.values(state.records).sort((a, b) => b.updatedAt - a.updatedAt);
      return history.length > 0 ? history[0] : null;
    },

    /**
     * Retrieve progress for a specific volume.
     */
    getProgressForVolume: (state) => (volumeId) => {
      if (!volumeId || !state.records[volumeId]) {
        return {
          volumeId,
          lastPage: 1,
          totalPages: 1,
          percentage: 0,
          completed: false,
          updatedAt: 0,
          bookmarks: [],
        };
      }
      return state.records[volumeId];
    },

    /**
     * Total number of books started or completed.
     */
    totalVolumesRead: (state) => Object.keys(state.records).length,
  },

  actions: {
    /**
     * Updates reading progress for a volume and synchronizes with localStorage.
     */
    saveProgress(volumeId, currentPage, totalPages, chapter = null, extraMeta = {}) {
      if (!volumeId) return;

      const total = Math.max(1, totalPages || 1);
      const page = Math.min(total, Math.max(1, currentPage));
      const percentage = Math.min(100, Math.round((page / total) * 100));
      const completed = page >= total;

      const existing = this.records[volumeId] || { bookmarks: [] };

      // Determine item type ('chapter' vs 'volume')
      let itemType = extraMeta.type || existing.type;
      if (!itemType) {
        if (volumeId.includes('chapter') || (extraMeta.title && /chapter/i.test(extraMeta.title))) {
          itemType = 'chapter';
        } else {
          itemType = 'volume';
        }
      }

      this.records[volumeId] = {
        volumeId,
        lastPage: page,
        totalPages: total,
        lastChapter: chapter,
        percentage,
        completed,
        updatedAt: Date.now(),
        bookmarks: existing.bookmarks || [],
        title: extraMeta.title || existing.title || null,
        type: itemType,
        coverUrl: extraMeta.coverUrl || existing.coverUrl || null,
        fileName: extraMeta.fileName || existing.fileName || null,
      };

      this._persist();
    },

    /**
     * Toggles bookmark state for a specific page within a volume.
     */
    toggleBookmark(volumeId, pageNumber) {
      if (!volumeId) return;
      if (!this.records[volumeId]) {
        this.records[volumeId] = {
          volumeId,
          lastPage: pageNumber,
          totalPages: 100,
          percentage: 1,
          updatedAt: Date.now(),
          bookmarks: [],
        };
      }

      const bookmarks = this.records[volumeId].bookmarks || [];
      const idx = bookmarks.indexOf(pageNumber);
      if (idx > -1) {
        bookmarks.splice(idx, 1);
      } else {
        bookmarks.push(pageNumber);
        bookmarks.sort((a, b) => a - b);
      }
      this.records[volumeId].bookmarks = bookmarks;
      this._persist();
    },

    /**
     * Checks if a page is currently bookmarked.
     */
    isBookmarked(volumeId, pageNumber) {
      const rec = this.records[volumeId];
      return rec?.bookmarks?.includes(pageNumber) || false;
    },

    /**
     * Sets user reading mode preference ('flipbook' or 'webtoon').
     */
    setReadMode(mode) {
      if (mode === 'flipbook' || mode === 'webtoon') {
        this.readMode = mode;
        localStorage.setItem(PREF_KEY, mode);
      }
    },

    /**
     * Sets reading direction preference ('rtl' or 'ltr').
     */
    setReadingDirection(dir) {
      this.readingDirection = dir === 'ltr' ? 'ltr' : 'rtl';
      localStorage.setItem(DIRECTION_KEY, this.readingDirection);
    },

    /**
     * Sets spread mode preference ('dual' or 'single').
     */
    setSpreadMode(mode) {
      this.spreadMode = mode === 'single' ? 'single' : 'dual';
      localStorage.setItem(SPREAD_KEY, this.spreadMode);
    },

    toggleSpreadMode() {
      this.setSpreadMode(this.spreadMode === 'dual' ? 'single' : 'dual');
    },

    /**
     * Toggles virtual 90° landscape rotation for mobile phone reading.
     */
    toggleVirtualRotation() {
      this.isRotatedLandscape = !this.isRotatedLandscape;
      localStorage.setItem(ROTATION_KEY, this.isRotatedLandscape ? 'true' : 'false');
    },

    /**
     * Removes an individual record from reading progress.
     */
    deleteRecord(volumeId) {
      if (this.records[volumeId]) {
        delete this.records[volumeId];
        this._persist();
      }
    },

    /**
     * Clears all reading progress from memory and localStorage.
     */
    clearAllHistory() {
      this.records = {};
      localStorage.removeItem(STORAGE_KEY);
    },

    _persist() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.records));
      } catch (err) {
        console.error('Failed to persist reading progress:', err);
      }
    },
  },
});
