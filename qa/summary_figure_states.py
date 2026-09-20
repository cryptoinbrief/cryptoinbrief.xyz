import argparse
import json
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGES = ("crypto-summary.html", "crypto-summary-ar.html")
WIDTHS = (390, 1440)
THEMES = ("light", "dark")
MOTIONS = ("no-preference", "reduce")


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


def element_states(figure, selector):
    return figure.locator(selector).evaluate_all(
        """elements => elements.map(element => {
            const style = getComputedStyle(element);
            return {
                display: style.display,
                opacity: Number(style.opacity),
                visibility: style.visibility,
                text: (element.textContent || '').trim()
            };
        })"""
    )


def require_hidden(states, label):
    require(states, f"{label}: missing exclusive state elements")
    require(
        all(state["display"] == "none" and state["visibility"] == "hidden" for state in states),
        f"{label}: inactive state is visible: {states}",
    )


def require_visible(states, label):
    require(states, f"{label}: missing active state elements")
    require(
        all(state["opacity"] >= 0.99 and state["visibility"] == "visible" for state in states),
        f"{label}: active state is not visible: {states}",
    )


def pause_figure(page, figure):
    page.wait_for_timeout(250)
    figure.evaluate(
        """figure => {
            if (figure.classList.contains('fp-playing')) {
                const button = figure.querySelector('.fp-toggle');
                if (button) button.click();
            }
        }"""
    )
    page.wait_for_timeout(30)
    require(not figure.evaluate("figure => figure.classList.contains('fp-playing')"), "automatic playback did not pause")


def screenshot(figure, directory, name):
    if directory and "-dark-no-preference" in name:
        figure.screenshot(path=str(directory / name), animations="disabled")
        return True
    return False


def verify_english(page, directory, suffix):
    figures = page.locator("figure[data-kind='toggle']")
    require(figures.count() == 5, f"English summary: expected 5 toggles, found {figures.count()}")
    for index in range(figures.count()):
        figure = figures.nth(index)
        figure.scroll_into_view_if_needed()
        pause_figure(page, figure)
        toggle = figure.locator(".figctl [data-act='toggle']")
        replay = figure.locator(".figctl [data-act='replay']")
        require(toggle.count() == 1 and replay.count() == 1, f"English toggle {index + 1}: missing native controls")
        if figure.locator("svg.fb").count():
            toggle.click()
        replay.click()
        require_hidden(element_states(figure, ".stB"), f"English toggle {index + 1} hidden B during replay")
        if index == figures.count() - 1 and directory and "-dark-no-preference" in suffix:
            page.wait_for_timeout(1300)
            require_visible(element_states(figure, ".stA"), f"English toggle {index + 1} settled state A")
            screenshot(figure, directory, f"english-mev-fair-{suffix}.png")
        toggle.click()
        require_hidden(element_states(figure, ".stA"), f"English toggle {index + 1} hidden A")
        if index == figures.count() - 1 and directory and "-dark-no-preference" in suffix:
            page.wait_for_timeout(300)
            require_visible(element_states(figure, ".stB"), f"English toggle {index + 1} state B")
            screenshot(figure, directory, f"english-mev-sandwich-{suffix}.png")


def verify_arabic(page, directory, suffix):
    figures = page.locator("figure:has(svg[data-fa])")
    require(figures.count() == 6, f"Arabic summary: expected 6 toggles, found {figures.count()}")
    for index in range(figures.count()):
        figure = figures.nth(index)
        figure.scroll_into_view_if_needed()
        pause_figure(page, figure)
        controls = figure.locator(".figui .fgb")
        require(controls.count() == 2, f"Arabic toggle {index + 1}: missing native controls")
        replay = controls.nth(0)
        toggle = controls.nth(1)
        if figure.locator("svg.fa").count():
            toggle.click()
        exclusive_a = element_states(figure, ".fa-only")
        exclusive_b = element_states(figure, ".fb-only")
        context_a = element_states(figure, ".sa")
        context_b = element_states(figure, ".sb")
        if exclusive_a or exclusive_b:
            replay.click()
            require_hidden(element_states(figure, ".fa-only"), f"Arabic toggle {index + 1} hidden A during replay")
        else:
            require(context_a and context_b, f"Arabic toggle {index + 1}: no alternate state elements")
            require(all(state["opacity"] <= 0.23 for state in context_a), f"Arabic toggle {index + 1}: inactive context A is not dimmed")
        if index == figures.count() - 1 and directory and "-dark-no-preference" in suffix:
            page.wait_for_timeout(1300)
            require_visible(element_states(figure, ".fb-only"), f"Arabic toggle {index + 1} settled state B")
            screenshot(figure, directory, f"arabic-mev-sandwich-{suffix}.png")
        toggle.click()
        if exclusive_a or exclusive_b:
            require_hidden(element_states(figure, ".fb-only"), f"Arabic toggle {index + 1} hidden B")
        else:
            page.wait_for_timeout(300)
            require(all(state["opacity"] <= 0.23 for state in element_states(figure, ".sb")), f"Arabic toggle {index + 1}: inactive context B is not dimmed")
        if index == figures.count() - 1 and directory and "-dark-no-preference" in suffix:
            page.wait_for_timeout(300)
            require_visible(element_states(figure, ".fa-only"), f"Arabic toggle {index + 1} state A")
            screenshot(figure, directory, f"arabic-mev-fair-{suffix}.png")


def run(engine, screenshot_dir):
    failures = []
    results = []
    if screenshot_dir:
        screenshot_dir.mkdir(parents=True, exist_ok=True)
    with local_server() as base_url, sync_playwright() as playwright:
        if engine == "chrome":
            browser = playwright.chromium.launch(channel="chrome")
        else:
            browser = playwright.webkit.launch()
        version = browser.version
        for width in WIDTHS:
            for theme in THEMES:
                for motion in MOTIONS:
                    for name in PAGES:
                        context = browser.new_context(
                            viewport={"width": width, "height": 1000},
                            reduced_motion=motion,
                        )
                        page = context.new_page()
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                        page.add_init_script(f"localStorage.setItem('cib-theme', {json.dumps(theme)})")
                        case = f"{name}:{width}:{theme}:{motion}"
                        try:
                            response = page.goto(f"{base_url}/{name}", wait_until="networkidle", timeout=30000)
                            require(response and response.status == 200, f"{case}: HTTP {response.status if response else 'none'}")
                            require(page.locator("html").get_attribute("data-theme") == theme, f"{case}: wrong theme")
                            suffix = f"{engine}-{width}-{theme}-{motion}"
                            if name == "crypto-summary.html":
                                verify_english(page, screenshot_dir, suffix)
                            else:
                                verify_arabic(page, screenshot_dir, suffix)
                            require(not errors, f"{case}: runtime errors: {errors}")
                            results.append({"case": case, "status": "pass"})
                        except Exception as exc:
                            failures.append({"case": case, "error": str(exc)})
                            results.append({"case": case, "status": "fail"})
                        finally:
                            context.close()
        browser.close()
    return {
        "engine": engine,
        "browserVersion": version,
        "cases": len(results),
        "passed": sum(result["status"] == "pass" for result in results),
        "failures": failures,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=("chrome", "webkit"), default="chrome")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    report = run(args.engine, args.screenshots)
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["failures"] else 0)
