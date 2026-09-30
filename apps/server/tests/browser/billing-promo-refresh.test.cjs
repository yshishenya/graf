'use strict';

// Real native form submission against ASGI routes/PostgreSQL, never setContent.
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
    config.screenshots_dir = path.join(config.screenshots_dir, config.receipt_verified ? 'verified' : 'unverified');
    fs.mkdirSync(config.screenshots_dir, { recursive: true });
  }
  const browser = await ({ chromium, webkit })[engine].launch({ headless: true });
  let submitRedirects = 0;
  let externalRequests = 0;
  const viewports = [320, 1280];
  try {
    for (const width of viewports) {
      const context = await browser.newContext({ viewport: { width, height: 1000 } });
      await context.addCookies([{
        name: config.cookie_name, value: config.session_token, url: base,
        httpOnly: true, sameSite: 'Lax', secure: false,
      }]);
      await context.route('**/*', async route => {
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
          assert.ok(summary.includes(`Автопродление ${renewal} ₽ за ${cycle === 'year' ? 'год' : 'месяц'}`));
          for (const name of ['offer_consent', 'recurring_consent']) {
            const consent = page.locator(`input[name="${name}"]`);
            assert.equal(await consent.count(), config.receipt_verified ? 1 : 0);
            if (config.receipt_verified) assert.equal(await consent.isChecked(), false);
          }
          if (config.receipt_verified) {
            assert.ok(normalized(await page.locator('[data-billing-primary]').innerText()).includes(`Оплатить ${today} ₽`));
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

      async function submit(button, target = page, endpoint = '/billing/checkout/preview') {
        const response = target.waitForResponse(response => response.request().method() === 'POST'
          && new URL(response.url()).pathname === endpoint);
        await Promise.all([target.waitForNavigation({ waitUntil: 'domcontentloaded' }), button.click()]);
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

      stage = `${width}:initial-apply`;
      await page.goto(`${base}/billing/checkout?cycle=month`, { waitUntil: 'domcontentloaded' });
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
      const enterResponse = page.waitForResponse(response => response.request().method() === 'POST'
        && new URL(response.url()).pathname === '/billing/checkout/preview');
      await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded' }), input.press('Enter')]);
      assert.equal((await enterResponse).status(), 303);
      submitRedirects++;
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
      await context.close();
    }
    process.stdout.write(JSON.stringify({
      engine, viewports, submit_redirects: submitRedirects, external_requests: externalRequests,
      receipt_verified: config.receipt_verified,
    }));
  } finally {
    await browser.close();
  }
}

run().catch(error => {
  // Do not dump cookies, HTML, CSRF form data, or request headers on failure.
  const reason = error.name === 'AssertionError' && !error.generatedMessage
    ? error.message.split('\n')[0] : error.name;
  process.stderr.write(`Promo DOM proof failed at ${stage} (${reason})\n`);
  process.exitCode = 1;
});
