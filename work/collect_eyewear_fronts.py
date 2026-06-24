import csv
import html
import json
import os
import re
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "eyewear_form_research"
IMG_DIR = OUT / "images"
THUMB_DIR = OUT / "thumbs"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


TARGETS = [
    # Classic optical icons
    ("Ray-Ban", "Wayfarer Ease Optics RB4340V", "thick square acetate"),
    ("Ray-Ban", "Clubmaster Optics RX5154", "browline combination"),
    ("Ray-Ban", "Round Metal Optics RX3447V", "round metal"),
    ("Ray-Ban", "Aviator Optics RX6489", "aviator metal"),
    ("Ray-Ban", "Hexagonal Optics RX6448", "geometric metal"),
    ("Oakley", "Holbrook RX", "sport square acetate"),
    ("Oakley", "Pitchman R", "round mixed material"),
    ("Oakley", "Centerboard", "soft rectangular"),
    ("Oakley", "Socket 5.5", "semi rimless performance"),
    ("Oakley", "Plank 2.0", "rectangular sport"),
    ("Persol", "PO3007V", "keyhole acetate"),
    ("Persol", "PO3092V", "round panto"),
    ("Persol", "PO5004VT", "metal bridge"),
    ("Persol", "PO3272V", "square acetate"),
    ("Oliver Peoples", "Gregory Peck OV5186", "round panto acetate"),
    ("Oliver Peoples", "O'Malley OV5183", "vintage round acetate"),
    ("Oliver Peoples", "Finley Esq OV5298U", "rectangular acetate"),
    ("Oliver Peoples", "Fairmont OV5219", "soft square acetate"),
    ("Moscot", "Lemtosh", "classic keyhole acetate"),
    ("Moscot", "Miltzen", "round keyhole acetate"),
    ("Moscot", "Zev", "round metal"),
    ("Moscot", "Dahven", "bold square acetate"),
    ("Warby Parker", "Haskell", "rounded square acetate"),
    ("Warby Parker", "Durand", "round acetate"),
    ("Warby Parker", "Percey", "panto acetate"),
    ("Warby Parker", "Wilkie", "rectangular acetate"),
    # Asian and trend-led brands
    ("Gentle Monster", "Zin 01", "minimal square"),
    ("Gentle Monster", "Alio GD1", "combination square"),
    ("Gentle Monster", "Jade 01", "bold rectangular"),
    ("Gentle Monster", "Mondo 01", "oversized square"),
    ("JINS", "Airframe Hingeless", "lightweight minimal"),
    ("JINS", "Classic Bold", "bold acetate"),
    ("JINS", "Combination Titanium", "mixed material"),
    ("Zoff", "Zoff SMART Skinny", "lightweight rectangular"),
    ("Zoff", "Zoff CLASSIC", "classic acetate"),
    ("Zoff", "United Arrows eyeglasses", "fashion collaboration"),
    ("Ace & Tate", "Neil", "panto acetate"),
    ("Ace & Tate", "Pierce", "square acetate"),
    ("Ace & Tate", "Saul", "round metal"),
    ("Ace & Tate", "Amy", "soft square acetate"),
    # Minimal / industrial / rimless
    ("MYKITA", "LITE Helmut", "thin metal panto"),
    ("MYKITA", "Mylon Marius", "technical square"),
    ("MYKITA", "No1 Achille", "stainless steel"),
    ("LINDBERG", "Air Titanium Rim", "rim wire minimal"),
    ("LINDBERG", "Strip Titanium", "sheet metal"),
    ("LINDBERG", "Acetanium", "acetate titanium hybrid"),
    ("Silhouette", "Titan Minimal Art", "rimless"),
    ("Silhouette", "Lite Spirit", "rimless"),
    ("Silhouette", "Momentum Aurum", "premium rimless"),
    ("ic! berlin", "The Lone Wolf", "sheet metal square"),
    ("ic! berlin", "Tijn", "thin metal panto"),
    ("ic! berlin", "Ralphi", "rectangular metal"),
    # Luxury fashion houses
    ("Tom Ford", "FT5401", "bold square acetate"),
    ("Tom Ford", "FT5629-B", "blue block rectangular"),
    ("Tom Ford", "FT5835-B", "geometric optical"),
    ("Prada", "PR 17WV", "bold square acetate"),
    ("Prada", "PR A01V", "modern rectangular"),
    ("Prada", "PR 16MV", "minimal rectangle"),
    ("Gucci", "GG0027O", "square acetate"),
    ("Gucci", "GG0459O", "round optical"),
    ("Gucci", "GG0958O", "oversized square"),
    ("Dior", "DiorBlackSuitO R1I", "thin rectangular"),
    ("Dior", "CD Diamond O S6I", "geometric optical"),
    ("Celine", "CL50049I", "bold rectangular"),
    ("Celine", "CL50105I", "cat eye optical"),
    ("Cartier", "CT0048O", "rimless luxury"),
    ("Cartier", "CT0292O", "pilot metal"),
]


