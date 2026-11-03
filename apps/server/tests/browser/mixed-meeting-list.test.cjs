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
    // Missing/invalid native metadata is unknown, not a measured zero.
    const zero = {...local, id:'local-0', title:'Нулевая', durationSeconds:0};
    const localIds = () => page.locator('[data-graf-local-recording-row]').evaluateAll(rows => rows.map(row => row.dataset.grafLocalRecordingId));
    const unknownRow = page.locator('[data-graf-local-recording-id="local-u"][data-graf-local-recording-row]');
    for (const value of [undefined, null, false, -1, '60', NaN, Infinity]) {
      const unknown = {...local, id:'local-u', title:'Неизмерено', showsPartialDuration:true, sessionDurationSeconds:120};
      delete unknown.durationSeconds;
      delete unknown.startedAt;
      if (value !== undefined) unknown.durationSeconds = value;
      await update([unknown, local, zero]);
      assert.equal(await unknownRow.locator('.meeting-duration').textContent(), 'Длительность неизвестна', `unknown duration: ${value}`);
      assert.equal(await unknownRow.getAttribute('data-sort-duration'), '', 'unknown sort key is absent, not zero');
      assert.equal(await page.locator('[data-graf-local-recording-id="local-0"] .meeting-duration').textContent(), '0 с', 'measured zero stays known');
      for (const [sort, ids] of [
        ['duration_asc', ['local-0','server-z','local-b','server-a','local-u']],
        ['duration_desc', ['server-a','local-b','server-z','local-0','local-u']],
      ]) {
        await page.locator('#meeting-sort').selectOption(sort);
        await update([unknown, zero, local]);
        assert.deepEqual(await order(), ids, `${sort}: unknown last (${value})`);
      }
      await page.getByRole('textbox').fill('0 с'); await update([unknown, local, zero]);
      assert.deepEqual(await localIds(), ['local-0'], 'unknown is not searchable as zero');
      await page.getByRole('textbox').fill('1 мин'); await update([unknown, local, zero]);
      assert.deepEqual(await localIds(), ['local-b'], 'invalid numeric string is not a measured minute');
      await page.getByRole('textbox').fill('Неизмерено'); await update([unknown, local, zero]);
      assert.deepEqual(await localIds(), ['local-u'], 'unknown row remains searchable by its title');
      await page.getByRole('textbox').fill('');
    }
    await update([{...local, durationSeconds:30, sessionDurationSeconds:120, showsPartialDuration:true}]);
    assert.equal(await page.locator('[data-graf-local-recording-row] .meeting-duration').textContent(), 'Сохранено 30 с из 2 мин', 'known Mac partial duration is unchanged');
    await update([{...local, showsPartialDuration:true}]);
    assert.equal(await page.locator('[data-graf-local-recording-row] .meeting-duration').textContent(), '1 мин', 'partial label needs both measured lengths');
    await update([{...local, durationSeconds:undefined}]);
    assert.equal(await page.locator('[data-graf-local-recording-row] .meeting-duration').textContent(), 'Длительность неизвестна', 'same-id refresh revokes the old duration');
    await page.locator('#meeting-sort').selectOption('title_asc'); await update();
    assert.equal(await page.locator('[data-graf-local-recording-row] .meeting-duration').textContent(), '1 мин', 'known duration restores on refresh');
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
    // A background rejection refreshes the list through the real form submission path.
    await page.evaluate(() => {
      const form = document.createElement('form'); form.className = 'cabinet-list-controls';
      form.addEventListener('submit', event => {
        event.preventDefault(); window.rejectionRefreshCount = (window.rejectionRefreshCount || 0) + 1;
        const row = document.querySelector('[data-meeting-id="server-a"]');
        row.querySelectorAll('input,button').forEach(control => { control.disabled = false; });
        row.querySelector('.row-meta').textContent = 'Доступно';
      });
      document.body.append(form);
    });
    await page.evaluate(op => window.GRAFLocalRecordings.update([], [{...op,phase:'rejected'}]), operation);
    assert.equal(await page.evaluate(() => window.rejectionRefreshCount),1);
    assert.equal(await page.locator('[data-meeting-id="server-a"] input').isDisabled(),false);
    await page.evaluate(op => window.GRAFLocalRecordings.update([], [{...op,phase:'rejected'}]), operation);
    assert.equal(await page.evaluate(() => window.rejectionRefreshCount),1,'no refresh storm for unchanged rejection');
    await page.locator('form.cabinet-list-controls').evaluate(form => form.remove());
    await page.evaluate(op => window.GRAFLocalRecordings.update([], [op]), operation);
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
    await page.evaluate(() => { window.GRAFDesktopPlatform = 'windows'; window.GRAFLocalRecordings.update([
      {id:'protected-unknown',title:'Запись',status:'Ожидает отправки',canOpen:false,canSend:false,canDelete:false}
    ], [], false); });
    assert.equal(await page.locator('[data-graf-local-recording-row] time').textContent(), 'На этом компьютере', 'protected inventory has no recording date');
    assert.equal(await page.locator('[data-graf-local-recording-row] .meeting-duration').textContent(), 'Длительность неизвестна');
    assert.equal(await page.locator('[data-graf-local-recording-row] button').count(), 0, 'no unimplemented actions');
    await page.getByRole('textbox').fill('На этом компьютере');
    await page.evaluate(() => window.GRAFLocalRecordings.update([{id:'protected-unknown',title:'Запись'}]));
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(), 1, 'search uses the displayed unknown-date label');
    await page.getByRole('textbox').fill('');
    for (const state of ['checking','unavailable',null,42,'unknown']) {
      await page.evaluate(state => window.GRAFLocalRecordings.update([], [], false, state), state);
      assert.match(await page.locator('[data-local-inventory-state]').textContent(), state === 'checking' ? /проверяются/ : /Не удалось/);
      assert.match(await page.locator('[data-meeting-result-count]').textContent(), /локальные записи/);
    }
    await page.evaluate(() => window.GRAFLocalRecordings.update([], [], false));
    assert.equal(await page.locator('[data-local-inventory-state]').count(), 0, 'existing Mac call defaults to ready');
    const serverMarkup = await page.locator('ol.meeting-list').innerHTML();
    await page.locator('ol.meeting-list').evaluate(list => { list.innerHTML = ''; list.insertAdjacentHTML('afterend', '<p class="empty-state">Записей пока нет.</p>'); });
    for (const state of ['ready', 'checking', 'unavailable', 'ready']) {
      await page.evaluate(state => window.GRAFLocalRecordings.update([{id:'synthetic-only',title:'Запись'}],[],false,state), state);
      assert.equal(await page.locator('.empty-state:visible').count(), 0, 'local rows never coexist with healthy empty state');
      await page.evaluate(state => window.GRAFLocalRecordings.update([],[],false,state), state);
      assert.equal(await page.locator('.empty-state:visible').count(), state === 'ready' ? 1 : 0, 'empty success only after complete ready');
    }
    await page.locator('ol.meeting-list').evaluate((list, markup) => { list.innerHTML = markup; }, serverMarkup);
    await page.evaluate(() => window.GRAFLocalRecordings.update([],[],false));
    await page.evaluate(() => { delete window.GRAFDesktopPlatform; });
    await page.evaluate(() => window.GRAFLocalRecordings.update([], [], true));
    assert.match(await page.locator('[data-local-account-recovery]').textContent(),/аккаунт не подтвержден/);
    await page.evaluate(() => window.GRAFLocalRecordings.update([], [], false));
    assert.equal(await page.locator('[data-local-account-recovery]').count(),0);
    // A completed manual upload is another view of the same meeting, not a permanent link.
    await page.reload();
    await page.setContent(`<meta name="csrf-token" content="synthetic-csrf">
      <div id="meeting-list-region"></div><div data-upload-activity-announcer></div>
      <dialog data-manual-upload-dialog data-upload-available="true">
      <form data-manual-upload-form><input type="file" data-manual-upload-file>
      <input data-manual-upload-title><input data-manual-upload-duration><input data-manual-upload-local-id>
      <input type="checkbox" data-manual-upload-archive checked><button data-manual-upload-submit>Загрузить</button></form></dialog>`);
    await page.evaluate(() => {
      window.XMLHttpRequest = class {
        upload = {}; status = 200;
        responseText = JSON.stringify({meeting:{meeting_id:'00000000-0000-0000-0000-000000000262'},workflow_started:true});
        open() {} setRequestHeader() {} getResponseHeader() { return ''; }
        send() { window.pendingSyntheticUpload = this; this.onload(); }
      };
    });
    await page.addScriptTag({path:path.join(assets,'cabinet.js')});
    const wav = Buffer.alloc(44 + 16000 * 2);
    wav.write('RIFF'); wav.writeUInt32LE(wav.length-8,4); wav.write('WAVEfmt ',8);
    wav.writeUInt32LE(16,16); wav.writeUInt16LE(1,20); wav.writeUInt16LE(1,22);
    wav.writeUInt32LE(16000,24); wav.writeUInt32LE(32000,28); wav.writeUInt16LE(2,32); wav.writeUInt16LE(16,34);
    wav.write('data',36); wav.writeUInt32LE(wav.length-44,40);
    await page.locator('[data-manual-upload-file]').setInputFiles({name:'F262.wav',mimeType:'audio/wav',buffer:wav});
    await page.waitForFunction(() => document.querySelector('[data-manual-upload-duration]').value === '1');
    await page.locator('[data-manual-upload-dialog]').evaluate(dialog => dialog.showModal());
    await page.locator('[data-manual-upload-submit]').click();
    assert.equal(await page.locator('[data-upload-activity-detail]').getAttribute('href'),'/meetings/00000000-0000-0000-0000-000000000262');
    await page.evaluate(() => window.GRAFLocalRecordings.update([], [{id:'manual-delete',phase:'accepted',target:{meeting:{_0:'00000000-0000-0000-0000-000000000262'}}}]));
    assert.equal(await page.locator('[data-upload-activity-row]').count(),0);
    assert.equal(await page.locator('[data-upload-activity-announcer]').textContent(),'');
    assert.deepEqual(errors,[]);
    console.log('mixed meeting list: seven sorts, stable ties, filters, dates, upload handoff and HTMX passed');
  } finally { await browser.close(); }
})().catch(error=>{ console.error(error); process.exitCode=1; });
