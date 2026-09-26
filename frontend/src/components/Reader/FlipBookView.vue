<template>
  <div 
    class="relative w-full h-full flex items-center justify-center overflow-hidden select-none bg-black transition-all duration-300"
    :class="[isRotated ? 'manga-virtual-landscape' : '']"
    @click="onBackgroundClick"
    @dblclick="toggleZoom"
  >
    <!-- StPageFlip Book Container -->
    <div class="st-page-flip-container relative flex items-center justify-center w-full h-full max-w-7xl max-h-[96vh] p-0 sm:p-2">
      <div 
        :key="`manga-book-${readingDirection}-${spreadMode}-${isRotated ? 'rot' : 'norm'}-${renderKey}`"
        ref="bookContainerRef" 
        class="shadow-2xl rounded-none will-change-transform"
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
      class="absolute left-3 sm:left-4 top-1/2 -translate-y-1/2 p-2.5 sm:p-3 rounded-full bg-black/60 backdrop-blur-md text-white/80 hover:text-white hover:bg-black/90 border border-white/10 shadow-elevation-2 transition-all md-state-layer z-20 group"
      :title="readingDirection === 'rtl' ? 'Next Page (Manga RTL / Arrow Left)' : 'Previous Page (Arrow Left)'"
    >
      <svg class="w-5 h-5 sm:w-6 sm:h-6 transform group-hover:-translate-x-0.5 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>

    <button 
      type="button"
      @click.stop="readingDirection === 'rtl' ? turnPrev() : turnNext()"
      class="absolute right-3 sm:right-4 top-1/2 -translate-y-1/2 p-2.5 sm:p-3 rounded-full bg-black/60 backdrop-blur-md text-white/80 hover:text-white hover:bg-black/90 border border-white/10 shadow-elevation-2 transition-all md-state-layer z-20 group"
      :title="readingDirection === 'rtl' ? 'Previous Page (Manga RTL / Arrow Right)' : 'Next Page (Arrow Right)'"
    >
      <svg class="w-5 h-5 sm:w-6 sm:h-6 transform group-hover:translate-x-0.5 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="m9 18 6-6-6-6" />
      </svg>
    </button>

    <!-- Floating Quick Zoom Trigger Button -->
    <button
      type="button"
      @click.stop="toggleZoom"
      class="absolute bottom-4 right-4 p-2.5 rounded-full bg-black/70 backdrop-blur-md text-slate-300 hover:text-white border border-white/10 shadow-lg transition-all z-20 hidden sm:flex items-center gap-1.5 text-xs"
      title="Zoom / Magnifier (Double-tap pages or press Z)"
    >
      <svg class="w-4 h-4 text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="11" y1="8" x2="11" y2="14" />
        <line x1="8" y1="11" x2="14" y2="11" />
      </svg>
      <span>Zoom</span>
    </button>

    <!-- ========================================================================= -->
    <!-- HIGH-DEFINITION ZOOM & PAN INSPECTOR MODAL                               -->
    <!-- ========================================================================= -->
    <div 
      v-if="isZoomed"
      class="fixed inset-0 z-50 bg-black/95 backdrop-blur-xl flex flex-col items-center justify-center select-none overflow-hidden"
      @click="closeZoom"
    >
      <!-- Top Floating Zoom Pill Bar -->
      <div 
        class="absolute top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 sm:gap-3 bg-slate-900/90 border border-sky-500/30 px-4 py-2 rounded-full backdrop-blur-xl shadow-2xl text-xs text-white" 
        @click.stop
      >
        <span class="font-bold text-sky-300 flex items-center gap-1">
          <span>🔍</span>
          <span>{{ Math.round(zoomScale * 100) }}%</span>
        </span>
        <div class="flex items-center gap-1 border-l border-white/20 pl-2">
          <button 
            type="button" 
            @click="zoomIn" 
            class="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 text-white font-bold flex items-center justify-center transition-colors"
            title="Zoom In"
          >
            +
          </button>
          <button 
            type="button" 
            @click="zoomOut" 
            class="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 text-white font-bold flex items-center justify-center transition-colors"
            title="Zoom Out"
          >
            −
          </button>
          <button 
            type="button" 
            @click="resetZoom" 
            class="px-2.5 py-1 rounded-full bg-white/10 hover:bg-white/20 text-[11px] transition-colors"
          >
            Reset
          </button>
        </div>
        <button 
          type="button" 
          @click="closeZoom" 
          class="border-l border-white/20 pl-2.5 text-slate-400 hover:text-white font-semibold transition-colors flex items-center gap-1"
        >
          <span>✕</span>
          <span class="hidden sm:inline">Close</span>
        </button>
      </div>

      <!-- Zoom Canvas (Supports Pointer Pan & Wheel Zoom) -->
      <div 
        class="w-full h-full flex items-center justify-center overflow-hidden cursor-grab active:cursor-grabbing p-4 touch-none"
        @pointerdown="onZoomPointerDown"
        @pointermove="onZoomPointerMove"
        @pointerup="onZoomPointerUp"
        @pointercancel="onZoomPointerUp"
        @wheel.prevent="onZoomWheel"
        @click.stop
      >
        <div 
          class="flex items-center justify-center gap-2 will-change-transform transition-transform duration-75 max-w-[96vw] max-h-[92vh]"
          :style="{
            transform: `translate(${zoomPanX}px, ${zoomPanY}px) scale(${zoomScale})`,
            transformOrigin: 'center center'
          }"
        >
          <img 
            v-for="p in currentZoomPages" 
            :key="p.pageNumber + '-' + (p.spreadPart || '')"
            :src="p.url"
            class="max-h-[88vh] object-contain shadow-2xl rounded pointer-events-none select-none border border-white/10"
            :alt="`Page ${p.pageNumber}`"
          />
        </div>
      </div>
    </div>
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
  spreadMode: {
    type: String,
    default: 'dual', // 'dual' (both pages visible side-by-side) | 'single'
  },
  isRotated: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['page-change', 'toggle-hud']);

