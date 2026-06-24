import csv
import html
import re
import shutil
import time
import urllib.request
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
BASE_OUT = ROOT / "outputs" / "eyewear_form_research_100"
OUT = ROOT / "outputs" / "eyewear_form_research_300"
IMG_DIR = OUT / "images"
THUMB_DIR = OUT / "thumbs"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
TARGET_TOTAL = 300


OPSM_BRAND_PAGES = [
    ("Ray-Ban", "https://www.opsm.com.au/glasses/ray-ban"),
    ("Oakley", "https://www.opsm.com.au/glasses/oakley"),
    ("Persol", "https://www.opsm.com.au/glasses/persol"),
    ("Oliver Peoples", "https://www.opsm.com.au/glasses/oliver-peoples"),
    ("Prada", "https://www.opsm.com.au/glasses/prada"),
    ("Prada Linea Rossa", "https://www.opsm.com.au/glasses/prada-linea-rossa"),
    ("Gucci", "https://www.opsm.com.au/glasses/gucci"),
    ("Tom Ford", "https://www.opsm.com.au/glasses/tom-ford"),
    ("Versace", "https://www.opsm.com.au/glasses/versace"),
    ("Miu Miu", "https://www.opsm.com.au/glasses/miu-miu"),
    ("Burberry", "https://www.opsm.com.au/glasses/burberry"),
    ("Giorgio Armani", "https://www.opsm.com.au/glasses/giorgio-armani"),
    ("Emporio Armani", "https://www.opsm.com.au/glasses/emporio-armani"),
    ("Armani Exchange", "https://www.opsm.com.au/glasses/armani-exchange"),
    ("Coach", "https://www.opsm.com.au/glasses/coach"),
    ("Dolce&Gabbana", "https://www.opsm.com.au/glasses/dolce&gabbana"),
    ("Jimmy Choo", "https://www.opsm.com.au/glasses/jimmy-choo"),
    ("Michael Kors", "https://www.opsm.com.au/glasses/michael-kors"),
    ("Moncler", "https://www.opsm.com.au/glasses/moncler"),
    ("Polo Ralph Lauren", "https://www.opsm.com.au/glasses/polo-ralph-lauren"),
    ("Ralph", "https://www.opsm.com.au/glasses/ralph"),
    ("Swarovski", "https://www.opsm.com.au/glasses/swarovski"),
    ("Vogue Eyewear", "https://www.opsm.com.au/glasses/vogue-eyewear"),
    ("Arnette", "https://www.opsm.com.au/glasses/arnette"),
    ("Brooks Brothers", "https://www.opsm.com.au/glasses/brooks-brothers"),
]

MOSCOT_COLLECTIONS = [
    ("MOSCOT", "https://moscot.com/collections/eyeglasses"),
    ("MOSCOT", "https://moscot.com/collections/all"),
]

MOSCOT_SKIP = [
    "clip",
    "sun",
    "chamois",
    "cloth",
    "case",
    "chain",
    "tint",
    "gift",
    "hat",
    "book",
    "pin",
    "lens",
    "spray",
    "donation",
]


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


def fetch_html(url):
    return request_bytes(url).decode("utf-8", "ignore")


