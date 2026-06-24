import re
import urllib.request


raw = urllib.request.urlopen(
    urllib.request.Request("https://www.matsuda.com/collections/optical", headers={"User-Agent": "Mozilla/5.0"}),
    timeout=20,
).read().decode("utf-8", "ignore")
print("data urls", len(re.findall(r"data-variant-img-url=", raw)))
print("quoted urls", len(re.findall(r"data-variant-img-url=[\"']([^\"']+)", raw)))
print("alt", len(re.findall(r"alt=[\"']([^\"']+)", raw)))
for m in re.findall(r"data-variant-img-url=[\"']([^\"']+).{0,500}", raw)[:5]:
    print(m[:500])
