import json
import re

with open("canon_volumes_complete.json", "r", encoding="utf-8") as f:
    vols = {int(k): v for k, v in json.load(f).items()}

# In One Piece, volume chapters are strictly contiguous!
# If start_ch was 1 for high volumes, correct it from previous volume end
sorted_keys = sorted(vols.keys())
last_end = 0
for v in sorted_keys:
    data = vols[v]
    st = data["ch_start"]
    en = data["ch_end"]

    # If st <= last_end, it means st was mistakenly reset or defaulted
    if st <= last_end:
        st = last_end + 1
        # If en was also bad or < st, calculate en
        if en < st:
            en = st + 9
        data["ch_start"] = st
        data["ch_end"] = en

    last_end = en

for v in [1, 2, 10, 20, 50, 90, 100, 103, 105, 108, 110, 111, 112, 113]:
    if v in vols:
        info = vols[v]
        print(f"Vol {v:3d}: Chapters {info['ch_start']:4d} to {info['ch_end']:4d} - '{info['title']}'")

with open("canon_volumes_complete.json", "w", encoding="utf-8") as out:
    json.dump(vols, out, indent=2)
print("Updated canon_volumes_complete.json successfully!")
