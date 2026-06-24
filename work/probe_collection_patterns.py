import re
import sys
import urllib.request


url = sys.argv[1]
needle = sys.argv[2]
raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8", "ignore")
print("bytes", len(raw))
print("count", raw.count(needle))
for match in re.findall(r".{0,90}" + re.escape(needle) + r".{0,180}", raw):
    print(match)
