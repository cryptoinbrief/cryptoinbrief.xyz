import argparse
import hashlib
import json
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "index.html",
    "crypto-summary.html",
    "crypto-summary-ar.html",
    "bitcoin-from-zero.html",
    "bitcoin-from-zero-ar.html",
    "bitcoin-whitepaper.html",
    "bitcoin-codebase.html",
    "bitcoin-vs-monero-whitepapers.html",
    "proof-of-stake.html",
    "solana.html",
    "sui.html",
    "monero-under-the-hood.html",
    "monero-from-zero-ar.html",
    "getting-monero.html",
    "zcash.html",
    "zero-knowledge-from-zero.html",
]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@contextmanager
def local_server():
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(ROOT), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def page_metrics(page):
    return page.evaluate(
        """() => ({
            innerWidth,
            documentWidth: document.documentElement.scrollWidth,
            bodyWidth: document.body.scrollWidth,
            brokenImages: [...document.images]
                .filter(image => image.complete && image.naturalWidth === 0)
                .map(image => image.getAttribute('src'))
        })"""
    )


def verify_theme(page, selector):
    button = page.locator(selector)
    require(button.count() == 1, f"missing theme control {selector}")
    before = page.locator("html").get_attribute("data-theme")
    button.click()
    after = page.locator("html").get_attribute("data-theme")
    require(after in {"light", "dark"} and after != before, f"theme did not change from {before}")
    page.reload(wait_until="networkidle")
    require(page.locator("html").get_attribute("data-theme") == after, "theme did not persist after reload")


def verify_diagram_zoom(page):
    expand = page.locator(".expand-diagram").first
    require(expand.count() == 1, "missing diagram zoom control")
    expand.scroll_into_view_if_needed()
    expand.click()
    require(page.locator("dialog[open] figure").count() == 1, "diagram dialog did not open")
    page.keyboard.press("Escape")
    require(page.locator("dialog[open]").count() == 0, "diagram dialog did not close on Escape")
    require(page.locator("main .expand-diagram").count() > 0, "diagram did not return to the article")


def verify_support(page):
    trigger = page.locator(".support-trigger")
    require(trigger.count() == 1, "missing support trigger")
    trigger.click()
    require(page.locator("dialog.support-dialog[open]").count() == 1, "support dialog did not open")
    require(page.locator(".support-tab").count() == 7, "support currency list is incomplete")
    referrals = page.locator(".support-referral-links a")
    require(referrals.count() == 2, "support referral links are incomplete")
    for index in range(referrals.count()):
        require("sponsored" in (referrals.nth(index).get_attribute("rel") or "").split(), "referral link lacks sponsored disclosure")
    page.keyboard.press("Escape")
    require(page.locator("dialog.support-dialog[open]").count() == 0, "support dialog did not close")


def verify_homepage(page):
    demo = page.locator("#payment-demo")
    tamper = page.locator("#demo-tamper")
    tamper.wait_for(state="visible")
    page.wait_for_function("() => !document.getElementById('demo-tamper').disabled")
    tamper.click()
    page.wait_for_function(
        "() => document.getElementById('payment-demo').dataset.proof === 'invalid'"
    )
    require(page.locator("#proof-result").inner_text() == "Signature rejected", "tampered P-256 signature was not rejected")
    require((page.locator("#alex-balance").text_content() or "").startswith("10 "), "rejected payment changed Alex's balance")
    require((page.locator("#sam-balance").text_content() or "").startswith("0 "), "rejected payment changed Sam's balance")
    tamper.click()
    page.wait_for_function(
        "() => document.getElementById('payment-demo').dataset.proof === 'valid'"
    )
    page.locator("[data-go-step='3']").click()
    require(page.locator("#proof-result").inner_text() == "Signature verified", "restored P-256 signature did not verify")
    require((page.locator("#sam-balance").text_content() or "").startswith("1 "), "verified payment did not update Sam's balance")
    page.locator("#demo-next").click()
    require(demo.get_attribute("data-step") == "0", "homepage next-step wraparound failed")
    page.locator("[data-go-step='2']").click()
    page.locator("[data-network='ethereum']").click()
    require("validator" in page.locator("#step-title").inner_text().lower(), "Ethereum network control failed")
    page.locator("[data-network='solana']").click()
    require("leader" in page.locator("#step-title").inner_text().lower(), "Solana network control failed")
    page.locator("[data-filter='privacy']").click()
    require(page.locator(".topic:visible").count() == 5, "privacy filter returned the wrong guides")
    page.locator("#topic-search").fill("zcash")
    require(page.locator(".topic:visible").count() == 1, "topic search did not narrow to Zcash")
    page.locator("#topic-search").fill("")
    page.locator("[data-filter='all']").click()
    require(page.locator(".topic:visible").count() == 12, "all-guides filter did not restore the library")


