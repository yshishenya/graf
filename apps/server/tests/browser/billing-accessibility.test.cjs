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
      } else {
        assert.equal(await page.getByRole('status').count(), 1, 'one payment status announcement region');
      }
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log('billing: initial/error focus, native consent keyboard, no focus steal, single status region passed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
