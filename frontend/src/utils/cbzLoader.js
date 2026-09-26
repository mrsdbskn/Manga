/**
 * cbzLoader.js - In-browser client-side JSZip unpacker & Blob URL manager.
 * Unpacks .cbz/.zip archives in memory, parses ComicInfo.xml, and converts page images
 * to Blob URLs for instantaneous local reading without server uploads.
 * Automatically revokes previous object URLs to prevent RAM memory leaks.
 */

import JSZip from 'jszip';

// Track currently active blob URLs for safe memory disposal
let activeBlobUrls = [];

/**
 * Natural sort comparator for filenames (e.g. page_2 before page_10)
 */
function naturalSortComparator(a, b) {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
}

/**
 * Revokes all previously allocated Blob URLs from browser memory.
 */
export function revokeAllocatedBlobs() {
  if (activeBlobUrls.length > 0) {
    activeBlobUrls.forEach(url => {
      try {
        URL.revokeObjectURL(url);
      } catch (e) {
        console.warn('Error revoking blob URL:', e);
      }
    });
    activeBlobUrls = [];
  }
}

/**
 * Parses raw ComicInfo.xml text into a structured metadata object.
 */
export function parseComicInfoXml(xmlText) {
  if (!xmlText) return null;
  try {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
    const getTag = (tag) => {
      const el = xmlDoc.getElementsByTagName(tag)[0];
      return el ? el.textContent.trim() : null;
    };

    return {
      title: getTag('Title'),
      series: getTag('Series'),
      volume: getTag('Volume'),
      number: getTag('Number'),
      startChapter: getTag('StartChapter'),
      endChapter: getTag('EndChapter'),
      pageCount: getTag('PageCount'),
      format: getTag('Format'),
      manga: getTag('Manga'),
      summary: getTag('Summary'),
      writer: getTag('Writer'),
      publisher: getTag('Publisher'),
      genre: getTag('Genre'),
    };
  } catch (err) {
    console.warn('Failed to parse ComicInfo.xml:', err);
    return null;
  }
}

/**
 * Unpacks a CBZ archive from a File (drag & drop) or ArrayBuffer/Fetch URL.
 * 
 * @param {File | Blob | ArrayBuffer} sourceData - The raw CBZ binary data
 * @param {Function} [onProgress] - Optional progress callback (percent: number, status: string)
 * @returns {Promise<{ pages: Array<{ pageNumber: number, url: string, name: string }>, comicInfo: Object | null, totalPages: number }>}
 */
