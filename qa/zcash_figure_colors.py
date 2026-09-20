import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def channels(value):
    match = re.fullmatch(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)", value)
    check(match, f"Unsupported computed color {value}")
    return tuple(int(channel) for channel in match.groups())


def luminance(color):
    values = []
    for channel in color:
        value = channel / 255
        values.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def contrast(foreground, background):
    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def blended(foreground, background, opacity):
    return tuple(round(front * opacity + back * (1 - opacity)) for front, back in zip(foreground, background))


def pause_playback(page):
    page.evaluate(
        """document.querySelectorAll('.fp-toggle').forEach(button => {
            if (button.textContent.trim() === 'Pause') button.click();
        })"""
    )


def inspect_figures(page):
    return page.locator("figure").evaluate_all(
        """figures => figures.map((figure, index) => ({
            index,
            background: getComputedStyle(figure).backgroundColor,
            texts: [...figure.querySelectorAll('svg text')].map(text => ({
                text: text.textContent.trim(),
                fill: getComputedStyle(text).fill,
                fontSize: parseFloat(getComputedStyle(text).fontSize)
            }))
        }))"""
    )


def inspect_visible_text(figure):
    return figure.evaluate(
        """figure => [...figure.querySelectorAll('svg text')].map(text => {
            let opacity = 1;
            let node = text;
            while (node && node !== figure) {
                opacity *= Number(getComputedStyle(node).opacity || 1);
                node = node.parentElement;
            }
            return {text: text.textContent.trim(), fill: getComputedStyle(text).fill, opacity};
        })"""
    )


def verify_context(browser, base_url, width, theme, screenshots):
    context = browser.new_context(viewport={"width": width, "height": 950}, color_scheme=theme)
    context.add_init_script(
        f"localStorage.setItem('cib-theme', '{theme}'); localStorage.setItem('cln-theme', '{theme}');"
    )
    page = context.new_page()
    errors = []
    failures = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "response",
        lambda response: failures.append(f"{response.status} {response.url}")
        if response.status >= 400 and response.url.startswith(base_url)
        else None,
    )
    response = page.goto(f"{base_url}/zcash.html", wait_until="networkidle")
    check(response and response.status == 200, f"{width} {theme}: page failed to load")
    try:
        page.wait_for_function(
            "window.__figurePlayback?.figures?.length === document.querySelectorAll('figure').length", timeout=10000
        )
    except PlaywrightTimeoutError:
        page.reload(wait_until="networkidle")
        page.wait_for_function(
            "window.__figurePlayback?.figures?.length === document.querySelectorAll('figure').length", timeout=10000
        )
    pause_playback(page)
    check(not errors, f"{width} {theme}: JavaScript errors {errors}")
    check(not failures, f"{width} {theme}: resource failures {failures}")
    check(page.evaluate("document.body.scrollWidth <= innerWidth + 1"), f"{width} {theme}: horizontal overflow")

    figures = inspect_figures(page)
    check(len(figures) == 7, f"{width} {theme}: expected 7 figures, found {len(figures)}")
    results = []
    for figure in figures:
        background = channels(figure["background"])
        check(figure["texts"], f"{width} {theme}: figure {figure['index'] + 1} has no SVG text")
        for text in figure["texts"]:
            ratio = contrast(channels(text["fill"]), background)
            check(
                ratio >= 4.5,
                f"{width} {theme}: figure {figure['index'] + 1} text {text['text']!r} contrast {ratio:.2f}",
            )
        results.append(
            {
                "figure": figure["index"] + 1,
                "texts": len(figure["texts"]),
                "minimum_contrast": round(
                    min(contrast(channels(text["fill"]), background) for text in figure["texts"]), 2
                ),
            }
        )

    first = page.locator("figure").first
    first.scroll_into_view_if_needed()
    page.wait_for_timeout(1800)
    step = first.locator("button").filter(has_text="Step")
    check(step.count() == 1, f"{width} {theme}: native figure controls missing")
    first.evaluate("figure => figure._figsteps?.clear()")
    for stage in (1, 2):
        step.click()
        page.wait_for_timeout(1000)
        check(
            first.locator(f"svg g[data-step='{stage}']:not(.fdim)").count() == 1,
            f"{width} {theme}: stage {stage} did not activate",
        )
        background = channels(first.evaluate("figure => getComputedStyle(figure).backgroundColor"))
        for text in inspect_visible_text(first):
            ratio = contrast(blended(channels(text["fill"]), background, text["opacity"]), background)
            check(
                ratio >= 4.5,
                f"{width} {theme}: stage {stage} text {text['text']!r} effective contrast {ratio:.2f}",
            )
        if screenshots:
            first.screenshot(
                path=str(screenshots / f"zcash-figure-1-{theme}-{width}-stage-{stage}.png"), animations="disabled"
            )
    context.close()
    return {"width": width, "theme": theme, "figures": results, "status": "pass"}


def run(base_url, screenshots):
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        for width in (390, 1440):
            for theme in ("light", "dark"):
                results.append(verify_context(browser, base_url, width, theme, screenshots))
        browser.close()
    return {"contexts": results, "status": "pass"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8934")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(args.base_url.rstrip("/"), args.screenshots), indent=2))
