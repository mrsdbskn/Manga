<template>
  <section 
    :id="`saga-section-${saga.id}`"
    class="w-full mb-16 scroll-mt-24"
  >
    <!-- Centered High-Impact Widescreen Art Banner -->
    <div 
      class="relative w-full rounded-3xl overflow-hidden mb-10 shadow-elevation-2 border border-white/10 group"
      :style="{ borderColor: `${saga.themeColor || '#38bdf8'}30` }"
    >
      <!-- Background Banner Artwork / Gradient Atmosphere -->
      <div class="absolute inset-0 bg-[#14161f]">
        <img 
          v-if="saga.bannerUrl"
          :src="saga.bannerUrl" 
          :alt="saga.name"
          class="w-full h-full object-cover object-center opacity-35 group-hover:scale-105 transition-transform duration-700 ease-out"
          @error="onBannerError"
        />
        <!-- Radial atmospheric tint with saga theme color -->
        <div 
          class="absolute inset-0"
          :style="{
            background: `radial-gradient(ellipse at center, ${saga.themeColor || '#38bdf8'}18 0%, rgba(15, 17, 24, 0.95) 85%)`
          }"
        ></div>
        <!-- Bottom fade -->
        <div class="absolute inset-0 bg-gradient-to-t from-[#0f1118] via-transparent to-black/30"></div>
      </div>

      <!-- Centered Content Typography -->
      <div class="relative z-10 py-10 sm:py-14 px-6 text-center max-w-4xl mx-auto flex flex-col items-center">
        <!-- Japanese Kana Title -->
        <span 
          v-if="saga.japaneseName"
          class="text-xs sm:text-sm font-japanese font-semibold tracking-widest uppercase mb-2"
          :style="{ color: saga.themeColor || '#a8c7fa' }"
        >
          {{ saga.japaneseName }}
        </span>

        <!-- Main Saga Title -->
        <h2 class="text-2xl sm:text-4xl font-extrabold text-white tracking-tight font-outfit uppercase">
          {{ saga.name }}
        </h2>

        <!-- Range Badges & Canon Chapter Scope -->
        <div class="flex flex-wrap items-center justify-center gap-2 mt-3 text-xs">
          <span 
            class="px-3 py-1 rounded-full font-mono font-bold shadow-sm"
            :style="{
              backgroundColor: `${saga.themeColor || '#38bdf8'}20`,
              color: saga.themeColor || '#38bdf8',
              border: `1px solid ${saga.themeColor || '#38bdf8'}40`
            }"
          >
            Vols {{ saga.volumeRange[0] }} – {{ saga.volumeRange[1] }}
          </span>

          <span class="px-3 py-1 rounded-full bg-white/[0.08] text-slate-300 font-mono">
            Ch. {{ saga.chapterRange[0] }} – {{ saga.chapterRange[1] }}
          </span>

          <span class="px-3 py-1 rounded-full bg-white/[0.08] text-slate-300">
            {{ volumes.length }} {{ volumes.length === 1 ? 'Volume' : 'Volumes' }}
          </span>
        </div>

        <!-- Description Snippet -->
        <p class="text-xs sm:text-sm text-slate-300/90 leading-relaxed max-w-2xl mt-4">
          {{ saga.description }}
        </p>

        <!-- Sub-arc Tags -->
        <div v-if="saga.arcs && saga.arcs.length" class="flex flex-wrap items-center justify-center gap-1.5 mt-4">
          <span 
            v-for="arc in saga.arcs" 
            :key="arc"
            class="text-[10px] px-2.5 py-0.5 rounded-full bg-black/40 text-slate-400 border border-white/5"
          >
            {{ arc }}
          </span>
        </div>
      </div>
    </div>

    <!-- Volumes Container: Grid Mode vs List Mode -->
    <div v-if="viewMode === 'grid'" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-8 sm:gap-10 justify-items-center">
      <VolumeCard3D 
        v-for="vol in volumes" 
        :key="vol.id" 
        :volume="vol" 
      />
    </div>

    <div v-else class="flex flex-col gap-4 max-w-5xl mx-auto">
      <VolumeListItem 
        v-for="vol in volumes" 
        :key="vol.id" 
        :volume="vol" 
      />
    </div>
  </section>
</template>

<script setup>
import VolumeCard3D from './VolumeCard3D.vue';
import VolumeListItem from './VolumeListItem.vue';

const props = defineProps({
  saga: {
    type: Object,
    required: true,
  },
  volumes: {
    type: Array,
    required: true,
  },
  viewMode: {
    type: String,
    default: 'grid',
  },
});

function onBannerError(e) {
  // If banner image fails or is missing, gradient stays visible
  e.target.style.display = 'none';
}
</script>
