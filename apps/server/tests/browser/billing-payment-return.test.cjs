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
      window.paymentEvents = {starts: [], finished: 0, swaps: 0, timeouts: 0, triggerPhases: [], processPhases: [], settlePhases: []};
      document.addEventListener('billing-status-check', event => {
        const form = event.target;
        if (form?.id === 'billing-status-refresh') window.paymentEvents.triggerPhases.push({
          time: performance.now(), processed: form['htmx-internal-data']?.initHash !== undefined});
      });
      document.addEventListener('htmx:afterProcessNode', event => {
        if (event.detail?.elt?.id === 'billing-status-refresh') window.paymentEvents.processPhases.push(performance.now());
      });
      document.addEventListener('htmx:afterSettle', event => {
        if (event.detail?.xhr?.grafBillingStatus) window.paymentEvents.settlePhases.push(performance.now());
      });
      document.addEventListener('htmx:beforeRequest', event => {
        if (event.defaultPrevented || event.detail?.elt?.id !== 'billing-status-refresh') return;
        window.paymentEvents.starts.push(performance.now());
        event.detail.xhr.addEventListener('timeout', () => { window.paymentEvents.timeouts++; }, {once: true});
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
    } else if (config.case === 'manual-cooldown') {
      await open(config.case); await initialCheck(); await stable();
      const button = () => page.getByRole('button', {name: 'Проверить оплату', exact: true});
      const cooldown = () => page.locator('[data-billing-status-message]');
      const unavailable = async () => await button().isDisabled() || await button().getAttribute('aria-disabled') === 'true';
      assert.equal(await unavailable(), true, 'fast pending reply exposes manual check as unavailable during10s cooldown');
      assert.equal(await cooldown().isVisible(), true, 'cooldown explains why manual check is unavailable');
      assert.match(await cooldown().innerText(), /через|секунд/i, 'cooldown provides understandable time feedback');
      const readinessStyle = () => button().evaluate(element => {
        const style = getComputedStyle(element);
        return {opacity: Number(style.opacity), cursor: style.cursor,
          described: element.getAttribute('aria-describedby')?.split(/\s+/).map(id => {
            const message = document.getElementById(id);
            return {visible: message && !message.hidden, text: message?.textContent};
          }) || []};
      });
      const waitingStyle = await readinessStyle();
      assert.ok(waitingStyle.opacity < 1, 'unavailable check is actually visually muted by loaded CSS');
      assert.equal(waitingStyle.cursor, 'not-allowed', 'loaded CSS visibly marks waiting action as unavailable');
      assert.ok(waitingStyle.described.some(item => item.visible && /через|секунд/i.test(item.text)),
        'aria-describedby references visible understandable cooldown feedback');
      if (await button().evaluate(element => !element.disabled)) {
        // aria-disabled remains focusable; force bypasses Playwright's ARIA
        // actionability gate to verify the application's actual click guard.
        await button().click({force: true});
        assert.equal(refreshPosts, 1, 'an aria-disabled click cannot send an early request');
        assert.equal(await cooldown().isVisible(), true, 'blocked action retains visible feedback');
      }
      const first = await page.evaluate(() => window.paymentEvents.starts[0]);
      for (let count = 2; count <= 6; count++) {
        const now = await page.evaluate(() => performance.now());
        await page.clock.runFor(first + (count - 1) * 10000 - 100 - now);
        assert.equal(await unavailable(), true, 'manual check remains unavailable before allowed interval');
        assert.equal(refreshPosts, count - 1, 'cooldown cannot start an early refresh');
        await page.clock.runFor(100); await waitFinished(count);
        assert.equal(refreshPosts, count, 'automatic check starts at its allowed interval');
        assert.equal(await unavailable(), true, 'each fast pending reply retains honest manual cooldown');
        assert.equal(await cooldown().isVisible(), true);
        if (count < 6) {
          assert.match(await cooldown().innerText(), /через|секунд/i);
        } else {
          assert.equal(await cooldown().innerText(),
            'Подтверждение пока не получено. Проверьте оплату позже. Повторно платить не нужно.',
            'six-check stop immediately explains ending during remaining manual cooldown');
          const separateCooldown = page.locator('[data-billing-status-cooldown]');
          assert.equal(await separateCooldown.isVisible(), true,
            'six-check stop retains a separate explanation of unavailable manual action');
          assert.match(await separateCooldown.innerText(), /через|секунд/i);
          const stoppedStyle = await readinessStyle();
          assert.ok(stoppedStyle.described.some(item => item.visible && /через|секунд/i.test(item.text)),
            'unavailable manual action still describes the separate remaining cooldown');
        }
      }
      const sixth = await page.evaluate(() => window.paymentEvents.starts[5]);
      const now = await page.evaluate(() => performance.now());
      await page.clock.runFor(sixth + 10000 - 100 - now);
      assert.equal(await unavailable(), true, 'six-check stop retains last request cooldown');
      await page.clock.runFor(100);
      assert.equal(refreshPosts, 6, 'automatic window never starts a seventh check');
      assert.equal(await button().isEnabled(), true, 'manual check becomes usable after allowed interval');
      assert.notEqual(await button().getAttribute('aria-disabled'), 'true', 'manual action is accessible after cooldown');
      const readyStyle = await readinessStyle();
      assert.equal(readyStyle.opacity, 1, 'ready check returns to actual active appearance');
      assert.notEqual(readyStyle.cursor, 'not-allowed', 'ready control no longer displays unavailable cursor');
      assert.equal(await button().getAttribute('aria-describedby'), null, 'obsolete cooldown explanation is removed');
      assert.match(await cooldown().innerText(), /Подтверждение пока не получено/);
      await button().click(); await waitFinished(7);
      assert.equal(refreshPosts, 7, 'enabled manual button actually sends a protected refresh');
      await noMore(7); await stable();
    } else if (config.case === 'focus-controls' || config.case === 'focus-latest' || config.case === 'focus-success') {
      await open(config.case); await initialCheck(); await stable();
      const details = () => main().locator('details.billing-coupon');
      await details().locator('summary').click();
      assert.equal(await details().getAttribute('open'), '');
      const receipt = () => main().getByRole('link', {name: 'Платеж и чек', exact: true});
      const summary = () => details().locator('summary');
      const plan = () => main().getByRole('link', {name: 'К тарифу и оплате', exact: true});
      const help = () => main().getByRole('link', {name: 'Помощь с оплатой', exact: true});
      const continuation = () => main().getByRole('button', {name: 'Вернуться к оплате', exact: true});
      const focused = locator => locator.evaluate(element => document.activeElement === element);
      const delayed = () => {
        let release; const gate = new Promise(resolve => { release = resolve; });
        const value = {arrived: false, gate, release, seen() { this.arrived = true; }};
        return value;
      };
      const nextHeld = async (count, control) => {
        hold = delayed(); await control().focus();
        const last = await page.evaluate(() => window.paymentEvents.starts.at(-1));
        const now = await page.evaluate(() => performance.now());
        await page.clock.runFor(Math.max(0, last + 10000 - now));
        await eventually(() => hold.arrived);
        assert.equal(refreshPosts, count, 'held request reached actual ASGI response');
        return hold;
      };
      if (config.case === 'focus-controls') {
        for (const [index, control] of [summary, receipt, plan, help, continuation].entries()) {
          const reply = await nextHeld(index + 2, control);
          // Buttons are disabled in flight; browsers may move activeElement on
          // disable. Other actionable elements must stay focused until swap.
          if (control !== continuation) assert.equal(await focused(control()), true);
          reply.release(); hold = null; await waitFinished(index + 2);
          assert.equal(await focused(control()), true, 'same actionable control regains focus after actual automatic swap');
          assert.equal(await details().getAttribute('open'), '', 'expanded payment details survive each status swap');
          const id = await control().getAttribute('id');
          assert.ok(id, 'each actionable payment control has a stable identifier');
          assert.equal(await page.locator(`[id="${id}"]`).count(), 1, 'focus identifier is unique in the actual document');
          await stable();
        }
        await noMore(6); await fits();
      } else if (config.case === 'focus-success') {
        const reply = await nextHeld(2, continuation);
        reply.release(); hold = null; await waitFinished(2); await paid();
        assert.equal(await page.evaluate(() => {
          const active = document.activeElement;
          const result = document.querySelector('main#cabinet-main.billing-operation-status-page');
          return active === result || active === result?.querySelector('[data-billing-primary]');
        }), true, 'disappearing continuation control moves focus to the confirmed result');
        assert.equal(await details().getAttribute('open'), '', 'expanded details survive success transition');
        await noMore(2); await stable(); await fits();
      } else {
        let reply = await nextHeld(2, continuation);
        assert.equal(await continuation().evaluate(element => element.disabled), true,
          'initially focused continuation is natively disabled during real held request');
        const disabledFocus = await page.evaluate(() => document.activeElement === document.body
          ? 'body' : document.activeElement?.id);
        assert.ok(['body', 'billing-status-continue'].includes(disabledFocus),
          'actual native disabling path is observed before user moves: ' + disabledFocus);
        await receipt().focus();
        assert.equal(await focused(receipt()), true, 'user moved focus while request remained in flight');
        reply.release(); hold = null; await waitFinished(2);
        assert.equal(await focused(receipt()), true, 'current focus immediately before swap wins over request-start focus');
        assert.equal(await details().getAttribute('open'), '');
        reply = await nextHeld(3, summary);
        // The real shell's skip link remains keyboard-accessible in desktop
        // and mobile; collapsed sidebar controls can be hidden at either width.
        const outside = page.getByRole('link', {name: 'К содержимому', exact: true});
        assert.equal(await outside.count(), 1, 'real shell navigation outside payment main is available');
        assert.equal(await outside.evaluate(element => !document.querySelector('#cabinet-main').contains(element)), true);
        await outside.focus();
        assert.equal(await outside.isVisible(), true, 'keyboard focus reveals the actual shell skip link');
        assert.equal(await focused(outside), true);
        reply.release(); hold = null; await waitFinished(3);
        assert.equal(await focused(outside), true, 'payment refresh does not steal focus moved outside its main');
        assert.equal(await details().getAttribute('open'), '');
        await stable(); await fits();
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
    } else if (config.case.startsWith('current-context-in-flight-')) {
      const field = config.case.slice('current-context-in-flight-'.length);
      const contextVariant = ({user: 'graf-time-user', workspace: 'graf-workspace',
        session: 'graf-time-session', invoice: 'invoice', replacement: 'replacement'})[field];
      assert.ok(contextVariant, 'known current context field');
      for (const variant of [contextVariant]) {
        let release; const gate = new Promise(resolve => { release = resolve; });
        const reply = {arrived: false, gate, seen() { this.arrived = true; }};
        const previous = refreshPosts;
        await open(`current-in-flight-${variant}`, '', {hold: reply});
        await page.clock.runFor(1); await eventually(() => reply.arrived);
        assert.equal(refreshPosts, previous + 1, 'held response came from actual protected POST303+GET');
        assert.equal(await main().getAttribute('aria-busy'), 'true');
        if (variant === 'replacement') {
          // A genuine second ASGI render replaces main. Only delivery of the
          // old request is held; no fake control or response HTML is injected.
          await page.evaluate(async statusPath => {
            const response = await fetch(statusPath + '?view=local');
            if (!response.ok) throw new Error('LocalRenderFailed');
            const html = new DOMParser().parseFromString(await response.text(), 'text/html');
            const incoming = html.querySelector('main#cabinet-main');
            if (!incoming) throw new Error('LocalRenderMissingMain');
            document.querySelector('#cabinet-main').replaceWith(document.importNode(incoming, true));
            window.paymentReplacement = document.querySelector('#cabinet-main');
            window.paymentReplacementHTML = window.paymentReplacement.outerHTML;
          }, config.status_path);
        } else {
          await page.evaluate(field => {
            const current = document.querySelector('#cabinet-main');
            window.paymentOriginalMain = current;
            if (field === 'invoice') current.dataset.billingInvoice = 'synthetic-other';
            else document.querySelector(`meta[name="${field}"]`).content = 'synthetic-other';
          }, variant);
        }
        release(); hold = null; await waitFinished(1);
        assert.equal(await page.evaluate(() => window.paymentEvents.swaps), 0,
          'changed context rejects old response without replacing payment main');
        if (variant === 'replacement') {
          assert.equal(await page.evaluate(() => document.querySelector('#cabinet-main') === window.paymentReplacement
            && window.paymentReplacement.outerHTML === window.paymentReplacementHTML), true,
          'late old request cannot alter a genuinely replacement page or its recovery controls');
          await noMore(previous + 1); await stable();
          continue;
        }
        assert.equal(await page.evaluate(() => document.querySelector('#cabinet-main') === window.paymentOriginalMain), true);
        const message = page.locator('[data-billing-status-message]');
        assert.equal(await message.isVisible(), true, 'same main context change exposes recovery immediately without reinit');
        assert.equal(await message.getAttribute('role'), 'alert');
        assert.match(await message.innerText(), /Сеанс|доступ|заново/);
        assert.equal(await main().locator('form button:enabled').count(), 0, 'old payment forms remain disabled');
        const recovery = page.locator('[data-billing-status-recovery]');
        assert.equal(await recovery.isVisible(), true, 'safe local GET recovery is immediately available');
        assert.equal(new URL(await recovery.getAttribute('href'), config.base_url).searchParams.get('view'), 'local');
        await noMore(previous + 1); await stable();
        await recovery.click(); intentionalNavigations++;
        await page.waitForLoadState('domcontentloaded');
        assert.equal(await main().getAttribute('data-billing-auto-check'), 'false');
        assert.equal(await main().locator('form[method=post]').count(), 0, 'recovery cannot send a financial POST');
        await noMore(previous + 1);
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
    } else if (['idle-five', 'six-final-cooldown'].includes(config.case)) {
      const sixFinal = config.case === 'six-final-cooldown';
      function delayedReply() {
        let release;
        const gate = new Promise(resolve => { release = resolve; });
        const reply = {gate, release, arrived: false};
        reply.seen = () => { reply.arrived = true; };
        return reply;
      }
      let pendingReply = delayedReply();
      await open(config.case, '', {hold: pendingReply});
      await page.clock.runFor(1);
      await eventually(() => pendingReply.arrived);
      const firstStart = await page.evaluate(() => window.paymentEvents.starts[0]);
      const finishes = sixFinal ? [12000, 22000, 32000, 42000, 52000, 53000] : [14000, 28000, 42000, 50000, 53000];
      const autoCount = finishes.length;
      for (let index = 0; index < finishes.length; index++) {
        stage = `${config.case}-reply-${index + 1}`;
        await eventually(() => pendingReply.arrived); // Actual POST303 -> ASGI GET HTML has completed.
        const now = await page.evaluate(() => performance.now());
        await page.clock.runFor(Math.max(0, firstStart + finishes[index] - now));
        const nextReply = index < autoCount - 1 ? delayedReply() : null;
        hold = nextReply;
        pendingReply.release();
        await waitFinished(index + 1);
        const observed = await page.evaluate(() => {
          const current = document.querySelector('main#cabinet-main.billing-operation-status-page');
          const message = current?.querySelector('[data-billing-status-message]');
          return {events: window.paymentEvents, busy: current?.getAttribute('aria-busy'),
            auto: current?.dataset.billingAutoCheck, error: current?.dataset.billingStatusError,
            visibleMessage: message && !message.hidden ? message.textContent : null};
        });
        assert.equal(observed.events.swaps, index + 1, 'actual reply swaps before next phase: ' + JSON.stringify(observed));
        assert.equal(await main().getAttribute('data-billing-auto-check'), 'true', 'actual pending response permits checks');
        assert.equal(await main().getAttribute('data-billing-status-error'), 'false', 'pending is not a server error');
        pendingReply = nextReply;
        if (sixFinal ? index < 4 : index < 3) {
          await page.clock.runFor(50);
          await sleep(100);
          const phase = await page.evaluate(() => {
            const current = document.querySelector('main#cabinet-main.billing-operation-status-page');
            const message = current?.querySelector('[data-billing-status-message]');
            return {events: window.paymentEvents, now: performance.now(), hidden: document.hidden,
              busy: current?.getAttribute('aria-busy'), auto: current?.dataset.billingAutoCheck,
              error: current?.dataset.billingStatusError, form: current?.querySelector('#billing-status-refresh')?.id,
              visibleMessage: message && !message.hidden ? message.textContent : null};
          });
          assert.equal(phase.events.starts.length, index + 2, 'next due check phase: ' + JSON.stringify(phase));
        }
        if (sixFinal ? index === 4 : index === 3) {
          const clockNow = await page.evaluate(() => performance.now());
          const lastStart = await page.evaluate(i => window.paymentEvents.starts[i] + 10000, index);
          await page.clock.runFor(Math.max(0, lastStart + 1 - clockNow));
        }
      }
      stage = `${config.case}-deadline`;
      const starts = await page.evaluate(() => window.paymentEvents.starts);
      assert.equal(starts.length, autoCount, 'exactly the scheduled actual checks finish before60s');
      (sixFinal ? [0, 12000, 22000, 32000, 42000, 52000] : [0, 14000, 28000, 42000, 52000]).forEach((target, index) => {
        assert.ok(Math.abs(starts[index] - firstStart - target) < 100,
          'starts follow the actual response-dependent schedule for ' + config.case);
      });
      assert.equal(await main().getAttribute('aria-busy'), null, 'last automatic check finishes around53s, then idle');
      const endingText = 'Подтверждение пока не получено. Проверьте оплату позже. Повторно платить не нужно.';
      if (sixFinal) {
        stage = 'six-final-cooldown-immediate53';
        assert.equal(await page.locator('[data-billing-status-message]').isVisible(), true,
          'sixth pending reply immediately explains end at53s despite remaining manual cooldown');
        assert.equal(await page.locator('[data-billing-status-message]').innerText(), endingText,
          'sixth pending reply retains honest ending instead of replacing it with cooldown');
        assert.equal(await page.locator('[data-billing-status-cooldown]').isVisible(), true,
          'remaining manual cooldown is explained separately from the ending');
        const earlyManual = page.getByRole('button', {name: 'Проверить оплату', exact: true});
        assert.equal(await earlyManual.isEnabled(), false, 'manual check is unavailable immediately after sixth reply');
        await earlyManual.focus(); await page.keyboard.press('Enter');
        assert.equal(refreshPosts, autoCount, 'early manual submit at53s starts no seventh POST');
      }
      const beforeDeadline = await page.evaluate(() => performance.now());
      await page.clock.runFor(Math.max(0, firstStart + 60000 - beforeDeadline));
      assert.equal(refreshPosts, autoCount, 'no further automatic POST starts after60s');
      assert.equal(await page.evaluate(() => window.paymentEvents.finished), autoCount);
      assert.equal(await main().getAttribute('aria-busy'), null, 'deadline does not fabricate an in-flight request');
      assert.equal(await page.locator('[data-billing-status-message]').isVisible(), true,
        'idle deadline reveals honest pending message without reinit');
      assert.equal(await page.locator('[data-billing-status-message]').innerText(),
        endingText);
      // The last automatic start was52s: automatic observation ends60s, while the
      // manual10s interval ends62s. Old enabled-at60s hid a silently ignored
      // submit; prove both honest ending copy and actual manual readiness.
      const manual = page.getByRole('button', {name: 'Проверить оплату', exact: true});
      assert.equal(await manual.isEnabled(), false, 'manual check remains unavailable until52s+10s');
      const cooldown = page.locator('[data-billing-status-cooldown]');
      assert.equal(await cooldown.isVisible(), true, 'ending and remaining manual cooldown are both explained');
      assert.match(await cooldown.innerText(), /через|секунд/i);
      await manual.focus(); await page.keyboard.press('Enter');
      assert.equal(refreshPosts, autoCount, 'keyboard submit during remaining cooldown starts no early request');
      const beforeReady = await page.evaluate(() => performance.now());
      await page.clock.runFor(Math.max(0, starts[autoCount - 1] + 10000 - beforeReady));
      assert.equal(await manual.isEnabled(), true, 'manual check becomes ready at62s without reinitialization');
      assert.equal(await cooldown.isVisible(), false);
      assert.equal(await main().getByRole('button', {name: 'Вернуться к оплате', exact: true}).isEnabled(), true);
      assert.equal(refreshPosts, autoCount, 'manual availability timer sends no automatic POST');
      await manual.click(); await waitFinished(autoCount + 1);
      const manualStart = await page.evaluate(i => window.paymentEvents.starts[i], autoCount);
      assert.ok(manualStart - starts[autoCount - 1] >= 10000, 'real manual POST respects previous start interval');
      await stable(); await noMore(autoCount + 1); await reinit(); await noMore(autoCount + 1); await stable();
    } else if (config.case.startsWith('deadline-')) {
      await open(config.case); await initialCheck();
      for (let count = 2; count <= 5; count++) {
        await reinit(); await page.clock.runFor(10000); await waitFinished(count);
        assert.equal(refreshPosts, count, 'only one automatic check per interval before sixth');
      }
      const sixthRealStart = Date.now();
      await page.clock.runFor(10000);
      await eventually(() => fs.existsSync(config.deadline_ready_path));
      const starts = await page.evaluate(() => window.paymentEvents.starts);
      assert.equal(starts.length, 6, 'sixth real POST reached provider transport');
      assert.ok(starts[5] - starts[0] >= 50000 && starts[5] - starts[0] < 51000, 'sixth begins around50s');
      assert.ok(starts.every((value, i) => i === 0 || value - starts[i - 1] >= 10000));
      await page.clock.runFor(12000); // Cross60s with the original real XHR still in flight.
      assert.equal(refreshPosts, 6, 'no seventh automatic POST at the start deadline');
      assert.equal(await main().getAttribute('aria-busy'), 'true', '60s start window must not abort sixth in-flight XHR');
      assert.equal(await page.evaluate(() => window.paymentEvents.finished), 5, 'sixth keeps its own15s request budget');
      await stable();
      if (config.case === 'deadline-timeout') {
        // XHR.timeout is a native browser timer, not the controlled window clock.
        await eventually(async () => await page.locator('[data-billing-status-message]').isVisible(), 22000);
        assert.equal(await page.evaluate(() => window.paymentEvents.timeouts), 1, 'own native15s timeout fires after global start window');
        assert.ok(Date.now() - sixthRealStart >= 14000, 'deadline does not masquerade as own15s timeout');
        assert.equal(await page.locator('[data-billing-status-message]').getAttribute('role'), 'alert');
        assert.equal(await page.getByRole('button', {name: 'Проверить оплату', exact: true}).isDisabled(), true);
      }
      fs.writeFileSync(config.deadline_release_path, '1', {mode: 0o600, flag: 'wx'});
      await eventually(() => fs.existsSync(config.deadline_complete_path));
      if (config.case === 'deadline-timeout') {
        await sleep(100);
        assert.equal(await page.getByRole('heading', {name: 'Проверяем оплату', exact: true}).count(), 1, 'late successful server response cannot replace timed-out document');
        assert.equal(await page.getByRole('heading', {name: 'Оплачено', exact: true}).count(), 0);
        await noMore(6); await stable();
        await page.locator('[data-billing-status-recovery]').click(); intentionalNavigations++;
        await page.waitForLoadState('domcontentloaded'); await paid();
        assert.equal(await main().locator('form[method=post]').count(), 0, 'local recovery creates no competing billing POST');
      } else {
        await waitFinished(6);
        assert.equal(await page.evaluate(() => window.paymentEvents.timeouts), 0, 'valid post60s response is within its own native timeout');
        if (config.case === 'deadline-success') await paid();
        else {
          assert.equal(await page.getByRole('heading', {name: 'Проверяем оплату', exact: true}).count(), 1);
          const message = page.locator('[data-billing-status-message]');
          assert.equal(await message.isVisible(), true, 'last pending response explains end of automatic waiting');
          assert.ok((await message.innerText()).includes('Подтверждение пока не получено'), 'pending has honest result');
          assert.ok((await message.innerText()).includes('Проверьте оплату позже'), 'manual recovery is understandable');
          assert.equal(await page.getByRole('button', {name: 'Проверить оплату', exact: true}).isEnabled(), true);
          assert.equal(await main().getByRole('button', {name: 'Вернуться к оплате', exact: true}).isEnabled(), true);
        }
        await stable();
      }
      await noMore(6); await reinit(); await noMore(6);
      assert.equal(refreshPosts, 6, 'start-window expiry cannot schedule seventh auto even after reinit');
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