const bookContainerRef = ref(null);
let pageFlipInstance = null;
const renderKey = ref(0);
const activePageNumber = ref(props.initialPage || 1);

// =========================================================================
// ZOOM & MAGNIFIER STATE
// =========================================================================
const isZoomed = ref(false);
const zoomScale = ref(2.0);
const zoomPanX = ref(0);
const zoomPanY = ref(0);
let isZoomPanning = false;
let zoomStartPoint = { x: 0, y: 0 };
let initialPan = { x: 0, y: 0 };

const currentZoomPages = computed(() => {
  if (!props.pages || props.pages.length === 0) return [];
  const curPage = activePageNumber.value || 1;
  // If spreadMode is single or page is 1 (front cover), show single
  if (props.spreadMode === 'single' || curPage === 1) {
    const p = props.pages.find(x => x.pageNumber === curPage) || props.pages[0];
    return p && !p.isBlank ? [p] : [];
  }
  // Otherwise find facing pair
  const p1 = props.pages.find(x => x.pageNumber === curPage);
  const p2 = props.pages.find(x => x.pageNumber === (curPage % 2 === 0 ? curPage + 1 : curPage - 1));
  const pair = [p1, p2].filter(p => p && !p.isBlank);
  if (props.readingDirection === 'rtl') {
    // In RTL, earlier page on right, later on left
    return pair.sort((a, b) => b.pageNumber - a.pageNumber);
  }
  return pair.sort((a, b) => a.pageNumber - b.pageNumber);
});

function toggleZoom() {
  if (isZoomed.value) {
    closeZoom();
  } else {
    openZoom();
  }
}

function openZoom() {
  isZoomed.value = true;
  zoomScale.value = 2.0;
  zoomPanX.value = 0;
  zoomPanY.value = 0;
}

function closeZoom() {
  isZoomed.value = false;
}

function zoomIn() {
  zoomScale.value = Math.min(4.0, zoomScale.value + 0.5);
}

function zoomOut() {
  zoomScale.value = Math.max(1.0, zoomScale.value - 0.5);
}

function resetZoom() {
  zoomScale.value = 2.0;
  zoomPanX.value = 0;
  zoomPanY.value = 0;
}

function onZoomWheel(e) {
  const delta = e.deltaY < 0 ? 0.2 : -0.2;
  zoomScale.value = Math.max(1.0, Math.min(4.0, zoomScale.value + delta));
}

function onZoomPointerDown(e) {
  isZoomPanning = true;
  zoomStartPoint = { x: e.clientX, y: e.clientY };
  initialPan = { x: zoomPanX.value, y: zoomPanY.value };
  if (e.target && e.target.setPointerCapture) {
    e.target.setPointerCapture(e.pointerId);
  }
}

function onZoomPointerMove(e) {
  if (!isZoomPanning) return;
  const dx = e.clientX - zoomStartPoint.x;
  const dy = e.clientY - zoomStartPoint.y;
  zoomPanX.value = initialPan.x + dx;
  zoomPanY.value = initialPan.y + dy;
}

function onZoomPointerUp() {
  isZoomPanning = false;
}

