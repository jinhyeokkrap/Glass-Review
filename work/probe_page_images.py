import html
import re
import sys
import urllib.request


def main() -> None:
    url = sys.argv[1]
    needle = sys.argv[2].lower() if len(sys.argv) > 2 else ""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
    raw = urllib.request.urlopen(req, timeout=24).read().decode("utf-8", "ignore")
    print(f"bytes={len(raw)}")
    count = 0
    for match in re.finditer(r"<img[^>]+>", raw, re.I):
        tag = html.unescape(match.group(0))
        if needle and needle not in tag.lower():
            continue
        print(tag[:1000])
        count += 1
        if count >= 30:
            break
    print(f"printed={count}")


if __name__ == "__main__":
    main()
