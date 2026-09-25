import requests
import json
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MangaApp/1.0'}

r = requests.get('https://en.wikipedia.org/w/api.php', params={
    'action': 'parse',
    'page': 'List of One Piece chapters (1016–current)',
    'prop': 'wikitext',
    'format': 'json'
}, headers=headers)
text = r.json().get('parse', {}).get('wikitext', {}).get('*', '')
starts = re.findall(r"\{\{Numbered list\s*\|\s*start\s*=\s*(\d+)", text, re.IGNORECASE)
print("Starts in 1016-current with flexible regex:", starts)



