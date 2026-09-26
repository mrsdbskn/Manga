<template>
  <div 
    class="relative w-full h-full flex items-center justify-center overflow-hidden select-none bg-black"
    @click="onBackgroundClick"
  >
    <!-- StPageFlip Book Container -->
    <div class="st-page-flip-container relative flex items-center justify-center w-full h-full max-w-6xl max-h-[96vh] p-0 sm:p-2">
      <div 
        ref="bookContainerRef" 
        class="shadow-2xl rounded-none"
        id="manga-stpageflip-book"
      >
        <!-- Individual Manga Pages -->
        <div 
          v-for="page in displayPages" 
          :key="page.pageNumber + '-' + (page.spreadPart || 'single')"
          class="page bg-white overflow-hidden flex items-center relative border-none"
          :class="[
            page.spreadPart === 'left' ? 'justify-end' : page.spreadPart === 'right' ? 'justify-start' : 'justify-center'
          ]"
          :data-density="page.pageNumber === 1 || page.pageNumber === displayPages.length ? 'hard' : 'soft'"
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

/**
 * Transforms the linear pages array for Authentic Japanese Manga Right-to-Left (RTL) reading.
 * On facing spreads:
 * - The RIGHT page is read FIRST (earlier page, e.g. Page 1, Page 3, Page 5).
 * - The LEFT page is read SECOND (later page, e.g. Page 2, Page 4, Page 6).
 * - Double-page spreads keep the Left half on the LEFT and Right half on the RIGHT,
 *   so the reader sweeps from Right (Title/intro) to Left (Climax/reveal).
 */
function transformPagesForRtl(rawPages) {
  if (!rawPages || rawPages.length <= 1) return rawPages || [];

  // Page 0 is Front Cover (Spread 0)
  const result = [rawPages[0]];

  // Process remaining pages in pairs of 2 (facing pages on desktop spread)
  let i = 1;
  while (i < rawPages.length) {
    const pFirst = rawPages[i];
    const pSecond = i + 1 < rawPages.length ? rawPages[i + 1] : null;

    // Check if this pair is a double-page spread
    const isSpreadPair = pFirst?.isSpread || pSecond?.isSpread;

    if (isSpreadPair) {
      // In a double-page spread:
      // The Left half of the illustration (Young Luffy) must be on the LEFT page
      // The Right half of the illustration (Romance Dawn) must be on the RIGHT page
      // Visually: Left half on left screen, Right half on right screen!
      // Reading flow: Japanese reader reads the Right page first (title/intro), then Left page second (hero/climax)!
      result.push(pFirst);
      if (pSecond) {
        result.push(pSecond);
      }
    } else {
      // For normal pages in RTL Manga mode:
      // StPageFlip places the first element of a spread on the LEFT and the second on the RIGHT.
      // In authentic Japanese manga, you read the RIGHT page first (Page N) and the LEFT page second (Page N+1).
      // Therefore, the earlier page (pFirst) is placed on the RIGHT, and the later page (pSecond) is placed on the LEFT!
      if (pSecond) {
        result.push(pSecond); // placed on LEFT screen
        result.push(pFirst);  // placed on RIGHT screen
      } else {
        result.push(pFirst);
      }
    }
    i += 2;
  }

  return result;
}

const displayPages = computed(() => {
  if (props.readingDirection === 'ltr') {
    return props.pages;
  }
  return transformPagesForRtl(props.pages);
});

function initPageFlip() {
  if (!bookContainerRef.value || !displayPages.value || displayPages.value.length === 0) return;

  // Cleanup old instance if re-initializing
  if (pageFlipInstance) {
    try {
      pageFlipInstance.destroy();
    } catch (e) {}
    pageFlipInstance = null;
  }

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

  // Calculate start index in displayPages based on initialPage
  let startIdx = 0;
  if (props.initialPage > 1) {
    const foundIdx = displayPages.value.findIndex(p => p.pageNumber === props.initialPage);
    startIdx = foundIdx !== -1 ? foundIdx : Math.max(0, props.initialPage - 1);
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

    const pageElements = bookContainerRef.value.querySelectorAll('.page');
    pageFlipInstance.loadFromHTML(pageElements);

    // Event listener for page flips
    pageFlipInstance.on('flip', (e) => {
      // In StPageFlip, e.data is current index (0-indexed)
      const currentZeroIdx = e.data;
      const curPageObj = displayPages.value[currentZeroIdx];
      const pageNum = curPageObj ? curPageObj.pageNumber : currentZeroIdx + 1;
      emit('page-change', pageNum);
      playPageFlipSound();
    });

    // Initial sync
    emit('page-change', Math.max(1, props.initialPage));
  } catch (err) {
    console.error('Error initializing StPageFlip:', err);
  }
}

function turnNext() {
  if (pageFlipInstance) {
    pageFlipInstance.flipNext();
  }
}

function turnPrev() {
  if (pageFlipInstance) {
    pageFlipInstance.flipPrev();
  }
}

function jumpToPage(pageNum) {
  if (pageFlipInstance && displayPages.value) {
    const idx = displayPages.value.findIndex(p => p.pageNumber === pageNum);
    const targetIdx = idx !== -1 ? idx : Math.max(0, Math.min(displayPages.value.length - 1, pageNum - 1));
    pageFlipInstance.flip(targetIdx);
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
  nextTick(() => {
    initPageFlip();
  });
});

watch(() => props.pages, () => {
  nextTick(() => {
    initPageFlip();
  });
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
  if (pageFlipInstance) {
    try {
      pageFlipInstance.destroy();
    } catch (e) {}
    pageFlipInstance = null;
  }
});
</script>
