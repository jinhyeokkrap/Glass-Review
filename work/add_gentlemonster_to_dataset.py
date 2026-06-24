import csv
import re
import shutil
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "eyewear_form_research_300"
BY_BRAND = ROOT / "outputs" / "eyewear_form_research_300_by_brand"
IMG_DIR = DATA / "images"
THUMB_DIR = DATA / "thumbs"


GENTLE_MONSTER_ITEMS = [
    ("Kant 01(BR)", "https://gm-prd-resource.gentlemonster.com/catalog/product/0MKYDKCMFG24F/4b816dac-6134-4ac6-8df7-9c4daf1e0433/11004762_FRONT.jpg?width=1400"),
    ("Kant 01(BL)", "https://gm-prd-resource.gentlemonster.com/catalog/product/0MKYDKCNQG254/c5ea583f-cdc6-4a4b-b886-b49935be1f2a/11004761_FRONT.jpg?width=1400"),
    ("Kafka 01(BL)", "https://gm-prd-resource.gentlemonster.com/catalog/product/0MKYDKCPKG261/a19c6f18-11d5-47fe-86da-83c0760241c1/11004765_FRONT.jpg?width=1400"),
    ("Kafka 01", "https://gm-prd-resource.gentlemonster.com/catalog/product/0MKYDKCP7G27S/1082e32f-901a-4ee9-ae37-83a8296c1f36/11004764_FRONT.jpg?width=1400"),
    ("Kant 01", "https://gm-prd-resource.gentlemonster.com/catalog/product/0MKYDKCKKG25Q/1d5ebf61-ae4f-4806-9695-59920462068f/11004760_FRONT.jpg?width=1400"),
    ("Kafka 01(V)", "https://gm-prd-resource.gentlemonster.com/catalog/product/0N1DWYKKTPKP5/0195930d-add5-409a-b803-1ad81af347ab/11004891_FRONT.jpg?width=1400"),
    ("Era 01", "https://gm-prd-resource.gentlemonster.com/catalog/product/UPBHR4XT3LJM/e404594c-4226-427b-893a-27c0d13ab437/11003979_FRONT.jpg?width=1400"),
    ("Gatta 01(C)", "https://gm-prd-resource.gentlemonster.com/catalog/product/J9Y3PS62AGY4/3a4ffab1-6f8d-47c5-89ab-e2fa201630f4/11003346_FRONT.jpg?width=1400"),
    ("Ego 01(B)", "https://gm-prd-resource.gentlemonster.com/catalog/product/FH6WIB671U9U/a7a473ce-7a72-4f5f-bbbd-699863fd0dc8/11003327_FRONT.jpg?width=1400"),
    ("Beca 01", "https://gm-prd-resource.gentlemonster.com/catalog/product/XOWH2RVEDE35/4f575522-c8e2-493f-9f85-8418f02b131b/11003170_FRONT.jpg?width=1400"),
    ("Rob 01", "https://gm-prd-resource.gentlemonster.com/catalog/product/W676ZS9QWS8B/9bda9389-714b-474a-a563-e6e6518bd8c5/11003135_FRONT.jpg?width=1400"),
    ("Alio X 01", "https://gm-prd-resource.gentlemonster.com/catalog/product/8NX8YBQ7JSZW/f4c33300-7f43-4366-8bed-2cf28e642d76/11000032_FRONT.jpg?width=1400"),
]


def request_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=24) as resp:
        return resp.read()


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


def main():
    metadata_path = DATA / "metadata.csv"
    with metadata_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if fieldnames is None:
        fieldnames = [
            "index",
            "brand",
            "model",
            "form_note",
            "image_path",
            "thumb_path",
            "image_url",
            "page_url",
            "source_domain",
            "source_type",
            "original_size",
        ]

    existing_models = {(row["brand"], row["model"]) for row in rows}
    existing_urls = {row["image_url"] for row in rows}
    next_index = max(int(row["index"]) for row in rows) + 1
    added = []
    for model, url in GENTLE_MONSTER_ITEMS:
        if ("Gentle Monster", model) in existing_models or url in existing_urls:
            continue
        raw = request_bytes(url)
        img = Image.open(BytesIO(raw))
        img.load()
        stem = f"{next_index:03d}_gentle_monster_{safe_name(model)}"
        image_path = IMG_DIR / f"{stem}.jpg"
        thumb_path = THUMB_DIR / f"{stem}.jpg"
        fit_on_white(img).save(image_path, quality=94)
        fit_on_white(img, (520, 390)).save(thumb_path, quality=90)
        row = {
            "index": str(next_index),
            "brand": "Gentle Monster",
            "model": model,
            "form_note": "Gentle Monster recommended optical frame",
            "image_path": f"images/{image_path.name}",
            "thumb_path": f"thumbs/{thumb_path.name}",
            "image_url": url,
            "page_url": "https://www.gentlemonster.com/kr/ja/item/ZYYE799SURVC/zin01",
            "source_domain": "www.gentlemonster.com",
            "source_type": "official",
            "original_size": f"{img.width}x{img.height}",
        }
        rows.append(row)
        added.append(row)
        next_index += 1

    with metadata_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    brand_dir = BY_BRAND / "Gentle Monster"
    brand_dir.mkdir(parents=True, exist_ok=True)
    for row in added:
        src = DATA / row["image_path"]
        dst = brand_dir / f"{int(row['index']):03d}_{src.name}"
        shutil.copy2(src, dst)

    print(f"added={len(added)} total={len(rows)} gentle_monster={sum(1 for r in rows if r['brand'] == 'Gentle Monster')}")


if __name__ == "__main__":
    main()
