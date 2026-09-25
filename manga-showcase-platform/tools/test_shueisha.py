import requests, json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

r = requests.get('https://www.shueisha.co.jp/books/search/search.html?seriesid=35169&order=1', headers=headers)
m = re.search(r'var\s+ssd\s*=\s*(\{.*?\});\s*\n', r.text)
data = json.loads(m.group(1))
items = data.get('data', {}).get('item_datas', [])

print(f'Total volumes found in search: {len(items)}')

test_vols = [1, 50, 100, 113, 114, 115]
for it in items:
    vol_num = int(float(it.get('volume_number', 0)))
    if vol_num in test_vols:
        isbn = it['isbn']
        url = f'https://www.shueisha.co.jp/books/items/contents.html?isbn={isbn}'
        r_vol = requests.get(url, headers=headers)
        m_vol = re.search(r'var\s+ssd\s*=\s*(\{.*?\});\s*\n', r_vol.text)
        if m_vol:
            v_data = json.loads(m_vol.group(1))
            imgs = v_data.get('datas', [{}])[0].get('image_datas', [])
            print(f'Volume {vol_num} (ISBN: {isbn}): found {len(imgs)} images')
            for idx, img in enumerate(imgs):
                print(f"  [{idx}] {img.get('image_url_l')}")
