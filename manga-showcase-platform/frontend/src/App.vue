<template>
  <div class="min-h-screen bg-[#0a0c12] text-[#e1e2ec] flex flex-col selection:bg-sky-500/30 selection:text-sky-200 relative overflow-x-hidden">
    
    <!-- Dynamic Saga Ambient Glow & Floating Particles -->
    <div 
      class="fixed inset-0 pointer-events-none z-0 overflow-hidden transition-all duration-700"
      :style="{
        background: `radial-gradient(circle at 50% 5%, ${activeSagaColor}18 0%, transparent 65%)`
      }"
    >
      <div 
        v-for="p in ambientParticles" 
        :key="p.id"
        class="absolute rounded-full pointer-events-none animate-pulse opacity-40 transition-colors duration-700"
        :style="{
          left: `${p.x}%`,
          top: `${p.y}%`,
          width: `${p.size}px`,
          height: `${p.size}px`,
          backgroundColor: activeSagaColor,
          boxShadow: `0 0 10px ${activeSagaColor}`,
        }"
      ></div>
    </div>
    
    <!-- TOP MD3 APP BAR / HEADER -->
    <header class="sticky top-0 z-40 glass-nav">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row items-center justify-between gap-4">
        
        <!-- Brand & Title -->
        <div class="flex items-center justify-between w-full md:w-auto gap-4">
          <div class="flex items-center gap-3 cursor-pointer" @click="resetFilters">
            <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-amber-400 via-rose-500 to-indigo-600 p-[1.5px] shadow-lg shadow-rose-500/20">
              <div class="w-full h-full bg-[#14161f] rounded-[14px] flex items-center justify-center">
                <span class="text-xl">☠️</span>
              </div>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h1 class="text-lg font-extrabold text-white tracking-wider font-outfit uppercase">
                  ONE PIECE
                </h1>
                <span class="text-[9px] px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 font-mono font-semibold border border-sky-500/30">
                  MD3 SHOWCASE
                </span>
              </div>
              <p class="text-[11px] text-slate-400 font-medium">3D FlipBook & Canon Manga Library</p>
            </div>
          </div>

          <!-- Mobile Actions -->
          <div class="flex items-center gap-2 md:hidden">
            <button 
              type="button"
              @click="libraryStore.toggleStorageModal()"
              class="p-2 rounded-full bg-white/[0.06] text-slate-300 hover:text-white relative"
              title="Manage Offline Downloads"
            >
              <svg class="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" x2="12" y1="15" y2="3" />
              </svg>
              <span v-if="libraryStore.cachedStorageInfo?.count > 0" class="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 text-[9px] font-bold rounded-full flex items-center justify-center text-white">
                {{ libraryStore.cachedStorageInfo.count }}
              </span>
            </button>
            <button 
              type="button"
              @click="libraryStore.toggleLocalDropzone()"
              class="p-2 rounded-full bg-white/[0.06] text-slate-300 hover:text-white"
              title="Open Local CBZ"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" x2="12" y1="3" y2="15" />
              </svg>
            </button>
            <button 
              type="button"
              @click="libraryStore.toggleHistoryDrawer()"
              class="p-2 rounded-full bg-white/[0.06] text-slate-300 hover:text-white relative"
              title="Reading History"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 8v4l3 3" />
                <circle cx="12" cy="12" r="9" />
              </svg>
              <span v-if="progressStore.totalVolumesRead > 0" class="absolute -top-1 -right-1 w-4 h-4 bg-sky-500 text-[9px] font-bold rounded-full flex items-center justify-center text-white">
                {{ progressStore.totalVolumesRead }}
              </span>
            </button>
          </div>
        </div>

        <!-- Center: Search Input -->
        <div class="w-full md:max-w-md relative">
          <div class="relative flex items-center">
            <svg class="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            <input 
              type="text" 
              v-model="libraryStore.searchQuery"
              placeholder="Search volumes, arcs, chapters (e.g. 'Romance Dawn', 'Vol 1')..."
              class="w-full pl-10 pr-9 py-2 bg-[#1d202d]/90 border border-white/10 rounded-full text-xs text-white placeholder-slate-400 focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400 transition-all shadow-inner"
            />
            <button 
              v-if="libraryStore.searchQuery"
              @click="libraryStore.searchQuery = ''"
              class="absolute right-3 text-slate-400 hover:text-white"
            >
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Right: Actions, Local CBZ, History & View Switcher -->
        <div class="hidden md:flex items-center gap-3">
          <!-- Offline Storage Trigger -->
          <button 
            type="button"
            @click="libraryStore.toggleStorageModal()"
            class="px-3.5 py-1.5 rounded-full text-xs font-semibold bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 border border-white/10 flex items-center gap-2 transition-all md-state-layer relative"
            title="Manage Offline Downloads & Storage Cache"
          >
            <svg class="w-3.5 h-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" x2="12" y1="15" y2="3" />
            </svg>
            <span>Downloads</span>
            <span v-if="libraryStore.cachedStorageInfo?.count > 0" class="px-1.5 py-0.2 rounded-full bg-emerald-500/80 text-[10px] font-bold text-white font-mono">
              {{ libraryStore.cachedStorageInfo.count }}
            </span>
          </button>

          <!-- Local Dropzone Trigger -->
          <button 
            type="button"
            @click="libraryStore.toggleLocalDropzone()"
            class="px-3.5 py-1.5 rounded-full text-xs font-semibold bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 border border-white/10 flex items-center gap-2 transition-all md-state-layer"
            title="Read any local CBZ directly in your browser"
          >
            <svg class="w-3.5 h-3.5 text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" x2="12" y1="3" y2="15" />
            </svg>
            <span>Local CBZ</span>
          </button>

          <!-- History Drawer Trigger -->
          <button 
            type="button"
            @click="libraryStore.toggleHistoryDrawer()"
            class="px-3.5 py-1.5 rounded-full text-xs font-semibold bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 border border-white/10 flex items-center gap-2 transition-all md-state-layer relative"
            title="Reading Progress History"
          >
            <svg class="w-3.5 h-3.5 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 8v4l3 3" />
              <circle cx="12" cy="12" r="9" />
            </svg>
            <span>History</span>
            <span v-if="progressStore.totalVolumesRead > 0" class="px-1.5 py-0.2 rounded-full bg-purple-500 text-[10px] font-bold text-white font-mono">
              {{ progressStore.totalVolumesRead }}
            </span>
          </button>

          <!-- Segmented View Switcher (Grid vs List) -->
          <ViewSwitcher v-model="libraryStore.viewMode" />
        </div>
      </div>

      <!-- SAGA FILTER CHIP CAROUSEL -->
      <div class="border-t border-white/[0.06] bg-[#10121a]/80 backdrop-blur-md">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex items-center gap-2 overflow-x-auto no-scrollbar text-xs">
          <!-- All Sagas Chip -->
          <button 
            type="button"
            @click="libraryStore.setActiveSagaFilter('all')"
            :class="[
              'px-3.5 py-1 rounded-full font-semibold shrink-0 transition-all md-state-layer',
              libraryStore.activeSagaFilter === 'all'
                ? 'bg-[#a8c7fa] text-[#042b5c] shadow-sm font-bold'
                : 'bg-white/[0.05] text-slate-400 hover:text-white hover:bg-white/[0.09]'
            ]"
          >
            All Sagas ({{ libraryStore.totalVolumeCount }})
          </button>

          <!-- Individual Saga Chips -->
          <button 
            v-for="saga in libraryStore.sagas" 
            :key="saga.id"
            type="button"
            @click="libraryStore.setActiveSagaFilter(saga.id)"
            :class="[
              'px-3 py-1 rounded-full shrink-0 transition-all md-state-layer flex items-center gap-1.5 font-medium',
              libraryStore.activeSagaFilter === saga.id
                ? 'bg-white text-slate-950 font-bold shadow-sm'
                : 'bg-white/[0.04] text-slate-400 hover:text-slate-200 hover:bg-white/[0.08]'
            ]"
          >
            <span 
              class="w-2 h-2 rounded-full"
              :style="{ backgroundColor: saga.themeColor || '#38bdf8' }"
            ></span>
            <span>{{ saga.name.replace(' Saga', '') }}</span>
          </button>
        </div>
      </div>
    </header>

    <!-- HERO PROMOTIONAL BANNER -->
    <section v-if="!libraryStore.searchQuery && libraryStore.activeSagaFilter === 'all'" class="relative overflow-hidden bg-gradient-to-b from-[#14161f] via-[#0f1118] to-[#0a0c12] border-b border-white/[0.06] py-12 sm:py-16">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 flex flex-col lg:flex-row items-center justify-between gap-10">
        
        <!-- Left Hero Copy -->
        <div class="max-w-2xl text-center lg:text-left">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold mb-4">
            <span class="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
            <span>Eiichiro Oda Masterpiece Showcase</span>
          </div>

          <h2 class="text-3xl sm:text-5xl lg:text-6xl font-black text-white font-outfit tracking-tight leading-none uppercase">
            THE GRAND LINE <span class="bg-gradient-to-r from-[#a8c7fa] via-[#d0bcff] to-[#f472b6] bg-clip-text text-transparent">CHRONICLES</span>
          </h2>

          <p class="text-sm sm:text-base text-slate-300 mt-4 leading-relaxed font-normal">
            Immerse yourself in the legendary story of Monkey D. Luffy. Experience every canon volume with hardware-accelerated 360° swipe-to-spin 3D book models, authentic Japanese Right-to-Left physical page-turning, and vertical Webtoon scroll.
          </p>

          <!-- Quick Stats Pill Row -->
          <div class="flex flex-wrap items-center justify-center lg:justify-start gap-4 mt-6 text-xs text-slate-400">
            <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl bg-white/[0.04] border border-white/5">
              <span class="text-white font-bold font-mono">108+</span>
              <span>Canon Volumes</span>
            </div>
            <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl bg-white/[0.04] border border-white/5">
              <span class="text-white font-bold font-mono">1,120+</span>
              <span>Chapters</span>
            </div>
            <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl bg-white/[0.04] border border-white/5">
              <span class="text-white font-bold font-mono">11</span>
              <span>Epic Sagas</span>
            </div>
          </div>

          <!-- Hero Action CTAs -->
          <div class="flex flex-wrap items-center justify-center lg:justify-start gap-3 mt-8">
            <!-- Resume Reading Hero CTA if reading progress exists -->
            <button 
              v-if="progressStore.mostRecentVolume"
              type="button"
              @click="resumeLastRead"
              class="px-6 py-3 rounded-full bg-gradient-to-r from-amber-500 via-rose-500 to-indigo-600 hover:opacity-95 text-white font-bold text-sm flex items-center gap-2 shadow-elevation-3 transition-all md-state-layer border border-amber-300/30"
              title="Resume reading from your last active page"
            >
              <svg class="w-4 h-4 text-amber-200" viewBox="0 0 24 24" fill="currentColor">
                <path d="M5 3l14 9-14 9V3z" />
              </svg>
              <span>Resume Reading ({{ resumeButtonLabel }})</span>
            </button>

            <button 
              type="button"
              @click="startAdventure"
              class="px-6 py-3 rounded-full bg-[#0842a0] hover:bg-[#0b57d0] text-white font-bold text-sm flex items-center gap-2 shadow-elevation-2 transition-all md-state-layer"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M5 3l14 9-14 9V3z" />
              </svg>
              <span>Begin Adventure (Vol. 1)</span>
            </button>

            <button 
              type="button"
              @click="libraryStore.toggleLocalDropzone()"
              class="px-5 py-3 rounded-full bg-white/[0.08] hover:bg-white/[0.14] text-white font-semibold text-sm flex items-center gap-2 border border-white/10 transition-all md-state-layer"
            >
              <svg class="w-4 h-4 text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" x2="12" y1="3" y2="15" />
              </svg>
              <span>Read Local CBZ</span>
            </button>
          </div>
        </div>

        <!-- Right Hero 3D Showcase Volume -->
        <div class="shrink-0 flex items-center justify-center py-4" v-if="libraryStore.volumes.length > 0">
          <VolumeCard3D :volume="libraryStore.volumes[0]" />
        </div>
      </div>
    </section>

    <!-- MAIN DASHBOARD CONTENT -->
    <main class="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full">
      
      <!-- Search Filter Results Indicator -->
      <div v-if="libraryStore.searchQuery" class="mb-8 flex items-center justify-between">
        <div>
          <h2 class="text-xl font-bold text-white font-outfit">
            Search Results for "{{ libraryStore.searchQuery }}"
          </h2>
          <p class="text-xs text-slate-400 mt-0.5">Found {{ libraryStore.filteredVolumes.length }} matching volumes</p>
        </div>

        <button 
          type="button"
          @click="libraryStore.searchQuery = ''"
          class="text-xs text-sky-400 hover:text-sky-300 underline"
        >
          Clear Search
        </button>
      </div>

      <!-- 3D Bookshelf View Mode -->
      <template v-if="libraryStore.viewMode === 'shelf'">
        <ShelfView3D :volumes="libraryStore.filteredVolumes" />
      </template>

      <!-- Arc-Separated Storyline Sections (Grid and List modes) -->
      <template v-else-if="libraryStore.groupedBySaga.length > 0">
        <ArcSection 
          v-for="group in libraryStore.groupedBySaga" 
          :key="group.saga.id"
          :saga="group.saga"
          :volumes="group.volumes"
          :viewMode="libraryStore.viewMode"
        />
      </template>

      <!-- Empty Filter State -->
      <div v-else class="text-center py-20 glass-card rounded-3xl p-8 max-w-lg mx-auto">
        <div class="w-16 h-16 rounded-full bg-white/[0.04] text-slate-500 flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
        </div>
        <h3 class="text-lg font-bold text-white font-outfit">No Volumes Found</h3>
        <p class="text-xs text-slate-400 mt-2 max-w-xs mx-auto">
          No manga volumes match your current filter query. Try searching for a different volume title or resetting filters.
        </p>
        <button 
          type="button"
          @click="resetFilters"
          class="mt-5 px-5 py-2 rounded-full bg-sky-500/20 text-sky-300 font-semibold text-xs border border-sky-500/30"
        >
          Reset All Filters
        </button>
      </div>
    </main>

    <!-- FOOTER -->
    <footer class="border-t border-white/[0.06] bg-[#0c0e15] py-10 mt-20 text-slate-400 text-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="flex items-center gap-3">
          <span class="text-2xl">🏴‍☠️</span>
          <div>
            <p class="text-slate-300 font-bold">Material Design 3 Manga Showcase & FlipBook Platform</p>
            <p class="text-[11px] text-slate-500">One Piece © Eiichiro Oda / Shueisha. Built for showcase and personal archive use.</p>
          </div>
        </div>

        <div class="flex items-center gap-4 text-[11px] text-slate-400">
          <span>Static SPA for GitHub Pages</span>
          <span>•</span>
          <span>JSZip In-Memory Streamer</span>
          <span>•</span>
          <span>3D StPageFlip RTL Engine</span>
        </div>
      </div>
    </footer>

    <!-- ========================================================================= -->
    <!-- FULLSCREEN READING ENGINE OVERLAY                                         -->
    <!-- ========================================================================= -->
    <div 
      v-if="libraryStore.isReading && libraryStore.activePages.length > 0"
      class="fixed inset-0 z-50 bg-black flex flex-col select-none overflow-hidden"
    >
      <!-- Floating MD3 HUD Controls -->
      <ReaderControls 
        :title="libraryStore.activeVolume?.title"
        :subtitle="readerSubtitle"
        :currentPage="currentReadingPage"
        :totalPages="libraryStore.activePages.length"
        :currentMode="progressStore.readMode"
        :readingDirection="progressStore.readingDirection"
        :spreadMode="progressStore.spreadMode"
        :isRotated="progressStore.isRotatedLandscape"
        :isBookmarked="isCurrentPageBookmarked"
        :isVisible="isHudVisible"
        @exit="exitReader"
        @jump-page="jumpToPage"
        @update:currentMode="onReaderModeChanged"
        @update:readingDirection="onReaderDirectionChanged"
        @toggle-spread-mode="progressStore.toggleSpreadMode()"
        @toggle-rotation="toggleScreenRotation"
        @toggle-zoom="onToggleZoom"
        @toggle-bookmark="toggleCurrentBookmark"
      />

      <!-- Dual Reading Engine Views -->
      <div class="flex-1 w-full h-full relative overflow-hidden">
        <!-- Mode 1: 3D FlipBook (StPageFlip RTL / LTR) -->
        <FlipBookView 
          v-if="progressStore.readMode === 'flipbook'"
          ref="flipBookRef"
          :key="`flipbook-${libraryStore.activeVolume?.id || 'vol'}-${progressStore.readingDirection}-${progressStore.spreadMode}-${progressStore.isRotatedLandscape}`"
          :pages="libraryStore.activePages"
          :readingDirection="progressStore.readingDirection"
          :spreadMode="progressStore.spreadMode"
          :isRotated="progressStore.isRotatedLandscape"
          :initialPage="currentReadingPage"
          @page-change="onPageChange"
          @toggle-hud="toggleHud"
        />

        <!-- Mode 2: Webtoon Continuous Vertical Scroll -->
        <WebtoonView 
          v-else
          ref="webtoonRef"
          :key="`webtoon-${libraryStore.activeVolume?.id || 'vol'}`"
          :pages="libraryStore.activePages"
          :initialPage="currentReadingPage"
          @page-change="onPageChange"
          @toggle-hud="toggleHud"
        />
      </div>
    </div>

    <!-- UNPACKING / LOADING MODAL -->
    <div 
      v-if="libraryStore.isUnpacking"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md"
    >
      <div class="glass-card rounded-3xl p-6 sm:p-8 max-w-sm w-full text-center border border-white/10 shadow-elevation-4">
        <!-- Animated Manga Icon -->
        <div class="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/30 text-sky-400 flex items-center justify-center mx-auto mb-4 animate-pulse">
          <svg class="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
          </svg>
        </div>

        <h3 class="text-base font-bold text-white font-outfit">Unpacking Manga Volume</h3>
        <p class="text-xs text-slate-400 mt-1 mb-4">{{ libraryStore.unpackStatusText || 'Extracting CBZ archive in memory...' }}</p>

        <!-- Progress Bar -->
        <ProgressBarMD3 :value="libraryStore.unpackProgress" :height="6" :showLabel="true" />
      </div>
    </div>

    <!-- ERROR ALERT MODAL -->
    <div 
      v-if="libraryStore.unpackError"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md"
    >
      <div class="glass-card rounded-3xl p-6 sm:p-8 max-w-md w-full border border-rose-500/30 shadow-elevation-4 text-center">
        <div class="w-12 h-12 rounded-2xl bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto mb-3">
          <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" x2="12" y1="8" y2="12" />
            <line x1="12" x2="12.01" y1="16" y2="16" />
          </svg>
        </div>
        <h3 class="text-base font-bold text-white font-outfit">Volume Notice</h3>
        <p class="text-xs text-slate-300 mt-2 leading-relaxed">{{ libraryStore.unpackError }}</p>

        <div class="flex items-center justify-center gap-3 mt-6">
          <button 
            type="button"
            @click="libraryStore.unpackError = null"
            class="px-4 py-2 rounded-full text-xs font-semibold bg-white/10 hover:bg-white/20 text-white"
          >
            Close
          </button>
          <button 
            type="button"
            @click="openDropzoneFromError"
            class="px-4 py-2 rounded-full text-xs font-semibold bg-sky-500 hover:bg-sky-600 text-white"
          >
            Drop Local CBZ File
          </button>
        </div>
      </div>
    </div>

    <!-- DRAWERS & MODALS -->
    <LocalDropzone 
      :isOpen="libraryStore.localDropzoneOpen" 
      @close="libraryStore.localDropzoneOpen = false" 
    />

    <HistoryDrawer 
      :isOpen="libraryStore.historyDrawerOpen" 
      @close="libraryStore.historyDrawerOpen = false" 
    />

    <OfflineStorageModal 
      :isOpen="libraryStore.storageModalOpen" 
      @close="libraryStore.storageModalOpen = false" 
    />

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useLibraryStore } from './stores/library.js';
import { useProgressStore } from './stores/progress.js';

