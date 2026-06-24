import csv
import html
import json
import re
import shutil
import time
import urllib.request
from collections import Counter
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus, unquote, urlparse

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "eyewear_form_research_300"
BY_BRAND = ROOT / "outputs" / "eyewear_form_research_300_by_brand"
IMG_DIR = DATA / "images"
THUMB_DIR = DATA / "thumbs"
META = DATA / "metadata.csv"
FAILURES = DATA / "phase2_download_failures.csv"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


BRANDS = [
    {
        "brand": "MYKITA",
        "count": 8,
        "note": "screwless / lightweight industrial optical frame",
        "domains": ["mykita.com"],
        "queries": ["MYKITA optical glasses front view", "MYKITA LITE optical frame", "MYKITA NO1 eyeglasses front"],
    },
    {
        "brand": "LINDBERG",
        "count": 8,
        "note": "ultra-light titanium / minimal optical frame",
        "domains": ["lindberg.com"],
        "queries": ["LINDBERG titanium glasses front view", "LINDBERG air titanium rim eyeglasses", "LINDBERG strip titanium optical frame"],
    },
    {
        "brand": "Silhouette",
        "count": 6,
        "note": "rimless lightweight optical frame",
        "domains": ["silhouette.com"],
        "queries": ["Silhouette Titan Minimal Art optical front", "Silhouette rimless eyeglasses front view"],
    },
    {
        "brand": "ic! berlin",
        "count": 6,
        "note": "screwless sheet-metal optical frame",
        "domains": ["ic-berlin.com", "ic-berlin.de"],
        "queries": ["ic berlin eyeglasses front view", "ic! berlin optical frame product front"],
    },
    {
        "brand": "DITA",
        "count": 8,
        "note": "premium titanium / acetate optical frame",
        "domains": ["dita.com"],
        "queries": ["DITA optical eyeglasses front view", "DITA glasses titanium optical front"],
    },
    {
        "brand": "Matsuda",
        "count": 8,
        "note": "Japanese detailed metal / acetate optical frame",
        "domains": ["matsuda.com"],
        "queries": ["Matsuda optical glasses front view", "Matsuda eyeglasses product front"],
    },
    {
        "brand": "EYEVAN",
        "count": 8,
        "note": "Japanese classic optical frame",
        "domains": ["eyevan.com", "eyevan7285.com"],
        "queries": ["EYEVAN eyeglasses front view", "EYEVAN optical frame product front", "EYEVAN 7285 optical glasses front"],
    },
    {
        "brand": "Masunaga",
        "count": 8,
        "note": "Japanese Sabae heritage optical frame",
        "domains": ["masunaga1905.com", "masunaga-opt.co.jp"],
        "queries": ["Masunaga optical glasses front view", "Masunaga eyeglasses product front"],
    },
    {
        "brand": "Jacques Marie Mage",
        "count": 8,
        "note": "bold sculpted acetate optical frame",
        "domains": ["jacquesmariemage.com"],
        "queries": ["Jacques Marie Mage optical glasses front view", "JMM optical frame product front"],
    },
    {
        "brand": "Warby Parker",
        "count": 8,
        "note": "mainstream DTC optical frame",
        "domains": ["warbyparker.com"],
        "queries": ["Warby Parker eyeglasses front view", "Warby Parker optical frame product front"],
    },
    {
        "brand": "PROJEKT PRODUKT",
        "count": 8,
        "note": "Korean contemporary optical frame",
        "domains": ["projektprodukt.co.kr", "projektprodukt.com"],
        "queries": ["PROJEKT PRODUKT eyeglasses front view", "프로젝트프로덕트 안경 정면"],
    },
    {
        "brand": "MANOMOS",
        "count": 6,
        "note": "Korean daily fashion optical frame",
        "domains": ["manomos.com"],
        "queries": ["MANOMOS eyeglasses front view", "마노모스 안경 정면"],
    },
    {
        "brand": "CARIN",
        "count": 6,
        "note": "Korean commercial fashion optical frame",
        "domains": ["caringlasses.com", "carin.co.kr"],
        "queries": ["CARIN eyeglasses front view", "카린 안경 정면"],
    },
    {
        "brand": "LASH",
        "count": 6,
        "note": "Korean acetate / metal optical frame",
        "domains": ["lasheyewear.com"],
        "queries": ["LASH eyewear eyeglasses front view", "래쉬 안경 정면"],
    },
    {
        "brand": "STEALER",
        "count": 6,
        "note": "Korean edgy metal / fashion optical frame",
        "domains": ["stealer.co.kr", "stealereyewear.com"],
        "queries": ["STEALER eyewear eyeglasses front view", "스틸러 안경 정면"],
    },
    {
        "brand": "MUZIK",
        "count": 6,
        "note": "Korean trend fashion optical frame",
        "domains": ["muzikofficial.com", "muzikeyewear.com"],
        "queries": ["MUZIK eyewear eyeglasses front view", "뮤지크 안경 정면"],
    },
    {
        "brand": "JINS",
        "count": 8,
        "note": "Japanese mass-market ergonomic optical frame",
        "domains": ["jins.com", "jins-eyewear.com"],
        "queries": ["JINS eyeglasses front view", "JINS airframe optical front"],
    },
    {
        "brand": "Zoff",
        "count": 8,
        "note": "Japanese mass-market optical frame",
        "domains": ["zoff.com"],
        "queries": ["Zoff eyeglasses front view", "Zoff SMART glasses front"],
    },
    {
        "brand": "OWNDAYS",
        "count": 8,
        "note": "Asian accessible retail optical frame",
        "domains": ["owndays.com"],
        "queries": ["OWNDAYS eyeglasses front view", "OWNDAYS optical frame product front"],
    },
    {
        "brand": "Yellows Plus",
        "count": 6,
        "note": "refined Japanese thin metal / acetate optical frame",
        "domains": ["yellowsplus.com"],
        "queries": ["Yellows Plus eyeglasses front view", "Yellows Plus optical frame product front"],
    },
    {
        "brand": "KameManNen",
        "count": 6,
        "note": "small round Japanese heritage metal optical frame",
        "domains": ["kamemannen.com"],
        "queries": ["KameManNen eyeglasses front view", "Kame ManNen optical frame product front"],
    },
    {
        "brand": "Ray-Ban Meta",
        "count": 4,
        "note": "mainstream AI camera glasses hardware reference",
        "domains": ["ray-ban.com", "meta.com"],
        "queries": ["Ray-Ban Meta smart glasses front view", "Ray-Ban Meta Wayfarer front product"],
    },
    {
        "brand": "XREAL",
        "count": 4,
        "note": "consumer display glasses hardware reference",
        "domains": ["xreal.com"],
        "queries": ["XREAL glasses front view product", "XREAL Air front view"],
    },
    {
        "brand": "Even Realities",
        "count": 4,
        "note": "everyday AI display glasses hardware reference",
        "domains": ["evenrealities.com"],
        "queries": ["Even Realities G1 glasses front view", "Even Realities smart glasses product front"],
    },
    {
        "brand": "Brilliant Labs",
        "count": 4,
        "note": "AI-first lightweight glasses hardware reference",
        "domains": ["brilliant.xyz", "brilliantlabs.ca"],
        "queries": ["Brilliant Labs Frame glasses front view", "Brilliant Labs AI glasses product front"],
    },
    {
        "brand": "Solos",
        "count": 4,
        "note": "audio / AI smart glasses hardware reference",
        "domains": ["solosglasses.com"],
        "queries": ["Solos AirGo smart glasses front view", "Solos glasses product front"],
    },
]


