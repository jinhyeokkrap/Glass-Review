import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "outputs" / "eyewear_brand_review_tool" / "index.html"
TOOL_DIR = TOOL.parent
META = ROOT / "outputs" / "eyewear_form_research_300" / "metadata.csv"


def main():
    html = TOOL.read_text(encoding="utf-8")
    match = re.search(r"const DATA = (\{.*?\});\n\s+const STORE_KEY", html, re.S)
    if not match:
        raise SystemExit("DATA block not found")
    data = json.loads(match.group(1))
    items = data["items"]
    expected = sum(1 for _ in META.open(encoding="utf-8-sig", newline="")) - 1
    if len(items) != expected:
        raise SystemExit(f"expected {expected} items, found {len(items)}")
    missing = []
    for item in items:
        for key in ("image", "thumb"):
            path = (TOOL_DIR / item[key]).resolve()
            if not path.exists():
                missing.append(str(path))
    if missing:
        raise SystemExit("missing image refs:\n" + "\n".join(missing[:10]))
    required = [
        "Brand Review",
        "CSV Export",
        "JSON Export",
        "localStorage",
        "detailEl.querySelectorAll",
        "ArrowRight",
        "imageModal",
        "openImageModal",
        "Save Picks by Brand",
        "showDirectoryPicker",
        "picked_by_brand",
    ]
    absent = [text for text in required if text not in html]
    if absent:
        raise SystemExit("missing required UI hooks: " + ", ".join(absent))
    print(f"ok items={len(items)} brands={len(data['brands'])}")


if __name__ == "__main__":
    main()
