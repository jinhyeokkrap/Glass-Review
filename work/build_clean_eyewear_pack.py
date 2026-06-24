import csv
import html
import re
import urllib.request
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "eyewear_form_research_clean"
IMG_DIR = OUT / "images"
THUMB_DIR = OUT / "thumbs"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


DIRECT_SOURCES = [
    {
        "brand": "Ray-Ban",
        "model": "Wayfarer Ease Optics RB4340V",
        "form_note": "classic thick square acetate",
        "image_url": "https://assets2.opsm.com/cdn-record-files-pi/e1c054ac-1a00-4bcd-8570-a72b00a745c8/832cff83-4d58-4abf-8e7f-acfe00554206/0RX4340V__2000__STD__shad__qt.png?impolicy=OP_PDP",
        "page_url": "https://www.ray-ban.com/usa/eyeglasses/RX4340V%20UNISEX%20wayfarer%20ease%20optics-black/8053672808469",
    },
    {
        "brand": "Ray-Ban",
        "model": "Clubmaster Optics RX5154",
        "form_note": "browline combination",
        "image_url": "https://assets2.opsm.com/prod-onecp-record-files/pieyewear/524f84cb-313d-4c36-9d57-b35d00ca73fb/0RX5154__2000__STD__shad__qt.png?impolicy=OP_PDP",
        "page_url": "https://www.ray-ban.com/usa/eyeglasses/RX5154%20UNISEX%20clubmaster%20optics-polished%20black/805289270102",
    },
    {
        "brand": "Oakley",
        "model": "Holbrook Low Bridge Fit OX8100F",
        "form_note": "sport square full-rim",
        "image_url": "https://assets.oakley.com/is/image/OakleyEYE/888392603012__STD__shad__fr.png",
        "page_url": "https://www.oakley.com/en-us/product/W0OX8100F?variant=888392603012",
    },
]

PAGE_SOURCES = [
    ("Gentle Monster", "Zin 01", "minimal square", "https://www.gentlemonster.com/kr/ja/item/ZYYE799SURVC/zin01", "_FRONT"),
    ("Gentle Monster", "Alio GD1", "combination square", "https://www.gentlemonster.com/kr/ja/item/194RVEG6I7XGB/aliogd1", "_FRONT"),
    ("Gentle Monster", "Ojo 01", "soft square acetate", "https://www.gentlemonster.com/cn/zh-CN/item/SDFZSB9VJ282/ojo01", "_FRONT"),
    ("Gentle Monster", "Matiny 01", "narrow rectangular", "https://www.gentlemonster.com/us/en/item/MZ8998WXRENN/matiny01", "_FRONT"),
    ("MOSCOT", "LEMTOSH", "keyhole rounded square acetate", "https://moscot.com/products/lemtosh", "pos-2"),
    ("MOSCOT", "MILTZEN", "round keyhole acetate", "https://moscot.com/products/miltzen", "pos-2"),
    ("MOSCOT", "ZEV", "round metal", "https://moscot.com/products/zev", "pos-2"),
    ("MOSCOT", "DAHVEN", "bold square acetate", "https://moscot.com/products/dahven", "pos-2"),
    ("MOSCOT", "NEBB", "rectangular acetate", "https://moscot.com/products/nebb", "pos-2"),
    ("MOSCOT", "YONTIF", "round panto acetate", "https://moscot.com/products/yontif", "pos-2"),
    ("MOSCOT", "MAYDELA", "soft square acetate", "https://moscot.com/products/maydela", "pos-2"),
    ("MOSCOT", "ZOLMAN", "round bold acetate", "https://moscot.com/products/zolman", "pos-2"),
    ("MOSCOT", "SHTARKER", "rectangular keyhole acetate", "https://moscot.com/products/shtarker", "pos-2"),
    ("MOSCOT", "YUKEL", "browline combination", "https://moscot.com/products/yukel", "pos-2"),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=18) as resp:
        return resp.read()


def fetch_html(url):
    return get(url).decode("utf-8", "ignore")


def extract_image_url(page_url, marker):
    raw = fetch_html(page_url)
    urls = []
    for value in re.findall(r"https?://[^\"'<> )]+", raw):
        value = html.unescape(value)
        lower = value.lower()
        if marker.lower() in lower and any(ext in lower for ext in [".jpg", ".jpeg", ".png"]):
            if "favicon" not in lower and "campaign" not in lower and "look_book" not in lower:
                urls.append(value)
    if not urls:
        raise RuntimeError(f"no image url found: {page_url}")
    if "moscot.com" in page_url:
        urls.sort(key=lambda u: (0 if "width=480" in u or "_grande" in u else 1, len(u)))
    return urls[0].replace("http://", "https://")


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()[:80]


def fit_on_white(img, size=(760, 540)):
    img = ImageOps.exif_transpose(img).convert("RGBA")
    img.thumbnail((size[0] - 44, size[1] - 92), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (250, 251, 249, 255))
    x = (size[0] - img.width) // 2
    y = 30 + (size[1] - 92 - img.height) // 2
    canvas.alpha_composite(img, (x, y))
    return canvas.convert("RGB")


def download_and_save(item, index):
    raw = get(item["image_url"])
    img = Image.open(BytesIO(raw))
    img.load()
    if img.width < 120 or img.height < 90:
        raise RuntimeError("image too small")
    stem = f"{index:02d}_{safe_name(item['brand'])}_{safe_name(item['model'])}"
    image_path = IMG_DIR / f"{stem}.jpg"
    thumb_path = THUMB_DIR / f"{stem}.jpg"
    fit_on_white(img).save(image_path, quality=94)
    fit_on_white(img, (520, 390)).save(thumb_path, quality=90)
    item["index"] = index
    item["image_path"] = f"images/{image_path.name}"
    item["thumb_path"] = f"thumbs/{thumb_path.name}"
    item["source_domain"] = urlparse(item["page_url"] or item["image_url"]).netloc
    return item


