/**
 * Converts a numeric volume number (e.g. 1, 25, 100) to Japanese Kanji notation
 * as used on authentic Shueisha Jump Comics One Piece tankōbon spines.
 * Examples: 1 -> 一, 10 -> 十, 11 -> 十一, 20 -> 二十, 25 -> 二十五, 100 -> 百
 */
export function toKanjiVolume(num) {
  const n = parseInt(num, 10);
  if (isNaN(n) || n <= 0) return String(num || 1);

  const KANJI_DIGITS = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九'];

  if (n < 10) {
    return KANJI_DIGITS[n];
  }

  if (n === 10) {
    return '十';
  }

  if (n < 20) {
    return '十' + KANJI_DIGITS[n % 10];
  }

  if (n < 100) {
    const tens = Math.floor(n / 10);
    const ones = n % 10;
    return KANJI_DIGITS[tens] + '十' + (ones > 0 ? KANJI_DIGITS[ones] : '');
  }

  if (n === 100) {
    return '百';
  }

  if (n < 1000) {
    const hundreds = Math.floor(n / 100);
    const rem = n % 100;
    const hStr = hundreds === 1 ? '百' : KANJI_DIGITS[hundreds] + '百';
    if (rem === 0) return hStr;
    if (rem < 10) return hStr + KANJI_DIGITS[rem];
    return hStr + toKanjiVolume(rem);
  }

  return String(n);
}
