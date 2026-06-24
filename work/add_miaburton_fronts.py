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
    ("ic! berlin", "ic-berlin", 6, "screwless sheet-metal optical frame"),
    ("KameManNen", "kamemannen", 6, "small round Japanese heritage metal optical frame"),
    ("Silhouette", "silhouette", 6, "rimless lightweight optical frame"),
    ("Tom Ford", "tom-ford", 5, "commercial luxury optical frame"),
    ("Gucci", "gucci", 5, "fashion-forward acetate / metal optical frame"),
    ("Saint Laurent", "saint-laurent", 5, "restrained luxury optical frame"),
    ("CELINE", "celine", 5, "fashion-minimal optical frame"),
    ("Dior", "dior", 5, "luxury fashion optical frame"),
    ("Cartier", "cartier", 5, "jewelry-like luxury optical frame"),
    ("Balenciaga", "balenciaga", 5, "extreme fashion optical frame"),
    ("Bottega Veneta", "bottega-veneta", 5, "quiet luxury optical frame"),
    ("AHLEM", "ahlem", 6, "architectural metal / acetate optical frame"),
    ("Garrett Leight", "garrett-leight", 6, "Californian daily classic optical frame"),
    ("Barton Perreira", "barton-perreira", 6, "premium Japanese-made optical classic"),
    ("Cutler and Gross", "cutler-and-gross", 6, "thick acetate heritage optical frame"),
    ("Etnia Barcelona", "etnia-barcelona", 6, "color-forward acetate optical frame"),
    ("L.G.R", "lgr", 6, "classic refined optical frame"),
]

ALIASES = {
    "ic! berlin": ["ic! berlin", "ic berlin"],
    "CELINE": ["celine"],
    "L.G.R": ["l.g.r", "lgr"],
}


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


def clean_model(brand: str, alt: str, url: str) -> str:
    value = html.unescape(alt)
    value = re.sub(r"\s+-\s+front view\s*$", "", value, flags=re.I)
    value = re.sub(r"\s+Eyeglasses\s+", " ", value, flags=re.I)
    value = re.sub(rf"^\s*{re.escape(brand)}\s+", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip()
    if value:
        return value[:80]
    slug = urlparse(url).path.rsplit("/", 1)[-1]
    slug = re.sub(r"-\d+x\d+(?=\.)", "", slug)
    slug = re.sub(r"\.[a-z0-9]+$", "", slug, flags=re.I)
    slug = re.sub(r"[-_]+", " ", slug)
    return slug.title()[:80] or "Optical frame"


def high_res_url(url: str) -> str:
    return re.sub(r"-\d+x\d+(?=\.(?:jpg|jpeg|png|webp))", "", url, flags=re.I)


def matches_brand(brand: str, alt: str) -> bool:
    normalized = re.sub(r"\s+", " ", alt).lower()
    aliases = ALIASES.get(brand, [brand])
    return any(alias.lower() in normalized for alias in aliases)


def candidates(brand: str, slug: str):
    page_url = f"https://miaburton.com/en/eyeglasses/{slug}"
    raw = request_bytes(page_url).decode("utf-8", "ignore")
    pattern = r'<img[^>]+src="([^"]+)"[^>]+alt="([^"]*front view[^"]*)"[^>]*>'
    seen = set()
    for image_url, alt in re.findall(pattern, raw, flags=re.I):
        alt = html.unescape(alt)
        if not matches_brand(brand, alt):
            continue
        image_url = html.unescape(image_url)
        if "miaburton.com" not in image_url:
            continue
        image_url = high_res_url(image_url)
        if image_url in seen:
            continue
        seen.add(image_url)
        yield page_url, image_url, alt


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
    if fieldnames is None:
        raise SystemExit("metadata fieldnames missing")
    counts = Counter(row["brand"] for row in rows)
    existing = {(row["brand"], row["model"]) for row in rows}
    urls = {row.get("image_url", "") for row in rows}
    next_index = max(int(row["index"]) for row in rows) + 1
    added = []

    for brand, slug, target, note in SOURCES:
        need = max(0, target - counts[brand])
        if need <= 0:
            print(f"{brand}: already {counts[brand]}/{target}")
            continue
        saved = 0
        try:
            items = list(candidates(brand, slug))
        except Exception as exc:
            print(f"{brand}: page failed: {exc}")
            continue
        print(f"{brand}: candidates={len(items)} need={need}", flush=True)
        for page_url, image_url, alt in items:
            if saved >= need:
                break
            model = clean_model(brand, alt, image_url)
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
                "form_note": note,
                "image_path": f"images/{image_path.name}",
                "thumb_path": f"thumbs/{thumb_path.name}",
                "image_url": image_url,
                "page_url": page_url,
                "source_domain": urlparse(image_url).netloc,
                "source_type": "retailer-front",
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
