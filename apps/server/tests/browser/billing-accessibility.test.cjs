const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, webkit } = require('playwright');
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
const publicAssets = path.join(__dirname, '../../src/twobrain_rec_server/public/static/public');
const pages = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const visualDirectory = process.env.BILLING_VISUAL_OUTPUT_DIR;
if (visualDirectory) {
  fs.mkdirSync(visualDirectory, { recursive: true });
  fs.copyFileSync(process.argv[2], path.join(visualDirectory, 'pages.json'));
}

async function checkTextContrast(page, label) {
  const failures = await page.evaluate(() => {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const rgba = color => {
      ctx.clearRect(0, 0, 1, 1);
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, 1, 1);
      return [...ctx.getImageData(0, 0, 1, 1).data].map((v, i) => i === 3 ? v / 255 : v);
    };
    const composite = (a, b) => [0, 1, 2].map(i => a[i] * a[3] + b[i] * (1 - a[3]));
    const luminance = color => color.map(v => v / 255)
      .map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
      .reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
    const issues = [];
    for (const element of document.querySelectorAll('main *')) {
      if (!element.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }) ||
          element.matches(':disabled, option') ||
          ![...element.childNodes].some(node => node.nodeType === 3 && node.textContent.trim())) continue;
      const ancestors = [];
      for (let node = element; node; node = node.parentElement) ancestors.unshift(node);
      let background = [255, 255, 255];
      for (const node of ancestors) background = composite(rgba(getComputedStyle(node).backgroundColor), background);
      const style = getComputedStyle(element);
      const light = [luminance(composite(rgba(style.color), background)), luminance(background)].sort((a, b) => b - a);
      const contrast = (light[0] + 0.05) / (light[1] + 0.05);
      const large = parseFloat(style.fontSize) >= 24 || (parseFloat(style.fontSize) >= 18.667 && Number(style.fontWeight) >= 700);
      if (contrast < (large ? 3 : 4.5) - 0.01) issues.push(`${contrast.toFixed(2)}: ${element.textContent.trim()}`);
    }
    return issues;
  });
  assert.deepEqual(failures, [], `${label}: text contrast`);
}

