import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "eyewear_form_research_gentlemonster_extra"
IMG_DIR = OUT / "images"
THUMB_DIR = OUT / "thumbs"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"

QUERIES = [
    'site:gentlemonster.com/us/en/item Gentle Monster optical glasses FRONT',
    'site:gentlemonster.com/kr/ja/item Gentle Monster optical glasses FRONT',
    'site:gentlemonster.com/kr/ko/item Gentle Monster optical glasses FRONT',
    'site:gentlemonster.com/cn/zh-CN/item Gentle Monster optical glasses FRONT',
    'site:gentlemonster.com/us/en/item "01" "Gentle Monster"',
    'site:gentlemonster.com/us/en/item "GD1" "Gentle Monster"',
    'site:gentlemonster.com/us/en/item "glasses" "Gentle Monster"',
    'site:gentlemonster.com/kr/ja/item "2024opticalcollection"',
    'site:gentlemonster.com/us/en/item "Ojo 01"',
    'site:gentlemonster.com/us/en/item "Lilit 01"',
    'site:gentlemonster.com/us/en/item "Atomic 02"',
    'site:gentlemonster.com/us/en/item "Eddy 01"',
]


def request_text(url):
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


def request_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def bing_search_urls(query, max_pages=3):
    found = []
    for page in range(max_pages):
        first = page * 10 + 1
        url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query) + f"&first={first}"
        try:
            raw = request_text(url)
        except Exception:
            continue
        for match in re.findall(r'https?://www\.gentlemonster\.com/(?:us/en|kr/ko|kr/ja|cn/zh-CN)/item/[^"\'<> \)&]+', raw):
            clean = html.unescape(match).split("?")[0].rstrip("/")
            found.append(clean)
        for match in re.findall(r'href="(https?://www\.gentlemonster\.com/[^"]+/item/[^"]+)"', raw):
            clean = html.unescape(match).split("?")[0].rstrip("/")
            found.append(clean)
        time.sleep(0.15)
    return found


def normalize_model_from_url(url):
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"[-_]+", " ", slug)
    slug = re.sub(r"(?i)([a-z]+)(\\d+)$", r"\1 \2", slug)
    return slug.strip().title() or "Gentle Monster Frame"


def extract_product(page_url):
    raw = request_text(page_url)
    front_urls = sorted(set(html.unescape(m) for m in re.findall(r'https://gm-prd-resource\.gentlemonster\.com/catalog/product/[^"\'<> ]+?_FRONT\.(?:jpg|jpeg|png)(?:\?[^"\'<> ]*)?', raw)))
    front_urls = [u for u in front_urls if "favicon" not in u.lower()]
    if not front_urls:
        raise RuntimeError("no front image")
    model = normalize_model_from_url(page_url)
    title_match = re.search(r'<title>(.*?)</title>', raw, re.S | re.I)
    if title_match:
        title = html.unescape(re.sub(r"\s+", " ", title_match.group(1))).strip()
        candidate = re.sub(r"\s*-\s*GENTLE MONSTER.*$", "", title, flags=re.I).strip()
        if candidate and len(candidate) < 60:
            model = candidate
    return {
        "brand": "Gentle Monster",
        "model": model,
        "form_note": "Gentle Monster optical / sunglass frame",
        "image_url": front_urls[0],
        "page_url": page_url,
        "source_type": "official",
    }


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()[:96]


def fit_on_white(img, size=(760, 540)):
    img = ImageOps.exif_transpose(img).convert("RGBA")
    img.thumbnail((size[0] - 44, size[1] - 92), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (250, 251, 249, 255))
    x = (size[0] - img.width) // 2
    y = 30 + (size[1] - 92 - img.height) // 2
    canvas.alpha_composite(img, (x, y))
    return canvas.convert("RGB")


def save_item(item, index):
    raw = request_bytes(item["image_url"])
    img = Image.open(BytesIO(raw))
    img.load()
    if img.width < 240 or img.height < 180:
        raise RuntimeError("image too small")
    stem = f"{index:03d}_gentle_monster_{safe_name(item['model'])}"
    image_path = IMG_DIR / f"{stem}.jpg"
    thumb_path = THUMB_DIR / f"{stem}.jpg"
    fit_on_white(img).save(image_path, quality=94)
    fit_on_white(img, (520, 390)).save(thumb_path, quality=90)
    item["index"] = index
    item["image_path"] = f"images/{image_path.name}"
    item["thumb_path"] = f"thumbs/{thumb_path.name}"
    item["original_size"] = f"{img.width}x{img.height}"
    item["source_domain"] = "www.gentlemonster.com"
    return item


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    for folder in (IMG_DIR, THUMB_DIR):
        for old in folder.glob("*.jpg"):
            old.unlink()

    urls = []
    for query in QUERIES:
        urls.extend(bing_search_urls(query))
    urls = list(dict.fromkeys(urls))
    print(f"candidate urls={len(urls)}")

    rows = []
    failures = []
    seen_images = set()
    seen_models = set()
    for url in urls:
        try:
            item = extract_product(url)
            if item["image_url"] in seen_images or item["model"].lower() in seen_models:
                continue
            saved = save_item(item, len(rows) + 1)
            rows.append(saved)
            seen_images.add(item["image_url"])
            seen_models.add(item["model"].lower())
            print(f"[{len(rows):03d}] {saved['model']}")
        except Exception as exc:
            failures.append({"page_url": url, "reason": str(exc)})
        if len(rows) >= 40:
            break

    fields = ["index", "brand", "model", "form_note", "image_path", "thumb_path", "image_url", "page_url", "source_domain", "source_type", "original_size"]
    with (OUT / "metadata.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    with (OUT / "failures.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["page_url", "reason"])
        writer.writeheader()
        writer.writerows(failures)
    print(f"DONE rows={len(rows)} failures={len(failures)}")


if __name__ == "__main__":
    main()
