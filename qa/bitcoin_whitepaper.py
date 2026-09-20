from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGE = "bitcoin-whitepaper.html"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class BitcoinWhitepaper(unittest.TestCase):
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

    def open_page(self, width, color_scheme="light", reduced_motion="no-preference"):
        context = self.browser.new_context(
            viewport={"width": width, "height": 900 if width > 600 else 844},
            color_scheme=color_scheme,
            reduced_motion=reduced_motion,
        )
        page = context.new_page()
        errors = []
        failures = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.on("response", lambda response: failures.append(f"{response.status} {response.url}") if response.status >= 400 else None)
        response = page.goto(f"{self.base}/{PAGE}", wait_until="networkidle")
        self.assertEqual(response.status, 200)
        story = page.locator(".pow-story")
        story.wait_for(state="attached")
        story.scroll_into_view_if_needed()
        page.wait_for_timeout(150)
        return context, page, story, errors, failures

    def assert_layout(self, page, story):
        metrics = story.evaluate(
            """element => {
                const box = element.getBoundingClientRect();
                const visibleText = [...element.querySelectorAll('button, label, output, p, strong, span')]
                  .filter(node => getComputedStyle(node).display !== 'none' && node.getBoundingClientRect().height > 0);
                const collisionTargets = [...element.querySelectorAll('.pow-wallet, .pow-payment, .pow-block')];
                const out = collisionTargets.some(node => {
                  const rect = node.getBoundingClientRect();
                  return rect.left < box.left - 1 || rect.right > box.right + 1;
                });
                return {
                  viewport: innerWidth,
                  documentWidth: document.documentElement.scrollWidth,
                  minFont: Math.min(...visibleText.map(node => parseFloat(getComputedStyle(node).fontSize))),
                  out,
                  width: box.width,
                  height: box.height
                };
            }"""
        )
        self.assertLessEqual(metrics["documentWidth"], metrics["viewport"] + 1)
        self.assertFalse(metrics["out"])
        self.assertGreaterEqual(metrics["minFont"], 10)
        self.assertLessEqual(metrics["width"], 760)
        self.assertLess(metrics["height"], 1450)

    def test_source_and_static_content_contract(self):
        source = (ROOT / PAGE).read_text()
        self.assertIn("https://bitcoin.org/bitcoin.pdf", source)
        self.assertIn("https://developer.bitcoin.org/reference/rpc/getblockchaininfo.html", source)
        self.assertIn("https://developer.bitcoin.org/devguide/p2p_network.html#headers-first", source)
        self.assertIn("https://developer.bitcoin.org/devguide/transactions.html#avoiding-key-reuse", source)
        self.assertIn("Interactive model:", source)
        self.assertIn("bitcoin-codebase.html", source)
        self.assertIn("bitcoin-vs-monero-whitepapers.html", source)
        self.assertNotIn("—", source)
        self.assertNotIn("–", source)

    def test_autoplay_controls_and_causal_inputs(self):
        context, page, story, errors, failures = self.open_page(1440)
        try:
            self.assertEqual(story.get_attribute("data-stage"), "0")
            page.wait_for_function("document.querySelector('.pow-story').dataset.stage === '1'", timeout=7200)
            story.get_by_role("button", name="Pause").click()
            paused = story.get_attribute("data-stage")
            page.wait_for_timeout(6300)
            self.assertEqual(story.get_attribute("data-stage"), paused)
            story.locator('[data-chapter="3"]').click()
            self.assertIn("selected", story.locator(".pow-chain-status").inner_text())
            before = story.locator(".pow-risk").inner_text()
            story.locator("#pow-attacker").evaluate("node => { node.value = 40; node.dispatchEvent(new Event('input', {bubbles:true})); }")
            after = story.locator(".pow-risk").inner_text()
            self.assertNotEqual(before, after)
            self.assertIn("40%", after)
            story.locator("#pow-attacker").evaluate("node => { node.value = 10; node.dispatchEvent(new Event('input', {bubbles:true})); }")
            story.locator("#pow-confirmations").evaluate("node => { node.value = 6; node.dispatchEvent(new Event('input', {bubbles:true})); }")
            self.assertIn("0.024%", story.locator(".pow-risk").inner_text())
            self.assertEqual(story.locator('img[src="assets/coins/bitcoin.svg"]').count(), 1)
            self.assert_layout(page, story)
            self.assertEqual(errors, [])
            self.assertEqual(failures, [])
        finally:
            context.close()

    def test_mobile_dark_and_reduced_motion(self):
        context, page, story, errors, failures = self.open_page(390, color_scheme="dark", reduced_motion="reduce")
        try:
            page.evaluate("document.documentElement.dataset.theme = 'dark'")
            page.wait_for_function("document.querySelector('.pow-story').dataset.stage === '1'", timeout=7200)
            self.assertEqual(story.get_attribute("data-stage"), "1")
            transitions = story.locator(".pow-payment, .pow-block").evaluate_all("nodes => nodes.map(node => getComputedStyle(node).transitionDuration)")
            self.assertTrue(all(value == "0s" for value in transitions))
            self.assert_layout(page, story)
            self.assertEqual(errors, [])
            self.assertEqual(failures, [])
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
