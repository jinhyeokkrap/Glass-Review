import csv
import html
import re
import time
import urllib.request
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "eyewear_form_research_100"
IMG_DIR = OUT / "images"
THUMB_DIR = OUT / "thumbs"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
TARGET_COUNT = 100


OPSM_BRAND_PAGES = [
    ("Ray-Ban", "https://www.opsm.com.au/glasses/ray-ban"),
    ("Persol", "https://www.opsm.com.au/glasses/persol"),
    ("Oliver Peoples", "https://www.opsm.com.au/glasses/oliver-peoples"),
    ("Prada", "https://www.opsm.com.au/glasses/prada"),
    ("Gucci", "https://www.opsm.com.au/glasses/gucci"),
    ("Tom Ford", "https://www.opsm.com.au/glasses/tom-ford"),
    ("Versace", "https://www.opsm.com.au/glasses/versace"),
    ("Miu Miu", "https://www.opsm.com.au/glasses/miu-miu"),
    ("Burberry", "https://www.opsm.com.au/glasses/burberry"),
    ("Tiffany & Co.", "https://www.opsm.com.au/glasses/tiffany-&-co."),
    ("Giorgio Armani", "https://www.opsm.com.au/glasses/giorgio-armani"),
]

MOSCOT_COLLECTIONS = [
    ("MOSCOT", "https://moscot.com/collections/eyeglasses"),
    ("MOSCOT", "https://moscot.com/collections/all"),
]

