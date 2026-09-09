// Run with NODE_PATH pointing at the existing Playwright installation.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ timezoneId: 'Asia/Yekaterinburg' });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('https://synthetic.invalid/**', (route) => route.fulfill({ contentType: 'text/html', body: '<html><body></body></html>' }));
    await page.goto('https://synthetic.invalid/meetings');
    await page.setContent(`<meta name="graf-timezone" content="Asia/Yekaterinburg"><meta name="graf-time-reload" content="false">
      <input id="meeting-search"><select id="meeting-access"><option value="">Все</option><option value="owner">Мои</option><option value="team">Команда</option></select>
      <select id="meeting-status"><option value="">Все</option><option value="ready">Готовые</option></select>
      <select id="meeting-sort">${['started_desc','started_asc','updated_desc','updated_asc','duration_desc','duration_asc','title_asc'].map(s=>`<option>${s}</option>`).join('')}</select>
      <div id="meeting-list-region"><div data-meeting-result-count>Найдено: 2</div><div data-meeting-result-complete="true"><section data-meeting-list><ol class="meeting-list">
      <li data-meeting-row data-meeting-id="server-a" data-sort-title="Альфа" data-sort-started="2026-09-05T20:30:00Z" data-sort-updated="2026-09-06T10:00:00Z" data-sort-duration="120">Альфа</li>
      <li data-meeting-row data-meeting-id="server-z" data-sort-title="Январь" data-sort-started="2026-09-05T22:30:00Z" data-sort-updated="2026-09-06T09:00:00Z" data-sort-duration="30">Январь</li>
      </ol></section></div></div>`);
    await page.addScriptTag({ path: path.join(assets, 'user-time.js') });
    await page.addScriptTag({ path: path.join(assets, 'cabinet.js') });
    const local = { id:'local-b', title:'Бета', startedAt:'2026-09-05T21:30:00Z', durationSeconds:60, status:'Ожидает отправки', canOpen:true, canDelete:true, uploadComplete:false };
    const order = () => page.locator('[data-meeting-row]').evaluateAll(rows=>rows.map(row=>row.dataset.meetingId || row.dataset.grafLocalRecordingId));
    const update = (rows = [local]) => page.evaluate(rows=>window.GRAFLocalRecordings.update(rows),rows);
    const expected = {
      started_desc:['server-z','local-b','server-a'], started_asc:['server-a','local-b','server-z'],
      updated_desc:['server-a','server-z','local-b'], updated_asc:['server-z','server-a','local-b'],
      duration_desc:['server-a','local-b','server-z'], duration_asc:['server-z','local-b','server-a'],
      title_asc:['server-a','local-b','server-z'],
    };
    for (const [sort, ids] of Object.entries(expected)) {
      await page.selectOption('#meeting-sort',sort);
      await update();
      assert.deepEqual(await order(),ids,sort);
      await update();
      assert.deepEqual(await order(),ids,`${sort} stable update`);
    }
    assert.equal(await page.locator('[data-graf-local-recording-row] time').textContent(),'06.09.2026, 02:30');
    assert.equal(await page.locator('[data-graf-local-recording-row] time').getAttribute('datetime'),local.startedAt);
    assert.equal(await page.locator('[data-graf-local-recording-row] .meeting-title').getAttribute('aria-describedby'),'graf-local-time-local-b');
    await page.fill('#meeting-search','06.09.2026'); await update();
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(),1);
    await page.fill('#meeting-search','05.09.2026'); await update();
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(),0);
    assert.equal(await page.locator('[data-meeting-result-count]').textContent(),'Найдено: 2');
    await page.fill('#meeting-search','');
    await page.selectOption('#meeting-access','team'); await update();
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(),0);
    await page.selectOption('#meeting-access','owner'); await update();
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(),1);
    await page.selectOption('#meeting-status','ready'); await update();
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(),0);
    await page.selectOption('#meeting-status','');
    await update([{...local, meetingId:'server-a',uploadComplete:true}]);
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(),0);
    // An absent server row (deletion, filters or pagination) cannot resurrect a local alias.
    const retainedServerRow = await page.locator('[data-meeting-id="server-a"]').evaluate(row => { const html = row.outerHTML; row.remove(); return html; });
    await update([{...local, meetingId:'server-a',uploadComplete:true}]);
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(),0);
    await update([{...local, meetingId:'not-on-this-page',uploadComplete:false}]);
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(),0);
    await update([local]);
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-meeting-select]').count(),1);
    await update([{...local, canDelete:false, canOpen:false}]);
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-meeting-select]').isDisabled(),true);
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-meeting-open]').count(),0);
    await page.locator("ol.meeting-list").evaluate((list, html) => list.insertAdjacentHTML("beforeend", html), retainedServerRow);
    // Equal instants are ordered by stable IDs regardless of incoming array order.
    await page.selectOption('#meeting-sort','started_asc');
    await update([{...local,id:'local-c'},{...local,id:'local-b',startedAt:'2026-09-06T00:30:00+03:00'}]);
    assert.deepEqual(await order(),['server-a','local-b','local-c','server-z']);
    // An HTML-fragment replacement re-applies the same local projection.
    await page.evaluate(()=>document.body.dispatchEvent(new CustomEvent('htmx:afterSwap',{detail:{target:document.querySelector('#meeting-list-region')}})));
    assert.deepEqual(await order(),['server-a','local-b','local-c','server-z']);
    await update([{...local,title:'Meeting - 2026-09-05 21:30'}]);
    assert.equal(await page.locator('[data-graf-local-recording-row] .meeting-title').textContent(),'Запись 06.09.2026, 02:30');
    // Native generated titles follow the selected display zone even if cookies are blocked.
    await page.evaluate(() => {
      document.querySelector('meta[name="graf-timezone"]').content = 'UTC';
      Object.defineProperty(document, 'cookie', {get: () => '', set: () => {}});
    });
    await page.addScriptTag({ path: path.join(assets, 'user-time.js') });
    await update([{...local,title:'Zoom — 06.09.2026, 02:30',generatedTitlePrefix:'Zoom — '}]);
    assert.equal(await page.locator('[data-graf-local-recording-row] .meeting-title').textContent(),'Zoom — 05.09.2026, 21:30 (UTC)');
    assert.equal(await page.locator('[data-graf-local-recording-row] time').textContent(),'05.09.2026, 21:30 (UTC)');
    // Selection and focus follow the local alias when its server row arrives.
    await page.evaluate(() => {
      document.body.insertAdjacentHTML('beforeend', '<h1 data-list-title tabindex="-1">Встречи</h1><div data-selection-toolbar><span data-selection-count></span><button data-selection-delete>Удалить выбранные</button></div><div id="delete-feedback-region"></div><div data-meeting-result-announcer></div><dialog data-delete-dialog data-title-one="Удаление" data-title-many="Удаление"><h2 data-delete-title></h2><p data-delete-count></p><p data-delete-error hidden></p><button data-delete-cancel>Отмена</button><button data-delete-confirm>Удалить</button></dialog>');
      for (const row of document.querySelectorAll('[data-meeting-id]')) row.insertAdjacentHTML('beforeend', '<input type="checkbox" data-meeting-select><button data-meeting-open>Открыть</button><span class="row-meta"></span>');
    });
    await update([local]);
    await page.locator('[data-graf-local-recording-row] [data-meeting-select]').check();
    await page.locator('[data-graf-local-recording-row] [data-graf-local-recording-action="open"]').focus();
    await update([{...local,meetingId:'server-a'}]);
    assert.equal(await page.locator('[data-meeting-id="server-a"] [data-meeting-select]').isChecked(),true);
    assert.equal(await page.locator('[data-meeting-id="server-a"] [data-meeting-open]').evaluate(node => node === document.activeElement),true);
    const operation = {id:'synthetic-operation', target:{meeting:{_0:'server-a'}}, phase:'sending'};
    await page.evaluate(op => window.GRAFLocalRecordings.update([], [op]), operation);
    assert.equal(await page.locator('[data-meeting-id="server-a"] input').isDisabled(),true);
    await page.evaluate(op => window.GRAFLocalRecordings.update([], [{...op,phase:'accepted'}]), operation);
    assert.equal(await page.locator('[data-meeting-id="server-a"]').count(),0);
    await page.locator('ol.meeting-list').evaluate((list,html) => list.insertAdjacentHTML('beforeend',html),retainedServerRow);
    await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap',{detail:{target:document.querySelector('#meeting-list-region')}})));
    assert.equal(await page.locator('[data-meeting-id="server-a"]').count(),0,'stale HTML cannot resurrect accepted deletion');
    // Native bulk keeps a frozen selection and reports accepted/pending/rejected separately.
    await update([local]);
    await page.locator('[data-graf-local-recording-row] [data-meeting-select]').check();
    await page.locator('[data-selection-delete]').click();
    await page.locator('[data-delete-confirm]').click();
    assert.match(await page.locator('[data-delete-error]').textContent(),/обновите приложение GRAF/);
    await page.locator('[data-delete-cancel]').click();
    await page.evaluate(() => {
      window.GRAFRecordingDeletionBridgeVersion = 1;
      window.webkit = {messageHandlers:{grafLocalRecording:{postMessage(message) {
        window.syntheticDeletionRequest = message;
        window.GRAFLocalRecordings.deletionCompleted(message.requestId,{saved:true,accepted:0,pending:1,rejected:0});
      }}}};
    });
    await page.locator('[data-selection-delete]').click();
    await page.locator('[data-delete-confirm]').click();
    assert.deepEqual(await page.evaluate(() => window.syntheticDeletionRequest.localIds),['local-b']);
    assert.equal(await page.locator('[data-delete-dialog]').evaluate(node => node.open),false);
    assert.match(await page.locator('#delete-feedback-region').textContent(),/Ожидают подтверждения: 1/);
    await page.evaluate(() => window.GRAFLocalRecordings.update([], [], true));
    assert.match(await page.locator('[data-local-account-recovery]').textContent(),/аккаунт не подтверждён/);
    await page.evaluate(() => window.GRAFLocalRecordings.update([], [], false));
    assert.equal(await page.locator('[data-local-account-recovery]').count(),0);
    assert.deepEqual(errors,[]);
    console.log('mixed meeting list: seven sorts, stable ties, filters, dates, upload handoff and HTMX passed');
  } finally { await browser.close(); }
})().catch(error=>{ console.error(error); process.exitCode=1; });
