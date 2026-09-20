from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "solana.html": {
        "resource": "Noor wallet",
        "gate": "Write lock found",
        "title": "One write waits behind the other",
    },
    "sui.html": {
        "resource": "Bazaar shared",
        "gate": "Consensus order",
        "title": "Consensus orders the Bazaar calls",
    },
}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class ExecutionStory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = partial(QuietHandler, directory=str(ROOT))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        candidates = (
            os.environ.get("CHROME_BIN"),
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        )
        executable = next((item for item in candidates if item and Path(item).is_file()), None)
        if not executable:
            raise RuntimeError("Set CHROME_BIN to a Chromium based browser executable")
        cls.browser = cls.playwright.chromium.launch(headless=True, executable_path=executable)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def open_page(self, name, reduced_motion="no-preference", width=1440):
        context = self.browser.new_context(
            viewport={"width": width, "height": 950 if width > 600 else 844},
            reduced_motion=reduced_motion,
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "console",
            lambda message: errors.append(message.text) if message.type == "error" and "cloudflareinsights" not in (message.location or {}).get("url", "") else None,
        )
        response = page.goto(f"{self.base}/{name}", wait_until="networkidle")
        self.assertEqual(response.status, 200)
        story = page.locator(".exec-story")
        story.wait_for(state="attached")
        story.evaluate("element => element.scrollIntoView({block: 'center'})")
        page.wait_for_timeout(150)
        return context, page, story, errors

    def restart(self, story):
        story.get_by_role("button", name="Replay").click()
        self.assertEqual(story.get_attribute("data-stage"), "0")
        self.assertEqual(story.locator(".est-narrator").get_attribute("aria-live"), "polite")

    def wait_for_stage(self, page, expected, timeout=4000):
        page.wait_for_function(
            "stage => document.querySelector('.exec-story')?.dataset.stage === stage",
            arg=str(expected),
            timeout=timeout,
        )

    def assert_story_layout(self, page, story):
        metrics = story.evaluate(
            """element => ({
                documentWidth: document.documentElement.scrollWidth,
                viewportWidth: innerWidth,
                storyHeight: element.getBoundingClientRect().height,
                clippedCards: [...element.querySelectorAll('.est-tx')]
                    .filter(card => card.scrollWidth > card.clientWidth || card.scrollHeight > card.clientHeight).length,
                labelSizes: [...element.querySelectorAll(
                    '.est-zone > span, .est-lane span, .est-gate span, .est-collision b, .est-resources span, .est-state, .est-tx-top b, .est-tx-top em, .est-tx > strong, .est-stage-number, .est-stage-title, .est-result strong, .est-controls button'
                )].filter(label => getComputedStyle(label).display !== 'none')
                    .map(label => parseFloat(getComputedStyle(label).fontSize)),
                proseSizes: [...element.querySelectorAll('.est-intro, .est-stage-copy, .est-result small')]
                    .map(label => parseFloat(getComputedStyle(label).fontSize))
            })"""
        )
        self.assertLessEqual(metrics["documentWidth"], metrics["viewportWidth"] + 1)
        if metrics["viewportWidth"] > 600:
            self.assertLessEqual(metrics["storyHeight"], 900)
        self.assertEqual(metrics["clippedCards"], 0)
        self.assertTrue(all(size >= 12 for size in metrics["labelSizes"]))
        self.assertTrue(all(size >= 14 for size in metrics["proseSizes"]))

    def assert_conflict_schedule(self, story, expected):
        story.locator(".est-conflict").click()
        self.assertEqual(story.locator(".est-conflict").get_attribute("aria-pressed"), "true")
        self.assertEqual(story.locator(".est-narrator").get_attribute("aria-live"), "polite")
        story.get_by_role("button", name="Next stage").click()
        story.get_by_role("button", name="Next stage").click()
        self.assertEqual(story.get_attribute("data-stage"), "2")
        self.assertEqual(story.locator(".est-stage-title").inner_text(), expected["title"])
        cards = story.locator(".est-tx")
        first = cards.nth(0)
        second = cards.nth(1)
        third = cards.nth(2)
        self.assertEqual(first.get_attribute("data-wave"), "0")
        self.assertEqual(second.get_attribute("data-wave"), "0")
        self.assertEqual(third.get_attribute("data-wave"), "1")
        self.assertEqual(first.get_attribute("data-lane"), third.get_attribute("data-lane"))
        self.assertNotEqual(first.get_attribute("data-lane"), second.get_attribute("data-lane"))
        self.assertEqual(third.get_attribute("data-state"), "queued")
        self.assertEqual(story.locator(".est-gate span").inner_text(), expected["gate"])
        shared = story.locator(".est-resources .is-shared")
        self.assertEqual(shared.count(), 2)
        self.assertTrue(all(value == expected["resource"] for value in shared.all_inner_texts()))
        story.get_by_role("button", name="Next stage").click()
        self.assertEqual(story.get_attribute("data-stage"), "3")
        self.assertEqual(story.locator(".est-result strong").inner_text(), "2 execution waves")
        self.assertIn("1 dependency found", story.locator(".est-result small").inner_text())

    def assert_independent_schedule(self, story):
        story.locator(".est-conflict").click()
        self.assertEqual(story.locator(".est-conflict").get_attribute("aria-pressed"), "false")
        for _ in range(3):
            story.get_by_role("button", name="Next stage").click()
        self.assertEqual(story.get_attribute("data-stage"), "3")
        waves = story.locator(".est-tx").evaluate_all("cards => cards.map(card => card.dataset.wave)")
        lanes = story.locator(".est-tx").evaluate_all("cards => cards.map(card => card.dataset.lane)")
        self.assertEqual(waves, ["0", "0", "0"])
        self.assertEqual(len(set(lanes)), 3)
        self.assertEqual(story.locator(".est-result strong").inner_text(), "1 execution wave")
        self.assertIn("0 dependencies found", story.locator(".est-result small").inner_text())

    def test_autoplay_controls_and_causal_schedule(self):
        for name, expected in PAGES.items():
            with self.subTest(page=name):
                context, page, story, errors = self.open_page(name)
                try:
                    self.restart(story)
                    self.wait_for_stage(page, 1)
                    self.assertEqual(story.locator(".est-narrator").get_attribute("aria-live"), "off")
                    story.get_by_role("button", name="Pause").click()
                    paused_stage = story.get_attribute("data-stage")
                    page.wait_for_timeout(2900)
                    self.assertEqual(story.get_attribute("data-stage"), paused_stage)
                    story.get_by_role("button", name="Resume").click()
                    self.wait_for_stage(page, 2)

                    self.restart(story)
                    self.wait_for_stage(page, 1)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2900)
                    self.assertEqual(story.get_attribute("data-stage"), "1")
                    story.evaluate("element => element.scrollIntoView({block: 'center'})")
                    self.wait_for_stage(page, 2)

                    page.evaluate(
                        """() => {
                            Object.defineProperty(document, 'hidden', {configurable: true, get: () => true});
                            document.dispatchEvent(new Event('visibilitychange'));
                        }"""
                    )
                    page.wait_for_timeout(2900)
                    self.assertEqual(story.get_attribute("data-stage"), "2")
                    page.evaluate(
                        """() => {
                            delete document.hidden;
                            document.dispatchEvent(new Event('visibilitychange'));
                        }"""
                    )
                    self.wait_for_stage(page, 3)

                    self.assert_conflict_schedule(story, expected)
                    self.assert_story_layout(page, story)
                    self.assert_independent_schedule(story)
                    self.assertEqual(errors, [])
                finally:
                    context.close()

    def test_reduced_motion_and_mobile_legibility(self):
        for name in PAGES:
            with self.subTest(page=name):
                context, page, story, errors = self.open_page(name, reduced_motion="reduce", width=390)
                try:
                    self.restart(story)
                    transitions = story.locator(".est-tx").evaluate_all(
                        "cards => cards.map(card => getComputedStyle(card).transitionDuration)"
                    )
                    self.assertTrue(all(value == "0s" for value in transitions))
                    self.wait_for_stage(page, 1)
                    self.assertEqual(story.locator(".est-narrator").get_attribute("aria-live"), "off")
                    metrics = story.evaluate(
                        """element => ({
                            brokenLogos: [...element.querySelectorAll('img')]
                                .filter(image => image.complete && image.naturalWidth === 0).length,
                        })"""
                    )
                    self.assertEqual(metrics["brokenLogos"], 0)
                    self.assert_story_layout(page, story)
                    self.assertEqual(errors, [])
                finally:
                    context.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
