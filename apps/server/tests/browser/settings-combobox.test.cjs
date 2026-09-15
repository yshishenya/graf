const { chromium, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const cabinet = path.join(__dirname, '../../src/twobrain_rec_server/cabinet');
const assets = path.join(cabinet, 'static/cabinet');
const recording = fs.readFileSync(path.join(cabinet, 'templates/cabinet/pages/settings_recording_content.html'), 'utf8').split('{% if embedded %}')[1].split('{% else %}')[0];
(async () => {
 const engine = process.env.BROWSER === 'webkit' ? webkit : chromium;
 const browser = await engine.launch({headless:true});
 try {
  const page = await browser.newPage({viewport:{width:900,height:900}});
  page.setDefaultTimeout(5000);
  await page.addInitScript(() => {
   const localeLowercase = String.prototype.toLocaleLowerCase;
   String.prototype.toLocaleLowerCase = function () { return localeLowercase.call(this, 'tr-TR'); };
  });
  const errors=[]; page.on('pageerror',error=>errors.push(error.message));
  await page.setContent(`<meta charset="utf-8"><meta name="graf-time-user" content="actor"><meta name="graf-workspace" content="space"><main class="settings-page"><h1>Запись</h1>${recording}
   <form data-settings-form><label>Язык<select data-settings-combobox name="language"><option value="ru">Русский</option><option disabled value="none">Недоступно</option><option value="en">English</option></select></label>
   <label for="large">Каталог</label><select id="large" data-settings-combobox name="catalog">${Array.from({length:600},(_,i)=>`<option value="${i}">Вариант ${i}</option>`).join('')}</select>
   <button type="submit">Сохранить</button><button type="reset">Отменить</button></form></main>`);
  await page.addStyleTag({path:path.join(assets,'cabinet.css')});
  await page.evaluate(()=>{
   window.calls=[]; window.delay=0;
   window.targets=[{id:'zoom',name:'Zoom',rule:'ask'},{id:'teams',name:'Microsoft Teams',rule:'never'},{id:'long',name:'Приложение с очень длинным названием для проверки переноса',rule:'always'}];
   window.webkit={messageHandlers:{grafRecordingSettings:{postMessage:async data=>{
    window.calls.push(data);
    if(window.delay) await new Promise(resolve=>setTimeout(resolve,window.delay));
    if(data.action==='set') window.targets.find(t=>t.id===data.targetID).rule=data.rule;
    if(data.action==='setAll') window.targets.forEach(t=>t.rule=data.rule);
    return {version:1,targets:window.targets};
   }}}};
  });
  await page.addScriptTag({path:path.join(assets,'settings-autosave.js')});
  await page.addScriptTag({path:path.join(assets,'cabinet.js')});
  await page.evaluate(()=>window.GRAFRecordingSettings.connect('synthetic-nonce'));
  await page.waitForFunction(()=>document.querySelectorAll('[data-recording-target]').length===3);
  const apps=page.getByRole('combobox',{name:'Приложения',exact:true});
  const options=page.getByRole('listbox').getByRole('option');
  await apps.focus();
  assert.equal(await apps.getAttribute('aria-expanded'),'false','Initial focus must not open the catalog');
  await apps.click(); assert.equal(await options.count(),3);
  assert((await apps.boundingBox()).width<=380,'Application field should not stretch across settings');
  assert(await options.evaluateAll(items=>items.every(item=>item.getAttribute('aria-selected')==='false')),'App filter must not imply a saved setting');

  await options.filter({hasText:'Microsoft Teams'}).click();
  assert.equal(await apps.inputValue(),'Microsoft Teams');
  assert.equal(await apps.getAttribute('aria-expanded'),'false');
  assert.equal(await page.locator('[data-recording-settings-targets] label:visible').count(),1);
  // Reopening must keep the retained application query on every opening path.
  for (const reopen of [() => apps.click(), () => apps.press('ArrowDown'),
    () => apps.locator('..').getByRole('button',{name:'Показать варианты'}).click()]) {
    await apps.press('Tab');
    await reopen();
    assert.equal(await options.count(),1,'Reopened app list must retain its query');
    assert.equal(await options.first().innerText(),'Microsoft Teams');
    await apps.press('Escape');
  }
  for (const query of ['Microsoft  Teams', 'Ｍicrosoft　Teams', '  MICROSOFT Teams  ', 'Teams Microsoft']) {
    await apps.fill(query);
    const expected = query === 'Teams Microsoft' ? 0 : 1;
    assert.equal(await options.count(),expected,`Popup matching: ${query}`);
    assert.equal(await page.locator('[data-recording-settings-targets] label:visible').count(),expected,`Row matching: ${query}`);
  }
  await apps.fill('zOo'); assert.equal(await options.count(),1);
  assert.equal(await page.locator('[data-recording-settings-targets] label:visible').count(),1);
  await apps.press('Escape');
  await apps.click({position:{x:20,y:15}});
  assert.equal(await apps.evaluate(el=>el.selectionStart===el.selectionEnd),true,'Reopening an app filter keeps the caret');
  assert.equal(await apps.inputValue(),'zOo','Reopening must preserve the app query');
  const callsBefore=await page.evaluate(()=>calls.length);
  await apps.press('ArrowDown'); await apps.press('Enter');
  assert.equal(await apps.inputValue(),'Zoom');
  assert.equal(await page.evaluate(()=>calls.length),callsBefore);
  const bulk=page.getByRole('combobox',{name:'Автозапись для всех приложений'});
  await bulk.click();
  const shortGeometry=await page.locator('.settings-combobox__popup:visible').evaluate(el=>({
    viewport:el.clientHeight, content:el.scrollHeight, radius:getComputedStyle(el).borderRadius,
    last:el.querySelector('[role=option]:last-child').getBoundingClientRect().bottom,
    bottom:el.getBoundingClientRect().bottom,
  }));
  assert.equal(shortGeometry.viewport,shortGeometry.content,'Three rules must fit without clipping or scrolling');
  assert(shortGeometry.last<=shortGeometry.bottom-1,'Last rule must fit within the border');
  assert.equal(shortGeometry.radius,'6px');
  await options.filter({hasText:'Никогда'}).click();
  await page.waitForFunction(()=>targets.every(t=>t.rule==='never'));
  assert.equal(await apps.inputValue(),'Zoom');
  assert.equal(await page.locator('[data-recording-settings-targets] label:visible').count(),1);
  await apps.fill('');
  assert.equal(await page.locator('[data-recording-settings-targets] label:visible').count(),3);
  await apps.fill('нет такого приложения'); assert.equal(await options.count(),0);
  await page.evaluate(()=>window.dispatchEvent(new Event('blur')));
  assert.equal(await apps.getAttribute('aria-expanded'),'false');
  assert.equal(await apps.inputValue(),'нет такого приложения','Deactivation preserves app query');
  await apps.press('Enter'); assert.equal(await apps.inputValue(),'нет такого приложения');
  await apps.fill(''); await apps.press('Tab');

  const beforeRename=await page.evaluate(()=>calls.length);
  await page.evaluate(()=>{targets[0].name='Zoom Workplace';window.GRAFRecordingSettings.refresh();});
  await page.getByRole('combobox',{name:'Автозапись: Zoom Workplace',exact:true}).waitFor({timeout:2000});
  assert.equal(await page.getByRole('combobox',{name:'Автозапись: Zoom',exact:true}).count(),0);
  assert(!(await page.evaluate(start=>calls.slice(start).some(call=>['set','setAll'].includes(call.action)),beforeRename)));
  await page.evaluate(()=>{targets[0].name='Zoom';window.GRAFRecordingSettings.refresh();});
  await page.getByRole('combobox',{name:'Автозапись: Zoom',exact:true}).waitFor({timeout:2000});

  const zoom=page.getByRole('combobox',{name:'Автозапись: Zoom',exact:true});
  await zoom.fill('Спра');
  const beforeRefresh=await page.evaluate(()=>calls.length);
  await page.evaluate(()=>{targets[0].rule='always';window.GRAFRecordingSettings.refresh();});
  assert.equal(await zoom.inputValue(),'Спра');
  assert.equal(await zoom.getAttribute('aria-expanded'),'true');
  assert.equal(await page.evaluate(()=>calls.length),beforeRefresh);
  await zoom.press('Escape'); await zoom.press('Tab');
  await page.waitForFunction(()=>document.querySelector('[data-recording-target=zoom]').value==='always');
  assert.equal(await zoom.inputValue(),'Всегда');

  const language=page.getByRole('combobox',{name:'Язык',exact:true});
  const original=page.locator('select[name=language]');
  assert.equal(await original.isVisible(),false);
  // A click after Escape or a mouse choice must replace the restored label, even while focused.
  for (const close of [async () => language.press('Escape'),
    async () => options.filter({hasText:'Русский'}).click()]) {
   await language.click(); await close();
   await language.click({position:{x:20,y:15}});
   await page.keyboard.type('Eng');
   assert.equal(await language.inputValue(),'Eng','Reopening must select the saved label before typing');
   assert.equal(await original.inputValue(),'ru','Typing must not save a setting');
   await language.click({position:{x:20,y:15}});
   assert.equal(await language.evaluate(el=>el.selectionStart===el.selectionEnd),true,'Editing clicks keep the caret');
   await language.press('Escape');
  }
  await language.dispatchEvent('compositionstart');
  await language.evaluate(el=>el.setSelectionRange(2,2));
  await language.locator('..').getByRole('button',{name:'Показать варианты'}).click();
  assert.deepEqual(await language.evaluate(el=>[el.selectionStart,el.selectionEnd]),[2,2],'Reopening must not select IME composition');
  await language.dispatchEvent('compositionend'); await language.press('Escape');
  await language.click(); assert.equal(await options.count(),3);
  assert.equal(await options.locator('[aria-hidden=true]').allTextContents().then(values=>values.join('')),'✓');
  assert.equal(await options.filter({hasText:'Русский'}).getAttribute('aria-selected'),'true');
  await language.press('ArrowDown'); await language.press('ArrowDown');
  assert.equal(await original.inputValue(),'ru');
  assert.equal(await options.filter({hasText:'Русский'}).getAttribute('aria-selected'),'true','Arrows must not move the saved checkmark');
  await language.press('Enter'); assert.equal(await original.inputValue(),'en');
  assert.equal(await language.getAttribute('aria-expanded'),'false');
  await language.fill('Рус');
  await page.evaluate(()=>window.dispatchEvent(new Event('blur')));
  assert.equal(await language.getAttribute('aria-expanded'),'false');
  assert.equal(await language.inputValue(),'English','Deactivation cancels unconfirmed setting');
  await language.fill('Рус'); await language.press('Escape');
  assert.equal(await language.inputValue(),'English'); assert.equal(await original.inputValue(),'en');
  await language.fill('Нет'); await language.press('Enter'); assert.equal(await original.inputValue(),'en');
  await language.press('Tab'); assert.equal(await language.inputValue(),'English');
  await language.fill('Рус');
  await language.dispatchEvent('keydown',{key:'Enter',isComposing:true});
  assert.equal(await original.inputValue(),'en');
  await language.press('Escape');
  await page.getByRole('button',{name:'Отменить',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('input[aria-label="Язык"]').value==='Русский');
  assert.equal(await original.inputValue(),'ru');
  await original.evaluate(el=>{el.disabled=true;});
  await page.waitForFunction(()=>document.querySelector('input[aria-label="Язык"]').disabled);
  await original.evaluate(el=>{el.disabled=false;el.value='en';el.dispatchEvent(new Event('change'));});
  await page.waitForFunction(()=>!document.querySelector('input[aria-label="Язык"]').disabled);
  assert.equal(await language.inputValue(),'English');
  await language.fill('Рус');
  await original.evaluate(el=>el.add(new Option('Français','fr')));
  assert.equal(await language.inputValue(),'Рус');
  await language.press('Escape');
  await language.click(); assert.equal(await options.count(),4);
  await language.press('Escape');
  const catalog=page.getByRole('combobox',{name:'Каталог',exact:true});
  await catalog.click();
  const longGeometry=await page.locator('.settings-combobox__popup:visible').evaluate(el=>({
    viewport:el.clientHeight, content:el.scrollHeight,
    eighth:el.querySelectorAll('[role=option]')[7].getBoundingClientRect().bottom,
    bottom:el.getBoundingClientRect().bottom,
  }));
  assert(longGeometry.content>longGeometry.viewport,'Large catalog must scroll');
  assert(Math.abs(longGeometry.eighth-(longGeometry.bottom-1))<=1,'Eight complete rows must fit before scrolling');
  await catalog.press('Escape');
  const ms=await catalog.evaluate(el=>{el.focus();const start=performance.now();el.value='599';el.dispatchEvent(new Event('input',{bubbles:true}));return performance.now()-start;});
  assert(ms<=100,`600 option filter took ${ms}ms`);
  assert.equal(await options.count(),1); await catalog.press('Enter');
  assert.equal(await page.locator('#large').inputValue(),'599');
  assert.deepEqual(await page.locator('form').evaluate(el=>[...new FormData(el).keys()]),['language','catalog']);

  await page.setViewportSize({width:375,height:812});
  await apps.fill(''); await apps.click();
  const popup=page.locator('.settings-combobox__popup:visible');
  const box=await popup.boundingBox(); assert(box.x>=0 && box.x+box.width<=375);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  if(process.env.SCREENSHOT_DIR){
   fs.mkdirSync(process.env.SCREENSHOT_DIR,{recursive:true});
   await page.screenshot({path:path.join(process.env.SCREENSHOT_DIR,'settings-combobox-light.png')});
   await page.evaluate(()=>document.documentElement.dataset.theme='dark');
   await page.screenshot({path:path.join(process.env.SCREENSHOT_DIR,'settings-combobox-dark.png')});
  }
  // Regression: an ordinary scrollbar consumes width after a shorter catalog replaces a tall one.
  await page.setViewportSize({width:900,height:1000});
  const gutterStyle=await page.addStyleTag({content:'.settings-combobox__popup::-webkit-scrollbar { width:18px; } #large { width:220px; } .settings-combobox:has(#large) {width:220px;position:fixed;top:80px;left:20px;}'});
  await page.locator('#large').evaluate(el=>el.replaceChildren(...Array.from({length:12},(_,i)=>new Option('Очень длинная строка '.repeat(5)+i,String(i)))));
  await catalog.click(); await catalog.press('Escape');
  await page.locator('#large').evaluate(el=>el.replaceChildren(...Array.from({length:9},(_,i)=>new Option('WWWWWWWWWWW'+i,String(i)))));
  await catalog.click();
  const gutter=await page.locator('.settings-combobox__popup:visible').evaluate(el=>({
   eighth:el.querySelectorAll('[role=option]')[7].getBoundingClientRect().bottom,
   bottom:el.getBoundingClientRect().bottom,
  }));
  assert(Math.abs(gutter.eighth-(gutter.bottom-1))<=1,'Non-overlay scrollbar must not change wrapping after measurement');
  await catalog.press('Escape'); await gutterStyle.evaluate(el=>el.remove());
  // The page deliberately forces locale-sensitive lowercase to Turkish above.
  // ASCII I must still match without changing the retained query or setting.
  await page.evaluate(()=>{targets[0].name='Indian/Maldives';window.GRAFRecordingSettings.refresh();});
  await page.getByRole('combobox',{name:'Автозапись: Indian/Maldives',exact:true}).waitFor({timeout:2000});
  await apps.fill('indian/maldives');
  assert.equal(await options.count(),1,'Locale-independent search must match ASCII I in Chromium/WebKit');
  assert.equal(await page.locator('[data-recording-settings-targets] label:visible').count(),1);
  assert.equal(await apps.inputValue(),'indian/maldives');
  for(const filename of fs.readdirSync(path.join(cabinet,'templates/cabinet/pages')).filter(name=>name.startsWith('settings_'))){
   const template=fs.readFileSync(path.join(cabinet,'templates/cabinet/pages',filename),'utf8');
   assert(!/<select(?![^>]*data-settings-combobox)/.test(template),`Unconverted select: ${filename}`);
   assert(!template.includes('data-timezone-search'),`Separate search: ${filename}`);
  }
  for (const canManageDefault of [false,true]) {
  const extra=await browser.newPage(); extra.setDefaultTimeout(5000);
  extra.on('pageerror',error=>errors.push(error.message));
  const summarySource=fs.readFileSync(path.join(cabinet,'templates/cabinet/pages/settings_summaries_content.html'),'utf8');
  const notificationSource=fs.readFileSync(path.join(cabinet,'templates/cabinet/pages/settings_notifications_content.html'),'utf8').split('{% if embedded %}')[1].split('{% else %}')[0];
  const summaryHTML=summarySource.replace(/{% for format in summary_formats %}([\s\S]*?){% endfor %}/g,(_,body)=>
   [{key:'auto',name:'Авто'},{key:'brief',name:'Кратко'}].map(format=>body
    .replaceAll('{{ format.key }}',format.key).replaceAll('{{ format.name }}',format.name)
    .replaceAll('{{ format.version }}','1').replaceAll('{{ format.purpose }}','Тестовый формат')
    .replaceAll("{{ format.sections|join(',') }}",'summary')).join(''));
  const notificationHTML=execFileSync(path.join(__dirname,'../../.venv/bin/python'),['-c',
   `import sys; from jinja2 import Environment, FileSystemLoader; print(Environment(loader=FileSystemLoader(sys.argv[1]), autoescape=True).from_string('{% import "cabinet/components/primitives.html" as ui %}'+sys.stdin.read()).render())`,
   path.join(cabinet,'templates')],{input:notificationSource,encoding:'utf8'});
  await extra.setContent(`<meta name="graf-time-user" content="actor"><meta name="graf-workspace" content="space">${summaryHTML}${notificationHTML}`);
  await extra.addStyleTag({path:path.join(assets,'cabinet.css')});
  await extra.evaluate(canManageDefault=>{
   window.summaryReady=new Promise(resolve=>window.releaseSummary=resolve);
   window.savedDefault=null; window.notificationWrites=[];
   window.fetch=async (url,options={})=>{
    if(options.method==='PUT') window.savedDefault=JSON.parse(options.body);
    await window.summaryReady;
    return new Response(JSON.stringify({actor:'actor',workspace:'space',personal:[],can_manage_default:canManageDefault,default_template_key:'brief',template_key:window.savedDefault?.template_key}),{status:200,headers:{'Content-Type':'application/json'}});
   };
   window.prefs={reminders:true,offsetMinutes:1,showTitles:false,sound:false};
   window.webkit={messageHandlers:{grafNotificationSettings:{postMessage:async data=>{
    if(data.action==='set'){notificationWrites.push(data);prefs[data.field]=data.value;}
    return {version:1,preferences:prefs,canEdit:true,canRequestPermission:false,permission:'Разрешено'};
   }}}};
  },canManageDefault);
  await extra.addScriptTag({path:path.join(assets,'settings-autosave.js')});
  await extra.addScriptTag({path:path.join(assets,'cabinet.js')});
  await extra.evaluate(()=>window.GRAFNotificationSettings.connect('synthetic-notifications'));
  const defaultField=extra.getByRole('combobox',{name:'Формат по умолчанию',exact:true});
  assert.equal(await defaultField.count(),1,'Accessible name must exclude transient loading help');
  assert.equal(await defaultField.getAttribute('aria-describedby'),'summary-default-help');
  assert.equal(await extra.locator('#summary-default-help').textContent(),'Загружаем доступные форматы…');
  await extra.evaluate(()=>releaseSummary());
  await extra.waitForFunction(()=>document.querySelector('[data-summary-default-help]').textContent!=='Загружаем доступные форматы…');
  assert.equal(await defaultField.count(),1,'Accessible name stays stable after loading');
  assert.equal(await defaultField.inputValue(),'Кратко','Loaded default must be shown even when read-only');
  assert.equal(await defaultField.isDisabled(),!canManageDefault);
  assert.equal(await extra.locator('[data-summary-default-template]').inputValue(),'brief');
  assert.equal(await extra.evaluate(()=>savedDefault),null,'Loading must not save the default');
  if (!canManageDefault) { await extra.close(); continue; }
  await defaultField.fill('Авто'); await defaultField.press('Enter');
  await extra.waitForFunction(()=>savedDefault?.template_key==='auto');
  await defaultField.fill('Кратко'); await defaultField.press('Enter');
  await extra.waitForFunction(()=>savedDefault?.template_key==='brief');
  await extra.getByRole('button',{name:'Создать формат',exact:true}).click();
  const modal=extra.locator('dialog');
  const modalLanguage=modal.getByRole('combobox',{name:'Язык',exact:true});
  await modalLanguage.fill('Eng'); await modalLanguage.press('ArrowDown'); await modalLanguage.press('Enter');
  assert.equal(await modal.locator('select[name=output_language]').inputValue(),'en');
  const detail=modal.getByRole('combobox',{name:'Подробность',exact:true});
  await detail.click(); await extra.getByRole('listbox').getByRole('option',{name:'Подробно',exact:true}).click();
  assert.equal(await modal.locator('select[name=detail_level]').inputValue(),'detailed');
  await modal.getByRole('button',{name:'Отмена',exact:true}).click();
  assert.equal(await modal.isVisible(),false);
  const offset=extra.getByRole('combobox',{name:'Когда напоминать',exact:true});
  // Settle scrolling before typing: viewport movement intentionally cancels open menus.
  await offset.scrollIntoViewIfNeeded();
  await extra.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  await offset.fill('За 5'); assert.equal(await extra.evaluate(()=>notificationWrites.length),0);
  await offset.press('ArrowDown'); await offset.press('Enter');
  await extra.waitForFunction(()=>prefs.offsetMinutes===5);
  assert.equal(await extra.evaluate(()=>notificationWrites.length),1);
  await extra.getByRole('switch',{name:'Напоминать о встречах',exact:true}).uncheck();
  await extra.waitForFunction(()=>document.querySelector('input[aria-label="Когда напоминать"]').disabled);
  await extra.getByRole('switch',{name:'Напоминать о встречах',exact:true}).check();
  await extra.waitForFunction(()=>!document.querySelector('input[aria-label="Когда напоминать"]').disabled);
  assert.equal(await offset.inputValue(),'За 5 минут');
  await extra.waitForFunction(()=>!GRAFSettings.pending());
  const writesBeforeDisconnect=await extra.evaluate(()=>notificationWrites.length);
  await offset.click();
  await extra.evaluate(()=>window.GRAFNotificationSettings.disconnect());
  assert.equal(await offset.inputValue(),'','Disconnect must clear the previous account reminder label');
  assert.equal(await offset.isDisabled(),true);
  assert.equal(await offset.getAttribute('aria-expanded'),'false');
  assert.equal(await extra.evaluate(()=>notificationWrites.length),writesBeforeDisconnect,'Disconnect must not save');
  await extra.evaluate(()=>{prefs.offsetMinutes=1;window.GRAFNotificationSettings.connect('next-synthetic-nonce');});
  await extra.waitForFunction(()=>document.querySelector('input[aria-label="Когда напоминать"]').value==='За минуту');
  assert.equal(await offset.isDisabled(),false);
  assert.equal(await extra.evaluate(()=>notificationWrites.length),writesBeforeDisconnect,'Reconnect read must not save');
  await offset.fill('За 5');await offset.press('Enter');
  await extra.waitForFunction(()=>prefs.offsetMinutes===5&&!GRAFSettings.pending());
  assert.equal(await extra.evaluate(()=>notificationWrites.at(-1).nonce),'next-synthetic-nonce','Reconnected editor uses the new queue');
  const writesBeforeQueuedDisconnect=await extra.evaluate(()=>notificationWrites.length);
  await extra.evaluate(()=>{
   const input=document.querySelector('[data-local-notification-field=sound]');input.checked=true;input.dispatchEvent(new Event('change',{bubbles:true}));
   GRAFNotificationSettings.disconnect();
  });
  await extra.waitForTimeout(100);
  assert.equal(await extra.evaluate(()=>notificationWrites.length),writesBeforeQueuedDisconnect,'Disconnect cancels queued old-context writes');
  assert.equal(await extra.evaluate(()=>GRAFSettings.pending()),false,'Disconnected queue cannot block leaving the page');
  await extra.close();
  }

  // Opening a saved middle/last option must not silently select the first one.
  const selection=await browser.newPage(); selection.setDefaultTimeout(5000);
  selection.on('pageerror',error=>errors.push(error.message));
  await selection.setContent('<label>Правило<select data-settings-combobox id="rule"><option value="first">Первое</option><option value="middle" selected>Среднее</option><option value="blocked" disabled>Недоступное</option><option value="last">Последнее</option></select></label>');
  await selection.addStyleTag({path:path.join(assets,'cabinet.css')});
  await selection.evaluate(()=>{window.changes=0;document.querySelector('#rule').addEventListener('change',()=>changes++);});
  await selection.addScriptTag({path:path.join(assets,'cabinet.js')});
  const rule=selection.getByRole('combobox',{name:'Правило',exact:true});
  const ruleSource=selection.locator('#rule');
  const ruleToggle=selection.getByRole('button',{name:'Показать варианты',exact:true});
  const setRule=async value=>{
   await ruleSource.evaluate((el,value)=>{el.value=value;el.dispatchEvent(new Event('change'));},value);
  };
  for(const value of ['middle','last']){
   for(const trigger of [rule,ruleToggle]){
    await setRule(value);
    const before=await selection.evaluate(()=>changes);
    await trigger.click(); await rule.press('Enter');
    assert.equal(await ruleSource.inputValue(),value,'Opening and Enter must preserve the saved option');
    assert.equal(await selection.evaluate(()=>changes),before,'Confirming the saved option must not dispatch change');
   }
  }
  await setRule('middle');
  await rule.press('ArrowDown'); await rule.press('Enter');
  assert.equal(await ruleSource.inputValue(),'last','Opening with ArrowDown advances from saved option and skips disabled');
  await rule.press('ArrowUp'); await rule.press('Enter');
  assert.equal(await ruleSource.inputValue(),'middle','Opening with ArrowUp advances from saved option and skips disabled');
  await rule.click();
  await ruleSource.evaluate(el=>el.options[2].disabled=true);
  await rule.press('Enter');
  assert.equal(await ruleSource.inputValue(),'middle','Unchanged source refresh must preserve the saved active option');
  await rule.click(); await rule.press('ArrowDown');
  await ruleSource.evaluate(el=>el.options[2].setAttribute('disabled',''));
  await rule.press('Enter');
  assert.equal(await ruleSource.inputValue(),'last','Unchanged refresh must preserve keyboard navigation');
  await rule.click();
  await ruleSource.evaluate(el=>el.options[3].disabled=true);
  await rule.press('Enter');
  assert.notEqual(await ruleSource.inputValue(),'last','A newly disabled active option must not be selected');
  await rule.fill('Сре');
  const beforeInput=await selection.evaluate(()=>changes);
  await ruleSource.evaluate(el=>el.add(new Option('Новое','new')));
  assert.equal(await rule.inputValue(),'Сре','Catalog refresh keeps the query');
  assert.equal(await rule.getAttribute('aria-activedescendant'),null,'Typing does not activate a saved option');
  assert.equal(await selection.evaluate(()=>changes),beforeInput);
  await rule.press('Enter'); assert.equal(await ruleSource.inputValue(),'middle');
  await selection.close();
  assert.deepEqual(errors,[]);
  console.log(`${engine.name()}: settings coverage, app filter/bulk, explicit selection, keyboard/IME, reset, disabled/catalog updates, 600 options (${ms.toFixed(1)}ms), narrow layout passed`);
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