import ArcSection from './components/Dashboard/ArcSection.vue';
import VolumeCard3D from './components/Dashboard/VolumeCard3D.vue';
import ViewSwitcher from './components/Dashboard/ViewSwitcher.vue';
import ShelfView3D from './components/Dashboard/ShelfView3D.vue';
import FlipBookView from './components/Reader/FlipBookView.vue';
import WebtoonView from './components/Reader/WebtoonView.vue';
import ReaderControls from './components/Reader/ReaderControls.vue';
import LocalDropzone from './components/Reader/LocalDropzone.vue';
import HistoryDrawer from './components/UI/HistoryDrawer.vue';
import OfflineStorageModal from './components/Dashboard/OfflineStorageModal.vue';
import ProgressBarMD3 from './components/UI/ProgressBarMD3.vue';

const libraryStore = useLibraryStore();
const progressStore = useProgressStore();

const flipBookRef = ref(null);
const webtoonRef = ref(null);
const isHudVisible = ref(true);

const currentReadingPage = ref(1);

// Sync reading page when switching volumes so it resumes from that volume's own progress (or page 1)
watch(
  () => libraryStore.activeVolume?.id,
  (newId, oldId) => {
    if (newId && newId !== oldId) {
      const saved = progressStore.getProgressForVolume(newId);
      currentReadingPage.value = (saved && saved.lastPage && saved.lastPage > 0) ? saved.lastPage : 1;
    }
  },
  { immediate: true }
);

