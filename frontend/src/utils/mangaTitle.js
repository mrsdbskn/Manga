/**
 * utils/mangaTitle.js - Smart title parser, deduplicator, and chapter/volume detector
 * for One Piece and manga filenames, comic metadata, and reading history entries.
 */

/**
 * Parses and cleans a filename, ID, or title string into structured manga metadata.
 *
 * @param {string} rawString - File name, volumeId, or title string
 * @param {object|null} comicInfo - Optional ComicInfo.xml metadata object
 * @param {number|null} totalPages - Optional page count (used as fallback heuristic)
 * @returns {{
 *   type: 'chapter' | 'volume',
 *   title: string,
 *   number: number|null,
 *   badge: 'CH' | 'VOL',
 *   cleanTitle: string
 * }}
 */
export function parseMangaMetadata(rawString = '', comicInfo = null, totalPages = null) {
  if (!rawString) {
    const isCh = totalPages && totalPages <= 70;
    return {
      type: isCh ? 'chapter' : 'volume',
      title: isCh ? 'Unknown Chapter' : 'Unknown Volume',
      number: null,
      badge: isCh ? 'CH' : 'VOL',
      cleanTitle: isCh ? 'Chapter' : 'Volume',
    };
  }

  // 1. Strip file extension
  let clean = rawString.replace(/\.(cbz|zip|cbr|rar|tar|gz|webp|png|jpg)$/i, '').trim();

  // 2. Handle legacy local IDs like 'local-1790346896740'
  if (/^local-\d+$/.test(clean)) {
    const isCh = totalPages && totalPages <= 70;
    const type = isCh ? 'chapter' : 'volume';
    return {
      type,
      title: isCh ? `Local Chapter (${totalPages} pages)` : `Local Volume (${totalPages} pages)`,
      number: null,
      badge: isCh ? 'CH' : 'VOL',
      cleanTitle: isCh ? 'Local Chapter' : 'Local Volume',
    };
  }

  // 3. Strip 'local-chapter-' or 'local-volume-' prefixes if present
  let forcedType = null;
  if (clean.startsWith('local-chapter-')) {
    forcedType = 'chapter';
    clean = clean.replace('local-chapter-', '');
  } else if (clean.startsWith('local-volume-')) {
    forcedType = 'volume';
    clean = clean.replace('local-volume-', '');
  }

  // Replace underscores with spaces if it looks like a sanitized filename
  if (clean.includes('_') && !clean.includes(' ')) {
    clean = clean.replace(/_/g, ' ');
  }

  // 4. Check ComicInfo if available
  if (comicInfo) {
    const chStart = parseInt(comicInfo.startChapter || comicInfo.chapter);
    const chEnd = parseInt(comicInfo.endChapter || comicInfo.chapter);
    const volNum = parseInt(comicInfo.volume);
    const ciTitle = comicInfo.title ? comicInfo.title.trim() : '';

    if (!isNaN(chStart) && (isNaN(chEnd) || chStart === chEnd) && isNaN(volNum)) {
      return {
        type: 'chapter',
        title: ciTitle ? `Chapter ${chStart}: ${cleanDuplicateChapterText(ciTitle, chStart)}` : `Chapter ${chStart}`,
        number: chStart,
        badge: 'CH',
        cleanTitle: ciTitle || `Chapter ${chStart}`,
      };
    }

    if (!isNaN(volNum)) {
      return {
        type: 'volume',
        title: ciTitle ? `Volume ${volNum}: ${cleanDuplicateVolumeText(ciTitle, volNum)}` : `Volume ${volNum}`,
        number: volNum,
        badge: 'VOL',
        cleanTitle: ciTitle || `Volume ${volNum}`,
      };
    }
  }

  // 5. Deduplicate repetitive patterns: e.g. "Chapter 1 - Chapter 1 - Romance Dawn"
  clean = clean.replace(/(?:One\s+Piece\s*[-–—:]*\s*)/gi, '').trim();

  // Pattern A: Chapter detection
  // Matches "Chapter 12", "Ch. 12", "Ch 012", "c012", "c12"
  const chMatch = clean.match(/(?:(?:Chapter|Ch\.?)\s*(\d+)|(?:\bc(\d{1,4})\b))/i);
  // Pattern B: Volume detection
  // Matches "Volume 02", "Vol. 2", "Vol 2", "v02", "v2"
  const volMatch = clean.match(/(?:(?:Volume|Vol\.?)\s*(\d+)|(?:\bv(\d{1,3})\b))/i);

  // If both volume and chapter range e.g. "v02 (c009-017)" or "Volume 2 (Chapters 9-17)"
  const volRangeMatch = clean.match(/(?:Volume|Vol\.?|v)\s*0*(\d+)\s*(?:\((?:c|chapters?)\s*0*(\d+)\s*[-–—]\s*0*(\d+)\))/i);
  if (volRangeMatch) {
    const vol = parseInt(volRangeMatch[1]);
    const c1 = parseInt(volRangeMatch[2]);
    const c2 = parseInt(volRangeMatch[3]);
    return {
      type: 'volume',
      title: `Volume ${vol} (Chapters ${c1}–${c2})`,
      number: vol,
      badge: 'VOL',
      cleanTitle: `Volume ${vol}`,
    };
  }

  // Deduplicate "Chapter X - Chapter X - Title"
  const doubleChMatch = clean.match(/^Chapter\s*(\d+)\s*[-–—:]+\s*Chapter\s*\1\s*[-–—:]+\s*(.*)$/i);
  if (doubleChMatch) {
    const chNum = parseInt(doubleChMatch[1]);
    const rest = doubleChMatch[2].trim();
    return {
      type: 'chapter',
      title: rest ? `Chapter ${chNum}: ${rest}` : `Chapter ${chNum}`,
      number: chNum,
      badge: 'CH',
      cleanTitle: rest || `Chapter ${chNum}`,
    };
  }

  // Single Chapter match
  if ((chMatch && !volMatch) || forcedType === 'chapter') {
    const chNum = chMatch ? parseInt(chMatch[1] || chMatch[2]) : null;
    let rest = clean;
    if (chMatch) {
      // Remove the chapter prefix from rest
      rest = clean.replace(new RegExp(`^(?:(?:Chapter|Ch\\.?)\\s*0*${chNum}|c0*${chNum})\\s*[-–—:]*\\s*`, 'i'), '').trim();
      // Also remove duplicate "Chapter X" if still at start of rest
      rest = rest.replace(new RegExp(`^(?:(?:Chapter|Ch\\.?)\\s*0*${chNum}|c0*${chNum})\\s*[-–—:]*\\s*`, 'i'), '').trim();
    }
    // Clean up any remaining leading/trailing dashes
    rest = rest.replace(/^[-–—:]+\s*/, '').replace(/\s*[-–—:]+$/, '').trim();

    const displayTitle = chNum !== null 
      ? (rest ? `Chapter ${chNum}: ${rest}` : `Chapter ${chNum}`)
      : clean;

    return {
      type: 'chapter',
      title: displayTitle,
      number: chNum,
      badge: 'CH',
      cleanTitle: rest || `Chapter ${chNum}`,
    };
  }

  // Single Volume match
  if (volMatch || forcedType === 'volume') {
    const volNum = volMatch ? parseInt(volMatch[1] || volMatch[2]) : 1;
    let rest = clean;
    if (volMatch) {
      rest = clean.replace(new RegExp(`^(?:(?:Volume|Vol\\.?)\\s*0*${volNum}|v0*${volNum})\\s*[-–—:]*\\s*`, 'i'), '').trim();
      rest = rest.replace(new RegExp(`^(?:(?:Volume|Vol\\.?)\\s*0*${volNum}|v0*${volNum})\\s*[-–—:]*\\s*`, 'i'), '').trim();
    }
    rest = rest.replace(/^[-–—:]+\s*/, '').replace(/\s*[-–—:]+$/, '').trim();

    const displayTitle = volNum !== null
      ? (rest ? `Volume ${volNum}: ${rest}` : `Volume ${volNum}`)
      : clean;

    return {
      type: 'volume',
      title: displayTitle,
      number: volNum,
      badge: 'VOL',
      cleanTitle: rest || `Volume ${volNum}`,
    };
  }

  // Fallback: heuristic based on page count or words
  const isCh = totalPages ? totalPages <= 70 : /chapter/i.test(clean);
  return {
    type: isCh ? 'chapter' : 'volume',
    title: clean,
    number: null,
    badge: isCh ? 'CH' : 'VOL',
    cleanTitle: clean,
  };
}

function cleanDuplicateChapterText(text, chNum) {
  return text.replace(new RegExp(`^Chapter\\s*0*${chNum}\\s*[-–—:]*\\s*`, 'i'), '').trim();
}

function cleanDuplicateVolumeText(text, volNum) {
  return text.replace(new RegExp(`^Volume\\s*0*${volNum}\\s*[-–—:]*\\s*`, 'i'), '').trim();
}
