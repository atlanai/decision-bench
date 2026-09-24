/** Run against a built viewer: npm run preview, then npm run test:site.
 * CHROME_PATH can select an installed Chrome; otherwise install Playwright Chromium.
 */
import assert from 'node:assert/strict';
import {mkdir, writeFile} from 'node:fs/promises';
import {chromium} from 'playwright';
import AxeBuilder from '@axe-core/playwright';

const base = process.env.SITE_URL || 'http://127.0.0.1:4173';
const output = new URL('../../tmp/site-audit/', import.meta.url);
await mkdir(output, {recursive: true});
const browser = await chromium.launch({headless: true, ...(process.env.CHROME_PATH ? {executablePath: process.env.CHROME_PATH} : {})});
const results = [];
let failures = 0;
const ready = async page => {
  await page.locator('#main h1').waitFor();
  await page.waitForFunction(() => !document.getElementById('boot'));
  await page.waitForFunction(() => ![...document.querySelectorAll('#main [role="status"]')].some(el => el.textContent.startsWith('Loading')));
};
try {
  for (const width of (process.argv.includes('--interactions-only') ? [] : [390, 1440])) for (const theme of ['light', 'dark']) {
    const context = await browser.newContext({viewport: {width, height: 900}, colorScheme: theme, reducedMotion: 'reduce'});
    const page = await context.newPage(), errors = [], requests = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => requests.push(r.url()));
    await page.goto(base); await ready(page);
    assert(!requests.some(url => /\/details\//.test(url)), 'Homepage must not fetch row details');
    const first = async path => page.locator(`a[href^="/${path}/"]`).first().getAttribute('href');
    const task = await first('task'), row = await first('row'), model = await first('model');
    const routes = ['/', '/tasks', task, row, '/models', model, '/compare', '/data', '/methodology', '/review'];
    for (const route of routes) {
      await page.goto(`${base}${route}`); await ready(page);
      const axe = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
      const result = {width, theme, route, overflow, errors: [...errors], violations: axe.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.map(n => ({target: n.target, summary: n.failureSummary}))}))};
      if (overflow || errors.length || result.violations.length) failures++;
      results.push(result);
      console.log(`${width} ${theme} ${route}: ${result.violations.length} accessibility violations, ${errors.length} errors, overflow=${overflow}`);
      if (route === '/') await page.screenshot({path: new URL(`after-${width}-${theme}.png`, output).pathname});
    }
    await context.close();
  }
  if (results.length) await writeFile(new URL('routes.json', output), JSON.stringify(results, null, 2));
  // Keyboard filtering, real lazy row content, and correct result disclosure semantics.
  const context = await browser.newContext({viewport: {width: 1440, height: 900}, reducedMotion: 'reduce'});
  const page = await context.newPage();
  await page.goto(base); await ready(page);
  await page.goto(`${base}/models`); await ready(page);
  assert.equal(await page.locator('main table tbody tr').count(), 12, 'Only models with published results should appear');
  assert.equal(await page.getByText(/not evaluated|not run yet/i).count(), 0);
  assert.equal(await page.getByRole('link', {name: /Claude Sonnet 5 Claude Code CLI|Claude Haiku 4\.5 Claude Code CLI/}).count(), 0);
  await page.goto(base); await ready(page);
  assert.equal(await page.getByText(/not yet evaluated|not evaluated|not run yet/i).count(), 0, 'Homepage should not advertise unpublished models');
  await page.keyboard.press('Tab');
  assert.equal(await page.locator(':focus').innerText(), 'Skip to content');
  await page.keyboard.press('Enter');
  assert.equal(await page.locator(':focus').getAttribute('id'), 'main');
  await page.getByRole('radio', {name: 'All inputs', exact: true}).focus();
  // Radix moves focus in the next task; hold the key through that transition.
  await page.keyboard.down('ArrowRight');
  await page.waitForURL(/modality=text/);
  await page.keyboard.up('ArrowRight');
  await page.locator('[role="radio"][value="text"][aria-checked="true"]').waitFor();
  await page.goto(base); await ready(page);
  const rowHref = await page.locator('a[href^="/row/"]').first().getAttribute('href');
  const detailResponse = page.waitForResponse(r => r.url().includes('/details/') && r.ok());
  await page.goto(`${base}${rowHref}`); await ready(page);
  const detail = await (await detailResponse).json();
  assert.equal(await page.locator('#main h1').innerText(), detail.case.title || detail.case.id);
  const disclosure = page.locator('main table button[aria-expanded]').first();
  await disclosure.focus(); await page.keyboard.press('Enter');
  assert.equal(await disclosure.getAttribute('aria-expanded'), 'true');
  await page.getByRole('heading', {name: 'Raw response', exact: true}).waitFor();
  await page.getByRole('button', {name: 'Exact input sent to the model (JSON)'}).click();
  const pres = await page.locator('pre').allTextContents();
  assert(pres.some(text => { try { return JSON.stringify(JSON.parse(text).state) === JSON.stringify(detail.case.state); } catch { return false; } }), 'Exact model input must survive lazy loading');
  await page.goto(`${base}/tasks`); await ready(page);
  await page.getByRole('searchbox').fill('icon');
  await page.waitForURL(/q=icon/);
  await page.waitForFunction(() => [...document.querySelectorAll('a[href^="/task/"]')].every(a => a.getAttribute('href').includes('DSN-1')));
  assert(await page.getByRole('link', {name: 'Name an icon', exact: true}).isVisible());
  const darkBefore = await page.locator('html').evaluate(el => el.classList.contains('dark'));
  await page.locator('button[aria-label="Toggle dark mode"]:visible').click();
  assert.notEqual(await page.locator('html').evaluate(el => el.classList.contains('dark')), darkBefore);
  await page.reload(); await ready(page);
  assert.notEqual(await page.locator('html').evaluate(el => el.classList.contains('dark')), darkBefore);
  // Client navigation keeps clean URLs; direct refresh and previously shared hash links still work.
  await page.goto(base); await ready(page);
  await page.getByRole('navigation', {name: 'Main navigation'}).getByRole('link', {name: /Tasks/}).click();
  assert.equal(new URL(page.url()).pathname, '/tasks');
  await page.goBack(); await ready(page); assert.equal(new URL(page.url()).pathname, '/');
  await page.goForward(); await ready(page); assert.equal(new URL(page.url()).pathname, '/tasks');
  await page.goto(`${base}/#/task/ENG-2`); await ready(page);
  assert.equal(new URL(page.url()).pathname, '/task/ENG-2');
  assert.equal(new URL(page.url()).hash, '');
  await page.reload(); await ready(page);
  assert(await page.getByRole('heading', {name: 'Label a code change', exact: true}).isVisible());
  await context.close();
  // A failed data request must show an actionable message, not a permanent splash.
  const failed = await browser.newContext(); const errorPage = await failed.newPage();
  await errorPage.route('**/viewer.json', route => route.fulfill({status: 503, body: 'Unavailable'}));
  await errorPage.goto(base);
  await errorPage.getByRole('heading', {name: 'Unable to load results'}).waitFor();
  await errorPage.getByRole('button', {name: 'Try again'}).waitFor();
  await errorPage.waitForFunction(() => !document.getElementById('boot'));
  await failed.close();
  const retryContext = await browser.newContext(); const retryPage = await retryContext.newPage();
  await retryPage.route('**/details/*.json', route => route.fulfill({status: 503, body: 'Unavailable'}));
  await retryPage.goto(`${base}${rowHref}`);
  await retryPage.getByRole('alert').filter({hasText: 'This record could not be loaded'}).waitFor();
  await retryPage.unroute('**/details/*.json');
  await retryPage.getByRole('button', {name: 'Try again'}).click();
  await retryPage.getByRole('heading', {name: 'The record', exact: true}).waitFor();
  await retryContext.close();
  const legacyContext = await browser.newContext(); const legacyPage = await legacyContext.newPage();
  await legacyPage.route('**/viewer.json', route => route.fulfill({status: 404, body: 'Not found'}));
  const fullData = legacyPage.waitForResponse(r => r.url().endsWith('/data.json') && r.ok());
  await legacyPage.goto(base); await ready(legacyPage); await fullData;
  await legacyContext.close();
  // No JavaScript: useful, visible text and working downloads must remain.
  const noJS = await browser.newContext({javaScriptEnabled: false}); const plain = await noJS.newPage();
  await plain.goto(base); assert(await plain.getByRole('heading', {name: 'Decision Bench', exact: true}).isVisible());
  assert.equal(await plain.locator('#boot').isVisible(), false);
  await noJS.close();

  assert.equal(failures, 0, 'Route checks failed; see tmp/site-audit/routes.json');
  console.log('Passed route matrix, keyboard, lazy data, error recovery, and JavaScript-disabled checks.');
} finally { await browser.close(); }
