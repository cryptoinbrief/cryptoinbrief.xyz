import argparse
import json

from playwright.sync_api import sync_playwright


PAGES = {
    "zcash.html": "zcash",
    "zero-knowledge-from-zero.html": "zk",
    "monero-under-the-hood.html": "monero",
}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def open_story(browser, base_url, name, reduced_motion="no-preference", width=1440):
    context = browser.new_context(
        viewport={"width": width, "height": 900},
        reduced_motion=reduced_motion,
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    response = page.goto(f"{base_url}/{name}", wait_until="networkidle")
    check(response.status == 200, f"{name}: HTTP {response.status}")
    page.wait_for_selector(".privacy-story")
    story = page.locator(".privacy-story")
    check(story.count() == 1, f"{name}: privacy story missing")
    check(page.locator(".lead + .privacy-story").count() == 1, f"{name}: story is not directly after the lead")
    check(not errors, f"{name}: load errors {errors}")
    story.scroll_into_view_if_needed()
    return context, page, story, errors


def run(base_url):
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        for name, kind in PAGES.items():
            context, page, story, errors = open_story(browser, base_url, name)
            page.wait_for_function("document.querySelector('.privacy-story').dataset.playing === 'true'")
            first = story.get_attribute("data-phase")
            page.wait_for_function(
                "first => document.querySelector('.privacy-story').dataset.phase !== first",
                arg=first,
                timeout=4500,
            )
            check(story.get_attribute("data-playing") == "true", f"{name}: autoplay did not start")
            page.locator(".ps-pause").click()
            paused = story.get_attribute("data-phase")
            page.wait_for_timeout(2900)
            check(story.get_attribute("data-phase") == paused, f"{name}: pause did not hold the stage")
            page.locator(".ps-next").click()
            check(story.get_attribute("data-phase") == str((int(paused) + 1) % 4), f"{name}: next stage failed")
            page.locator(".ps-replay").click()
            check(story.get_attribute("data-phase") == "0", f"{name}: replay did not return to stage one")
            check(page.locator(".ps-copy").get_attribute("aria-live") == "polite", f"{name}: manual change was not announced")
            page.locator(".ps-pause").click()

            if kind == "zcash":
                page.locator('.ps-step[data-step="3"]').click()
                page.wait_for_timeout(1700)
                rejected = page.locator(".ps-status.is-bad")
                check(rejected.inner_text() == "REPLAY REJECTED", "Zcash: replay rejection label missing")
                check(float(rejected.evaluate("element => getComputedStyle(element).opacity")) > .95, "Zcash: rejection outcome hidden")
                check(page.locator('.ps-brand img[alt="Zcash"]').count() == 1, "Zcash: official logo missing")
                page.locator(".ps-choice").click()
                page.wait_for_timeout(1700)
                accepted = page.locator(".ps-status.ps-fresh")
                check(float(accepted.evaluate("element => getComputedStyle(element).opacity")) > .95, "Zcash: fresh note outcome hidden")
                check("FRESH NULLIFIER ACCEPTED" in accepted.inner_text(), "Zcash: fresh note was not accepted")

            if kind == "zk":
                check(page.locator(".ps-brand img").count() == 0, "ZK: unrelated coin logo shown")
                page.locator(".ps-age").fill("15")
                page.locator(".ps-nonce").fill("demo nonce ! 72")
                check(page.locator(".ps-nonce").input_value() == "demononce72", "ZK: fictional nonce was not sanitized")
                page.locator('.ps-step[data-step="3"]').click()
                page.wait_for_timeout(900)
                result = page.locator(".ps-status").inner_text()
                check("ELIGIBLE: NO" in result and "AGE: HIDDEN" in result, "ZK: private predicate result incorrect")
                check("15" not in result, "ZK: private age leaked into verifier output")

            if kind == "monero":
                page.locator('.ps-step[data-step="3"]').click()
                page.wait_for_timeout(1100)
                check(page.locator('.ps-status:has-text("SIGNER: UNRESOLVED")').count() == 1, "Monero: signer ambiguity missing")
                borders = page.locator(".ps-candidate").evaluate_all("nodes => nodes.map(node => getComputedStyle(node).borderColor)")
                check(len(set(borders)) == 1, "Monero: one candidate was visually identified as the sender")
                check(page.locator('.ps-brand img[alt="Monero"]').count() == 1, "Monero: official logo missing")
                page.locator(".ps-choice").click()
                page.wait_for_timeout(1000)
                invalid = page.locator(".ps-status.ps-invalid")
                check(float(invalid.evaluate("element => getComputedStyle(element).opacity")) > .95, "Monero: tampered signature outcome hidden")

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(400)
            check(story.get_attribute("data-playing") == "false", f"{name}: story kept playing offscreen")
            check(not errors, f"{name}: interaction errors {errors}")
            results.append({"page": name, "autoplay": "pass", "controls": "pass", "outcome": "pass"})
            context.close()

        for name in PAGES:
            context, page, story, errors = open_story(browser, base_url, name, reduced_motion="reduce", width=390)
            page.wait_for_function("document.querySelector('.privacy-story').dataset.playing === 'true'")
            reduced_phase = story.get_attribute("data-phase")
            page.wait_for_function(
                "phase => document.querySelector('.privacy-story').dataset.phase !== phase",
                arg=reduced_phase,
                timeout=4500,
            )
            page.locator('.ps-step[data-step="3"]').click()
            page.wait_for_timeout(100)
            check(story.get_attribute("data-playing") == "true", f"{name}: reduced motion semantic autoplay stopped")
            check(page.locator(".ps-packet").evaluate("element => getComputedStyle(element).display") == "none", f"{name}: packet still moved in reduced motion")
            check(story.evaluate("element => element.scrollWidth <= element.clientWidth + 1"), f"{name}: mobile overflow")
            height = story.evaluate("element => Math.round(element.getBoundingClientRect().height)")
            check(380 <= height <= 490, f"{name}: mobile story height {height}px")
            geometry = page.evaluate("""() => {
                const scene = document.querySelector('.privacy-story .ps-scene').getBoundingClientRect();
                const boxes = [...document.querySelectorAll('.privacy-story .ps-node')].map(node => {
                    const box = node.getBoundingClientRect();
                    return {left: box.left, right: box.right, top: box.top, bottom: box.bottom, contentFits: node.scrollHeight <= node.clientHeight + 1};
                });
                const input = document.querySelector('.privacy-story .ps-inputs')?.getBoundingClientRect();
                return {scene: {left: scene.left, right: scene.right, top: scene.top, bottom: scene.bottom}, boxes, input: input && {left: input.left, right: input.right, top: input.top, bottom: input.bottom}};
            }""")
            for box in geometry["boxes"]:
                check(box["left"] >= geometry["scene"]["left"] and box["right"] <= geometry["scene"]["right"] and box["top"] >= geometry["scene"]["top"] and box["bottom"] <= geometry["scene"]["bottom"], f"{name}: scene node clipped {box}")
                check(box["contentFits"], f"{name}: scene node text clipped {box}")
            if name == "zero-knowledge-from-zero.html":
                check(geometry["input"]["bottom"] <= min(box["top"] for box in geometry["boxes"]), f"{name}: private inputs overlap the proof flow")
            visible_statuses = page.locator(".ps-status").evaluate_all("nodes => nodes.filter(node => Number(getComputedStyle(node).opacity) > .95).length")
            check(visible_statuses >= 1, f"{name}: reduced motion outcome hidden")
            check(not errors, f"{name}: reduced motion errors {errors}")
            results.append({"page": name, "reduced_motion": "pass", "mobile_height": height})
            context.close()
        browser.close()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8934")
    args = parser.parse_args()
    print(json.dumps(run(args.base_url.rstrip("/")), indent=2))
