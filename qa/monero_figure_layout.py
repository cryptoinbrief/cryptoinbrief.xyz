import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def pause(figure):
    button = figure.locator(".fp-toggle")
    if button.count() and button.inner_text().strip() in ("Pause", "إيقاف مؤقت"):
        button.click()


def text_geometry(svg):
    return svg.evaluate("""svg => {
        const view = svg.viewBox.baseVal;
        const texts = [...svg.querySelectorAll('text')].filter(text => {
            let node = text;
            while (node && node !== svg) {
                const style = getComputedStyle(node);
                if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) < 0.01) return false;
                node = node.parentElement;
            }
            return true;
        }).map(text => {
            const box = text.getBBox();
            return {text: text.textContent.trim(), x: box.x, y: box.y, right: box.x + box.width, bottom: box.y + box.height};
        });
        const outside = texts.filter(box => box.x < view.x - .2 || box.y < view.y - .2 || box.right > view.x + view.width + .2 || box.bottom > view.y + view.height + .2);
        const overlaps = [];
        for (let i = 0; i < texts.length; i++) {
            for (let j = i + 1; j < texts.length; j++) {
                const a = texts[i], b = texts[j];
                const width = Math.min(a.right, b.right) - Math.max(a.x, b.x);
                const height = Math.min(a.bottom, b.bottom) - Math.max(a.y, b.y);
                if (width > 1 && height > 1) overlaps.push([a.text, b.text]);
            }
        }
        return {outside, overlaps};
    }""")


def contained_labels(svg):
    return svg.evaluate("""svg => {
        const visible = element => {
            let node = element;
            while (node && node !== svg) {
                const style = getComputedStyle(node);
                if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) < 0.01) return false;
                node = node.parentElement;
            }
            return true;
        };
        return [...svg.querySelectorAll('rect')].filter(rect => {
        const x = Number(rect.getAttribute('x'));
        const y = Number(rect.getAttribute('y'));
        const width = Number(rect.getAttribute('width'));
        return visible(rect) && width >= 90 && y >= 40 && x >= 20;
    }).map(rect => {
        const box = rect.getBBox();
        const labels = [...svg.querySelectorAll('text')].filter(text => visible(text) && (() => {
            const textBox = text.getBBox();
            const cx = textBox.x + textBox.width / 2;
            const cy = textBox.y + textBox.height / 2;
            return cx >= box.x && cx <= box.x + box.width && cy >= box.y && cy <= box.y + box.height;
        })());
        return {
            rect: {x: box.x, y: box.y, width: box.width, height: box.height},
            labels: labels.map(text => {
                const textBox = text.getBBox();
                return {
                    text: text.textContent.trim(),
                    inside: textBox.x >= box.x - .2 && textBox.y >= box.y - .2 && textBox.x + textBox.width <= box.x + box.width + .2 && textBox.y + textBox.height <= box.y + box.height + .2
                };
            })
        };
    });
    }""")


def verify_geometry(svg, name):
    geometry = text_geometry(svg)
    check(not geometry["outside"], f"{name}: labels outside SVG {geometry['outside']}")
    check(not geometry["overlaps"], f"{name}: overlapping labels {geometry['overlaps']}")


