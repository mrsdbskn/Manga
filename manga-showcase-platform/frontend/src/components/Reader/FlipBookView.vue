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
          v-for="page in pages" 
          :key="page.pageNumber"
          class="page bg-black overflow-hidden flex items-center relative border-none"
          :class="[
            page.spreadPart === 'right' ? 'justify-end' : page.spreadPart === 'left' ? 'justify-start' : 'justify-center'
          ]"
          :data-density="page.pageNumber === 1 || page.pageNumber === pages.length ? 'hard' : 'soft'"
        >
          <img 
            :src="page.url" 
            :alt="`Page ${page.pageNumber}`"
            :class="[
              'w-full h-full pointer-events-none select-none bg-black',
              page.spreadPart === 'right' ? 'object-cover object-right' : page.spreadPart === 'left' ? 'object-cover object-left' : 'object-contain'
            ]"
            loading="eager"
          />
          <!-- Page Number Indicator at Bottom -->
          <div class="absolute bottom-2 right-3 text-[10px] font-mono text-slate-400 bg-black/75 px-1.5 py-0.5 rounded backdrop-blur-sm pointer-events-none border border-white/5 flex items-center gap-1">
            <span v-if="page.isSpread" class="text-amber-400 font-bold text-[8px] tracking-wider">SPREAD</span>
            <span>{{ page.pageNumber }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Floating Navigation Arrows (RTL aware: Left advances forward, Right goes back) -->
    <button 
      type="button"
      @click.stop="turnNext"
      class="absolute left-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-black/60 backdrop-blur-md text-white/80 hover:text-white hover:bg-black/90 border border-white/10 shadow-elevation-2 transition-all md-state-layer z-20 group"
      title="Next Page (RTL / Arrow Left)"
    >
      <svg class="w-6 h-6 transform group-hover:-translate-x-0.5 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>

    <button 
      type="button"
      @click.stop="turnPrev"
      class="absolute right-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-black/60 backdrop-blur-md text-white/80 hover:text-white hover:bg-black/90 border border-white/10 shadow-elevation-2 transition-all md-state-layer z-20 group"
      title="Previous Page (RTL / Arrow Right)"
    >
      <svg class="w-6 h-6 transform group-hover:translate-x-0.5 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="m9 18 6-6-6-6" />
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
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
});

const emit = defineEmits(['page-change', 'toggle-hud']);

const bookContainerRef = ref(null);
let pageFlipInstance = null;

function initPageFlip() {
  if (!bookContainerRef.value || !props.pages || props.pages.length === 0) return;

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

  try {
    pageFlipInstance = new PageFlip(bookContainerRef.value, {
      width: pageW,
      height: pageH,
      size: 'stretch',
      minWidth: 280,
      maxWidth: 900,
      minHeight: 420,
      maxHeight: 1200,
      maxShadowOpacity: 0.6,
      showCover: true,
      mobileScrollSupport: false,
      usePortrait: isMobile,
      startPage: Math.max(0, props.initialPage - 1),
      flippingTime: 450,
      direction: 'rtl', // Authentically Japanese Manga Right-to-Left!
    });

    const pageElements = bookContainerRef.value.querySelectorAll('.page');
    pageFlipInstance.loadFromHTML(pageElements);

    // Event listener for page flips
    pageFlipInstance.on('flip', (e) => {
      // In StPageFlip, e.data is current index (0-indexed)
      const currentZeroIdx = e.data;
      emit('page-change', currentZeroIdx + 1);
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
  if (pageFlipInstance) {
    const targetIdx = Math.max(0, Math.min(props.pages.length - 1, pageNum - 1));
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
  // In Manga RTL, ArrowLeft goes to NEXT page, ArrowRight goes to PREVIOUS page
  if (e.key === 'ArrowLeft') {
    turnNext();
  } else if (e.key === 'ArrowRight') {
    turnPrev();
  }
}

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
  }, 250);
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
