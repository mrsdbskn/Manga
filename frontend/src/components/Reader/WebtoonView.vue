<template>
  <div 
    ref="containerRef"
    class="w-full h-full overflow-y-auto overflow-x-hidden bg-black relative scroll-smooth"
    @scroll="onScrollThrottled"
    @click="onContainerClick"
  >
    <!-- Centered Webtoon Strip Container -->
    <div class="max-w-4xl mx-auto py-8 px-2 sm:px-4 flex flex-col items-center">
      <div 
        v-for="page in displayPages" 
        :key="page.pageNumber"
        :id="`webtoon-page-${page.pageNumber}`"
        :data-page="page.pageNumber"
        class="webtoon-page-wrapper w-full mb-1 sm:mb-2 relative flex justify-center group"
      >
        <img 
          :src="page.originalUrl || page.url" 
          :alt="`Page ${page.pageNumber}`"
          :class="[
            'h-auto object-contain rounded-sm shadow-elevation-2 select-none transition-all',
            page.isSpread ? 'w-full max-w-4xl' : 'w-full max-w-2xl'
          ]"
          loading="lazy"
        />

        <!-- Hover Page Tag on Side -->
        <div class="absolute top-2 right-2 sm:-right-12 opacity-0 group-hover:opacity-100 transition-opacity bg-black/70 backdrop-blur-sm text-[10px] font-mono text-slate-300 px-2 py-0.5 rounded-full border border-white/10 pointer-events-none flex items-center gap-1">
          <span v-if="page.isSpread" class="text-amber-400 font-bold">SPREAD</span>
          <span>P. {{ page.pageNumber }}</span>
        </div>
      </div>

      <!-- End of Volume Marker -->
      <div class="w-full text-center py-12 border-t border-white/10 mt-8 text-slate-400">
        <span class="text-xs uppercase tracking-widest text-sky-400 font-bold block mb-1">To Be Continued</span>
        <p class="text-[11px] text-slate-500">You have reached the end of this volume.</p>
      </div>
    </div>

    <!-- Floating Quick Page Pill & Back to Top -->
    <div class="fixed bottom-6 right-6 z-30 flex items-center gap-2 pointer-events-auto">
      <div class="px-3.5 py-1.5 rounded-full bg-black/80 backdrop-blur-md border border-white/15 shadow-elevation-3 text-xs font-mono text-white flex items-center gap-2">
        <span class="text-sky-300 font-bold">{{ activePage }}</span>
        <span class="text-slate-500">/</span>
        <span>{{ pages.length }}</span>
      </div>

      <button 
        type="button"
        @click="scrollToTop"
        class="p-2.5 rounded-full bg-black/80 backdrop-blur-md border border-white/15 text-slate-300 hover:text-white shadow-elevation-3 transition-colors md-state-layer"
        title="Scroll to Top"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="m18 15-6-6-6 6" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';

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

const displayPages = computed(() => {
  // If smart double spread splitting occurred, skip the left split in Webtoon vertical scroll so the wide panoramic image is displayed once in full width
  return props.pages.filter(p => !p.isSpread || p.spreadPart !== 'left');
});

const containerRef = ref(null);
const activePage = ref(props.initialPage || 1);
let observer = null;

function setupIntersectionObserver() {
  if (!containerRef.value) return;

  const options = {
    root: containerRef.value,
    rootMargin: '-30% 0px -40% 0px',
    threshold: 0,
  };

  observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const pageNum = parseInt(entry.target.getAttribute('data-page'));
        if (!isNaN(pageNum) && pageNum !== activePage.value) {
          activePage.value = pageNum;
          emit('page-change', pageNum);
        }
      }
    });
  }, options);

  const targets = containerRef.value.querySelectorAll('.webtoon-page-wrapper');
  targets.forEach(t => observer.observe(t));
}

function jumpToPage(pageNum) {
  const targetEl = document.getElementById(`webtoon-page-${pageNum}`);
  if (targetEl) {
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    activePage.value = pageNum;
  }
}

function scrollToTop() {
  if (containerRef.value) {
    containerRef.value.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

defineExpose({
  jumpToPage,
});

function onContainerClick(e) {
  // If clicking on margin or page, toggle HUD
  if (e.target.tagName !== 'BUTTON' && !e.target.closest('button')) {
    emit('toggle-hud');
  }
}

let scrollTimeout = null;
function onScrollThrottled() {
  if (scrollTimeout) return;
  scrollTimeout = setTimeout(() => {
    scrollTimeout = null;
  }, 100);
}

onMounted(() => {
  nextTick(() => {
    setupIntersectionObserver();
    if (props.initialPage > 1) {
      setTimeout(() => jumpToPage(props.initialPage), 200);
    }
  });
});

onUnmounted(() => {
  if (observer) {
    observer.disconnect();
    observer = null;
  }
});
</script>
