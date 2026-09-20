import argparse
import json
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


PAGES = [
    "index.html",
    "crypto-summary.html",
    "crypto-summary-ar.html",
    "bitcoin-from-zero.html",
    "bitcoin-from-zero-ar.html",
    "proof-of-stake.html",
    "solana.html",
    "sui.html",
    "monero-under-the-hood.html",
    "monero-from-zero-ar.html",
    "zcash.html",
    "zero-knowledge-from-zero.html",
    "getting-monero.html",
]
ADDRESSES = {
    "XMR": "49BWStdJJVEfPRDQTmCtrT39QSqXNWLUGNvTzU7cMfsMHTG1ozR1YFQPCKb65oduji5isbVAowiwVFPpseHv9Dg3875rB9G",
    "BTC": "bc1q7avt57ekp002lzq2untsr5lpqy9hsfqudf7a5h",
    "LTC": "ltc1qrvecg74m4elgm9j2el78zgau5a4l3x245jwqmj",
    "ZEC": "u1hpydpv0n36jvucwevy6477auq5ml5wjgzfrwq20xsau78mj9x576fkx7cd2q23f35lr0wctznsj27tnxh0anujlcdn45sqsvqm0kshl09982f4tmpa64npzezu5m3d7wm4vv6uqjlvkdda9lzavn8yqfgmzaykgcxt5lqmme5qr5epwt",
    "DASH": "XjZo388Ct5tssNwC9BDbzXqC52YXqyUPsz",
    "ETH": "0x56102e5dc2bCE0ab5766e87a2363cea93FbB7D4d",
    "SOL": "8jUUGAtcTW7ZxGMUPtuJGsmyep5oxmcrBENFZ8TDoiBm",
}
NETWORKS = {
    "XMR": "Monero network",
    "BTC": "Bitcoin network",
    "LTC": "Litecoin network",
    "ZEC": "Zcash Unified Address",
    "DASH": "Dash network",
    "ETH": "Ethereum network",
    "SOL": "Solana network",
}
REFERRALS = {
    "Bybit": "https://www.bybit.com/invite?ref=MWBL9%230&medium=referral&utm_campaign=evergreen",
    "Binance": "https://www.binance.com/referral/earn-together/refer2earn-usdc/claim?hl=en&ref=GRO_28502_WQILP&utm_source=referral_entrance",
}
DISCLOSURE = "These are referral links. I may receive a benefit if you use them."


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def origin_for(base_url):
    parsed = urlsplit(base_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def verify_includes(page, base_url):
    results = []
    for name in PAGES:
        response = page.goto(f"{base_url}/{name}", wait_until="networkidle")
        check(response and response.status == 200, f"{name}: HTTP load failed")
        page.wait_for_function("window.__support?.dialog", timeout=5000)
        check(page.locator(".support-trigger").count() == 1, f"{name}: expected one Donate button")
        check(page.locator("dialog.support-dialog").count() == 1, f"{name}: expected one support dialog")
        results.append(name)
    return results


def open_dialog(page):
    trigger = page.locator(".support-trigger")
    trigger.focus()
    trigger.click()
    dialog = page.locator("dialog.support-dialog")
    check(dialog.get_attribute("open") is not None, "Dialog did not open")
    page.wait_for_function("document.activeElement?.id === 'support-tab-xmr'", timeout=1000)
    return trigger, dialog


def verify_currencies(page, dialog):
    copied = []
    for code, expected in ADDRESSES.items():
        tab = dialog.locator(f"[data-currency='{code}']")
        check(tab.count() == 1, f"{code}: currency option missing")
        tab.click()
        check(dialog.locator(".support-address").inner_text() == expected, f"{code}: displayed address changed")
        check(dialog.locator(".support-identity-copy span").inner_text() == NETWORKS[code], f"{code}: wrong network label")
        copy_button = dialog.locator(".support-copy")
        check(copy_button.is_enabled(), f"{code}: copy unexpectedly disabled")
        copy_button.click()
        page.wait_for_function(
            "code => document.querySelector('.support-status')?.textContent.includes(code)",
            arg=code,
            timeout=2000,
        )
        clipboard = page.evaluate("navigator.clipboard.readText()")
        check(clipboard == expected, f"{code}: clipboard value changed")
        copied.append(code)
    check(copied == ["XMR", "BTC", "LTC", "ZEC", "DASH", "ETH", "SOL"], f"Unexpected copied currencies {copied}")
    return copied


def verify_referrals(dialog):
    links = dialog.locator(".support-referral-links a")
    check(links.count() == 2, "Expected two referral links")
    for index, (name, expected) in enumerate(REFERRALS.items()):
        link = links.nth(index)
        check(link.inner_text().startswith(name), f"{name}: label missing")
        check(link.get_attribute("href") == expected, f"{name}: URL changed")
        rel = set((link.get_attribute("rel") or "").split())
        check(rel == {"sponsored", "noopener", "noreferrer"}, f"{name}: rel attributes wrong")
    check(dialog.locator(".support-disclosure").inner_text() == DISCLOSURE, "Referral disclosure changed")
    hrefs = dialog.locator("a").evaluate_all("links => links.map(link => link.getAttribute('href'))")
    check(hrefs == list(REFERRALS.values()), "Unexpected dialog link or transaction link present")
    remote_images = dialog.locator("img").evaluate_all(
        "images => images.map(image => image.getAttribute('src')).filter(src => /^https?:/i.test(src || ''))"
    )
    check(not remote_images, f"Remote image dependency present {remote_images}")


def verify_keyboard(page, trigger, dialog):
    page.keyboard.press("Escape")
    check(dialog.get_attribute("open") is None, "Escape did not close dialog")
    check(trigger.evaluate("el => el === document.activeElement"), "Focus did not return to Donate button")
    trigger.click()
    dialog.locator(".support-close").click()
    check(dialog.get_attribute("open") is None, "Close button did not close dialog")
    check(trigger.evaluate("el => el === document.activeElement"), "Close button did not restore focus")


def verify_copy_error(browser, base_url):
    context = browser.new_context(viewport={"width": 1000, "height": 800})
    page = context.new_page()
    page.goto(f"{base_url}/index.html", wait_until="networkidle")
    page.wait_for_function("window.__support?.dialog", timeout=5000)
    page.evaluate(
        """() => {
            Object.defineProperty(navigator, 'clipboard', {
                configurable: true,
                value: {writeText: () => Promise.reject(new Error('blocked'))}
            });
            Document.prototype.execCommand = () => false;
        }"""
    )
    page.locator(".support-trigger").click()
    page.locator(".support-copy").click()
    page.wait_for_function("document.querySelector('.support-status')?.textContent.startsWith('Copy failed')", timeout=2000)
    check("manually" in page.locator(".support-status").inner_text(), "Copy error did not provide manual fallback")
    context.close()


def verify_mobile(browser, base_url):
    results = []
    for width in (390, 320):
        context = browser.new_context(viewport={"width": width, "height": 844})
        page = context.new_page()
        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        page.wait_for_function("window.__support?.dialog", timeout=5000)
        check(page.locator(".support-trigger").is_visible(), f"Donate button hidden at {width}px")
        page.locator(".support-trigger").click()
        metrics = page.locator("dialog.support-dialog").evaluate(
            """dialog => {
                const box = dialog.getBoundingClientRect();
                const tabs = [...dialog.querySelectorAll('.support-tab')].map(tab => {
                    const rect = tab.getBoundingClientRect();
                    return {left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom};
                });
                const tablist = dialog.querySelector('.support-tabs');
                return {
                    left: box.left,
                    right: box.right,
                    top: box.top,
                    bottom: box.bottom,
                    viewport: innerWidth,
                    tabs,
                    tabOverflow: tablist.scrollWidth - tablist.clientWidth,
                    addressSize: parseFloat(getComputedStyle(dialog.querySelector('.support-address')).fontSize)
                };
            }"""
        )
        check(metrics["left"] >= 0 and metrics["right"] <= metrics["viewport"], f"Mobile dialog overflow at {width}px: {metrics}")
        check(len(metrics["tabs"]) == 7, f"Expected seven mobile tabs at {width}px")
        check(
            all(
                tab["left"] >= metrics["left"]
                and tab["right"] <= metrics["right"]
                and tab["top"] >= metrics["top"]
                and tab["bottom"] <= metrics["bottom"]
                for tab in metrics["tabs"]
            ),
            f"Currency tab escaped visible dialog at {width}px: {metrics}",
        )
        check(metrics["tabOverflow"] <= 1, f"Currency grid overflow at {width}px: {metrics}")
        check(metrics["addressSize"] == 12, f"Address text is not 12px at {width}px")
        check(page.evaluate("document.body.scrollWidth <= innerWidth + 1"), f"Mobile page overflow at {width}px")
        results.append({"width": width, "tabs": len(metrics["tabs"]), "address_px": metrics["addressSize"]})
        context.close()
    return results


def verify_dark(browser, base_url):
    context = browser.new_context(viewport={"width": 1100, "height": 800})
    page = context.new_page()
    page.goto(f"{base_url}/index.html", wait_until="networkidle")
    page.wait_for_function("window.__support?.dialog", timeout=5000)
    page.evaluate("document.documentElement.dataset.theme = 'dark'")
    page.locator(".support-trigger").click()
    colors = page.locator("dialog.support-dialog").evaluate(
        "dialog => ({dialog: getComputedStyle(dialog).backgroundColor, page: getComputedStyle(document.documentElement).getPropertyValue('--page').trim()})"
    )
    check(colors["dialog"] not in {"rgb(255, 255, 255)", "#fff", "white"}, f"Dark dialog remained white {colors}")
    check(page.locator(".support-trigger").is_visible(), "Donate button disappeared in dark theme")
    context.close()


def verify_rtl(browser, base_url):
    context = browser.new_context(viewport={"width": 1100, "height": 800})
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin_for(base_url))
    page = context.new_page()
    page.goto(f"{base_url}/crypto-summary-ar.html", wait_until="networkidle")
    page.wait_for_function("window.__support?.dialog", timeout=5000)
    trigger = page.locator(".support-trigger")
    check(trigger.inner_text() == "تبرع", "Arabic Donate label missing")
    trigger.click()
    dialog = page.locator("dialog.support-dialog")
    check(dialog.evaluate("el => getComputedStyle(el).direction") == "rtl", "Dialog did not inherit RTL")
    check(dialog.locator(".support-address").evaluate("el => getComputedStyle(el).direction") == "ltr", "Address did not remain LTR")
    dialog.locator("[data-currency='BTC']").click()
    dialog.locator(".support-copy").click()
    page.wait_for_function("document.querySelector('.support-status')?.textContent.includes('BTC')", timeout=2000)
    check(page.evaluate("navigator.clipboard.readText()") == ADDRESSES["BTC"], "RTL copy changed BTC address")
    page.keyboard.press("Escape")
    check(trigger.evaluate("el => el === document.activeElement"), "RTL Escape did not restore focus")
    context.close()


def run(base_url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin_for(base_url))
        page = context.new_page()
        included = verify_includes(page, base_url)
        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        trigger, dialog = open_dialog(page)
        copied = verify_currencies(page, dialog)
        verify_referrals(dialog)
        verify_keyboard(page, trigger, dialog)
        context.close()
        verify_copy_error(browser, base_url)
        mobile = verify_mobile(browser, base_url)
        verify_dark(browser, base_url)
        verify_rtl(browser, base_url)
        browser.close()
    return {
        "included_pages": included,
        "copied_currencies": copied,
        "ethereum": "checksum valid and copied exactly",
        "referrals": "pass",
        "keyboard_and_focus": "pass",
        "copy_error_fallback": "pass",
        "mobile": mobile,
        "dark": "pass",
        "rtl": "pass",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8934")
    args = parser.parse_args()
    print(json.dumps(run(args.base_url.rstrip("/")), indent=2, ensure_ascii=False))
