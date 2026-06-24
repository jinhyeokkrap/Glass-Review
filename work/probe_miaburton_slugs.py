import re
import sys
import urllib.error
import urllib.request


SLUGS = sys.argv[1:]


def count_fronts(slug: str) -> tuple[int, str]:
    url = f"https://miaburton.com/en/eyeglasses/{slug}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
    try:
        raw = urllib.request.urlopen(req, timeout=18).read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as exc:
        return 0, f"http {exc.code}"
    except Exception as exc:
        return 0, type(exc).__name__
    return len(re.findall(r"front view", raw, flags=re.I)), "ok"


def main() -> None:
    for slug in SLUGS:
        count, status = count_fronts(slug)
        print(f"{slug}: {count} ({status})", flush=True)


if __name__ == "__main__":
    main()
