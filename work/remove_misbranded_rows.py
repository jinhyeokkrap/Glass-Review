import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "eyewear_form_research_300"
BY_BRAND = ROOT / "outputs" / "eyewear_form_research_300_by_brand"
META = DATA / "metadata.csv"
BAD_INDEXES = {
    416, 417, 418, 419, 420,
    421, 422, 423, 424, 425,
    441, 442, 443, 444, 445, 446,
    453, 454,
}


def safe_unlink(path: Path) -> None:
    resolved = path.resolve()
    if DATA.resolve() not in resolved.parents and BY_BRAND.resolve() not in resolved.parents:
        raise RuntimeError(f"refusing to delete outside output folders: {resolved}")
    if resolved.exists():
        resolved.unlink()


def main() -> None:
    with META.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    kept = []
    removed = []
    for row in rows:
        index = int(row["index"])
        if index not in BAD_INDEXES:
            kept.append(row)
            continue
        removed.append(row)
        for rel_key in ("image_path", "thumb_path"):
            rel = row.get(rel_key, "")
            if rel:
                safe_unlink(DATA / rel)
        brand_dir = BY_BRAND / row["brand"]
        for file in brand_dir.glob(f"{index:03d}_*"):
            safe_unlink(file)

    with META.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    print(f"removed={len(removed)} kept={len(kept)}")


if __name__ == "__main__":
    main()
