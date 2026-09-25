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

  // Unpack images to Blob URLs
  const pages = [];
  const total = imageEntries.length;

  for (let i = 0; i < total; i++) {
    const entry = imageEntries[i];
    const blob = await entry.async('blob');
    const blobUrl = URL.createObjectURL(blob);
    activeBlobUrls.push(blobUrl);

    pages.push({
      pageNumber: i + 1,
      url: blobUrl,
      name: entry.name.split('/').pop() || entry.name,
    });

    if (i % 5 === 0 || i === total - 1) {
      const pct = 50 + Math.round(((i + 1) / total) * 45);
      onProgress(pct, `Unpacked page ${i + 1} of ${total}`);
    }
  }

  onProgress(100, 'Ready to read!');
  return {
    pages,
    comicInfo,
    totalPages: pages.length,
  };
}

/**
 * Loads a remote CBZ file via fetch and unpacks it.
 */
export async function loadRemoteCbz(url, onProgress = () => {}) {
  onProgress(5, 'Fetching manga volume...');
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download volume: HTTP ${response.status} ${response.statusText}`);
  }
  const arrayBuffer = await response.arrayBuffer();
  return unpackCbz(arrayBuffer, onProgress);
}
