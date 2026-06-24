import html
import re
import urllib.request


URLS = [
    "https://www.gentlemonster.com/kr/ja/item/ZYYE799SURVC/zin01",
    "https://www.gentlemonster.com/kr/ja/item/194RVEG6I7XGB/aliogd1",
    "https://www.gentlemonster.com/cn/zh-CN/item/SDFZSB9VJ282/ojo01",
    "https://www.gentlemonster.com/us/en/item/MZ8998WXRENN/matiny01",
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", "ignore")


for url in URLS:
    print("\nPAGE", url)
    try:
        raw = fetch(url)
    except Exception as exc:
        print("ERR", exc)
        continue
    print("len", len(raw))
    fronts = sorted(set(html.unescape(m) for m in re.findall(r'https://gm-prd-resource\.gentlemonster\.com/catalog/product/[^"\'<> ]+?_FRONT\.(?:jpg|jpeg|png)(?:\?[^"\'<> ]*)?', raw)))
    print("fronts", len(fronts))
    for front in fronts[:12]:
        idx = raw.find(front.split("?")[0])
        context = raw[max(0, idx - 350): idx + 240] if idx >= 0 else ""
        context = re.sub(r"\s+", " ", context)
        print("IMG", front)
        print("CTX", context[:700].encode("ascii", "backslashreplace").decode("ascii"))
