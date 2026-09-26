<template>
  <div 
    class="flex flex-col items-center select-none group"
    :id="`volume-card-${volume.volumeNumber}`"
  >
    <!-- 3D Perspective Stage -->
    <div 
      ref="stageRef"
      class="perspective-1200 w-[210px] h-[300px] flex items-center justify-center cursor-grab active:cursor-grabbing relative py-4 touch-none select-none"
      @pointerdown="onPointerDown"
      @dblclick="onDoubleTap"
      title="Drag to spin 360° • Swipe fast to flick • Double-tap to flip/reset"
    >
      <!-- 3D Book Container with Dynamic Rotation (Official 12.7 x 2.03 x 19.05 cm) -->
      <div 
        class="preserve-3d relative w-[180px] h-[270px] will-change-transform"
        :style="{
          transform: `rotateY(${rotationY}deg) rotateX(${rotationX}deg)`,
          transition: isDragging || isFlicking ? 'none' : 'transform 0.45s cubic-bezier(0.19, 1, 0.22, 1)',
        }"
      >
        <!-- FRONT COVER -->
        <div 
          class="absolute inset-0 rounded-l-sm overflow-hidden bg-[#181a26] shadow-elevation-3 border-l border-t border-b border-white/10 backface-hidden"
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
          <!-- Front Cover Gloss -->
          <div 
            class="absolute inset-0 cover-gloss"
            :style="{
              opacity: Math.max(0.1, Math.min(0.6, (1 - Math.cos((rotationY * Math.PI) / 180)) * 0.4))
            }"
          ></div>
        </div>

        <!-- BACK COVER (180deg) -->
        <div 
          class="absolute inset-0 rounded-r-sm overflow-hidden bg-[#13151f] shadow-elevation-3 border-r border-t border-b border-white/10 backface-hidden"
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

        <!-- FORE-EDGE (Left Face - Paper Pages Block in Manga Orientation) -->
        <div 
          class="absolute top-0 bottom-0 w-[28.8px] overflow-hidden paper-block-pattern shadow-inner"
          :style="{
            left: 'calc(50% - 14.4px)',
            transform: 'rotateY(-90deg) translateZ(90px)',
          }"
        >
          <!-- Inset page edge shadows -->
          <div class="absolute inset-y-0 left-0 w-1 bg-black/30"></div>
          <div class="absolute inset-y-0 right-0 w-1 bg-black/30"></div>
        </div>

        <!-- SPINE (Right Face - Official 2.03cm / 28.8px - Authentic Japanese Manga Orientation) -->
        <div 
          class="absolute top-0 bottom-0 w-[28.8px] overflow-hidden flex flex-col justify-between text-center bg-white"
          :style="{
            left: 'calc(50% - 14.4px)',
            transform: 'rotateY(90deg) translateZ(90px)',
          }"
        >
          <!-- Authentic Reconstructed Jump Comics Manga Spine -->
          <MangaSpine :volume-number="volume.volumeNumber" />
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
          class="absolute bottom-1 bg-black/75 backdrop-blur-md border border-white/10 text-[9px] text-slate-300 px-2.5 py-0.5 rounded-full pointer-events-none flex items-center gap-1.5 shadow-sm"
        >
          <svg class="w-2.5 h-2.5 text-sky-400 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
          <span>Drag or flick 360° • Double-tap to flip</span>
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
import MangaSpine from './MangaSpine.vue';

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

// 3D Physics, Touch & Flick Engine State
const stageRef = ref(null);
const rotationY = ref(-22); // Default isometric aesthetic angle showing cover and right spine
const rotationX = ref(0);
const isDragging = ref(false);
const isFlicking = ref(false);
const hasInteracted = ref(false);

let startX = 0;
let startY = 0;
let initialRotY = -22;
let initialRotX = 0;
let lastPointerX = 0;
let lastPointerTime = 0;
let velocityHistory = [];
let dragDistance = 0;
let lastTapTime = 0;
let flickVelocity = 0;
let rafId = null;

function onPointerDown(e) {
  isDragging.value = true;
  isFlicking.value = false;
  hasInteracted.value = true;
  if (rafId) cancelAnimationFrame(rafId);

  // Prevent unwanted page scrolling during 3D book interaction
  e.preventDefault();

  try {
    e.currentTarget?.setPointerCapture?.(e.pointerId);
  } catch (_) {}

  const now = performance.now();
  startX = e.clientX;
  startY = e.clientY;
  lastPointerX = e.clientX;
  lastPointerTime = now;
  initialRotY = rotationY.value;
  initialRotX = rotationX.value;
  velocityHistory = [];
  dragDistance = 0;

  window.addEventListener('pointermove', onPointerMove, { passive: false });
  window.addEventListener('pointerup', onPointerUp);
  window.addEventListener('pointercancel', onPointerCancel);
}

