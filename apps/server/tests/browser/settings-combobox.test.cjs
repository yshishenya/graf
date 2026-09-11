const { chromium, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
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
  const errors=[]; page.on('pageerror',error=>errors.push(error.message));
  await page.setContent(`<meta charset="utf-8"><main class="settings-page"><h1>Запись</h1>${recording}
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
  await page.addScriptTag({path:path.join(assets,'cabinet.js')});
  await page.evaluate(()=>window.GRAFRecordingSettings.connect('synthetic-nonce'));
  await page.waitForFunction(()=>document.querySelectorAll('[data-recording-target]').length===3);
  const apps=page.getByRole('combobox',{name:'Приложения',exact:true});
  const options=page.getByRole('listbox').getByRole('option');
  await apps.click(); assert.equal(await options.count(),3);
  await options.filter({hasText:'Microsoft Teams'}).click();
  assert.equal(await apps.inputValue(),'Microsoft Teams');
  assert.equal(await apps.getAttribute('aria-expanded'),'false');
  assert.equal(await page.locator('[data-recording-settings-targets] label:visible').count(),1);
  await apps.fill('zOo'); assert.equal(await options.count(),1);
  assert.equal(await page.locator('[data-recording-settings-targets] label:visible').count(),1);
  const callsBefore=await page.evaluate(()=>calls.length);
  await apps.press('ArrowDown'); await apps.press('Enter');
  assert.equal(await apps.inputValue(),'Zoom');
  assert.equal(await page.evaluate(()=>calls.length),callsBefore);
  const bulk=page.getByRole('combobox',{name:'Автозапись для всех приложений'});
  await bulk.click(); await options.filter({hasText:'Никогда'}).click();
  await page.waitForFunction(()=>targets.every(t=>t.rule==='never'));
  assert.equal(await apps.inputValue(),'Zoom');
  assert.equal(await page.locator('[data-recording-settings-targets] label:visible').count(),1);
  await apps.fill('');
  assert.equal(await page.locator('[data-recording-settings-targets] label:visible').count(),3);
  await apps.fill('нет такого приложения'); assert.equal(await options.count(),0);
  await apps.press('Enter'); assert.equal(await apps.inputValue(),'нет такого приложения');
  await apps.fill(''); await apps.press('Tab');

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
  await language.click(); assert.equal(await options.count(),3);
  await language.press('ArrowDown'); await language.press('ArrowDown');
  assert.equal(await original.inputValue(),'ru');
  await language.press('Enter'); assert.equal(await original.inputValue(),'en');
  assert.equal(await language.getAttribute('aria-expanded'),'false');
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
  for(const filename of fs.readdirSync(path.join(cabinet,'templates/cabinet/pages')).filter(name=>name.startsWith('settings_'))){
   const template=fs.readFileSync(path.join(cabinet,'templates/cabinet/pages',filename),'utf8');
   assert(!/<select(?![^>]*data-settings-combobox)/.test(template),`Unconverted select: ${filename}`);
   assert(!template.includes('data-timezone-search'),`Separate search: ${filename}`);
  }
  const extra=await browser.newPage(); extra.setDefaultTimeout(5000);
  extra.on('pageerror',error=>errors.push(error.message));
  const summarySource=fs.readFileSync(path.join(cabinet,'templates/cabinet/pages/settings_summaries_content.html'),'utf8');
  const notificationSource=fs.readFileSync(path.join(cabinet,'templates/cabinet/pages/settings_notifications_content.html'),'utf8').split('{% if embedded %}')[1].split('{% else %}')[0];
  await extra.setContent(`<section data-summary-template-settings data-template-endpoint="/templates" data-summary-default-endpoint="/default">
   <label>Формат новых итогов<select data-settings-combobox data-summary-default-template disabled><option value="auto">Авто</option><option value="brief">Кратко</option></select></label>
   <button data-summary-template-create>Создать формат</button>${summarySource.match(/<dialog[\s\S]*?<\/dialog>/)[0]}</section>${notificationSource}`);
  await extra.addStyleTag({path:path.join(assets,'cabinet.css')});
  await extra.evaluate(()=>{
   window.savedDefault=null; window.notificationWrites=[];
   window.fetch=async (url,options={})=>{
    if(options.method==='PUT') window.savedDefault=JSON.parse(options.body);
    return {ok:true,status:200,json:async()=>({personal:[],can_manage_default:true,default_template_key:'auto'})};
   };
   window.prefs={reminders:true,offsetMinutes:1,showTitles:false,sound:false};
   window.webkit={messageHandlers:{grafNotificationSettings:{postMessage:async data=>{
    if(data.action==='set'){notificationWrites.push(data);prefs[data.field]=data.value;}
    return {version:1,preferences:prefs,canEdit:true,canRequestPermission:false,permission:'Разрешено'};
   }}}};
  });
  await extra.addScriptTag({path:path.join(assets,'cabinet.js')});
  await extra.evaluate(()=>window.GRAFNotificationSettings.connect('synthetic-notifications'));
  const defaultField=extra.getByRole('combobox',{name:'Формат новых итогов',exact:true});
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
  await offset.fill('За 5'); assert.equal(await extra.evaluate(()=>notificationWrites.length),0);
  await offset.press('ArrowDown'); await offset.press('Enter');
  await extra.waitForFunction(()=>prefs.offsetMinutes===5);
  assert.equal(await extra.evaluate(()=>notificationWrites.length),1);
  await extra.getByRole('switch',{name:'Напоминать о встречах',exact:true}).uncheck();
  await extra.waitForFunction(()=>document.querySelector('input[aria-label="Когда напоминать"]').disabled);
  await extra.getByRole('switch',{name:'Напоминать о встречах',exact:true}).check();
  await extra.waitForFunction(()=>!document.querySelector('input[aria-label="Когда напоминать"]').disabled);
  assert.equal(await offset.inputValue(),'За 5 минут');
  await extra.close();
  assert.deepEqual(errors,[]);
  console.log(`${engine.name()}: settings coverage, app filter/bulk, explicit selection, keyboard/IME, reset, disabled/catalog updates, 600 options (${ms.toFixed(1)}ms), narrow layout passed`);
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
