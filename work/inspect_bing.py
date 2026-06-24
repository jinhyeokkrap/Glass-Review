import urllib.request

url = "https://www.bing.com/images/search?q=Ray-Ban+Wayfarer+eyeglasses+front+view"
raw = urllib.request.urlopen(
    urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=10
).read().decode("utf-8", "ignore")

for pat in ["iusc", 'class="iusc', 'm="{', "&quot;murl&quot;", '\\"murl\\"']:
    print(pat, raw.find(pat))

idx = raw.find('class="iusc')
print(raw[idx : idx + 1400].encode("ascii", "backslashreplace").decode("ascii"))
