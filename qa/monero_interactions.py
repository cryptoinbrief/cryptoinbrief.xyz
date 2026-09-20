from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGES = ("monero-under-the-hood.html", "monero-from-zero-ar.html")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class MoneroInteractions(unittest.TestCase):
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

    def open_page(self, name, width=1280):
        page = self.browser.new_page(
            viewport={"width": width, "height": 800},
            reduced_motion="no-preference",
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "console",
            lambda message: errors.append(message.text) if message.type == "error" and "cloudflareinsights" not in message.text else None,
        )
        page.goto(f"{self.base}/{name}", wait_until="domcontentloaded")
        page.wait_for_timeout(200)
        return page, errors

    def exercise_english_figures(self, page):
        figures = page.locator("figure")
        self.assertEqual(figures.count(), 11)
        self.assertEqual(page.locator(".figctl").count(), figures.count())
        for index in range(figures.count()):
            figure = figures.nth(index)
            figure.scroll_into_view_if_needed()
            figure.get_by_role("button", name="Replay").click()
            self.assertGreater(figure.locator("svg").evaluate("svg => (svg.__anims || []).length"), 0)
            step = figure.get_by_role("button", name="Step")
            if step.count():
                step.click()
                self.assertGreater(figure.locator(".figcur").count(), 0)
            toggles = figure.locator(".figctl button:not(:has-text('Replay')):not(:has-text('Step'))")
            if toggles.count():
                before = figure.locator("svg").get_attribute("class") or ""
                toggles.first.click()
                after = figure.locator("svg").get_attribute("class") or ""
                self.assertNotEqual(before, after)
            target = figure.locator("[data-note]").first
            if target.count():
                target.dispatch_event("pointerenter", {"pointerType": "mouse"})
                self.assertTrue(figure.locator(".fignote").evaluate("el => el.classList.contains('on')"))
                target.dispatch_event("pointerleave", {"pointerType": "mouse"})

    def exercise_arabic_figures(self, page):
        figures = page.locator("figure[data-fig]")
        self.assertEqual(figures.count(), 13)
        for index in range(figures.count()):
            figure = figures.nth(index)
            figure.scroll_into_view_if_needed()
            page.wait_for_function("el => el.dataset.fxDone === '1'", arg=figure.element_handle())
            figure.get_by_role("button", name="إعادة").click()
            self.assertTrue(figure.locator("svg").evaluate("svg => [...svg.querySelectorAll('path,line,rect,circle,ellipse,polygon,polyline,text')].some(el => el.style.transition)"))
            step = figure.get_by_role("button", name="خطوة")
            if step.count():
                step.click()
                self.assertGreater(figure.locator(".fx-cur").count(), 0)
            toggle = figure.locator(".fx-strip button").filter(has_text="اعرض")
            if toggle.count():
                before = figure.locator("svg").get_attribute("class") or ""
                toggle.click()
                after = figure.locator("svg").get_attribute("class") or ""
                self.assertNotEqual(before, after)
            target = figure.locator("[data-note]").first
            if target.count():
                target.dispatch_event("pointerenter", {"pointerType": "mouse"})
                self.assertTrue(figure.locator(".fx-note").evaluate("el => el.classList.contains('on')"))
                target.dispatch_event("pointerleave", {"pointerType": "mouse"})
        self.assertEqual(page.locator(".fx-strip").count(), figures.count())

    def test_english_labs_and_figures(self):
        page, errors = self.open_page(PAGES[0])
        try:
            page.wait_for_function("typeof Hp2 === 'bigint'")
            page.click('button[onclick="stGenWallet()"]')
            page.click("#stpaybtn")
            page.click("#stagainbtn")
            page.click("#stscanbtn")
            self.assertEqual(page.evaluate("st.pays.length"), 2)
            self.assertTrue(page.evaluate("st.pays.every(p => modpow(G, st.a, P) !== 0n && modpow(p.R, st.a, P) !== 0n)"))
            self.assertIn("that's mine", page.locator("#stout").inner_text())
            page.click("#sp0")
            self.assertIn("accepted", page.locator("#ringout").inner_text())
            page.click("#sp0b")
            self.assertIn("REJECTED", page.locator("#ringout").inner_text())
            page.click("#sp1")
            self.assertEqual(page.evaluate("ledger.size"), 2)
            ring_checks = page.evaluate("""
                async () => {
                    const secrets = [1n, 2n, 3n, 4n, 5n];
                    const ring = secrets.map(secret => modpow(G, secret, P));
                    const hps = await Promise.all(ring.map(hpOf));
                    const sig = await lsagSign('qa message', ring, hps, 0, secrets[0]);
                    const valid = await lsagVerify('qa message', ring, hps, sig);
                    const tampered = await lsagVerify('changed message', ring, hps, sig);
                    const oldShortcut = [];
                    for (const key of ring) oldShortcut.push(modpow(key, await Hs('hp', key), P) === sig.I);
                    return {valid, tampered, oldShortcut};
                }
            """)
            self.assertTrue(ring_checks["valid"])
            self.assertFalse(ring_checks["tampered"])
            self.assertFalse(ring_checks["oldShortcut"][0])
            page.click('button[onclick="pedTamper()"]')
            self.assertIn("fails", page.locator("#pedout").inner_text())
            page.click('button[onclick="pedNegative()"]')
            self.assertIn("passes", page.locator("#pedout").inner_text())
            self.assertIn("not this example", page.locator("#pednote").inner_text())
            page.locator("#v1sl").evaluate("el => { el.value = 70; el.dispatchEvent(new Event('input', {bubbles:true})); }")
            self.assertIn("70", page.locator("#v1v").inner_text())
            page.click('button[onclick="pedRender()"]')
            self.assertIn("Honest split", page.locator("#pednote").inner_text())
            self.exercise_english_figures(page)
            self.assertEqual(errors, [])
        finally:
            page.close()

    def test_arabic_labs_and_figures(self):
        page, errors = self.open_page(PAGES[1])
        try:
            page.wait_for_function("typeof Hp2 === 'bigint'")
            page.click('button[onclick="stGenWallet()"]')
            page.click("#stpaybtn")
            page.click("#stagainbtn")
            page.click("#stscanbtn")
            self.assertEqual(page.evaluate("st.pays.length"), 2)
            self.assertIn("ده بتاعي", page.locator("#stout").inner_text())
            page.click("#gsignbtn")
            self.assertIn("التوقيع صحيح", page.locator("#gameout").inner_text())
            page.locator("#guessbtns button").first.click()
            spend_buttons = page.locator('#ringout').locator("xpath=preceding::div[contains(@class,'m-ctrl')][1]/button")
            spend_buttons.nth(0).click()
            self.assertIn("مقبولة", page.locator("#ringout").inner_text())
            spend_buttons.nth(2).click()
            self.assertIn("مرفوضة", page.locator("#ringout").inner_text())
            page.click('button[onclick="pedTamper()"]')
            self.assertIn("مش متوازن", page.locator("#pedout").inner_text())
            page.click('button[onclick="pedNegative()"]')
            self.assertIn("متوازن", page.locator("#pedout").inner_text())
            self.assertIn("مكانتش المثال ده", page.locator("#pedout").inner_text())
            page.locator("#v1sl").evaluate("el => { el.value = 70; el.dispatchEvent(new Event('input', {bubbles:true})); }")
            self.assertIn("70", page.locator("#v1v").inner_text())
            page.click('button[onclick="pedRender()"]')
            self.assertIn("تقسيم صح", page.locator("#pedout").inner_text())
            self.exercise_arabic_figures(page)
            self.assertEqual(page.locator("html").get_attribute("dir"), "rtl")
            self.assertEqual(errors, [])
        finally:
            page.close()

    def test_mobile_layout_and_model_labels(self):
        for name in PAGES:
            with self.subTest(page=name):
                page, errors = self.open_page(name, width=390)
                try:
                    dimensions = page.evaluate("({scroll: document.documentElement.scrollWidth, inner: innerWidth})")
                    self.assertLessEqual(dimensions["scroll"], dimensions["inner"] + 1)
                    self.assertTrue(page.locator('.machine .m-type, .machine .chip').evaluate_all("els => els.every(el => el.textContent.trim() === 'TOY')"))
                    self.assertIn("favicon.svg", page.locator('link[rel="icon"]').get_attribute("href"))
                    before = page.locator("html").get_attribute("data-theme")
                    page.click("#themego")
                    after = page.locator("html").get_attribute("data-theme")
                    self.assertNotEqual(before, after)
                    self.assertEqual(errors, [])
                finally:
                    page.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
