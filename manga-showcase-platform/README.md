# 🏴‍☠️ Material Design 3 Manga Showcase & 3D Interactive FlipBook Platform

A decoupled manga showcase platform and local ingestion engine built for canon One Piece volume bundling, ComicRack metadata compliance, and interactive 3D reading.

![One Piece Showcase](frontend/public/assets/arcs/east-blue.webp)

---

## 🌟 Key Highlights

- **360° Interactive 3D Volume Cards (`VolumeCard3D.vue`)**:
  Pure hardware-accelerated CSS 3D transforms (`preserve-3d`, backface-culling, specular highlights, dynamic cast shadows, realistic multi-ply fore-edge paper block texture). Touch and pointer drag tracking allows users to spin any volume 360° across the Y-axis with smooth inertia damping.
- **Dual Reading Engines**:
  - **3D FlipBook (`FlipBookView.vue`)**: Realistic paper-turning physics powered by `StPageFlip` (`page-flip`) with authentic Japanese **Right-to-Left (RTL)** manga mode.
  - **Webtoon Mode (`WebtoonView.vue`)**: Seamless vertical continuous scroll with floating page pill indicator and viewport IntersectionObserver tracking.
- **Client-Side In-Memory CBZ Extraction (`cbzLoader.js`)**:
  Unpacks `.cbz` and `.zip` archives directly in browser memory via JSZip and converts pages into temporary Blob URLs. Automatically revokes previous Blobs upon navigation to prevent RAM leaks.
- **Instant Local Reader (`LocalDropzone.vue`)**:
  Drag & drop any local `.cbz` file directly from your operating system file manager to read immediately in the 3D flipbook — **100% offline, zero server uploads**.
- **Persistent Progress Store (`stores/progress.js`)**:
  Tracks last-read page, chapter, completion percentage, bookmarks, and user reading mode preference across sessions via `localStorage`.
- **Local Ingestion & Packaging Utility (`tools/`)**:
  Desktop GUI (`CustomTkinter`) and CLI tool suite that packages loose chapter folders/CBZs into official canon volume archives (`One Piece - v[Vol] (c[Start]-[End]).cbz`), injects ComicRack-compliant `ComicInfo.xml`, and synchronizes `index.json`.

---

## 📁 Project Directory Structure

```plaintext
manga-showcase-platform/
├── .gitignore                      # Strictly ignores *.cbz, *.zip, and local staging folders
├── .github/
│   └── workflows/
│       └── deploy.yml              # GitHub Actions workflow for Vite build & Pages deploy
├── tools/                          # Local Python packaging and indexing tool
│   ├── organizer_gui.py            # CustomTkinter GUI for volume bundling & metadata
│   ├── catalog_indexer.py          # Auto-generates index.json with canon Arc/Saga mappings
│   ├── comic_info.py               # Generates ComicInfo.xml metadata
│   ├── generate_banners.py         # Generates widescreen storyline banner artworks
│   └── requirements.txt            # customtkinter, pillow
├── frontend/                       # Vue 3 SPA (Deployable to GitHub Pages)
│   ├── public/
│   │   ├── comics/
│   │   │   ├── covers/             # Extracted cover thumbnails
│   │   │   └── index.json          # Master catalog manifest (volumes, chapters, arc links)
│   │   └── assets/
│   │       └── arcs/               # Storyline banner artworks for each major saga
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard/
│   │   │   │   ├── ArcSection.vue          # Centered saga banner art, title & chapter badge
│   │   │   │   ├── VolumeCard3D.vue        # 360° swipe/drag-to-spin CSS 3D book model
│   │   │   │   ├── VolumeListItem.vue      # List view layout with 3D cover on left
│   │   │   │   └── ViewSwitcher.vue        # MD3 segmented button (Grid vs List)
│   │   │   ├── Reader/
│   │   │   │   ├── FlipBookView.vue        # 3D physical book page-turning (StPageFlip)
│   │   │   │   ├── WebtoonView.vue         # Seamless vertical continuous scroll mode
│   │   │   │   ├── ReaderControls.vue      # Floating MD3 HUD (fullscreen, jump, modes)
│   │   │   │   └── LocalDropzone.vue       # Drag & drop local CBZ files for instant reading
│   │   │   └── UI/
│   │   │       ├── HistoryDrawer.vue       # Slide-over panel of recent reads & bookmarks
│   │   │       └── ProgressBarMD3.vue      # MD3 tonal progress bar
│   │   ├── stores/
│   │   │   ├── library.js                  # Pinia store for comics catalog & sagas
│   │   │   └── progress.js                 # Persistent reading progress store (localStorage)
│   │   ├── utils/
│   │   │   ├── cbzLoader.js                # In-browser JSZip unpacker & Blob URL manager
│   │   │   └── sagaData.js                 # Canon One Piece Arc/Saga taxonomy
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── style.css                       # MD3 tonal variables, glass surfaces, 3D CSS
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
└── README.md                               # Usage instructions & deployment guide
```

