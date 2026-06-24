import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "outputs" / "eyewear_form_research_300" / "metadata.csv"


def clean_lash_model(model: str, index: int) -> str:
    compact = re.sub(r"\s+", " ", model).strip()
    match = re.search(r"(Jack|August)\s+([A-Z])\s+Type\s+\1?\s*([A-Z]\d)", compact, re.I)
    if match:
        family, variant, color = match.groups()
        return f"{family.title()} {variant.upper()} Type {color.upper()}"
    match = re.search(r"(Jack|August).*?([A-Z]\d)", compact, re.I)
    if match:
        family, color = match.groups()
        return f"{family.title()} {color.upper()}"
    return f"LASH Optical {index:03d}"


def main() -> None:
    with META.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    lash_count = 0
    for row in rows:
        if row.get("brand") != "LASH":
            continue
        lash_count += 1
        row["model"] = clean_lash_model(row.get("model", ""), lash_count)

    with META.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"normalized LASH rows={lash_count}")


if __name__ == "__main__":
    main()
