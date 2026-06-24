import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "eyewear_form_research_100"


def draw_sheet(rows, output_path, cols=5, cell_w=330, cell_h=268):
    label_h = 54
    sheet = Image.new("RGB", (cols * cell_w, ((len(rows) + cols - 1) // cols) * cell_h), (241, 243, 240))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, row in enumerate(rows):
        col, r = i % cols, i // cols
        x, y = col * cell_w, r * cell_h
        img = Image.open(OUT / row["thumb_path"]).convert("RGB")
        img.thumbnail((cell_w - 26, cell_h - label_h - 12), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + (cell_w - img.width) // 2, y + 10))
        draw.text((x + 12, y + cell_h - label_h + 6), f"{int(row['index']):03d}. {row['brand']} - {row['model']}"[:48], fill=(20, 22, 20), font=font)
        draw.text((x + 12, y + cell_h - label_h + 26), row["form_note"][:52], fill=(88, 94, 86), font=font)
    sheet.save(output_path, quality=92)


def main():
    with (OUT / "metadata.csv").open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    draw_sheet(rows, OUT / "contact_sheet.jpg")
    for offset in range(0, len(rows), 25):
        draw_sheet(rows[offset : offset + 25], OUT / f"contact_sheet_{offset // 25 + 1:02d}.jpg")


if __name__ == "__main__":
    main()
