<template>
  <div 
    :class="[
      'w-full h-full bg-white flex flex-col justify-between items-center select-none overflow-hidden relative text-slate-900',
      compact ? 'py-1' : 'py-1.5'
    ]"
  >
    <!-- TOP SECTION: Jump Comics JC Logo & Main Titles -->
    <div class="flex flex-col items-center w-full shrink-0">
      <!-- Official Jump Comics JC Logo -->
      <div :class="compact ? 'w-3.5 h-3 my-0.5' : 'w-5 h-4 my-1'" class="flex items-center justify-center">
        <img 
          src="/comics/assets/jump_comics_logo.png" 
          alt="JC" 
          class="w-full h-full object-contain pointer-events-none"
        />
      </div>

      <!-- Title Block: Vertical "ONE PIECE" & Japanese "ワンピース" -->
      <div class="relative flex items-center justify-center w-full px-0.5 mt-0.5">
        <!-- Katakana Sub-title on Left (ワンピース) -->
        <span 
          v-if="!compact"
          class="absolute left-[1px] top-6 [writing-mode:vertical-rl] font-extrabold text-[5.5px] leading-none text-slate-800 tracking-tight"
        >
          ワンピース
        </span>

        <!-- Vertical Bold Red "ONE PIECE" -->
        <div 
          class="flex flex-col items-center leading-none text-[#b91c1c] font-black uppercase tracking-tight select-none"
          :class="compact ? 'text-[7px]' : 'text-[9.5px]'"
          style="font-family: Impact, 'Arial Black', sans-serif;"
        >
          <span>O</span>
          <span>N</span>
          <span>E</span>
          <span :class="compact ? 'h-[1px]' : 'h-[2px]'"></span>
          <span>P</span>
          <span>I</span>
          <span>E</span>
          <span>C</span>
          <span>E</span>
        </div>
      </div>

      <!-- Straw Hat Jolly Roger Volume Emblem -->
      <div 
        :class="compact ? 'w-4 h-4 mt-1' : 'w-5.5 h-5.5 mt-1.5'" 
        class="relative flex items-center justify-center shrink-0"
      >
        <svg 
          viewBox="0 0 100 100" 
          class="w-full h-full drop-shadow-none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- Crossbones -->
          <g fill="#f59e0b" stroke="#d97706" stroke-width="1.5">
            <line x1="16" y1="16" x2="84" y2="84" stroke="#f59e0b" stroke-width="9" stroke-linecap="round" />
            <circle cx="12" cy="12" r="6" />
            <circle cx="18" cy="8" r="6" />
            <circle cx="82" cy="92" r="6" />
            <circle cx="88" cy="88" r="6" />

            <line x1="84" y1="16" x2="16" y2="84" stroke="#f59e0b" stroke-width="9" stroke-linecap="round" />
            <circle cx="88" cy="12" r="6" />
            <circle cx="82" cy="8" r="6" />
            <circle cx="12" cy="88" r="6" />
            <circle cx="18" cy="92" r="6" />
          </g>

          <!-- Skull Head Base -->
          <path 
            d="M 24 45 C 24 22 76 22 76 45 C 76 54 70 58 68 64 C 67 67 67 76 64 78 C 60 80 40 80 36 78 C 33 76 33 67 32 64 C 30 58 24 54 24 45 Z" 
            fill="#f59e0b" 
            stroke="#d97706" 
            stroke-width="1.5" 
          />

          <!-- Straw Hat Brim & Ribbon -->
          <path d="M 12 38 Q 50 30 88 38 Q 50 34 12 38 Z" fill="#b45309" stroke="#78350f" stroke-width="1" />
          <path d="M 32 25 Q 50 18 68 25 Q 50 21 32 25 Z" fill="#dc2626" />

          <!-- Forehead: '巻' (Kan) -->
          <text 
            x="50" 
            y="32" 
            font-family="'Noto Sans JP', sans-serif" 
            font-size="13" 
            font-weight="900" 
            text-anchor="middle" 
            fill="#18181b"
          >
            巻
          </text>

          <!-- White Eye Sockets -->
          <circle cx="40" cy="50" r="7" fill="#ffffff" stroke="#d97706" stroke-width="1" />
          <circle cx="60" cy="50" r="7" fill="#ffffff" stroke="#d97706" stroke-width="1" />

          <!-- Mouth / Teeth Area with Volume Kanji -->
          <rect x="34" y="64" width="32" height="14" rx="2" fill="#fbbf24" stroke="#d97706" stroke-width="1" />
          <text 
            x="50" 
            y="75.5" 
            font-family="'Noto Sans JP', sans-serif" 
            :font-size="kanjiText.length > 2 ? '10' : kanjiText.length === 2 ? '11.5' : '13'" 
            font-weight="900" 
            text-anchor="middle" 
            fill="#18181b"
          >
            {{ kanjiText }}
          </text>
        </svg>
      </div>
    </div>

    <!-- MIDDLE SECTION: Clean Minimalist Graphic Space (Keeps character art out per user design) -->
    <div class="my-auto flex-1 flex flex-col items-center justify-center w-full py-1">
      <!-- Subtle artistic accent dot -->
      <div v-if="!compact" class="w-1 h-1 rounded-full bg-slate-300/60 my-auto"></div>
    </div>

    <!-- BOTTOM SECTION: Author Credit & Shueisha Box -->
    <div class="flex flex-col items-center w-full shrink-0">
      <!-- Eiichiro Oda Credit (尾田栄一郎◆) -->
      <div 
        class="[writing-mode:vertical-rl] font-bold text-slate-900 tracking-widest text-center select-none mb-1.5"
        :class="compact ? 'text-[6px] tracking-normal' : 'text-[7.5px]'"
      >
        <span>尾田栄一郎◆</span>
      </div>

      <!-- Publisher Block: Cyan Blue Box with "集英社" (Shueisha) -->
      <div 
        class="w-full bg-[#00a0e9] flex flex-col items-center justify-center py-1 text-white font-black tracking-widest select-none"
        :class="compact ? 'py-0.5' : 'py-1'"
      >
        <div 
          class="[writing-mode:vertical-rl] text-center leading-none text-white font-extrabold"
          :class="compact ? 'text-[5.5px]' : 'text-[7px]'"
        >
          集英社
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { toKanjiVolume } from '@/utils/kanji.js';

const props = defineProps({
  volumeNumber: {
    type: [Number, String],
    required: true,
  },
  compact: {
    type: Boolean,
    default: false,
  },
});

const kanjiText = computed(() => {
  return toKanjiVolume(props.volumeNumber);
});
</script>

<style scoped>
/* Ensure clean vertical typographic rendering */
span {
  user-select: none;
}
</style>
