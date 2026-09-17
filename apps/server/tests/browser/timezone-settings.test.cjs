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
const formHTML = `<meta charset="utf-8"><meta name="graf-time-user" content="actor"><meta name="graf-workspace" content="space"><meta name="graf-timezone" content="Asia/Yekaterinburg"><meta name="graf-time-preferred" content=""><meta name="graf-time-reload" content="false"><meta name="csrf-token" content="synthetic-csrf">
 <form data-account-preferences data-settings-autosave method="post" action="/settings/account/preferences">
 <fieldset data-settings-inputs disabled><input type="hidden" name="_csrf" value="synthetic-csrf">
 <label>Часовой пояс<select name="timezone" data-settings-combobox data-timezone-select>${zones.map(([value,label],i)=>`<option value="${value}" ${i?'':'selected'}>${label}</option>`).join('')}</select></label>
 <output data-timezone-preview hidden></output>
 <select name="theme"><option value="system">Системная</option><option value="dark">Тёмная</option></select>
 </fieldset><p data-settings-form-status hidden></p></form>`;
(async () => {
 const browser=await chromium.launch({headless:true});let saved='Asia/Yekaterinburg',failure=true,posts=[];
 const server=http.createServer(async(req,res)=>{
  if(req.method==='POST'){
   let raw='';for await(const chunk of req)raw+=chunk;const body=new URLSearchParams(raw);posts.push(body);
   assert.equal(req.headers['x-csrf-token'],'synthetic-csrf');
   if(failure){res.writeHead(422);res.end('{}');return;}
   saved=body.get('timezone');res.setHeader('Content-Type','application/json');res.end(JSON.stringify({saved:true,actor:'actor',workspace:'space',values:{timezone:saved}}));return;
  }
  res.setHeader('Content-Type','text/html; charset=utf-8');res.end(formHTML);
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const origin=`http://127.0.0.1:${server.address().port}`;
 try {
  const context=await browser.newContext({timezoneId:'Asia/Yekaterinburg'});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/settings/account');
  for(const file of ['user-time.js','settings-autosave.js','cabinet.js'])await page.addScriptTag({path:path.join(assets,file)});
  const select=page.locator('[data-timezone-select]'),search=page.getByRole('combobox',{name:'Часовой пояс'});
  assert(await select.isEnabled());assert(await search.isVisible());
  for(const query of ['Москва','Europe/Moscow','UTC+03:00']){
   await search.fill(query);assert.equal(await page.getByRole('listbox').getByRole('option').count(),1);assert.equal(await select.inputValue(),'Asia/Yekaterinburg');
  }
  await page.waitForTimeout(600);assert.equal(posts.length,0);
  assert.equal(await select.locator('option').count(),4);
  await search.fill('UTC+05:45');await page.getByRole('listbox').getByRole('option').click();
  assert.match(await page.locator('[data-timezone-preview]').textContent(),/UTC\+05:45/);
  await page.waitForFunction(()=>document.querySelector('form').dataset.state==='error');
  assert.equal(await select.inputValue(),'Asia/Kathmandu');assert.equal(await page.evaluate(()=>GRAFTime.timezone),'Asia/Yekaterinburg');
  await search.fill('ничего-похожего');assert.match(await page.locator('[data-combobox-status]').textContent(),/Совпадений нет/);
  failure=false;await page.getByRole('button',{name:'Повторить'}).click();await page.waitForFunction(()=>!GRAFSettings.pending());
  assert.equal(saved,'Asia/Kathmandu');assert.equal(await page.evaluate(()=>GRAFTime.timezone),'Asia/Kathmandu');assert.equal(new URL(page.url()).pathname,'/settings/account');
  assert(posts.every(p=>!p.has('theme')));assert.deepEqual(errors,[]);
  const noJS=await browser.newContext({javaScriptEnabled:false});const plain=await noJS.newPage();await plain.goto(origin);
  assert.equal(await plain.locator('[data-timezone-select]').isEnabled(),false);assert.equal(await plain.getByRole('button',{name:'Сохранить'}).count(),0);
  console.log('timezone: Russian/IANA/offset search, retained selection, preview, 422 recovery, autosave and no-JS passed');
 }finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
