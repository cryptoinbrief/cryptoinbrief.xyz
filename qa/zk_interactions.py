from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            pass


class ZkInteractions(unittest.TestCase):
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
            os.environ.get("CHROME_PATH"),
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

    def open_page(self, name):
        page = self.browser.new_page(
            viewport={"width": 1280, "height": 900},
            reduced_motion="no-preference",
        )

        def handle_request(route):
            url = route.request.url
            if url.startswith("http") and not url.startswith(self.base):
                route.fulfill(status=204, body="")
            else:
                route.continue_()

        page.route("**/*", handle_request)
        errors = []
        page.on("pageerror", lambda error: errors.append(f"page: {error}"))
        page.on(
            "console",
            lambda message: errors.append(f"console: {message.text}")
            if message.type == "error" and "cloudflareinsights" not in message.text
            else None,
        )
        page.on(
            "response",
            lambda response: errors.append(f"http {response.status}: {response.url}")
            if response.url.startswith(self.base) and response.status >= 400
            else None,
        )
        response = page.goto(f"{self.base}/{name}", wait_until="domcontentloaded")
        self.assertEqual(response.status, 200)
        page.wait_for_function("typeof nap === 'function' && typeof mulberry32 === 'function'")
        page.evaluate("nap = async function(){}; RND = mulberry32(20260920)")
        return page, errors

    def run_and_reset(self, page, lab, expected):
        page.locator(f"#{lab}run").click()
        page.wait_for_function(
            "id => document.getElementById(id).dataset.state === 'done'",
            arg=lab,
            timeout=20000,
        )
        output = page.locator(f"#{lab}out").inner_text()
        for text in expected:
            self.assertIn(text, output)
        self.assertFalse(page.locator(f"#{lab}cpy").is_disabled())
        page.locator(f"#{lab}rst").click()
        self.assertEqual(page.locator(f"#{lab}").get_attribute("data-state"), "idle")
        self.assertEqual(page.locator(f"#{lab}out").inner_text(), "")
        self.assertTrue(page.locator(f"#{lab}cpy").is_disabled())

    def test_zcash_labs_complete_reject_and_reset(self):
        page, errors = self.open_page("zcash.html")
        try:
            self.run_and_reset(
                page,
                "m1",
                ("REJECTED, nullifier already spent", "ledger: ACCEPTED", "amounts: none"),
            )
            self.run_and_reset(
                page,
                "m2",
                ("VIEW OK", "REJECTED", "owner spends", "ACCEPTED"),
            )
            self.assertEqual(errors, [])
        finally:
            page.close()

    def test_zero_knowledge_labs_complete_and_reset(self):
        page, errors = self.open_page("zero-knowledge-from-zero.html")
        try:
            self.run_and_reset(
                page,
                "m1",
                ("20 rounds clean", "1 in 1,048,576", "you know the word"),
            )
            page.evaluate("RND = function(){ return 0 }")
            page.locator("#m2seed").fill("qa-transcript")
            self.run_and_reset(
                page,
                "m2",
                ("faker: committed", "no door, caught", "identical odds"),
            )
            page.evaluate("RND = mulberry32(20260920)")
            self.run_and_reset(
                page,
                "m3",
                ("ADULT = YES", "Still sealed", "aggregate check"),
            )
            self.assertEqual(errors, [])
        finally:
            page.close()

    def test_zero_knowledge_failure_paths(self):
        page, errors = self.open_page("zero-knowledge-from-zero.html")
        try:
            page.locator("#m1knows").uncheck()
            page.evaluate("RND = function(){ return 0 }")
            page.locator("#m1right").click()
            page.wait_for_function("document.getElementById('m1').dataset.state === 'done'")
            cave = page.locator("#m1out").inner_text()
            self.assertIn("stuck: no word, no door", cave)
            self.assertIn("CAUGHT at round 1", cave)
            page.locator("#m1rst").click()
            self.assertEqual(page.locator("#m1").get_attribute("data-state"), "idle")

            page.evaluate("RND = mulberry32(20260920)")
            page.locator("#m3run").click()
            page.wait_for_function("document.getElementById('m3').dataset.state === 'done'")
            self.assertFalse(page.locator("#m3tamper").is_disabled())
            page.locator("#m3tamper").click()
            page.wait_for_function(
                "document.getElementById('m3out').textContent.includes('proof dead')"
            )
            tamper = page.locator("#m3out").inner_text()
            self.assertIn("INVALID", tamper)
            self.assertIn("proof dead", tamper)
            page.locator("#m3rst").click()
            self.assertEqual(page.locator("#m3").get_attribute("data-state"), "idle")

            current_year = page.evaluate("new Date().getFullYear()")
            page.locator("#m3year").fill(str(current_year))
            page.locator("#m3run").click()
            page.wait_for_function("document.getElementById('m3').dataset.state === 'done'")
            underage = page.locator("#m3out").inner_text()
            self.assertIn("NOT PROVEN ADULT", underage)
            self.assertIn("Honest refusal", underage)
            page.locator("#m3rst").click()
            self.assertEqual(page.locator("#m3").get_attribute("data-state"), "idle")
            self.assertEqual(errors, [])
        finally:
            page.close()

    def test_legacy_fragment_routing(self):
        routes = {
            "problem": "zcash.html#problem",
            "origin": "zcash.html#origin",
            "shielded": "zcash.html#shielded",
            "seallab": "zcash.html#seallab",
            "scorecard": "zcash.html#scorecard",
            "cave": "zero-knowledge-from-zero.html#cave",
            "cavelab": "zero-knowledge-from-zero.html#cave",
            "snark": "zero-knowledge-from-zero.html#snark",
            "honeypot": "zero-knowledge-from-zero.html#honeypot",
            "passport": "zero-knowledge-from-zero.html#passport",
            "ecosystem": "zero-knowledge-from-zero.html#today",
        }
        page = self.browser.new_page()
        try:
            response = page.goto(
                f"{self.base}/zcash-zk-proofs.html", wait_until="domcontentloaded"
            )
            self.assertEqual(response.status, 200)
            self.assertTrue(page.url.endswith("/zcash-zk-proofs.html"))
        finally:
            page.close()
        for fragment, target in routes.items():
            with self.subTest(fragment=fragment):
                page = self.browser.new_page()
                try:
                    page.goto(
                        f"{self.base}/zcash-zk-proofs.html#{fragment}",
                        wait_until="domcontentloaded",
                    )
                    page.wait_for_url(f"**/{target}")
                    self.assertTrue(page.url.endswith(f"/{target}"))
                finally:
                    page.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
