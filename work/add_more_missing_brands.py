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
    {
        "brand": "Jacques Marie Mage",
        "note": "bold sculpted acetate optical frame",
        "page": "https://miaburton.com/en/eyeglasses/jacques-marie-mage",
        "items": [
            ("Ichikawa Opt Noir X", "https://images.miaburton.com/2026/jacques-marie-mage-ichikawa-opt-noir-x.jpg"),
            ("Domoto Opt Black", "https://images.miaburton.com/2026/jacques-marie-mage-domoto-opt-black.jpg"),
            ("Dealan 53 Opt Breccia", "https://images.miaburton.com/2026/jacques-marie-mage-dealan-53-opt-breccia.jpg"),
            ("Moscova Opt London", "https://images.miaburton.com/2026/jacques-marie-mage-moscova-opt-london.jpg"),
            ("Hartigan Argyle", "https://images.miaburton.com/2026/jacques-marie-mage-hartigan-argyle.jpg"),
            ("Jax Opt Etnia", "https://images.miaburton.com/2026/jacques-marie-mage-jax-opt-etnia.jpg"),
            ("Hartigan Opt Phantom", "https://images.miaburton.com/2026/jacques-marie-mage-hartigan-opt-phantom.jpg"),
            ("Clark Opt Phantom", "https://images.miaburton.com/2026/jacques-marie-mage-clark-opt-phantom.jpg"),
        ],
    },
    {
        "brand": "Silhouette",
        "note": "rimless lightweight optical frame",
        "page": "https://www.eurooptica.com/products/silhouette-r-titan-minimal-art-stellar-nl",
        "items": [
            ("Titan Minimal Art Stellar NL", "https://www.eurooptica.com/cdn/shop/files/titan-minimal-art-stellar-nl-9040-00_1024x1024.jpg?v=1705001802"),
        ],
    },
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

    for group in ITEMS:
        for model, url in group["items"]:
            if (group["brand"], model) in existing or url in urls:
                continue
            raw = request_bytes(url)
            if len(raw) < 7000:
                continue
            img = Image.open(BytesIO(raw))
            img.load()
            if img.width < 220 or img.height < 160:
                continue
            stem = f"{next_index:03d}_{safe_name(group['brand'])}_{safe_name(model)}"
            image_path = IMG_DIR / f"{stem}.jpg"
            thumb_path = THUMB_DIR / f"{stem}.jpg"
            fit_on_white(img).save(image_path, quality=94)
            fit_on_white(img, (520, 390)).save(thumb_path, quality=90)
            row = {
                "index": str(next_index),
                "brand": group["brand"],
                "model": model,
                "form_note": group["note"],
                "image_path": f"images/{image_path.name}",
                "thumb_path": f"thumbs/{thumb_path.name}",
                "image_url": url,
                "page_url": group["page"],
                "source_domain": urlparse(url).netloc,
                "source_type": "phase2-manual",
                "original_size": f"{img.width}x{img.height}",
            }
            rows.append(row)
            added.append(row)
            brand_dir = BY_BRAND / group["brand"]
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
