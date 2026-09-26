"""
Slice One Piece manga spines (Volumes 1 to 95) from the official Jump Comics compilation sheet.
Source sheet: https://i.imgur.com/up3vQpx.jpeg (2479 x 2360 px)

Grid structure:
  - Row 1: Volumes 01 to 40 (40 spines)
  - Row 2: Volumes 41 to 80 (40 spines)
  - Row 3: Volumes 81 to 95 (15 spines, centered)
"""

import os
import sys
import urllib.request
from PIL import Image

SHEET_URL = "https://i.imgur.com/up3vQpx.jpeg"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "tools", "cache")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "comics", "covers")

def ensure_sheet_image(local_cache_path: str) -> str:
    """Download or return cached sheet image."""
    if os.path.exists(local_cache_path) and os.path.getsize(local_cache_path) > 100_000:
        return local_cache_path

    # Check brain scratch directory if available
    brain_scratch = os.path.expanduser(
        r"~/.gemini/antigravity-ide/brain/5e4a8001-22f2-4cb2-a459-cdbd82a9b138/scratch/imgur_spines.jpg"
    )
    if os.path.exists(brain_scratch) and os.path.getsize(brain_scratch) > 100_000:
        return brain_scratch

    print(f"Downloading spine sheet from {SHEET_URL}...")
    os.makedirs(os.path.dirname(local_cache_path), exist_ok=True)
    req = urllib.request.Request(SHEET_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(local_cache_path, "wb") as f:
        f.write(resp.read())
    print(f"Downloaded to {local_cache_path} ({os.path.getsize(local_cache_path):,} bytes)")
    return local_cache_path

def get_crop_box(volume_num: int) -> tuple[int, int, int, int]:
    """Calculate exact bounding box (x1, y1, x2, y2) for a given volume number (1-95)."""
    if 1 <= volume_num <= 40:
        i = volume_num - 1
        x1 = round(24 + i * 60.8)
        x2 = round(24 + (i + 1) * 60.8)
        y1, y2 = 2, 785
    elif 41 <= volume_num <= 80:
        i = volume_num - 41
        x1 = round(0 + i * 61.975)
        x2 = round(0 + (i + 1) * 61.975)
        y1, y2 = 789, 1571
    elif 81 <= volume_num <= 95:
        i = volume_num - 81
        x1 = round(777 + i * 61.2)
        x2 = round(777 + (i + 1) * 61.2)
        y1, y2 = 1574, 2356
    else:
        raise ValueError(f"Volume {volume_num} is outside sheet range (1-95)")
    return (x1, y1, x2, y2)

# Official Tankōbon Dimensions (Width x Depth x Height):
# 12.7 cm x 2.03 cm x 19.05 cm (5.0" x 0.8" x 7.5")
OFFICIAL_WIDTH_CM = 12.7
OFFICIAL_SPINE_CM = 2.03
OFFICIAL_HEIGHT_CM = 19.05
OFFICIAL_SPINE_ASPECT_RATIO = OFFICIAL_SPINE_CM / OFFICIAL_HEIGHT_CM  # ~0.10656

def slice_all_spines(output_dir: str = DEFAULT_OUTPUT_DIR):
    """Slice volumes 1 to 95 and save both .webp and .jpg scaled to official tankōbon dimensions."""
    os.makedirs(output_dir, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, "one_piece_spines_1_95.jpg")
    sheet_path = ensure_sheet_image(cache_path)

    print(f"Opening sheet image: {sheet_path}")
    sheet = Image.open(sheet_path).convert("RGB")
    print(f"Sheet dimensions: {sheet.size}")
    print(f"Target official spine aspect ratio: {OFFICIAL_SPINE_ASPECT_RATIO:.4f} ({OFFICIAL_SPINE_CM}cm / {OFFICIAL_HEIGHT_CM}cm)")

    count = 0
    for vol in range(1, 96):
        box = get_crop_box(vol)
        cropped = sheet.crop(box)

        # Scale width to match official tankōbon physical spine ratio
        target_w = round(cropped.height * OFFICIAL_SPINE_ASPECT_RATIO)
        official_spine = cropped.resize((target_w, cropped.height), Image.Resampling.LANCZOS)

        vol_tag = f"v{vol:02d}"
        jpg_name = f"spine-{vol_tag}.jpg"
        webp_name = f"spine-{vol_tag}.webp"

        jpg_path = os.path.join(output_dir, jpg_name)
        webp_path = os.path.join(output_dir, webp_name)

        # Save high quality JPEG and WebP
        official_spine.save(jpg_path, "JPEG", quality=93)
        official_spine.save(webp_path, "WEBP", quality=90, method=6)
        count += 1
        if vol % 20 == 0 or vol == 95:
            print(f"  Sliced {vol}/95: {webp_name} ({official_spine.size[0]}x{official_spine.size[1]}px, ratio={official_spine.size[0]/official_spine.size[1]:.4f})")

    print(f"\n[DONE] Successfully extracted {count} manga spines formatted to official dimensions ({OFFICIAL_WIDTH_CM} x {OFFICIAL_SPINE_CM} x {OFFICIAL_HEIGHT_CM} cm)")
    print(f"Destination directory: {output_dir}")

if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT_DIR
    slice_all_spines(out_dir)
