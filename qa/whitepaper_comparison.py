import os
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
URL = os.getenv("SITE_URL", "http://127.0.0.1:8934") + "/bitcoin-vs-monero-whitepapers.html"


class WhitepaperComparisonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="chrome", headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def open_page(self, width=1440, theme="light", reduced_motion="no-preference"):
        context = self.browser.new_context(
            viewport={"width": width, "height": 900},
            reduced_motion=reduced_motion,
            color_scheme=theme,
        )
        context.add_init_script(f"localStorage.setItem('cib-theme', '{theme}')")
        page = context.new_page()
        errors = []
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" and "cloudflareinsights" not in message.text else None)
        page.goto(URL, wait_until="networkidle")
        lab = page.locator("#paper-payment-lab")
        lab.scroll_into_view_if_needed()
        page.wait_for_timeout(250)
        return context, page, lab, errors

    def assert_layout(self, page, lab, width):
        metrics = page.evaluate(
            """() => ({
                viewport: innerWidth,
                documentWidth: document.documentElement.scrollWidth,
                brokenImages: [...document.images].filter(image => image.complete && image.naturalWidth === 0).length,
                minSvgText: Math.min(...[...document.querySelectorAll('#paper-payment-lab svg text')].map(node => parseFloat(getComputedStyle(node).fontSize))),
                scenes: [...document.querySelectorAll('.paper-scene')].map(node => {
                    const box = node.getBoundingClientRect();
                    return {left: box.left, right: box.right, width: box.width};
                })
            })"""
        )
        self.assertLessEqual(metrics["documentWidth"], metrics["viewport"] + 1)
        self.assertEqual(metrics["brokenImages"], 0)
        self.assertGreaterEqual(metrics["minSvgText"], 10)
        self.assertTrue(all(scene["left"] >= -1 and scene["right"] <= width + 1 for scene in metrics["scenes"]))
        self.assertEqual(lab.locator("svg").count(), 2)

    def test_autoplay_views_and_controls(self):
        context, page, lab, errors = self.open_page()
        try:
            self.assertEqual(lab.get_attribute("data-view"), "observer")
            page.wait_for_timeout(4000)
            self.assertEqual(lab.get_attribute("data-phase"), "2")
            self.assertIn("repeated key image", lab.locator(".paper-narrator").inner_text())
            hidden_recipient = lab.locator(".reveal-recipient").evaluate_all(
                "nodes => nodes.map(node => parseFloat(getComputedStyle(node).opacity))"
            )
            self.assertTrue(all(value == 0 for value in hidden_recipient))
            page.wait_for_timeout(2300)
            self.assertEqual(lab.get_attribute("data-view"), "recipient")
            lab.get_by_role("button", name="Pause").click()
            held = (lab.get_attribute("data-view"), lab.get_attribute("data-phase"))
            page.wait_for_timeout(6300)
            self.assertEqual((lab.get_attribute("data-view"), lab.get_attribute("data-phase")), held)
            lab.get_by_role("tab", name="Public observer").click()
            self.assertEqual(lab.get_attribute("data-view"), "observer")
            lab.get_by_role("tab", name="Public observer").press("ArrowRight")
            self.assertEqual(lab.get_attribute("data-view"), "recipient")
            lab.get_by_role("button", name="Replay").click()
            self.assertEqual(lab.get_attribute("data-phase"), "0")
            self.assert_layout(page, lab, 1440)
            self.assertEqual(errors, [])
        finally:
            context.close()

    def test_mobile_dark_and_reduced_motion(self):
        context, page, lab, errors = self.open_page(width=390, theme="dark", reduced_motion="reduce")
        try:
            transitions = lab.locator(".reveal, .flow-line").evaluate_all(
                "nodes => nodes.map(node => getComputedStyle(node).transitionDuration)"
            )
            self.assertTrue(all(value == "0s" for value in transitions))
            page.wait_for_timeout(4000)
            self.assertEqual(lab.get_attribute("data-phase"), "2")
            lab.get_by_role("tab", name="Recipient wallet").click()
            page.wait_for_timeout(2000)
            self.assertIn("private view key", lab.locator(".paper-narrator").inner_text())
            self.assert_layout(page, lab, 390)
            self.assertEqual(errors, [])
        finally:
            context.close()

    def test_source_boundary_and_copy(self):
        source = (ROOT / "bitcoin-vs-monero-whitepapers.html").read_text()
        self.assertIn("https://bitcoin.org/bitcoin.pdf", source)
        self.assertIn("https://www.getmonero.org/resources/research-lab/pubs/cryptonote-whitepaper.pdf", source)
        self.assertIn("October 17, 2013", source)
        self.assertIn("It is not a complete specification of today’s Monero", source)
        self.assertIn("the amount stays visible in the 2013 CryptoNote model", source)
        self.assertNotIn("—", source)
        words = len(source.split())
        self.assertGreater(words, 1500)
        self.assertLess(words, 4000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
