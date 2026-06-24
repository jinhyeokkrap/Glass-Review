import html
import re
import sys
import urllib.parse
import urllib.request


query = " ".join(sys.argv[1:])
url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query)
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
raw = urllib.request.urlopen(req, timeout=18).read().decode("utf-8", "ignore")
urls = []
for href in re.findall(r'<a[^>]+href="(https?://[^"]+)"', raw):
    href = html.unescape(href)
    if "bing.com" in href:
        continue
    if href not in urls:
        urls.append(href)
for item in urls[:20]:
    print(item)
