// Run with NODE_PATH pointing at the existing Playwright installation.
const { chromium, webkit } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch({ headless: true });
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
    await update([{...local, canDelete:true, canOpen:false}]);
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-meeting-select]').isEnabled(),true);
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-meeting-open]').count(),0);
    await update([{...local, canDelete:false, canOpen:true}]);
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-meeting-select]').isDisabled(),true);
    assert.equal(await page.locator('[data-graf-local-recording-row] [data-meeting-open]').count(),1);
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
    await page.evaluate(() => {
      window.GRAFRecordingDeletionBridgeVersion = 1;
      window.aliasDeletionMessages = [];
      window.webkit = {messageHandlers:{grafLocalRecording:{postMessage(message) {
        if (message.action !== 'deleteSelection') return;
        window.aliasDeletionMessages.push(message);
        window.GRAFLocalRecordings.deletionCompleted(message.requestId,{saved:true,accepted:0,pending:1,rejected:0});
      }}}};
    });
    await page.locator('[data-selection-delete]').click();
    await page.locator('[data-delete-confirm]').click();
    const aliasMessages = await page.evaluate(() => window.aliasDeletionMessages);
    assert.equal(aliasMessages.length,1,'handoff produces one bridge command');
    assert.deepEqual(aliasMessages[0].localIds,[]);
    assert.deepEqual(aliasMessages[0].meetingIds,['server-a']);
    await page.evaluate(() => { delete window.GRAFRecordingDeletionBridgeVersion; delete window.webkit; });
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
    // Multiple accepted deletions keep the visible count and selection coherent.
    const aliases = [local, {...local,id:'alias-a',meetingId:'server-a',uploadComplete:true}, {...local,id:'alias-z',meetingId:'server-z',uploadComplete:true}];
    await update(aliases);
    const staleRows = await page.locator('[data-meeting-id]').evaluateAll(rows => rows.map(row => row.outerHTML).join(''));
    for (const checkbox of await page.locator('[data-meeting-id] [data-meeting-select]').all()) await checkbox.check();
    assert.equal(await page.locator('[data-meeting-result-count]').textContent(),'Найдено: 3');
    assert.equal(await page.locator('[data-selection-count]').textContent(),'Выбрано: 2');
    const accepted = ['server-a','server-z'].map(id => ({id:`delete-${id}`,target:{meeting:{_0:id}},phase:'accepted'}));
    await page.evaluate(({rows,operations}) => window.GRAFLocalRecordings.update(rows,operations),{rows:aliases,operations:accepted});
    assert.deepEqual(await order(),['local-b']);
    assert.equal(await page.locator('[data-meeting-result-count]').textContent(),'Найдено: 1');
    assert.equal(await page.locator('[data-selection-count]').textContent(),'Выбрано: 0');
    assert.equal(await page.locator('[data-selection-toolbar]').isHidden(),true);
    await page.locator('ol.meeting-list').evaluate((list,html) => list.insertAdjacentHTML('beforeend',html),staleRows);
    await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap',{detail:{target:document.querySelector('#meeting-list-region')}})));
    assert.deepEqual(await order(),['local-b'],'stale HTML cannot resurrect accepted deletions before a native update');
    assert.equal(await page.locator('[data-meeting-result-count]').textContent(),'Найдено: 1');
    assert.equal(await page.locator('[data-selection-count]').textContent(),'Выбрано: 0');
    assert.equal(await page.locator('[data-selection-toolbar]').isHidden(),true);
    await page.evaluate(({rows,operations}) => window.GRAFLocalRecordings.update(rows,operations),{rows:aliases,operations:accepted});
    assert.deepEqual(await order(),['local-b'],'stale HTML and linked aliases cannot resurrect accepted deletions');
    assert.equal(await page.locator('[data-meeting-result-count]').textContent(),'Найдено: 1');
    assert.equal(await page.locator('[data-selection-count]').textContent(),'Выбрано: 0');
    assert.equal(await page.locator('[data-selection-toolbar]').isHidden(),true);
    await page.locator('[data-meeting-result-complete]').evaluate(node => { node.dataset.meetingResultComplete = 'false'; });
    await page.evaluate(({rows,operations}) => window.GRAFLocalRecordings.update(rows,operations),{rows:aliases,operations:accepted});
    assert.equal(await page.locator('[data-meeting-result-count]').textContent(),'Найдено: больше 1');
    await page.locator('[data-meeting-result-complete]').evaluate(node => { node.dataset.meetingResultComplete = 'true'; });
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
        if (message.action !== 'deleteSelection') return;
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
    assert.match(await page.locator('[data-local-account-recovery]').textContent(),/аккаунт не подтвержден/);
    await page.evaluate(() => window.GRAFLocalRecordings.update([], [], false));
    assert.equal(await page.locator('[data-local-account-recovery]').count(),0);
    // S44: per-item truth arrives before the late aggregate reply for the same bulk.
    for (const canAccess of [true, false]) {
      const bulk = await browser.newPage();
      try {
        bulk.on('pageerror', error => errors.push(error.message));
        await bulk.route('https://synthetic.invalid/**', route => route.fulfill({contentType:'text/html',body:'<html><body></body></html>'}));
        await bulk.goto('https://synthetic.invalid/desktop/meetings');
        const serverRow = (id, allowed = true) => `<li data-meeting-row data-meeting-id="${id}"><input type="checkbox" data-meeting-select ${allowed ? '' : 'disabled'}><button data-meeting-open ${allowed ? '' : 'disabled'}>Открыть</button><span class="row-meta">${allowed ? 'Доступно' : 'Нет доступа'}</span></li>`;
        const staleAccepted = serverRow('accepted');
        await bulk.setContent(`<form class="cabinet-list-controls"></form><h1 data-list-title tabindex="-1">Встречи</h1>
          <div id="meeting-list-region"><div data-meeting-result-count>Найдено: 2</div><div data-meeting-result-complete="true"><section data-meeting-list><ol class="meeting-list">${staleAccepted}${serverRow('rejected')}</ol></section></div></div>
          <div data-selection-toolbar hidden><span data-selection-count></span><button data-selection-delete>Удалить выбранные</button></div><div id="delete-feedback-region"></div><div data-meeting-result-announcer></div>
          <dialog data-delete-dialog data-title-one="Удаление" data-title-many="Удаление"><h2 data-delete-title></h2><p data-delete-count></p><p data-delete-error hidden></p><button data-delete-cancel>Отмена</button><button data-delete-confirm>Удалить</button></dialog>`);
        await bulk.evaluate(resultHTML => {
          window.GRAFRecordingDeletionBridgeVersion = 1;
          window.bulkMessages = []; window.bulkRefreshes = 0;
          window.webkit = {messageHandlers:{grafLocalRecording:{postMessage(message) {
            if (message.action === 'deleteSelection') window.bulkMessages.push(message);
          }}}};
          document.querySelector('form').addEventListener('submit', event => {
            event.preventDefault(); window.bulkRefreshes += 1;
            // A fresh server list response determines the rejected row's current rights.
            document.querySelector('ol').innerHTML = resultHTML;
            document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {detail:{target:document.querySelector('#meeting-list-region')}}));
          });
        }, serverRow('rejected', canAccess));
        await bulk.addScriptTag({path:path.join(assets,'user-time.js')});
        await bulk.addScriptTag({path:path.join(assets,'cabinet.js')});
        const alias = {...local,id:'accepted-local',meetingId:'accepted',uploadComplete:true};
        const operations = ['accepted','rejected'].map(id => ({id:`operation-${id}`,target:{meeting:{_0:id}},phase:'sending'}));
        const project = ops => bulk.evaluate(({alias,ops}) => window.GRAFLocalRecordings.update([alias],ops),{alias,ops});
        await project([]);
        for (const checkbox of await bulk.locator('[data-meeting-select]').all()) await checkbox.check();
        await bulk.locator('[data-selection-delete]').click();
        await bulk.locator('[data-delete-confirm]').click();
        const messages = await bulk.evaluate(() => window.bulkMessages);
        assert.equal(messages.length,1);
        assert.deepEqual(messages[0].meetingIds,['accepted','rejected']);
        assert.deepEqual(messages[0].localIds,[]);
        await project(operations);
        assert.equal(await bulk.locator('[data-meeting-select]:disabled').count(),2);
        const settled = operations.map(op => ({...op,phase:op.target.meeting._0}));
        await project(settled);
        assert.equal(await bulk.evaluate(() => window.bulkRefreshes),1,'rejection requests fresh rights');
        const assertResult = async () => {
          assert.equal(await bulk.locator('[data-meeting-id="accepted"], [data-graf-local-recording-row]').count(),0,'accepted and its local alias stay absent');
          assert.equal(await bulk.locator('[data-meeting-row]').count(),1);
          assert.equal(await bulk.locator('[data-meeting-id="rejected"] [data-meeting-select]').isEnabled(),canAccess);
          assert.equal(await bulk.locator('[data-meeting-id="rejected"] [data-meeting-open]').isEnabled(),canAccess);
          assert.equal(await bulk.locator('[data-meeting-result-count]').textContent(),'Найдено: 1');
          assert.equal(await bulk.locator('[data-selection-count]').textContent(),'Выбрано: 0');
          assert.equal(await bulk.locator('[data-selection-toolbar]').isHidden(),true);
          assert.equal(await bulk.evaluate(() => window.bulkMessages.length),1,'no second destructive command');
        };
        await assertResult();
        const result = {saved:true,accepted:1,pending:0,rejected:1};
        await bulk.evaluate(({id,result}) => window.GRAFLocalRecordings.deletionCompleted(id,result),{id:messages[0].requestId,result});
        await bulk.waitForFunction(() => !document.querySelector('[data-delete-dialog]').open);
        assert.match(await bulk.locator('#delete-feedback-region').textContent(),/Удалено из списка: 1\. Ожидают подтверждения: 0\. Отклонено: 1\./);
        await assertResult();
        await bulk.locator('ol').evaluate((list,html) => list.insertAdjacentHTML('beforeend',html),staleAccepted);
        await bulk.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap',{detail:{target:document.querySelector('#meeting-list-region')}})));
        await assertResult();
        await project(settled);
        await assertResult();
        const refreshes = await bulk.evaluate(() => window.bulkRefreshes);
        await bulk.evaluate(({id,result}) => window.GRAFLocalRecordings.deletionCompleted(id,result),{id:messages[0].requestId,result});
        await assertResult();
        assert.equal(await bulk.evaluate(() => window.bulkRefreshes),refreshes,'duplicate reply does not refresh or repeat deletion');
      } finally { await bulk.close(); }
    }
    console.log('S44 mixed native bulk: late and duplicate replies, accepted alias, current allowed/denied rights passed');
    // Viewport hints include local and linked aliases, never filtered/offscreen history.
    const visibility = await browser.newPage({viewport:{width:800,height:500}});
    await visibility.route('https://synthetic.invalid/**', route => route.fulfill({contentType:'text/html',body:'<html><body></body></html>'}));
    await visibility.goto('https://synthetic.invalid/desktop/meetings');
    await visibility.setContent(`<style>[data-meeting-row]{height:100px} body{margin:0}</style>
      <input id="meeting-search"><div id="meeting-list-region"><div data-meeting-list><ol class="meeting-list">
      <li data-meeting-row data-meeting-id="linked" data-sort-started="2026-09-06T00:00:00Z">Linked</li></ol></div></div>`);
    await visibility.evaluate(() => {
      window.GRAFRecordingDeletionBridgeVersion = 1; window.visibilityMessages = [];
      window.webkit = {messageHandlers:{grafLocalRecording:{postMessage(message) {
        if (message.action === 'visibleRecordings') window.visibilityMessages.push(message);
      }}}};
    });
    await visibility.addScriptTag({path:path.join(assets,'user-time.js')});
    await visibility.addScriptTag({path:path.join(assets,'cabinet.js')});
    await visibility.evaluate(local => window.GRAFLocalRecordings.update([
      {...local,id:'linked-local',meetingId:'linked',uploadComplete:true},
      ...Array.from({length:12},(_,n)=>({...local,id:`visible-${n}`})),
      {...local,id:'absent',meetingId:'not-on-page',uploadComplete:true},
    ]),local);
    await visibility.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap',
      {detail:{target:document.querySelector('#meeting-list-region')}})));
    await visibility.waitForFunction(() => window.visibilityMessages.at(-1)?.ids.includes('linked-local')
      && window.visibilityMessages.at(-1).ids.includes('visible-0') && !window.visibilityMessages.at(-1).ids.includes('absent'));
    const firstVisible = await visibility.evaluate(() => window.visibilityMessages.at(-1).ids);
    assert.ok(firstVisible.includes('linked-local'));
    assert.ok(firstVisible.includes('visible-0'));
    assert.ok(!firstVisible.includes('visible-9'));
    assert.ok(!firstVisible.includes('absent'));
    await visibility.locator('[data-graf-local-recording-row][data-graf-local-recording-id="visible-9"]').scrollIntoViewIfNeeded();
    await visibility.waitForFunction(() => window.visibilityMessages.at(-1).ids.includes('visible-9'));
    assert.ok(!(await visibility.evaluate(() => window.visibilityMessages.at(-1).ids)).includes('linked-local'));
    await visibility.fill('#meeting-search','does-not-match');
    await visibility.evaluate(() => window.GRAFLocalRecordings.update([]));
    await visibility.waitForFunction(() => window.visibilityMessages.at(-1).ids.length === 0);
    await visibility.setContent('<main data-meeting-id="00000000-0000-0000-0000-000000000262"></main>');
    await visibility.addScriptTag({path:path.join(assets,'user-time.js')});
    await visibility.addScriptTag({path:path.join(assets,'cabinet.js')});
    await visibility.evaluate(local => window.GRAFLocalRecordings.update([
      {...local,id:'detail-local',meetingId:'00000000-0000-0000-0000-000000000262'},
      {...local,id:'unrelated',meetingId:'00000000-0000-0000-0000-000000000263'},
    ]),local);
    await visibility.waitForFunction(() => window.visibilityMessages.at(-1).ids.includes('detail-local'));
    assert.deepEqual(await visibility.evaluate(() => window.visibilityMessages.at(-1).ids),['detail-local']);
    await visibility.setContent('<div data-meeting-list><ol class="meeting-list"></ol></div>');
    await visibility.addScriptTag({path:path.join(assets,'user-time.js')});
    await visibility.addScriptTag({path:path.join(assets,'cabinet.js')});
    await visibility.evaluate(local => {
      window.GRAFLocalRecordings.update(Array.from({length:120},(_,n)=>({...local,id:`bounded-${n}`})));
      document.querySelectorAll('[data-meeting-row]').forEach(row=>{row.style.height='2px';row.style.overflow='hidden'});
    },local);
    await visibility.waitForFunction(() => window.visibilityMessages.at(-1).ids.length === 100);
    const bounded = await visibility.evaluate(() => window.visibilityMessages.at(-1));
    assert.equal(bounded.version,1);
    assert.equal(new Set(bounded.ids).size,100);
    await visibility.close();
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
