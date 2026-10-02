'use strict';

// Real preview XHR and native payment forms against ASGI/PostgreSQL, never setContent.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, webkit } = require(path.join(process.env.GRAF_NODE_MODULES || path.join(__dirname, 'node_modules'), 'playwright'));

const engine = process.env.GRAF_BROWSER || 'chromium';
let stage = 'configuration';

async function run() {
  assert.ok(['chromium', 'webkit'].includes(engine));
  const config = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const base = config.base_url;
  if (config.screenshots_dir) {
    config.screenshots_dir = path.join(config.screenshots_dir, config.provider_rejection || (config.receipt_verified ? 'verified' : 'unverified'));
    fs.mkdirSync(config.screenshots_dir, { recursive: true });
  }
  const browser = await ({ chromium, webkit })[engine].launch({ headless: true });
  let submitRedirects = 0;
  let previewUpdates = 0;
  let externalRequests = 0;
  let providerRedirects = 0;
  const viewports = config.provider_rejection || config.inline_case ? [config.width] : [320, 1280];
  try {
    for (const width of viewports) {
      const context = await browser.newContext({ viewport: { width, height: 1000 },
        javaScriptEnabled: config.inline_case !== 'inline-native' });
      await context.addCookies([{
        name: config.cookie_name, value: config.session_token, url: base,
        httpOnly: true, sameSite: 'Lax', secure: false,
      }]);
      await context.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (config.receipt_verified && stage === `${width}:one-period-start`
            && url.origin === base && url.pathname === '/billing/checkout/start'
            && route.request().method() === 'POST') {
          // Send the native browser form to the real ASGI route and inspect its
          // redirect without following the deliberately unresolvable provider.
          const response = await route.fetch({maxRedirects: 0});
          assert.equal(response.status(), 303, 'real checkout returns a provider redirect');
          const destination = new URL(response.headers().location);
          assert.ok(destination.origin === 'https://yookassa.test'
            && destination.pathname.startsWith('/checkout/'), 'expected synthetic provider destination');
          providerRedirects++;
          await route.fulfill({status: 200, contentType: 'text/html; charset=utf-8', body: '<meta charset="utf-8"><p>Переход к оплате проверен</p>'});
          return;
        }
        if (new URL(route.request().url()).origin !== base) {
          externalRequests++;
          await route.abort();
        } else {
          await route.continue();
        }
      });
      const page = await context.newPage();
      const input = page.locator('#billing-promo');
      const apply = page.locator('button[form="billing-promo-preview"][value="apply"]');
      let recurringChoice = true;
      const normalized = text => text.replace(/\s+/gu, ' ').replace(/(?<=\d)\s+(?=\d)/gu, '').trim();

      async function verify({ code, cycle, today, renewal, error = false }) {
        await page.evaluate(() => document.fonts.ready);
        assert.equal(await input.inputValue(), code);
        assert.equal(new URL(page.url()).searchParams.has('promo_code'), false);
        assert.equal(new URL(page.url()).searchParams.has('quote_id'), false);
        assert.equal(await page.locator('.billing-period-switch button[aria-current="true"]').getAttribute('value'), cycle);
        if (error) {
          assert.equal(await input.getAttribute('aria-invalid'), 'true');
          assert.ok(await page.locator('#billing-checkout-error').isVisible());
          assert.equal(await page.locator('form[action="/billing/checkout/start"]').count(), 0);
          assert.equal(await page.locator('.billing-coupon[open] #billing-promo').count(), 1);
        } else {
          const summary = normalized(await page.locator('.billing-order-summary').first().innerText());
          assert.ok(summary.includes(`К оплате сегодня ${today} ₽`));
          if (recurringChoice) {
            assert.ok(summary.includes(`${config.inline_case === 'inline-native' ? 'При автопродлении' : 'Автопродление'} ${renewal} ₽ за ${cycle === 'year' ? 'год' : 'месяц'}`), 'renewal amount and period visible');
          } else {
            assert.ok(summary.includes('Отключено — автоматического списания не будет.'));
            assert.equal(await page.locator('[data-billing-next-attempt]').isVisible(), false);
          }
          for (const name of ['offer_consent', 'recurring_consent']) {
            const consent = page.locator(`input[name="${name}"]`);
            assert.equal(await consent.count(), config.receipt_verified ? 1 : 0);
            if (config.receipt_verified) {
              assert.equal(await consent.isChecked(), name === 'recurring_consent' ? recurringChoice : false);
              assert.equal(await consent.evaluate(el => el.required), name === 'offer_consent');
            }
          }
          if (config.receipt_verified) {
            assert.ok(normalized(await page.locator('[data-billing-primary]').innerText()).includes(`Оплатить ${today} ₽`));
            assert.ok(await page.locator('[data-billing-primary]').isEnabled(), 'fresh valid calculation permits payment');
            const compactConsents = await page.locator('.billing-checkout-form').evaluate(form => {
              const px = value => Number.parseFloat(value) || 0;
              return [...form.querySelectorAll('.billing-consent')].every(label => {
                const style = getComputedStyle(label);
                const content = Math.max(px(style.minHeight), ...[...label.children].map(child => {
                  const childStyle = getComputedStyle(child);
                  return child.getBoundingClientRect().height
                    + px(childStyle.marginTop) + px(childStyle.marginBottom);
                }));
                const needed = content + px(style.paddingTop) + px(style.paddingBottom)
                  + px(style.borderTopWidth) + px(style.borderBottomWidth);
                return label.getBoundingClientRect().height <= needed + 2;
              });
            });
            assert.ok(compactConsents, 'consent rows fit their visible text and controls');
          }
        }
        if (!config.receipt_verified) {
          assert.equal(await page.locator('form[action="/billing/checkout/start"]').count(), 0);
          assert.ok(await page.getByRole('link', { name: 'Подтвердить почту', exact: true }).isVisible());
        }
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false);
      }

      async function submit(button, target = page, endpoint = '/billing/checkout/preview', keyboard = false) {
        if (endpoint === '/billing/checkout/preview') {
          await target.evaluate(() => {
            window.grafPreviewSettled = false;
            document.body.addEventListener('htmx:afterSettle', () => { window.grafPreviewSettled = true; }, {once: true});
            window.grafPreviewMain = document.querySelector('main.billing-checkout-page');
            window.grafPreviewDocument = document;
          });
          const response = target.waitForResponse(response => response.status() === 200
            && response.request().resourceType() === 'xhr'
            && new URL(response.url()).pathname === '/billing/checkout');
          if (keyboard) await button.focus();
          await (keyboard ? button.press('Enter') : button.click());
          await (await response).finished();
          await target.waitForFunction(() => window.grafPreviewMain !== document.querySelector('main.billing-checkout-page'));
          await target.waitForFunction(() => window.grafPreviewSettled);
          assert.equal(await target.evaluate(() => window.grafPreviewDocument === document), true,
            'preview uses the existing document');
          previewUpdates++;
          return;
        }
        const response = target.waitForResponse(response => response.request().method() === 'POST'
          && new URL(response.url()).pathname === endpoint);
        if (keyboard) await button.focus();
        await Promise.all([target.waitForNavigation({ waitUntil: 'domcontentloaded' }),
          keyboard ? button.press('Enter') : button.click()]);
        assert.equal((await response).status(), 303);
        submitRedirects++;
      }

      async function reloadTwice(expected) {
        for (let i = 0; i < 2; i++) {
          await page.reload({ waitUntil: 'domcontentloaded' });
          await verify(expected);
        }
      }

      async function screenshot(state) {
        if (config.screenshots_dir) {
          await page.screenshot({
            path: path.join(config.screenshots_dir, `promo-refresh-${engine}-${width}-${state}.png`),
            fullPage: true,
          });
          if (config.receipt_verified && (state === 'applied' || state === 'cleared')) {
            const form = page.locator('.billing-checkout-form');
            const layout = () => form.evaluate(el => ({
              form_height: el.getBoundingClientRect().height,
              row_tracks: getComputedStyle(el).gridTemplateRows,
              labels: [...el.querySelectorAll('.billing-consent')].map(label => ({
                top: label.getBoundingClientRect().top - el.getBoundingClientRect().top,
                height: label.getBoundingClientRect().height,
                width: label.getBoundingClientRect().width,
                row_tracks: getComputedStyle(label).gridTemplateRows,
                column_tracks: getComputedStyle(label).gridTemplateColumns,
                span_width: label.querySelector('span').getBoundingClientRect().width,
                span_height: label.querySelector('span').getBoundingClientRect().height,
                input_width: label.querySelector('input').getBoundingClientRect().width,
                input_height: label.querySelector('input').getBoundingClientRect().height,
              })),
              button_top: el.querySelector('[data-billing-primary]').getBoundingClientRect().top
                - el.getBoundingClientRect().top,
            }));
            const before = await layout();
            await page.locator('.billing-checkout-form').screenshot({
              path: path.join(config.screenshots_dir, `promo-refresh-${engine}-${width}-${state}-consents.png`),
            });
            fs.writeFileSync(path.join(config.screenshots_dir, `promo-refresh-${engine}-${width}-${state}-layout.json`),
              JSON.stringify({ before, after: await layout() }));
          }
        }
      }

      if (config.inline_case) {
        stage = `${width}:inline-initial`;
        const native = config.inline_case === 'inline-native';
        const blocked = config.inline_case.includes('-blocked');
        if (blocked) await context.addInitScript(() => {
          for (const method of ['getItem', 'setItem']) Storage.prototype[method] = () => { throw new DOMException('blocked', 'SecurityError'); };
        });
        await page.goto(`${base}/billing/checkout?cycle=year`, { waitUntil: 'domcontentloaded' });
        recurringChoice = !config.receipt_verified || !config.inline_case.includes('-off-');
        if (blocked) await page.evaluate(() => {
          for (const method of ['getItem', 'setItem']) Storage.prototype[method] = () => { throw new DOMException('blocked', 'SecurityError'); };
        });
        if (config.receipt_verified) {
          assert.equal(await page.locator('input[name="recurring_consent"]').isChecked(), true);
          await page.locator('input[name="recurring_consent"]').setChecked(recurringChoice);
        }
        const marker = 'synthetic-inline-document';
        let documentNavigations = 0;
        let checkingPreview = false;
        page.on('request', request => {
          if (checkingPreview && request.isNavigationRequest() && request.frame() === page.mainFrame()) documentNavigations++;
        });
        if (!native) await page.evaluate(value => { window.grafInlineMarker = value; document.body.dataset.inlineMarker = value; }, marker);
        const historyLength = await page.evaluate(() => history.length);
        let updates = 0;
        let recoveryChecks = 0;
        let busyChecks = 0;
        const main = () => page.locator('main.billing-checkout-page');
        const quote = () => main().locator('input[name="quote_id"]').first().inputValue();
        const consent = () => page.locator('input[name="offer_consent"]');
        const openCoupon = async () => { if (!(await input.isVisible())) await page.getByText('Есть промокод?', { exact: true }).click(); };
        const safeURL = async cycle => {
          const url = new URL(page.url());
          assert.equal(url.searchParams.get('cycle'), cycle);
          for (const field of ['promo_code', 'quote_id', 'recurring_consent', 'offer_consent', ...(native ? [] : ['result'])]) assert.equal(url.searchParams.has(field), false, 'private calculation fields stay out of URL');
        };
        const identity = async () => {
          assert.equal(await page.evaluate(() => window.grafInlineMarker), marker, 'preview retains window');
          assert.equal(await page.locator('body').getAttribute('data-inline-marker'), marker, 'preview retains document');
          assert.equal(documentNavigations, 0, 'preview sends no main document request');
          assert.equal(await page.evaluate(() => history.length), historyLength, 'preview does not append history');
        };
        const inline = async (button, expected, keyboard = false) => {
          if (config.receipt_verified && await consent().count()) await consent().check();
          checkingPreview = true;
          if (native) {
            const response = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/billing/checkout/preview');
            await Promise.all([page.waitForNavigation({waitUntil: 'domcontentloaded'}), keyboard ? button.press('Enter') : button.click()]);
            assert.equal((await response).status(), 303);
            submitRedirects++;
          } else {
            await submit(button, page, '/billing/checkout/preview', keyboard);
            await identity();
            assert.equal(await main().getAttribute('aria-busy'), null);
            assert.ok(await button.isEnabled());
          }
          checkingPreview = false;
          await verify(expected);
          await safeURL(expected.cycle);
          if (!native) {
            assert.equal(await page.evaluate(() => document.activeElement?.id === 'billing-promo'
              || document.activeElement?.getAttribute('form') === 'billing-promo-preview'
              || document.activeElement?.matches('.billing-coupon summary')), true, 'focus returns to visible input/action/summary');
            if (!expected.error) assert.ok(await page.locator('[data-billing-preview-status]').filter({hasText: /К оплате/}).isVisible());
          }
          updates++;
        };
        const month = {code: 'SYNTH-PRESENTATION', cycle: 'month', today: '900', renewal: '1000'};
        const year = {code: 'SYNTH-PRESENTATION', cycle: 'year', today: '9000', renewal: '10000'};
        await openCoupon();
        await input.fill(month.code);
        stage = `${width}:inline-apply`;
        await inline(apply, year);
        if (native || config.inline_case.startsWith('inline-basic')) {
          stage = `${width}:inline-month`;
          await inline(page.locator('.billing-period-switch button[value="month"]'), month, true);
          if (!native) {
            for (let i = 0; i < 2; i++) {
              await page.reload({waitUntil: 'domcontentloaded'});
              recurringChoice = blocked ? true : recurringChoice;
              await verify(month);
              await safeURL('month');
            }
            await page.evaluate(value => { window.grafInlineMarker = value; document.body.dataset.inlineMarker = value; }, marker);
          }
          if (blocked && config.receipt_verified) {
            recurringChoice = !config.receipt_verified || !config.inline_case.includes('-off-');
            await page.locator('input[name="recurring_consent"]').setChecked(recurringChoice);
          }
          stage = `${width}:inline-invalid-twice`;
          for (const code of ['AB', 'SYNTH-UNKNOWN']) {
            await input.fill(code);
            await inline(apply, {code, cycle: 'month', error: true}, code === 'AB');
            assert.equal((await main().innerText()).includes('Проверочное окно'), false);
          }
          stage = `${width}:inline-correct-with-enter`;
          await input.fill(month.code);
          await inline(input, month, true);
          stage = `${width}:inline-year`;
          await inline(page.locator('.billing-period-switch button[value="year"]'), year);
          stage = `${width}:inline-clear`;
          await input.fill('');
          await inline(apply, {code: '', cycle: 'year', today: '10000', renewal: '10000'});
          if (!native) {
            await page.reload({waitUntil: 'domcontentloaded'});
            recurringChoice = blocked ? true : recurringChoice;
            await verify({code: '', cycle: 'year', today: '10000', renewal: '10000'});
            await safeURL('year');
          }
        } else {
          // Hold the real response to prove the controls and duplicate/start guards.
          stage = `${width}:inline-busy`;
          let release;
          let intercepted;
          const held = new Promise(resolve => { intercepted = resolve; });
          const gate = new Promise(resolve => { release = resolve; });
          let requests = 0;
          const holdRoute = async route => { requests++; intercepted(); await gate; await route.continue(); };
          await page.route('**/billing/checkout/preview', holdRoute);
          await apply.click();
          await held;
          assert.equal(await main().getAttribute('aria-busy'), 'true');
          assert.equal(await main().locator('input:not(:disabled),button:not(:disabled)').count(), 0);
          assert.ok(await page.getByRole('status').filter({hasText: 'Проверяем сумму'}).isVisible());
          if (config.receipt_verified) {
            assert.equal(await consent().isChecked(), false);
            assert.equal(await page.locator('form[action="/billing/checkout/start"]').evaluate(form => {
              const event = new Event('submit', {bubbles: true, cancelable: true}); form.dispatchEvent(event); return event.defaultPrevented;
            }), true, 'start blocked during preview');
          }
          await page.locator('#billing-promo-preview').evaluate(form => form.requestSubmit());
          assert.equal(requests, 1, 'duplicate preview dropped');
          release();
          await page.waitForFunction(() => !document.querySelector('main.billing-checkout-page[aria-busy="true"]'));
          await page.unroute('**/billing/checkout/preview', holdRoute);
          await verify(year);
          await identity();
          busyChecks++;
          const failure = async (name, responder, beforeRelease = null) => {
            stage = `${width}:inline-${name}`;
            const previous = await quote();
            const previousScope = await page.locator('meta[name="graf-workspace"]').getAttribute("content");
            const handler = async route => {
              const response = responder ? await responder(route) : null;
              if (beforeRelease) await beforeRelease();
              if (response) await route.fulfill(response);
            };
            await page.route('**/billing/checkout/preview', handler);
            checkingPreview = true;
            await apply.click();
            await page.waitForFunction(() => document.querySelector('main.billing-checkout-page')?.dataset.billingPreviewState === 'recovery');
            checkingPreview = false;
            assert.equal(await quote(), previous, 'failed response does not replace authoritative quote');
            assert.ok(await input.isEnabled());
            assert.ok(await apply.isEnabled());
            assert.equal(await main().getAttribute('aria-busy'), null);
            assert.ok(await page.locator('[data-billing-preview-status][role="alert"]').isVisible());
            assert.ok(await page.getByRole('link', {name: 'Открыть оплату заново'}).isVisible());
            assert.equal(await page.evaluate(() => document.activeElement?.getAttribute('value') === 'apply'), true);
            if (config.receipt_verified) {
              assert.ok(await page.locator('form[action="/billing/checkout/start"] button').isDisabled());
              assert.equal(await consent().isChecked(), false);
            }
            await identity();
            await page.unroute('**/billing/checkout/preview', handler);
            recoveryChecks++;
            await page.locator('meta[name="graf-workspace"]').evaluate((meta, value) => { meta.content = value; }, previousScope);
            await inline(apply, year);
          };
          if (config.inline_case === 'inline-errors') {
            for (const status of [500, 429, 401, 403]) await failure(`http-${status}`, async () => ({status, contentType: 'text/html', body: '<p>synthetic failure</p>'}));
            await failure('network', async route => { await route.abort(); });
            await failure('unexpected-html', async () => ({status: 200, contentType: 'text/html', body: '<main id="cabinet-main">synthetic unexpected</main>'}));
          } else if (config.inline_case === 'inline-timeout') {
            // The ASGI bridge holds this real response beyond the configured
            // 15s timeout. Native XHR timeout starts differently under WebKit
            // interception, so this handler lets the network run normally.
            await failure('timeout', async route => { await route.continue(); });
          } else if (config.inline_case === 'inline-guards') {
            for (const name of ['graf-time-user', 'graf-workspace', 'graf-time-session']) {
              await failure(`response-scope-${name}`, async route => {
                const response = await route.fetch();
                const body = (await response.text()).replace(new RegExp(`(<meta name="${name}" content=")[^"]*(")`), '$1synthetic-other$2');
                return {response, body};
              });
            }
            await failure('auth-html', async () => ({status: 200, contentType: 'text/html', body: '<main id="cabinet-main"><h1>Войти</h1></main>'}));
            await failure('changed-current-scope', async route => {
              const response = await route.fetch();
              return {response, body: await response.text()};
            }, async () => { await page.locator('meta[name="graf-workspace"]').evaluate(meta => { meta.content = 'synthetic-other'; }); });
            // An already detached target may never receive a late response.
            stage = `${width}:inline-detached-late`;
            let releaseLate;
            let lateSeen;
            const lateGate = new Promise(resolve => { releaseLate = resolve; });
            const lateIntercept = new Promise(resolve => { lateSeen = resolve; });
            const late = async route => {
              const response = await route.fetch(); lateSeen(); await lateGate;
              await route.fulfill({response, body: await response.text()});
            };
            await page.route('**/billing/checkout/preview', late);
            const freshMarkup = await main().evaluate(el => el.outerHTML);
            await page.evaluate(() => {
              window.grafLateRequestFinished = false;
              const observePreview = event => {
                if (event.detail?.elt?.id !== 'billing-promo-preview') return;
                document.body.removeEventListener('htmx:beforeRequest', observePreview);
                event.detail.xhr.addEventListener('loadend', () => { window.grafLateRequestFinished = true; }, {once: true});
              };
              document.body.addEventListener('htmx:beforeRequest', observePreview);
            });
            await apply.click();
            await lateIntercept;
            await main().evaluate((el, markup) => {
              const replacement = document.createRange().createContextualFragment(markup).firstElementChild;
              replacement.dataset.syntheticReplacement = 'true'; el.replaceWith(replacement);
              window.htmx.process(replacement);
            }, freshMarkup);
            const previous = await quote();
            const lateResponse = page.waitForResponse(r => new URL(r.url()).pathname === '/billing/checkout/preview');
            releaseLate();
            await (await lateResponse).finished();
            await page.waitForFunction(() => window.grafLateRequestFinished);
            await page.waitForFunction(() => document.querySelector('main.billing-checkout-page')?.dataset.syntheticReplacement === 'true');
            assert.equal(await quote(), previous);
            await page.unroute('**/billing/checkout/preview', late);
            stage = `${width}:inline-detached-fresh-retry`;
            await inline(apply, year);
          }
        }
        await context.close();
        process.stdout.write(JSON.stringify({engine, viewports, inline_case: config.inline_case,
          external_requests: externalRequests, document_navigations: native ? undefined : documentNavigations,
          submit_redirects: submitRedirects, updates, recovery_checks: recoveryChecks, busy_checks: busyChecks}));
        return;
      }

      if (config.provider_rejection) {
        let starts = 0;
        page.on('request', request => {
          if (request.method() === 'POST' && new URL(request.url()).pathname === '/billing/checkout/start') starts++;
        });
        const recurring = page.getByRole('checkbox', { name: /Разрешаю автоматические списания/ });
        const offer = page.getByRole('checkbox', { name: /Принимаю/ });
        const quote = () => page.locator('form[action="/billing/checkout/start"] input[name="quote_id"]').inputValue();
        const assertSafe = async () => {
          const url = new URL(page.url());
          for (const field of ['promo_code', 'quote_id', 'recurring_consent', 'offer_consent']) {
            assert.equal(url.searchParams.has(field), false, 'checkout fields stay out of URL');
          }
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false,
            'status and checkout fit the viewport');
          const text = await page.locator('#cabinet-main').innerText();
          assert.equal(text.includes('YooMoney'), false, 'raw provider description is never rendered');
          assert.equal(text.includes('Synthetic unrelated'), false, 'unknown provider text is never rendered');
        };
        stage = `${width}:provider-promo-year`;
        await page.goto(`${base}/billing/checkout?cycle=year`, {waitUntil: 'domcontentloaded'});
        await page.getByText('Есть промокод?', {exact: true}).click();
        await input.fill('SYNTH-PRESENTATION');
        await submit(apply);
        await verify({code: 'SYNTH-PRESENTATION', cycle: 'year', today: '9000', renewal: '10000'});
        const oldQuote = await quote();
        assert.equal(starts, 0);
        await offer.focus();
        await offer.press('Space');
        assert(await offer.isChecked());
        stage = `${width}:provider-true-rejection`;
        await submit(page.getByRole('button', {name: /^Оплатить/}), page, '/billing/checkout/start', true);
        const statusUrl = page.url();
        assert.ok(new URL(statusUrl).pathname.startsWith('/billing/checkout/status/'));
        const specific = config.provider_rejection === 'recurring';
        const uncertain = config.provider_rejection === 'uncertain';
        for (let i = 0; i < 3; i++) {
          if (i) await page.reload({waitUntil: 'domcontentloaded'});
          await assertSafe();
          const title = await page.locator('#billing-operation-title').innerText();
          assert.equal(title === 'Не удалось начать оплату', !uncertain, 'creation rejection differs from unknown outcome');
          const text = await page.locator('#cabinet-main').innerText();
          if (!uncertain) {
            assert.ok(text.includes('Оплата не началась.'), 'rejected creation is explained as not started');
            assert.equal(text.includes('Проверьте этот платеж позже.'), false, 'historical result cannot override definite rejection');
          }
          assert.equal(text.includes('Автопродление недоступно'), specific, 'only the exact rejection gets a precise hint');
          assert.equal(text.includes('снимите галочку'), specific, 'only the exact rejection explains manual False');
          const primary = page.locator('[data-billing-primary]');
          assert.equal(await primary.innerText(), uncertain ? 'Проверить статус' : specific ? 'Вернуться к оплате' : 'Попробовать снова');
          assert.equal(starts, 1, 'status GET and reload never create another payment');
        }
        await screenshot('provider-status');
        stage = `${width}:provider-keyboard-return`;
        if (uncertain) {
          assert.equal(await page.locator('a[href^="/billing/checkout?cycle="]').count(), 0, 'unknown result has no retry');
          await page.goto(`${base}/billing/checkout?cycle=year`, {waitUntil: 'domcontentloaded'});
          for (let i = 0; i < 3; i++) {
            if (i) await page.reload({waitUntil: 'domcontentloaded'});
            assert.equal(await page.locator('form[action="/billing/checkout/start"]').count(), 0,
              'unknown result blocks a new checkout form');
            assert.equal(await page.getByRole('button', {name: /^Оплатить/}).count(), 0);
            assert.equal(starts, 1);
            await assertSafe();
          }
          await screenshot('provider-blocked');
        } else {
          const retry = page.locator('[data-billing-primary]');
          assert.equal(await retry.getAttribute('href'), '/billing/checkout?cycle=year');
          await retry.focus();
          assert(await retry.evaluate(el => el === document.activeElement), 'retry receives keyboard focus');
          await Promise.all([page.waitForNavigation({waitUntil: 'domcontentloaded'}), retry.press('Enter')]);
          await verify({code: '', cycle: 'year', today: '10000', renewal: '10000'});
          assert.notEqual(await quote(), oldQuote, 'retry receives a fresh quote after draft consumption');
          assert.equal(starts, 1, 'retry navigation has no money POST');
          for (let i = 0; i < 2; i++) {
            await page.reload({waitUntil: 'domcontentloaded'});
            await verify({code: '', cycle: 'year', today: '10000', renewal: '10000'});
            assert.equal(starts, 1);
          }
          await recurring.focus();
          await recurring.press('Space');
          recurringChoice = false;
          await verify({code: '', cycle: 'year', today: '10000', renewal: '10000'});
          await assertSafe();
          await screenshot('provider-manual-false');
          await offer.focus();
          await offer.press('Space');
          assert(await offer.isChecked(), 'fresh offer explicitly accepted');
          stage = `${width}:one-period-start`;
          const submitted = page.waitForRequest(request => request.method() === 'POST'
            && new URL(request.url()).pathname === '/billing/checkout/start');
          const pay = page.getByRole('button', {name: /^Оплатить/});
          await pay.focus();
          await Promise.all([page.waitForNavigation({waitUntil: 'domcontentloaded'}), pay.press('Enter')]);
          await page.getByText('Переход к оплате проверен', {exact: true}).waitFor({state: 'visible'});
          const fields = new URLSearchParams((await submitted).postData());
          assert.equal(fields.get('recurring_consent'), null);
          assert.equal(fields.get('offer_consent'), 'true');
          assert.equal(fields.get('cycle'), 'year');
          assert.notEqual(fields.get('quote_id'), oldQuote);
          assert.equal(starts, 2, 'manual False dispatches exactly one new checkout POST');
        }
        await context.close();
        continue;
      }

      stage = `${width}:initial-apply`;
      await page.goto(`${base}/billing/checkout?cycle=month`, { waitUntil: 'domcontentloaded' });
      if (config.receipt_verified) {
        const recurring = page.getByRole('checkbox', { name: /Разрешаю автоматические списания/ });
        assert(await recurring.isChecked(), 'first visit defaults to optional recurring enabled');
        assert.equal(await recurring.evaluate(el => el.required), false);
        await recurring.uncheck();
        recurringChoice = false;
        assert(await page.getByText('Отключено — автоматического списания не будет.', { exact: true }).isVisible());
      }
      stage = `${width}:initial-open`;
      await page.getByText('Есть промокод?', { exact: true }).click();
      stage = `${width}:initial-fill`;
      await input.fill('SYNTH-PRESENTATION');
      stage = `${width}:initial-submit`;
      await submit(apply);
      const month = { code: 'SYNTH-PRESENTATION', cycle: 'month', today: '900', renewal: '1000' };
      await verify(month);
      stage = `${width}:two-reloads`;
      await reloadTwice(month);
      await screenshot('applied');

      stage = `${width}:back-and-return`;
      await page.getByRole('link', { name: 'Назад к тарифам', exact: true }).click();
      stage = `${width}:plans-url`;
      await page.waitForURL('**/billing/plans');
      stage = `${width}:go-back`;
      await page.goBack({ waitUntil: 'domcontentloaded' });
      stage = `${width}:verify-after-back`;
      await verify(month);
      stage = `${width}:return-without-cycle`;
      await page.goto(`${base}/billing/checkout`, { waitUntil: 'domcontentloaded' });
      stage = `${width}:verify-return`;
      await verify(month);

      stage = `${width}:year`;
      await submit(page.locator('.billing-period-switch button[value="year"]'));
      const year = { code: 'SYNTH-PRESENTATION', cycle: 'year', today: '9000', renewal: '10000' };
      await verify(year);
      await reloadTwice(year);

      stage = `${width}:enter-keeps-year`;
      await input.fill('SYNTH-PRESENTATION');
      await submit(input, page, '/billing/checkout/preview', true);
      await verify(year);
      await page.goto(`${base}/billing/checkout`, { waitUntil: 'domcontentloaded' });
      await verify(year);
      stage = `${width}:month`;
      await submit(page.locator('.billing-period-switch button[value="month"]'));
      await verify(month);

      stage = `${width}:malformed`;
      await input.fill('AB');
      await submit(apply);
      const invalid = { code: 'AB', cycle: 'month', error: true };
      await verify(invalid);
      await reloadTwice(invalid);
      await screenshot('error');

      stage = `${width}:edit-and-switch`;
      // Switch period while editing: associated native submit must use the live
      // input value, rather than the last server-rendered hidden copy.
      await input.fill('SYNTH-PRESENTATION');
      await submit(page.locator('.billing-period-switch button[value="year"]'));
      await verify(year);
      await reloadTwice(year);

      stage = `${width}:clear`;
      await input.fill('');
      await submit(apply);
      const empty = { code: '', cycle: 'year', today: '10000', renewal: '10000' };
      await verify(empty);
      await reloadTwice(empty);
      await screenshot('cleared');

      stage = `${width}:first-unsubmitted-code-switch`;
      await page.getByText('Есть промокод?', { exact: true }).click();
      await input.fill('SYNTH-PRESENTATION');
      await submit(page.locator('.billing-period-switch button[value="month"]'));
      await verify(month);
      await reloadTwice(month);

      // Two native pages share cookies but retain different rendered inputs.
      for (const staleCode of ['SYNTH-PRESENTATION', '']) {
        stage = `${width}:stale-${staleCode ? 'nonempty' : 'empty'}-tab`;
        assert.equal(await input.inputValue(), staleCode);
        const other = await context.newPage();
        await other.goto(`${base}/billing/checkout`, { waitUntil: 'domcontentloaded' });
        if (config.receipt_verified) assert(await other.getByRole('checkbox', { name: /Разрешаю/ }).isChecked(), 'other tab has its own default');
        const otherInput = other.locator('#billing-promo');
        if (!(await otherInput.isVisible())) await other.getByText('Есть промокод?', { exact: true }).click();
        await otherInput.fill('SYNTH-SECOND');
        await submit(other.locator('button[form="billing-promo-preview"][value="apply"]'), other);
        const draft = async () => {
          const cookie = (await context.cookies()).find(cookie => cookie.name === 'graf_checkout_promo_draft');
          assert.ok(cookie);
          return JSON.parse(Buffer.from(cookie.value.split('.')[0], 'base64url').toString('utf8'));
        };
        const expiry = (await draft()).expiry;
        await new Promise(resolve => setTimeout(resolve, 1100));
        const cycle = staleCode ? 'year' : 'month';
        await submit(page.locator(`.billing-period-switch button[value="${cycle}"]`));
        const latest = { code: 'SYNTH-SECOND', cycle, today: cycle === 'year' ? '7500' : '750', renewal: cycle === 'year' ? '10000' : '1000' };
        await verify(latest);
        assert.equal((await draft()).expiry, expiry, 'stale period does not renew latest draft');
        await reloadTwice(latest);
        await page.goto(`${base}/billing/checkout`, { waitUntil: 'domcontentloaded' });
        await verify(latest);

        stage = `${width}:explicit-replace-after-stale-tab`;
        await input.fill('SYNTH-PRESENTATION');
        await submit(apply);
        await verify(cycle === 'year' ? year : month);
        assert.ok((await draft()).expiry > expiry, 'explicit replacement has its own lifetime');
        await input.fill('');
        await submit(apply);
        await verify({ code: '', cycle, today: cycle === 'year' ? '10000' : '1000', renewal: cycle === 'year' ? '10000' : '1000' });
        await other.close();
      }

      for (const code of ['SYNTH-PRESENTATION', 'SYNTH-UNKNOWN']) {
        stage = `${width}:annual-discounts-${code === 'SYNTH-UNKNOWN' ? 'invalid' : 'valid'}`;
        await page.goto(`${base}/billing/discounts`, { waitUntil: 'domcontentloaded' });
        const discounts = page.locator('form[action="/billing/discounts/apply"]');
        assert.equal(await discounts.locator('[name="cycle"]').count(), 0);
        await discounts.locator('input[name="promo_code"]').fill(code);
        await submit(discounts.getByRole('button', { name: 'Применить и проверить цену' }), page, '/billing/discounts/apply');
        const annual = code === 'SYNTH-UNKNOWN' ? { code, cycle: 'year', error: true } : year;
        await verify(annual);
        await reloadTwice(annual);
        await page.goto(`${base}/billing/checkout`, { waitUntil: 'domcontentloaded' });
        await verify(annual);
        await screenshot(code === 'SYNTH-UNKNOWN' ? 'annual-discounts-error' : 'annual-discounts');
      }
      if (config.receipt_verified && width === 1280) {
        stage = `${width}:one-period-preview`;
        await input.fill('SYNTH-PRESENTATION');
        await submit(apply);
        await verify(year);

        stage = `${width}:offer-required-redirect`;
        // Exercise the server guard too; native required validation is covered
        // separately and only this synthetic submission bypasses it.
        await page.locator('form[action="/billing/checkout/start"]').evaluate(form => { form.noValidate = true; });
        await submit(page.getByRole('button', { name: /^Оплатить/ }), page, '/billing/checkout/start');
        assert(await page.getByRole('alert').filter({hasText: 'Откройте и примите оферту'}).isVisible());
        await verify(year);
        await reloadTwice(year);

        stage = `${width}:stale-offer-conflict`;
        // A form opened before an offer update must be rejected and freshly
        // rendered without changing the tab's explicit one-period preference.
        await page.locator('input[name="offer_version"]').evaluate(input => { input.value = 'synthetic-older-offer'; });
        await page.getByRole('checkbox', { name: /Принимаю/ }).check();
        const conflict = page.waitForResponse(response => response.request().method() === 'POST'
          && new URL(response.url()).pathname === '/billing/checkout/start');
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
          page.getByRole('button', { name: /^Оплатить/ }).click(),
        ]);
        assert.equal((await conflict).status(), 409);
        assert(await page.getByRole('alert').filter({hasText: 'Условия оплаты изменились'}).isVisible());
        await verify(year);
        await page.goto(`${base}/billing/checkout`, { waitUntil: 'domcontentloaded' });
        await reloadTwice(year);

        await page.getByRole('checkbox', { name: /Принимаю/ }).check();
        stage = `${width}:one-period-start`;
        const submitted = page.waitForRequest(request => request.method() === 'POST'
          && new URL(request.url()).pathname === '/billing/checkout/start');
        assert.equal(await page.getByRole('button', { name: /^Оплатить/ }).count(), 1, 'one checkout submit button');
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
          page.getByRole('button', { name: /^Оплатить/ }).click(),
        ]);
        stage = `${width}:one-period-document`;
        await page.getByText('Переход к оплате проверен', {exact: true}).waitFor({state: 'visible'});
        stage = `${width}:one-period-fields`;
        const fields = new URLSearchParams((await submitted).postData());
        assert.equal(fields.get('recurring_consent'), null, 'unchecked optional field is omitted from the real HTTP request');
        assert.equal(fields.get('offer_consent'), 'true', 'native form sends accepted offer');
        assert.equal(fields.get('cycle'), 'year', 'native form sends the chosen year');
      }
      await context.close();
    }
    process.stdout.write(JSON.stringify({
      engine, viewports, submit_redirects: submitRedirects, preview_updates: previewUpdates, external_requests: externalRequests,
      receipt_verified: config.receipt_verified,
      provider_redirects: providerRedirects,
      ...(config.provider_rejection ? {provider_rejection: config.provider_rejection} : {}),
    }));
  } finally {
    await browser.close();
  }
}

run().catch(error => {
  // Do not dump cookies, HTML, CSRF form data, or request headers on failure.
  const reason = error.name === 'AssertionError' && !error.generatedMessage
    ? error.message.split('\n')[0] : error.name;
  const browserCode = error.message.match(/(?:net::)?ERR_[A-Z_]+|strict mode violation|Target (?:page|closed)|not a valid selector/)?.[0];
  const location = error.stack?.match(/billing-promo-refresh\.test\.cjs:(\d+):(\d+)/)?.[0] || '';
  process.stderr.write(`Promo DOM proof failed at ${stage} (${reason}${browserCode ? `: ${browserCode}` : ''}) ${location}\n`);
  process.exitCode = 1;
});
