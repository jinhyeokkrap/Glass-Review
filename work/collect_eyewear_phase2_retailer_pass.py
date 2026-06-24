import importlib.util
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("phase2", ROOT / "work" / "collect_eyewear_phase2.py")
phase2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase2)


RETAILER_DOMAINS = [
    "pretavoir.co.uk",
    "fashioneyewear.com",
    "smartbuyglasses.com",
    "eye-oo.com",
    "goodseeco.com",
    "misterspex.com",
    "edel-optics.com",
    "ssense.com",
]


RETAILER_BRANDS = [
    {"brand": "MYKITA", "count": 8, "note": "screwless / lightweight industrial optical frame", "queries": ["MYKITA eyeglasses", "MYKITA optical glasses", "MYKITA lite glasses"]},
    {"brand": "Silhouette", "count": 6, "note": "rimless lightweight optical frame", "queries": ["Silhouette eyeglasses", "Silhouette optical glasses", "Silhouette Titan Minimal Art"]},
    {"brand": "ic! berlin", "count": 6, "note": "screwless sheet-metal optical frame", "queries": ["ic berlin eyeglasses", "ic! berlin optical glasses"]},
    {"brand": "DITA", "count": 8, "note": "premium titanium / acetate optical frame", "queries": ["DITA eyeglasses", "DITA optical glasses"]},
    {"brand": "Matsuda", "count": 8, "note": "Japanese detailed metal / acetate optical frame", "queries": ["Matsuda eyeglasses", "Matsuda optical glasses"]},
    {"brand": "Masunaga", "count": 8, "note": "Japanese Sabae heritage optical frame", "queries": ["Masunaga eyeglasses", "Masunaga optical glasses"]},
    {"brand": "Jacques Marie Mage", "count": 8, "note": "bold sculpted acetate optical frame", "queries": ["Jacques Marie Mage eyeglasses", "JMM optical glasses"]},
    {"brand": "Warby Parker", "count": 8, "note": "mainstream DTC optical frame", "queries": ["Warby Parker eyeglasses", "Warby Parker optical glasses"]},
    {"brand": "PROJEKT PRODUKT", "count": 8, "note": "Korean contemporary optical frame", "queries": ["PROJEKT PRODUKT eyeglasses", "Projekt Produkt optical glasses"]},
    {"brand": "MANOMOS", "count": 6, "note": "Korean daily fashion optical frame", "queries": ["MANOMOS eyeglasses", "MANOMOS optical glasses"]},
    {"brand": "CARIN", "count": 6, "note": "Korean commercial fashion optical frame", "queries": ["CARIN eyeglasses", "CARIN optical glasses"]},
    {"brand": "LASH", "count": 6, "note": "Korean acetate / metal optical frame", "queries": ["LASH eyewear eyeglasses", "LASH optical glasses"]},
    {"brand": "STEALER", "count": 6, "note": "Korean edgy metal / fashion optical frame", "queries": ["STEALER eyewear eyeglasses", "STEALER optical glasses"]},
    {"brand": "MUZIK", "count": 6, "note": "Korean trend fashion optical frame", "queries": ["MUZIK eyewear eyeglasses", "MUZIK optical glasses"]},
    {"brand": "JINS", "count": 8, "note": "Japanese mass-market ergonomic optical frame", "queries": ["JINS eyeglasses", "JINS optical glasses", "JINS airframe"]},
    {"brand": "Zoff", "count": 8, "note": "Japanese mass-market optical frame", "queries": ["Zoff eyeglasses", "Zoff optical glasses"]},
    {"brand": "OWNDAYS", "count": 8, "note": "Asian accessible retail optical frame", "queries": ["OWNDAYS eyeglasses", "OWNDAYS optical glasses"]},
    {"brand": "Yellows Plus", "count": 6, "note": "refined Japanese thin metal / acetate optical frame", "queries": ["Yellows Plus eyeglasses", "Yellows Plus optical glasses"]},
    {"brand": "KameManNen", "count": 6, "note": "small round Japanese heritage metal optical frame", "queries": ["KameManNen eyeglasses", "Kame ManNen optical glasses"]},
    {"brand": "Ray-Ban Meta", "count": 4, "note": "mainstream AI camera glasses hardware reference", "queries": ["Ray-Ban Meta smart glasses", "Ray Ban Meta Wayfarer glasses"]},
    {"brand": "XREAL", "count": 4, "note": "consumer display glasses hardware reference", "queries": ["XREAL Air glasses", "XREAL glasses product"]},
    {"brand": "Even Realities", "count": 4, "note": "everyday AI display glasses hardware reference", "queries": ["Even Realities G1 glasses"]},
    {"brand": "Brilliant Labs", "count": 4, "note": "AI-first lightweight glasses hardware reference", "queries": ["Brilliant Labs Frame glasses"]},
    {"brand": "Solos", "count": 4, "note": "audio / AI smart glasses hardware reference", "queries": ["Solos AirGo smart glasses", "Solos smart glasses"]},
]


def main():
    for brand in RETAILER_BRANDS:
        brand["domains"] = RETAILER_DOMAINS
    phase2.BRANDS = RETAILER_BRANDS
    phase2.main()

    _, rows = phase2.load_metadata()
    counts = Counter(row["brand"] for row in rows)
    print("current_counts=" + ", ".join(f"{brand['brand']}:{counts[brand['brand']]}" for brand in RETAILER_BRANDS))


if __name__ == "__main__":
    main()