const isCurrentPageBookmarked = computed(() => {
  if (!libraryStore.activeVolume) return false;
  return progressStore.isBookmarked(libraryStore.activeVolume.id, currentReadingPage.value);
});

const readerSubtitle = computed(() => {
  const vol = libraryStore.activeVolume;
  if (!vol) return 'Manga Reader';
  if (vol.type === 'chapter') {
    return `Chapter ${vol.chapterStart || ''} • ${vol.arcName || vol.sagaName || 'Single Chapter'}`;
  }
  return `Volume ${vol.volumeNumber} • ${vol.arcName || vol.sagaName}`;
});

function onPageChange(pageNum) {
  currentReadingPage.value = pageNum;
  if (libraryStore.activeVolume) {
    const act = libraryStore.activeVolume;
    progressStore.saveProgress(
      act.id,
      pageNum,
      libraryStore.activePages.length,
      act.chapterStart,
      {
        title: act.title,
        type: act.type || (act.isRealVolume ? 'volume' : (act.id.includes('chapter') ? 'chapter' : 'volume')),
        coverUrl: act.coverUrl,
        fileName: act.fileName,
      }
    );
  }
}

function jumpToPage(pageNum) {
  currentReadingPage.value = pageNum;
  if (progressStore.readMode === 'flipbook' && flipBookRef.value) {
    flipBookRef.value.jumpToPage(pageNum);
  } else if (progressStore.readMode === 'webtoon' && webtoonRef.value) {
    webtoonRef.value.jumpToPage(pageNum);
  }
}

