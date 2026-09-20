from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGE = "getting-monero.html"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class AcquisitionRoutes(unittest.TestCase):
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
            viewport={"width": width, "height": 900 if width > 600 else 844},
            reduced_motion=reduced_motion,
        )
        page = context.new_page()
        errors = []
        failures = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "console",
            lambda message: errors.append(message.text) if message.type == "error" and "cloudflareinsights" not in (message.location or {}).get("url", "") else None,
        )
        page.on(
            "response",
            lambda response: failures.append(f"{response.status} {response.url}")
            if response.status >= 400
            else None,
        )
        response = page.goto(f"{self.base}/{PAGE}", wait_until="networkidle")
        self.assertEqual(response.status, 200)
        explorer = page.locator(".acq-explorer")
        explorer.wait_for(state="attached")
        explorer.evaluate("element => element.scrollIntoView({block: 'center'})")
        page.wait_for_timeout(150)
        return context, page, explorer, errors, failures

    def restart(self, explorer):
        explorer.get_by_role("button", name="Replay").click()
        self.assertEqual(explorer.get_attribute("data-stage"), "0")
        self.assertEqual(explorer.locator(".acq-narrator").get_attribute("aria-live"), "polite")

    def wait_for_stage(self, page, expected, timeout=7500):
        page.wait_for_function(
            "stage => document.querySelector('.acq-explorer')?.dataset.stage === stage",
            arg=str(expected),
            timeout=timeout,
        )

    def assert_geometry(self, page, explorer, desktop):
        metrics = explorer.evaluate(
            """element => {
                const box = element.getBoundingClientRect();
                const figure = element.querySelector('.acq-figure').getBoundingClientRect();
                const svg = element.querySelector('.acq-map').getBoundingClientRect();
                const nodes = [...element.querySelectorAll('.acq-node')].map(node => node.getBoundingClientRect());
                const marker = element.querySelector('.acq-marker').getBoundingClientRect();
                const boundaryLabel = element.querySelector('.acq-boundary-label').getBoundingClientRect();
                const collides = (one, two) => one.left < two.right && one.right > two.left && one.top < two.bottom && one.bottom > two.top;
                const labels = [...element.querySelectorAll(
                    '.acq-kicker, .acq-routes button, .acq-stage-number, .acq-narrator div strong, .acq-boundary-label, .acq-map text, .acq-trust strong, .acq-controls button'
                )].filter(node => getComputedStyle(node).display !== 'none');
                const prose = [...element.querySelectorAll('.acq-route-copy p, .acq-narrator div p, .acq-trust p')];
                return {
                    viewport: innerWidth,
                    documentWidth: document.documentElement.scrollWidth,
                    width: box.width,
                    height: box.height,
                    svgWidth: svg.width,
                    svgHeight: svg.height,
                    figureOverflow: figure.right > innerWidth + 1,
                    brokenImages: [...element.querySelectorAll('img, image')].filter(image => {
                        if (image instanceof HTMLImageElement) return image.complete && image.naturalWidth === 0;
                        return false;
                    }).length,
                    nodeOverflow: nodes.some(node => node.left < svg.left - 1 || node.right > svg.right + 1 || node.top < svg.top - 1 || node.bottom > svg.bottom + 1),
                    markerCollision: nodes.some(node => collides(marker, node)),
                    boundaryLabelCollision: nodes.some(node => collides(boundaryLabel, node)),
                    minLabel: Math.min(...labels.map(node => parseFloat(getComputedStyle(node).fontSize))),
                    minProse: Math.min(...prose.map(node => parseFloat(getComputedStyle(node).fontSize))),
                    boundaryVisible: getComputedStyle(element.querySelector('.acq-boundary-label')).display !== 'none',
                    boundaryHeight: element.querySelector('.acq-boundary-label').getBoundingClientRect().height
                };
            }"""
        )
        self.assertLessEqual(metrics["documentWidth"], metrics["viewport"] + 1)
        self.assertFalse(metrics["figureOverflow"])
        self.assertFalse(metrics["nodeOverflow"])
        self.assertFalse(metrics["markerCollision"])
        self.assertFalse(metrics["boundaryLabelCollision"])
        self.assertEqual(metrics["brokenImages"], 0)
        self.assertGreaterEqual(metrics["minLabel"], 12)
        self.assertGreaterEqual(metrics["minProse"], 14)
        if metrics["boundaryVisible"]:
            self.assertGreaterEqual(metrics["boundaryHeight"], 11.5)
        if desktop:
            self.assertLessEqual(metrics["width"], 760)
            self.assertLessEqual(metrics["height"], 850)
            self.assertLessEqual(metrics["svgHeight"], 330)
        else:
            self.assertLessEqual(metrics["width"], 350)

    def test_routes_autoplay_controls_and_offscreen_pause(self):
        context, page, explorer, errors, failures = self.open_page()
        try:
            tabs = explorer.get_by_role("tab")
            self.assertEqual(tabs.count(), 3)
            self.assertEqual(explorer.locator("figure svg").count(), 1)
            self.assertEqual(explorer.locator(".expand-diagram").count(), 1)
            self.assertIn("Atomic swap", explorer.locator(".acq-route-copy strong").inner_text())
            self.assertIn("refund path", explorer.locator(".acq-trust").inner_text())

            self.restart(explorer)
            initial_transform = explorer.locator(".acq-marker").evaluate("node => getComputedStyle(node).transform")
            self.wait_for_stage(page, 1)
            self.assertEqual(explorer.locator(".acq-narrator").get_attribute("aria-live"), "off")
            page.wait_for_timeout(850)
            next_transform = explorer.locator(".acq-marker").evaluate("node => getComputedStyle(node).transform")
            self.assertNotEqual(initial_transform, next_transform)

            explorer.get_by_role("button", name="Pause").click()
            paused_stage = explorer.get_attribute("data-stage")
            page.wait_for_timeout(6300)
            self.assertEqual(explorer.get_attribute("data-stage"), paused_stage)
            explorer.get_by_role("button", name="Resume").click()
            self.wait_for_stage(page, 2)

            self.restart(explorer)
            self.wait_for_stage(page, 1)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(6300)
            self.assertEqual(explorer.get_attribute("data-stage"), "1")
            explorer.evaluate("element => element.scrollIntoView({block: 'center'})")
            self.wait_for_stage(page, 2)

            tabs.get_by_text("Haveno P2P").click()
            self.assertEqual(explorer.get_attribute("data-stage"), "0")
            self.assertIn("2 of 3 multisig", explorer.locator(".acq-route-copy").inner_text())
            self.assertIn("payment provider may link real identities", explorer.locator(".acq-trust").inner_text())
            explorer.get_by_role("button", name="Next stage").click()
            explorer.get_by_role("button", name="Next stage").click()
            self.assertIn("outside the protocol", explorer.locator(".acq-narrator").inner_text())

            tabs.get_by_text("Exchange", exact=True).click()
            self.assertIn("internal balance", explorer.locator(".acq-route-copy").inner_text())
            self.assertIn("until XMR reaches your wallet", explorer.locator(".acq-trust").inner_text())
            for _ in range(3):
                explorer.get_by_role("button", name="Next stage").click()
            self.assertIn("self custody", explorer.locator(".acq-narrator").inner_text())

            self.assert_geometry(page, explorer, desktop=True)
            self.assertEqual(errors, [])
            self.assertEqual(failures, [])
        finally:
            context.close()

    def test_mobile_reduced_motion_keeps_semantic_autoplay(self):
        context, page, explorer, errors, failures = self.open_page(width=390, reduced_motion="reduce")
        try:
            self.restart(explorer)
            transitions = explorer.locator(".acq-marker, .acq-links path, .acq-node rect").evaluate_all(
                "nodes => nodes.map(node => getComputedStyle(node).transitionDuration)"
            )
            self.assertTrue(all(value == "0s" for value in transitions))
            self.wait_for_stage(page, 1)
            self.assertEqual(explorer.locator(".acq-narrator").get_attribute("aria-live"), "off")
            self.assertEqual(explorer.locator(".acq-map").get_attribute("viewBox"), "0 0 340 540")
            self.assert_geometry(page, explorer, desktop=False)
            self.assertEqual(errors, [])
            self.assertEqual(failures, [])
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
