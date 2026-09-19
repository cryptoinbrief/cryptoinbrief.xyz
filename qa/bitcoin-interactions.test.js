const assert = require('assert');
const {spawn} = require('child_process');
const {createHash} = require('crypto');
const {existsSync} = require('fs');
const puppeteer = require('puppeteer');

const root = require('path').resolve(__dirname, '..');
const port = Number(process.env.BITCOIN_QA_PORT || 20000 + process.pid % 20000);
const base = process.env.BITCOIN_QA_BASE_URL || `http://127.0.0.1:${port}`;
const macChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const chrome = process.env.CHROME_PATH || (existsSync(macChrome) ? macChrome : undefined);
const files = ['bitcoin-from-zero.html', 'bitcoin-from-zero-ar.html', 'crypto-summary.html', 'crypto-summary-ar.html'];

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function doubleSha256(bytes) {
  return createHash('sha256').update(createHash('sha256').update(bytes).digest()).digest();
}

function expectedMerkleRoot(transactions) {
  const leaves = transactions.map(value => doubleSha256(Buffer.from(value)));
  const left = doubleSha256(Buffer.concat([leaves[0], leaves[1]]));
  const right = doubleSha256(Buffer.concat([leaves[2], leaves[3]]));
  return doubleSha256(Buffer.concat([left, right])).toString('hex');
}

async function waitForServer() {
  for (let i = 0; i < 50; i += 1) {
    try {
      const response = await fetch(`${base}/bitcoin-from-zero.html`);
      if (response.ok) return;
    } catch (error) {
      if (i === 49) throw error;
    }
    await sleep(100);
  }
  throw new Error(`Server did not start at ${base}`);
}

async function waitForText(page, selector, pattern, timeout = 30000) {
  await page.waitForFunction(
    (target, source, flags) => new RegExp(source, flags).test(document.querySelector(target)?.textContent || ''),
    {timeout},
    selector,
    pattern.source,
    pattern.flags
  );
}

async function semanticFigureState(page, index) {
  return page.evaluate(i => {
    const figure = document.querySelectorAll('figure')[i];
    const svg = figure.querySelector('svg');
    return {
      svgClass: svg.getAttribute('class') || '',
      steps: [...svg.querySelectorAll('[data-step]')].map(node => node.getAttribute('class') || ''),
      controls: [...figure.querySelectorAll('.figctl button,.figui button')].map(button => button.textContent),
      note: figure.querySelector('.fignote.on,.figcap.on')?.textContent || ''
    };
  }, index);
}

async function verifyFigures(page, file) {
  await sleep(1700);
  const figures = await page.$$eval('figure', nodes => nodes.map(node => node.querySelectorAll('.figctl button,.figui button').length));
  assert(figures.length > 0, `${file}: no figures`);
  for (let i = 0; i < figures.length; i += 1) {
    assert(figures[i] > 0, `${file}: figure ${i + 1} has no controls`);
    const noteResult = await page.evaluate(index => {
      const figure = document.querySelectorAll('figure')[index];
      const target = figure.querySelector('svg [data-note]');
      if (!target) return {available: false, visible: true};
      target.dispatchEvent(new PointerEvent('pointerenter', {pointerType: 'mouse'}));
      const note = figure.querySelector('.fignote.on,.figcap.on');
      target.dispatchEvent(new PointerEvent('pointerleave', {pointerType: 'mouse'}));
      return {available: true, visible: Boolean(note?.textContent.trim())};
    }, i);
    if (noteResult.available) assert(noteResult.visible, `${file}: figure ${i + 1} annotation is dead`);
    await page.evaluate(index => document.querySelectorAll('figure')[index].querySelectorAll('.figctl button,.figui button')[0].click(), i);
    await sleep(80);
    const initial = await semanticFigureState(page, i);
    const animating = await page.evaluate(index => {
      const svg = document.querySelectorAll('figure')[index].querySelector('svg');
      return [...svg.querySelectorAll('path,line,rect,circle,polyline,polygon,text')].some(node => node.style.transition || node.style.strokeDashoffset || node.style.opacity === '0');
    }, i);
    assert(animating, `${file}: figure ${i + 1} replay did not restart animation`);
    if (figures[i] > 1) {
      await page.evaluate(index => document.querySelectorAll('figure')[index].querySelectorAll('.figctl button,.figui button')[1].click(), i);
      await sleep(80);
      const changed = await semanticFigureState(page, i);
      assert.notDeepStrictEqual(changed, initial, `${file}: figure ${i + 1} secondary control is dead`);
    }
    await page.evaluate(index => document.querySelectorAll('figure')[index].querySelectorAll('.figctl button,.figui button')[0].click(), i);
    await sleep(80);
    const replayed = await semanticFigureState(page, i);
    assert.deepStrictEqual(replayed, initial, `${file}: figure ${i + 1} replay did not reset state`);
  }
}