MANUAL_DIRECT = [
    {
        "brand": "Oakley",
        "model": "Holbrook Low Bridge Fit OX8100F",
        "form_note": "sport square full-rim",
        "image_url": "https://assets.oakley.com/is/image/OakleyEYE/888392603012__STD__shad__fr.png",
        "page_url": "https://www.oakley.com/en-us/product/W0OX8100F?variant=888392603012",
        "source_type": "official",
    },
    {
        "brand": "Gentle Monster",
        "model": "Zin 01",
        "form_note": "minimal square",
        "image_url": "https://gm-prd-resource.gentlemonster.com/catalog/product/ZYYE799SURVC/ce740893-5a4c-43c6-9f10-c3a1bcc1118c/11003137_FRONT.jpg",
        "page_url": "https://www.gentlemonster.com/kr/ja/item/ZYYE799SURVC/zin01",
        "source_type": "official",
    },
    {
        "brand": "Gentle Monster",
        "model": "Alio GD1",
        "form_note": "combination square",
        "image_url": "https://gm-prd-resource.gentlemonster.com/catalog/product/194RVEG6I7XGB/e0a36042-2095-43f0-b716-0eb75d6de77e/11000251_FRONT.jpeg",
        "page_url": "https://www.gentlemonster.com/kr/ja/item/194RVEG6I7XGB/aliogd1",
        "source_type": "official",
    },
    {
        "brand": "Gentle Monster",
        "model": "Ojo 01",
        "form_note": "soft square acetate",
        "image_url": "https://gm-prd-resource.gentlemonster.com/catalog/product/SDFZSB9VJ282/202537fa-e60e-4e89-8ce7-a282c325e692/11003134_FRONT.jpg",
        "page_url": "https://www.gentlemonster.com/cn/zh-CN/item/SDFZSB9VJ282/ojo01",
        "source_type": "official",
    },
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


def model_from_opsm_url(url):
    parts = [p for p in urlparse(url).path.split("/") if p]
    if len(parts) >= 3:
        return clean_text(parts[-2])
    return clean_text(parts[-1])


def infer_form_note(model):
    lower = model.lower()
    if any(word in lower for word in ["round", "rund", "ov5183", "po3092"]):
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


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()[:96]


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
        for ref in refs:
            url = urljoin(page, html.unescape(ref)).split("#")[0]
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
        print(f"OPSM {brand}: {len(refs)} refs", flush=True)
    return items


def score_opsm_image(url):
    lower = url.lower()
    if "thumb" in lower:
        return -100
    score = 0
    if "__std__" in lower:
        score += 20
    if "__p21__" in lower:
        score += 14
    if "__noshad__fr" in lower:
        score += 50
    if "__shad__fr" in lower:
        score += 45
    if "__noshad__qt" in lower:
        score += 25
    if "__shad__qt" in lower:
        score += 20
    if "__shad__cfr" in lower:
        score += 12
    if "__shad__lt" in lower or "__shad__bk" in lower or "__shad__al" in lower:
        score -= 15
    if "wid=200" in lower:
        score -= 30
    return score


def extract_opsm_image(page_url):
    raw = fetch_html(page_url)
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
    urls = sorted(set(urls), key=score_opsm_image, reverse=True)
    return urls[0]


def collect_moscot_product_pages(limit=35):
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
                    "form_note": infer_form_note(handle) if handle not in ("lemtosh", "miltzen") else ("keyhole rounded square acetate" if handle == "lemtosh" else "round keyhole acetate"),
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
    urls = sorted(set(urls), key=lambda u: (0 if "width=480" in u or "_grande" in u else 1, len(u)))
    return urls[0]


def image_stats(img):
    rgb = img.convert("RGB").resize((1, 1))
    return rgb.getpixel((0, 0))


def fit_on_white(img, size=(760, 540)):
    img = ImageOps.exif_transpose(img).convert("RGBA")
    img.thumbnail((size[0] - 44, size[1] - 92), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (250, 251, 249, 255))
    x = (size[0] - img.width) // 2
    y = 30 + (size[1] - 92 - img.height) // 2
    canvas.alpha_composite(img, (x, y))
    return canvas.convert("RGB")


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
    if img.width / max(img.height, 1) > 5.2 or img.height / max(img.width, 1) > 3.0:
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


def make_contact_sheet(rows):
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
            draw.text((x + 12, y + cell_h - label_h + 6), f"{row['index']:03d}. {row['brand']} - {row['model']}"[:48], fill=(20, 22, 20), font=font)
            draw.text((x + 12, y + cell_h - label_h + 26), row["form_note"][:52], fill=(88, 94, 86), font=font)
        sheet.save(output_path, quality=92)

    cols = 5
    cell_w, cell_h = 330, 268
    label_h = 54
    draw_sheet(rows, OUT / "contact_sheet.jpg", cols, cell_w, cell_h)
    for offset in range(0, len(rows), 25):
        page_rows = rows[offset : offset + 25]
        page = offset // 25 + 1
        draw_sheet(page_rows, OUT / f"contact_sheet_{page:02d}.jpg", cols, cell_w, cell_h)


def write_html(rows):
    cards = []
    for row in rows:
        cards.append(f"""
      <article class="card" data-brand="{html.escape(row['brand'])}" data-text="{html.escape((row['brand'] + ' ' + row['model'] + ' ' + row['form_note']).lower())}">
        <button class="pick" type="button">Pick</button>
        <img src="{row['image_path']}" alt="{html.escape(row['brand'] + ' ' + row['model'])}">
        <div class="meta">
          <span>{row['index']:03d}</span>
          <h2>{html.escape(row['brand'])}</h2>
          <p>{html.escape(row['model'])}</p>
          <small>{html.escape(row['form_note'])}</small>
          <a href="{html.escape(row['page_url'])}" target="_blank" rel="noreferrer">source</a>
        </div>
      </article>""")
    doc = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Eyewear Form Research 100</title>
<style>
body{{margin:0;background:#f4f5f2;color:#171918;font-family:Arial,'Noto Sans KR',sans-serif}}
header{{position:sticky;top:0;z-index:2;background:rgba(244,245,242,.94);backdrop-filter:blur(10px);border-bottom:1px solid #d6dbd2;padding:14px 18px;display:flex;justify-content:space-between;gap:12px;align-items:center}}
h1{{font-size:18px;margin:0}} .tools{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}} input,button,select{{height:34px;border:1px solid #aeb8ad;background:#fff;border-radius:6px;padding:0 10px}}
main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px;padding:16px}}
.card{{position:relative;background:white;border:1px solid #d9ded6;border-radius:8px;overflow:hidden;min-height:288px}}
.card img{{width:100%;aspect-ratio:1.35/1;object-fit:contain;background:#fafbf9;border-bottom:1px solid #e4e8e1;display:block}}
.meta{{padding:9px 11px 12px}} h2{{font-size:14px;margin:4px 0 2px}} p{{margin:0;font-size:12px;line-height:1.35}} small{{display:block;margin-top:5px;color:#626c60;font-size:11px}} a{{display:inline-block;margin-top:7px;color:#245b7a;font-size:11px}}
.pick{{position:absolute;top:8px;right:8px}} .selected{{outline:3px solid #20251f}} .selected .pick{{background:#20251f;color:white}}
.hidden{{display:none}}
</style></head><body>
<header><h1>Eyewear Form Research 100 <span id="count"></span></h1><div class="tools"><input id="q" placeholder="brand / model / form"><button id="picked">Picked only</button><button id="export">Export picks</button></div></header>
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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    for folder in (IMG_DIR, THUMB_DIR):
        for old in folder.glob("*.jpg"):
            old.unlink()

    candidates = []
    candidates.extend(MANUAL_DIRECT)
    candidates.extend(collect_moscot_product_pages(limit=34))
    candidates.extend(collect_opsm_product_pages())

    rows = []
    failures = []
    seen_pages = set()
    seen_images = set()
    seen_brand_model = set()
    for candidate in candidates:
        key = (candidate.get("brand", ""), candidate.get("model", ""))
        page = candidate.get("page_url", "")
        if page in seen_pages or key in seen_brand_model:
            continue
        seen_pages.add(page)
        seen_brand_model.add(key)
        try:
            item = download_candidate(dict(candidate), len(rows) + 1, seen_images)
            rows.append(item)
            print(f"[{len(rows):03d}] saved {item['brand']} - {item['model']}", flush=True)
        except Exception as exc:
            failures.append({**candidate, "reason": str(exc)})
            print(f"missed {candidate.get('brand')} - {candidate.get('model')}: {exc}", flush=True)
        time.sleep(0.05)
        if len(rows) >= TARGET_COUNT:
            break

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

    make_contact_sheet(rows)
    write_html(rows)
    by_brand = {}
    for row in rows:
        by_brand[row["brand"]] = by_brand.get(row["brand"], 0) + 1
    brand_lines = "\n".join(f"- {brand}: {count}" for brand, count in sorted(by_brand.items()))
    (OUT / "README.md").write_text(
        f"# Eyewear Form Research 100\n\nGenerated on 2026-06-23.\n\nUsable product images: {len(rows)}.\n\n{brand_lines}\n\nUse `preference_board.html` for quick personal form picks. Use `metadata.csv` for source tracking. Images are for private research/reference; verify usage rights before public presentation.\n",
        encoding="utf-8",
    )
    print(f"DONE {len(rows)} images", flush=True)


if __name__ == "__main__":
    main()
