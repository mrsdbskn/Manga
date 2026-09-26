<template>
  <div 
    class="flex flex-col items-center select-none group"
    :id="`volume-card-${volume.volumeNumber}`"
  >
    <!-- 3D Perspective Stage -->
    <div 
      ref="stageRef"
      class="perspective-1200 w-[210px] h-[300px] flex items-center justify-center cursor-grab active:cursor-grabbing relative py-4"
      @pointerdown="onPointerDown"
      @dblclick="resetRotation"
      title="Drag to spin 360° • Double-click to reset"
    >
      <!-- 3D Book Container with Dynamic Rotation (Official 12.7 x 2.03 x 19.05 cm) -->
      <div 
        class="preserve-3d relative w-[180px] h-[270px] transition-transform will-change-transform"
        :style="{
          transform: `rotateY(${rotationY}deg) rotateX(${rotationX}deg)`,
          transition: isDragging ? 'none' : 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        }"
      >
        <!-- FRONT COVER -->
        <div 
          class="absolute inset-0 rounded-r-sm overflow-hidden bg-[#181a26] shadow-elevation-3 border-r border-t border-b border-white/10 backface-hidden"
          style="transform: translateZ(14.4px);"
        >
          <!-- Cover Image or High-Aesthetic Graphic -->
          <img 
            v-if="volume.coverUrl && !imageError"
            :src="volume.coverUrl" 
            :alt="volume.title"
            class="w-full h-full object-cover object-center pointer-events-none select-none"
            @error="onImageError"
            loading="lazy"
          />
          <!-- Graphic Fallback if cover image is loading/missing -->
          <div 
            v-else 
            class="w-full h-full flex flex-col justify-between p-3 relative overflow-hidden"
            :style="{ background: `linear-gradient(145deg, #181b28 0%, ${volume.spineColor || '#0842a0'}40 100%)` }"
          >
            <!-- Jump Comics Header -->
            <div class="flex items-center justify-between z-10 border-b border-white/20 pb-1.5">
              <span class="text-[10px] font-bold tracking-widest text-amber-400">JUMP COMICS</span>
              <span class="text-[9px] px-1.5 py-0.5 rounded bg-black/40 text-slate-300 font-mono">VOL. {{ volume.volumeNumber }}</span>
            </div>

            <!-- Title & Arc Center -->
            <div class="z-10 text-center my-auto px-1">
              <p class="text-[11px] font-japanese text-slate-300 line-clamp-1 mb-1">{{ volume.japaneseTitle }}</p>
              <h4 class="text-base font-extrabold text-white leading-tight font-outfit uppercase tracking-tight line-clamp-2">
                {{ volume.title }}
              </h4>
              <p class="text-[10px] text-sky-300/80 font-medium mt-1">{{ volume.arcName }}</p>
            </div>

            <!-- Bottom Credits -->
            <div class="flex items-end justify-between z-10 pt-1 border-t border-white/10 text-[9px] text-slate-400">
              <span class="font-bold text-white tracking-wider">EIICHIRO ODA</span>
              <span>Ch. {{ volume.chapterStart }}-{{ volume.chapterEnd }}</span>
            </div>

            <!-- Background watermark -->
            <div class="absolute -right-4 -bottom-6 text-7xl font-black text-white/[0.04] select-none pointer-events-none">
              {{ volume.volumeNumber }}
            </div>
          </div>

          <!-- Gloss / Specular Lighting Overlay -->
          <div 
            class="absolute inset-0 cover-gloss"
            :style="{
              opacity: Math.max(0.1, Math.min(0.6, (1 - Math.cos((rotationY * Math.PI) / 180)) * 0.4))
            }"
          ></div>

          <!-- Left Hinge Crease Shadow -->
          <div class="absolute left-0 top-0 bottom-0 w-3 bg-gradient-to-r from-black/50 via-black/20 to-transparent pointer-events-none"></div>
        </div>

        <!-- BACK COVER (180deg) -->
        <div 
          class="absolute inset-0 rounded-l-sm overflow-hidden bg-[#13151f] shadow-elevation-3 border-l border-t border-b border-white/10 backface-hidden"
          style="transform: rotateY(180deg) translateZ(14.4px);"
        >
          <!-- Real Back Cover Image if available -->
          <img 
            v-if="volume.backCoverUrl && !backImageError"
            :src="volume.backCoverUrl" 
            :alt="`${volume.title} Back Cover`"
            class="w-full h-full object-cover object-center pointer-events-none select-none"
            @error="onBackImageError"
            loading="lazy"
          />

          <!-- Graphic Fallback if back cover is missing/error -->
          <div 
            v-else
            class="w-full h-full p-3.5 flex flex-col justify-between"
          >
            <!-- Back Header -->
            <div class="flex items-center justify-between border-b border-white/10 pb-1.5">
              <span class="text-[10px] font-bold tracking-widest text-slate-400">SHUEISHA MANGA</span>
              <span class="text-[9px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 font-mono">CANON {{ volume.volumeNumber }}</span>
            </div>

            <!-- Back Synopsis / Details -->
            <div class="my-auto py-1">
              <p class="text-[11px] text-slate-300 leading-relaxed line-clamp-5 italic">
                "{{ volume.summary || 'Monkey D. Luffy embarks on his grand voyage across the Grand Line to discover the One Piece.' }}"
              </p>

              <div class="mt-2.5 pt-2 border-t border-white/10 text-[10px] text-slate-400 space-y-1">
                <div class="flex justify-between">
                  <span>Story & Art:</span>
                  <span class="text-white font-medium">Eiichiro Oda</span>
                </div>
                <div class="flex justify-between">
                  <span>Chapters:</span>
                  <span class="text-white font-mono">{{ volume.chapterStart }} – {{ volume.chapterEnd }}</span>
                </div>
                <div class="flex justify-between">
                  <span>Pages:</span>
                  <span class="text-white font-mono">{{ volume.pageCount || 200 }}</span>
                </div>
              </div>
            </div>

            <!-- Barcode Mock -->
            <div class="pt-2 border-t border-white/10 flex items-center justify-between">
              <div class="h-6 w-24 bg-gradient-to-r from-white/70 via-white/40 to-white/70 rounded-sm opacity-60 flex items-center justify-center">
                <span class="text-[7px] font-mono text-black font-bold tracking-tighter">||| | |||| | ||||</span>
              </div>
              <span class="text-[9px] font-mono text-slate-500">ISBN 978-4-08</span>
            </div>
          </div>

          <!-- Reverse lighting overlay -->
          <div class="absolute inset-0 bg-gradient-to-tr from-black/40 via-transparent to-white/5 pointer-events-none"></div>
        </div>

        <!-- SPINE (Left Face - Official 2.03cm / 28.8px) -->
        <div 
          class="absolute top-0 bottom-0 w-[28.8px] overflow-hidden flex flex-col justify-between text-center shadow-lg"
          :style="{
            left: 'calc(50% - 14.4px)',
            transform: 'rotateY(-90deg) translateZ(90px)',
            backgroundColor: volume.spineColor || '#1e2235',
          }"
        >
          <!-- Real Spine Image if available -->
          <img
            v-if="volume.spineUrl && !spineImageError"
            :src="volume.spineUrl"
            :alt="`${volume.title} Spine`"
            class="w-full h-full object-fill object-center pointer-events-none select-none"
            @error="onSpineImageError"
            loading="lazy"
          />
          <!-- Graphic Fallback if spine image is missing -->
          <template v-else>
            <!-- Top Spine Logo -->
            <div class="z-10 pt-2">
              <span class="text-[8px] font-black text-amber-300 tracking-tighter block">JC</span>
              <div class="w-5 h-[1px] bg-white/30 mx-auto my-1"></div>
            </div>

            <!-- Vertical Volume Title & Japanese Text -->
            <div class="my-auto z-10 flex flex-col items-center">
              <span class="text-[12px] font-extrabold text-white bg-black/40 w-6 h-6 rounded-full flex items-center justify-center mb-2 font-mono shadow-sm">
                {{ volume.volumeNumber }}
              </span>
              <span class="text-[9px] font-bold text-white tracking-widest uppercase [writing-mode:vertical-rl] max-h-[110px] overflow-hidden truncate">
                ONE PIECE
              </span>
            </div>

            <!-- Bottom Spine Oda Credit -->
            <div class="z-10 pb-2 text-[8px] text-white/80 font-bold [writing-mode:vertical-rl] mx-auto">
              尾田栄一郎
            </div>
          </template>

          <!-- Spine Curvature Texture & Highlight -->
          <div class="absolute inset-0 spine-emboss pointer-events-none"></div>
        </div>

        <!-- FORE-EDGE (Right Face - Paper Pages Block) -->
        <div 
          class="absolute top-0 bottom-0 w-[28.8px] overflow-hidden paper-block-pattern shadow-inner"
          :style="{
            left: 'calc(50% - 14.4px)',
            transform: 'rotateY(90deg) translateZ(90px)',
          }"
        >
          <!-- Inset page edge shadows -->
          <div class="absolute inset-y-0 left-0 w-1 bg-black/30"></div>
          <div class="absolute inset-y-0 right-0 w-1 bg-black/30"></div>
        </div>

        <!-- TOP EDGE (Top Paper Block) -->
        <div 
          class="absolute left-0 right-0 h-[28.8px] paper-block-top overflow-hidden"
          :style="{
            top: 'calc(50% - 14.4px)',
            transform: 'rotateX(90deg) translateZ(135px)',
          }"
        ></div>

        <!-- BOTTOM EDGE (Bottom Paper Block) -->
        <div 
          class="absolute left-0 right-0 h-[28.8px] paper-block-top overflow-hidden"
          :style="{
            top: 'calc(50% - 14.4px)',
            transform: 'rotateX(-90deg) translateZ(135px)',
          }"
        ></div>

        <!-- GROUND CAST SHADOW -->
        <div 
          class="absolute w-[180px] h-[55px] rounded-[50%] blur-md pointer-events-none transition-opacity duration-300"
          :style="{
            top: '265px',
            left: '0px',
            transform: 'rotateX(80deg) translateZ(-35px)',
            background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0) 70%)',
            opacity: isDragging ? 0.9 : 0.6,
          }"
        ></div>
      </div>

      <!-- 360° Spin Drag Hint Badge & Flip Button -->
      <div class="absolute top-1 right-1 z-20">
        <button 
          type="button" 
          @click.stop="toggleFlip"
          class="p-1.5 rounded-full bg-black/60 hover:bg-black/90 text-slate-300 hover:text-white border border-white/10 backdrop-blur-md shadow-sm transition-all"
          title="Flip Book (Front / Back)"
        >
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
            <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
            <path d="M16 21h5v-5"/>
          </svg>
        </button>
      </div>

      <!-- 360° Spin Drag Hint Badge (Fades after first interaction) -->
      <transition name="fade">
        <div 
          v-if="!hasInteracted"
          class="absolute bottom-1 bg-black/60 backdrop-blur-md border border-white/10 text-[9px] text-slate-300 px-2 py-0.5 rounded-full pointer-events-none flex items-center gap-1 shadow-sm"
        >
          <svg class="w-2.5 h-2.5 text-sky-400 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
          <span>Drag to spin 360°</span>
        </div>
      </transition>
    </div>

    <!-- Volume Metadata & Quick Actions -->
    <div class="w-full max-w-[210px] mt-2 flex flex-col items-center text-center">
      <!-- Title & Number -->
      <h3 class="text-sm font-bold text-white truncate max-w-full leading-snug group-hover:text-[#a8c7fa] transition-colors" :title="formattedVolumeTitle">
        {{ formattedVolumeTitle }}
      </h3>
      
      <!-- Chapter Badge -->
      <div class="flex items-center gap-1.5 mt-1 text-[11px] text-slate-400">
        <span class="px-1.5 py-0.5 rounded-md bg-white/[0.06] font-mono text-[10px] text-slate-300">
          Ch. {{ volume.chapterStart }}–{{ volume.chapterEnd }}
        </span>
        <span v-if="volume.arcName" class="truncate max-w-[100px] text-[10px] text-slate-400">
          {{ volume.arcName.replace(' Arc', '') }}
        </span>
      </div>

      <!-- Reading Progress Bar -->
      <div v-if="userProgress.percentage > 0" class="w-full mt-2 px-1">
        <ProgressBarMD3 
          :value="userProgress.percentage" 
          :height="4"
          :barColor="volume.spineColor || '#a8c7fa'"
          :showLabel="true"
        />
      </div>

      <!-- Read / Resume Button -->
      <button 
        type="button"
        @click="openReader"
        :class="[
          'mt-2.5 w-full py-1.5 px-3 rounded-full text-xs font-semibold flex items-center justify-center gap-1.5 transition-all duration-200 md-state-layer',
          userProgress.percentage > 0
            ? 'bg-[#a8c7fa]/20 text-[#a8c7fa] hover:bg-[#a8c7fa]/30 border border-[#a8c7fa]/30'
            : 'bg-[#0842a0] text-white hover:bg-[#0b57d0] shadow-elevation-1'
        ]"
      >
        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M5 3l14 9-14 9V3z" />
        </svg>
        <span>{{ userProgress.percentage > 0 ? (userProgress.completed ? 'Re-read' : 'Resume P.' + userProgress.lastPage) : 'Read Volume' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useLibraryStore } from '../../stores/library.js';
import { useProgressStore } from '../../stores/progress.js';
import ProgressBarMD3 from '../UI/ProgressBarMD3.vue';

const props = defineProps({
  volume: {
    type: Object,
    required: true,
  },
});

const libraryStore = useLibraryStore();
const progressStore = useProgressStore();

const userProgress = computed(() => {
  return progressStore.getProgressForVolume(props.volume.id);
});

const formattedVolumeTitle = computed(() => {
  const vNum = props.volume.volumeNumber;
  let rawTitle = (props.volume.title || '').trim();
  // Strip redundant leading "Vol. 112 -", "Volume 112 -", "Volume 112:", "Vol 112:"
  rawTitle = rawTitle.replace(/^(?:volume|vol\.?)\s*\d+\s*[:\-–—]\s*/i, '').trim();
  // If rawTitle is just "Volume 112" or "Vol. 112" or empty
  if (!rawTitle || /^(?:volume|vol\.?)\s*\d+$/i.test(rawTitle)) {
    return `Vol. ${vNum}`;
  }
  return `Vol. ${vNum} - ${rawTitle}`;
});

// 3D Physics & Drag Engine State
const stageRef = ref(null);
const rotationY = ref(22); // Default isometric aesthetic angle showing cover and spine
const rotationX = ref(0);
const isDragging = ref(false);
const hasInteracted = ref(false);

let startX = 0;
let startY = 0;
let initialRotY = 22;
let initialRotX = 0;
let lastPointerX = 0;
let velocityX = 0;
let rafId = null;

function onPointerDown(e) {
  isDragging.value = true;
  hasInteracted.value = true;
  if (rafId) cancelAnimationFrame(rafId);

  startX = e.clientX;
  startY = e.clientY;
  lastPointerX = e.clientX;
  initialRotY = rotationY.value;
  initialRotX = rotationX.value;

  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', onPointerUp);
}

function onPointerMove(e) {
  if (!isDragging.value) return;

  const deltaX = e.clientX - startX;
  const deltaY = e.clientY - startY;

  // Calculate velocity for inertia release
  velocityX = e.clientX - lastPointerX;
  lastPointerX = e.clientX;

  // 360° horizontal spin with sensitivity
  rotationY.value = (initialRotY + deltaX * 0.9) % 360;

  // Subtle vertical tilt clamped between -15° and +15°
  const tilt = initialRotX - deltaY * 0.25;
  rotationX.value = Math.max(-15, Math.min(15, tilt));
}

function onPointerUp() {
  if (!isDragging.value) return;
  isDragging.value = false;

  window.removeEventListener('pointermove', onPointerMove);
  window.removeEventListener('pointerup', onPointerUp);

  // Apply smooth inertia damping
  applyInertia();
}

function applyInertia() {
  if (Math.abs(velocityX) > 0.3) {
    rotationY.value = (rotationY.value + velocityX * 0.8) % 360;
    velocityX *= 0.92; // Friction factor
    // Subtle tilt relaxation
    rotationX.value *= 0.88;
    rafId = requestAnimationFrame(applyInertia);
  } else {
    // Snap tilt back to 0
    rotationX.value = 0;
  }
}

function resetRotation() {
  rotationY.value = 22;
  rotationX.value = 0;
  velocityX = 0;
}

function toggleFlip() {
  hasInteracted.value = true;
  velocityX = 0;
  rotationX.value = 0;
  // If close to back (180deg), flip to front (22deg); otherwise flip to 180deg
  const normY = ((rotationY.value % 360) + 360) % 360;
  if (Math.abs(normY - 180) < 60) {
    rotationY.value = 22;
  } else {
    rotationY.value = 180;
  }
}

function openReader() {
  libraryStore.openReader(props.volume);
}

const imageError = ref(false);
const backImageError = ref(false);
const spineImageError = ref(false);

function onImageError() {
  imageError.value = true;
}

function onBackImageError() {
  backImageError.value = true;
}

function onSpineImageError() {
  spineImageError.value = true;
}
</script>