export async function unpackCbz(sourceData, onProgress = () => {}) {
  // Free any previous volume blobs before loading new volume
  revokeAllocatedBlobs();

  onProgress(10, 'Opening comic archive...');
  const zip = new JSZip();
  let zipContent;

  try {
    zipContent = await zip.loadAsync(sourceData);
  } catch (err) {
    throw new Error('Could not open archive. Ensure it is a valid .cbz or .zip file.');
  }

  onProgress(30, 'Scanning manga pages & metadata...');

  // Check for ComicInfo.xml
  let comicInfo = null;
  const comicInfoFile = Object.values(zipContent.files).find(
    f => !f.dir && f.name.toLowerCase().endsWith('comicinfo.xml')
  );

  if (comicInfoFile) {
    try {
      const xmlText = await comicInfoFile.async('text');
      comicInfo = parseComicInfoXml(xmlText);
    } catch (e) {
      console.warn('Notice: ComicInfo.xml read error:', e);
    }
  }

  // Check for Table of Contents (toc.json)
  let toc = null;
  const tocFile = Object.values(zipContent.files).find(
    f => !f.dir && f.name.toLowerCase().endsWith('toc.json')
  );
  if (tocFile) {
    try {
      const tocText = await tocFile.async('text');
      const tocJson = JSON.parse(tocText);
      toc = tocJson.chapters || [];
    } catch (e) {
      console.warn('Notice: toc.json read error:', e);
    }
  }

  // Filter image files (jpg, jpeg, png, webp, avif, gif)
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.webp', '.avif', '.gif'];
  const imageEntries = Object.values(zipContent.files).filter(entry => {
    if (entry.dir) return false;
    const lower = entry.name.toLowerCase();
    // Exclude MacOS metadata and hidden files
    if (lower.includes('__macosx') || lower.startsWith('.') || lower.includes('/.')) return false;
    return imageExtensions.some(ext => lower.endsWith(ext));
  });

  if (imageEntries.length === 0) {
    throw new Error('No valid image pages found inside this manga archive.');
  }

  // Natural sort images so pages are in sequential reading order
  imageEntries.sort((a, b) => naturalSortComparator(a.name, b.name));

  onProgress(50, `Unpacking ${imageEntries.length} pages...`);

/**
 * Splits a wide double-page spread image into Right and Left halves for authentic RTL manga reading.
 * @param {Blob} blob - The raw image blob
 * @param {number} width - Natural pixel width
 * @param {number} height - Natural pixel height
 * @returns {Promise<{ blobR: Blob, blobL: Blob } | null>}
 */
async function splitDoublePageSpread(blob, width, height) {
  try {
    const halfW = Math.floor(width / 2);
    let bmp;
    if (typeof createImageBitmap === 'function') {
      bmp = await createImageBitmap(blob);
    } else {
      bmp = await new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = URL.createObjectURL(blob);
      });
    }

    // Right half (Read first in Japanese RTL)
    const canvasR = document.createElement('canvas');
    canvasR.width = halfW;
    canvasR.height = height;
    const ctxR = canvasR.getContext('2d');
    ctxR.drawImage(bmp, halfW, 0, width - halfW, height, 0, 0, halfW, height);
    const blobR = await new Promise(res => canvasR.toBlob(res, 'image/jpeg', 0.92));

    // Left half (Read second in Japanese RTL)
    const canvasL = document.createElement('canvas');
    canvasL.width = halfW;
    canvasL.height = height;
    const ctxL = canvasL.getContext('2d');
    ctxL.drawImage(bmp, 0, 0, halfW, height, 0, 0, halfW, height);
    const blobL = await new Promise(res => canvasL.toBlob(res, 'image/jpeg', 0.92));

    if (bmp && typeof bmp.close === 'function') {
      bmp.close();
    }

    return { blobR, blobL };
  } catch (err) {
    console.warn('Smart double spread split fallback:', err);
    return null;
  }
}

  // Unpack images to Blob URLs with Smart Double-Page Spread Detection
  const pages = [];
  const total = imageEntries.length;

  for (let i = 0; i < total; i++) {
    const entry = imageEntries[i];
    const blob = await entry.async('blob');
    const baseName = entry.name.split('/').pop() || entry.name;
    const blobUrl = URL.createObjectURL(blob);
    activeBlobUrls.push(blobUrl);

    // Smart double-page spread detection (aspect ratio >= 1.25)
    let isSpread = false;
    let splitResult = null;
    try {
      if (typeof createImageBitmap === 'function') {
        const bmp = await createImageBitmap(blob);
        const aspect = bmp.width / bmp.height;
        if (aspect >= 1.25) {
          isSpread = true;
          splitResult = await splitDoublePageSpread(blob, bmp.width, bmp.height);
        }
        bmp.close();
      }
    } catch (e) {}

    if (isSpread && splitResult) {
      // Spread Parity Alignment:
      // In dual-page flipbook mode with showCover: true, facing spreads are [pages[1], pages[2]], [pages[3], pages[4]], etc.
      // The left page is always an ODD 0-index (even 1-based page number).
      // If pages.length is currently even (and > 0), the next slot would be the right page of the previous spread,
      // which would split the double spread across two turns. Insert a blank page to ensure both halves open together:
      if (pages.length % 2 === 0 && pages.length > 0) {
        pages.push({
          pageNumber: pages.length + 1,
          url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1500"><rect width="1000" height="1500" fill="%23ffffff"/></svg>',
          originalUrl: null,
          name: 'Blank Endpaper (Spread Alignment)',
          isBlank: true,
          isSpread: false,
        });
      }

      const urlL = URL.createObjectURL(splitResult.blobL);
      const urlR = URL.createObjectURL(splitResult.blobR);
      activeBlobUrls.push(urlL, urlR);

      // Left half of illustration -> Left page of book
      pages.push({
        pageNumber: pages.length + 1,
        url: urlL,
        originalUrl: blobUrl,
        name: `${baseName} (Left Spread)`,
        isSpread: true,
        spreadPart: 'left',
      });

      // Right half of illustration -> Right page of book
      pages.push({
        pageNumber: pages.length + 1,
        url: urlR,
        originalUrl: blobUrl,
        name: `${baseName} (Right Spread)`,
        isSpread: true,
        spreadPart: 'right',
      });
    } else {
      pages.push({
        pageNumber: pages.length + 1,
        url: blobUrl,
        originalUrl: blobUrl,
        name: baseName,
        isSpread: false,
      });
    }

    if (i % 5 === 0 || i === total - 1) {
      const pct = 50 + Math.round(((i + 1) / total) * 45);
      onProgress(pct, `Unpacked page ${i + 1} of ${total}`);
    }
  }

  onProgress(100, 'Ready to read!');
  return {
    pages,
    comicInfo,
    toc,
    totalPages: pages.length,
  };
}