function onReaderModeChanged(mode) {
  progressStore.setReadMode(mode);
}

function onReaderDirectionChanged(dir) {
  progressStore.setReadingDirection(dir);
}

function toggleCurrentBookmark() {
  if (libraryStore.activeVolume) {
    progressStore.toggleBookmark(libraryStore.activeVolume.id, currentReadingPage.value);
  }
}

function toggleHud() {
  isHudVisible.value = !isHudVisible.value;
}

function exitReader() {
  libraryStore.closeReader();
  currentReadingPage.value = 1;
}

function openDropzoneFromError() {
  libraryStore.unpackError = null;
  libraryStore.localDropzoneOpen = true;
}

function resetFilters() {
  libraryStore.activeSagaFilter = 'all';
  libraryStore.searchQuery = '';
}

function startAdventure() {
  if (libraryStore.volumes.length > 0) {
    libraryStore.openReader(libraryStore.volumes[0]);
  }
}

const resumeButtonLabel = computed(() => {
  const rec = progressStore.mostRecentVolume;
  if (!rec) return '';
  if (rec.type === 'chapter') {
    return `Ch. ${rec.lastChapter || 'Latest'} • p.${rec.lastPage}`;
  }
  const vol = libraryStore.volumes.find(v => v.id === rec.volumeId);
  const volNum = vol ? vol.volumeNumber : rec.volumeId.replace(/\D/g, '');
  return `Vol. ${volNum || 1} • p.${rec.lastPage}`;
});

