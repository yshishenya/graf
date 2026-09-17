const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
(async () => {
  const browser = await chromium.launch({headless:true});
  let saved = {display_name:'Тест', theme:'system', timezone:'UTC'}, mode = '', delay = 0, requests = 0, reads = 0, active = 0, peak = 0;
  const markup = () => `<meta charset="utf-8"><meta name="csrf-token" content="synthetic"><meta name="graf-time-user" content="actor"><meta name="graf-workspace" content="space">
    <form data-settings-autosave action="/settings/account/preferences" method="post"><fieldset data-settings-inputs disabled><label>Тема в меню<select name="theme" aria-label="Тема в меню"><option>system</option><option>dark</option><option>light</option></select></label></fieldset><p data-settings-form-status hidden></p></form>
    <form data-settings-autosave action="/settings/account/profile" method="post"><fieldset data-settings-inputs disabled><label>Имя<input name="display_name" value="${saved.display_name}"></label></fieldset><p data-settings-form-status hidden></p></form>
    <form data-settings-autosave action="/settings/account/preferences" method="post"><fieldset data-settings-inputs disabled><label>Тема<select name="theme" aria-label="Тема"><option>system</option><option>dark</option><option>light</option></select></label><label>Часовой пояс<select name="timezone"><option>UTC</option><option>Asia/Yekaterinburg</option></select></label><input type="search" aria-label="Поиск" data-timezone-search></fieldset><p data-settings-form-status hidden></p></form>
    <a href="/next">Дальше</a>`;
  const server = http.createServer(async (req,res) => {
    if(req.url === '/settings-autosave.js') {res.setHeader('Content-Type','text/javascript');res.end(fs.existsSync(path.join(assets,'settings-autosave.js')) ? fs.readFileSync(path.join(assets,'settings-autosave.js')) : '');return;}
    if(req.method === 'POST') {
      let raw='';for await(const chunk of req)raw+=chunk;
      requests++; active++; peak=Math.max(peak,active);
      assert.equal(req.headers['x-csrf-token'],'synthetic');
      assert.equal(req.headers['x-graf-expected-actor'],'actor');assert.equal(req.headers['x-graf-expected-workspace'],'space');
      const data=new URLSearchParams(raw), values={};
      for(const key of Object.keys(saved))if(data.has(key))values[key]=key === 'display_name' ? data.get(key).trim().replace(/\s+/g,' ') : data.get(key);
      if(delay)await new Promise(r=>setTimeout(r,delay)); active--;
      if(mode==='error') {res.writeHead(503);res.end();return;}
      if(mode==='login') {res.writeHead(303,{Location:'/login'});res.end();return;}
      if(mode==='malformed') {res.setHeader('Content-Type','application/json');res.end('{}');return;}
      Object.assign(saved,values);
      if(mode==='lost') {req.socket.destroy();return;}
      if(mode==='timeout') {res.writeHead(200,{'Content-Type':'application/json'});res.write('{');return;}
      res.setHeader('Content-Type','application/json');res.end(JSON.stringify({saved:true,actor:'actor',workspace:'space',values}));return;
    }
    if(req.headers['x-graf-settings-autosave']==='true'){reads++;await new Promise(r=>setTimeout(r,100));}
    res.setHeader('Content-Type','text/html; charset=utf-8');
    res.end(req.url==='/next'?'<h1>Другая страница</h1>':req.url==='/login'?'<h1>Вход</h1>':markup());
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const origin=`http://127.0.0.1:${server.address().port}`;
  try {
    const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(origin+'/settings/account');await page.addScriptTag({url:origin+'/settings-autosave.js'});
    assert.equal(await page.evaluate(()=>typeof window.GRAFSettings?.init),'function','shared autosave must exist');
    await page.evaluate(()=>window.GRAFSettings.init());
    const name=page.getByLabel('Имя',{exact:true});
    delay=150;await name.fill('А');await name.press('Tab');await name.fill('Б');await name.press('Tab');await name.fill('Последнее имя');
    await page.waitForFunction(()=>window.GRAFSettings.pending()===false);
    assert.equal(saved.display_name,'Последнее имя');assert.equal(peak,1);assert.equal(new URL(page.url()).pathname,'/settings/account');
    assert.equal(await name.inputValue(),'Последнее имя');
    await name.fill('');await name.press('Tab');await page.waitForFunction(()=>!window.GRAFSettings.pending());assert.equal(saved.display_name,'');
    const count=requests;await page.getByLabel('Поиск').fill('UTC');await page.waitForTimeout(650);assert.equal(requests,count);
    await page.getByLabel('Тема в меню',{exact:true}).selectOption('dark');await page.getByLabel('Тема',{exact:true}).selectOption('light');
    await page.waitForFunction(()=>!window.GRAFSettings.pending());assert.equal(saved.theme,'light');assert.equal(await page.getByLabel('Тема в меню',{exact:true}).inputValue(),'light');
    mode='error';await name.fill('После ошибки');await name.press('Tab');
    await page.waitForFunction(()=>document.querySelector('[action$="/profile"]').dataset.state==='error');assert.equal(await name.inputValue(),'После ошибки');assert.equal(saved.display_name,'');
    mode='';const beforeReads=reads;await page.locator('[action$="/profile"]').getByRole('button',{name:'Повторить',exact:true}).evaluate(button=>{button.click();button.click();});
    assert.equal(await page.evaluate(()=>GRAFSettings.flushAll()),true,'Leaving waits for pending read-back');
    await page.waitForFunction(()=>!window.GRAFSettings.pending());assert.equal(saved.display_name,'После ошибки');assert.equal(reads,beforeReads+1,'Double retry performs one verification');
    for(const failure of ['login','malformed']) {
      mode=failure;await name.fill(failure);await name.press('Tab');
      await page.waitForFunction(()=>document.querySelector('[action$="/profile"]').dataset.state==='error');
      assert.equal(saved.display_name,failure === 'login' ? 'После ошибки' : 'login');assert.equal(new URL(page.url()).pathname,'/settings/account');
      mode='';await page.locator('[action$="/profile"]').getByRole('button',{name:'Повторить',exact:true}).click();
      await page.waitForFunction(()=>!window.GRAFSettings.pending());
    }
    mode='lost';await name.fill('  Ответ   потерян  ');await name.press('Tab');
    await page.waitForFunction(()=>document.querySelector('[action$="/profile"]').dataset.state==='error');
    assert.equal(saved.display_name,'Ответ потерян');mode='';const afterLost=requests;
    await page.locator('[action$="/profile"]').getByRole('button',{name:'Повторить',exact:true}).click();
    await page.waitForFunction(()=>!GRAFSettings.pending());assert.equal(requests,afterLost,'read-back confirms lost reply without replay');
    mode='timeout';await name.fill('Ответ завис');await name.press('Tab');
    await page.waitForFunction(()=>document.querySelector('[action$="/profile"]').dataset.state==='error');
    assert.equal(saved.display_name,'Ответ завис');const timedOutCount=requests;mode='';
    await page.locator('[action$="/profile"]').getByRole('button',{name:'Повторить',exact:true}).click();
    await page.waitForFunction(()=>!GRAFSettings.pending());assert.equal(requests,timedOutCount);
    mode='error';await name.fill('Мой выбор');await name.press('Tab');
    await page.waitForFunction(()=>document.querySelector('[action$="/profile"]').dataset.state==='error');
    saved.display_name='Другое устройство';mode='';
    await page.locator('[action$="/profile"]').getByRole('button',{name:'Повторить',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('[action$="/profile"]').dataset.state==='conflict');
    assert.equal(await name.inputValue(),'Мой выбор');
    await page.locator('[action$="/profile"]').getByRole('button',{name:'Применить мой выбор'}).click();
    await page.waitForFunction(()=>!GRAFSettings.pending());assert.equal(saved.display_name,'Мой выбор');
    mode='error';await name.fill('Не заменять серверное');await name.press('Tab');
    await page.waitForFunction(()=>document.querySelector('[action$="/profile"]').dataset.state==='error');
    saved.display_name='Сохранённое имя';mode='';
    await page.locator('[action$="/profile"]').getByRole('button',{name:'Повторить',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('[action$="/profile"]').dataset.state==='conflict');
    const beforeAccept=requests;
    await page.getByRole('button',{name:'Загрузить сохранённое',exact:true}).click();
    await page.waitForFunction(()=>!GRAFSettings.pending());
    assert.equal(await name.inputValue(),'Сохранённое имя');assert.equal(requests,beforeAccept);
    await page.route('**/problem',route=>route.fulfill({status:422,contentType:'application/problem+json',body:JSON.stringify({code:'summary_template_limit'})}));
    assert.equal(await page.evaluate(()=>GRAFSettings.request('/problem').then(()=>null,error=>error.message)),'summary_template_limit');
    // Composition must not submit intermediate input.
    const beforeIME=requests;await name.dispatchEvent('compositionstart');await name.fill('Составной ввод');await page.waitForTimeout(650);assert.equal(requests,beforeIME);
    await name.dispatchEvent('compositionend');await page.waitForFunction(()=>!window.GRAFSettings.pending());assert.equal(saved.display_name,'Составной ввод');
    // An older acknowledgement must not replace an active composed value.
    delay=300;await name.fill('Перед составным вводом');await name.press('Tab');
    await page.waitForFunction(()=>document.querySelector('[action$="/profile"]').dataset.state==='saving');
    await name.focus();await name.dispatchEvent('compositionstart');await name.fill('Незавершённый IME');
    await page.waitForTimeout(450);assert.equal(await name.inputValue(),'Незавершённый IME','In-flight acknowledgement preserves composition');
    assert.equal(await page.evaluate(()=>GRAFSettings.pending()),true,'Composition keeps exit protection active');
    assert.equal(await page.evaluate(()=>GRAFSettings.prepareToLeave()),false,'Unfinished composition cannot be discarded by closing');
    await name.dispatchEvent('compositionend');await page.waitForFunction(()=>!window.GRAFSettings.pending());
    assert.equal(saved.display_name,'Незавершённый IME');delay=150;
    const scopedCount=requests;
    await page.evaluate(()=>document.querySelector('meta[name="graf-workspace"]').content='other');
    await name.fill('Старая область');await name.press('Tab');
    await page.waitForFunction(()=>document.querySelector('[action$="/profile"]').dataset.state==='error');assert.equal(requests,scopedCount);
    await page.evaluate(()=>document.querySelector('meta[name="graf-workspace"]').content='space');
    await page.locator('[action$="/profile"]').getByRole('button',{name:'Повторить',exact:true}).click();await page.waitForFunction(()=>!GRAFSettings.pending());
    delay=150;await name.fill('Перед переходом');await page.getByRole('link',{name:'Дальше'}).click();await page.waitForURL('**/next');assert.equal(saved.display_name,'Перед переходом');
    assert.deepEqual(errors,[]);
    const calendars=await browser.newPage();let calendarWrites=0, selected=Array.from({length:20},(_,i)=>String(i));
    await calendars.route('**/calendar-selection',async route=>{
      calendarWrites++;const body=new URLSearchParams(route.request().postData());
      assert.deepEqual(JSON.parse(body.get('expected_selected_ids')),selected.slice().sort());
      selected=body.getAll('selected_provider_calendar_ids');
      await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({saved:true,actor:'actor',workspace:'space',values:{selected_provider_calendar_ids:selected}})});
    });
    await calendars.goto(origin);
    await calendars.setContent(`<meta name="graf-time-user" content="actor"><meta name="graf-workspace" content="space"><form action="/calendar-selection" data-settings-autosave data-calendar-mutation="selection" data-calendar-selection-limit="20"><fieldset data-settings-inputs disabled>${Array.from({length:21},(_,i)=>`<label>Календарь ${i}<input type="checkbox" name="selected_provider_calendar_ids" value="${i}" ${i<20?'checked':''}></label>`).join('')}</fieldset><p data-settings-form-status data-calendar-mutation-status hidden></p></form>`);
    for(const file of ['settings-autosave.js','cabinet.js'])await calendars.addScriptTag({path:path.join(assets,file)});
    await calendars.evaluate(()=>GRAFSettings.init());
    await calendars.getByLabel('Календарь 20',{exact:true}).click();
    assert.equal(await calendars.locator('input:checked').count(),20);assert.equal(calendarWrites,0);assert.equal(await calendars.getByText('Можно выбрать до 20 календарей.',{exact:true}).isVisible(),true);
    for(let i=0;i<20;i++)await calendars.getByLabel('Календарь '+i,{exact:true}).uncheck();
    await calendars.waitForFunction(()=>!GRAFSettings.pending());assert.deepEqual(selected,[]);
    await calendars.getByLabel('Календарь 0',{exact:true}).check();await calendars.waitForFunction(()=>!GRAFSettings.pending());assert.deepEqual(selected,['0']);
    for(let i=1;i<20;i++)await calendars.getByLabel('Календарь '+i,{exact:true}).check();
    await calendars.waitForFunction(()=>!GRAFSettings.pending());assert.equal(selected.length,20);
    assert.equal(await calendars.getByRole('button',{name:/Сохранить/}).count(),0);
    const plain=await browser.newContext({javaScriptEnabled:false});const noJS=await plain.newPage();await noJS.goto(origin+'/settings/account');assert.equal(await noJS.getByLabel('Имя',{exact:true}).isDisabled(),true);assert.equal(await noJS.getByRole('button',{name:/Сохранить/}).count(),0);
    console.log('settings autosave: last edit, empty name, shared theme, search, failure/read-back/retry, false success, IME, navigation and no-JS passed');
  } finally {await browser.close();await new Promise(r=>server.close(r));}
})().catch(error=>{console.error(error);process.exitCode=1;});
