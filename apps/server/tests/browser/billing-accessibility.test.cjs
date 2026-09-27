const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
const pages = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const [name, html] of Object.entries(pages)) {
      const page = await browser.newPage();
      page.setDefaultTimeout(5000);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('https://graf.test/**', route => route.fulfill({
        contentType: 'text/html; charset=utf-8', body: `<html lang="ru"><meta charset="utf-8"><body>${html}</body></html>`,
      }));
      await page.goto('https://graf.test/billing');
      await page.addStyleTag({ path: path.join(assets, 'cabinet.css') });
      await page.addScriptTag({ path: path.join(assets, 'cabinet.js') });
      const target = name === 'error' ? page.getByRole('alert') : page.getByRole('heading', { level: 1 });
      assert(await target.evaluate(el => el === document.activeElement), `${name}: initial focus`);
      await page.keyboard.press('Tab');
      const focus = await page.evaluate(() => document.activeElement.outerHTML);
      assert(!focus.startsWith('<body'), `${name}: keyboard can leave initial focus`);
      await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap')));
      assert.equal(await page.evaluate(() => document.activeElement.outerHTML), focus, 're-init must not steal focus');
      if (name === 'packages') {
        const select = page.getByLabel('Дополнительные пакеты по 5 ГБ');
        await page.getByRole('button', {name: 'Добавить один пакет 5 ГБ'}).click();
        assert.equal(await select.inputValue(), '2');
        assert.match(await page.locator('#storage-package-summary').innerText(), /15 ГБ всего.*500 ₽.*1500 ₽/);
        await select.selectOption('0');
        assert(await page.getByRole('button', {name: 'Убрать один пакет 5 ГБ'}).isDisabled());
        await select.selectOption('99');
        assert(await page.getByRole('button', {name: 'Добавить один пакет 5 ГБ'}).isDisabled());
        assert.match(await page.locator('#storage-package-summary').innerText(), /500 ГБ всего.*25750 ₽/);
        await select.selectOption('1');
        await page.getByRole('button', {name: 'Добавить один пакет 5 ГБ'}).focus();
        await page.keyboard.press('Space');
        assert.equal(await select.inputValue(), '2');
        const form = page.locator('form[action="/billing/storage/preview"]');
        assert.equal(await form.evaluate(el => new FormData(el).get('package_count')), '2');
      }
      if (name === 'checkout' || name === 'error') {
        const consents = page.getByRole('checkbox');
        assert.equal(await consents.count(), 2);
        for (let index = 0; index < 2; index++) {
          assert.equal(await consents.nth(index).isChecked(), false);
          await consents.nth(index).focus();
          await page.keyboard.press('Space');
          assert(await consents.nth(index).isChecked());
        }
        await page.keyboard.press('Tab');
        assert(await page.getByRole('button', { name: /^Оплатить/ }).evaluate(el => el === document.activeElement));
        await page.keyboard.press('Shift+Tab');
        assert(await consents.nth(1).evaluate(el => el === document.activeElement));
      } else if (name.startsWith('status-')) {
        assert.equal(await page.getByRole('status').count(), 1, 'one payment status announcement region');
      } else if (name !== 'packages') {
        const consent = page.getByRole('checkbox');
        assert.equal(await consent.count(), 1, 'one-time purchase must not imply recurring consent');
        assert.equal(await consent.isChecked(), false);
        await consent.focus();
        await page.keyboard.press('Space');
        assert(await consent.isChecked());
        assert(await page.getByRole('button', { name: /^(Оплатить|Сохранить выбор)/ }).isVisible());
      }
      for (const width of [360, 1280]) {
        await page.setViewportSize({ width, height: 900 });
        for (const theme of ['light', 'dark']) {
          for (const zoom of [1, 2]) {
            await page.evaluate(({ theme, zoom }) => {
              document.documentElement.dataset.theme = theme;
              document.body.style.zoom = String(zoom);
            }, { theme, zoom });
            const overflow = await page.evaluate(() => {
              const main = document.querySelector('main');
              return main.scrollWidth > main.clientWidth + 1;
            });
            assert(!overflow, `${name}: content clipped at ${width}px, ${theme}, ${zoom * 100}%`);
          }
        }
      }
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log('billing: initial/error focus, native consent keyboard, no focus steal, single status region passed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
