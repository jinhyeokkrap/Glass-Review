import html
import re
import sys
import urllib.request


def main() -> None:
    url = sys.argv[1]
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"},
    )
    raw = urllib.request.urlopen(req, timeout=24).read().decode("utf-8", "ignore")
    print(f"bytes={len(raw)}")
    for match in re.finditer(r"<img[^>]+>", raw, re.I):
        tag = html.unescape(match.group(0))
        if "front view" in tag.lower():
            print(tag[:900])


if __name__ == "__main__":
    main()
