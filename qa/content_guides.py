#!/usr/bin/env python3
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "crypto-terms.html": {
        "needles": ["confirmation time"],
        "hrefs": [],
        "codes": [],
    },
    "starting-with-crypto.html": {
        "needles": [
            "Rabby",
            "MetaMask",
            "hardware",
            "Jupiter",
            "Phantom",
            "Etherscan",
            "confirmation time",
            "33760 Block Confirmations",
            "Finalized (MAX Confirmations)",
        ],
        "hrefs": [
            "https://www.ether.fi/@moon1337",
            "https://jupiter.go.link/7RRSd",
            "https://waitlist.arcus.xyz/s/TWITTER",
        ],
        "codes": ["56VLD9"],
    },
    "dollar-yield.html": {
        "needles": ["DefiLlama", "Ethena", "Kamino", "loop"],
        "hrefs": ["https://app.ethena.fi/join/urfcl"],
        "codes": [],
    },
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1_count = 0
        self.title_parts = []
        self.in_title = False
        self.images = []
        self.anchors = []
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        values = {key: value or "" for key, value in attrs}
        if tag == "title":
            self.in_title = True
        if tag == "h1":
            self.h1_count += 1
        if tag == "img" and values.get("src"):
            self.images.append(values["src"])
        if tag == "a" and values.get("href"):
            self.anchors.append((values.get("href"), values.get("rel", "")))

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        self.text_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    @property
    def title(self):
        return "".join(self.title_parts).strip()

    @property
    def text(self):
        return "".join(self.text_parts)


def local_target(source_path, reference):
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith("//"):
        return None
    raw_path = unquote(parsed.path)
    if not raw_path:
        return source_path
    if raw_path.startswith("/"):
        return ROOT / raw_path.lstrip("/")
    return (source_path.parent / raw_path).resolve()


def main():
    errors = []
    for name, spec in PAGES.items():
        path = ROOT / name
        if not path.is_file():
            errors.append(f"{name}: missing file")
            continue
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        if parser.h1_count != 1:
            errors.append(f"{name}: expected one h1, found {parser.h1_count}")
        if "Crypto in Brief" not in parser.title:
            errors.append(f"{name}: title missing Crypto in Brief")
        body = parser.text
        html = path.read_text(encoding="utf-8")
        for needle in spec["needles"]:
            if needle not in body and needle not in html:
                errors.append(f"{name}: missing text {needle!r}")
        for href in spec["hrefs"]:
            if href not in html:
                errors.append(f"{name}: missing href {href}")
        for code in spec["codes"]:
            if code not in html:
                errors.append(f"{name}: missing code {code}")
        for href, rel in parser.anchors:
            if href in spec["hrefs"] or "referral-link" in html and href.startswith("http") and any(
                href == item for item in spec["hrefs"]
            ):
                if "sponsored" not in rel.split():
                    if href in spec["hrefs"]:
                        errors.append(f"{name}: {href} missing sponsored rel")
        for href, rel in parser.anchors:
            if href in spec["hrefs"] and "sponsored" not in rel.split():
                errors.append(f"{name}: referral {href} lacks sponsored")
        for src in parser.images:
            target = local_target(path, src)
            if target is None:
                errors.append(f"{name}: hotlinked image {src}")
                continue
            if not target.is_file():
                errors.append(f"{name}: missing image file {src}")
    dollar = (ROOT / "dollar-yield.html").read_text(encoding="utf-8")
    if "defillama.com" not in dollar and "DefiLlama" not in dollar:
        errors.append("dollar-yield.html: missing DefiLlama or defillama.com")
    if "</tr\n" in dollar or "</tr<" in dollar:
        errors.append("dollar-yield.html: unclosed table row")
    starter = (ROOT / "starting-with-crypto.html").read_text(encoding="utf-8")
    if "Blockscout Ethereum transaction page" in starter:
        errors.append("starting-with-crypto.html: etherscan figure still describes Blockscout")
    if "cluster stats" in starter:
        errors.append("starting-with-crypto.html: solana figure still describes cluster stats")
    for message in errors:
        print(f"ERROR {message}")
    if errors:
        print(f"FAIL  {len(PAGES)} guide pages, {len(errors)} errors")
        return 1
    print(f"PASS  {len(PAGES)} guide pages, referrals, local images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
