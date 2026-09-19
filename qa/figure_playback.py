import argparse
import json

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


PAGES = [
    "crypto-summary.html",
    "crypto-summary-ar.html",
    "bitcoin-from-zero.html",
    "bitcoin-from-zero-ar.html",
    "monero-under-the-hood.html",
    "monero-from-zero-ar.html",
    "solana.html",
    "zcash.html",
    "zero-knowledge-from-zero.html",
]
STORY_SELECTOR = ".cstory, .exec-story, .privacy-story"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def figure_state(figure):
    return figure.evaluate(
        """figure => ({
            counter: figure.querySelector('.fp-counter')?.textContent.trim() || '',
            narrative: figure.querySelector('.fp-narrative')?.textContent.trim() || '',
            status: figure.querySelector('.fp-status')?.textContent.trim() || '',
            focused: figure.querySelectorAll('.fp-focus').length,
            muted: figure.querySelectorAll('.fp-muted').length,
            logo: Boolean(figure.querySelector('.fp-logo, .fp-concept-mark'))
        })"""
    )


def open_page(page, base_url, name):
    errors = []
    failures = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "response",
        lambda response: failures.append(f"{response.status} {response.url}")
        if response.status >= 400 and response.url.startswith(base_url)
        else None,
    )
    response = page.goto(f"{base_url}/{name}", wait_until="networkidle")
    check(response and response.status == 200, f"{name}: HTTP load failed")
    try:
        page.wait_for_function("window.__figurePlayback?.figures?.length > 0", timeout=10000)
    except PlaywrightTimeoutError:
        page.reload(wait_until="networkidle")
        page.wait_for_function("window.__figurePlayback?.figures?.length > 0", timeout=10000)
    check(not errors, f"{name}: JavaScript errors {errors}")
    check(not failures, f"{name}: failed local resources {failures}")
    return errors, failures


def assert_story_isolation(page, name):
    result = page.evaluate(
        """selector => {
            const stories = [...document.querySelectorAll(selector)];
            return {
                count: stories.length,
                contaminated: stories.filter(story =>
                    story.matches('[data-figure-playback]') ||
                    story.querySelector('[data-figure-playback], .fp-topline, .fp-lesson, .fp-toggle')
                ).length
            };
        }""",
        STORY_SELECTOR,
    )
    check(result["contaminated"] == 0, f"{name}: figure playback entered a story module")
    return result["count"]


def assert_autoplay(page, name):
    figure = page.locator("figure[data-figure-playback='ready']").first
    check(figure.count() == 1, f"{name}: first figure was not mounted")
    figure.scroll_into_view_if_needed()
    page.wait_for_function(
        "figure => window.__figurePlayback.active()?.figure === figure",
        arg=figure.element_handle(),
        timeout=10000,
    )
    before = figure_state(figure)
    page.wait_for_function(
        "({figure, before}) => figure.querySelector('.fp-counter')?.textContent.trim() !== before",
        arg={"figure": figure.element_handle(), "before": before["counter"]},
        timeout=4200,
    )
    after = figure_state(figure)
    check(after["status"] in {"Playing automatically", "يعمل تلقائيا"}, f"{name}: autoplay status missing")
    check(after["counter"] != before["counter"], f"{name}: semantic counter did not advance")
    check(after["focused"] == 1, f"{name}: expected one focused semantic element")
    check(after["narrative"] != before["narrative"], f"{name}: narration did not change")
    check(after["logo"], f"{name}: network identity mark missing")
    return figure, before, after


def assert_pause_and_offscreen(page, name, figure):
    figure.locator(".fp-toggle").click()
    paused = figure_state(figure)
    check(paused["status"] in {"Paused", "متوقف مؤقتا"}, f"{name}: pause status missing")
    page.wait_for_timeout(3800)
    held = figure_state(figure)
    check(held["counter"] == paused["counter"], f"{name}: counter advanced while paused")
    check(held["narrative"] == paused["narrative"], f"{name}: narration advanced while paused")
    figure.locator(".fp-toggle").click()
    page.wait_for_function(
        "figure => window.__figurePlayback.active()?.figure === figure",
        arg=figure.element_handle(),
        timeout=3000,
    )
    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    page.wait_for_function(
        "figure => window.__figurePlayback.active()?.figure !== figure",
        arg=figure.element_handle(),
        timeout=3000,
    )
    check(
        figure.locator(".fp-status").inner_text() in {"Paused", "متوقف مؤقتا"},
        f"{name}: offscreen figure did not stop",
    )