function onPointerMove(e) {
  if (!isDragging.value) return;
  e.preventDefault();

  const now = performance.now();
  const deltaX = e.clientX - startX;
  const deltaY = e.clientY - startY;
  dragDistance = Math.hypot(deltaX, deltaY);

  // Track velocity over rolling time window (last 100ms)
  const dt = now - lastPointerTime;
  if (dt > 6) {
    const dx = e.clientX - lastPointerX;
    const v = dx / dt; // pixels per ms
    velocityHistory.push({ v, t: now });
    if (velocityHistory.length > 5) velocityHistory.shift();
    lastPointerX = e.clientX;
    lastPointerTime = now;
  }

  // Responsive 1.4x multiplier: nimble, lightweight, and natural on high-density mobile screens
  rotationY.value = (initialRotY + deltaX * 1.4) % 360;

  // Subtle vertical tilt clamped between -15° and +15°
  const tilt = initialRotX - deltaY * 0.22;
  rotationX.value = Math.max(-15, Math.min(15, tilt));
}

function onPointerUp(e) {
  if (!isDragging.value) return;
  isDragging.value = false;

  window.removeEventListener('pointermove', onPointerMove);
  window.removeEventListener('pointerup', onPointerUp);
  window.removeEventListener('pointercancel', onPointerCancel);

  try {
    e.currentTarget?.releasePointerCapture?.(e.pointerId);
  } catch (_) {}

  const now = performance.now();

  // If minimal movement, check for tap / double tap
  if (dragDistance < 8) {
    const timeSinceLastTap = now - lastTapTime;
    lastTapTime = now;
    if (timeSinceLastTap < 330) {
      onDoubleTap();
      return;
    }
  }

  // Calculate release velocity from the rolling history
  const recentSamples = velocityHistory.filter(s => now - s.t < 120);
  let avgVelocity = 0;
  if (recentSamples.length > 0) {
    const sum = recentSamples.reduce((acc, cur) => acc + cur.v, 0);
    avgVelocity = sum / recentSamples.length;
  }

  // If swiped fast (flick momentum):
  if (Math.abs(avgVelocity) > 0.16) {
    isFlicking.value = true;
    flickVelocity = avgVelocity * 18;
    // Cap maximum flick angular velocity to keep motion comfortable
    flickVelocity = Math.max(-32, Math.min(32, flickVelocity));
    startFlickInertia();
  } else {
    springRelaxTilt();
  }
}

function onPointerCancel(e) {
  onPointerUp(e);
}

function startFlickInertia() {
  if (Math.abs(flickVelocity) > 0.15) {
    rotationY.value = (rotationY.value + flickVelocity) % 360;
    flickVelocity *= 0.935; // Friction factor
    rotationX.value *= 0.88; // Tilt relaxation
    rafId = requestAnimationFrame(startFlickInertia);
  } else {
    isFlicking.value = false;
    flickVelocity = 0;
    springRelaxTilt();
  }
}

function springRelaxTilt() {
  if (Math.abs(rotationX.value) > 0.3) {
    rotationX.value *= 0.82;
    rafId = requestAnimationFrame(springRelaxTilt);
  } else {
    rotationX.value = 0;
  }
}

function onDoubleTap() {
  hasInteracted.value = true;
  isFlicking.value = false;
  if (rafId) cancelAnimationFrame(rafId);

  // Subtle mobile haptic feedback if supported
  if (typeof navigator !== 'undefined' && navigator.vibrate) {
    try { navigator.vibrate(15); } catch (_) {}
  }

  // Normalize current angle into [-180, 180]
  let norm = ((rotationY.value % 360) + 360) % 360;
  if (norm > 180) norm -= 360;

  // If not near default front (-22deg), reset smoothly to front
  // If already at front (-22deg), flip to back (158deg)
  // If at back, flip back to front
  if (Math.abs(norm - (-22)) > 28 && Math.abs(norm - 158) > 28) {
    rotationY.value = -22;
    rotationX.value = 0;
  } else if (Math.abs(norm - (-22)) <= 28) {
    rotationY.value = 158;
    rotationX.value = 0;
  } else {
    rotationY.value = -22;
    rotationX.value = 0;
  }
}

function resetRotation() {
  onDoubleTap();
}

function toggleFlip() {
  onDoubleTap();
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
