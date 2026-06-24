import html
import re
import urllib.request
from urllib.parse import urljoin

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


def get(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", "ignore")


pages = [
    "https://moscot.com/collections/eyeglasses",
    "https://moscot.com/collections/all",
    "https://www.opsm.com.au/glasses/ray-ban",
    "https://www.opsm.com.au/glasses/persol",
    "https://www.opsm.com.au/glasses/oliver-peoples",
    "https://www.opsm.com.au/glasses/prada",
    "https://www.opsm.com.au/glasses/gucci",
    "https://www.opsm.com.au/glasses/tom-ford",
]

for page in pages:
    print("\nPAGE", page)
    try:
        raw = get(page)
    except Exception as exc:
        print("ERR", exc)
        continue
    print("len", len(raw))
    products = sorted(set(urljoin(page, html.unescape(m)) for m in re.findall(r'href=["\']([^"\']*/products/[^"\']+)["\']', raw)))
    print("products", len(products), products[:8])
    opsm_product_refs = sorted(set(urljoin(page, html.unescape(m)) for m in re.findall(r'href=["\']([^"\']+/\d{10,14}[^"\']*)["\']', raw)))
    print("digit product refs", len(opsm_product_refs), opsm_product_refs[:8])
    image_refs = sorted(set(html.unescape(m) for m in re.findall(r'https?://[^"\']+\.(?:png|jpg|jpeg)[^"\']*', raw)))
    useful = [u for u in image_refs if any(s in u.lower() for s in ["__std__shad__qt", "__std__shad__fr", "pos-2", "front"])]
    print("useful images", len(useful), useful[:8])

sample_pages = [
    "https://www.opsm.com.au/glasses/ray-ban/rb3447v-round-metal-optics/7895653330320",
    "https://www.opsm.com.au/glasses/persol/po3007v/8053672663501",
    "https://www.opsm.com.au/glasses/oliver-peoples/ov5183-o-malley/827934405493",
    "https://www.opsm.com.au/glasses/prada/pr-10zv/8056597747714",
]

for page in sample_pages:
    print("\nSAMPLE", page)
    try:
        raw = get(page)
    except Exception as exc:
        print("ERR", exc)
        continue
    print("len", len(raw))
    image_refs = sorted(set(html.unescape(m) for m in re.findall(r'https?://[^"\']+\.(?:png|jpg|jpeg)[^"\']*', raw)))
    useful = [u for u in image_refs if any(s in u.lower() for s in ["__std__shad__qt", "__std__shad__fr", "__std__noshad__fr", "op_pdp"])]
    print("useful images", len(useful))
    for u in useful[:12]:
        print(u[:300])
