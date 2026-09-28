// Run against tests.fixtures.settings_visual_ui_harness (synthetic data only).
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
// Contract-only mode executes the shipped notification JS without opening a browser or app.
if(process.argv.includes('--notification-contract')){
 const {test}=require('node:test');
 const vm=require('node:vm');
 const cabinet=path.join(__dirname,'../../src/twobrain_rec_server/cabinet');
 const source=fs.readFileSync(path.join(cabinet,'static/cabinet/cabinet.js'),'utf8');
 const notificationSource=source.slice(source.indexOf('  let notificationSettingsNonce ='),source.indexOf('  const initSettingsFormState ='));
 const snapshot=()=>({version:2,preferences:{reminders:true,offsetMinutes:1,showTitles:false,sound:false,quiet:false},canEdit:true,message:''});
 const settle=async()=>{for(let i=0;i<12;i++)await new Promise(resolve=>setImmediate(resolve));};
 const fixture=(reply=async()=>snapshot(),{realQueue=false}={})=>{
  const element=()=>({hidden:false,disabled:true,dataset:{},textContent:'',listeners:new Map(),addEventListener(name,fn){this.listeners.set(name,fn);},setAttribute(){},getAttribute(){return null;}});
  const controls=element(),status=element(),retry=element(),reload=element();
  const preview={...element(),dataset:{localNotificationAction:'test'}};
  const fields=['reminders','offsetMinutes','showTitles','sound','quiet'].map(field=>({...element(),dataset:{localNotificationField:field},type:field==='offsetMinutes'?'select-one':'checkbox',checked:false,value:''}));
  controls.querySelectorAll=selector=>selector==='[data-local-notification-field]'?fields:selector==='[data-local-notification-action]'||selector==='[data-local-notification-action="test"]'?[preview]:[];
  const nodes={'[data-local-notification-controls]':controls,'[data-local-notification-status]':status,'[data-local-notification-retry]':retry,'[data-local-notification-reload]':reload};
  const listeners=new Map();
  const root={dataset:{},isConnected:true,querySelector:selector=>nodes[selector]??null,querySelectorAll:()=>fields,
   addEventListener(name,fn){listeners.set(name,fn);},dispatchEvent(event){listeners.get(event.type)?.(event);}};
  const requests=[];let queueOptions,actualQueue,disposed=false;
  const window={addEventListener(){},webkit:{messageHandlers:{grafNotificationSettings:{postMessage:async request=>{requests.push(request);return reply(request);}}}},
   GRAFSettings:{headers:()=>({'X-Graf-Expected-Actor':'synthetic','X-Graf-Expected-Workspace':'synthetic'}),offerRemote(){},create(_id,options){queueOptions=options;return {pending:()=>false,refresh(){},dispose(){disposed=true;},edit(){},flush:async()=>true};}}};
  const document={querySelector:selector=>selector.startsWith('meta[')?{content:'synthetic'}:root,querySelectorAll:()=>[],addEventListener(){}};
  const context=vm.createContext({window,document,Event,setTimeout,clearTimeout,initSettingsComboboxes(){},settingsCombos:new Map()});
  if(realQueue){
   vm.runInContext(fs.readFileSync(path.join(cabinet,'static/cabinet/settings-autosave.js'),'utf8'),context);
   const create=window.GRAFSettings.create;
   window.GRAFSettings.create=(id,options)=>{queueOptions=options;actualQueue=create(id,options);return actualQueue;};
  }
  vm.runInContext(notificationSource,context);
  window.GRAFNotificationSettings.connect('current');
  return {window,root,controls,fields,status,preview,requests,ready:settle(),options:()=>queueOptions,queue:()=>actualQueue,disposed:()=>disposed};
 };
 test('F277 template exposes exactly five preferences and one preview action',()=>{
  const html=fs.readFileSync(path.join(cabinet,'templates/cabinet/pages/settings_notifications_content.html'),'utf8').split('{% if embedded %}')[1].split('{% else %}')[0];
  const fields=[...html.matchAll(/(?:local_notification_field|data-local-notification-field)="([^"]+)"/g)].map(match=>match[1]);
  assert.deepEqual(fields.sort(),['offsetMinutes','quiet','reminders','showTitles','sound']);
  assert.deepEqual([...html.matchAll(/data-local-notification-action="([^"]+)"/g)].map(match=>match[1]),['test']);
  assert(!/data-local-notification-permission|разрешение macOS|Настройки macOS/.test(html));
 });
 test('F277 read uses version 2 and renders defaults without permission status',async()=>{
  const f=fixture();await f.ready;
  assert.equal(f.requests[0].version,2);
  assert.deepEqual(Object.keys(f.requests[0]).sort(),['action','nonce','version']);
  assert.equal(f.controls.disabled,false);
  assert.equal(f.fields.find(field=>field.dataset.localNotificationField==='quiet').checked,false);
 });
 test('F277 rejects old and malformed native responses',async()=>{
  const cases=[{version:1}, {permission:'Разрешено'}, {canRequestPermission:true}, {canEdit:'yes'}, {message:null}, {preferences:{...snapshot().preferences,quiet:undefined}}, {preferences:{...snapshot().preferences,quiet:1}}, {preferences:{...snapshot().preferences,unknown:true}}, {preferences:{...snapshot().preferences,offsetMinutes:2}}];
  for(const patch of cases){const f=fixture(async()=>({...snapshot(),...patch}));await f.ready;assert.equal(f.controls.disabled,true,JSON.stringify(patch));assert(f.status.textContent);}
 });
 test('F277 writes are serialized and a failed save never acknowledges success',async()=>{
  let active=0,maxActive=0;const state=snapshot();
  const f=fixture(async request=>{
   if(request.action==='set'){active++;maxActive=Math.max(active,maxActive);await settle();active--;state.preferences[request.field]=request.value;}
   return structuredClone(state);
  });await f.ready;assert(f.options(),'version 2 must establish the editor');
  const saved=await f.options().save({quiet:true,sound:true},state.preferences);
  assert.equal(saved.saved,true);assert.equal(maxActive,1);
  assert.equal(saved.values.quiet,true);assert.equal(saved.values.sound,true);
  for(const request of f.requests){assert.equal(request.version,2);assert.equal(request.nonce,'current');}
  const failed=fixture(async request=>request.action==='set'?{...snapshot(),error:'Не удалось сохранить настройки.'}:snapshot());
  await failed.ready;await assert.rejects(failed.options().save({quiet:true},snapshot().preferences));
 });
 test('F277 preview sends only the test action and shows the presenter result',async()=>{
  const f=fixture(async request=>({...snapshot(),message:request.action==='test'?'Сначала ответьте на вопрос о записи.':''}));
  await f.ready;f.preview.listeners.get('click')();await settle();
  const request=f.requests.at(-1);
  assert.equal(request.action,'test');assert.equal(request.version,2);
  assert.deepEqual(Object.keys(request).sort(),['action','nonce','version']);
  assert.equal(f.status.textContent,'Сначала ответьте на вопрос о записи.');
  assert.equal(f.requests.filter(request=>request.action==='set').length,0);
 });
 test('F277 disconnect prevents a late response restoring another account',async()=>{
  let release;const f=fixture(()=>new Promise(resolve=>{release=resolve;}));
  await settle();
  f.window.GRAFNotificationSettings.disconnect();
  release({...snapshot(),preferences:{...snapshot().preferences,quiet:true,sound:true}});
  await f.ready;assert.equal(f.controls.disabled,true);
  assert(f.fields.filter(field=>field.type==='checkbox').every(field=>field.checked===false));
  assert.match(f.status.textContent,/Аккаунт изменился/);
 });
 test('F277 real autosave preserves the draft after failure and blocks preview until confirmed',async()=>{
  let fail=true;const state=snapshot();
  const f=fixture(async request=>{
   if(request.action==='set'){
    if(fail)return {...snapshot(),error:'Не удалось сохранить настройки.'};
    state.preferences[request.field]=request.value;
   }
   return structuredClone(state);
  },{realQueue:true});await f.ready;
  const quiet=f.fields.find(field=>field.dataset.localNotificationField==='quiet');
  quiet.checked=true;f.root.dispatchEvent({type:'change',target:quiet});
  assert.equal(await f.window.GRAFSettings.flushAll(),false);
  assert.equal(quiet.checked,true);assert.equal(state.preferences.quiet,false);
  assert.equal(f.root.dataset.state,'error');assert(!f.status.textContent.includes('Сохранено'));
  f.preview.listeners.get('click')();await settle();
  assert.equal(f.requests.some(request=>request.action==='test'),false);
  fail=false;await f.queue().retry();
  assert.equal(state.preferences.quiet,true);assert.equal(f.window.GRAFSettings.pending(),false);
  assert.equal(f.status.textContent,'Сохранено');
  f.window.GRAFNotificationSettings.disconnect();
 });
 test('F277 real autosave merges rapid edits and serializes all field writes',async()=>{
  let active=0,maxActive=0;const state=snapshot();
  const f=fixture(async request=>{
   if(request.action==='set'){active++;maxActive=Math.max(maxActive,active);await settle();state.preferences[request.field]=request.value;active--;}
   return structuredClone(state);
  },{realQueue:true});await f.ready;
  for(const field of ['quiet','sound']){
   const input=f.fields.find(input=>input.dataset.localNotificationField===field);
   input.checked=true;f.root.dispatchEvent({type:'change',target:input});
  }
  assert.equal(await f.window.GRAFSettings.flushAll(),true);
  assert.equal(maxActive,1);assert.equal(state.preferences.quiet,true);assert.equal(state.preferences.sound,true);
  assert.deepEqual(f.requests.filter(request=>request.action==='set').map(request=>request.field),['sound','quiet']);
  f.window.GRAFNotificationSettings.disconnect();
 });
 test('F277 reconnect cannot send an old draft through the next nonce',async()=>{
  let release;const state=snapshot();
  const f=fixture(async request=>{
   if(request.action==='set')await new Promise(resolve=>{release=resolve;});
   return structuredClone(state);
  },{realQueue:true});await f.ready;
  const oldOptions=f.options();f.queue().edit({quiet:true,sound:true},500);
  const saving=f.window.GRAFSettings.flushAll();await settle();
  f.window.GRAFNotificationSettings.disconnect();
  f.window.GRAFNotificationSettings.connect('next');await settle();
  release();await saving;await settle();
  assert.equal(f.requests.filter(request=>request.action==='set').length,1,'Only already dispatched mutation may finish');
  await assert.rejects(oldOptions.save({quiet:true}));
  assert.equal(f.window.GRAFSettings.pending(),false);
  assert.equal(f.controls.disabled,false);assert(f.fields.filter(field=>field.type==='checkbox'&&field.dataset.localNotificationField!=='reminders').every(field=>!field.checked));
  f.window.GRAFNotificationSettings.disconnect();
 });
 test('F277 unavailable context cannot edit preferences or start preview',async()=>{
  const f=fixture(async()=>({...snapshot(),canEdit:false}),{realQueue:true});await f.ready;
  assert.equal(f.controls.disabled,true);assert.match(f.status.textContent,/недоступны/);
  const input=f.fields.find(field=>field.dataset.localNotificationField==='quiet');
  input.checked=true;f.root.dispatchEvent({type:'change',target:input});
  f.preview.listeners.get('click')();await settle();
  assert.equal(f.window.GRAFSettings.pending(),false);
  assert(f.requests.every(request=>request.action==='read'));
  f.window.GRAFNotificationSettings.disconnect();
 });
 test('F277 pending preview cannot replace the account-change message',async()=>{
  let release;const f=fixture(request=>request.action==='test'?new Promise(resolve=>{release=resolve;}):Promise.resolve(snapshot()));
  await f.ready;f.preview.listeners.get('click')();await settle();
  f.window.GRAFNotificationSettings.disconnect();
  release({...snapshot(),message:'Проверочное уведомление показано.'});await settle();
  assert.match(f.status.textContent,/Аккаунт изменился/);assert.equal(f.controls.disabled,true);
 });
 for(const action of ['read','test']){
  test(`F277 late ${action} response preserves a newer draft and its save status`,async()=>{
   let releaseResponse,releaseSave,reads=0,failSave=true;
   const state=snapshot();
   const f=fixture(async request=>{
    if((action==='read'&&request.action==='read'&&++reads===2)||(action==='test'&&request.action==='test')){
     const old=structuredClone(state);old.message='Ответ до изменения настройки';
     await new Promise(resolve=>{releaseResponse=resolve;});return old;
    }
    if(request.action==='set'){
     if(failSave){await new Promise(resolve=>{releaseSave=resolve;});return {...structuredClone(state),error:'Не удалось сохранить настройки.'};}
     state.preferences[request.field]=request.value;
    }
    return structuredClone(state);
   },{realQueue:true});await f.ready;
   let saving;
   try{
    if(action==='read')f.window.GRAFNotificationSettings.refresh();else f.preview.listeners.get('click')();
    await settle();assert.equal(typeof releaseResponse,'function');
    const quiet=f.fields.find(field=>field.dataset.localNotificationField==='quiet');
    quiet.checked=true;f.root.dispatchEvent({type:'change',target:quiet});
    saving=f.window.GRAFSettings.flushAll();await settle();
    assert.equal(quiet.checked,true);assert.equal(f.root.dataset.state,'saving');
    releaseResponse();await settle();
    assert.equal(quiet.checked,true,'The older response must not replace the newer visible draft');
    assert.equal(f.window.GRAFSettings.pending(),true);
    assert.equal(f.status.textContent,'Сохраняем…','The older response must not replace the current save status');
    assert.equal(state.preferences.quiet,false,'The changed setting is not confirmed yet');
    releaseSave();assert.equal(await saving,false);
    assert.equal(quiet.checked,true);assert.equal(f.root.dataset.state,'error');
    assert.match(f.status.textContent,/Не удалось сохранить/);
    failSave=false;await f.queue().retry();
    assert.equal(state.preferences.quiet,true);assert.equal(quiet.checked,true);
    assert.equal(f.window.GRAFSettings.pending(),false);assert.equal(f.status.textContent,'Сохранено');
    assert(f.requests.every(request=>request.version===2&&request.nonce==='current'));
   }finally{
    f.window.GRAFNotificationSettings.disconnect();releaseResponse?.();await settle();releaseSave?.();await saving;
   }
  });
 }
 for(const action of ['read','test'])for(const pending of [false,true])for(const canEdit of [false,true])for(const scope of ['current','new-nonce','new-generation']){
  test(`F277 response matrix ${action} pending=${pending} canEdit=${canEdit} scope=${scope}`,async()=>{
   let native=snapshot(),reads=0,deferred=false,releaseResponse,releaseSave,saving;
   const remote={...snapshot(),canEdit,preferences:{...snapshot().preferences,quiet:!pending,sound:true}};
   const f=fixture(async request=>{
    if(!deferred&&request.action===action&&(action==='test'||++reads===2)){
     deferred=true;native=structuredClone(remote);
     await new Promise(resolve=>{releaseResponse=resolve;});return structuredClone(remote);
    }
    if(request.action==='set'){
     assert.equal(native.canEdit,true,'No mutation is sent for a read-only context');
     if(pending)await new Promise(resolve=>{releaseSave=resolve;});
     native.preferences[request.field]=request.value;
    }
    return structuredClone(native);
   },{realQueue:true});await f.ready;
   try{
    if(action==='read')f.window.GRAFNotificationSettings.refresh();else f.preview.listeners.get('click')();
    await settle();assert.equal(typeof releaseResponse,'function');
    const quiet=f.fields.find(field=>field.dataset.localNotificationField==='quiet');
    if(pending){
     quiet.checked=true;f.root.dispatchEvent({type:'change',target:quiet});
     saving=f.window.GRAFSettings.flushAll();await settle();
    }
    assert.equal(f.requests.filter(request=>request.action==='set').length,0,'Read/test and queued drafts do not send unsolicited writes');
    if(scope!=='current'){
     f.window.GRAFNotificationSettings.disconnect();native=snapshot();
     const nextNonce=scope==='new-nonce'?'next':'current';
     f.window.GRAFNotificationSettings.connect(nextNonce);await settle();
     releaseResponse();await settle();await saving;
     assert.equal(quiet.checked,false,'Old response cannot restore an old preference');
     assert.equal(f.queue().attach({}).quiet,false);
     assert.equal(f.controls.disabled,false,'Old canEdit cannot disable the current account');
     assert.equal(f.window.GRAFSettings.pending(),false);
     assert.equal(f.requests.filter(request=>request.action==='set').length,0);
     assert.equal(f.requests.at(-1).nonce,nextNonce);
     return;
    }
    releaseResponse();await settle();
    assert.equal(f.controls.disabled,!canEdit);
    assert.equal(quiet.checked,true,'Render preserves pending draft or adopts confirmed native values');
    assert.equal(f.queue().attach({}).quiet,true,'Visible value and queue draft must agree');
    if(pending){
     assert.equal(f.window.GRAFSettings.pending(),true);
     if(canEdit){
      assert.equal(f.status.textContent,'Сохраняем…');
      releaseSave();assert.equal(await saving,true);
      assert.equal(native.preferences.quiet,true);assert.equal(native.preferences.sound,true);
     }else{
      assert.equal(await saving,false);assert.equal(native.preferences.quiet,false);
      assert.equal(f.requests.filter(request=>request.action==='set').length,0);
      assert(!f.status.textContent.includes('Сохранено'));
     }
    }else{
     assert.equal(f.queue().attach({}).sound,true);
     assert.equal(f.window.GRAFSettings.pending(),false);
     assert.equal(f.requests.filter(request=>request.action==='set').length,0,'Applying a native snapshot never saves');
     quiet.checked=false;f.root.dispatchEvent({type:'change',target:quiet});
     assert.equal(await f.window.GRAFSettings.flushAll(),true);
     if(canEdit){assert.equal(native.preferences.quiet,false);assert.equal(native.preferences.sound,true);}
    }
    const writes=f.requests.filter(request=>request.action==='set');
    assert.equal(writes.length,canEdit?1:0,'One explicit edit yields exactly one mutation, with no duplicate edit');
    if(canEdit){assert.equal(writes[0].field,'quiet');assert.equal(writes[0].value,pending);}
    assert(f.requests.every(request=>request.version===2&&request.nonce==='current'));
   }finally{
    f.window.GRAFNotificationSettings.disconnect();releaseResponse?.();await settle();releaseSave?.();await saving;
   }
  });
 }
}else{
const {chromium}=require('playwright');
const origin=process.env.SETTINGS_PREVIEW_URL||'http://127.0.0.1:8874';
const pages=['account','workspace','recording','summaries','integrations/calendar','notifications','billing'];
(async()=>{
 const browser=await chromium.launch({headless:true});let checks=0;
 try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
   const targets=[{id:'zoom',name:'Zoom',rule:'ask'},{id:'teams',name:'Microsoft Teams',rule:'never'}];
   const preferences={reminders:true,offsetMinutes:1,showTitles:false,sound:false,quiet:false};
   window.webkit={messageHandlers:{
    grafRecordingSettings:{postMessage:async()=>({version:1,targets})},
    grafNotificationSettings:{postMessage:async request=>{if(request.version!==2)throw Error('Обновите окно настроек');return {version:2,preferences,canEdit:true,message:''};}}
   }};
   document.addEventListener('DOMContentLoaded',()=>{window.GRAFRecordingSettings?.connect('synthetic');window.GRAFNotificationSettings?.connect('synthetic');});
  });
  const signatures={};
  for(const surface of ['web','desktop'])for(const theme of ['light','dark','system'])for(const width of [1440,1024,768,540,360])for(const route of pages){
   await page.emulateMedia({colorScheme:'dark'});await page.setViewportSize({width,height:900});
   const response=await page.goto(`${origin}/${surface==='desktop'?'desktop/':''}settings/${route}?theme=${theme}`);assert.equal(response.status(),200,route);
   if(surface==='desktop'&&route==='recording')await page.locator('[data-recording-target]').first().waitFor({state:'attached'});
   if(surface==='desktop'&&route==='notifications')await page.waitForFunction(()=>!document.querySelector('[data-local-notification-controls]').disabled);
   if(route==='summaries')await page.waitForFunction(()=>!document.querySelector('[data-summary-default-template]').disabled);
   const result=await page.evaluate(()=>{
    const scope=document.querySelector('.settings-page,.calendar-settings');
    const visible=el=>el.getClientRects().length>0;
    const style=(el,props)=>Object.fromEntries(props.map(p=>[p,getComputedStyle(el)[p]]));
    const controls=[...scope.querySelectorAll('input[role=combobox], input[type=text], input[type=password], input[type=url]')].filter(visible);
    const buttons=[...scope.querySelectorAll('.button')].filter(visible);
    return {overflow:document.documentElement.scrollWidth>innerWidth,
     title:style(scope.querySelector('h1'),['fontSize']),
     headings:[...scope.querySelectorAll('section>h2,section>.settings-section__heading h2,section>.calendar-section-head h2')].filter(visible).map(el=>style(el,['fontSize'])),
     controls:controls.map(el=>style(el,['minHeight','borderRadius','fontSize'])),
     buttons:buttons.map(el=>style(el,['minHeight','borderRadius','fontSize'])),
     switches:[...scope.querySelectorAll('.cabinet-switch__track')].filter(visible).map(el=>style(el,['width','height','borderRadius'])),
     surface:style(document.querySelector('.cabinet-main'),['backgroundColor','color']),
     unnamed:controls.filter(el=>!el.getAttribute('aria-label')&&!el.labels?.length&&!el.getAttribute('aria-labelledby')).length};
   });
   const label=`${surface} ${route} ${theme} ${width}`;
   assert(!result.overflow,`Overflow: ${label}`);assert.equal(result.title.fontSize,'20px',label);assert.equal(result.unnamed,0,label);
   assert(result.headings.every(s=>s.fontSize==='15px'),`Headings: ${label} ${JSON.stringify(result.headings)}`);
   for(const s of [...result.controls,...result.buttons])assert.deepEqual(s,{minHeight:'36px',borderRadius:'6px',fontSize:'13px'},label);
   if(result.switches.length){signatures.switch||=result.switches[0];assert(result.switches.every(s=>JSON.stringify(s)===JSON.stringify(signatures.switch)),`Switches: ${label}`);}
   assert.equal(await page.getByRole('button',{name:/^Сохранить$/}).count(),0,label);
   assert.equal(await page.locator('[data-settings-header]').count(),1,`Shared header: ${label}`);
   assert.equal(await page.locator('[data-settings-header] p,.settings-scope-badge').count(),0,`No introductory copy: ${label}`);
   if(theme!=='system')signatures[surface+route+width+theme]=result.surface;
   if(theme==='system'){
    assert.deepEqual(result.surface,signatures[surface+route+width+'dark'],`System dark: ${label}`);
    await page.emulateMedia({colorScheme:'light'});
    const light=await page.locator('.cabinet-main').evaluate(el=>({backgroundColor:getComputedStyle(el).backgroundColor,color:getComputedStyle(el).color}));
    assert.deepEqual(light,signatures[surface+route+width+'light'],`System light: ${label}`);
   }
   if(process.env.SCREENSHOT_DIR&&[1440,360].includes(width)&&theme!=='system'){
    fs.mkdirSync(process.env.SCREENSHOT_DIR,{recursive:true});await page.screenshot({path:`${process.env.SCREENSHOT_DIR}/${surface}-${route.replaceAll('/','-')}-${theme}-${width}.png`,fullPage:true});
   }
   checks++;
  }
  // At 200%, a 720 CSS-pixel viewport has the available width of a 1440px desktop.
  await page.setViewportSize({width:720,height:450});
  for(const surface of ['web','desktop'])for(const route of pages){
   await page.goto(`${origin}/${surface==='desktop'?'desktop/':''}settings/${route}?theme=light`);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`200% reflow: ${route}`);
   checks++;
  }
  const dialogStyles=[];
  for(const route of ['summaries','integrations/calendar']){
   await page.setViewportSize({width:360,height:812});await page.goto(`${origin}/desktop/settings/${route}?theme=light`);
   if(route==='summaries')await page.getByRole('button',{name:'Создать формат',exact:true}).click();
   else {await page.locator('[data-calendar-add-source]>summary').click();await page.locator('[data-calendar-provider-open="calendar-provider-dialog-caldav_yandex"]').click();}
   const dialog=page.locator('dialog[open]');await dialog.waitFor();
   dialogStyles.push(await dialog.evaluate(el=>{const s=getComputedStyle(el);return [s.borderRadius,s.backgroundColor,s.boxShadow];}));
   assert(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth),'Dialog overflow');
   const controls=await dialog.locator('button:not(.settings-combobox__toggle),input:not([type=hidden]):not([type=checkbox]),select').evaluateAll(elements=>elements.filter(el=>el.getClientRects().length).map(el=>{const s=getComputedStyle(el);return {minHeight:s.minHeight,borderRadius:s.borderRadius,fontSize:s.fontSize};}));
   controls.forEach(style=>assert.deepEqual(style,{minHeight:'36px',borderRadius:'6px',fontSize:'13px'},'Dialog controls'));
   await page.keyboard.press('Escape');assert.equal(await dialog.count(),0);
  }
  assert.deepEqual(dialogStyles[0],dialogStyles[1],'Shared dialog surface');
  // Reused hints remain available from keyboard/touch without taking page space.
  for(const [route,id] of [['recording','recording-rules-help'],['summaries','summary-default-scope'],['notifications','notification-sound-help']]){
   await page.goto(`${origin}/desktop/settings/${route}?theme=light`);
   const hint=page.locator(`#${id}`), trigger=page.locator(`[popovertarget="${id}"]`);
   if(route==='recording'){
    const center=el=>{const r=el.getBoundingClientRect();return r.top+r.height/2;};
    assert(Math.abs(await trigger.evaluate(center)-await page.locator('#recording-rules-title').evaluate(center))<6,'Recording hint stays beside its heading on narrow screens');
   }
   assert(!await hint.isVisible(),'Hint is initially collapsed');
   await trigger.focus();await hint.waitFor({state:'visible'});
   assert(await hint.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight;}),'Hint fits viewport');
   await page.keyboard.press('Escape');assert(!await hint.isVisible(),'Escape closes hint');
   await trigger.click();await hint.waitFor({state:'visible'});await page.keyboard.press('Escape');
  }
  for(const width of [1440,360]){
   await page.setViewportSize({width,height:900});
   await page.goto(`${origin}/settings/billing?theme=dark&plan=free&payments=off`);
   assert.equal(await page.locator('[data-billing-primary]').count(),1,'One trial action when payments unavailable');
   assert.equal(await page.locator('a[href="/billing/plans"]').count(),0,'Unavailable payment is not offered');
   assert.equal(await page.locator('#billing-options-title,.settings-scope-badge').count(),0,'No duplicate plan section');
   const trial=page.locator('[data-trial-confirmation]');
   assert.equal(await trial.evaluate(el=>getComputedStyle(el).borderTopWidth),'0px','No lines around trial action');
   assert(!await trial.locator('form').isVisible(),'Trial requires explicit confirmation');
   await trial.locator('summary').click();assert(await trial.locator('form').isVisible());
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Free trial confirmation fits');
   if(process.env.SCREENSHOT_DIR)await page.screenshot({path:`${process.env.SCREENSHOT_DIR}/billing-free-dark-${width}.png`,fullPage:true});
  }
  // Account closure is explicit and compact, including without JavaScript.
  for(const javaScriptEnabled of [true,false]){
   const context=await browser.newContext({javaScriptEnabled});const closePage=await context.newPage();
   for(const width of [360,1024]){
    await closePage.setViewportSize({width,height:812});
    await closePage.goto(`${origin}/settings/account?theme=dark`);
    const section=closePage.locator('.account-close-card'), disclosure=section.locator('details');
    assert.equal(await section.locator('h2').count(),1,'One closure heading');
    assert(!await disclosure.locator('form').isVisible(),'Confirmation starts collapsed');
    await disclosure.locator('summary').focus();await closePage.keyboard.press('Enter');
    const field=closePage.getByLabel('Введите «Закрыть аккаунт»',{exact:true});
    assert(await field.isVisible(),'Phrase has a visible label');
    assert.equal(await field.getAttribute('required'),'');
    await field.fill('Неверная фраза');assert(!await field.evaluate(el=>el.checkValidity()));
    await field.fill('Закрыть аккаунт');assert(await field.evaluate(el=>el.checkValidity()));
    assert.equal(await disclosure.locator('form').getAttribute('method'),'post');
    assert.equal(await disclosure.locator('form[data-settings-autosave]').count(),0,'Closure never autosaves');
    assert(await closePage.getByRole('button',{name:'Закрыть через 7 дней',exact:true}).isVisible());
    assert(await closePage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Closure fits narrow width');
    if(javaScriptEnabled){
     const hint=closePage.locator('#account-close-access');
     await closePage.getByRole('button',{name:'Что будет с доступом и данными',exact:true}).click();
     assert(await hint.isVisible());await closePage.keyboard.press('Escape');assert(!await hint.isVisible());
    }
    await disclosure.locator('summary').click();assert(!await field.isVisible());
   }
   await context.close();
  }
  assert.deepEqual(errors,[]);
  console.log(`settings consistency: ${checks} page/theme/width cases, common controls, system dark, reflow, dialogs passed`);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
}
