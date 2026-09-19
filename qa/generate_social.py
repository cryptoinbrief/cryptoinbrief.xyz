from pathlib import Path

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[1]
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1200, "height": 630}, reduced_motion="reduce")
    page.goto("http://127.0.0.1:8934/", wait_until="networkidle")
    page.add_style_tag(content="""
        .shell {padding-inline:56px;max-width:none}
        .site-header {height:85px;border:0}
        .site-nav,.demo-controls,.intro-note,.learning-path,.library,.arabic,.site-footer,.demo-caption {display:none}
        .hero {padding:32px 0 0;gap:45px;grid-template-columns:1fr 1fr}
        .hero h1 {font-size:64px}
        .hero-copy>p:not(.eyebrow) {font-size:18px;max-width:33ch}
        .hero .cta,.hero .secondary-link {display:none}
        .hero-demo {box-shadow:none}
        .hero-demo .diagram {padding-block:27px}
        .eyebrow {font-size:11px}
    """)
    page.evaluate("document.fonts.ready")
    page.screenshot(path=str(root / "og.png"))
    browser.close()
print("Generated og.png from the site's real homepage interface.")