async function resumeLastRead() {
  const rec = progressStore.mostRecentVolume;
  if (!rec) return;
  const vol = libraryStore.volumes.find(v => v.id === rec.volumeId);
  if (vol) {
    await libraryStore.openReader(vol);
  } else if (libraryStore.volumes.length > 0) {
    startAdventure();
  }
}

async function toggleScreenRotation() {
  progressStore.toggleVirtualRotation();
  if (typeof screen !== 'undefined' && screen.orientation) {
    try {
      if (progressStore.isRotatedLandscape && screen.orientation.lock) {
        await screen.orientation.lock('landscape');
      } else if (!progressStore.isRotatedLandscape && screen.orientation.unlock) {
        await screen.orientation.unlock();
      }
    } catch (e) {
      // Ignored if browser rejects orientation lock
    }
  }
}

function onToggleZoom() {
  if (flipBookRef.value && flipBookRef.value.toggleZoom) {
    flipBookRef.value.toggleZoom();
  }
}

function onGlobalKeydown(e) {
  if (!libraryStore.isReading) return;
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

  const key = e.key.toLowerCase();
  if (key === 'd') {
    progressStore.toggleSpreadMode();
  } else if (key === 'o') {
    toggleScreenRotation();
  } else if (key === 'z') {
    onToggleZoom();
  } else if (key === 'm') {
    progressStore.setReadMode(progressStore.readMode === 'flipbook' ? 'webtoon' : 'flipbook');
  } else if (key === 'r') {
    progressStore.setReadingDirection(progressStore.readingDirection === 'rtl' ? 'ltr' : 'rtl');
  } else if (key === 'b') {
    toggleCurrentBookmark();
  } else if (key === 'h') {
    toggleHud();
  } else if (e.key === 'Escape') {
    exitReader();
  }
}

const activeSagaColor = computed(() => {
  if (!libraryStore.activeSagaFilter || libraryStore.activeSagaFilter === 'all') {
    return '#38bdf8';
  }
  const saga = libraryStore.sagas.find(s => s.id === libraryStore.activeSagaFilter);
  return saga?.themeColor || '#38bdf8';
});

const ambientParticles = Array.from({ length: 16 }, (_, i) => ({
  id: i,
  x: Math.floor(Math.random() * 94) + 3,
  y: Math.floor(Math.random() * 88) + 6,
  size: Math.floor(Math.random() * 5) + 3,
}));

onMounted(() => {
  libraryStore.loadCatalog();
  libraryStore.refreshStorageInfo();
  window.addEventListener('keydown', onGlobalKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown);
});
</script>
