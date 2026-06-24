import re
import sys
import urllib.request


url = sys.argv[1]
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
raw = urllib.request.urlopen(req, timeout=18).read().decode("utf-8", "ignore")
print("bytes", len(raw))
for match in re.findall(r"https?://[^\"'<> ]+\.(?:jpg|jpeg|png|webp)[^\"'<> ]*", raw, re.I)[:20]:
    print(match)
