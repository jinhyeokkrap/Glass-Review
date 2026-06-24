import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "eyewear_brand_review_tool" / "review_state.json"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: create_review_state_from_export.py <eyewear_review_export.json>")
    source = Path(sys.argv[1])
    rows = json.loads(source.read_text(encoding="utf-8"))
    state = {}
    for row in rows:
        item_id = str(row.get("id", "")).zfill(3)
        if not item_id.strip("0"):
            continue
        state[item_id] = {
            "verdict": row.get("verdict") or "",
            "rating": int(row.get("rating") or 0),
            "tags": row.get("tags") if isinstance(row.get("tags"), list) else [],
            "note": row.get("note") or "",
        }
    OUT.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {}
    for review in state.values():
        verdict = review.get("verdict") or "empty"
        counts[verdict] = counts.get(verdict, 0) + 1
    print(f"wrote={OUT}")
    print(f"items={len(state)} counts={counts}")


if __name__ == "__main__":
    main()