---

## 🛠️ Local Ingestion & Packaging Utility (`tools/`)

### 1. Requirements
Ensure Python 3.10+ is installed:
```bash
cd tools
pip install -r requirements.txt
```

### 2. Launch the Desktop GUI
Launch the modern CustomTkinter dark-mode packaging GUI:
```bash
python organizer_gui.py
```
- **Select Source**: Choose a folder containing loose chapter images or chapter files.
- **Select Volume #**: Select the volume number (e.g. `1`); canon titles, arcs, and chapter ranges will auto-populate.
- **Pack Volume CBZ**: Automatically archives images, injects `ComicInfo.xml`, and updates `index.json`.
- **Generate Demo Sample CBZ**: Creates an aesthetic demo volume for immediate showcase verification.

### 3. Headless CLI Usage
The organizer tool can also be run entirely from the command line:
```bash
# Generate a test demo volume (e.g. Volume 1)
python organizer_gui.py --sample --volume 1 --output ../frontend/public/comics

# Pack an existing folder into Volume 3
python organizer_gui.py --cli --source "D:/Manga/Chapters" --volume 3 --output ../frontend/public/comics

# Download a chapter directly from MangaPlus via viewer URL
python organizer_gui.py --mangaplus https://mangaplus.shueisha.co.jp/viewer/7002654

# Or invoke the dedicated mangaplus_downloader CLI
python mangaplus_downloader.py https://mangaplus.shueisha.co.jp/viewer/7002654 -o ../frontend/public/comics

# Sync index.json only
python catalog_indexer.py --scan ../frontend/public/comics --output ../frontend/public/comics/index.json
```

### 4. Direct MangaPlus Ingestion
MangaPlus enforces dynamic `SESSION-TOKEN` authentication headers to prevent bot bans. We provide:
- **`mangaplus_downloader.py`**: Automatically generates valid UUIDv1 session tokens, queries `https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer`, decrypts the XOR-scrambled image streams, packages the chapter into a `.cbz`, injects `ComicInfo.xml`, and updates `index.json`.
- **`mloader` Patch**: Applied automatic patch to `mloader` library to include the required `SESSION-TOKEN` header and Windows path fix, allowing the standard `mloader <URL>` command to function seamlessly.

### 4. Embedded ComicInfo.xml Schema
Archives generated adhere to the ComicRack specification:
```xml
<?xml version="1.0" encoding="utf-8"?>
<ComicInfo xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Title>Romance Dawn</Title>
  <Series>One Piece</Series>
  <Volume>1</Volume>
  <Number>1</Number>
  <StartChapter>1</StartChapter>
  <EndChapter>8</EndChapter>
  <PageCount>210</PageCount>
  <Format>Digital</Format>
  <Manga>YesAndRightToLeft</Manga>
  <Summary>Monkey D. Luffy embarks on his journey to become the Pirate King!</Summary>
  <Writer>Eiichiro Oda</Writer>
  <Publisher>Shueisha</Publisher>
  <Genre>Action, Adventure, Fantasy, Shounen</Genre>
  <LanguageISO>en</LanguageISO>
</ComicInfo>
```

---

## 💻 Frontend Web Showcase (`frontend/`)

### 1. Install & Run Locally
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` to explore the showcase.

### 2. Build for Production
```bash
npm run build
```
Generates a static SPA in `frontend/dist/` ready to be hosted on any static web server or CDN.

---

## 🚀 GitHub Pages Deployment

The repository includes a production-ready GitHub Actions workflow at [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml).

1. Push this repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Manga Showcase Platform"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
2. In your GitHub repository settings, navigate to **Settings > Pages**.
3. Under **Build and deployment > Source**, select **GitHub Actions**.
4. Every push to `main` will automatically build the static Vite bundle and deploy to GitHub Pages.

---

## 🛡️ Git Hygiene & Exclusion Policy
- Binary archives (`*.cbz`, `*.cbr`, `*.zip`) are strictly excluded by [`.gitignore`](.gitignore).
- Staging and temporary folders (`staging/`, `temp/`, `dist/`, `node_modules/`) are completely ignored.
- Only manifests (`index.json`), extracted lightweight cover thumbnails, and code are committed to Git.
