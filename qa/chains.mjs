import assert from 'node:assert/strict';
import http from 'node:http';
import { mkdtemp, rm } from 'node:fs/promises';
import { createReadStream, existsSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';
import { tmpdir } from 'node:os';
import puppeteer from 'puppeteer';

const root = new URL('../', import.meta.url).pathname;
const types = new Map([['.html', 'text/html'], ['.css', 'text/css'], ['.js', 'application/javascript'], ['.woff2', 'font/woff2'], ['.svg', 'image/svg+xml'], ['.png', 'image/png']]);
const server = http.createServer((request, response) => {
  const requestPath = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname);
  if (requestPath === '/favicon.ico') {
    response.writeHead(204).end();
    return;
  }
  const relativePath = normalize(requestPath).replace(/^[/\\]+/, '');
  if (relativePath.startsWith('..')) {
    response.writeHead(403).end();
    return;
  }
  const filePath = join(root, relativePath || 'index.html');
  response.setHeader('Content-Type', types.get(extname(filePath)) || 'application/octet-stream');
  const stream = createReadStream(filePath);
  stream.on('error', () => response.writeHead(404).end());
  stream.pipe(response);
});

await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const address = server.address();
const base = `http://127.0.0.1:${address.port}`;
const profile = await mkdtemp(join(tmpdir(), 'cryptoinbrief-chains-'));
const macChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const chromePath = process.env.CHROME_PATH || (existsSync(macChrome) ? macChrome : undefined);
const launchOptions = {
  headless: true,
  userDataDir: profile
};
if (chromePath) launchOptions.executablePath = chromePath;
const browser = await puppeteer.launch(launchOptions);

const pages = [
  {
    path: 'proof-of-stake.html',
    labs: [
      ['#lab1', '#lab1-run', '#lab1-reset', '#lab1-console', /validator\s+stake\s+expected\s+actual/, '#lab1-copy'],
      ['#lab2', '#lab2-run', '#lab2-reset', '#lab2-console', /verdict:/, '#lab2-copy'],
      ['#lab3', '#lab3-run', '#lab3-reset', '#lab3-console', /PROOF OF STAKE/, '#lab3-copy']
    ]
  },
  {
    path: 'solana.html',
    labs: [
      ['#lab1', '#lab1run', '#lab1reset', '#lab1out', /verification ran|verified/, '#lab1copy'],
      ['#lab2', '#lab2run', '#lab2reset', '#lab2out', /confirmation at slot/, '#lab2copy'],
      ['#lab3', '#lab3run', '#lab3reset', '#lab3out', /speedup|parallel/, '#lab3copy']
    ]
  },
  {
    path: 'sui.html',
    labs: [
      ['#m-live', '#b-live-run', '#b-live-reset', '#m-live .out', /Toy object generated/, '#b-live-copy'],
      ['#m-fast', '#b-fast-run', '#b-fast-reset', '#m-fast .out', /Owned lane:/, '#b-fast-copy'],
      ['#m-counter', '#b-counter-run', '#b-counter-reset', '#m-counter .out', /Conceptual model:/, '#b-counter-copy'],
      ['#m-types', '#b-types-run', '#b-types-reset', '#m-types .out', /Type wall:/, '#b-types-copy']
    ]
  }
];

async function auditPage(spec, reducedMotion) {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });
  page.on('response', response => {
    if (response.status() >= 400) errors.push(`response: ${response.status()} ${response.url()}`);
  });
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: reducedMotion ? 'reduce' : 'no-preference' }]);
  await page.goto(`${base}/${spec.path}`, { waitUntil: 'networkidle0' });
  await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async text => { window.__copied = text; } } }));
  assert.equal(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches), reducedMotion);
  assert.equal(errors.length, 0, `${spec.path} emitted errors on load: ${errors.join(' | ')}`);

  if (spec.path === 'solana.html' && !reducedMotion) {
    await page.click('#lab2run');
    await page.waitForFunction(() => document.querySelector('#lab2')?.dataset.state === 'running');
    await page.click('#lab2stop');
    await page.waitForFunction(() => document.querySelector('#lab2')?.dataset.state === 'idle');
    assert.match(await page.$eval('#lab2out', element => element.textContent), /race stopped/);
    await page.click('#lab2reset');
  }

  if (spec.path === 'sui.html' && !reducedMotion) {
    await page.click('#b-fast-run');
    await page.waitForFunction(() => document.querySelector('#m-fast')?.dataset.state === 'running');
    await page.click('#b-fast-reset');
    await new Promise(resolve => setTimeout(resolve, 700));
    assert.equal(await page.$eval('#m-fast', element => element.dataset.state), 'idle');
    assert.equal(await page.$eval('#m-fast .out', element => element.textContent), '');
    assert.equal(await page.$eval('#b-fast-run', element => element.disabled), false);
  }

  for (const [rootSelector, runSelector, resetSelector, outputSelector, expected, copySelector] of spec.labs) {
    assert.equal(await page.$eval(runSelector, element => !element.disabled && element.getBoundingClientRect().width > 0), true);
    await page.click(runSelector);
    await page.waitForFunction(selector => document.querySelector(selector)?.dataset.state === 'done', { timeout: 15000 }, rootSelector);
    const output = await page.$eval(outputSelector, element => element.textContent);
    assert.match(output, expected, `${spec.path} ${rootSelector} output was incomplete`);
    assert.equal(await page.$eval(copySelector, element => element.disabled), false);
    await page.evaluate(() => { window.__copied = ''; });
    await page.click(copySelector);
    await page.waitForFunction(() => typeof window.__copied === 'string' && window.__copied.length > 0);
    assert.equal(errors.length, 0, `${spec.path} ${rootSelector} emitted errors: ${errors.join(' | ')}`);
    await page.click(resetSelector);
    assert.equal(await page.$eval(rootSelector, element => element.dataset.state), 'idle');
    assert.equal(await page.$eval(runSelector, element => element.disabled), false);
  }

  if (reducedMotion) {
    const bayAnimation = await page.$eval('.bay', element => getComputedStyle(element).animationName);
    assert.equal(bayAnimation, 'none', `${spec.path} animates its hero under reduced motion`);
  }
  await page.close();
  return `${spec.path}: ${spec.labs.length} labs passed with reduced-motion=${reducedMotion}`;
}

try {
  const results = [];
  for (const spec of pages) results.push(await auditPage(spec, false));
  for (const spec of pages) results.push(await auditPage(spec, true));
  process.stdout.write(`${results.join('\n')}\n`);
} finally {
  await browser.close();
  await new Promise(resolve => server.close(resolve));
  await rm(profile, { recursive: true, force: true });
}