DOMAIN_PREFERENCE = {
    "ray-ban.com": 10,
    "oakley.com": 10,
    "persol.com": 10,
    "oliverpeoples.com": 10,
    "moscot.com": 10,
    "warbyparker.com": 10,
    "gentlemonster.com": 10,
    "jins.com": 9,
    "zoff.com": 9,
    "aceandtate.com": 9,
    "mykita.com": 10,
    "lindberg.com": 10,
    "silhouette.com": 10,
    "ic-berlin.de": 10,
    "tomfordfashion.com": 10,
    "prada.com": 10,
    "gucci.com": 10,
    "dior.com": 10,
    "celine.com": 10,
    "cartier.com": 10,
    "lenscrafters.com": 6,
    "glassesusa.com": 5,
    "smartbuyglasses.com": 5,
    "fashioneyewear.com": 5,
    "pretavoir.co.uk": 5,
    "eyeglasses.com": 4,
}

BRAND_DOMAINS = {
    "Ray-Ban": ["ray-ban.com", "opsm.com.au", "lenscrafters.com", "sunglasshut.com", "smartbuyglasses.com"],
    "Oakley": ["oakley.com"],
    "Persol": ["persol.com", "sunglasshut.com", "lenscrafters.com", "smartbuyglasses.com"],
    "Oliver Peoples": ["oliverpeoples.com", "pretavoir.co.uk", "fashioneyewear.com"],
    "Moscot": ["moscot.com"],
    "Warby Parker": ["warbyparker.com"],
    "Gentle Monster": ["gentlemonster.com"],
    "JINS": ["jins.com", "jins-eyewear.com"],
    "Zoff": ["zoff.com"],
    "Ace & Tate": ["aceandtate.com"],
    "MYKITA": ["mykita.com"],
    "LINDBERG": ["lindberg.com"],
    "Silhouette": ["silhouette.com"],
    "ic! berlin": ["ic-berlin.de", "ic-berlin.com"],
    "Tom Ford": ["tomfordfashion.com", "fashioneyewear.com", "lenscrafters.com", "smartbuyglasses.com"],
    "Prada": ["prada.com", "lenscrafters.com", "fashioneyewear.com", "smartbuyglasses.com"],
    "Gucci": ["gucci.com", "lenscrafters.com", "fashioneyewear.com", "smartbuyglasses.com"],
    "Dior": ["dior.com", "fashioneyewear.com", "smartbuyglasses.com"],
    "Celine": ["celine.com", "fashioneyewear.com", "smartbuyglasses.com"],
    "Cartier": ["cartier.com", "fashioneyewear.com", "smartbuyglasses.com"],
}


def request_url(url: str, timeout=18) -> bytes:
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def bing_image_candidates(query: str, max_items=24):
    url = f"https://www.bing.com/images/search?q={quote_plus(query)}&form=HDRSC2&first=1"
    raw = request_url(url).decode("utf-8", errors="ignore")
    candidates = []
    for match in re.finditer(r'm="\{(.*?)\}"', raw):
        chunk = "{" + match.group(1) + "}"
        chunk = html.unescape(chunk)
        try:
            data = json.loads(chunk)
        except Exception:
            continue
        image_url = data.get("murl")
        page_url = data.get("purl") or data.get("p")
        if image_url:
            candidates.append({"image_url": image_url, "page_url": page_url})
        if len(candidates) >= max_items:
            break

    if not candidates:
        for image_url in re.findall(r'"murl":"(.*?)"', raw):
            candidates.append({"image_url": image_url.encode("utf-8").decode("unicode_escape"), "page_url": ""})
            if len(candidates) >= max_items:
                break
    return candidates


