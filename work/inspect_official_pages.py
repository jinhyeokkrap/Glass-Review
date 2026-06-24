import html
import re
import urllib.request

pages = [
    "https://www.oakley.com/en-us/product/W0OX8100F?variant=888392603012",
    "https://moscot.com/products/lemtosh",
    "https://www.gentlemonster.com/kr/ja/item/ZYYE799SURVC/zin01",
]

for page in pages:
    print("\nPAGE", page)
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(page, headers={"User-Agent": "Mozilla/5.0"}), timeout=12
        ).read().decode("utf-8", "ignore")
    except Exception as exc:
        print("ERR", exc)
        continue
    print("len", len(raw))
    urls = []
    for value in re.findall(r"https?://[^\"'<> )]+", raw):
        value = html.unescape(value)
        if any(ext in value.lower() for ext in [".jpg", ".jpeg", ".png", "/is/image/"]):
            urls.append(value)
    for url in urls[:30]:
        print(url[:260])
