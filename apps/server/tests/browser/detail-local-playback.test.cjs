const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, webkit } = require('playwright');
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');

(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch({ headless: true });
  try {
    for (const platform of ['macos', 'windows']) {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('https://graf.test/**', route => route.fulfill({ contentType: 'text/html', body: '<body></body>' }));
      await page.goto('https://graf.test/desktop/meetings/meeting');
      await page.setContent('<main data-meeting-id="meeting"></main><section class="detail-playback" data-playback-state="ready"></section>');
      await page.evaluate(platform => { window.GRAFDesktopPlatform = platform; }, platform);
      await page.addScriptTag({ path: path.join(assets, 'user-time.js') });
      await page.addScriptTag({ path: path.join(assets, 'cabinet.js') });
      const button = page.getByRole('button', { name: platform === 'windows'
        ? 'Слушать запись с этого компьютера' : 'Слушать запись с этого Mac', exact: true });
      const row = { id: 'local-meeting', meetingId: 'MEETING', canOpen: true };
      const publish = rows => page.evaluate(rows => window.GRAFLocalRecordings.update(rows), rows);
      assert.equal(await button.count(), 0, 'no native inventory means no local action');
      await publish([row]);
      assert.equal(await button.count(), 1, 'matching native capability exposes one local action');
      assert.equal(await button.getAttribute('data-graf-local-recording-action'), 'open');
      assert.equal(await button.getAttribute('data-graf-local-recording-id'), row.id);
      await button.focus();
      await publish([row]);
      assert.equal(await button.count(), 1, 'repeated inventory does not duplicate the action');
      assert.equal(await button.evaluate(node => node === document.activeElement), true, 'unchanged action retains keyboard focus');
      await publish([{ ...row, canOpen: false }]);
      assert.equal(await button.count(), 0, 'revoked capability removes the action');
      await publish([{ ...row, meetingId: 'other' }]);
      assert.equal(await button.count(), 0, 'another meeting cannot supply local playback');
      for (const state of ['deleting', 'deleted']) {
        await page.locator('.detail-playback').evaluate((node, state) => { node.dataset.playbackState = state; }, state);
        await publish([row]);
        assert.equal(await button.count(), 0, `${state} blocks the action`);
      }
      await page.locator('.detail-playback').evaluate(node => { node.dataset.playbackState = 'ready'; node.dataset.playbackReason = 'access_denied'; });
      await publish([row]);
      assert.equal(await button.count(), 0, 'denied access blocks the action');
      await page.locator('.detail-playback').evaluate(node => { delete node.dataset.playbackReason; });
      await publish([row]);
      await page.evaluate(() => {
        const playback = document.querySelector('.detail-playback');
        playback.replaceWith(playback.cloneNode(false));
        document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', { detail: { target: document.querySelector('.detail-playback') } }));
      });
      assert.equal(await button.count(), 1, 'HTMX replacement restores the local action');
      await publish([]);
      assert.equal(await button.count(), 0, 'removed native row revokes the action');
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log('PASS: shared detail local playback uses platform copy, current native capabilities and HTMX reconciliation');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
