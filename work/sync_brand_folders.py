import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "eyewear_form_research_300"
BY_BRAND = ROOT / "outputs" / "eyewear_form_research_300_by_brand"
META = DATA / "metadata.csv"


def assert_inside(path: Path, parent: Path) -> None:
    resolved = path.resolve()
    base = parent.resolve()
    if resolved != base and base not in resolved.parents:
        raise RuntimeError(f"refusing path outside target folder: {resolved}")


def safe_clear_folder(folder: Path) -> None:
    assert_inside(folder, BY_BRAND)
    if not folder.exists():
        return
    for child in folder.iterdir():
        assert_inside(child, BY_BRAND)
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> None:
    BY_BRAND.mkdir(parents=True, exist_ok=True)
    safe_clear_folder(BY_BRAND)

    with META.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    counts = {}
    for row in rows:
        brand = row["brand"]
        counts[brand] = counts.get(brand, 0) + 1
        brand_dir = BY_BRAND / brand
        brand_dir.mkdir(parents=True, exist_ok=True)
        src = DATA / row["image_path"]
        dst = brand_dir / f"{int(row['index']):03d}_{src.name}"
        shutil.copy2(src, dst)

    index_path = BY_BRAND / "brand_folder_index.csv"
    with index_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["brand", "count", "folder"])
        for brand in sorted(counts):
            writer.writerow([brand, counts[brand], str((BY_BRAND / brand).resolve())])

    print(f"synced brands={len(counts)} images={len(rows)}")


if __name__ == "__main__":
    main()