BAD_HOSTS = ["pinterest.", "facebook.", "instagram.", "youtube.", "tiktok.", "ebay.", "amazon.", "aliexpress."]
GOOD_WORDS = ["front", "optical", "eyeglass", "glasses", "frame", "product", "rx", "view"]
BAD_WORDS = ["side", "lifestyle", "model", "wearing", "case", "clip", "lenscloth", "logo", "banner"]


def request_bytes(url, timeout=22):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def bing_image_candidates(query, max_items=80):
    url = f"https://www.bing.com/images/search?q={quote_plus(query)}&form=HDRSC2&first=1"
    raw = request_bytes(url).decode("utf-8", errors="ignore")
    candidates = []
    for match in re.finditer(r'm="\{(.*?)\}"', raw):
        chunk = "{" + html.unescape(match.group(1)) + "}"
        try:
            data = json.loads(chunk)
        except Exception:
            continue
        image_url = data.get("murl")
        page_url = data.get("purl") or data.get("p")
        if image_url:
            candidates.append({"image_url": image_url, "page_url": page_url or ""})
        if len(candidates) >= max_items:
            break
    if not candidates:
        for image_url in re.findall(r'"murl":"(.*?)"', raw):
            candidates.append({"image_url": image_url.encode("utf-8").decode("unicode_escape"), "page_url": ""})
            if len(candidates) >= max_items:
                break
    return candidates


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()[:96] or "item"