def domain_score(url: str) -> int:
    host = urlparse(url).netloc.lower().replace("www.", "")
    score = 0
    for domain, value in DOMAIN_PREFERENCE.items():
        if domain in host:
            score = max(score, value)
    bad_hosts = ["pinterest.", "facebook.", "instagram.", "youtube.", "tiktok.", "ebay.", "amazon."]
    if any(bad in host for bad in bad_hosts):
        score -= 8
    return score


def candidate_score(candidate, brand: str, model: str) -> int:
    image_url = candidate.get("image_url", "")
    page_url = candidate.get("page_url") or ""
    text = f"{image_url} {page_url}".lower()
    score = domain_score(image_url) + domain_score(page_url)
    for token in re.findall(r"[a-z0-9]+", brand.lower() + " " + model.lower()):
        if len(token) > 2 and token in text:
            score += 1
    if any(word in text for word in ["front", "optical", "eyeglass", "glasses", "rx", "frame"]):
        score += 2
    if any(word in text for word in ["side", "model-wearing", "lifestyle", "try-on", "sunglasses"]):
        score -= 2
    return score


def is_allowed_candidate(candidate, brand: str) -> bool:
    allowed_domains = BRAND_DOMAINS.get(brand, [])
    text = f"{candidate.get('image_url', '')} {candidate.get('page_url') or ''}".lower()
    return any(domain in text for domain in allowed_domains)


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return value[:90] or "item"


def download_image(url: str):
    raw = request_url(url, timeout=22)
    if len(raw) < 7000:
        raise ValueError("too small")
    img = Image.open(BytesIO(raw))
    img.load()
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    width, height = img.size
    if width < 240 or height < 180:
        raise ValueError(f"image too small {width}x{height}")
    if width / max(height, 1) > 3.2 or height / max(width, 1) > 3.2:
        raise ValueError(f"unusual aspect {width}x{height}")
    return img


def fit_on_white(img: Image.Image, size=(700, 520)):
    img = ImageOps.exif_transpose(img).convert("RGBA")
    img.thumbnail((size[0] - 40, size[1] - 78), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (255, 255, 255, 255))
    x = (size[0] - img.width) // 2
    y = 30 + (size[1] - 78 - img.height) // 2
    canvas.alpha_composite(img, (x, y))
    return canvas.convert("RGB")


def make_contact_sheet(rows):
    if not rows:
        return
    cols = 4
    cell_w, cell_h = 360, 290
    label_h = 52
    pad = 18
    font = ImageFont.load_default()
    total_rows = (len(rows) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, total_rows * cell_h), (245, 246, 247))
    draw = ImageDraw.Draw(sheet)

    for idx, row in enumerate(rows):
        col = idx % cols
        r = idx // cols
        x = col * cell_w
        y = r * cell_h
        try:
            img = Image.open(row["thumb_abs"]).convert("RGB")
        except Exception:
            continue
        img.thumbnail((cell_w - pad * 2, cell_h - label_h - pad), Image.Resampling.LANCZOS)
        ix = x + (cell_w - img.width) // 2
        iy = y + pad
        sheet.paste(img, (ix, iy))
        label = f'{idx + 1:02d}. {row["brand"]} - {row["model"]}'
        form = row["form_note"]
        draw.text((x + pad, y + cell_h - label_h + 8), label[:54], fill=(24, 24, 24), font=font)
        draw.text((x + pad, y + cell_h - label_h + 28), form[:58], fill=(92, 92, 92), font=font)

    sheet.save(OUT / "contact_sheet.jpg", quality=92)


