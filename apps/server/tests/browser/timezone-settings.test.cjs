const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const http = require('node:http');
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
const zones = [
 ['Asia/Yekaterinburg','UTC+05:00 — Екатеринбург, Россия'],
 ['Europe/Moscow','UTC+03:00 — Москва, Россия'],
 ['Asia/Kathmandu','UTC+05:45 — Катманду, Непал'],
 ['America/New_York','UTC−04:00 — Нью-Йорк, США'],
];
const formHTML = `<meta charset="utf-8"><meta name="graf-timezone" content="Asia/Yekaterinburg"><meta name="graf-time-preferred" content=""><meta name="graf-time-reload" content="false"><meta name="csrf-token" content="synthetic-csrf">
 <form data-account-preferences data-settings-form method="post" action="/settings/account/preferences">
 <input type="hidden" name="_csrf" value="synthetic-csrf">
 <label hidden data-timezone-search-wrap>Найти город<input type="search" data-timezone-search></label>
 <label>Часовой пояс<select name="timezone" data-timezone-select>${zones.map(([value,label],i)=>`<option value="${value}" ${i?'':'selected'}>${label}</option>`).join('')}</select></label>
 <output data-timezone-preview hidden></output><span data-timezone-search-result hidden></span>
 <select name="theme"><option value="system">Системная</option><option value="dark">Тёмная</option></select>
 <button type="submit">Сохранить</button><button type="reset">Отменить</button><p data-settings-form-status hidden></p></form>`;
(async () => {
 const browser = await chromium.launch({headless:true});
 let failure = 'network', postCount = 0, successCount = 0, validationCount = 0, posted = '', nativePosted = '';
 const server = http.createServer(async (request, response) => {
  if (request.method === 'POST') {
   let body = '';
   for await (const chunk of request) body += chunk;
   if (request.headers['x-csrf-token']) {
    postCount++;
    posted = body;
    assert.equal(request.headers['x-csrf-token'],'synthetic-csrf');
    if (failure === 'network') { request.socket.destroy(); return; }
    if (failure === 'validation') {
     validationCount++;
     response.writeHead(422, {'Content-Type':'application/json'});
     response.end('{"code":"invalid_account_preference"}'); return;
    }
    successCount++;
   } else { nativePosted = body; }
   response.writeHead(303, {Location:'/settings/account?preferences=saved'});
   response.end(); return;
  }
  response.writeHead(200, {'Content-Type':'text/html; charset=utf-8'});
  response.end(request.url.includes('preferences=saved') ? '<h1>Настройки сохранены</h1>' : formHTML);
 });
 await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
 const origin = `http://127.0.0.1:${server.address().port}`;
 try {
  const context = await browser.newContext({timezoneId:'Asia/Yekaterinburg'});
  const page = await context.newPage();
  const errors=[]; page.on('pageerror', error=>errors.push(error.message));
  await page.goto(`${origin}/settings/account`);
  await page.addScriptTag({path:path.join(assets,'user-time.js')});
  await page.addScriptTag({path:path.join(assets,'cabinet.js')});
  const select=page.locator('[data-timezone-select]');
  const search=page.locator('[data-timezone-search]');
  assert.equal(await select.inputValue(),'Asia/Yekaterinburg');
  assert.equal(await search.isVisible(),true);
  for(const query of ['Москва','Europe/Moscow','UTC+03:00']) {
   await search.fill(query);
   assert.equal(await select.locator('option').count(),2); // Match plus current draft.
   assert.equal(await select.inputValue(),'Asia/Yekaterinburg');
  }
  await search.fill('UTC+05:45');
  assert.equal(await select.locator('option[value="Asia/Kathmandu"]').count(),1);
  await select.selectOption('Asia/Kathmandu');
  assert.match(await page.locator('[data-timezone-preview]').textContent(),/UTC\+05:45/);
  assert.equal(await page.evaluate(()=>window.GRAFTime.timezone),'Asia/Yekaterinburg');
  await search.fill('ничего-похожего');
  assert.match(await page.locator('[data-timezone-search-result]').textContent(),/Совпадений нет/);
  assert.equal(await select.inputValue(),'Asia/Kathmandu');
  await page.getByRole('button',{name:'Отменить'}).click();
  await page.waitForFunction(()=>document.querySelector('[data-timezone-select]').value==='Asia/Yekaterinburg');
  assert.equal(await search.inputValue(),'');
  assert.equal(await select.locator('option').count(),4);
  assert.equal(await page.locator('form').getAttribute('data-state'),'pristine');
  await select.selectOption('America/New_York');
  await page.selectOption('[name="theme"]','dark');
  await page.getByRole('button',{name:'Сохранить'}).click();
  await page.waitForFunction(()=>document.querySelector('form').dataset.state==='error');
  assert.equal(await select.inputValue(),'America/New_York');
  assert.equal(await page.locator('[name="theme"]').inputValue(),'dark');
  assert.equal(await page.getByRole('button',{name:'Сохранить'}).isEnabled(),true);
  assert.match(posted,/name="timezone"\r\n\r\nAmerica\/New_York/);
  assert(!posted.includes('Найти город'));
  failure='validation';
  await page.getByRole('button',{name:'Сохранить'}).click();
  await page.waitForFunction(()=>document.querySelector('[data-settings-form-status]').textContent.includes('Проверьте часовой пояс'));
  assert.equal(await select.inputValue(),'America/New_York');
  assert.equal(await page.getByRole('button',{name:'Сохранить'}).isEnabled(),true);
  failure='';
  await page.getByRole('button',{name:'Сохранить'}).click();
  await page.waitForURL('**/settings/account?preferences=saved');
  assert(postCount >= 3); // Chromium may retry a dropped TCP connection.
  assert.equal(validationCount,1);
  assert.equal(successCount,1);
  assert.deepEqual(errors,[]);
  // Native form submission remains usable when JavaScript is disabled.
  const noJS = await browser.newContext({javaScriptEnabled:false});
  const plain=await noJS.newPage(); await plain.goto(`${origin}/settings/account`);
  assert.equal(await plain.locator('[data-timezone-search]').isVisible(),false);
  assert.equal(await plain.locator('[data-timezone-select]').isEnabled(),true);
  assert.equal(await plain.locator('[data-timezone-select] option').count(),4);
  await plain.locator('[data-timezone-select]').selectOption('Asia/Kathmandu');
  await plain.getByRole('button',{name:'Сохранить'}).click();
  await plain.waitForURL('**/settings/account?preferences=saved');
  assert.equal(new URLSearchParams(nativePosted).get('timezone'),'Asia/Kathmandu');
  assert.equal(new URLSearchParams(nativePosted).get('_csrf'),'synthetic-csrf');
  console.log('timezone settings: Russian/IANA/offset search, preview, Cancel, network/422 retry, redirect and no-JS passed');
 } finally { await browser.close(); await new Promise(resolve=>server.close(resolve)); }
})().catch(error=>{console.error(error);process.exitCode=1;});
