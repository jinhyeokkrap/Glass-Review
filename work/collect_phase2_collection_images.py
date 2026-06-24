import csv
import html
import re
import shutil
import urllib.request
from collections import Counter
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


COLLECTIONS = [
    {
        "brand": "Matsuda",
        "target": 8,
        "url": "https://www.matsuda.com/collections/optical",
        "note": "Japanese detailed metal / acetate optical frame",
    },
    {
        "brand": "Warby Parker",
        "target": 8,
        "url": "https://www.warbyparker.com/eyeglasses",
        "note": "mainstream DTC optical frame",
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


def copy_to_brand(row):
    brand_dir = BY_BRAND / row["brand"]
    brand_dir.mkdir(parents=True, exist_ok=True)
    src = DATA / row["image_path"]
    dst = brand_dir / f"{int(row['index']):03d}_{src.name}"
    if not dst.exists():
        shutil.copy2(src, dst)


def download_image(url):
    raw = request_bytes(url)
    if len(raw) < 7000:
        raise RuntimeError("image bytes too small")
    img = Image.open(BytesIO(raw))
    img.load()
    if img.width < 220 or img.height < 160:
        raise RuntimeError(f"image too small {img.width}x{img.height}")
    return img


def matsuda_candidates(raw):
    candidates = []
    seen_models = set()
    pattern = r'data-variant-img-url="([^"]+)"(?:(?!data-variant-img-url=).){0,900}?<img[^>]+alt="([^"]+)"'
    for url, model in re.findall(pattern, raw, flags=re.I | re.S):
        model = html.unescape(model).strip()
        url = html.unescape(url).replace("&amp;", "&")
        if url.startswith("//"):
            url = "https:" + url
        if "front" not in url.lower() and model in seen_models:
            continue
        if "width=" in url:
            url = re.sub(r"width=\d+", "width=1400", url)
        else:
            url += "&width=1400" if "?" in url else "?width=1400"
        if model in seen_models:
            continue
        seen_models.add(model)
        candidates.append((model, url))
    return candidates


def warby_candidates(raw):
    candidates = []
    seen_models = set()
    pattern = r"Image: ([^,†]+), front view[^†]*†www\.warbyparker\.com.*?(https://i\.warbycdn\.com/s/c/[^\"'<> )]+)"
    for model, url in re.findall(pattern, raw, flags=re.I | re.S):
        model = html.unescape(model).strip()
        url = html.unescape(url)
        if "width=" not in url:
            url += "&width=1600" if "?" in url else "?width=1600"
        if model in seen_models:
            continue
        seen_models.add(model)
        candidates.append((model, url))
    if not candidates:
        urls = re.findall(r"https://i\.warbycdn\.com/s/c/[^\"'<> )]+", raw)
        labels = re.findall(r"Image: ([^,†]+), front view", raw)
        for model, url in zip(labels, urls):
            candidates.append((html.unescape(model), html.unescape(url)))
    return candidates


def candidates_for(config):
    raw = request_text(config["url"])
    if config["brand"] == "Matsuda":
        return matsuda_candidates(raw)
    if config["brand"] == "Warby Parker":
        return warby_candidates(raw)
    return []


def main():
    fieldnames, rows = load_rows()
    counts = Counter(row["brand"] for row in rows)
    existing_images = {row.get("image_url", "") for row in rows}
    existing_models = {(row.get("brand", ""), row.get("model", "")) for row in rows}
    next_index = max(int(row["index"]) for row in rows) + 1
    added = []
    for config in COLLECTIONS:
        brand = config["brand"]
        need = max(0, config["target"] - counts[brand])
        if need <= 0:
            continue
        candidates = candidates_for(config)
        print(f"{brand}: candidates={len(candidates)} need={need}", flush=True)
        saved = 0
        for model, image_url in candidates:
            if saved >= need:
                break
            if image_url in existing_images or (brand, model) in existing_models:
                continue
            try:
                img = download_image(image_url)
            except Exception as exc:
                print(f"missed {brand} {model}: {exc}", flush=True)
                continue
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
                "page_url": config["url"],
                "source_domain": urlparse(config["url"]).netloc,
                "source_type": "official",
                "original_size": f"{img.width}x{img.height}",
            }
            rows.append(row)
            added.append(row)
            copy_to_brand(row)
            existing_images.add(image_url)
            existing_models.add((brand, model))
            counts[brand] += 1
            saved += 1
            print(f"[{next_index:03d}] saved {brand} - {model}", flush=True)
            next_index += 1
    write_rows(fieldnames, rows)
    print(f"added={len(added)} total={len(rows)}")


if __name__ == "__main__":
    main()