def write_html(rows):
    cards = []
    for idx, row in enumerate(rows):
        img_rel = Path(row["image_path"]).as_posix()
        source = html.escape(row["page_url"] or row["image_url"])
        cards.append(
            f"""
      <article class="card" data-brand="{html.escape(row['brand'])}" data-form="{html.escape(row['form_note'])}">
        <button class="pick" type="button" aria-label="pick">Pick</button>
        <img src="{img_rel}" alt="{html.escape(row['brand'] + ' ' + row['model'])}">
        <div class="meta">
          <span class="num">{idx + 1:02d}</span>
          <h2>{html.escape(row['brand'])}</h2>
          <p class="model">{html.escape(row['model'])}</p>
          <p class="form">{html.escape(row['form_note'])}</p>
          <a href="{source}" target="_blank" rel="noreferrer">source</a>
        </div>
      </article>"""
        )

    html_doc = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Eyewear Form Preference Board</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, "Noto Sans KR", sans-serif;
      background: #f6f7f4;
      color: #181a1b;
    }}
    body {{ margin: 0; }}
    header {{
      position: sticky;
      top: 0;
      z-index: 2;
      display: flex;
      gap: 16px;
      align-items: center;
      justify-content: space-between;
      padding: 16px 22px;
      background: rgba(246, 247, 244, .94);
      border-bottom: 1px solid #d9ddd6;
      backdrop-filter: blur(10px);
    }}
    h1 {{ margin: 0; font-size: 18px; font-weight: 700; letter-spacing: 0; }}
    .tools {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
    input, button {{
      height: 36px;
      border: 1px solid #bfc7bd;
      background: white;
      border-radius: 6px;
      padding: 0 10px;
      font-size: 13px;
    }}
    button {{ cursor: pointer; }}
    main {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
      gap: 14px;
      padding: 18px;
    }}
    .card {{
      position: relative;
      background: white;
      border: 1px solid #d8ddd5;
      border-radius: 8px;
      overflow: hidden;
      min-height: 316px;
    }}
    .card img {{
      display: block;
      width: 100%;
      aspect-ratio: 1.28 / 1;
      object-fit: contain;
      background: #f4f5f3;
      border-bottom: 1px solid #e4e7e2;
    }}
    .meta {{ padding: 10px 12px 12px; }}
    .num {{ color: #738071; font-size: 12px; }}
    h2 {{ margin: 4px 0 2px; font-size: 15px; line-height: 1.2; }}
    p {{ margin: 0; }}
    .model {{ font-size: 13px; line-height: 1.35; }}
    .form {{ margin-top: 6px; color: #657062; font-size: 12px; line-height: 1.35; }}
    a {{ display: inline-block; margin-top: 8px; color: #245b7a; font-size: 12px; }}
    .pick {{
      position: absolute;
      top: 8px;
      right: 8px;
      height: 30px;
      border-color: #9aa79a;
      background: rgba(255, 255, 255, .92);
    }}
    .card.selected {{ outline: 3px solid #252b26; }}
    .card.selected .pick {{ background: #252b26; color: white; }}
    .hidden {{ display: none; }}
  </style>
</head>
<body>
  <header>
    <h1>Eyewear Form Preference Board</h1>
    <div class="tools">
      <input id="filter" type="search" placeholder="brand / model / form">
      <button id="showPicked" type="button">Picked only</button>
      <button id="export" type="button">Export picks</button>
    </div>
  </header>
  <main>
    {''.join(cards)}
  </main>
  <script>
    const cards = Array.from(document.querySelectorAll('.card'));
    const filter = document.querySelector('#filter');
    const showPicked = document.querySelector('#showPicked');
    let pickedOnly = false;
    cards.forEach(card => card.querySelector('.pick').addEventListener('click', () => card.classList.toggle('selected')));
    function applyFilter() {{
      const q = filter.value.trim().toLowerCase();
      cards.forEach(card => {{
        const text = card.innerText.toLowerCase() + ' ' + card.dataset.brand.toLowerCase() + ' ' + card.dataset.form.toLowerCase();
        const visible = (!q || text.includes(q)) && (!pickedOnly || card.classList.contains('selected'));
        card.classList.toggle('hidden', !visible);
      }});
    }}
    filter.addEventListener('input', applyFilter);
    showPicked.addEventListener('click', () => {{
      pickedOnly = !pickedOnly;
      showPicked.textContent = pickedOnly ? 'Show all' : 'Picked only';
      applyFilter();
    }});
    document.querySelector('#export').addEventListener('click', () => {{
      const rows = cards.filter(c => c.classList.contains('selected')).map(c => {{
        const bits = Array.from(c.querySelectorAll('h2,.model,.form,a')).map(el => el.textContent.trim());
        return bits.join(',');
      }});
      const blob = new Blob([rows.join('\\n')], {{type: 'text/csv'}});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'selected_eyewear_forms.csv';
      a.click();
    }});
  </script>
</body>
</html>"""
    (OUT / "preference_board.html").write_text(html_doc, encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    for folder in (IMG_DIR, THUMB_DIR):
        for old_file in folder.glob("*.jpg"):
            old_file.unlink()

    rows = []
    failures = []
    used_urls = set()

    for index, (brand, model, form_note) in enumerate(TARGETS, 1):
        domain_queries = [
            f'site:{domain} {brand} "{model}" eyeglasses optical frame front view product image'
            for domain in BRAND_DOMAINS.get(brand, [])[:3]
        ]
        base_query = f'{brand} "{model}" eyeglasses optical frame front view product image official'
        fallback_query = f'{brand} {model} glasses front view product image'
        candidates = []
        for query in (*domain_queries, base_query, fallback_query):
            try:
                candidates.extend(bing_image_candidates(query))
            except Exception as exc:
                failures.append({"brand": brand, "model": model, "reason": f"search failed: {exc}"})
            time.sleep(0.15)

        unique = []
        seen = set()
        for candidate in candidates:
            image_url = candidate.get("image_url", "")
            if not image_url or image_url in seen or image_url in used_urls:
                continue
            if not is_allowed_candidate(candidate, brand):
                continue
            seen.add(image_url)
            unique.append(candidate)
        unique.sort(key=lambda c: candidate_score(c, brand, model), reverse=True)

        saved = None
        for candidate in unique[:18]:
            image_url = candidate["image_url"]
            try:
                img = download_image(image_url)
            except Exception:
                continue
            used_urls.add(image_url)
            stem = f"{index:02d}_{safe_name(brand)}_{safe_name(model)}"
            image_path = IMG_DIR / f"{stem}.jpg"
            thumb_path = THUMB_DIR / f"{stem}.jpg"
            fit_on_white(img).save(image_path, quality=94)
            fit_on_white(img, size=(520, 390)).save(thumb_path, quality=90)
            saved = {
                "index": index,
                "brand": brand,
                "model": model,
                "form_note": form_note,
                "image_path": f"images/{image_path.name}",
                "thumb_path": f"thumbs/{thumb_path.name}",
                "image_abs": str(image_path),
                "thumb_abs": str(thumb_path),
                "image_url": image_url,
                "page_url": candidate.get("page_url") or "",
                "source_domain": urlparse(candidate.get("page_url") or image_url).netloc,
            }
            print(f"[{index:02d}] saved {brand} - {model}", flush=True)
            break

        if saved:
            rows.append(saved)
        else:
            failures.append({"brand": brand, "model": model, "reason": "no usable image downloaded"})
            print(f"[{index:02d}] missed {brand} - {model}", flush=True)

    with (OUT / "metadata.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        fields = [
            "index",
            "brand",
            "model",
            "form_note",
            "image_path",
            "thumb_path",
            "image_url",
            "page_url",
            "source_domain",
        ]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})

    with (OUT / "download_failures.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["brand", "model", "reason"])
        writer.writeheader()
        writer.writerows(failures)

    make_contact_sheet(rows)
    write_html(rows)

    readme = f"""# Eyewear Form Research Starter Pack

Generated on 2026-06-23.

- Downloaded usable front/reference images: {len(rows)}
- Missed targets: {len(failures)}
- Use `preference_board.html` for quick form picking.
- Use `metadata.csv` for source tracking and later refinement.

This is an initial broad collection for private design research. Verify usage rights before including any image in public-facing decks.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