def verify_bitcoin_hash(page):
    value = "Crypto in Brief WebKit SHA-256 smoke"
    expected = hashlib.sha256(value.encode()).hexdigest()
    page.locator("#hin").fill(value)
    page.wait_for_function(
        "expected => document.getElementById('hout')?.textContent.trim() === expected",
        arg=expected,
        timeout=10000,
    )
    require(page.locator("#hout").inner_text().strip() == expected, "Bitcoin WebCrypto hash output is incorrect")


def run():
    results = []
    failures = []
    with local_server() as base_url, sync_playwright() as playwright:
        browser = playwright.webkit.launch()
        version = browser.version
        for name in PAGES:
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=1,
                reduced_motion="no-preference",
            )
            page = context.new_page()
            runtime_errors = []
            failed_resources = []
            page.on("pageerror", lambda error: runtime_errors.append(f"pageerror: {error}"))
            page.on(
                "console",
                lambda message: runtime_errors.append(f"console: {message.text}")
                if message.type == "error"
                else None,
            )
            page.on(
                "requestfailed",
                lambda request: failed_resources.append(
                    f"{request.url}: {request.failure or 'request failed'}"
                ),
            )
            page.on(
                "response",
                lambda response: failed_resources.append(
                    f"{response.url}: HTTP {response.status}"
                )
                if response.status >= 400
                else None,
            )
            try:
                response = page.goto(f"{base_url}/{name}", wait_until="networkidle", timeout=30000)
                require(response is not None and response.status == 200, f"HTTP {response.status if response else 'no response'}")
                metrics = page_metrics(page)
                require(metrics["documentWidth"] <= 391, f"document horizontal overflow: {metrics}")
                require(metrics["bodyWidth"] <= 391, f"body horizontal overflow: {metrics}")
                require(not metrics["brokenImages"], f"broken images: {metrics['brokenImages']}")
                require(not runtime_errors, f"runtime errors: {runtime_errors}")
                require(not failed_resources, f"failed resources: {failed_resources}")
                verify_support(page)
                if name == "index.html":
                    verify_homepage(page)
                    verify_theme(page, "#theme-toggle")
                else:
                    theme_selector = "#themego" if page.locator("#themego").count() else "#theme-toggle"
                    verify_theme(page, theme_selector)
                    verify_diagram_zoom(page)
                if name == "bitcoin-from-zero.html":
                    verify_bitcoin_hash(page)
                require(not runtime_errors, f"interaction errors: {runtime_errors}")
                results.append({"page": name, "status": "pass", "metrics": metrics})
            except Exception as exc:
                failures.append({"page": name, "error": str(exc)})
                results.append({"page": name, "status": "fail", "error": str(exc)})
            finally:
                context.close()
        browser.close()
    return {
        "playwright": "1.58.0",
        "engine": "webkit",
        "browserVersion": version,
        "viewport": {"width": 390, "height": 844},
        "pages": results,
        "failures": failures,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()
    report = run()
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["failures"] else 0)