def clean_text(value):
    value = re.sub(r"[-_]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value.upper() if len(value) <= 9 and any(c.isdigit() for c in value) else value.title()


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()[:96]


def model_from_opsm_url(url):
    parts = [p for p in urlparse(url).path.split("/") if p]
    return clean_text(parts[-2] if len(parts) >= 3 else parts[-1])


def model_tokens_from_page(url):
    model = model_from_opsm_url(url)
    raw = model.lower()
    tokens = set(re.findall(r"[a-z0-9]+", raw))
    normalized = re.sub(r"[^a-z0-9]+", "", raw)
    if normalized:
        tokens.add(normalized)
    # Add common image-server code variants: pr-10zv -> 0pr_10zv, rb3447v -> 0rx3447v/0rb3447v.
    if tokens:
        joined = "_".join(re.findall(r"[a-z0-9]+", raw))
        tokens.add(joined)
        tokens.add("0" + joined)
        tokens.add("0" + normalized)
    if normalized.startswith("rb"):
        tokens.add("0rx" + normalized[2:])
        tokens.add("0" + normalized)
    if normalized.startswith("gg") or normalized.startswith("gc"):
        tokens.add("0" + normalized)
    if normalized.startswith(("pr", "po", "ov", "ve", "mu", "be", "ar", "ax", "mk")):
        tokens.add("0" + normalized)
    return {t for t in tokens if len(t) >= 3}


def infer_form_note(model):
    lower = model.lower()
    if any(word in lower for word in ["round", "miltzen", "zev", "po3092", "ov5183"]):
        return "round / panto optical"
    if any(word in lower for word in ["square", "wayfarer", "holbrook"]):
        return "square optical"
    if any(word in lower for word in ["clubmaster", "yukel", "brow"]):
        return "browline combination"
    if any(word in lower for word in ["aviator", "pilot"]):
        return "pilot / aviator optical"
    if any(word in lower for word in ["rimless", "titan"]):
        return "minimal rimless"
    return "optical frame"


def collect_opsm_product_pages():
    items = []
    seen = set()
    for brand, page in OPSM_BRAND_PAGES:
        try:
            raw = fetch_html(page)
        except Exception as exc:
            print(f"brand page failed {brand}: {exc}", flush=True)
            continue
        refs = re.findall(r'href=["\']([^"\']+/\d{10,14}(?:\?[^"\']*)?)["\']', raw)
        count = 0
        for ref in refs:
            url = urljoin(page, html.unescape(ref)).split("#")[0]
            url = re.sub(r"\?.*$", "", url)
            if url in seen:
                continue
            seen.add(url)
            model = model_from_opsm_url(url)
            items.append(
                {
                    "brand": brand,
                    "model": model,
                    "form_note": infer_form_note(model),
                    "page_url": url,
                    "source_type": "retailer",
                }
            )
            count += 1
        print(f"OPSM {brand}: {count} unique refs", flush=True)
    return items


def score_opsm_image(url, tokens):
    lower = url.lower()
    normalized = re.sub(r"[^a-z0-9]+", "", lower)
    if "thumb" in lower:
        return -1000
    score = 0
    if tokens and not any(t in lower or t in normalized for t in tokens):
        score -= 120
    if "__std__" in lower:
        score += 24
    if "__p21__" in lower:
        score += 16
    if "__noshad__fr" in lower:
        score += 60
    if "__shad__fr" in lower:
        score += 55
    if "__noshad__qt" in lower:
        score += 35
    if "__shad__qt" in lower:
        score += 30
    if "__shad__cfr" in lower:
        score += 20
    if "__shad__lt" in lower or "__shad__bk" in lower or "__shad__al" in lower:
        score -= 16
    if "wid=200" in lower:
        score -= 40
    if "differenturl=true" in lower:
        score -= 10
    return score


def extract_opsm_image(page_url):
    raw = fetch_html(page_url)
    tokens = model_tokens_from_page(page_url)
    urls = []
    for value in re.findall(r'https?://[^"\'<> )]+\.(?:png|jpg|jpeg)[^"\'<> )]*', raw):
        value = html.unescape(value)
        lower = value.lower()
        if "assets2.opsm.com" not in lower:
            continue
        if not any(marker in lower for marker in ["__std__", "__p21__"]):
            continue
        if not any(view in lower for view in ["__shad__fr", "__noshad__fr", "__shad__qt", "__noshad__qt", "__shad__cfr"]):
            continue
        urls.append(value)
    if not urls:
        raise RuntimeError("no OPSM product image")
    urls = sorted(set(urls), key=lambda u: score_opsm_image(u, tokens), reverse=True)
    if score_opsm_image(urls[0], tokens) < -30:
        raise RuntimeError("no model-matching OPSM image")
    return urls[0]


def collect_moscot_product_pages(limit=60):
    seen = set()
    pages = []
    for brand, collection in MOSCOT_COLLECTIONS:
        try:
            raw = fetch_html(collection)
        except Exception as exc:
            print(f"MOSCOT collection failed: {exc}", flush=True)
            continue
        refs = re.findall(r'href=["\']([^"\']*/products/[^"\']+)["\']', raw)
        for ref in refs:
            url = urljoin(collection, html.unescape(ref)).split("?")[0].split("#")[0]
            handle = url.rstrip("/").split("/")[-1]
            if url in seen or any(skip in handle for skip in MOSCOT_SKIP):
                continue
            seen.add(url)
            pages.append(
                {
                    "brand": brand,
                    "model": clean_text(handle),
                    "form_note": infer_form_note(handle),
                    "page_url": url,
                    "source_type": "official",
                }
            )
            if len(pages) >= limit:
                return pages
    return pages


def extract_moscot_image(page_url):
    raw = fetch_html(page_url)
    urls = []
    for value in re.findall(r'https?://[^"\'<> )]+\.(?:png|jpg|jpeg)[^"\'<> )]*', raw):
        value = html.unescape(value).replace("http://", "https://")
        lower = value.lower()
        if "moscot.com/cdn/shop/files" not in lower:
            continue
        if "pos-2" not in lower and "pos_2" not in lower:
            continue
        if any(skip in lower for skip in ["clip", "sun"]):
            continue
        urls.append(value)
    if not urls:
        raise RuntimeError("no MOSCOT front-ish product image")
    return sorted(set(urls), key=lambda u: (0 if "width=480" in u or "_grande" in u else 1, len(u)))[0]


def fit_on_white(img, size=(760, 540)):
    img = ImageOps.exif_transpose(img).convert("RGBA")
    img.thumbnail((size[0] - 44, size[1] - 92), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (250, 251, 249, 255))
    x = (size[0] - img.width) // 2
    y = 30 + (size[1] - 92 - img.height) // 2
    canvas.alpha_composite(img, (x, y))
    return canvas.convert("RGB")


def copy_existing_rows():
    rows = []
    existing_images = set()
    existing_pages = set()
    existing_models = set()
    if OUT.exists():
        shutil.rmtree(OUT)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    with (BASE_OUT / "metadata.csv").open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            image_src = BASE_OUT / row["image_path"]
            thumb_src = BASE_OUT / row["thumb_path"]
            image_dst = IMG_DIR / image_src.name
            thumb_dst = THUMB_DIR / thumb_src.name
            shutil.copy2(image_src, image_dst)
            shutil.copy2(thumb_src, thumb_dst)
            row["image_path"] = f"images/{image_dst.name}"
            row["thumb_path"] = f"thumbs/{thumb_dst.name}"
            row.setdefault("source_type", "existing")
            rows.append(row)
            existing_images.add(row.get("image_url", ""))
            existing_pages.add(row.get("page_url", ""))
            existing_models.add((row.get("brand", ""), row.get("model", "")))
    return rows, existing_images, existing_pages, existing_models


def download_candidate(item, index, seen_image_urls):
    if "image_url" not in item:
        if "opsm.com.au" in item["page_url"]:
            item["image_url"] = extract_opsm_image(item["page_url"])
        elif "moscot.com" in item["page_url"]:
            item["image_url"] = extract_moscot_image(item["page_url"])
        else:
            raise RuntimeError("no extractor for page")
    if item["image_url"] in seen_image_urls:
        raise RuntimeError("duplicate image url")

    raw = request_bytes(item["image_url"])
    if len(raw) < 8000:
        raise RuntimeError("image too small bytes")
    img = Image.open(BytesIO(raw))
    img.load()
    if img.width < 300 or img.height < 180:
        raise RuntimeError(f"image too small {img.width}x{img.height}")
    if img.width / max(img.height, 1) > 5.5 or img.height / max(img.width, 1) > 3.0:
        raise RuntimeError(f"unusual aspect {img.width}x{img.height}")

    stem = f"{index:03d}_{safe_name(item['brand'])}_{safe_name(item['model'])}"
    image_path = IMG_DIR / f"{stem}.jpg"
    thumb_path = THUMB_DIR / f"{stem}.jpg"
    fit_on_white(img).save(image_path, quality=94)
    fit_on_white(img, (520, 390)).save(thumb_path, quality=90)
    seen_image_urls.add(item["image_url"])
    item["index"] = index
    item["image_path"] = f"images/{image_path.name}"
    item["thumb_path"] = f"thumbs/{thumb_path.name}"
    item["source_domain"] = urlparse(item["page_url"] or item["image_url"]).netloc
    item["original_size"] = f"{img.width}x{img.height}"
    return item


def draw_sheet(sheet_rows, output_path, cols=5, cell_w=330, cell_h=268):
    label_h = 54
    sheet = Image.new("RGB", (cols * cell_w, ((len(sheet_rows) + cols - 1) // cols) * cell_h), (241, 243, 240))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, row in enumerate(sheet_rows):
        col, r = i % cols, i // cols
        x, y = col * cell_w, r * cell_h
        img = Image.open(OUT / row["thumb_path"]).convert("RGB")
        img.thumbnail((cell_w - 26, cell_h - label_h - 12), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + (cell_w - img.width) // 2, y + 10))
        draw.text((x + 12, y + cell_h - label_h + 6), f"{int(row['index']):03d}. {row['brand']} - {row['model']}"[:48], fill=(20, 22, 20), font=font)
        draw.text((x + 12, y + cell_h - label_h + 26), row.get("form_note", "optical frame")[:52], fill=(88, 94, 86), font=font)
    sheet.save(output_path, quality=92)


def make_contact_sheets(rows):
    draw_sheet(rows, OUT / "contact_sheet.jpg")
    for offset in range(0, len(rows), 25):
        draw_sheet(rows[offset : offset + 25], OUT / f"contact_sheet_{offset // 25 + 1:02d}.jpg")


def write_html(rows):
    cards = []
    for row in rows:
        cards.append(f"""
      <article class="card" data-text="{html.escape((row['brand'] + ' ' + row['model'] + ' ' + row.get('form_note', '')).lower())}">
        <button class="pick" type="button">Pick</button>
        <img src="{row['image_path']}" alt="{html.escape(row['brand'] + ' ' + row['model'])}">
        <div class="meta">
          <span>{int(row['index']):03d}</span>
          <h2>{html.escape(row['brand'])}</h2>
          <p>{html.escape(row['model'])}</p>
          <small>{html.escape(row.get('form_note', 'optical frame'))}</small>
          <a href="{html.escape(row['page_url'])}" target="_blank" rel="noreferrer">source</a>
        </div>
      </article>""")
    doc = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Eyewear Form Research 300</title>
<style>
body{{margin:0;background:#f4f5f2;color:#171918;font-family:Arial,'Noto Sans KR',sans-serif}}
header{{position:sticky;top:0;z-index:2;background:rgba(244,245,242,.94);backdrop-filter:blur(10px);border-bottom:1px solid #d6dbd2;padding:14px 18px;display:flex;justify-content:space-between;gap:12px;align-items:center}}
h1{{font-size:18px;margin:0}} .tools{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}} input,button{{height:34px;border:1px solid #aeb8ad;background:#fff;border-radius:6px;padding:0 10px}}
main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px;padding:16px}}
.card{{position:relative;background:white;border:1px solid #d9ded6;border-radius:8px;overflow:hidden;min-height:288px}}
.card img{{width:100%;aspect-ratio:1.35/1;object-fit:contain;background:#fafbf9;border-bottom:1px solid #e4e8e1;display:block}}
.meta{{padding:9px 11px 12px}} h2{{font-size:14px;margin:4px 0 2px}} p{{margin:0;font-size:12px;line-height:1.35}} small{{display:block;margin-top:5px;color:#626c60;font-size:11px}} a{{display:inline-block;margin-top:7px;color:#245b7a;font-size:11px}}
.pick{{position:absolute;top:8px;right:8px}} .selected{{outline:3px solid #20251f}} .selected .pick{{background:#20251f;color:white}}
.hidden{{display:none}}
</style></head><body>
<header><h1>Eyewear Form Research 300 <span id="count"></span></h1><div class="tools"><input id="q" placeholder="brand / model / form"><button id="picked">Picked only</button><button id="export">Export picks</button></div></header>
<main>{''.join(cards)}</main>
<script>
const cards=[...document.querySelectorAll('.card')], q=document.querySelector('#q'), picked=document.querySelector('#picked'), count=document.querySelector('#count'); let only=false;
cards.forEach(c=>c.querySelector('.pick').onclick=()=>{{c.classList.toggle('selected'); apply();}});
function apply(){{const s=q.value.toLowerCase(); let visible=0; cards.forEach(c=>{{const show=c.dataset.text.includes(s)&&(!only||c.classList.contains('selected')); c.classList.toggle('hidden',!show); if(show) visible++;}}); count.textContent=`(${{visible}} / ${{cards.length}})`;}}
q.oninput=apply; picked.onclick=()=>{{only=!only; picked.textContent=only?'Show all':'Picked only'; apply();}};
document.querySelector('#export').onclick=()=>{{const rows=cards.filter(c=>c.classList.contains('selected')).map(c=>[...c.querySelectorAll('h2,p,small,a')].map(e=>`"${{e.textContent.trim().replaceAll('"','""')}}"`).join(',')); const blob=new Blob([rows.join('\\n')],{{type:'text/csv'}}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='selected_eyewear_forms.csv'; a.click();}};
apply();
</script></body></html>"""
    (OUT / "preference_board.html").write_text(doc, encoding="utf-8")


def write_indices(rows, failures):
    fields = ["index", "brand", "model", "form_note", "image_path", "thumb_path", "image_url", "page_url", "source_domain", "source_type", "original_size"]
    with (OUT / "metadata.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    with (OUT / "download_failures.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        fail_fields = ["brand", "model", "page_url", "image_url", "reason"]
        writer = csv.DictWriter(fh, fieldnames=fail_fields)
        writer.writeheader()
        for row in failures:
            writer.writerow({k: row.get(k, "") for k in fail_fields})
    with (OUT / "image_location_index.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        fieldnames = ["index", "brand", "model", "image_absolute_path", "source_url"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "index": row["index"],
                    "brand": row["brand"],
                    "model": row["model"],
                    "image_absolute_path": str((OUT / row["image_path"]).resolve()),
                    "source_url": row["page_url"],
                }
            )
    lines = ["# Eyewear Image Location Index 300", "", "| # | Brand | Product | Image file |", "|---:|---|---|---|"]
    for row in rows:
        image_path = (OUT / row["image_path"]).resolve()
        lines.append(f"| {int(row['index']):03d} | {row['brand']} | {row['model']} | [{image_path.name}]({image_path}) |")
    (OUT / "image_location_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    by_brand = {}
    for row in rows:
        by_brand[row["brand"]] = by_brand.get(row["brand"], 0) + 1
    brand_lines = "\n".join(f"- {brand}: {count}" for brand, count in sorted(by_brand.items()))
    (OUT / "README.md").write_text(
        f"# Eyewear Form Research 300\n\nGenerated on 2026-06-24.\n\nTotal usable product images: {len(rows)}.\nNew images beyond prior 100: {max(0, len(rows) - 100)}.\n\n{brand_lines}\n\nUse `preference_board.html` for quick personal form picks. Use `metadata.csv` and `image_location_index.csv` for source and file tracking. Images are for private research/reference; verify usage rights before public presentation.\n",
        encoding="utf-8",
    )


def main():
    rows, seen_images, seen_pages, seen_models = copy_existing_rows()
    failures = []
    candidates = collect_moscot_product_pages(limit=60) + collect_opsm_product_pages()
    print(f"START existing={len(rows)} candidates={len(candidates)}", flush=True)
    for candidate in candidates:
        page = candidate.get("page_url", "")
        key = (candidate.get("brand", ""), candidate.get("model", ""))
        if page in seen_pages or key in seen_models:
            continue
        seen_pages.add(page)
        seen_models.add(key)
        try:
            item = download_candidate(dict(candidate), len(rows) + 1, seen_images)
            rows.append(item)
            print(f"[{len(rows):03d}] saved {item['brand']} - {item['model']}", flush=True)
        except Exception as exc:
            failures.append({**candidate, "reason": str(exc)})
            print(f"missed {candidate.get('brand')} - {candidate.get('model')}: {exc}", flush=True)
        time.sleep(0.04)
        if len(rows) >= TARGET_TOTAL:
            break
    make_contact_sheets(rows)
    write_html(rows)
    write_indices(rows, failures)
    print(f"DONE total={len(rows)} new={max(0, len(rows)-100)} failures={len(failures)}", flush=True)


if __name__ == "__main__":
    main()
