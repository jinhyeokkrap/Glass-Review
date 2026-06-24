import csv
import html
import re
import shutil
import urllib.request
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "eyewear_form_research_300"
BY_BRAND = ROOT / "outputs" / "eyewear_form_research_300_by_brand"
IMG_DIR = DATA / "images"
THUMB_DIR = DATA / "thumbs"
META = DATA / "metadata.csv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


SOURCES = [
    {
        "brand": "PROJEKT PRODUKT",
        "target": 6,
        "url": "https://www.blackzmith.com/collections/projekt-produkt-sc17-sc18",
        "note": "Korean contemporary optical frame",
        "pattern": r'<img src="(//www\.blackzmith\.com/cdn/shop/products/[^"]+?\.jpg\?v=[^"]+)" alt="([^"]+)" class="card__image"',
    },
    {
        "brand": "LASH",
        "target": 6,
        "url": "https://totalsun.co.kr/category/%EB%9E%98%EC%89%AC-lash/117/",
        "note": "Korean acetate / metal optical frame",
        "pattern": r'<a href="([^"]*/product/[^"]+)"><img src="(//totalsun\.co\.kr/web/product/big/[^"]+?\.jpg)"[^>]+>',
    },
]


def request_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=24) as resp:
        return resp.read().decode("utf-8", "ignore")


def request_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=24) as resp:
        return resp.read()


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()[:96] or "item"


def fit_on_white(img, size=(760, 540)):
    img = ImageOps.exif_transpose(img).convert("RGBA")
    img.thumbnail((size[0] - 44, size[1] - 92), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (250, 251, 249, 255))
    x = (size[0] - img.width) // 2
    y = 30 + (size[1] - 92 - img.height) // 2
    canvas.alpha_composite(img, (x, y))
    return canvas.convert("RGB")


def load_rows():
    with META.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def write_rows(fieldnames, rows):
    with META.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def clean_model(value, fallback):
    value = html.unescape(value)
    value = re.sub(r"Projekt Produkt\s*-\s*", "", value, flags=re.I)
    value = re.sub(r"[\ufffd�]+.*$", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    if value:
        return value[:80]
    fallback = urlparse(fallback).path.strip("/").split("/")[1:3]
    return " ".join(fallback).replace("-", " ").title()[:80] or "Optical frame"


def candidates(source):
    raw = request_text(source["url"])
    found = []
    for match in re.findall(source["pattern"], raw, flags=re.I | re.S):
        if source["brand"] == "PROJEKT PRODUKT":
            image_url, label = match
            page_url = source["url"]
            model = clean_model(label, image_url)
        else:
            page_ref, image_url = match
            page_url = "https://totalsun.co.kr" + page_ref if page_ref.startswith("/") else page_ref
            model = clean_model("", page_url)
        image_url = "https:" + image_url if image_url.startswith("//") else image_url
        if "_1024x1024" in image_url:
            image_url = image_url.replace("_1024x1024", "_1400x1400")
        found.append((model, image_url, page_url))
    return found


def main():
    fieldnames, rows = load_rows()
    existing = {(row["brand"], row["model"]) for row in rows}
    urls = {row["image_url"] for row in rows}
    counts = {}
    for row in rows:
        counts[row["brand"]] = counts.get(row["brand"], 0) + 1
    next_index = max(int(row["index"]) for row in rows) + 1
    added = []
    for source in SOURCES:
        need = max(0, source["target"] - counts.get(source["brand"], 0))
        if need <= 0:
            continue
        saved = 0
        for model, image_url, page_url in candidates(source):
            if saved >= need:
                break
            if (source["brand"], model) in existing or image_url in urls:
                continue
            raw = request_bytes(image_url)
            if len(raw) < 7000:
                continue
            img = Image.open(BytesIO(raw))
            img.load()
            if img.width < 220 or img.height < 160:
                continue
            stem = f"{next_index:03d}_{safe_name(source['brand'])}_{safe_name(model)}"
            image_path = IMG_DIR / f"{stem}.jpg"
            thumb_path = THUMB_DIR / f"{stem}.jpg"
            fit_on_white(img).save(image_path, quality=94)
            fit_on_white(img, (520, 390)).save(thumb_path, quality=90)
            row = {
                "index": str(next_index),
                "brand": source["brand"],
                "model": model,
                "form_note": source["note"],
                "image_path": f"images/{image_path.name}",
                "thumb_path": f"thumbs/{thumb_path.name}",
                "image_url": image_url,
                "page_url": page_url,
                "source_domain": urlparse(image_url).netloc,
                "source_type": "phase2-page",
                "original_size": f"{img.width}x{img.height}",
            }
            rows.append(row)
            added.append(row)
            brand_dir = BY_BRAND / source["brand"]
            brand_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, brand_dir / f"{next_index:03d}_{image_path.name}")
            existing.add((source["brand"], model))
            urls.add(image_url)
            saved += 1
            next_index += 1
        print(f"{source['brand']}: saved={saved}/{need}")
    write_rows(fieldnames, rows)
    print(f"added={len(added)} total={len(rows)}")


if __name__ == "__main__":
    main()
