import re
import sys
import urllib.request


url = sys.argv[1]
raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8", "ignore")
print("bytes", len(raw))
for pat in sys.argv[2:] or [r'href=["\']([^"\']+)']:
    print("PATTERN", pat)
    seen = []
    for match in re.findall(pat, raw):
        value = match[0] if isinstance(match, tuple) else match
        if value not in seen:
            seen.append(value)
    for value in seen[:80]:
        print(value)
