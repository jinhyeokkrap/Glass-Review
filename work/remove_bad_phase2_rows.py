import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "eyewear_form_research_300"
BY_BRAND = ROOT / "outputs" / "eyewear_form_research_300_by_brand"
META = DATA / "metadata.csv"
BAD_INDEXES = {"329", "346"}


def delete_if_safe(path):
    path = path.resolve()
    data_root = DATA.resolve()
    brand_root = BY_BRAND.resolve()
    if (str(path).startswith(str(data_root)) or str(path).startswith(str(brand_root))) and path.exists():
        path.unlink()


def main():
    with META.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)
    keep = []
    removed = []
    for row in rows:
        if row["index"] in BAD_INDEXES:
            removed.append(row)
            delete_if_safe(DATA / row["image_path"])
            delete_if_safe(DATA / row["thumb_path"])
            brand_dir = BY_BRAND / row["brand"]
            for copied in brand_dir.glob(f"{int(row['index']):03d}_*.jpg"):
                delete_if_safe(copied)
        else:
            keep.append(row)
    with META.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in keep:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    print(f"removed={len(removed)} total={len(keep)}")


if __name__ == "__main__":
    main()
