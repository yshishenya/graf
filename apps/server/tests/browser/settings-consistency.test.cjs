// Run against tests.fixtures.settings_visual_ui_harness (synthetic data only).
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const origin=process.env.SETTINGS_PREVIEW_URL||'http://127.0.0.1:8874';
const pages=['account','workspace','recording','summaries','integrations/calendar','notifications','billing'];
(async()=>{
 const browser=await chromium.launch({headless:true});let checks=0;
 try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
   const targets=[{id:'zoom',name:'Zoom',rule:'ask'},{id:'teams',name:'Microsoft Teams',rule:'never'}];
   const preferences={reminders:true,offsetMinutes:1,showTitles:false,sound:false};
   window.webkit={messageHandlers:{
    grafRecordingSettings:{postMessage:async()=>({version:1,targets})},
    grafNotificationSettings:{postMessage:async()=>({version:1,preferences,canEdit:true,canRequestPermission:false,permission:'Разрешено'})}
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
   assert(!result.overflow,`Overflow: ${label}`);assert.equal(result.title.fontSize,'18px',label);assert.equal(result.unnamed,0,label);
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
  assert.deepEqual(errors,[]);
  console.log(`settings consistency: ${checks} page/theme/width cases, common controls, system dark, reflow, dialogs passed`);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