def make_contact_sheet(rows):
    cols = 4
    cell_w, cell_h = 390, 310
    label_h = 58
    sheet = Image.new("RGB", (cols * cell_w, ((len(rows) + cols - 1) // cols) * cell_h), (241, 243, 240))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, row in enumerate(rows):
        col, r = i % cols, i // cols
        x, y = col * cell_w, r * cell_h
        img = Image.open(OUT / row["thumb_path"]).convert("RGB")
        img.thumbnail((cell_w - 28, cell_h - label_h - 12), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + (cell_w - img.width) // 2, y + 12))
        draw.text((x + 16, y + cell_h - label_h + 8), f"{row['index']:02d}. {row['brand']} - {row['model']}"[:56], fill=(20, 22, 20), font=font)
        draw.text((x + 16, y + cell_h - label_h + 30), row["form_note"][:62], fill=(92, 98, 90), font=font)
    sheet.save(OUT / "contact_sheet.jpg", quality=92)


def write_html(rows):
    cards = []
    for row in rows:
        cards.append(f"""
      <article class="card">
        <button class="pick" type="button">Pick</button>
        <img src="{row['image_path']}" alt="{html.escape(row['brand'] + ' ' + row['model'])}">
        <div class="meta">
          <span>{row['index']:02d}</span>
          <h2>{html.escape(row['brand'])}</h2>
          <p>{html.escape(row['model'])}</p>
          <small>{html.escape(row['form_note'])}</small>
          <a href="{html.escape(row['page_url'])}" target="_blank" rel="noreferrer">source</a>
        </div>
      </article>""")
    doc = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clean Eyewear Front Board</title>
<style>
body{{margin:0;background:#f4f5f2;color:#171918;font-family:Arial,'Noto Sans KR',sans-serif}}
header{{position:sticky;top:0;background:rgba(244,245,242,.94);backdrop-filter:blur(10px);border-bottom:1px solid #d6dbd2;padding:14px 18px;display:flex;justify-content:space-between;gap:12px;align-items:center}}
h1{{font-size:18px;margin:0}} input,button{{height:34px;border:1px solid #aeb8ad;background:#fff;border-radius:6px;padding:0 10px}}
main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;padding:16px}}
.card{{position:relative;background:white;border:1px solid #d9ded6;border-radius:8px;overflow:hidden}}
.card img{{width:100%;aspect-ratio:1.35/1;object-fit:contain;background:#fafbf9;border-bottom:1px solid #e4e8e1;display:block}}
.meta{{padding:10px 12px 12px}} h2{{font-size:15px;margin:4px 0 2px}} p{{margin:0;font-size:13px}} small{{display:block;margin-top:6px;color:#626c60}} a{{display:inline-block;margin-top:8px;color:#245b7a;font-size:12px}}
.pick{{position:absolute;top:8px;right:8px}} .selected{{outline:3px solid #20251f}} .selected .pick{{background:#20251f;color:white}}
.hidden{{display:none}}
</style></head><body>
<header><h1>Clean Eyewear Front Board</h1><div><input id="q" placeholder="filter"><button id="picked">Picked only</button></div></header>
<main>{''.join(cards)}</main>
<script>
const cards=[...document.querySelectorAll('.card')], q=document.querySelector('#q'), picked=document.querySelector('#picked'); let only=false;
cards.forEach(c=>c.querySelector('.pick').onclick=()=>c.classList.toggle('selected'));
function apply(){{const s=q.value.toLowerCase(); cards.forEach(c=>c.classList.toggle('hidden',(!c.innerText.toLowerCase().includes(s))||(only&&!c.classList.contains('selected'))));}}
q.oninput=apply; picked.onclick=()=>{{only=!only; picked.textContent=only?'Show all':'Picked only'; apply();}};
</script></body></html>"""
    (OUT / "preference_board.html").write_text(doc, encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    for folder in (IMG_DIR, THUMB_DIR):
        for old in folder.glob("*.jpg"):
            old.unlink()

    sources = [dict(item) for item in DIRECT_SOURCES]
    for brand, model, form_note, page_url, marker in PAGE_SOURCES:
        try:
            image_url = extract_image_url(page_url, marker)
            sources.append({"brand": brand, "model": model, "form_note": form_note, "image_url": image_url, "page_url": page_url})
        except Exception as exc:
            print(f"missed {brand} {model}: {exc}", flush=True)

    rows = []
    failures = []
    for item in sources:
        try:
            rows.append(download_and_save(item, len(rows) + 1))
            print(f"saved {rows[-1]['brand']} - {rows[-1]['model']}", flush=True)
        except Exception as exc:
            failures.append({**item, "reason": str(exc)})
            print(f"failed {item['brand']} - {item['model']}: {exc}", flush=True)

    with (OUT / "metadata.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        fields = ["index", "brand", "model", "form_note", "image_path", "thumb_path", "image_url", "page_url", "source_domain"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    with (OUT / "download_failures.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        fields = ["brand", "model", "image_url", "page_url", "reason"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in failures:
            writer.writerow({k: row.get(k, "") for k in fields})
    make_contact_sheet(rows)
    write_html(rows)
    (OUT / "README.md").write_text(
        f"# Clean Eyewear Front Board\n\nGenerated on 2026-06-23.\n\nUsable official/front-oriented images: {len(rows)}.\n\nUse `preference_board.html` for quick personal form picks. Use `metadata.csv` for source tracking.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