(async () => {
  const isWebKit = process.env.GRAF_BROWSER === 'webkit';
  const browser = await (isWebKit ? webkit : chromium).launch({ headless: true });
  // WebKit on macOS follows the system preference; Option-Tab reaches every control.
  const tabKey = isWebKit ? 'Alt+Tab' : 'Tab';
  try {
    for (const [name, html] of Object.entries(pages)) {
      const page = await browser.newPage();
      page.setDefaultTimeout(5000);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      const fullShell = name.startsWith('shell-');
      await page.route('https://graf.test/**', route => {
        if (route.request().resourceType() !== 'document') {
          const filename = path.basename(new URL(route.request().url()).pathname);
          const asset = [assets, publicAssets].map(dir => path.join(dir, filename)).find(file => fs.existsSync(file) && fs.statSync(file).isFile());
          return asset ? route.fulfill({ path: asset }) : route.fulfill({ status: 204 });
        }
        return route.fulfill({
          contentType: 'text/html; charset=utf-8', body: fullShell ? html : `<html lang="ru"><meta charset="utf-8"><body data-surface-mode="standalone_browser">${html}</body></html>`,
        });
      });
      await page.goto('https://graf.test/billing');
      if (!fullShell) {
        await page.addStyleTag({ path: path.join(assets, 'cabinet.css') });
        await page.addScriptTag({ path: path.join(assets, 'cabinet.js') });
      }
      for (const link of await page.locator('.billing-page a:not(.button):visible').all()) {
        assert(await link.evaluate(el => getComputedStyle(el).textDecorationLine.includes('underline')), `${name}: text link distinguishable`);
      }
      const target = await page.getByRole('alert').count()
        ? page.getByRole('alert').first() : page.getByRole('heading', { level: 1 });
      if (name !== 'referrals') {
        assert(await target.evaluate(el => el === document.activeElement), `${name}: initial focus`);
      }
      await page.keyboard.press(tabKey);
      const focus = await page.evaluate(() => document.activeElement.outerHTML);
      assert(!focus.startsWith('<body'), `${name}: keyboard can leave initial focus`);
      await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap')));
      assert.equal(await page.evaluate(() => document.activeElement.outerHTML), focus, 're-init must not steal focus');
      if (name === 'packages') {
        const select = page.getByLabel('Общий объем хранения', { exact: true });
        await page.getByRole('button', {name: 'Выбрать больший объем'}).click();
        assert.equal(await select.inputValue(), '2');
        assert.match(await page.locator('#storage-package-summary').innerText(), /15 ГБ всего.*1500 ₽ за месяц/);
        await select.selectOption('0');
        assert(await page.getByRole('button', {name: 'Выбрать меньший объем'}).isDisabled());
        await select.selectOption('99');
        assert(await page.getByRole('button', {name: 'Выбрать больший объем'}).isDisabled());
        assert.match(await page.locator('#storage-package-summary').innerText(), /500 ГБ всего.*25750 ₽/);
        await select.selectOption('1');
        await page.getByRole('button', {name: 'Выбрать больший объем'}).focus();
        await page.keyboard.press('Space');
        assert.equal(await select.inputValue(), '2');
        const form = page.locator('form[action="/billing/storage/preview"]');
        assert.equal(await form.evaluate(el => new FormData(el).get('package_count')), '2');
        await select.selectOption('0');
        await select.locator('option[value="1"]').evaluate(el => el.remove());
        await page.getByRole('button', {name: 'Выбрать больший объем'}).click();
        assert.equal(await select.inputValue(), '2', 'skip unavailable catalog volume without promising a fixed step');
      }
      if (name === 'checkout' || name === 'error') {
        assert.equal(await page.locator('details.billing-coupon').evaluate(el => el.open), false);
        const form = page.locator('form[action="/billing/checkout/start"]');
        assert.equal(await form.evaluate(el => el.checkValidity()), false, 'empty consent prevents payment');
        const consents = page.getByRole('checkbox');
        assert.equal(await consents.count(), 2);
        for (let index = 0; index < 2; index++) {
          assert.equal(await consents.nth(index).isChecked(), false);
          await consents.nth(index).focus();
          await page.keyboard.press('Space');
          assert(await consents.nth(index).isChecked());
        }
        await page.keyboard.press(tabKey);
        assert(await page.getByRole('button', { name: /^Оплатить/ }).evaluate(el => el === document.activeElement));
        await page.keyboard.press(isWebKit ? 'Shift+Alt+Tab' : 'Shift+Tab');
        assert(await consents.nth(1).evaluate(el => el === document.activeElement));
        assert(await form.evaluate(el => el.checkValidity()), 'explicit consents permit submit');
      } else if (name.startsWith('status-')) {
        assert.equal(await page.getByRole('status').count(), 1, 'one payment status announcement region');
      } else if (name === 'invoice') {
        const help = page.locator('summary', { hasText: 'Помощь и возврат' });
        await help.focus();
        await page.keyboard.press('Space');
        assert(await page.getByText('Результат возврата уточняйте у поддержки:', { exact: false }).isVisible());
        assert(await page.getByRole('link', { name: 'Управлять автопродлением' }).isVisible());
      } else if (name === 'discounts-error') {
        const promo = page.getByRole('textbox', { name: 'Промокод', exact: true });
        assert.equal(await promo.inputValue(), 'DEMO');
        assert.equal(await promo.getAttribute('aria-invalid'), 'true');
        assert(await page.getByRole('alert').isVisible());
      } else if (name === 'subscription-expired-pending') {
        assert(await page.getByRole('button', { name: 'Отключить автопродление' }).isVisible());
        assert.equal(await page.getByRole('link', { name: 'Выбрать тариф' }).count(), 0);
        assert(await page.locator('a[href="/billing/checkout/status/INV-SYNTHETIC"]').isVisible());
      } else if (name === 'overview-expired-pending') {
        assert(await page.getByRole('link', { name: 'Управлять автопродлением' }).isVisible());
        assert(await page.getByRole('link', { name: 'Открыть статус платежа' }).isVisible());
        assert.equal(await page.locator('main .button.primary:visible').count(), 1);
      } else if (name === 'subscription-prepared') {
        assert(!(await page.locator('main').innerText()).includes('Уже отправленный платеж'));
        const early = page.locator('summary', { hasText: 'Оплатить следующий период заранее' });
        await early.focus();
        await page.keyboard.press('Space');
        assert(await page.locator('form[action="/billing/subscription/early-preview"]').isVisible());
      } else if (['storage_upgrade', 'early_renewal', 'storage_schedule', 'storage-price-confirmation'].includes(name)) {
        const consent = page.getByRole('checkbox');
        assert.equal(await consent.count(), 1, 'one-time purchase must not imply recurring consent');
        assert.equal(await consent.isChecked(), false);
        await consent.focus();
        await page.keyboard.press('Space');
        assert(await consent.isChecked());
        assert(await page.getByRole('button', { name: /^(Оплатить|Сохранить выбор)/ }).isVisible());
      }
      if (name.includes('discounts')) {
        const promo = page.getByRole('textbox', { name: 'Промокод', exact: true });
        assert(await promo.isVisible());
        await promo.focus();
        assert(await promo.evaluate(el => el === document.activeElement));
        await page.keyboard.press(tabKey);
        assert(await page.getByRole('button', { name: 'Применить и проверить цену' }).evaluate(el => el === document.activeElement));
        assert.equal(await page.getByText('Действующие предложения', { exact: true }).count(), 0);
        if (name.includes('history-year')) assert.match(await page.locator('[aria-label="История скидок"]').innerText(), /Применён · Год/);
        if (name.includes('history-unknown')) {
          const history = await page.locator('[aria-label="История скидок"]').innerText();
          assert(history.includes('Скидка 10%') && history.includes('Применён'));
          assert(!/Год|Месяц|·/.test(history));
        }
      }
      for (const width of [320, 360, 768, 1280]) {
        await page.setViewportSize({ width, height: 900 });
        for (const theme of ['light', 'dark']) {
          for (const zoom of [1, 2]) {
            await page.evaluate(({ theme, zoom }) => {
              document.documentElement.dataset.theme = theme;
              document.body.style.zoom = String(zoom);
            }, { theme, zoom });
            const overflow = await page.evaluate(() => {
              const main = document.querySelector('main');
              return main.scrollWidth > main.clientWidth + 1 ||
                document.documentElement.scrollWidth > window.innerWidth + 1;
            });
            assert(!overflow, `${name}: content clipped at ${width}px, ${theme}, ${zoom * 100}%`);
            const smallTargets = await page.evaluate(() => [...document.querySelectorAll(
              'main button, main .button, main summary, main select, main input[type=text], main label.billing-consent',
            )].filter(el => el.checkVisibility() && !el.matches(':disabled')).filter(el => {
              const rect = el.getBoundingClientRect();
              return rect.width < 24 || rect.height < 24;
            }).map(el => el.textContent.trim()));
            assert.deepEqual(smallTargets, [], `${name}: main control target size`);
            if (width === 1280 && zoom === 1) await checkTextContrast(page, `${name}, ${theme}`);
            if (visualDirectory && zoom === 1 && [320, 1280].includes(width)) {
              await page.screenshot({ path: path.join(visualDirectory, `${name}-${width}-${theme}.png`), fullPage: true });
            }
            const primary = page.locator('main .button.primary:visible').first();
            if (await primary.count()) {
              await primary.scrollIntoViewIfNeeded();
              const reachable = await primary.evaluate(el => {
                const rect = el.getBoundingClientRect();
                return rect.left >= -1 && rect.right <= innerWidth + 1 && rect.top >= -1 && rect.bottom <= innerHeight + 1;
              });
              assert(reachable, `${name}: primary action reachable at ${width}px, ${theme}, ${zoom * 100}%`);
              if (visualDirectory && zoom === 2 && width === 320 && name === 'shell-checkout') {
                await page.screenshot({ path: path.join(visualDirectory, `${name}-320-${theme}-200-action.png`) });
              }
              await page.locator('main').evaluate(el => el.scrollTop = 0);
            }
          }
        }
      }
      assert.deepEqual(errors, []);
      await page.close();
    }
    // Submit the actual native form with scripting disabled. The intercepted
    // request proves browser validation and serialization, not provider success.
    const noScriptPage = await browser.newPage({ javaScriptEnabled: false });
    noScriptPage.setDefaultTimeout(5000);
    const posts = [];
    await noScriptPage.route('https://graf.test/**', route => {
      const request = route.request();
      if (request.method() === 'POST') posts.push(request);
      return route.fulfill({contentType: 'text/html; charset=utf-8', body: request.method() === 'POST'
        ? '<meta charset="utf-8"><p>Синтетическая отправка принята</p>' : `<html lang="ru"><meta charset="utf-8"><body>${pages.checkout}</body></html>`});
    });
    await noScriptPage.goto('https://graf.test/billing/checkout');
    await noScriptPage.getByRole('button', {name: /^Оплатить/}).click();
    assert.equal(posts.length, 0, 'native validation blocks unchecked consents without JS');
    for (const checkbox of await noScriptPage.getByRole('checkbox').all()) await checkbox.check();
    await Promise.all([
      noScriptPage.waitForURL('https://graf.test/billing/checkout/start'),
      noScriptPage.getByRole('button', {name: /^Оплатить/}).click(),
    ]);
    assert.equal(posts.length, 1);
    const submitted = new URLSearchParams(posts[0].postData());
    assert.equal(submitted.get('quote_id'), 'synthetic-quote');
    assert.equal(submitted.get('cycle'), 'month');
    assert.equal(submitted.get('offer_consent'), 'true');
    assert.equal(submitted.get('recurring_consent'), 'true');
    await noScriptPage.close();
    console.log('billing: initial/error focus, native consent keyboard, no focus steal, single status region passed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
