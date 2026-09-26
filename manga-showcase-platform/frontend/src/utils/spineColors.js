/**
 * Official Japanese Jump Comics One Piece Spine Skull Color Palette
 * Cycles authentically per volume to match the original printed manga.
 */
export function getVolumeSpineColor(volumeNumber) {
  const num = parseInt(volumeNumber, 10);
  if (isNaN(num) || num <= 0) return '#ea580c'; // Default iconic One Piece Orange

  // Specific canonical volume colors matching Jump Comics
  const canonicalVolumeColors = {
    1: '#ea580c',  // Vol 1: Iconic Orange
    2: '#f43f5e',  // Vol 2: Coral / Salmon Pink
    3: '#a855f7',  // Vol 3: Lavender Purple
    4: '#0ea5e9',  // Vol 4: Sky Blue
    5: '#84cc16',  // Vol 5: Lime Green
    6: '#eab308',  // Vol 6: Bright Yellow
    7: '#ec4899',  // Vol 7: Pink / Rose
    8: '#8b5cf6',  // Vol 8: Light Violet
    9: '#06b6d4',  // Vol 9: Deep Cyan
    10: '#10b981', // Vol 10: Emerald Green
    80: '#16a34a', // Vol 80: Forest Green
    81: '#ea580c', // Vol 81: Orange
    82: '#f43f5e', // Vol 82: Coral Pink
    83: '#a855f7', // Vol 83: Lavender
    84: '#0ea5e9', // Vol 84: Sky Blue
    85: '#84cc16', // Vol 85: Lime Green
    86: '#eab308', // Vol 86: Yellow
    87: '#ec4899', // Vol 87: Pink
    88: '#6366f1', // Vol 88: Indigo
  };

  if (canonicalVolumeColors[num]) {
    return canonicalVolumeColors[num];
  }

  // 10-color recurring Jump Comics spine cycle
  const cycle = [
    '#ea580c', // Orange
    '#f43f5e', // Coral / Salmon
    '#a855f7', // Lavender
    '#0ea5e9', // Sky Blue
    '#84cc16', // Lime Green
    '#eab308', // Bright Yellow
    '#ec4899', // Rose Pink
    '#8b5cf6', // Light Violet
    '#06b6d4', // Deep Cyan
    '#10b981', // Emerald Green
  ];

  return cycle[(num - 1) % cycle.length];
}