def assert_native_controls(page):
    figure = page.locator("figure[data-kind='seq']").first
    check(figure.count() == 1, "crypto-summary.html: sequential figure missing")
    figure.scroll_into_view_if_needed()
    page.wait_for_function(
        "figure => window.__figurePlayback.active()?.figure === figure",
        arg=figure.element_handle(),
        timeout=5000,
    )
    step = figure.locator("[data-act='step']")
    replay = figure.locator("[data-act='replay']")
    check(step.count() == 1 and replay.count() == 1, "crypto-summary.html: native controls missing")
    before = step.inner_text()
    step.evaluate("button => button.click()")
    after = step.inner_text()
    check(before != after, "crypto-summary.html: native Step did not change the scene")
    check(figure.locator(".fp-status").inner_text() == "Paused", "Synthetic native click did not pause wrapper")
    held = after
    page.wait_for_timeout(3800)
    check(step.inner_text() == held, "Native scene changed after manual pause")
    replay.evaluate("button => button.click()")
    check(step.inner_text() != held, "crypto-summary.html: native Replay did not reset the scene")
    check(figure.locator(".fp-status").inner_text() == "Paused", "Native Replay resumed wrapper")


def assert_reduced_motion(browser, base_url):
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = context.new_page()
    open_page(page, base_url, "crypto-summary.html")
    figure = page.locator("figure[data-figure-playback='ready']").first
    figure.scroll_into_view_if_needed()
    page.wait_for_function(
        "figure => window.__figurePlayback.active()?.figure === figure",
        arg=figure.element_handle(),
        timeout=5000,
    )
    figure.locator(".fp-toggle").click()
    check(figure.locator(".fp-status").inner_text() == "Paused", "Reduced motion pause failed")
    figure.locator(".fp-toggle").click()
    before = figure_state(figure)
    page.wait_for_function(
        "figure => figure.querySelectorAll('.fp-focus').length === 1",
        arg=figure.element_handle(),
        timeout=1500,
    )
    after = figure_state(figure)
    check(after["focused"] == 1, "Reduced motion did not expose a meaningful state")
    check(after["counter"] != "0 / 2", "Reduced motion semantic state did not advance")
    check(
        page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"),
        "Reduced motion emulation was not active",
    )
    check(
        figure.locator(".fp-status").evaluate("el => getComputedStyle(el, '::before').animationName === 'none'"),
        "Reduced motion left physical status animation running",
    )
    context.close()
    return {"before": before["counter"], "after": after["counter"]}


def run(base_url):
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="no-preference")
        page = context.new_page()
        for name in PAGES:
            open_page(page, base_url, name)
            story_count = assert_story_isolation(page, name)
            figure, before, after = assert_autoplay(page, name)
            if name == "crypto-summary.html":
                assert_pause_and_offscreen(page, name, figure)
                page.goto(f"{base_url}/{name}", wait_until="networkidle")
                page.wait_for_function("window.__figurePlayback?.figures?.length > 0", timeout=10000)
                assert_native_controls(page)
            results.append(
                {
                    "page": name,
                    "before": before["counter"],
                    "after": after["counter"],
                    "story_modules": story_count,
                    "status": "pass",
                }
            )
        context.close()
        reduced = assert_reduced_motion(browser, base_url)
        browser.close()
    return {
        "pages": results,
        "manual_pause": "pass",
        "native_controls": "pass",
        "offscreen_pause": "pass",
        "reduced_motion": reduced,
        "story_isolation": "pass",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8934")
    args = parser.parse_args()
    print(json.dumps(run(args.base_url.rstrip("/")), indent=2, ensure_ascii=False))
