from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGE = "bitcoin-codebase.html"
COMMIT = "9be056a8a72b624dae9623b2f7bded92c2a21c91"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class BitcoinCodebaseGuide(unittest.TestCase):
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

    def open_page(self, width=1440, reduced_motion="no-preference"):
        context = self.browser.new_context(
            viewport={"width": width, "height": 940 if width > 600 else 844},
            reduced_motion=reduced_motion,
        )
        page = context.new_page()
        errors = []
        failures = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "console",
            lambda message: errors.append(message.text) if message.type == "error" and "cloudflareinsights" not in message.text else None,
        )
        page.on(
            "response",
            lambda response: failures.append(f"{response.status} {response.url}")
            if response.status >= 400
            else None,
        )
        response = page.goto(f"{self.base}/{PAGE}", wait_until="networkidle")
        self.assertEqual(response.status, 200)
        return context, page, errors, failures

    def test_source_tabs_flow_and_theme(self):
        context, page, errors, failures = self.open_page()
        try:
            explorer = page.locator("[data-code-explorer]")
            tabs = explorer.get_by_role("tab")
            self.assertEqual(tabs.count(), 5)
            tabs.get_by_text("Peer", exact=True).click()
            self.assertIn("ProcessTransaction", page.locator("#code-peer").inner_text())
            tabs.get_by_text("Mine", exact=True).focus()
            page.keyboard.press("End")
            self.assertEqual(tabs.nth(4).get_attribute("aria-selected"), "true")
            source_links = page.locator('.code-meta a[href*="github.com/bitcoin/bitcoin/blob/"]')
            self.assertEqual(source_links.count(), 5)
            self.assertTrue(all(COMMIT in href for href in source_links.evaluate_all("links => links.map(link => link.href)")))

            flow = page.locator("[data-flow]")
            flow.scroll_into_view_if_needed()
            self.assertEqual(
                flow.locator("#flow-status").evaluate(
                    "node => getComputedStyle(node, '::before').display"
                ),
                "none",
            )
            flow.get_by_role("button", name="Next").click()
            self.assertEqual(flow.get_attribute("data-step"), "1")
            flow.get_by_role("button", name="Pause").click()
            paused = flow.get_attribute("data-step")
            page.wait_for_timeout(6200)
            self.assertEqual(flow.get_attribute("data-step"), paused)
            flow.get_by_role("button", name="Replay").click()
            self.assertEqual(flow.get_attribute("data-step"), "0")

            page.locator("#themego").click()
            self.assertEqual(page.locator("html").get_attribute("data-theme"), "dark")
            metrics = page.evaluate(
                """() => ({
                    documentWidth: document.documentElement.scrollWidth,
                    viewportWidth: innerWidth,
                    smallestBodyText: Math.min(...[...document.querySelectorAll('.annotation p, .module-grid p, .flow-narration p')].map(node => parseFloat(getComputedStyle(node).fontSize))),
                    brokenImages: [...document.images].filter(image => image.complete && image.naturalWidth === 0).length
                })"""
            )
            self.assertLessEqual(metrics["documentWidth"], metrics["viewportWidth"] + 1)
            self.assertGreaterEqual(metrics["smallestBodyText"], 13)
            self.assertEqual(metrics["brokenImages"], 0)
            page.screenshot(path="/tmp/bitcoin-codebase-dark-1440.png", full_page=True)
            self.assertEqual(errors, [])
            self.assertEqual(failures, [])
        finally:
            context.close()

    def test_mobile_and_reduced_motion(self):
        context, page, errors, failures = self.open_page(width=390, reduced_motion="reduce")
        try:
            flow = page.locator("[data-flow]")
            flow.scroll_into_view_if_needed()
            self.assertEqual(flow.get_attribute("data-playing"), "true")
            self.assertIn("Motion reduced", page.locator("#flow-status").inner_text())
            page.wait_for_function(
                "() => document.querySelector('[data-flow]')?.dataset.step === '1'",
                timeout=7000,
            )
            transitions = flow.locator(".flow-progress, .flow-node circle, .flow-packet").evaluate_all(
                "nodes => nodes.map(node => getComputedStyle(node).transitionDuration)"
            )
            self.assertTrue(all(value == "0s" for value in transitions))
            metrics = page.evaluate(
                """() => ({
                    documentWidth: document.documentElement.scrollWidth,
                    viewportWidth: innerWidth,
                    codeScrollable: [...document.querySelectorAll('.code-layout pre')].every(node => node.scrollWidth >= node.clientWidth),
                    navVisible: getComputedStyle(document.querySelector('.site-header')).display !== 'none'
                })"""
            )
            self.assertLessEqual(metrics["documentWidth"], metrics["viewportWidth"] + 1)
            self.assertTrue(metrics["codeScrollable"])
            self.assertTrue(metrics["navVisible"])
            page.screenshot(path="/tmp/bitcoin-codebase-mobile-390.png", full_page=True)
            self.assertEqual(errors, [])
            self.assertEqual(failures, [])
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
