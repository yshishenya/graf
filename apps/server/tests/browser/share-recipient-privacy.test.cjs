const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, webkit } = require(require.resolve('playwright', { paths: [process.env.GRAF_NODE_MODULES || process.cwd()] }));

(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch({ headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(5000);
    const requests = [], errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const base = '/api/v1/cabinet/meetings/synthetic-meeting/summary-sharing';
    await page.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      requests.push({ origin: url.origin, method: request.method(), path: url.pathname, query: url.searchParams.get('query') });
      if (url.origin !== 'https://graf.test' || request.method() !== 'GET') return route.abort();
      if (url.pathname === '/share') return route.fulfill({ contentType: 'text/html', body:
        '<meta charset="utf-8"><meta name="graf-time-user" content="synthetic-owner"><meta name="graf-workspace" content="synthetic-workspace">' + fs.readFileSync(process.argv[2], 'utf8') });
      if (url.pathname === base + '/link') return route.fulfill({ json: { state: 'absent' } });
      if (url.pathname === base + '/auto-send') return route.fulfill({ json: { state: 'off', roster: [], rules: {} } });
      if (url.pathname === base + '/recipients') return route.fulfill({ json: { recipients: url.searchParams.get('query') === 'teammate' ? [
        { email: 'teammate@example.test', display_label: 'Synthetic Teammate', source: 'workspace' }
      ] : [] } });
      return route.abort();
    });
    await page.goto('https://graf.test/share');
    await page.evaluate(() => {
      window.contactCalls = [];
      const forbidden = () => { contactCalls.push('contacts_or_permission'); throw Error('Contacts access is forbidden'); };
      Object.defineProperty(navigator, 'contacts', { value: { select: forbidden } });
      Object.defineProperty(navigator, 'permissions', { value: { query: forbidden, request: forbidden } });
      window.webkit = { messageHandlers: new Proxy({}, { get: () => ({ postMessage: forbidden }) }) };
    });
    await page.addScriptTag({ path: path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/summary-sharing.js') });
    await page.getByRole('tab', { name: 'По почте' }).click();
    const input = page.getByRole('combobox', { name: 'Кому отправить' });
    await input.fill('teammate');
    await page.getByRole('option', { name: /Synthetic Teammate/ }).click();
    const selected = page.locator('[data-summary-share-recipients] li');
    assert.equal(await selected.count(), 1);
    assert.match(await selected.first().textContent(), /teammate@example.test/);
    const response = page.waitForResponse(r => new URL(r.url()).searchParams.get('query') === 'unknown@example.test');
    await input.fill('unknown@example.test');
    await response;
    await input.press('Enter');
    assert.equal(await selected.count(), 2);
    assert.match(await selected.nth(1).textContent(), /unknown@example.test/);
    assert.equal(await input.inputValue(), '');
    assert.deepEqual(await page.evaluate(() => contactCalls), []);
    assert.deepEqual(errors, []);
    assert.equal(requests.length, 5, JSON.stringify(requests));
    assert(requests.every(r => r.origin === 'https://graf.test' && r.method === 'GET' &&
      ['/share', base + '/link', base + '/auto-send', base + '/recipients'].includes(r.path)), JSON.stringify(requests));
    assert.deepEqual(requests.filter(r => r.path === base + '/recipients').map(r => r.query), ['teammate', 'unknown@example.test']);
    console.log('PASS: real share fragment and script; suggestion and typed email stay local; no Contacts, permission, bridge, provider, grant or delivery request');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
