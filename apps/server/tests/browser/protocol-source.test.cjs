const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const asset = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
  try {
    for (const source of ['segment-current', 'segment-old']) {
      const page = await browser.newPage();
      await page.route('https://graf.test/**', route => route.fulfill({
        contentType: 'text/html', body: `<meta charset="utf-8">
          <button data-detail-tab="outcomes">Итоги</button><button data-detail-tab="recording">Расшифровка</button>
          <section data-detail-panel="outcomes">Полный протокол</section>
          <section data-detail-panel="recording" hidden>
            <article data-transcript-turn data-source-segments="segment-current" data-start-seconds="12.25" data-end-seconds="20" tabindex="-1">Проверяемый фрагмент</article>
          </section><p data-playback-live-status role="status"></p>`,
      }));
      await page.goto(`https://graf.test/meetings/synthetic#graf-source=${source}`);
      await page.addScriptTag({ path: asset });
      if (source === 'segment-current') {
        await page.waitForFunction(() => document.activeElement.hasAttribute('data-transcript-turn'));
        assert.equal(await page.locator('[data-detail-panel="recording"]').isVisible(), true);
        assert.match(await page.locator('[data-playback-live-status]').textContent(), /00:12/);
      } else {
        assert.match(await page.locator('[data-playback-live-status]').textContent(), /ревизии недоступен/);
        assert.equal(await page.locator('[data-transcript-turn]').isVisible(), false);
      }
      await page.close();
    }
    console.log('PASS: exact protocol source; stale reference never jumps to another revision');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
