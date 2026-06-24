import html
import re
import urllib.request


URLS = [
    "https://www.gentlemonster.com/robots.txt",
    "https://www.gentlemonster.com/sitemap.xml",
    "https://www.gentlemonster.com/sitemap_index.xml",
    "https://www.gentlemonster.com/kr/ko",
    "https://www.gentlemonster.com/us/en",
    "https://www.gentlemonster.com/us/en/category/optical",
    "https://www.gentlemonster.com/us/en/optical",
    "https://www.gentlemonster.com/us/en/shop/item/all_optical",
    "https://www.gentlemonster.com/kr/ko/category/optical",
    "https://www.gentlemonster.com/kr/ko/optical",
    "https://www.gentlemonster.com/kr/ko/shop/item/all_optical",
]


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=18) as resp:
        return resp.read().decode("utf-8", "ignore")


for url in URLS:
    print("\nURL", url)
    try:
        raw = fetch(url)
    except Exception as exc:
        print("ERR", exc)
        continue
    print("len", len(raw))
    item_refs = sorted(set(html.unescape(m) for m in re.findall(r'/(?:us/en|kr/ko|kr/ja|cn/zh-CN)/item/[^"\'<> ]+', raw)))
    front_imgs = sorted(set(html.unescape(m) for m in re.findall(r'https://gm-prd-resource\.gentlemonster\.com/[^"\'<> ]+?_FRONT\.(?:jpg|jpeg|png)(?:\?[^"\'<> ]*)?', raw)))
    print("item refs", len(item_refs), item_refs[:8])
    print("front imgs", len(front_imgs), front_imgs[:5])
