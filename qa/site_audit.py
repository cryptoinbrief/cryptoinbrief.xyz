import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://cryptoinbrief.xyz"
PAGES = {
    "index.html": ("en", f"{BASE_URL}/"),
    "crypto-summary.html": ("en", f"{BASE_URL}/crypto-summary.html"),
    "crypto-summary-ar.html": ("ar", f"{BASE_URL}/crypto-summary-ar.html"),
    "bitcoin-from-zero.html": ("en", f"{BASE_URL}/bitcoin-from-zero.html"),
    "bitcoin-from-zero-ar.html": ("ar", f"{BASE_URL}/bitcoin-from-zero-ar.html"),
    "bitcoin-whitepaper.html": ("en", f"{BASE_URL}/bitcoin-whitepaper.html"),
    "bitcoin-codebase.html": ("en", f"{BASE_URL}/bitcoin-codebase.html"),
    "bitcoin-vs-monero-whitepapers.html": ("en", f"{BASE_URL}/bitcoin-vs-monero-whitepapers.html"),
    "proof-of-stake.html": ("en", f"{BASE_URL}/proof-of-stake.html"),
    "solana.html": ("en", f"{BASE_URL}/solana.html"),
    "sui.html": ("en", f"{BASE_URL}/sui.html"),
    "monero-under-the-hood.html": ("en", f"{BASE_URL}/monero-under-the-hood.html"),
    "monero-from-zero-ar.html": ("ar", f"{BASE_URL}/monero-from-zero-ar.html"),
    "getting-monero.html": ("en", f"{BASE_URL}/getting-monero.html"),
    "crypto-terms.html": ("en", f"{BASE_URL}/crypto-terms.html"),
    "starting-with-crypto.html": ("en", f"{BASE_URL}/starting-with-crypto.html"),
    "dollar-yield.html": ("en", f"{BASE_URL}/dollar-yield.html"),
    "zcash.html": ("en", f"{BASE_URL}/zcash.html"),
    "zero-knowledge-from-zero.html": ("en", f"{BASE_URL}/zero-knowledge-from-zero.html"),
}
LEGACY_PAGE = "zcash-zk-proofs.html"
REQUIRED_META = {
    "description",
    "viewport",
    "author",
    "twitter:card",
    "twitter:title",
    "twitter:description",
    "twitter:image",
}
REQUIRED_OG = {
    "og:site_name",
    "og:type",
    "og:title",
    "og:description",
    "og:url",
    "og:image",
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.title_parts = []
        self.in_title = False
        self.h1_count = 0
        self.ids = []
        self.references = []
        self.meta = {}
        self.properties = {}
        self.canonical = []
        self.scripts = []
        self.current_script = None

    def handle_starttag(self, tag, attrs):
        values = {key: value or "" for key, value in attrs}
        if tag == "html":
            self.lang = values.get("lang", "")
        if tag == "title":
            self.in_title = True
        if tag == "h1":
            self.h1_count += 1
        if "id" in values:
            self.ids.append(values["id"])
        for key in ("href", "src"):
            if values.get(key):
                self.references.append(values[key])
        if tag == "meta":
            if values.get("name"):
                self.meta[values["name"].lower()] = values.get("content", "").strip()
            if values.get("property"):
                self.properties[values["property"].lower()] = values.get("content", "").strip()
        if tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonical.append(values.get("href", ""))
        if tag == "script":
            self.current_script = {"type": values.get("type", "").lower(), "src": values.get("src", ""), "text": []}

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.current_script is not None:
            self.current_script["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "script" and self.current_script is not None:
            self.current_script["text"] = "".join(self.current_script["text"])
            self.scripts.append(self.current_script)
            self.current_script = None

    @property
    def title(self):
        return "".join(self.title_parts).strip()


def error(errors, file_name, message):
    errors.append(f"{file_name}: {message}")


def warning(warnings, file_name, message):
    warnings.append(f"{file_name}: {message}")


def read_text(path, errors):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        error(errors, path.name, f"cannot read file: {exc}")
        return ""


def parse_page(path, errors):
    parser = PageParser()
    try:
        parser.feed(read_text(path, errors))
        parser.close()
    except Exception as exc:
        error(errors, path.name, f"cannot parse HTML: {exc}")
    return parser


def check_json_ld(file_name, parser, canonical, lang, errors):
    documents = []
    for script in parser.scripts:
        if script["type"] != "application/ld+json":
            continue
        try:
            documents.append(json.loads(script["text"]))
        except json.JSONDecodeError as exc:
            error(errors, file_name, f"invalid JSON-LD: {exc}")
    if not documents:
        error(errors, file_name, "missing JSON-LD")
        return
    document = documents[0]
    if not isinstance(document, dict):
        error(errors, file_name, "JSON-LD root must be an object")
        return
    author = document.get("author", {})
    if not isinstance(author, dict) or author.get("name") != "Moamen Basel" or author.get("url") != "https://moamenbasel.com":
        error(errors, file_name, "JSON-LD author must identify Moamen Basel and moamenbasel.com")
    if file_name == "index.html":
        if document.get("@type") != "WebSite" or document.get("url") != canonical:
            error(errors, file_name, "JSON-LD must describe the canonical WebSite")
    else:
        if document.get("@type") not in {"Article", "TechArticle"}:
            error(errors, file_name, "JSON-LD type must be Article or TechArticle")
        if document.get("mainEntityOfPage") != canonical:
            error(errors, file_name, f"JSON-LD mainEntityOfPage must be {canonical}")
        if document.get("inLanguage") != lang:
            error(errors, file_name, f"JSON-LD inLanguage must be {lang}")


def check_scripts(file_name, parser, node, errors, warnings):
    if not node:
        warning(warnings, file_name, "Node.js unavailable, skipped JavaScript syntax checks")
        return
    scripts = [script for script in parser.scripts if script["type"] not in {"application/ld+json", "application/json"}]
    for index, script in enumerate(scripts, start=1):
        if script["src"]:
            target, _ = local_target(ROOT / file_name, script["src"])
            if target is None or target.suffix.lower() not in {".js", ".mjs"} or not target.is_file():
                continue
            try:
                result = subprocess.run([node, "--check", str(target)], capture_output=True, text=True, timeout=20)
            except subprocess.TimeoutExpired:
                error(errors, file_name, f"script {script['src']} syntax check timed out")
            else:
                if result.returncode:
                    detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown syntax error"
                    error(errors, file_name, f"script {script['src']} failed syntax check: {detail}")
            continue
        source = script["text"]
        if not source.strip():
            continue
        suffix = ".mjs" if script["type"] == "module" else ".js"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=suffix, delete=False) as handle:
            handle.write(source)
            temp_path = Path(handle.name)
        try:
            result = subprocess.run([node, "--check", str(temp_path)], capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            error(errors, file_name, f"inline script {index} syntax check timed out")
        else:
            if result.returncode:
                detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown syntax error"
                error(errors, file_name, f"inline script {index} failed syntax check: {detail}")
        finally:
            temp_path.unlink(missing_ok=True)


def local_target(source_path, reference):
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith("//"):
        return None, ""
    if parsed.scheme in {"data", "mailto", "tel", "javascript"}:
        return None, ""
    raw_path = unquote(parsed.path)
    if not raw_path:
        target = source_path
    elif raw_path.startswith("/"):
        target = ROOT / raw_path.lstrip("/")
    else:
        target = source_path.parent / raw_path
    if raw_path.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target.resolve(), unquote(parsed.fragment)


def check_references(file_name, source_path, parser, parsed_pages, errors):
    for reference in parser.references:
        target, fragment = local_target(source_path, reference)
        if target is None:
            continue
        try:
            target.relative_to(ROOT)
        except ValueError:
            error(errors, file_name, f"local reference escapes repository root: {reference}")
            continue
        if target.name == LEGACY_PAGE:
            error(errors, file_name, f"canonical page links to legacy gateway: {reference}")
            continue
        if not target.exists():
            error(errors, file_name, f"missing local target: {reference}")
            continue
        if not fragment or target.suffix.lower() != ".html":
            continue
        target_parser = parsed_pages.get(target.name)
        if target_parser is None:
            target_parser = parse_page(target, errors)
            parsed_pages[target.name] = target_parser
        if fragment not in set(target_parser.ids):
            error(errors, file_name, f"missing fragment target: {reference}")


def check_page(file_name, lang, canonical, parser, errors, warnings):
    if parser.lang != lang:
        error(errors, file_name, f"expected html lang={lang}, found {parser.lang or 'missing'}")
    if not parser.title:
        error(errors, file_name, "missing title")
    elif file_name != "index.html" and "Crypto in Brief" not in parser.title:
        error(errors, file_name, "title does not include Crypto in Brief")
    if parser.h1_count != 1:
        error(errors, file_name, f"expected one h1, found {parser.h1_count}")
    duplicates = sorted(value for value, count in Counter(parser.ids).items() if count > 1)
    if duplicates:
        error(errors, file_name, f"duplicate ids: {', '.join(duplicates)}")
    missing_meta = sorted(key for key in REQUIRED_META if not parser.meta.get(key))
    if missing_meta:
        error(errors, file_name, f"missing metadata: {', '.join(missing_meta)}")
    missing_og = sorted(key for key in REQUIRED_OG if not parser.properties.get(key))
    if missing_og:
        error(errors, file_name, f"missing Open Graph metadata: {', '.join(missing_og)}")
    if parser.canonical != [canonical]:
        error(errors, file_name, f"canonical must be exactly {canonical}")
    if parser.properties.get("og:url") != canonical:
        error(errors, file_name, f"og:url must be {canonical}")
    if parser.meta.get("author") != "Moamen Basel":
        error(errors, file_name, "meta author must be Moamen Basel")
    description = parser.meta.get("description", "")
    if description and not 50 <= len(description) <= 220:
        warning(warnings, file_name, f"meta description length is {len(description)} characters")
    source = read_text(ROOT / file_name, errors)
    if "https://moamenbasel.com" not in source:
        error(errors, file_name, "missing moamenbasel.com authorship link")
    if "https://greycorelabs.com" not in source:
        error(errors, file_name, "missing Grey Core Labs credit link")
    check_json_ld(file_name, parser, canonical, lang, errors)


def xml_urls(path, selector, errors):
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        error(errors, path.name, f"invalid XML: {exc}")
        return set()
    return {element.text.strip() for element in tree.findall(selector) if element.text and element.text.strip()}


def check_discovery(errors):
    expected = {canonical for _, canonical in PAGES.values()}
    sitemap_urls = xml_urls(ROOT / "sitemap.xml", ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc", errors)
    missing = sorted(expected - sitemap_urls)
    extra = sorted(sitemap_urls - expected)
    if missing:
        error(errors, "sitemap.xml", f"missing canonical URLs: {', '.join(missing)}")
    if extra:
        error(errors, "sitemap.xml", f"unexpected URLs: {', '.join(extra)}")
    feed_urls = xml_urls(ROOT / "rss.xml", ".//item/link", errors)
    expected_feed = expected - {f"{BASE_URL}/"}
    if feed_urls != expected_feed:
        missing_feed = sorted(expected_feed - feed_urls)
        extra_feed = sorted(feed_urls - expected_feed)
        if missing_feed:
            error(errors, "rss.xml", f"missing essay URLs: {', '.join(missing_feed)}")
        if extra_feed:
            error(errors, "rss.xml", f"unexpected essay URLs: {', '.join(extra_feed)}")
    discovery_files = ["sitemap.xml", "rss.xml", "llms.txt", "llms-full.txt"]
    for name in discovery_files:
        text = read_text(ROOT / name, errors)
        if LEGACY_PAGE in text:
            error(errors, name, f"legacy page must not be discoverable: {LEGACY_PAGE}")
    for name in ("llms.txt", "llms-full.txt"):
        text = read_text(ROOT / name, errors)
        absent = sorted(url for url in expected if url not in text)
        if absent:
            error(errors, name, f"missing canonical URLs: {', '.join(absent)}")
    robots = read_text(ROOT / "robots.txt", errors)
    if "Sitemap: https://cryptoinbrief.xyz/sitemap.xml" not in robots:
        error(errors, "robots.txt", "missing absolute sitemap declaration")


def main():
    errors = []
    warnings = []
    parsed_pages = {}
    node = shutil.which("node")
    for file_name, (lang, canonical) in PAGES.items():
        path = ROOT / file_name
        if not path.is_file():
            error(errors, file_name, "canonical page is missing")
            continue
        parser = parse_page(path, errors)
        parsed_pages[file_name] = parser
        check_page(file_name, lang, canonical, parser, errors, warnings)
        check_scripts(file_name, parser, node, errors, warnings)
    for label, values in (
        ("title", {name: parser.title for name, parser in parsed_pages.items()}),
        ("meta description", {name: parser.meta.get("description", "") for name, parser in parsed_pages.items()}),
    ):
        counts = Counter(value for value in values.values() if value)
        for value, count in counts.items():
            if count > 1:
                names = ", ".join(sorted(name for name, candidate in values.items() if candidate == value))
                error(errors, "metadata", f"duplicate {label} across {names}")
    for file_name, parser in list(parsed_pages.items()):
        check_references(file_name, ROOT / file_name, parser, parsed_pages, errors)
    check_discovery(errors)
    for message in warnings:
        print(f"WARN  {message}")
    for message in errors:
        print(f"ERROR {message}")
    if errors:
        print(f"FAIL  {len(PAGES)} canonical pages checked, {len(errors)} errors, {len(warnings)} warnings")
        return 1
    print(f"PASS  {len(PAGES)} canonical pages checked, {len(warnings)} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