def verify_arabic(page, base_url, width, theme, motion, screenshots):
    page.goto(f"{base_url}/monero-from-zero-ar.html", wait_until="networkidle")
    check(page.evaluate("document.body.scrollWidth <= innerWidth + 1"), f"Arabic {width} {theme} {motion}: horizontal overflow")
    key = page.locator('[data-figure-id="key-image-ar"]')
    key.scroll_into_view_if_needed()
    page.wait_for_timeout(1800 if motion == "no-preference" else 150)
    pause(key)
    replay = key.locator(".fx-strip .fx-b").filter(has_text="إعادة")
    step = key.locator(".fx-strip .fx-b").filter(has_text="خطوة")
    check(replay.count() == 1 and step.count() == 1, "Arabic key image controls missing")
    replay.click()
    page.wait_for_timeout(1500 if motion == "no-preference" else 50)
    verify_geometry(key.locator("svg"), f"Arabic key image neutral {width} {theme} {motion}")
    for phase in range(1, 5):
        step.click()
        current = key.locator(f'[data-step="{phase}"].fx-cur')
        check(current.count() > 0, f"Arabic key image phase {phase} did not activate")
        verify_geometry(key.locator("svg"), f"Arabic key image phase {phase} {width} {theme} {motion}")
    boxes = contained_labels(key.locator("svg"))
    check(all(item["labels"] and all(label["inside"] for label in item["labels"]) for item in boxes), f"Arabic key image box containment failed {boxes}")
    glossary = page.locator('[data-figure-id="glossary-map-ar"]')
    glossary.scroll_into_view_if_needed()
    page.wait_for_timeout(1800 if motion == "no-preference" else 150)
    pause(glossary)
    replay = glossary.locator(".fx-strip .fx-b").filter(has_text="إعادة")
    step = glossary.locator(".fx-strip .fx-b").filter(has_text="خطوة")
    replay.click()
    page.wait_for_timeout(1500 if motion == "no-preference" else 50)
    verify_geometry(glossary.locator("svg"), f"Arabic glossary neutral {width} {theme} {motion}")
    for phase in range(1, 7):
        step.click()
        check(glossary.locator(f'[data-step="{phase}"].fx-cur').count() > 0, f"Arabic glossary phase {phase} did not activate")
        verify_geometry(glossary.locator("svg"), f"Arabic glossary phase {phase} {width} {theme} {motion}")
    boxes = contained_labels(glossary.locator("svg"))
    check(len(boxes) == 7, f"Arabic glossary box count changed {len(boxes)}")
    check(all(len(item["labels"]) == 2 and all(label["inside"] for label in item["labels"]) for item in boxes), f"Arabic glossary labels escaped boxes {boxes}")
    if screenshots and width in (390, 1440) and theme == "light" and motion == "no-preference":
        key.scroll_into_view_if_needed()
        page.screenshot(path=str(screenshots / f"monero-key-image-ar-{width}.png"), clip=key.bounding_box())
        glossary.scroll_into_view_if_needed()
        page.screenshot(path=str(screenshots / f"monero-glossary-ar-{width}.png"), clip=glossary.bounding_box())


def verify_english(page, base_url, width, theme, motion, screenshots):
    page.goto(f"{base_url}/monero-under-the-hood.html", wait_until="networkidle")
    check(page.evaluate("document.body.scrollWidth <= innerWidth + 1"), f"English {width} {theme} {motion}: horizontal overflow")
    figure = page.locator('[data-figure-id="key-image-en"]')
    figure.scroll_into_view_if_needed()
    page.wait_for_timeout(1800 if motion == "no-preference" else 150)
    pause(figure)
    replay = figure.locator(".figctl button").filter(has_text="Replay")
    toggle = figure.locator(".figctl button").filter(has_text="1st:")
    check(replay.count() == 1 and toggle.count() == 1, "English key image controls missing")
    replay.click()
    page.wait_for_timeout(1500 if motion == "no-preference" else 50)
    svg = figure.locator("svg")
    for state, active, inactive in (("first", ".fa-on", ".fb-on"), ("second", ".fb-on", ".fa-on")):
        opacities = svg.evaluate("(svg, selectors) => ({active: Number(getComputedStyle(svg.querySelector(selectors[0])).opacity), inactive: Number(getComputedStyle(svg.querySelector(selectors[1])).opacity)})", [active, inactive])
        check(opacities["active"] > .99 and opacities["inactive"] < .01, f"English {state} state leaked both alternatives {opacities}")
        verify_geometry(svg, f"English key image {state} {width} {theme} {motion}")
        if state == "first":
            toggle.click()
            page.wait_for_timeout(350)
    if screenshots and width in (390, 1440) and theme == "light" and motion == "no-preference":
        page.screenshot(path=str(screenshots / f"monero-key-image-en-{width}.png"), clip=figure.bounding_box())


def run(base_url, screenshots):
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        for width in (390, 1440):
            for theme in ("light", "dark"):
                for motion in ("no-preference", "reduce"):
                    context = browser.new_context(viewport={"width": width, "height": 950}, color_scheme=theme, reduced_motion=motion)
                    context.add_init_script(f"localStorage.setItem('cib-theme', '{theme}'); localStorage.setItem('cln-theme', '{theme}');")
                    page = context.new_page()
                    verify_arabic(page, base_url, width, theme, motion, screenshots)
                    verify_english(page, base_url, width, theme, motion, screenshots)
                    results.append({"width": width, "theme": theme, "motion": motion, "status": "pass"})
                    context.close()
        browser.close()
    return {"contexts": len(results), "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8934")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(args.base_url.rstrip("/"), args.screenshots), indent=2))
