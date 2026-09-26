<template>
  <div 
    class="relative w-full h-full flex items-center justify-center overflow-hidden select-none bg-black"
    @click="onBackgroundClick"
  >
    <!-- StPageFlip Book Container -->
    <div class="st-page-flip-container relative flex items-center justify-center w-full h-full max-w-6xl max-h-[96vh] p-0 sm:p-2">
      <div 
        :key="`manga-book-${readingDirection}-${renderKey}`"
        ref="bookContainerRef" 
        class="shadow-2xl rounded-none"
        id="manga-stpageflip-book"
      >
        <!-- Individual Manga Pages -->
        <div 
          v-for="(page, pageIdx) in displayPages" 
          :key="page.pageNumber + '-' + (page.spreadPart || 'single')"
          class="page bg-white overflow-hidden flex items-center relative border-none"
          :class="[
            page.spreadPart === 'left' ? 'justify-end' : page.spreadPart === 'right' ? 'justify-start' : 'justify-center'
          ]"
          :data-density="pageIdx === 0 || pageIdx === displayPages.length - 1 ? 'hard' : 'soft'"
        >
          <!-- Regular Image Page -->
          <img 
            v-if="!page.isBlank"
            :src="page.url" 
            :alt="`Page ${page.pageNumber}`"
            :class="[
              'w-full h-full pointer-events-none select-none bg-white',
              page.spreadPart === 'left' ? 'object-cover object-right' : page.spreadPart === 'right' ? 'object-cover object-left' : 'object-contain'
            ]"
            loading="eager"
          />
          <!-- Blank Endpaper (Used for Spread Parity Alignment) -->
          <div v-else class="w-full h-full bg-[#fdfbf7] flex items-center justify-center pointer-events-none select-none">
            <span class="text-[11px] font-serif italic text-slate-300 select-none"></span>
          </div>
          <!-- Page Number Indicator at Bottom -->
          <div v-if="!page.isBlank" class="absolute bottom-2 right-3 text-[10px] font-mono text-slate-400 bg-black/75 px-1.5 py-0.5 rounded backdrop-blur-sm pointer-events-none border border-white/5 flex items-center gap-1">
            <span v-if="page.isSpread" class="text-amber-400 font-bold text-[8px] tracking-wider">SPREAD</span>
            <span>{{ page.pageNumber }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Floating Navigation Arrows (RTL aware: Left advances forward, Right goes back) -->
    <button 
      type="button"
      @click.stop="readingDirection === 'rtl' ? turnNext() : turnPrev()"
      class="absolute left-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-black/60 backdrop-blur-md text-white/80 hover:text-white hover:bg-black/90 border border-white/10 shadow-elevation-2 transition-all md-state-layer z-20 group"
      :title="readingDirection === 'rtl' ? 'Next Page (Manga RTL / Arrow Left)' : 'Previous Page (Arrow Left)'"
    >
      <svg class="w-6 h-6 transform group-hover:-translate-x-0.5 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>

    <button 
      type="button"
      @click.stop="readingDirection === 'rtl' ? turnPrev() : turnNext()"
      class="absolute right-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-black/60 backdrop-blur-md text-white/80 hover:text-white hover:bg-black/90 border border-white/10 shadow-elevation-2 transition-all md-state-layer z-20 group"
      :title="readingDirection === 'rtl' ? 'Previous Page (Manga RTL / Arrow Right)' : 'Next Page (Arrow Right)'"
    >
      <svg class="w-6 h-6 transform group-hover:translate-x-0.5 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="m9 18 6-6-6-6" />
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { PageFlip } from 'page-flip';
import { playPageFlipSound } from '../../utils/audioEngine.js';

const props = defineProps({
  pages: {
    type: Array,
    required: true,
  },
  initialPage: {
    type: Number,
    default: 1,
  },
  readingDirection: {
    type: String,
    default: 'rtl',
  },
});

const emit = defineEmits(['page-change', 'toggle-hud']);

const bookContainerRef = ref(null);
let pageFlipInstance = null;
const renderKey = ref(0);
const activePageNumber = ref(props.initialPage || 1);

/**
 * Transforms the linear pages array for Authentic Japanese Manga Right-to-Left (RTL) reading.
 * In authentic Japanese manga:
 * - The front cover is on the LEFT side of the closed book and opens to the RIGHT.
 * - All forward page turns flip to the RIGHT (not left).
 * - On facing spreads:
 *   - The RIGHT page is read FIRST (earlier page, e.g. Page 1, Page 3, Page 5).
 *   - The LEFT page is read SECOND (later page, e.g. Page 2, Page 4, Page 6).
 *   - Double-page spreads keep the Left half on the LEFT and Right half on the RIGHT,
 *     so the reader sweeps from Right (Title/intro) to Left (Climax/reveal).
 * By ordering spreads in reversed sequence with StPageFlip, the front cover starts on the LEFT
 * and every forward turn physically flips to the RIGHT.
 */
function transformPagesForRtl(rawPages) {
  if (!rawPages || rawPages.length <= 1) return rawPages || [];

  const spreads = [];
  // Spread 0: Front Cover
  spreads.push([rawPages[0]]);

  let i = 1;
  while (i < rawPages.length) {
    const pFirst = rawPages[i];
    const pSecond = i + 1 < rawPages.length ? rawPages[i + 1] : null;

    if (pFirst && pSecond) {
      const isSpread = pFirst.isSpread || pSecond.isSpread;
      if (isSpread) {
        // Double-page spread: Left half on Left screen, Right half on Right screen
        spreads.push([pFirst, pSecond]);
      } else {
        // Normal manga pages:
        // pFirst (Page N) is read 1st -> on RIGHT screen!
        // pSecond (Page N+1) is read 2nd -> on LEFT screen!
        // Spread format: [LeftScreen, RightScreen]
        spreads.push([pSecond, pFirst]);
      }
    } else {
      // Single trailing page at end of volume
      spreads.push([pFirst]);
    }
    i += 2;
  }

  // Ensure total elements across spreads is even for single front and back cover
  const totalCount = spreads.reduce((acc, sp) => acc + sp.length, 0);
  if (totalCount % 2 !== 0) {
    spreads.push([{
      pageNumber: rawPages.length + 1,
      url: '',
      isBlank: true,
      name: 'Back Endpaper',
    }]);
  }

  // Reverse spreads so StPageFlip starts at the Front Cover on the LEFT and turns all pages to the RIGHT
  const reversedSpreads = [...spreads].reverse();
  return reversedSpreads.flat();
}

const displayPages = computed(() => {
  if (props.readingDirection === 'ltr') {
    return props.pages;
  }
  return transformPagesForRtl(props.pages);
});

function cleanupPageFlip() {
  if (pageFlipInstance) {
    try {
      if (typeof pageFlipInstance.getUI === 'function' && pageFlipInstance.getUI()) {
        pageFlipInstance.getUI().destroy();
      } else if (typeof pageFlipInstance.clear === 'function') {
        pageFlipInstance.clear();
      }
    } catch (e) {
      console.warn('PageFlip cleanup notice:', e);
    }
    pageFlipInstance = null;
  }
}

function initPageFlip(targetPageNum = null) {
  if (!bookContainerRef.value || !displayPages.value || displayPages.value.length === 0) return;

  cleanupPageFlip();

  // Calculate responsive dimensions based on true digital manga page aspect ratio (1 : 1.501)
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const isMobile = vw < 768;
  const mangaAspect = 1 / 1.501;

  let pageH = Math.min(960, Math.floor(vh * 0.94));
  let pageW = Math.floor(pageH * mangaAspect);

  if (isMobile) {
    pageW = Math.min(Math.floor(vw * 0.98), 580);
    pageH = Math.floor(pageW / mangaAspect);
    if (pageH > vh * 0.92) {
      pageH = Math.floor(vh * 0.92);
      pageW = Math.floor(pageH * mangaAspect);
    }
  } else {
    // On desktop in dual-spread mode (2 pages side-by-side)
    if (pageW * 2 > vw * 0.96) {
      pageW = Math.floor((vw * 0.96) / 2);
      pageH = Math.floor(pageW / mangaAspect);
    }
  }

  // Calculate start index in displayPages based on targetPageNum or initialPage
  const pageToOpen = targetPageNum !== null ? targetPageNum : (activePageNumber.value || props.initialPage || 1);
  let startIdx = 0;
  if (props.readingDirection === 'rtl') {
    if (pageToOpen > 1) {
      const foundIdx = displayPages.value.findIndex(p => p.pageNumber === pageToOpen);
      startIdx = foundIdx !== -1 ? foundIdx : Math.max(0, displayPages.value.length - 1);
    } else {
      // In RTL, Front Cover is at the last index of displayPages (Spread Last on the LEFT)
      startIdx = Math.max(0, displayPages.value.length - 1);
    }
  } else {
    if (pageToOpen > 1) {
      const foundIdx = displayPages.value.findIndex(p => p.pageNumber === pageToOpen);
      startIdx = foundIdx !== -1 ? foundIdx : Math.max(0, pageToOpen - 1);
    } else {
      startIdx = 0;
    }
  }

  const pageElements = bookContainerRef.value.querySelectorAll('.page');
  if (pageElements.length === 0) {
    console.warn('No page elements found in container, deferring StPageFlip init');
    return;
  }

  try {
    pageFlipInstance = new PageFlip(bookContainerRef.value, {
      width: pageW,
      height: pageH,
      size: 'stretch',
      minWidth: 280,
      maxWidth: 900,
      minHeight: 420,
      maxHeight: 1200,
      maxShadowOpacity: 0.35, // Natural, subtle paper curl shadow (avoids heavy dark overlay)
      showCover: true,
      mobileScrollSupport: false,
      usePortrait: isMobile,
      startPage: startIdx,
      flippingTime: 450,
    });

    pageFlipInstance.loadFromHTML(pageElements);

    // Event listener for page flips
    pageFlipInstance.on('flip', (e) => {
      // In StPageFlip, e.data is current spread[0] index (0-indexed)
      const currentZeroIdx = e.data;
      let pageNum = 1;
      if (props.readingDirection === 'rtl') {
        const p1 = displayPages.value[currentZeroIdx];
        const p2 = displayPages.value[currentZeroIdx + 1];
        const validPages = [p1, p2].filter(p => p && !p.isBlank && p.pageNumber);
        pageNum = validPages.length > 0 ? Math.min(...validPages.map(p => p.pageNumber)) : 1;
      } else {
        const curPageObj = displayPages.value[currentZeroIdx];
        pageNum = curPageObj ? curPageObj.pageNumber : currentZeroIdx + 1;
      }
      activePageNumber.value = pageNum;
      emit('page-change', pageNum);
      playPageFlipSound();
    });

    // Initial sync
    activePageNumber.value = pageToOpen;
    emit('page-change', Math.max(1, pageToOpen));
  } catch (err) {
    console.error('Error initializing StPageFlip:', err);
  }
}

function turnNext() {
  if (pageFlipInstance) {
    if (props.readingDirection === 'rtl') {
      // In RTL manga, reading forward turns pages to the RIGHT (StPageFlip flipPrev)
      pageFlipInstance.flipPrev();
    } else {
      pageFlipInstance.flipNext();
    }
  }
}

function turnPrev() {
  if (pageFlipInstance) {
    if (props.readingDirection === 'rtl') {
      // In RTL manga, going back turns pages to the LEFT (StPageFlip flipNext)
      pageFlipInstance.flipNext();
    } else {
      pageFlipInstance.flipPrev();
    }
  }
}

function jumpToPage(pageNum) {
  if (pageFlipInstance && displayPages.value && displayPages.value.length > 0) {
    if (props.readingDirection === 'rtl') {
      const idx = displayPages.value.findIndex(p => p.pageNumber === pageNum);
      const targetIdx = idx !== -1 ? idx : Math.max(0, displayPages.value.length - 1);
      pageFlipInstance.flip(targetIdx);
    } else {
      const idx = displayPages.value.findIndex(p => p.pageNumber === pageNum);
      const targetIdx = idx !== -1 ? idx : Math.max(0, Math.min(displayPages.value.length - 1, pageNum - 1));
      pageFlipInstance.flip(targetIdx);
    }
  }
}

defineExpose({
  jumpToPage,
  turnNext,
  turnPrev,
});

function onBackgroundClick(e) {
  // If clicked directly on background, toggle controls HUD
  if (e.target === e.currentTarget) {
    emit('toggle-hud');
  }
}

function onKeydown(e) {
  const isRtl = props.readingDirection === 'rtl';
  if (e.key === 'ArrowLeft') {
    // In Manga RTL, ArrowLeft advances forward; in LTR, ArrowLeft goes back
    isRtl ? turnNext() : turnPrev();
  } else if (e.key === 'ArrowRight') {
    // In Manga RTL, ArrowRight goes back; in LTR, ArrowRight advances forward
    isRtl ? turnPrev() : turnNext();
  }
}

watch(() => props.readingDirection, () => {
  cleanupPageFlip();
  renderKey.value++;
  nextTick(() => {
    initPageFlip(activePageNumber.value);
  });
});

watch(() => props.pages, () => {
  cleanupPageFlip();
  activePageNumber.value = props.initialPage || 1;
  renderKey.value++;
  nextTick(() => {
    initPageFlip(props.initialPage || 1);
  });
});

watch(() => props.initialPage, (newPage) => {
  if (newPage && newPage !== activePageNumber.value) {
    activePageNumber.value = newPage;
    jumpToPage(newPage);
  }
});

onMounted(() => {
  nextTick(() => {
    initPageFlip();
  });
  window.addEventListener('keydown', onKeydown);
  window.addEventListener('resize', onResize);
});

let resizeTimer = null;
function onResize() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    initPageFlip();
  });
}

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown);
  window.removeEventListener('resize', onResize);
  cleanupPageFlip();
});
</script>
