const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const http=require('node:http');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html; charset=utf-8');res.end(`<meta name="graf-time-user" content="actor"><meta name="graf-workspace" content="space"><meta name="csrf-token" content="synthetic">
 <section data-summary-template-settings data-template-endpoint="/api/templates" data-summary-default-endpoint="/api/templates/default">
 <button data-summary-template-create>Создать формат</button><select aria-label="Формат" data-summary-default-template disabled><option value="auto">Авто</option><option value="short">Кратко</option></select><span data-summary-default-help></span>
 <div data-summary-personal-template-list></div><p data-summary-template-settings-status></p>
 <dialog data-summary-template-dialog><h2 data-summary-template-dialog-title></h2><form data-summary-template-form><input name="name" aria-label="Название" required maxlength="80"><textarea name="purpose" aria-label="Назначение" required></textarea><label><input name="sections" type="checkbox" value="summary" checked>Кратко</label><select name="output_language"><option>ru</option></select><select name="detail_level"><option>standard</option></select><p data-summary-template-form-error hidden></p><button type="button" data-summary-template-dialog-cancel>Отмена</button><button type="submit" data-summary-template-submit>Создать</button></form></dialog></section>`);});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const origin=`http://127.0.0.1:${server.address().port}`;
 let template={template_id:'id1',template_key:'personal',version:1,name:'Исходный',purpose:'Итоги',sections:['summary'],output_language:'ru',detail_level:'standard'},key='auto',patches=0,creates=0,fail=false,responseDelay=0;
 try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/templates**',async route=>{
   const req=route.request();assert.equal(req.headers()['x-graf-expected-actor'],'actor');let body;
   if(req.method()==='GET')body={actor:'actor',workspace:'space',personal:[template],can_manage_default:true,default_template_key:key};
   else if(req.method()==='PUT'){key=req.postDataJSON().template_key;body={actor:'actor',workspace:'space',template_key:key,version:1};}
   else if(req.method()==='PATCH'){
    if(fail){await route.fulfill({status:503,body:'{}'});return;}
    const data=req.postDataJSON();assert.equal(data.expected_version,template.version);assert(req.url().endsWith('/'+template.template_id));
    patches++;template={...template,...data,template_id:'id'+(patches+1),version:template.version+1};delete template.expected_version;
    body={...template,actor:'actor',workspace:'space'};
   }else {creates++;body={...template,actor:'actor',workspace:'space'};}
   if(responseDelay)await new Promise(resolve=>setTimeout(resolve,responseDelay));
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
  });
  await page.goto(origin);
  const assets=path.join(__dirname,'../../src/twobrain_rec_server/cabinet/static/cabinet');
  for(const file of ['settings-autosave.js','cabinet.js'])await page.addScriptTag({path:path.join(assets,file)});
  await page.waitForFunction(()=>!document.querySelector('[data-summary-default-template]').disabled);
  await page.locator('[data-summary-default-template]').selectOption('short');await page.waitForFunction(()=>!GRAFSettings.pending());assert.equal(key,'short');
  await page.locator('summary[aria-label^="Действия с форматом"]').click();await page.getByRole('button',{name:'Изменить',exact:true}).click();
  assert.equal(await page.locator('[data-summary-template-submit]').isVisible(),false);
  const name=page.getByLabel('Название',{exact:true});await name.fill('Новое');await name.press('Tab');await page.waitForFunction(()=>!GRAFSettings.pending());
  await name.fill('Последнее');await name.press('Tab');await page.waitForFunction(()=>!GRAFSettings.pending());assert.equal(template.name,'Последнее');assert.equal(patches,2);assert.equal(creates,0);
  await name.fill('');await name.press('Tab');assert.equal(await page.locator('dialog').isVisible(),true);
  page.once('dialog',d=>d.dismiss());await page.getByRole('button',{name:'Готово'}).click();assert.equal(await page.locator('dialog').isVisible(),true);
  await name.fill('Исправлено');await name.press('Tab');await page.waitForFunction(()=>!GRAFSettings.pending());
  fail=true;await name.fill('Повтор');await name.press('Tab');await page.getByRole('button',{name:'Повторить',exact:true}).waitFor();
  fail=false;await page.getByRole('button',{name:'Повторить',exact:true}).click();await page.waitForFunction(()=>!GRAFSettings.pending());assert.equal(template.name,'Повтор');
  responseDelay=300;await name.fill('До IME');await name.press('Tab');await page.getByText('Сохраняем…',{exact:true}).waitFor();
  await name.focus();await name.dispatchEvent('compositionstart');await name.fill('Составное название');
  await page.waitForTimeout(450);assert.equal(await name.inputValue(),'Составное название');
  await page.getByRole('button',{name:'Готово'}).click();assert(await page.locator('dialog').isVisible(),'Do not close during composition');
  await name.dispatchEvent('compositionend');await page.waitForFunction(()=>!GRAFSettings.pending());assert.equal(template.name,'Составное название');responseDelay=0;
  await page.getByRole('button',{name:'Готово'}).click();assert.equal(await page.locator('dialog').isVisible(),false);assert.deepEqual(errors,[]);
  await page.getByRole('button',{name:'Создать формат',exact:true}).click();
  await name.fill('Новый формат');await page.getByLabel('Назначение').fill('Назначение');await name.press('Enter');assert.equal(creates,0);
  await page.getByLabel('Назначение').press('Enter');assert((await page.getByLabel('Назначение').inputValue()).includes('\n'));
  await page.getByRole('button',{name:'Создать',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('dialog').open);assert.equal(creates,1);
  console.log('summary settings: default autosave, immutable revision IDs, edit without Save, invalid draft, close guard and retry passed');
 }finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
