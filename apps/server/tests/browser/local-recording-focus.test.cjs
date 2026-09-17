// Run with NODE_PATH pointing at the existing Playwright installation.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('https://synthetic.invalid/**', route => route.fulfill({contentType:'text/html', body:'<html></html>'}));
    await page.goto('https://synthetic.invalid/meetings');
    await page.setContent(`<meta name="graf-timezone" content="UTC"><meta name="graf-time-reload" content="false">
      <h1 data-list-title tabindex="-1">Встречи</h1><input id="meeting-search">
      <select id="meeting-sort"><option value="started_desc">Дата</option><option value="updated_desc">Обновление</option><option value="title_asc">Название</option></select>
      <div data-selection-toolbar hidden><span data-selection-count></span></div>
      <div id="meeting-list-region"><div data-meeting-result-count></div><section data-meeting-list><ol class="meeting-list">
      <li data-meeting-row data-meeting-id="server-a" data-sort-started="2026-09-05T20:30:00Z"><input type="checkbox" data-meeting-select><button data-meeting-open>Server A</button></li>
      </ol></section></div>`);
    await page.addScriptTag({path:path.join(assets,'user-time.js')});
    await page.addScriptTag({path:path.join(assets,'cabinet.js')});
    const local = {id:'local-a', title:'Local A', generatedTitlePrefix:'Запись — ', startedAt:'2026-09-05T21:30:00Z', updatedAt:'2026-09-06T00:30:00Z', durationSeconds:60, status:'Ожидает отправки', canOpen:true, canSend:true, canDelete:true};
    const publish = (items = [local]) => page.evaluate(items => window.GRAFLocalRecordings.update(items), items);
    await publish();
    await page.evaluate(() => {
      window.GRAFRecordingDeletionBridgeVersion = 1;
      window.localKeyboardOpenClicks = 0;
      document.addEventListener('click', event => {
        if (event.target.closest('[data-graf-local-recording-action="open"]')) window.localKeyboardOpenClicks++;
      });
      window.webkit = {messageHandlers:{grafLocalRecording:{postMessage() {}}}};
      document.body.insertAdjacentHTML('beforeend', '<dialog data-delete-dialog data-title-one="Удаление" data-title-many="Удаление"><h2 data-delete-title></h2><p data-delete-count></p><p data-delete-error hidden></p><button data-delete-cancel>Отмена</button><button data-delete-confirm>Удалить</button></dialog>');
    });
    const keyboardCheckbox = page.locator('[data-graf-local-recording-row] [data-meeting-select]');
    await keyboardCheckbox.focus();
    await page.keyboard.press('Space');
    assert.equal(await keyboardCheckbox.isChecked(), true, 'Space selects the local recording');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('[data-graf-local-recording-action="open"]').evaluate(node => node === document.activeElement), true);
    await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(() => window.localKeyboardOpenClicks), 1, 'Enter activates the local open control');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-row-delete]').evaluate(node => node === document.activeElement), true);
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('[data-delete-dialog]').evaluate(node => node.open), true);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('[data-delete-dialog]').evaluate(node => node.open), false);
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-row-delete]').evaluate(node => node === document.activeElement), true, 'Escape restores the initiating delete button');
    await keyboardCheckbox.focus();
    await page.keyboard.press('Space');
    assert.equal(await keyboardCheckbox.isChecked(), false);
    await page.evaluate(() => {
      window.localListMoves = 0;
      window.localListObserver = new MutationObserver(records => { window.localListMoves += records.length; });
      window.localListObserver.observe(document.querySelector('ol.meeting-list'), {childList:true});
    });
    for (const selector of ['[data-meeting-select]', '[data-graf-local-recording-action="open"]', '[data-graf-local-recording-action="send"]', '[data-row-delete]']) {
      const control = page.locator(`[data-graf-local-recording-row] ${selector}`);
      await control.focus();
      await page.evaluate(() => {
        window.localListMoves = 0;
        window.originalFocusedControl = document.activeElement;
        window.originalLocalRow = document.activeElement.closest('[data-meeting-row]');
      });
      for (let iteration = 0; iteration < 20; iteration++) await publish();
      assert.equal(await page.evaluate(() => window.originalFocusedControl === document.activeElement),true,`${selector}: identical publications retain the focused node`);
      assert.equal(await page.evaluate(() => window.originalLocalRow === document.querySelector('[data-graf-local-recording-row]')),true,'unchanged native row is reused');
      assert.equal(await page.evaluate(() => window.localListMoves),0,'already sorted rows are not detached and appended again');
    }
    await page.evaluate(() => window.localListObserver.disconnect());
    await page.locator('[data-graf-local-recording-row] [data-meeting-select]').check();
    await page.locator('[data-graf-local-recording-row] [data-meeting-select]').focus();
    await publish([{...local, status:'Повторная отправка'}]);
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-meeting-select]').evaluate(node => node === document.activeElement),true,'changed status keeps checkbox focus');
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-meeting-select]').isChecked(),true);
    assert.equal(await page.locator('[data-graf-local-recording-row] .row-meta').textContent(),'Повторная отправка');
    await page.locator('[data-graf-local-recording-action="send"]').focus();
    await publish([{...local, canSend:false}]);
    assert.equal(await page.locator('[data-graf-local-recording-action="open"]').evaluate(node => node === document.activeElement),true,'removed action falls back to an available action');
    await page.locator('[data-graf-local-recording-row] [data-meeting-select]').focus();
    await publish([{...local, meetingId:'server-a'}]);
    assert.equal(await page.locator('[data-meeting-id="server-a"] [data-meeting-select]').evaluate(node => node === document.activeElement),true,'server handoff preserves checkbox intent');
    assert.equal(await page.locator('[data-meeting-id="server-a"] [data-meeting-select]').isChecked(),true);
    await publish();
    await page.locator('[data-graf-local-recording-action="open"]').focus();
    const oldDate = await page.locator('[data-graf-local-recording-row] time').textContent();
    await page.selectOption('#meeting-sort','updated_desc');
    await publish();
    assert.notEqual(await page.locator('[data-graf-local-recording-row] time').textContent(),oldDate,'sort context must update rendered time');
    await page.locator('[data-graf-local-recording-action="open"]').focus();
    await page.evaluate(() => { document.querySelector('meta[name="graf-timezone"]').content = 'Asia/Yekaterinburg'; });
    await page.addScriptTag({path:path.join(assets,'user-time.js')});
    await publish();
    assert.match(await page.locator('[data-graf-local-recording-row] time').textContent(),/05:30/,'timezone changes invalidate the rendered row');
    assert.match(await page.locator('[data-graf-local-recording-row] .meeting-title').textContent(),/02:30/,'generated title follows timezone too');
    await page.locator('[data-graf-local-recording-action="open"]').focus();
    await page.evaluate(() => { document.querySelector('#meeting-search').value = 'no-matching-local-recording'; });
    await publish();
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(),0);
    assert.equal(await page.evaluate(() => document.activeElement.isConnected && document.activeElement !== document.body),true,'filtered focused row uses a connected fallback');
    await page.evaluate(() => { document.querySelector('#meeting-search').value = ''; });
    await publish();
    await page.locator('[data-graf-local-recording-row] [data-row-delete]').focus();
    await publish([]);
    assert.equal(await page.evaluate(() => document.activeElement.isConnected && document.activeElement !== document.body),true,'removed focused row uses a connected fallback');
    assert.deepEqual(errors,[]);
    console.log('local recording focus: stable keyed nodes, changed controls, checkbox handoff, time context and safe removal PASS');
  } finally { await browser.close(); }
})();
