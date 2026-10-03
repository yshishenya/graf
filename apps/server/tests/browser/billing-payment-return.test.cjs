'use strict';
// Actual ASGI server/PostgreSQL; only named fault responses/environment are controlled.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {chromium, webkit} = require(path.join(process.env.GRAF_NODE_MODULES || path.join(__dirname, 'node_modules'), 'playwright'));
const engine = process.env.GRAF_BROWSER || 'chromium';
let stage = 'configuration';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function eventually(check, timeout = 6000) {
  const until = Date.now() + timeout;
  while (!(await check())) { if (Date.now() >= until) throw new Error('ConditionTimeout'); await sleep(20); }
}
(async () => {
  const config = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  assert.ok(['chromium', 'webkit'].includes(engine));
  const browser = await ({chromium, webkit})[engine].launch({headless: true});
  let documentRequests = 0, initialDocumentRequests = 0, refreshDocumentNavigations = 0;
  let refreshPosts = 0, externalRequests = 0, intentionalNavigations = 0;
  const scenarios = [], runtimeErrors = [];
  let fault = null, hold = null;
  try {
    const native = config.case === 'native';
    const clocked = !native && config.case !== 'timeout';
    const context = await browser.newContext({viewport: {width: config.width, height: 1000},
      timezoneId: 'UTC', javaScriptEnabled: !native, colorScheme: 'light'});
    // user-time.js legitimately replaces an initial page whose zone differs.
    // Pre-agree its actual server cookie and browser zone; never permit a second
    // document request from status-checks or reset a marker on every navigation.
    await context.addCookies([
      {name: config.cookie_name, value: config.session_token, url: config.base_url,
        httpOnly: true, sameSite: 'Lax', secure: false},
      {name: 'graf_timezone', value: 'UTC', url: config.base_url, sameSite: 'Lax'},
    ]);
    await context.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.origin !== config.base_url) { externalRequests++; await route.abort(); return; }
      if (request.isNavigationRequest() && request.resourceType() === 'document') documentRequests++;
      if (request.method() === 'POST') {
        assert.equal(url.pathname, config.status_path + '/refresh', 'no start/continue payment');
        refreshPosts++;
      }
      await route.continue();
    });
    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    page.on('pageerror', error => runtimeErrors.push(error.name));
    if (clocked) {
      await page.clock.install({time: new Date('2026-10-03T12:00:00Z')});
      await page.clock.pauseAt(new Date('2026-10-03T12:00:01Z'));
    }
    await page.addInitScript(() => {
      window.paymentEvents = {starts: [], finished: 0, swaps: 0};
      document.addEventListener('htmx:beforeRequest', event => {
        if (event.defaultPrevented || event.detail?.elt?.id !== 'billing-status-refresh') return;
        window.paymentEvents.starts.push(performance.now());
        event.detail.xhr.addEventListener('loadend', () => { window.paymentEvents.finished++; }, {once: true});
      });
      document.addEventListener('htmx:afterSwap', event => {
        if (event.detail?.xhr?.grafBillingStatus) window.paymentEvents.swaps++;
      });
    });
    // Playwright routes only the first URL of a redirect chain. For named faults
    // fetch the actual POST303 and its actual GET, then transform that HTML.
    // Happy-path navigation/redirects are never fulfilled by a fixture.
    await page.route('**/billing/checkout/status/**', async route => {
      const request = route.request(), url = new URL(request.url());
      if (request.method() !== 'POST' || request.resourceType() !== 'xhr' || url.pathname !== config.status_path + '/refresh'
          || (!fault && !hold)) { await route.fallback(); return; }
      refreshPosts++; // route.fetch bypasses the lower context route, count its real POST once.
      const response = await route.fetch({maxRedirects: 20});
      let body = await response.text(), status = response.status();
      if (hold) { const currentHold = hold; currentHold.seen(); await currentHold.gate; }
      if (fault === 'network') { await route.abort(); return; }
      if (/^http-/.test(fault || '')) status = Number(fault.slice(5));
      else if (fault === 'unexpected') body = '<!doctype html><html><head></head><body><main id="cabinet-main"><h1>Войти</h1></main></body></html>';
      else if (fault?.startsWith('incoming-')) {
        const field = fault.slice(9);
        body = field === 'invoice' ? body.replace(/(data-billing-invoice=")[^"]*(")/, '$1synthetic-other$2')
          : body.replace(new RegExp(`(name="${field}" content=")[^"]*(")`), '$1synthetic-other$2');
      }
      await route.fulfill({response, status, body});
    });
    const main = () => page.locator('main#cabinet-main.billing-operation-status-page');
    const reinit = () => page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap',
      {bubbles: true, detail: {target: document.querySelector('#cabinet-main')}})));
    let marker, navBaseline;
    async function open(name, query = '', options = {}) {
      stage = name; scenarios.push(name); fault = options.fault || null; hold = options.hold || null;
      const previous = documentRequests;
      await page.goto(config.base_url + config.status_path + query, {waitUntil: 'domcontentloaded'});
      assert.equal(documentRequests - previous, 1, 'timezone is agreed before initial GET');
      initialDocumentRequests++;
      assert.equal(await main().count(), 1, 'actual invoice status page');
      navBaseline = documentRequests;
      if (!native) {
        marker = crypto.randomUUID();
        await page.evaluate(value => { window.paymentDocument = document; window.paymentMarker = value; }, marker);
      }
    }
    async function stable() {
      const navigations = documentRequests - navBaseline;
      refreshDocumentNavigations += navigations;
      assert.equal(navigations, 0, 'status checks cannot navigate the document');
      assert.equal(await page.evaluate(value => window.paymentMarker === value && window.paymentDocument === document, marker), true,
        'runner-captured marker and document survive actual refresh');
    }
    async function waitFinished(count) {
      await eventually(() => page.evaluate(n => window.paymentEvents.finished >= n, count));
      if (clocked) await page.clock.runFor(30);
    }
    async function initialCheck() {
      if (clocked) await page.clock.runFor(1);
      await waitFinished(1);
    }
    async function noMore(previous) {
      if (clocked) await page.clock.runFor(65000);
      else await sleep(300);
      assert.equal(refreshPosts, previous, 'stopped auto sequence stays stopped');
    }
    async function paid() {
      await eventually(async () => (await page.getByRole('heading', {name: 'Оплачено', exact: true}).count()) === 1);
      assert.equal(await main().getByRole('link', {name: 'К встречам', exact: true}).count(), 1);
      assert.equal(await main().getByText(/Оплаченный срок:/).count(), 1, 'actual linked grant period is rendered');
      assert.equal(await page.getByRole('button', {name: /Продолжить оплату|Вернуться к оплате/}).count(), 0, 'paid never offers continuing payment');
    }
    async function fits() {
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'document fits viewport');
      assert.equal(await main().getAttribute('tabindex'), '-1', 'status main can receive focus after swap');
      await page.emulateMedia({colorScheme: 'dark'});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'document fits viewport');
      await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, '200% reflow');
      await page.evaluate(() => { document.documentElement.style.zoom = ''; });
      await page.emulateMedia({colorScheme: 'light'});
    }
    if (['success', 'historical', 'native'].includes(config.case)) {
      await open(config.case);
      if (native) {
        assert.equal(refreshPosts, 0, 'JS-off does not send automatic checks');
        const response = page.waitForResponse(r => r.request().method() === 'POST');
        await page.getByRole('button', {name: 'Проверить оплату', exact: true}).click();
        assert.equal((await response).status(), 303);
        await paid(); intentionalNavigations++;
      } else {
        if (config.case === 'success') await initialCheck();
        await paid(); await stable();
        await noMore(refreshPosts);
        await fits();
      }
      assert.equal(refreshPosts, native || config.case === 'success' ? 1 : 0);
    } else if (['canceled', 'refused', 'service-gap'].includes(config.case)) {
      await open(config.case);
      assert.equal(await main().getAttribute('data-billing-auto-check'), 'false');
      if (config.case === 'canceled') assert.equal(await page.getByRole('heading', {name: 'Платеж отменен', exact: true}).count(), 1);
      else {
        assert.equal(await page.getByRole('heading', {name: 'Оплата получена. Проверяем доступ', exact: true}).count(), 1);
        assert.equal(await main().getByRole('link', {name: 'К встречам', exact: true}).count(), 0);
        assert.equal(await main().getByText('Оплата прошла, оплаченный доступ предоставлен.', {exact: true}).count(), 0);
      }
      await noMore(0); await stable(); await fits();
    } else if (config.case === 'pending' || config.case === 'a11y') {
      await open(config.case);
      assert.equal(await page.getByRole('heading', {name: 'Проверяем оплату', exact: true}).count(), 1);
      await initialCheck();
      assert.equal(await main().locator('[role="status"]').first().getAttribute('aria-live'), 'off',
        'unchanged pending is actually suppressed in inserted server HTML');
      await stable();
      if (config.case === 'pending') {
        assert.equal(await main().getByRole('button', {name: 'Вернуться к оплате', exact: true}).count(), 1,
          'a confirmed unchanged pending payment offers secondary continuation');
        for (let count = 2; count <= 6; count++) {
          await reinit(); await reinit();
          await page.clock.runFor(10000);
          await waitFinished(count);
          assert.equal(refreshPosts, count, 'one refresh after each >=10s interval');
        }
        const starts = await page.evaluate(() => window.paymentEvents.starts);
        assert.equal(starts.length, 6);
        assert.ok(starts.every((value, i) => i === 0 || value - starts[i - 1] >= 10000));
        assert.ok(starts[5] - starts[0] < 60000);
        await noMore(6); await reinit(); await noMore(6);
        assert.equal(await page.getByRole('button', {name: 'Проверить оплату', exact: true}).isEnabled(), true);
        await page.getByRole('button', {name: 'Проверить оплату', exact: true}).click();
        await waitFinished(7); await noMore(7);
        await stable();
      } else {
        const button = page.getByRole('button', {name: 'Проверить оплату', exact: true});
        await button.focus();
        await page.clock.runFor(10000); await waitFinished(2);
        assert.equal(await page.evaluate(() => document.activeElement?.id), 'billing-status-check', 'focus survives refresh');
        await page.keyboard.press(engine === 'webkit' ? 'Alt+Tab' : 'Tab');
        assert.ok(await page.evaluate(() => document.activeElement !== document.body && document.activeElement?.id !== 'billing-status-check'), 'keyboard moves to next actionable element');
        await fits();
        await page.evaluate(() => { Object.defineProperty(document, 'hidden', {configurable: true, value: true}); document.dispatchEvent(new Event('visibilitychange')); });
        await noMore(2);
      }
    } else if (config.case === 'cancel-on-check' || config.case === 'provider-unavailable') {
      await open(config.case); await initialCheck(); await stable();
      if (config.case === 'cancel-on-check') {
        assert.equal(await page.getByRole('heading', {name: 'Платеж отменен', exact: true}).count(), 1);
        assert.equal(await main().locator('form[action$="/continue"]').count(), 0);
      } else {
        assert.notEqual(await main().locator('[role="status"]').first().getAttribute('aria-live'), 'off',
          'new provider error in same operation state must be announced');
        assert.equal(await main().getAttribute('data-billing-status-error'), 'true', 'provider failure stops refresh');
        assert.ok((await main().innerText()).includes('Действие сейчас недоступно'), 'real refresh result unavailable exposes recoverable error');
        assert.equal(await page.locator('[data-billing-status-recovery]').isVisible(), true);
      }
      await noMore(1);
    } else if (config.case === 'errors' || config.case === 'guards') {
      const variants = config.case === 'errors'
        ? ['http-401', 'http-403', 'http-429', 'http-500', 'network', 'unexpected']
        : ['incoming-graf-time-user', 'incoming-graf-workspace', 'incoming-graf-time-session', 'incoming-invoice',
          'current-graf-time-user', 'current-graf-workspace', 'current-graf-time-session', 'current-invoice', 'missing-session'];
      for (const variant of variants) {
        const previous = refreshPosts;
        await open(variant, '', {fault: variant});
        if (variant.startsWith('current-') || variant === 'missing-session') {
          await initialCheck();
          assert.equal(refreshPosts, previous + 1, 'one initial check before changing current scope');
          const field = variant === 'missing-session' ? 'graf-time-session' : variant.slice(8);
          await page.evaluate(name => {
            if (name === 'invoice') document.querySelector('#cabinet-main').dataset.billingInvoice = 'synthetic-other';
            else document.querySelector(`meta[name="${name}"]`).content = name === 'graf-time-session' ? '' : 'synthetic-other';
          }, field);
          await reinit();
          await noMore(refreshPosts); await stable();
          assert.equal(await page.locator('[data-billing-status-message]').getAttribute('role'), 'alert');
          continue;
        }
        await initialCheck();
        assert.equal(refreshPosts, previous + 1);
        assert.equal(await page.getByRole('heading', {name: 'Проверяем оплату', exact: true}).count(), 1, 'bad response never replaces trusted status');
        assert.equal(await page.getByRole('heading', {name: 'Войти', exact: true}).count(), 0);
        assert.equal(await page.locator('[data-billing-status-message]').isVisible(), true);
        assert.equal(await page.locator('[data-billing-status-message]').getAttribute('role'), 'alert');
        assert.equal(await page.getByRole('button', {name: 'Проверить оплату', exact: true}).isDisabled(), true);
        await noMore(previous + 1); await reinit(); await noMore(previous + 1); await stable();
      }
    } else if (config.case === 'lifecycle') {
      for (const variant of ['busy', 'hidden', 'detached', 'navigation']) {
        let seen, release;
        const arrived = new Promise(resolve => { seen = resolve; });
        const gate = new Promise(resolve => { release = resolve; });
        const previous = refreshPosts;
        await open(variant, '', {hold: {seen, gate}});
        await page.clock.runFor(1);
        await Promise.race([arrived, sleep(6000).then(() => { throw new Error('HeldResponseTimeout'); })]);
        assert.equal(await page.getByRole('button', {name: 'Проверить оплату', exact: true}).isDisabled(), true);
        if (variant === 'busy') {
          await page.evaluate(() => {
            const form = document.getElementById('billing-status-refresh');
            window.htmx.trigger(form, 'billing-status-check'); window.htmx.trigger(form, 'billing-status-check');
          });
          await reinit(); assert.equal(refreshPosts, previous + 1);
        } else if (variant === 'hidden') {
          await page.evaluate(() => { Object.defineProperty(document, 'hidden', {configurable: true, value: true}); document.dispatchEvent(new Event('visibilitychange')); });
          await page.evaluate(() => { Object.defineProperty(document, 'hidden', {configurable: true, value: false}); document.dispatchEvent(new Event('visibilitychange')); });
        } else if (variant === 'detached') {
          await main().evaluate(element => {
            const replacement = document.createRange().createContextualFragment(element.outerHTML).firstElementChild;
            replacement.dataset.syntheticReplacement = 'true'; element.replaceWith(replacement); window.htmx.process(replacement);
          });
          await reinit();
        } else {
          await page.goto(config.base_url + '/billing', {waitUntil: 'domcontentloaded'}); intentionalNavigations++;
        }
        release(); hold = null;
        if (variant !== 'navigation') await waitFinished(1);
        if (variant === 'busy') {
          await page.evaluate(() => window.dispatchEvent(new Event('pagehide')));
        }
        await noMore(previous + 1);
        if (variant === 'detached') assert.equal(await main().getAttribute('data-synthetic-replacement'), 'true');
        if (variant !== 'navigation') await stable();
        else assert.equal(await main().count(), 0);
      }
    } else if (config.case === 'timeout') {
      await open('timeout');
      await eventually(async () => await page.locator('[data-billing-status-message]').isVisible(), 22000);
      assert.equal(await page.locator('[data-billing-status-message]').getAttribute('role'), 'alert');
      assert.equal(await page.getByRole('button', {name: 'Проверить оплату', exact: true}).isDisabled(), true);
      await noMore(1); await stable();
      const previous = refreshPosts;
      await page.locator('[data-billing-status-recovery]').click(); intentionalNavigations++;
      await page.waitForLoadState('domcontentloaded');
      await sleep(500);
      assert.equal(await main().getAttribute('data-billing-auto-check'), 'false', 'local recovery does not start auto checks');
      assert.equal(await main().locator('form[method=post]').count(), 0, 'local recovery has no competing billing POST');
      assert.equal(refreshPosts, previous, 'timeout recovery reads local status without overlapping/restarted POST');
    }
    assert.equal(runtimeErrors.length, 0, 'no runtime JS exceptions');
    assert.equal(externalRequests, 0);
    await context.close();
    process.stdout.write(JSON.stringify({engine, case: config.case, width: config.width, scenarios,
      initial_document_requests: initialDocumentRequests, refresh_document_navigations: refreshDocumentNavigations,
      refresh_posts: refreshPosts, external_requests: externalRequests, intentional_navigations: intentionalNavigations}));
  } finally { await browser.close(); }
})().catch(error => {
  process.stderr.write(`billing-payment-return stage=${stage} error=${error.name} detail=${error.name === 'AssertionError' ? error.message.slice(0, 600).replaceAll('\n', ' ') : (error.code || error.message.split('\n')[0])} source=${error.stack?.split('\n').find(line => line.includes('billing-payment-return.test.cjs:'))?.trim() || 'unknown'}\n`);
  process.exitCode = 1;
});
