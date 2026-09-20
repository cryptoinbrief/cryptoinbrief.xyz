import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


PAGES = [
    "index.html", "crypto-summary.html", "crypto-summary-ar.html",
    "bitcoin-from-zero.html", "bitcoin-from-zero-ar.html",
    "bitcoin-whitepaper.html", "bitcoin-codebase.html", "bitcoin-vs-monero-whitepapers.html",
    "proof-of-stake.html", "solana.html", "sui.html", "monero-under-the-hood.html",
    "monero-from-zero-ar.html", "getting-monero.html", "zcash.html",
    "zero-knowledge-from-zero.html",
    "crypto-terms.html", "starting-with-crypto.html", "dollar-yield.html",
]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def verify_support(page, name):
    trigger = page.locator(".support-trigger")
    check(trigger.count() == 1, f"{name}: missing support trigger")
    trigger.click()
    check(page.locator("dialog.support-dialog[open]").count() == 1, f"{name}: support dialog did not open")
    check(page.locator(".support-tab").count() == 7, f"{name}: support currency list is incomplete")
    referrals = page.locator(".support-referral-links a")
    check(referrals.count() == 2, f"{name}: support referral links are incomplete")
    for index in range(referrals.count()):
        check("sponsored" in (referrals.nth(index).get_attribute("rel") or "").split(), f"{name}: referral link lacks sponsored disclosure")
    page.keyboard.press("Escape")
    check(page.locator("dialog.support-dialog[open]").count() == 0, f"{name}: support dialog did not close")


def run(base_url, output):
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        for width in (390, 1440):
            for theme in ("light", "dark"):
                context = browser.new_context(viewport={"width": width, "height": 950}, reduced_motion="reduce")
                context.add_init_script(f"localStorage.setItem('cib-theme', '{theme}');")
                page = context.new_page()
                for name in PAGES:
                    errors = []
                    failed = []
                    on_error = lambda error: errors.append(str(error))
                    on_response = lambda response: failed.append(response.url) if response.status >= 400 and response.url.startswith(base_url) else None
                    page.on("pageerror", on_error)
                    page.on("response", on_response)
                    response = page.goto(f"{base_url}/{name}", wait_until="networkidle")
                    check(response.status == 200, f"{name}: HTTP {response.status}")
                    page.wait_for_timeout(150)
                    metrics = page.evaluate("""() => ({
                        width: innerWidth,
                        body: document.body.scrollWidth,
                        theme: document.documentElement.dataset.theme,
                        h1: document.querySelectorAll('h1').length,
                        broken: [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src)
                    })""")
                    check(metrics["body"] <= width + 1, f"{name}: horizontal overflow {metrics}")
                    check(metrics["theme"] == theme, f"{name}: wrong theme {metrics['theme']}")
                    check(metrics["h1"] == 1, f"{name}: expected one heading")
                    check(not metrics["broken"], f"{name}: broken images {metrics['broken']}")
                    check(not errors, f"{name}: JavaScript errors {errors}")
                    check(not failed, f"{name}: failed local resources {failed}")
                    verify_support(page, name)
                    if name != "index.html":
                        expand = page.locator(".expand-diagram").first
                        check(expand.count() > 0, f"{name}: missing diagram zoom")
                        expand.click()
                        check(page.locator("dialog[open] figure").count() == 1, f"{name}: diagram did not open")
                        page.keyboard.press("Escape")
                        check(page.locator("dialog[open]").count() == 0, f"{name}: diagram did not close")
                        page.locator("main .expand-diagram").first.wait_for(state="attached")
                        check(page.locator("main .expand-diagram").count() > 0, f"{name}: diagram not restored")
                    if output and name in ("index.html", "bitcoin-from-zero.html", "solana.html", "crypto-summary-ar.html", "zero-knowledge-from-zero.html"):
                        page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
                        page.screenshot(path=str(output / f"{name[:-5]}-{width}-{theme}.png"))
                    results.append({"page": name, "width": width, "theme": theme, "status": "pass"})
                    page.remove_listener("pageerror", on_error)
                    page.remove_listener("response", on_response)
                context.close()
        context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="no-preference")
        page = context.new_page()
        page.goto(f"{base_url}/")
        page.wait_for_function("document.querySelector('#payment-demo').dataset.step === '1'", timeout=7000)
        movement_before = page.locator(".signed-packet").evaluate("e => getComputedStyle(e).transform")
        page.wait_for_function("before => getComputedStyle(document.querySelector('.signed-packet')).transform !== before", arg=movement_before, timeout=3000)
        movement_after = page.locator(".signed-packet").evaluate("e => getComputedStyle(e).transform")
        check(movement_before != movement_after, "Automatic signed payment animation did not move")
        page.locator("#demo-play").click()
        page.locator(".signed-packet").evaluate("async e => { await Promise.all(e.getAnimations().map(a => a.ready)); }")
        paused_before = page.locator(".signed-packet").evaluate("e => getComputedStyle(e).transform")
        page.wait_for_timeout(350)
        paused_after = page.locator(".signed-packet").evaluate("e => getComputedStyle(e).transform")
        check(paused_before == paused_after, "Pause did not stop physical motion")
        for step in range(4):
            page.locator(f"[data-go-step='{step}']").click()
            check(page.locator("#payment-demo").get_attribute("data-step") == str(step), "Walkthrough step mismatch")
        check(page.locator("#alex-balance").text_content() == "9 BTC", "Sender balance incorrect")
        check(page.locator("#sam-balance").text_content() == "1 BTC", "Recipient balance incorrect")
        page.locator("[data-go-step='2']").click()
        page.locator("[data-network='ethereum']").click()
        check("validator" in page.locator("#step-title").inner_text(), "Ethereum mechanism did not update")
        page.locator("[data-network='solana']").click()
        check("leader" in page.locator("#step-title").inner_text(), "Solana mechanism did not update")
        page.locator("#demo-tamper").click()
        page.wait_for_function("document.querySelector('#payment-demo').dataset.proof === 'invalid'")
        check(page.locator("#sam-balance").text_content() == "0 SOL", "Tampered payment changed the balance")
        check(page.locator("#proof-result").text_content() == "Signature rejected", "Real signature failure not shown")
        page.locator("#demo-tamper").click()
        page.wait_for_function("document.querySelector('#payment-demo').dataset.proof === 'valid'")
        page.locator("#demo-play").click()
        page.wait_for_timeout(3500)
        check(page.locator("#payment-demo").get_attribute("data-step") == "1", "Walkthrough playback failed")
        page.locator("#demo-play").click()
        page.locator("[data-filter='privacy']").click()
        check(page.locator(".topic:visible").count() == 5, "Privacy filter incorrect")
        page.locator("#topic-search").fill("zcash")
        check(page.locator(".topic:visible").count() == 1, "Search did not narrow results")
        page.locator("#topic-search").fill("no-matching-guide")
        check(page.locator("#empty-topics").is_visible(), "Missing empty state")
        page.locator("#topic-search").fill("")
        page.locator("[data-filter='all']").click()
        check(page.locator(".topic:visible").count() == 15, "All guides did not restore")
        page.locator("#theme-toggle").click()
        check(page.locator("html").get_attribute("data-theme") == "dark", "Theme switch failed")
        page.reload()
        check(page.locator("html").get_attribute("data-theme") == "dark", "Theme did not persist")
        browser.close()
    return {"responsive_views": len(results), "homepage_controls": "pass", "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8934")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(args.base_url.rstrip("/"), args.screenshots), indent=2))
