import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "eyewear_form_research_300"
BY_BRAND = ROOT / "outputs" / "eyewear_form_research_300_by_brand"
META = DATA / "metadata.csv"
CANDIDATES = ROOT / "outputs" / "eyewear_brand_expansion_candidates.md"
OUT = ROOT / "outputs" / "eyewear_collection_status_2026-06-24.md"


def load_counts() -> tuple[int, dict[str, int]]:
    with META.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["brand"]] = counts.get(row["brand"], 0) + 1
    return len(rows), counts


def load_targets() -> list[tuple[str, int]]:
    text = CANDIDATES.read_text(encoding="utf-8")
    targets: list[tuple[str, int]] = []
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if not parts or parts[0] in {"Brand", "Brand / product family"}:
            continue
        if parts[-1].isdigit():
            targets.append((parts[0], int(parts[-1])))
    return targets


def main() -> None:
    total, counts = load_counts()
    targets = load_targets()
    target_names = [brand for brand, _ in targets]
    remaining = [(brand, counts.get(brand, 0), target) for brand, target in targets if counts.get(brand, 0) < target]
    covered_targets = [(brand, counts.get(brand, 0), target) for brand, target in targets if counts.get(brand, 0) >= target]
    extra_brands = sorted(brand for brand in counts if brand not in target_names)

    lines = [
        "# Eyewear Collection Status",
        "",
        "Updated: 2026-06-24",
        "",
        "## Current Finalized Batch",
        "",
        f"- Total front/reference images: {total}",
        f"- Brands in review tool: {len(counts)}",
        f"- Brand folders synced: {BY_BRAND}",
        "- Review tool: outputs/eyewear_brand_review_tool/index.html",
        "- Review tool zip: outputs/eyewear_brand_review_tool.zip",
        "",
        "## Included Brands",
        "",
    ]
    for brand in sorted(counts):
        lines.append(f"- {brand}: {counts[brand]}")

    lines.extend([
        "",
        "## Candidate Targets Reached",
        "",
    ])
    for brand, count, target in covered_targets:
        lines.append(f"- {brand}: {count}/{target}")

    lines.extend([
        "",
        "## Remaining Candidate Targets",
        "",
    ])
    for brand, count, target in remaining:
        lines.append(f"- {brand}: {count}/{target}")

    lines.extend([
        "",
        "## Notes",
        "",
        "- This batch stops at the current verified collection state by request.",
        "- Several remaining brands need different collection routes because official pages are JavaScript-heavy, blocked, or expose product images through APIs.",
        "- Some Etnia Barcelona and L.G.R official product images include a little temple perspective, but the front form is visible enough for silhouette review.",
        "- Metadata indexes may not be perfectly contiguous because misbranded rows were removed during quality cleanup; the review tool validates by item count and metadata rows.",
    ])

    if extra_brands:
        lines.extend(["", "## Additional Brands Beyond Candidate Plan", ""])
        for brand in extra_brands:
            lines.append(f"- {brand}: {counts[brand]}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"total={total} brands={len(counts)} remaining_targets={len(remaining)}")


if __name__ == "__main__":
    main()
