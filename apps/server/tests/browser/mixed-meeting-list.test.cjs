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
    assert.deepEqual(errors,[]);
    console.log('mixed meeting list: seven sorts, stable ties, filters, dates, upload handoff and HTMX passed');
  } finally { await browser.close(); }
})().catch(error=>{ console.error(error); process.exitCode=1; });
