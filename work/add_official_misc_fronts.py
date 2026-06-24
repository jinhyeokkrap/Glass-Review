import csv
import html
import re
import shutil
import time
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


SOURCES = [
    {
        "brand": "Etnia Barcelona",
        "target": 6,
        "url": "https://www.etniabarcelona.com/us/en/optical",
        "note": "color-forward acetate optical frame",
        "pattern": r'<img[^>]+src="(//etniabarcelona\.com/cdn/shop/files/[^"]+?_2\.jpg\?v=[^"]+?(?:&amp;|&)width=3840)"[^>]+alt="([^"]+)"',
    },
    {
        "brand": "L.G.R",
        "target": 6,
        "url": "https://lgrworld.com/collections/optical",
        "note": "classic refined optical frame",
        "pattern": r'<img[^>]+data-src="(https://www\.lgrworld\.com/wp-content/uploads/[^"]+?-1\.jpg)"[^>]+alt="([^"]+?-1)"',
    },
]


def request_bytes(url: str, timeout: int = 24) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()[:96] or "item"


def fit_on_white(img: Image.Image, size=(760, 540)) -> Image.Image:
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


def write_rows(fieldnames, rows) -> None:
    with META.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def clean_model(brand: str, alt: str) -> str:
    value = html.unescape(alt)
    value = re.sub(r"^\d+-", "", value)
    value = re.sub(r"[-_](?:1|2|3|ok)$", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value.replace("-", " ")).strip()
    if brand == "Etnia Barcelona":
        return value.title()[:80]
    if brand == "L.G.R":
        value = re.sub(r"^\d+\s+", "", value)
        return value.title()[:80]
    return value[:80] or "Optical frame"


def candidates(source):
    raw = request_bytes(source["url"]).decode("utf-8", "ignore")
    seen_models = set()
    for image_url, alt in re.findall(source["pattern"], raw, flags=re.I):
        image_url = html.unescape(image_url)
        if image_url.startswith("//"):
            image_url = "https:" + image_url
        model = clean_model(source["brand"], alt)
        if not model or model in seen_models:
            continue
        seen_models.add(model)
        yield model, image_url


def download_image(url: str) -> Image.Image:
    raw = request_bytes(url)
    if len(raw) < 7000:
        raise RuntimeError("image bytes too small")
    img = Image.open(BytesIO(raw))
    img.load()
    if img.width < 220 or img.height < 160:
        raise RuntimeError(f"image too small {img.width}x{img.height}")
    return img


def main() -> None:
    fieldnames, rows = load_rows()
    counts = Counter(row["brand"] for row in rows)
    existing = {(row["brand"], row["model"]) for row in rows}
    urls = {row.get("image_url", "") for row in rows}
    next_index = max(int(row["index"]) for row in rows) + 1
    added = []

    for source in SOURCES:
        brand = source["brand"]
        need = max(0, source["target"] - counts[brand])
        if need <= 0:
            print(f"{brand}: already {counts[brand]}/{source['target']}")
            continue
        saved = 0
        items = list(candidates(source))
        print(f"{brand}: candidates={len(items)} need={need}", flush=True)
        for model, image_url in items:
            if saved >= need:
                break
            if (brand, model) in existing or image_url in urls:
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
                "form_note": source["note"],
                "image_path": f"images/{image_path.name}",
                "thumb_path": f"thumbs/{thumb_path.name}",
                "image_url": image_url,
                "page_url": source["url"],
                "source_domain": urlparse(image_url).netloc,
                "source_type": "official",
                "original_size": f"{img.width}x{img.height}",
            }
            rows.append(row)
            added.append(row)
            brand_dir = BY_BRAND / brand
            brand_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, brand_dir / f"{next_index:03d}_{image_path.name}")
            existing.add((brand, model))
            urls.add(image_url)
            counts[brand] += 1
            saved += 1
            print(f"[{next_index:03d}] saved {brand} - {model}", flush=True)
            next_index += 1
            time.sleep(0.05)
        print(f"{brand}: saved={saved}/{need}", flush=True)

    write_rows(fieldnames, rows)
    print(f"added={len(added)} total={len(rows)}")


if __name__ == "__main__":
    main()
