const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const script = path.join(__dirname,'../../src/twobrain_rec_server/cabinet/static/cabinet/public-sharing.js');
const {parseFragment} = require(script);
assert.deepEqual(parseFragment('#recording?position_ms=14000'),{tab:'recording',position:14000});
for(const hash of ['#recording?position_ms=-1','#recording?position_ms=86400001','#outcomes?position_ms=1','#recording?position_ms=1&x=1','#evil']) assert.deepEqual(parseFragment(hash),{tab:'outcomes',position:null});
const assets = path.dirname(script);
const wav = Buffer.alloc(44 + 240000, 128);
wav.write('RIFF',0);wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);
wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);
wav.writeUInt32LE(8000,24);wav.writeUInt32LE(8000,28);wav.writeUInt16LE(1,32);wav.writeUInt16LE(8,34);
wav.write('data',36);wav.writeUInt32LE(240000,40);
const {chromium,webkit} = require(require.resolve('playwright',{paths:[process.env.GRAF_NODE_MODULES || process.cwd()]}));
async function checkContext(page, tab, position) {
 for (const selector of ['[data-public-auth]', '[data-public-native]']) {
  const link=page.locator(selector).first();
  // Inspect the real click handler's URI without leaving the page or launching an app.
  await link.evaluate(el=>el.addEventListener('click',event=>event.preventDefault(),{once:true}));
  await link.dispatchEvent('click');
  const url=new URL(await link.getAttribute('href'),'https://graf.test');
  assert.equal(url.searchParams.get('tab'),tab);
  assert.equal(url.searchParams.get('position_ms'),position);
  assert.equal(url.searchParams.get('media_version'),'a'.repeat(24));
  assert.equal(url.protocol,selector==='[data-public-native]'?'grafrec-dev:':'https:');
 }
}
async function target24(locator) {
 await locator.scrollIntoViewIfNeeded();
 const hit = await locator.evaluate(el => {
  const {x,y,width,height}=el.getBoundingClientRect();
  const hits=[x+width/2-11,x+width/2+11].flatMap(px=>[y+height/2-11,y+height/2+11].map(py=>document.elementFromPoint(px,py)));
  return [width,height,hits.every(node=>el.contains(node)),hits.map(node=>node?.className)];
 });
 assert(hit[0]>=24&&hit[1]>=24&&hit[2], `unreachable target: ${locator} ${hit}`);
}
(async()=>{
 const browser=await (process.env.GRAF_BROWSER==='webkit'?webkit:chromium).launch({headless:true});
 try {
  for(const width of [320,390,1440]) for(const colorScheme of ['light','dark']){
   const context=await browser.newContext({viewport:{width,height:900},colorScheme});
   const page=await context.newPage(),errors=[],privateRequests=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',route=>{const url=new URL(route.request().url());if(url.pathname==='/reader')return route.fulfill({contentType:'text/html',body:fs.readFileSync(process.argv[2],'utf8')});if(url.pathname==='/audio') {
     const range = /^bytes=(\d+)-(\d*)$/.exec(route.request().headers().range || '');
     const start = range ? Number(range[1]) : 0, end = range && range[2] ? Math.min(Number(range[2]), wav.length-1) : wav.length-1;
     return route.fulfill({status:range?206:200,contentType:'audio/wav',headers:{'Accept-Ranges':'bytes','Content-Length':String(end-start+1),...(range?{'Content-Range':`bytes ${start}-${end}/${wav.length}`}:{})},body:wav.subarray(start,end+1)});
    }
    const name=path.basename(url.pathname);
    if(/\.(js|css)$/.test(name)&&fs.existsSync(path.join(assets,name)))return route.fulfill({contentType:name.endsWith('.js')?'text/javascript':'text/css',body:fs.readFileSync(path.join(assets,name),'utf8')});
    if(/\/(comments|contacts|shares|recipients)(?:\?|$)/.test(url.pathname))privateRequests.push(url.pathname);
    return route.fulfill({status:204});});
   await page.goto('https://graf.test/reader');
   await page.getByRole('button',{name:'Посмотреть встречу',exact:true}).click();
   await target24(page.getByRole('link',{name:'Войти',exact:true}));
   await target24(page.getByRole('link',{name:'Итоги',exact:true}));
   await target24(page.getByRole('link',{name:'Расшифровка',exact:true}));
   await page.getByRole('link',{name:'Расшифровка',exact:true}).click();
   await target24(page.locator('[data-public-seek]').first());
   const search=page.getByRole('searchbox');await search.fill('неттакогослова');
   assert.equal(await page.locator('[data-public-turn]:visible').count(),0);
   await search.fill('Проверка');assert.equal(await page.locator('[data-public-turn]:visible').count(),1);
   await search.fill('');await page.locator('[data-public-seek]').first().click();
   assert.equal(new URL(page.url()).hash,'#recording?position_ms=14000');
   const audio=page.locator('[data-playback-player]');
   await page.waitForFunction(()=>document.querySelector('audio').readyState>=1);
   assert.equal(await page.locator('[data-speaker-lane]').count(),2);
   assert.deepEqual(await page.locator('[data-speaker-lane]').evaluateAll(rows=>rows.map(row=>row.dataset.speakerKey)),['speaker-1','speaker-2']);
   const lane = page.locator('[data-speaker-lane="speaker-1"]');
   const track = lane.locator('[data-timeline-track]');
   const intervals = lane.locator('[data-timeline-intervals]');
   await target24(track);
   await target24(intervals);
   const choose = page.locator('[data-timeline-interval-dialog]');
   await intervals.press('Enter');
   assert.equal(await choose.isVisible(),true);
   await target24(choose.locator('[data-timeline-interval-choice]').nth(1));
   await page.keyboard.press('Escape');
   await choose.waitFor({state:'hidden'});
   assert.equal(await intervals.evaluate(el=>el===document.activeElement),true);
   assert.equal(await audio.evaluate(a=>a.currentTime),14);
   await intervals.click();
   await choose.locator('[data-timeline-interval-choice]').nth(1).press('Enter');
   await choose.waitFor({state:'hidden'});
   assert.equal(await audio.evaluate(a=>a.currentTime),14.25);
   assert.equal(await intervals.evaluate(el=>el===document.activeElement),true);
   await intervals.click();
   const firstChoice = choose.locator('[data-timeline-interval-choice]').first();
   assert.notEqual(await firstChoice.textContent(),await choose.locator('[data-timeline-interval-choice]').nth(1).textContent());
   await firstChoice.click();
   assert.equal(await audio.evaluate(a=>a.currentTime),14);
   await page.waitForFunction(()=>document.querySelector('[data-public-turn].is-source-highlight')?.textContent.includes('Проверка'));
   const trackBox=await track.boundingBox();
   const [first, second]=await lane.locator('[data-lane-segment]').evaluateAll(nodes=>nodes.map(el=>{
    const {left,right}=el.getBoundingClientRect();return {left,right};
   }));
   assert(first.right>second.left);
   await page.mouse.click((first.right+second.left)/2,trackBox.y+trackBox.height/2);
   assert.equal(await audio.evaluate(a=>a.currentTime),14.25,'overlap chooses the upper interval');
   await page.mouse.click(trackBox.x+trackBox.width*0.25,trackBox.y+trackBox.height/2);
   assert(Math.abs(await audio.evaluate(a=>a.currentTime)-7.5)<0.25,'empty track seeks proportionally');
   await track.press('ArrowRight');
   assert(Math.abs(await audio.evaluate(a=>a.currentTime)-22.5)<0.25);
   await track.press('ArrowLeft');
   assert(Math.abs(await audio.evaluate(a=>a.currentTime)-7.5)<0.25);
   await page.locator('[data-public-sharing]').evaluate(el=>el.addEventListener('graf:public-recording',event=>{
    window.requestedEnd=event.detail.seconds;
   },{once:true}));
   await track.press('End');
   assert.equal(await page.evaluate(()=>window.requestedEnd),30);
   const last=page.locator('[data-lane-segment]').last();
   await last.scrollIntoViewIfNeeded();
   const box=await last.boundingBox();
   await page.mouse.click(box.x+box.width/2,box.y+box.height/2);
   await page.waitForFunction(()=>Math.abs(document.querySelector('audio').currentTime-18)<0.5,{},{timeout:3000});
   assert(Math.abs(await audio.evaluate(a=>a.currentTime)-18)<0.5, JSON.stringify({errors,ready:await page.locator('[data-playback-shell]').getAttribute('data-playback-ready'),time:await audio.evaluate(a=>a.currentTime)}));
   assert.equal(new URL(page.url()).hash,'#recording?position_ms=18000');
   await page.getByRole('button',{name:'Скорость воспроизведения',exact:true}).click();
   await page.locator('[data-playback-speed-option="1.5"]').click();
   assert.equal(await audio.evaluate(a=>a.playbackRate),1.5);
   await page.getByRole('button',{name:'Скрыть дорожки',exact:true}).click();
   assert.equal(await page.locator('[data-speaker-timeline-shell]').evaluate(el=>el.classList.contains('is-collapsed')),true);
   await page.getByRole('button',{name:'Показать дорожки',exact:true}).click();
   await page.locator('[data-timeline-track]').first().press('Home');
   assert.equal(await audio.evaluate(a=>a.currentTime),0);
   await page.getByRole('button',{name:'Следующая реплика',exact:true}).click();
   assert(Math.abs(await audio.evaluate(a=>a.currentTime)-14)<0.5);
   await page.getByRole('button',{name:'Слушать спикеров',exact:true}).click();
   await page.locator('[data-listen-speaker="speaker-2"]').check();
   await page.waitForFunction(()=>document.querySelector('audio').currentTime>=18&&!document.querySelector('audio').paused);
   await page.getByRole('button',{name:'Приостановить',exact:true}).click();
   await checkContext(page,'recording',String(await audio.evaluate(a=>Math.round(a.currentTime*1000))));
   assert.deepEqual(privateRequests,[]);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
   assert.equal(overflow,false,`overflow ${width}/${colorScheme}`);
   await page.getByRole('link',{name:'Войти',exact:true}).click({noWaitAfter:true});
   assert.deepEqual(errors,[]);
   await context.close();
  }
  for(const [position,changed] of [[15000,false],[0,false],[15000,true]]) {
   const context=await browser.newContext();const page=await context.newPage();
   await page.route('**/*',route=>{
    const url=new URL(route.request().url()),name=path.basename(url.pathname);
    if(url.pathname==='/reader')return route.fulfill({contentType:'text/html',body:fs.readFileSync(process.argv[2],'utf8').replace('data-source-changed="false"',`data-source-changed="${changed}"`)});
    if(/\.(js|css)$/.test(name)&&fs.existsSync(path.join(assets,name)))return route.fulfill({contentType:name.endsWith('.js')?'text/javascript':'text/css',body:fs.readFileSync(path.join(assets,name),'utf8')});
    return route.fulfill({status:204});
   });
   await page.goto(`https://graf.test/reader#recording?position_ms=${position}`);
   await page.getByRole('button',{name:'Посмотреть встречу',exact:true}).click();
   assert.equal(await page.locator('audio').evaluate(a=>a.readyState),0);
   await checkContext(page,'recording',changed?null:String(position));
   await page.getByRole('link',{name:'Итоги',exact:true}).click();
   await page.locator('#outcomes').waitFor({state:'visible'});
   await checkContext(page,'outcomes',null);
   await context.close();
  }
  const context=await browser.newContext({javaScriptEnabled:false});const page=await context.newPage();
  await page.route('**/*',r=>{
   const name=path.basename(new URL(r.request().url()).pathname);
   if(name==='reader')return r.fulfill({contentType:'text/html',body:fs.readFileSync(process.argv[2],'utf8')});
   if(name.endsWith('.css')&&fs.existsSync(path.join(assets,name)))return r.fulfill({contentType:'text/css',path:path.join(assets,name)});
   return r.fulfill({status:204});
  });
  await page.goto('https://graf.test/reader');
  assert.equal(await page.locator('#outcomes').isVisible(),true);assert.equal(await page.locator('#recording').isVisible(),true);
  assert.equal(await page.locator('[data-timeline-intervals]').first().isVisible(),false);
  assert.equal(await page.locator('audio[controls]').isVisible(),true);
  await context.close();
  console.log('public reader: fragments, tabs, welcome, search, timestamp, pending/loaded/changed continuation, 320/390/1440 light/dark, no-JS PASS');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
