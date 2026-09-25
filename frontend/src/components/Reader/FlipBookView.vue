<template>
  <div 
    class="relative w-full h-full flex items-center justify-center overflow-hidden select-none bg-[#0a0c12]"
    @click="onBackgroundClick"
  >
    <!-- StPageFlip Book Container -->
    <div class="st-page-flip-container relative flex items-center justify-center w-full h-full max-w-5xl max-h-[90vh] p-4">
      <div 
        ref="bookContainerRef" 
        class="shadow-2xl rounded-sm"
        id="manga-stpageflip-book"
      >
        <!-- Individual Manga Pages -->
        <div 
          v-for="page in pages" 
          :key="page.pageNumber"
          class="page bg-[#12131a] overflow-hidden flex items-center justify-center relative border border-white/5"
          :data-density="page.pageNumber === 1 || page.pageNumber === pages.length ? 'hard' : 'soft'"
        >
          <img 
            :src="page.url" 
            :alt="`Page ${page.pageNumber}`"
            class="w-full h-full object-contain pointer-events-none"
            loading="eager"
          />
          <!-- Page Number Indicator at Bottom -->
          <div class="absolute bottom-2 right-3 text-[10px] font-mono text-slate-400 bg-black/60 px-1.5 py-0.5 rounded backdrop-blur-sm pointer-events-none">
            {{ page.pageNumber }}
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

  // Calculate responsive dimensions
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const isMobile = vw < 768;

  // Single page aspect ratio approx 1 : 1.45
  let pageW = Math.min(520, Math.floor(vw * 0.45));
  let pageH = Math.min(780, Math.floor(vh * 0.85));

  if (isMobile) {
    pageW = Math.floor(vw * 0.9);
    pageH = Math.min(750, Math.floor(vh * 0.8));
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
      flippingTime: 500,
      direction: 'rtl', // Authentically Japanese Manga Right-to-Left!
    });

    const pageElements = bookContainerRef.value.querySelectorAll('.page');
    pageFlipInstance.loadFromHTML(pageElements);

    // Event listener for page flips
    pageFlipInstance.on('flip', (e) => {
      // In StPageFlip, e.data is current index (0-indexed)
      const currentZeroIdx = e.data;
      emit('page-change', currentZeroIdx + 1);
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
