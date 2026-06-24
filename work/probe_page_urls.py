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
    urls = []
    for match in re.finditer(r"https?:\\/\\/[^\"'<> ]+|//[^\"'<> ]+\.(?:jpg|jpeg|png|webp)[^\"'<> ]*", raw, re.I):
        value = html.unescape(match.group(0)).replace("\\/", "/")
        if needle and needle not in value.lower():
            continue
        urls.append(value)
    seen = []
    for value in urls:
        if value not in seen:
            seen.append(value)
    for value in seen[:80]:
        print(value)
    print(f"unique={len(seen)}")


if __name__ == "__main__":
    main()
