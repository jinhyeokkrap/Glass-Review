import csv
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


ITEMS = [
    ("Poston Midnight Matte", "https://i.warbycdn.com/s/c/3fc24614c80ce49d8bd669f23e424a9f5e3220f0?quality=80&width=3840"),
    ("Denman Rye Tortoise Matte", "https://i.warbycdn.com/s/c/84aee7ef70b4b4c8e3865ff91c75fa3c2f88a2e2?quality=80&width=3840"),
    ("Ernie Shore Pine Matte", "https://i.warbycdn.com/s/c/891f234ccea59882b0e0a7f6dacabbe7c24176b4?quality=80&width=3840"),
    ("Marvin Rye Tortoise", "https://i.warbycdn.com/s/c/0b3f2a56c2130a791e9abe9af6299016647c784d?quality=80&width=3840"),
    ("Amaya Saddle Tortoise", "https://i.warbycdn.com/s/c/2c0897bd6485b3bc5e00608092b78e0fba9a7bcf?quality=80&width=3840"),
    ("Carlton Amalfi Tortoise", "https://i.warbycdn.com/s/c/d0790ce515e9f2bfb1b1178dccf605ea69d0adca?quality=80&width=3840"),
    ("Hayden Seaweed Crystal Matte", "https://i.warbycdn.com/s/c/dcd533c1a522e964795ac82c2d5fb98f876183f0?quality=80&width=3840"),
    ("Wilkie Black Matte Eclipse", "https://i.warbycdn.com/s/c/392aa5615b28164947d08e27bbaff34931d44234?quality=80&width=3840"),
]


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()[:96] or "item"


def request_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=24) as resp:
        return resp.read()


def fit_on_white(img, size=(760, 540)):
    img = ImageOps.exif_transpose(img).convert("RGBA")
    img.thumbnail((size[0] - 44, size[1] - 92), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (250, 251, 249, 255))
    x = (size[0] - img.width) // 2
    y = 30 + (size[1] - 92 - img.height) // 2
    canvas.alpha_composite(img, (x, y))
    return canvas.convert("RGB")


def main():
    with META.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)
    existing = {(row["brand"], row["model"]) for row in rows}
    urls = {row["image_url"] for row in rows}
    next_index = max(int(row["index"]) for row in rows) + 1
    added = []
    for model, url in ITEMS:
        if ("Warby Parker", model) in existing or url in urls:
            continue
        raw = request_bytes(url)
        img = Image.open(BytesIO(raw))
        img.load()
        stem = f"{next_index:03d}_warby_parker_{safe_name(model)}"
        image_path = IMG_DIR / f"{stem}.jpg"
        thumb_path = THUMB_DIR / f"{stem}.jpg"
        fit_on_white(img).save(image_path, quality=94)
        fit_on_white(img, (520, 390)).save(thumb_path, quality=90)
        row = {
            "index": str(next_index),
            "brand": "Warby Parker",
            "model": model,
            "form_note": "mainstream DTC optical frame",
            "image_path": f"images/{image_path.name}",
            "thumb_path": f"thumbs/{thumb_path.name}",
            "image_url": url,
            "page_url": "https://www.warbyparker.com/eyeglasses",
            "source_domain": urlparse(url).netloc,
            "source_type": "official",
            "original_size": f"{img.width}x{img.height}",
        }
        rows.append(row)
        added.append(row)
        brand_dir = BY_BRAND / "Warby Parker"
        brand_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, brand_dir / f"{next_index:03d}_{image_path.name}")
        next_index += 1
    with META.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    print(f"added={len(added)} total={len(rows)}")


if __name__ == "__main__":
    main()
