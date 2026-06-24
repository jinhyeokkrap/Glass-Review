import csv
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "eyewear_form_research_300"
BY_BRAND = ROOT / "outputs" / "eyewear_form_research_300_by_brand"
META = OUT / "metadata.csv"


def load_rows():
    with META.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def refresh_image_location_index(rows):
    csv_path = OUT / "image_location_index.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
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
                    "source_url": row.get("page_url", ""),
                }
            )

    lines = ["# Eyewear Image Location Index", "", "| # | Brand | Product | Image file |", "|---:|---|---|---|"]
    for row in rows:
        image_path = (OUT / row["image_path"]).resolve()
        lines.append(f"| {int(row['index']):03d} | {row['brand']} | {row['model']} | [{image_path.name}]({image_path}) |")
    (OUT / "image_location_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_brand_folder_index(rows):
    counts = Counter(row["brand"] for row in rows)
    with (BY_BRAND / "brand_folder_index.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["Brand", "Count", "FolderPath"])
        writer.writeheader()
        for brand in sorted(counts):
            writer.writerow({"Brand": brand, "Count": counts[brand], "FolderPath": str((BY_BRAND / brand).resolve())})


def draw_sheet(rows, output_path, cols=5, cell_w=330, cell_h=268):
    label_h = 54
    sheet_h = ((len(rows) + cols - 1) // cols) * cell_h
    sheet = Image.new("RGB", (cols * cell_w, sheet_h), (241, 243, 240))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, row in enumerate(rows):
        col, sheet_row = i % cols, i // cols
        x, y = col * cell_w, sheet_row * cell_h
        img = Image.open(OUT / row["thumb_path"]).convert("RGB")
        img.thumbnail((cell_w - 26, cell_h - label_h - 12), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + (cell_w - img.width) // 2, y + 10))
        label = f"{int(row['index']):03d}. {row['brand']} - {row['model']}"[:48]
        note = row.get("form_note", "")[:52]
        draw.text((x + 12, y + cell_h - label_h + 6), label, fill=(20, 22, 20), font=font)
        draw.text((x + 12, y + cell_h - label_h + 26), note, fill=(88, 94, 86), font=font)
    sheet.save(output_path, quality=92)


def refresh_contact_sheets(rows):
    draw_sheet(rows, OUT / "contact_sheet.jpg")
    for old_path in OUT.glob("contact_sheet_*.jpg"):
        old_path.unlink()
    for offset in range(0, len(rows), 25):
        draw_sheet(rows[offset : offset + 25], OUT / f"contact_sheet_{offset // 25 + 1:02d}.jpg")


def refresh_readme(rows):
    counts = Counter(row["brand"] for row in rows)
    lines = [
        "# Eyewear Form Research",
        "",
        "Generated on 2026-06-24.",
        "",
        f"Total usable product images: {len(rows)}.",
        "Original 300-image set is preserved in place; Gentle Monster was expanded after review.",
        "",
    ]
    lines.extend(f"- {brand}: {counts[brand]}" for brand in sorted(counts))
    lines.extend(
        [
            "",
            "Use `preference_board.html` for quick personal form picks. Use `metadata.csv` and `image_location_index.csv` for source and file tracking. Images are for private research/reference; verify usage rights before public presentation.",
        ]
    )
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    rows = load_rows()
    refresh_image_location_index(rows)
    refresh_brand_folder_index(rows)
    refresh_contact_sheets(rows)
    refresh_readme(rows)
    print(f"refreshed rows={len(rows)} gentle_monster={sum(1 for row in rows if row['brand'] == 'Gentle Monster')}")


if __name__ == "__main__":
    main()