// =========================================================================
// RTL PAGE TRANSFORM
// =========================================================================
/**
 * Transforms linear pages for Authentic Japanese Manga Right-to-Left (RTL) reading.
 * - Front cover starts on the LEFT of the closed book and opens to the RIGHT.
 * - All forward page turns flip to the RIGHT.
 * - Facing spreads show the earlier page on the RIGHT (1st) and later on the LEFT (2nd).
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
        // pFirst (Page N) read 1st -> on RIGHT screen!
        // pSecond (Page N+1) read 2nd -> on LEFT screen!
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

  // Reverse spreads so StPageFlip starts at Front Cover on LEFT and turns all pages to RIGHT
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

// =========================================================================
// INIT STPAGEFLIP WITH DUAL-SPREAD MOBILE FIT
// =========================================================================
function initPageFlip(targetPageNum = null) {
  if (!bookContainerRef.value || !displayPages.value || displayPages.value.length === 0) return;

  cleanupPageFlip();

  // If virtual 90deg rotation is active, viewport dimensions invert
  const isRotated = props.isRotated;
  const rawVw = window.innerWidth;
  const rawVh = window.innerHeight;
  const effectiveVw = isRotated ? rawVh : rawVw;
  const effectiveVh = isRotated ? rawVw : rawVh;
  const mangaAspect = 1 / 1.501;

  const isDual = props.spreadMode !== 'single';
  const availW = Math.floor(effectiveVw * (effectiveVw < 768 ? 0.98 : 0.96));
  const availH = Math.floor(effectiveVh * 0.94);

  let pageW, pageH;

  if (isDual) {
    // Dual spread mode: BOTH pages visible side-by-side (total book width = pageW * 2)
    // Book aspect ratio = (2 * mangaAspect) = 2 / 1.501 ≈ 1.332
    if ((availW / 2) / mangaAspect <= availH) {
      // Width is the constraining dimension (e.g. mobile phone held vertical)
      pageW = Math.floor(availW / 2);
      pageH = Math.floor(pageW / mangaAspect);
    } else {
      // Height is the constraining dimension (e.g. desktop or phone held landscape)
      pageH = Math.min(availH, 960);
      pageW = Math.floor(pageH * mangaAspect);
      if (pageW * 2 > availW) {
        pageW = Math.floor(availW / 2);
        pageH = Math.floor(pageW / mangaAspect);
      }
    }
  } else {
    // Single page mode
    pageH = Math.min(availH, 960);
    pageW = Math.floor(pageH * mangaAspect);
    if (pageW > availW) {
      pageW = availW;
      pageH = Math.floor(pageW / mangaAspect);
    }
  }

  // Safety boundaries
  pageW = Math.max(140, pageW);
  pageH = Math.max(210, pageH);

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
      minWidth: 140,
      maxWidth: 960,
      minHeight: 210,
      maxHeight: 1200,
      maxShadowOpacity: 0.35,
      showCover: true,
      mobileScrollSupport: false,
      usePortrait: !isDual, // When false, StPageFlip ALWAYS displays both pages side-by-side!
      startPage: startIdx,
      flippingTime: 450,
    });

    pageFlipInstance.loadFromHTML(pageElements);

    // Event listener for page flips
    pageFlipInstance.on('flip', (e) => {
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
      pageFlipInstance.flipPrev();
    } else {
      pageFlipInstance.flipNext();
    }
  }
}

function turnPrev() {
  if (pageFlipInstance) {
    if (props.readingDirection === 'rtl') {
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
  openZoom,
  closeZoom,
  toggleZoom,
  isZoomed,
});

function onBackgroundClick(e) {
  if (e.target === e.currentTarget) {
    emit('toggle-hud');
  }
}

function onKeydown(e) {
  if (isZoomed.value) {
    if (e.key === 'Escape') closeZoom();
    if (e.key === '+' || e.key === '=') zoomIn();
    if (e.key === '-') zoomOut();
    return;
  }
  const isRtl = props.readingDirection === 'rtl';
  if (e.key === 'ArrowLeft') {
    isRtl ? turnNext() : turnPrev();
  } else if (e.key === 'ArrowRight') {
    isRtl ? turnPrev() : turnNext();
  } else if (e.key.toLowerCase() === 'z') {
    toggleZoom();
  }
}

watch([() => props.readingDirection, () => props.spreadMode, () => props.isRotated], () => {
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
  }, 100);
}

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown);
  window.removeEventListener('resize', onResize);
  cleanupPageFlip();
});
</script>

<style scoped>
/* Virtual 90-degree landscape rotation for mobile phone reading */
.manga-virtual-landscape {
  position: fixed !important;
  width: 100vh !important;
  height: 100vw !important;
  top: 50% !important;
  left: 50% !important;
  transform: translate(-50%, -50%) rotate(90deg) !important;
  transform-origin: center center !important;
  z-index: 45;
}
</style>
