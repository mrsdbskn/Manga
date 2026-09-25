/**
 * stores/progress.js - Persistent reading progress store backed by localStorage.
 * Automatically saves last-read page, chapter, completion percentage, bookmarks,
 * and user reading mode preference across sessions.
 */

import { defineStore } from 'pinia';

const STORAGE_KEY = 'manga_showcase_reading_progress';
const PREF_KEY = 'manga_showcase_reader_pref';

export const useProgressStore = defineStore('progress', {
  state: () => ({
    // Records keyed by volumeId (e.g. 'one-piece-v01')
    records: JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'),
    // Preferred reading engine: 'flipbook' (3D StPageFlip RTL) | 'webtoon' (Vertical scroll)
    readMode: localStorage.getItem(PREF_KEY) || 'flipbook',
  }),

  getters: {
    /**
     * Returns a sorted list of recently read volume IDs, ordered by most recently updated.
     */
    recentHistory: (state) => {
      return Object.values(state.records).sort((a, b) => b.updatedAt - a.updatedAt);
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
    saveProgress(volumeId, currentPage, totalPages, chapter = null) {
      if (!volumeId) return;

      const total = Math.max(1, totalPages || 1);
      const page = Math.min(total, Math.max(1, currentPage));
      const percentage = Math.min(100, Math.round((page / total) * 100));
      const completed = page >= total;

      const existing = this.records[volumeId] || { bookmarks: [] };

      this.records[volumeId] = {
        volumeId,
        lastPage: page,
        totalPages: total,
        lastChapter: chapter,
        percentage,
        completed,
        updatedAt: Date.now(),
        bookmarks: existing.bookmarks || [],
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
