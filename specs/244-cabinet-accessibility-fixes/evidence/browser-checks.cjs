/* Run with NODE_PATH pointing to the installed Playwright module. Synthetic loopback only. */
const { chromium, webkit } = require('playwright');
const assert = require('node:assert/strict');
const base = process.env.F244_BASE_URL || 'http://127.0.0.1:56645';
assert.equal(new URL(base).hostname, '127.0.0.1');
let checks = 0;
function check(value, message) { checks++; assert.ok(value, message); }
const frame = page => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
async function focusGeometry(page, label) {
  await frame(page);
  const r = await page.evaluate(() => {
    const dialog = document.querySelector('[data-manual-upload-dialog]');
    const active = document.activeElement;
    let visible = active;
    if (active.matches('[data-manual-upload-file]')) visible = dialog.querySelector('[data-manual-upload-dropzone]');
    if (active.matches('input[type="checkbox"]')) visible = active.closest('label');
    const d = dialog.getBoundingClientRect(), t = visible.getBoundingClientRect();
    return {inside:dialog.contains(active), tag:active.outerHTML.slice(0,160),top:t.top,bottom:t.bottom,left:t.left,right:t.right,
      dt:d.top+dialog.clientTop,db:d.top+dialog.clientTop+dialog.clientHeight,dl:d.left,dr:d.right,scroll:dialog.scrollTop};
  });
  check(r.inside && r.top >= r.dt && r.bottom <= r.db && r.left >= r.dl && r.right <= r.dr, `${label}: focus ${JSON.stringify(r)}`);
}
async function run(browser, engine) {
  const initialChecks = checks;
  const page = await browser.newPage();
  page.setDefaultTimeout(5000);
  const errors=[]; page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/v1/cabinet/media-uploads', () => {throw new Error('test must not upload');});
  for (const embedded of [false,true]) for (const theme of ['light','dark']) for (const [width,height] of [[390,320],[640,400]]) {
    for (const state of ['empty','valid','invalid','unavailable']) {
      const label = `${engine}/${embedded}/${theme}/${width}/${state}`;
      await page.setViewportSize({width,height});
      const path = state === 'unavailable' ? `/f244-unavailable?embedded=${embedded}&theme=${theme}` : `${embedded?'/desktop':''}/meetings?theme=${theme}`;
      await page.goto(base+path);
      const trigger = page.locator('[data-manual-upload-open]');
      await trigger.click();
      const dialog=page.getByRole('dialog',{name:'Загрузить файл',exact:true});
      check(await dialog.count() === 1,label+' accessible name');
      check(await dialog.locator('#manual-upload-heading').count() === 1,label+' one visible heading');
      if (state === 'valid' || state === 'invalid') {
        const data=Buffer.alloc(state==='valid' ? 16044 : 3);
        if (state==='valid') {
          data.write('RIFF');data.writeUInt32LE(data.length-8,4);data.write('WAVEfmt ',8);data.writeUInt32LE(16,16);
          data.writeUInt16LE(1,20);data.writeUInt16LE(1,22);data.writeUInt32LE(8000,24);data.writeUInt32LE(16000,28);
          data.writeUInt16LE(2,32);data.writeUInt16LE(16,34);data.write('data',36);data.writeUInt32LE(16000,40);
        }
        await page.locator('[data-manual-upload-file]').setInputFiles({name:'synthetic-long-name-'.repeat(8)+'.wav',mimeType:'audio/wav',buffer:data});
        await page.waitForFunction(expected => expected ? !document.querySelector('[data-manual-upload-submit]').disabled : !document.querySelector('[data-manual-upload-validation]').hidden,state==='valid');
      }
      await focusGeometry(page,label+'/initial');
      const count=await dialog.locator('a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),[tabindex="0"]').count();
      for (const key of ['Tab','Shift+Tab']) for(let i=0;i<count+1;i++) {
        await page.keyboard.press(key); await focusGeometry(page,label+'/'+key+'/'+i);
      }
      const bounds=await dialog.boundingBox();check(bounds.y>=0 && bounds.y+bounds.height<=height,label+' bounds');
      await dialog.hover();await page.mouse.wheel(0,900);await frame(page);
      check(await dialog.evaluate(d=>d.scrollHeight<=d.clientHeight || d.scrollTop>0),label+' wheel');
      await page.keyboard.press('Escape');check(await trigger.evaluate(t=>document.activeElement===t),label+' Escape restore');
      await trigger.click();await focusGeometry(page,label+'/reopen');
      await page.locator('[data-manual-upload-close]').click();check(await trigger.evaluate(t=>document.activeElement===t),label+' close restore');
    }
  }
  for (const embedded of [false,true]) {
    const label=`${engine}/rail/${embedded}`;
    await page.setViewportSize({width:1440,height:400});
    await page.goto(base+`${embedded?'/desktop':''}/meetings?theme=light`);
    await page.evaluate(()=>sessionStorage.removeItem('graf-cabinet-rail'));await page.reload();
    const toggle=page.locator('[data-cabinet-rail-toggle]'), search=page.locator('input[type="search"]').first();
    await toggle.click();await toggle.click();
    check(await page.evaluate(()=>sessionStorage.getItem('graf-cabinet-rail'))==='expanded',label+' explicit expanded');
    await search.focus();
    for (const width of [640,320,641,980,981,1120,1121,1440]) {
      await page.setViewportSize({width,height:400});await frame(page);
      check(await page.evaluate(()=>sessionStorage.getItem('graf-cabinet-rail'))==='expanded',label+' resize preference '+width);
      if(width<=640) {
        const r=await search.evaluate(t=>{const b=t.getBoundingClientRect(),main=t.closest('main').getBoundingClientRect();return {main:main.width,hit:document.elementFromPoint((b.left+b.right)/2,(b.top+b.bottom)/2)===t};});
        check(r.main>=width-64 && r.hit,label+' focus visible '+JSON.stringify(r));
      }
    }
    check(await toggle.getAttribute('aria-expanded')==='true',label+' wide restored');
    await page.setViewportSize({width:320,height:400});await page.reload();
    if (embedded) {
      if(await toggle.getAttribute('aria-expanded')!=='true')await toggle.click();
      await search.focus();await frame(page);check(await toggle.getAttribute('aria-expanded')==='false',label+' main focus collapses');
      await toggle.click();check(await toggle.getAttribute('aria-expanded')==='true',label+' toggle opens');
      await page.locator('[data-manual-upload-open]').focus();
      await page.locator('[data-manual-upload-open]').click();
      check(await page.locator('[data-manual-upload-dialog]').evaluate(d=>d.open),label+' modal open');
      await page.keyboard.press('Escape');
      // Modal focus enters main, so the rail may already be temporarily hidden; preference is untouched.
      check(await page.evaluate(()=>sessionStorage.getItem('graf-cabinet-rail'))==='expanded',label+' dialog Escape preserves preference');
      await toggle.click();await page.keyboard.press('Escape');
      check(await page.evaluate(()=>sessionStorage.getItem('graf-cabinet-rail'))==='collapsed',label+' explicit Escape');
      const profile=page.locator('[data-profile-menu-trigger]');await profile.focus();
      const r=await profile.boundingBox();check(r.y>=0 && r.y+r.height<=400,label+' lower controls reachable');
    }
  }
  check(errors.length===0,`${engine} page errors: ${errors.join(';')}`);
  console.log(JSON.stringify({engine,checks:checks-initialChecks,totalChecks:checks,result:'PASS'}));
  await page.close();
}
(async()=>{
  if(process.env.F244_ENGINE !== 'webkit') {
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try {await run(browser,'Chrome');} finally {await browser.close();}
  }
  const wk=await webkit.launch({executablePath:process.env.F244_WEBKIT_EXECUTABLE,headless:true});
  try {await run(wk,'WebKit');} finally {await wk.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