async function verifyBitcoinLabs(page, arabic) {
  await waitForText(page, '#hout', /^[0-9a-f]{64}$/);
  const initialHash = await page.$eval('#hout', node => node.textContent);
  await page.$eval('#hin', node => {
    node.value += 'x';
    node.dispatchEvent(new Event('input', {bubbles: true}));
  });
  await page.waitForFunction(hash => document.querySelector('#hout').textContent !== hash, {}, initialHash);

  if (!arabic) {
    await page.click('#sigbtn');
    await waitForText(page, '#sigout', /Signature valid:/);
    const valid = await page.$$eval('#sigout .ok', nodes => nodes.map(node => node.textContent));
    assert.deepStrictEqual(valid, ['✓ yes', '✓ yes']);
    const body = await page.$eval('body', node => node.innerText);
    assert.match(body, /P-256/);
    assert.match(body, /secp256k1/);
  }

  await page.click('#genbtn');
  await waitForText(page, '#genout', /^000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f$/);

  await page.waitForFunction(() => /^[0-9a-f]{10}…$/.test(document.querySelector('#nroot .hv')?.textContent || ''));
  const transactions = await page.$$eval('#tx0,#tx1,#tx2,#tx3', nodes => nodes.map(node => node.value));
  assert.strictEqual(await page.$eval('#nroot .hv', node => node.textContent), `${expectedMerkleRoot(transactions).slice(0, 10)}…`);
  await page.evaluate(() => document.querySelector('[onclick="sealRoot()"]').click());
  await page.$eval('#tx1', node => {
    node.value += 'x';
    node.dispatchEvent(new Event('input', {bubbles: true}));
  });
  await waitForText(page, '#sealmsg', arabic ? /الجذر اتغيّر/ : /root changed/i);

  await page.select('#zsel', '1');
  await page.click('#minebtn');
  await waitForText(page, '#s-msg', arabic ? /لقيتها/ : /Found it/, 30000);
  assert(Number((await page.$eval('#s-att', node => node.textContent)).replaceAll(',', '')) > 0);

  await page.waitForFunction(ar => {
    const states = [...document.querySelectorAll('[id^="bs"]')];
    const broken = ar ? /مكسور/ : /broken/;
    return states.length === 3 && states.every(node => !broken.test(node.textContent));
  }, {timeout: 30000}, arabic);
  await page.$eval('#bd0', node => {
    node.value += 'x';
    node.dispatchEvent(new Event('input', {bubbles: true}));
  });
  await page.waitForFunction(ar => {
    const broken = ar ? /مكسور/ : /broken/;
    return [...document.querySelectorAll('[id^="bs"]')].every(node => broken.test(node.textContent));
  }, {}, arabic);
  for (let i = 0; i < 3; i += 1) {
    await page.click(`#bm${i}`);
    await page.waitForFunction(index => !document.querySelector(`#bm${index}`).disabled, {timeout: 30000}, i);
  }
  await page.waitForFunction(ar => {
    const broken = ar ? /مكسور/ : /broken/;
    return [...document.querySelectorAll('[id^="bs"]')].every(node => !broken.test(node.textContent));
  }, {}, arabic);

  if (!arabic) {
    const raceInitial = await page.$eval('#racebox', node => node.innerHTML);
    await page.evaluate(() => forkStep());
    assert.notStrictEqual(await page.$eval('#racebox', node => node.innerHTML), raceInitial);
    await page.evaluate(() => forkReset());
    assert.strictEqual(await page.$eval('#racebox', node => node.innerHTML), raceInitial);

    const oddsInitial = await page.$eval('#atkout', node => node.textContent);
    await page.$eval('#zsl', node => {
      node.value = '2';
      node.dispatchEvent(new Event('input', {bubbles: true}));
    });
    assert.notStrictEqual(await page.$eval('#atkout', node => node.textContent), oddsInitial);

    await page.evaluate(() => setFair());
    const fair = await page.$eval('#sandout', node => node.textContent);
    await page.evaluate(() => setSandwich());
    const sandwich = await page.$eval('#sandout', node => node.textContent);
    assert.notStrictEqual(sandwich, fair);
    assert.match(sandwich, /before fees/i);
  }
}

async function run() {
  let server;
  if (!process.env.BITCOIN_QA_BASE_URL) {
    server = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1'], {cwd: root, stdio: 'ignore'});
  }
  try {
    await waitForServer();
    const browser = await puppeteer.launch({...chrome && {executablePath: chrome}, headless: true});
    try {
      for (const file of files) {
        const page = await browser.newPage();
        await page.emulateMediaFeatures([{name: 'prefers-reduced-motion', value: 'no-preference'}]);
        const errors = [];
        page.on('pageerror', error => errors.push(`page: ${error.message}`));
        page.on('console', message => {
          if (message.type() === 'error') errors.push(`console: ${message.text()}`);
        });
        page.on('response', response => {
          if (response.url().startsWith(base) && response.status() >= 400) errors.push(`http ${response.status()}: ${response.url()}`);
        });
        await page.goto(`${base}/${file}`, {waitUntil: 'domcontentloaded'});
        const structure = await page.evaluate(() => {
          const ids = [...document.querySelectorAll('[id]')].map(node => node.id);
          const duplicates = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
          const emptyButtons = [...document.querySelectorAll('button')].filter(button => !button.textContent.trim() && !button.getAttribute('aria-label')).length;
          return {duplicates, emptyButtons};
        });
        assert.deepStrictEqual(structure.duplicates, [], `${file}: duplicate IDs`);
        assert.strictEqual(structure.emptyButtons, 0, `${file}: unlabeled buttons`);
        const initialTheme = await page.$eval('html', node => node.getAttribute('data-theme'));
        await page.click('#themego');
        assert.notStrictEqual(await page.$eval('html', node => node.getAttribute('data-theme')), initialTheme, `${file}: theme control is dead`);
        if (file === 'bitcoin-from-zero.html') await verifyBitcoinLabs(page, false);
        if (file === 'bitcoin-from-zero-ar.html') await verifyBitcoinLabs(page, true);
        await verifyFigures(page, file);
        const text = await page.$eval('body', node => node.innerText);
        assert(!/[–—]/.test(text), `${file}: prose contains a dash character`);
        assert.deepStrictEqual(errors, [], `${file}: runtime errors`);
        await page.close();
        process.stdout.write(`PASS ${file}\n`);
      }
    } finally {
      await browser.close();
    }
  } finally {
    if (server) server.kill('SIGTERM');
  }
}

run().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