const CACHE_NAME = 'one-piece-manga-cbz-v1';

/**
 * Checks if a remote volume URL is already cached in browser CacheStorage.
 */
export async function isVolumeCached(url) {
  if (!('caches' in window)) return false;
  try {
    const cache = await caches.open(CACHE_NAME);
    const match = await cache.match(url);
    return !!match;
  } catch {
    return false;
  }
}

/**
 * Clears the offline manga volume cache.
 */
export async function clearVolumeCache() {
  if ('caches' in window) {
    try {
      await caches.delete(CACHE_NAME);
      return true;
    } catch (e) {
      console.warn('Error clearing cache:', e);
    }
  }
  return false;
}

/**
 * Loads a remote CBZ file via fetch with real-time download speed/progress tracking
 * and automatic CacheStorage offline caching.
 */
export async function loadRemoteCbz(url, onProgress = () => {}) {
  // 1. Check instant offline cache first
  if ('caches' in window) {
    try {
      const cache = await caches.open(CACHE_NAME);
      const cachedResponse = await cache.match(url);
      if (cachedResponse) {
        onProgress(25, '⚡ Loaded from offline instant cache!');
        const arrayBuffer = await cachedResponse.arrayBuffer();
        return unpackCbz(arrayBuffer, onProgress);
      }
    } catch (e) {
      console.warn('Offline cache lookup error:', e);
    }
  }

  onProgress(5, 'Connecting to manga stream...');
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to stream volume: HTTP ${response.status} ${response.statusText}`);
  }

  const contentLength = +response.headers.get('Content-Length') || 0;

  // Stream reader with live byte counter & speed calculator
  if (response.body && typeof response.body.getReader === 'function') {
    const reader = response.body.getReader();
    let receivedLength = 0;
    const chunks = [];
    const startTime = performance.now();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      receivedLength += value.length;

      const elapsedSec = (performance.now() - startTime) / 1000;
      const speedMBps = elapsedSec > 0 ? (receivedLength / (1024 * 1024)) / elapsedSec : 0;
      const loadedMB = (receivedLength / (1024 * 1024)).toFixed(1);

      if (contentLength > 0) {
        const totalMB = (contentLength / (1024 * 1024)).toFixed(1);
        const percent = Math.min(48, Math.round((receivedLength / contentLength) * 48));
        const rawPct = Math.round((receivedLength / contentLength) * 100);
        onProgress(
          percent,
          `📥 Downloading: ${loadedMB} / ${totalMB} MB (${rawPct}% • ${speedMBps.toFixed(1)} MB/s)`
        );
      } else {
        onProgress(20, `📥 Streaming: ${loadedMB} MB downloaded (${speedMBps.toFixed(1)} MB/s)`);
      }
    }

    // Assemble chunks into full Uint8Array
    const allChunks = new Uint8Array(receivedLength);
    let position = 0;
    for (const chunk of chunks) {
      allChunks.set(chunk, position);
      position += chunk.length;
    }

    // Cache to browser CacheStorage in the background
    if ('caches' in window) {
      try {
        const cache = await caches.open(CACHE_NAME);
        await cache.put(
          url,
          new Response(allChunks.buffer, {
            headers: {
              'Content-Type': 'application/vnd.comicbook+zip',
              'Content-Length': String(receivedLength),
            },
          })
        );
      } catch (cacheErr) {
        console.warn('CacheStorage save warning:', cacheErr);
      }
    }

    return unpackCbz(allChunks.buffer, onProgress);
  } else {
    // Fallback for browsers without stream reader
    onProgress(15, 'Downloading manga volume...');
    const arrayBuffer = await response.arrayBuffer();
    return unpackCbz(arrayBuffer, onProgress);
  }
}
