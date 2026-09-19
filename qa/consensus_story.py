from pathlib import Path
import sys

from playwright.sync_api import sync_playwright


BASE_URL = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://127.0.0.1:8934'


def browser_options():
    candidates = [
        Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
        Path('/usr/bin/google-chrome'),
        Path('/usr/bin/chromium'),
    ]
    executable = next((str(path) for path in candidates if path.exists()), None)
    return {'headless': True, **({'executable_path': executable} if executable else {})}


def state(page):
    return page.locator('.cstory').get_attribute('data-stage')


def pause(page):
    button = page.locator('.cstory-pause')
    if button.inner_text() == 'Pause':
        button.click()


def test_bitcoin(page):
    page.goto(f'{BASE_URL}/bitcoin-from-zero.html', wait_until='networkidle')
    story = page.locator('.cstory')
    assert story.count() == 1
    assert story.get_attribute('data-kind') == 'bitcoin'
    assert story.locator('img.cstory-logo[src="assets/coins/bitcoin.svg"]').count() == 1
    page.locator('.cstory').scroll_into_view_if_needed()
    page.wait_for_function("document.querySelector('.cstory').dataset.stage !== '0'", timeout=5500)
    assert state(page) == '1'
    changed_hash = page.locator('.cstory-hash0').inner_text()
    old_pointer = page.locator('.cstory-prev1').inner_text()
    assert changed_hash != old_pointer
    assert page.locator('.cstory-verdict-title').inner_text() == 'Block 2 points to the old hash'
    page.locator('.cstory-rebuild').click()
    assert state(page) == '3'
    assert page.locator('.cstory-hash0').inner_text() == page.locator('.cstory-prev1').inner_text()
    assert 'proof of work' in page.locator('.cstory-verdict-copy').inner_text().lower()
    page.locator('.cstory-replay').click()
    pause(page)
    assert state(page) == '0'


def test_pos(page):
    page.goto(f'{BASE_URL}/proof-of-stake.html', wait_until='networkidle')
    story = page.locator('.cstory')
    assert story.count() == 1
    assert story.get_attribute('data-kind') == 'pos'
    assert story.locator('img.cstory-logo[src="assets/coins/ethereum.svg"]').count() == 2
    page.locator('.cstory').scroll_into_view_if_needed()
    page.wait_for_function("document.querySelector('.cstory').dataset.stage !== '0'", timeout=5500)
    assert state(page) == '1'
    pause(page)
    assert page.locator('.cstory-blockstatus').text_content() == 'included'
    assert page.locator('.cstory-finality').inner_text() == 'Not justified'
    page.locator('.cstory-next').click()
    assert state(page) == '2'
    assert page.locator('.cstory-blockstatus').text_content() == 'included'
    assert page.locator('.cstory-finality').inner_text() == 'C1 justified'
    assert page.locator('.cstory-nextfinality').inner_text() == 'C2 waiting'
    assert 'does not finalize c1 yet' in page.locator('.cstory-captioncopy').inner_text().lower()
    page.locator('.cstory-next').click()
    assert state(page) == '3'
    assert page.locator('.cstory-blockstatus').text_content() == 'included'
    assert page.locator('.cstory-finality').inner_text() == 'C1 finalized'
    assert page.locator('.cstory-nextfinality').inner_text() == 'C2 justified'
    assert page.locator('.cstory-linklabel').inner_text() == '80% link'
    page.locator('.cstory-offline').click()
    assert state(page) == '3'
    assert page.locator('.cstory-gaugevalue').inner_text() == '60%'
    assert page.locator('.cstory-blockstatus').text_content() == 'included'
    assert page.locator('.cstory-finality').inner_text() == 'C1 stays justified'
    assert page.locator('.cstory-nextfinality').inner_text() == 'C2 not justified'
    assert 'not finalized' in page.locator('.cstory-captioncopy').inner_text().lower()
    page.locator('.cstory-restore').click()
    assert state(page) == '3'
    assert page.locator('.cstory-gaugevalue').inner_text() == '80%'
    assert page.locator('.cstory-finality').inner_text() == 'C1 finalized'


def test_reduced_motion_autoplay(browser):
    context = browser.new_context(viewport={'width': 760, 'height': 800}, reduced_motion='reduce')
    page = context.new_page()
    page.goto(f'{BASE_URL}/bitcoin-from-zero.html', wait_until='networkidle')
    page.locator('.cstory').scroll_into_view_if_needed()
    assert page.locator('.cstory-caption').get_attribute('aria-live') == 'off'
    assert page.locator('.cstory-block').first.evaluate("node => getComputedStyle(node).transitionDuration") == '0s'
    page.wait_for_function("document.querySelector('.cstory').dataset.stage !== '0'", timeout=5500)
    assert state(page) == '1'
    assert page.locator('.cstory-caption').get_attribute('aria-live') == 'off'
    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    page.wait_for_timeout(400)
    offscreen_state = state(page)
    assert page.locator('.cstory').get_attribute('data-pause-reason') == 'offscreen'
    page.wait_for_timeout(4200)
    assert state(page) == offscreen_state
    page.locator('.cstory').scroll_into_view_if_needed()
    page.wait_for_function(f"document.querySelector('.cstory').dataset.stage !== '{offscreen_state}'", timeout=5500)
    page.locator('.cstory-pause').click()
    assert page.locator('.cstory-caption').get_attribute('aria-live') == 'polite'
    manual_state = state(page)
    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    page.wait_for_timeout(400)
    page.locator('.cstory').scroll_into_view_if_needed()
    page.wait_for_timeout(4200)
    assert state(page) == manual_state
    assert page.locator('.cstory').get_attribute('data-pause-reason') == 'manual'
    context.close()


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_options())
        context = browser.new_context(viewport={'width': 1440, 'height': 913}, reduced_motion='no-preference')
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        test_bitcoin(page)
        test_pos(page)
        assert not errors, errors
        context.close()
        test_reduced_motion_autoplay(browser)
        browser.close()
    print('consensus stories: causal states, checkpoint finality, autoplay lifecycle, reduced motion, and controls passed')


if __name__ == '__main__':
    main()
