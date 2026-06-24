import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "eyewear_form_research_100"
META = OUT / "metadata.csv"


def main():
    with META.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

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
                    "source_url": row["page_url"],
                }
            )

    lines = ["# Eyewear Image Location Index", "", "| # | Brand | Product | Image file |", "|---:|---|---|---|"]
    for row in rows:
        image_path = (OUT / row["image_path"]).resolve()
        lines.append(
            f"| {int(row['index']):03d} | {row['brand']} | {row['model']} | [{image_path.name}]({image_path}) |"
        )
    (OUT / "image_location_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
