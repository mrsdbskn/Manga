<template>
  <div 
    :class="[
      'w-full h-full bg-white flex flex-col justify-between items-center select-none overflow-hidden relative text-slate-900',
      compact ? 'pt-1 pb-0' : 'pt-1.5 pb-0'
    ]"
  >
    <!-- TOP SECTION: Jump Comics JC Logo & Official ONE PIECE Spine Title -->
    <div class="flex flex-col items-center w-full shrink-0">
      <!-- Official Jump Comics JC Logo -->
      <div :class="compact ? 'w-3.5 h-3 my-0.5' : 'w-4.5 h-3.5 my-1'" class="flex items-center justify-center">
        <img 
          src="/comics/assets/jump_comics_logo.png" 
          alt="JC" 
          class="w-full h-full object-contain pointer-events-none select-none"
        />
      </div>

      <!-- Authentic ONE PIECE & ワンピース Spine Title (Official Sizing & Proportion) -->
      <div class="w-full flex items-center justify-center my-0.5 px-0.5">
        <img 
          src="/comics/assets/one_piece_spine_title.png" 
          alt="ONE PIECE ワンピース" 
          :class="compact ? 'w-[90%] max-h-[70px]' : 'w-[88%] max-h-[105px]'"
          class="object-contain pointer-events-none select-none"
        />
      </div>

      <!-- Straw Hat Jolly Roger Volume Emblem (Vector SVG Watermark with Kanji Overlay) -->
      <div 
        :class="compact ? 'w-4.5 h-4.5 mt-0.5' : 'w-6 h-6 mt-1'" 
        class="relative flex flex-col items-center justify-center shrink-0"
        :style="{ color: spineSkullColor }"
      >
        <!-- Background Skull Watermark Silhouette (Crisp 100% Vector with authentic volume color) -->
        <svg 
          viewBox="0 0 223 237" 
          class="absolute inset-0 w-full h-full object-contain pointer-events-none select-none"
          aria-hidden="true"
        >
          <path :d="SKULL_SVG_PATH" fill="currentColor" fill-rule="evenodd" />
        </svg>

        <!-- Foreground Kanji Text: '巻' on top forehead + Volume Number through center -->
        <div class="relative z-10 flex flex-col items-center justify-center text-center select-none font-japanese leading-none pointer-events-none">
          <!-- '巻' (Volume) situated on forehead -->
          <span 
            class="font-black text-slate-900 leading-none"
            :class="compact ? 'text-[5.5px] mb-[0.5px]' : 'text-[7px] mb-[1px]'"
          >
            巻
          </span>

          <!-- Volume Kanji Numeral (e.g. 一, 二, 十, 九十六) situated through center -->
          <div 
            class="flex flex-col items-center font-black text-slate-900 leading-none"
            :class="[
              compact 
                ? (kanjiText.length > 2 ? 'text-[4.5px]' : kanjiText.length === 2 ? 'text-[5.5px]' : 'text-[7px]')
                : (kanjiText.length > 2 ? 'text-[6px]' : kanjiText.length === 2 ? 'text-[7.5px]' : 'text-[9.5px]')
            ]"
          >
            <span v-for="(char, idx) in kanjiText" :key="idx" class="leading-none">
              {{ char }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- MIDDLE SECTION: Clean Minimalist Graphic Space (Keeps character art out per user design) -->
    <div class="my-auto flex-1 flex flex-col items-center justify-center w-full"></div>

    <!-- BOTTOM SECTION: Author Credit & Slim Shueisha Cyan Bar -->
    <div class="flex flex-col items-center w-full shrink-0">
      <!-- Eiichiro Oda Credit (尾田栄一郎◆) -->
      <div 
        class="[writing-mode:vertical-rl] font-bold text-slate-900 tracking-widest text-center select-none font-japanese"
        :class="compact ? 'text-[6px] mb-1' : 'text-[7.5px] mb-1.5'"
      >
        <span>尾田栄一郎◆</span>
      </div>

      <!-- Publisher Block: Slim Cyan Blue Box with horizontal "集英社" (Shueisha) -->
      <div 
        class="w-full bg-[#00a0e9] flex items-center justify-center text-white font-extrabold select-none shrink-0"
        :class="compact ? 'py-[1.5px]' : 'py-0.5'"
      >
        <span 
          class="font-japanese tracking-[0.2em] leading-none text-white text-center"
          :class="compact ? 'text-[5px]' : 'text-[6.5px]'"
        >
          集英社
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { toKanjiVolume } from '@/utils/kanji.js';
import { getVolumeSpineColor } from '@/utils/spineColors.js';
import { SKULL_SVG_PATH } from '@/utils/skullPath.js';

const props = defineProps({
  volumeNumber: {
    type: [Number, String],
    required: true,
  },
  compact: {
    type: Boolean,
    default: false,
  },
  customColor: {
    type: String,
    default: null,
  },
});

const kanjiText = computed(() => {
  return toKanjiVolume(props.volumeNumber);
});

const spineSkullColor = computed(() => {
  if (props.customColor) return props.customColor;
  return getVolumeSpineColor(props.volumeNumber);
});
</script>

<style scoped>
/* Ensure clean vertical typographic rendering */
span {
  user-select: none;
}
</style>
