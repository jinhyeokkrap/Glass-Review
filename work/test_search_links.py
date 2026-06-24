import html
import re
import urllib.parse
import urllib.request

queries = [
    "Ray-Ban RX3447V official eyeglasses",
    "Persol PO3007V official eyeglasses",
    "Moscot Lemtosh official eyeglasses",
]

for q in queries:
    url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(q)
    raw = urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=10
    ).read().decode("utf-8", "ignore")
    print("\nQUERY", q)
    for u in re.findall(r"https?://[^\"'<> ]+", raw):
        u = html.unescape(u)
        if any(domain in u.lower() for domain in ["ray-ban.com", "persol.com", "moscot.com"]):
            print(u[:260])
