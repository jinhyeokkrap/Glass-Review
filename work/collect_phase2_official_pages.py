import csv
import html
import re
import shutil
import time
import urllib.request
from collections import Counter
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "eyewear_form_research_300"
BY_BRAND = ROOT / "outputs" / "eyewear_form_research_300_by_brand"
IMG_DIR = DATA / "images"
THUMB_DIR = DATA / "thumbs"
META = DATA / "metadata.csv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


COLLECTIONS = [
    {
        "brand": "DITA",
        "target": 8,
        "note": "premium titanium / acetate optical frame",
        "urls": ["https://dita.com/collections/optical", "https://dita.com/collections/optical?page=2"],
        "product_re": r'href=["\']([^"\']*/products/[^"\'?#]+)',
        "image_re": r"https?://[^\"'<> ]+\.(?:jpg|jpeg|png|webp)[^\"'<> ]*",
        "image_filter": lambda u: "dita.com/cdn/shop/products" in u.lower() and "front" in u.lower(),
    },
    {
        "brand": "MYKITA",
        "target": 8,
        "note": "screwless / lightweight industrial optical frame",
        "urls": ["https://mykita.com/en/prescription-glasses"],
        "product_re": r'href=["\']([^"\']*/en/prescription-glasses/[^"\'?#]+)',
        "image_re": r"https?://[^\"'<> ]+\.(?:jpg|jpeg|png|webp)[^\"'<> ]*",
        "image_filter": lambda u: "mykitamedia.com/media/image" in u.lower() and "-p-2" in u.lower(),
    },
]


def request_text(url, timeout=22):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def request_bytes(url, timeout=22):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()[:96] or "item"


def clean_model_from_url(url):
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    slug = re.sub(r"^(optical-|glasses-)", "", slug, flags=re.I)
    slug = re.sub(r"[-_]+", " ", slug)
    slug = re.sub(r"\b(c\d+|clear|black|silver|gold|shiny|matte|optical|frame|glasses|eyeglasses)\b", " ", slug, flags=re.I)
    slug = re.sub(r"\s+", " ", slug).strip()
    return slug[:80].title() or "Optical frame"


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


def copy_to_brand(row):
    brand_dir = BY_BRAND / row["brand"]
    brand_dir.mkdir(parents=True, exist_ok=True)
    src = DATA / row["image_path"]
    dst = brand_dir / f"{int(row['index']):03d}_{src.name}"
    if not dst.exists():
        shutil.copy2(src, dst)


def extract_product_pages(config):
    found = []
    seen = set()
    for collection_url in config["urls"]:
        raw = request_text(collection_url)
        for ref in re.findall(config["product_re"], raw, flags=re.I):
            url = urljoin(collection_url, html.unescape(ref)).split("#")[0]
            if url in seen:
                continue
            seen.add(url)
            found.append(url)
    return found


def extract_image(config, page_url):
    raw = request_text(page_url)
    images = []
    for value in re.findall(config["image_re"], raw, flags=re.I):
        value = html.unescape(value).replace("http://", "https://")
        if config["image_filter"](value):
            images.append(value)
    if not images:
        return ""
    # Prefer original or larger images where available.
    images = sorted(set(images), key=lambda u: (("_1200x" in u or "_1024x" in u or "small/" in u), len(u)))
    return images[0]


def download_image(url):
    raw = request_bytes(url)
    if len(raw) < 7000:
        raise RuntimeError("image bytes too small")
    img = Image.open(BytesIO(raw))
    img.load()
    if img.width < 220 or img.height < 160:
        raise RuntimeError(f"image too small {img.width}x{img.height}")
    return img


def main():
    fieldnames, rows = load_rows()
    if fieldnames is None:
        raise SystemExit("metadata fieldnames missing")
    counts = Counter(row["brand"] for row in rows)
    existing_pages = {row.get("page_url", "") for row in rows}
    existing_images = {row.get("image_url", "") for row in rows}
    existing_models = {(row.get("brand", ""), row.get("model", "")) for row in rows}
    next_index = max(int(row["index"]) for row in rows) + 1
    added = []

    for config in COLLECTIONS:
        brand = config["brand"]
        need = max(0, config["target"] - counts[brand])
        if need <= 0:
            continue
        pages = extract_product_pages(config)
        print(f"{brand}: pages={len(pages)} need={need}", flush=True)
        saved = 0
        for page_url in pages:
            if saved >= need:
                break
            if page_url in existing_pages:
                continue
            try:
                image_url = extract_image(config, page_url)
                if not image_url or image_url in existing_images:
                    continue
                img = download_image(image_url)
            except Exception as exc:
                print(f"missed {brand} {page_url}: {exc}", flush=True)
                continue
            model = clean_model_from_url(page_url)
            model_base = model
            suffix = 2
            while (brand, model) in existing_models:
                model = f"{model_base} {suffix}"
                suffix += 1
            stem = f"{next_index:03d}_{safe_name(brand)}_{safe_name(model)}"
            image_path = IMG_DIR / f"{stem}.jpg"
            thumb_path = THUMB_DIR / f"{stem}.jpg"
            fit_on_white(img).save(image_path, quality=94)
            fit_on_white(img, (520, 390)).save(thumb_path, quality=90)
            row = {
                "index": str(next_index),
                "brand": brand,
                "model": model,
                "form_note": config["note"],
                "image_path": f"images/{image_path.name}",
                "thumb_path": f"thumbs/{thumb_path.name}",
                "image_url": image_url,
                "page_url": page_url,
                "source_domain": urlparse(page_url).netloc,
                "source_type": "official",
                "original_size": f"{img.width}x{img.height}",
            }
            rows.append(row)
            added.append(row)
            copy_to_brand(row)
            existing_pages.add(page_url)
            existing_images.add(image_url)
            existing_models.add((brand, model))
            counts[brand] += 1
            saved += 1
            print(f"[{next_index:03d}] saved {brand} - {model}", flush=True)
            next_index += 1
            time.sleep(0.08)

    write_rows(fieldnames, rows)
    print(f"added={len(added)} total={len(rows)}")


if __name__ == "__main__":
    main()
