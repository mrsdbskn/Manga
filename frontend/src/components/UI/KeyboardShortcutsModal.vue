<template>
  <div 
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md select-none animate-in fade-in duration-200"
    @click.self="$emit('close')"
  >
    <div class="glass-card rounded-3xl p-6 sm:p-8 max-w-lg w-full border border-sky-500/20 shadow-2xl relative">
      <!-- Modal Header -->
      <div class="flex items-center justify-between border-b border-white/10 pb-4 mb-5">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="M6 8h.001M10 8h.001M14 8h.001M18 8h.001M8 12h.001M12 12h.001M16 12h.001M7 16h10" />
            </svg>
          </div>
          <div>
            <h3 class="text-base font-bold text-white font-outfit">Keyboard Shortcuts</h3>
            <p class="text-[11px] text-slate-400">Power gestures for seamless manga reading</p>
          </div>
        </div>
        <button 
          type="button" 
          @click="$emit('close')"
          class="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white flex items-center justify-center text-xs transition-colors"
        >
          ✕
        </button>
      </div>

      <!-- Shortcuts Grid -->
      <div class="space-y-4 text-xs">
        <!-- Navigation Section -->
        <div>
          <div class="text-[10px] font-bold text-sky-400 uppercase tracking-wider mb-2">Page Turning & Flow</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5">
              <span class="text-slate-300">Turn Page</span>
              <div class="flex items-center gap-1 font-mono">
                <kbd class="px-1.5 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-sky-300">←</kbd>
                <kbd class="px-1.5 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-sky-300">→</kbd>
              </div>
            </div>
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5">
              <span class="text-slate-300">Next Page</span>
              <kbd class="px-2 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-sky-300 font-mono">Space</kbd>
            </div>
          </div>
        </div>

        <!-- Layout & Screen Orientation -->
        <div>
          <div class="text-[10px] font-bold text-sky-400 uppercase tracking-wider mb-2">Orientation & Spreads</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5">
              <span class="text-slate-300">Dual / Single Spread</span>
              <kbd class="px-2 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-amber-300 font-mono">D</kbd>
            </div>
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5">
              <span class="text-slate-300">Rotate Screen (90°)</span>
              <kbd class="px-2 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-amber-300 font-mono">O</kbd>
            </div>
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5">
              <span class="text-slate-300">Manga RTL / LTR</span>
              <kbd class="px-2 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-emerald-300 font-mono">R</kbd>
            </div>
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5">
              <span class="text-slate-300">3D Flip / Webtoon</span>
              <kbd class="px-2 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-purple-300 font-mono">M</kbd>
            </div>
          </div>
        </div>

        <!-- View & Tools -->
        <div>
          <div class="text-[10px] font-bold text-sky-400 uppercase tracking-wider mb-2">View & Tools</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5">
              <span class="text-slate-300">Zoom Inspector</span>
              <kbd class="px-2 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-sky-300 font-mono">Z</kbd>
            </div>
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5">
              <span class="text-slate-300">Toggle Fullscreen</span>
              <kbd class="px-2 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-sky-300 font-mono">F</kbd>
            </div>
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5">
              <span class="text-slate-300">Toggle HUD Bar</span>
              <kbd class="px-2 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-sky-300 font-mono">H</kbd>
            </div>
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5">
              <span class="text-slate-300">Bookmark Page</span>
              <kbd class="px-2 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-sky-300 font-mono">B</kbd>
            </div>
            <div class="flex items-center justify-between p-2 rounded-xl bg-white/[0.04] border border-white/5 sm:col-span-2">
              <span class="text-slate-300">Return to Bookshelf</span>
              <kbd class="px-2 py-0.5 rounded bg-black/60 border border-white/10 text-[10px] text-rose-300 font-mono">Esc</kbd>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom Tip -->
      <div class="mt-5 pt-3 border-t border-white/10 flex items-center justify-between text-[11px] text-slate-400">
        <span>💡 Press <kbd class="px-1 py-0.2 rounded bg-black/40 text-slate-300 font-mono">?</kbd> anytime to open</span>
        <button 
          type="button" 
          @click="$emit('close')"
          class="px-4 py-1.5 rounded-full bg-sky-500/20 text-sky-300 hover:bg-sky-500/30 border border-sky-500/30 font-semibold text-xs"
        >
          Got it
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
});

defineEmits(['close']);
</script>
