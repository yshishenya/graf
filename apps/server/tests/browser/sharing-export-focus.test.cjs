const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium, webkit} = require(require.resolve('playwright', {paths:[process.env.GRAF_NODE_MODULES || process.cwd()]}));
const script = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js');

(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch({headless:true});
  try {
    for (const mode of ['standalone', 'sharing', 'sharing-failure']) {
      const page = await browser.newPage();
      page.setDefaultTimeout(5000);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('https://graf.test/**', route => {
        if (route.request().method() === 'POST') return route.fulfill(mode === 'sharing-failure'
          ? {status:503, json:{code:'export_generation_failed'}}
          : {contentType:'text/plain', headers:{'Content-Disposition':'attachment; filename="synthetic.txt"'}, body:'Synthetic export'});
        return route.fulfill({contentType:'text/html', body:`<meta charset="utf-8">
          <main class="detail-page-main">
            <button data-meeting-panel-open="more">Ещё</button>
            <button data-export-dialog-open>Экспорт</button>
            <dialog data-content-export-dialog>
              <h2 tabindex="-1" data-export-dialog-title>Экспорт</h2>
              <form data-content-export-form data-endpoint="/export" data-export-delivery="save"
                data-export-formats-transcript="txt" data-processing-result-id="synthetic">
                <select data-export-scope><option value="transcript">Расшифровка</option></select>
                <select data-export-format><option value="txt">TXT</option></select>
                <p data-export-status></p><button data-export-submit>Сохранить</button>
              </form>
            </dialog>
            <dialog id="sharing"><h2>Поделиться</h2></dialog>
          </main>`});
      });
      await page.goto('https://graf.test/export');
      await page.addScriptTag({content:fs.readFileSync(script, 'utf8')});
      if (mode === 'standalone') await page.locator('[data-export-dialog-open]').click();
      else await page.evaluate(() => {
        const sharing = document.querySelector('#sharing');
        sharing.append(document.querySelector('[data-content-export-form]'));
        sharing.show();
      });
      await page.locator('[data-export-submit]').click();
      await page.locator(`[data-export-status][data-state=${mode === 'sharing-failure' ? 'error' : 'success'}]`).waitFor({state:'attached'});
      if (mode === 'standalone') {
        assert.equal(await page.locator('[data-content-export-dialog]').evaluate(el => el.open), false);
        assert.equal(await page.locator('[data-export-dialog-open]').evaluate(el => el === document.activeElement), true);
      } else {
        assert.equal(await page.locator('#sharing').evaluate(el => el.open), true);
        assert.equal(await page.locator('[data-export-submit]').evaluate(el => el === document.activeElement), true,
          `${mode}: export must retain focus inside the dialog that owns the reused form`);
      }
      assert.deepEqual(errors, []);
      await page.close();
      console.log(`${mode}: export focus PASS`);
    }
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