def clean_model(value):
    value = unquote(value)
    value = re.sub(r"\.(jpg|jpeg|png|webp).*", "", value, flags=re.I)
    value = re.sub(r"[_-]+", " ", value)
    value = re.sub(r"\b(front|optical|eyeglasses|glasses|frame|product|image|view|large|main|black|brown|clear)\b", " ", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip(" /_-")
    if not value:
        return "Optical frame"
    return value[:80].title()


def model_from_candidate(brand, candidate):
    for source in (candidate.get("page_url") or "", candidate.get("image_url") or ""):
        path = urlparse(source).path.strip("/")
        parts = [part for part in path.split("/") if part]
        if parts:
            for part in reversed(parts[-4:]):
                cleaned = clean_model(part)
                if cleaned and brand.lower().split()[0] not in cleaned.lower() and len(cleaned) > 2:
                    return cleaned
    return "Optical frame"


def candidate_host_score(url, domains):
    host = urlparse(url).netloc.lower().replace("www.", "")
    score = 0
    if any(domain in host for domain in domains):
        score += 16
    trusted_retailers = [
        "pretavoir.co.uk",
        "fashioneyewear.com",
        "smartbuyglasses.com",
        "eye-oo.com",
        "misterspex.",
        "farfetch.com",
        "ssense.com",
        "goodseeco.com",
        "edel-optics.",
    ]
    if any(domain in host for domain in trusted_retailers):
        score += 5
    if any(bad in host for bad in BAD_HOSTS):
        score -= 20
    return score


def candidate_score(candidate, brand_info):
    domains = brand_info["domains"]
    text = f"{candidate.get('image_url', '')} {candidate.get('page_url', '')}".lower()
    score = candidate_host_score(candidate.get("image_url", ""), domains) + candidate_host_score(candidate.get("page_url", ""), domains)
    brand_tokens = [token for token in re.findall(r"[a-z0-9]+", brand_info["brand"].lower()) if len(token) > 2]
    score += sum(2 for token in brand_tokens if token in text)
    score += sum(2 for word in GOOD_WORDS if word in text)
    score -= sum(4 for word in BAD_WORDS if word in text)
    if any(ext in text for ext in [".jpg", ".jpeg", ".png", ".webp"]):
        score += 2
    return score


def is_allowed(candidate, brand_info):
    text = f"{candidate.get('image_url', '')} {candidate.get('page_url', '')}".lower()
    if any(bad in text for bad in BAD_HOSTS):
        return False
    domains = brand_info["domains"]
    trusted = [
        "pretavoir.co.uk",
        "fashioneyewear.com",
        "smartbuyglasses.com",
        "eye-oo.com",
        "misterspex.",
        "farfetch.com",
        "ssense.com",
        "goodseeco.com",
        "edel-optics.",
    ]
    return any(domain in text for domain in domains + trusted)


def download_image(url):
    raw = request_bytes(url, timeout=24)
    if len(raw) < 7000:
        raise RuntimeError("image bytes too small")
    img = Image.open(BytesIO(raw))
    img.load()
    if img.width < 220 or img.height < 160:
        raise RuntimeError(f"image dimensions too small {img.width}x{img.height}")
    if img.width / max(img.height, 1) > 5.8 or img.height / max(img.width, 1) > 3.2:
        raise RuntimeError(f"unusual aspect {img.width}x{img.height}")
    return img


def fit_on_white(img, size=(760, 540)):
    img = ImageOps.exif_transpose(img).convert("RGBA")
    img.thumbnail((size[0] - 44, size[1] - 92), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (250, 251, 249, 255))
    x = (size[0] - img.width) // 2
    y = 30 + (size[1] - 92 - img.height) // 2
    canvas.alpha_composite(img, (x, y))
    return canvas.convert("RGB")


def load_metadata():
    with META.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def write_metadata(fieldnames, rows):
    with META.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def copy_to_brand_folder(row):
    brand_dir = BY_BRAND / row["brand"]
    brand_dir.mkdir(parents=True, exist_ok=True)
    src = DATA / row["image_path"]
    dst = brand_dir / f"{int(row['index']):03d}_{src.name}"
    if not dst.exists():
        shutil.copy2(src, dst)


def main():
    fieldnames, rows = load_metadata()
    if fieldnames is None:
        raise SystemExit("metadata fieldnames missing")
    existing_urls = {row.get("image_url", "") for row in rows if row.get("image_url")}
    existing_models = {(row.get("brand", ""), row.get("model", "")) for row in rows}
    counts = Counter(row["brand"] for row in rows)
    next_index = max(int(row["index"]) for row in rows) + 1
    added = []
    failures = []

    for brand_info in BRANDS:
        brand = brand_info["brand"]
        needed = max(0, brand_info["count"] - counts[brand])
        if needed <= 0:
            continue
        candidates = []
        domain_queries = [f"site:{domain} {query}" for domain in brand_info["domains"][:2] for query in brand_info["queries"][:2]]
        for query in [*domain_queries, *brand_info["queries"], f"{brand} eyeglasses optical frame front view product image"]:
            try:
                candidates.extend(bing_image_candidates(query))
            except Exception as exc:
                failures.append({"brand": brand, "query": query, "image_url": "", "page_url": "", "reason": f"search failed: {exc}"})
            time.sleep(0.12)

        unique = []
        seen = set()
        for candidate in candidates:
            image_url = candidate.get("image_url", "")
            if not image_url or image_url in seen or image_url in existing_urls:
                continue
            if not is_allowed(candidate, brand_info):
                continue
            seen.add(image_url)
            unique.append(candidate)
        unique.sort(key=lambda item: candidate_score(item, brand_info), reverse=True)

        saved_for_brand = 0
        for candidate in unique[:70]:
            if saved_for_brand >= needed:
                break
            image_url = candidate["image_url"]
            model = model_from_candidate(brand, candidate)
            dedupe_model = model
            suffix = 2
            while (brand, dedupe_model) in existing_models:
                dedupe_model = f"{model} {suffix}"
                suffix += 1
            try:
                img = download_image(image_url)
            except Exception as exc:
                failures.append({"brand": brand, "query": "", "image_url": image_url, "page_url": candidate.get("page_url", ""), "reason": str(exc)})
                continue
            stem = f"{next_index:03d}_{safe_name(brand)}_{safe_name(dedupe_model)}"
            image_path = IMG_DIR / f"{stem}.jpg"
            thumb_path = THUMB_DIR / f"{stem}.jpg"
            fit_on_white(img).save(image_path, quality=94)
            fit_on_white(img, (520, 390)).save(thumb_path, quality=90)
            row = {
                "index": str(next_index),
                "brand": brand,
                "model": dedupe_model,
                "form_note": brand_info["note"],
                "image_path": f"images/{image_path.name}",
                "thumb_path": f"thumbs/{thumb_path.name}",
                "image_url": image_url,
                "page_url": candidate.get("page_url", ""),
                "source_domain": urlparse(candidate.get("page_url") or image_url).netloc,
                "source_type": "phase2",
                "original_size": f"{img.width}x{img.height}",
            }
            rows.append(row)
            added.append(row)
            existing_urls.add(image_url)
            existing_models.add((brand, dedupe_model))
            copy_to_brand_folder(row)
            counts[brand] += 1
            saved_for_brand += 1
            print(f"[{next_index:03d}] saved {brand} - {dedupe_model}", flush=True)
            next_index += 1

        if saved_for_brand < needed:
            failures.append({"brand": brand, "query": "", "image_url": "", "page_url": "", "reason": f"saved {saved_for_brand}/{needed}"})
            print(f"partial {brand}: saved {saved_for_brand}/{needed}", flush=True)

    write_metadata(fieldnames, rows)
    with FAILURES.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["brand", "query", "image_url", "page_url", "reason"])
        writer.writeheader()
        writer.writerows(failures)

    added_counts = Counter(row["brand"] for row in added)
    print(f"added={len(added)} total={len(rows)} brands_added={dict(sorted(added_counts.items()))}", flush=True)
    print(f"failures={len(failures)}")


if __name__ == "__main__":
    main()
