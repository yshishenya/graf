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
   await page.getByRole('link',{name:'Расшифровка',exact:true}).click();
   const search=page.getByRole('searchbox');await search.fill('неттакогослова');
   assert.equal(await page.locator('[data-public-turn]:visible').count(),0);
   await search.fill('Проверка');assert.equal(await page.locator('[data-public-turn]:visible').count(),1);
   await search.fill('');await page.locator('[data-public-seek]').first().click();
   assert.equal(new URL(page.url()).hash,'#recording?position_ms=14000');
   const audio=page.locator('[data-playback-player]');
   await page.waitForFunction(()=>document.querySelector('audio').readyState>=1);
   assert.equal(await page.locator('[data-speaker-lane]').count(),2);
   assert.deepEqual(await page.locator('[data-speaker-lane]').evaluateAll(rows=>rows.map(row=>row.dataset.speakerKey)),['speaker-1','speaker-2']);
   await page.locator('[data-lane-segment]').last().click();
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
   assert.deepEqual(privateRequests,[]);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
   assert.equal(overflow,false,`overflow ${width}/${colorScheme}`);
   await page.getByRole('link',{name:'Войти',exact:true}).click({noWaitAfter:true});
   assert.deepEqual(errors,[]);
   await context.close();
  }
  const context=await browser.newContext({javaScriptEnabled:false});const page=await context.newPage();
  await page.route('**/*',r=>r.fulfill({contentType:'text/html',body:fs.readFileSync(process.argv[2],'utf8')}));await page.goto('https://graf.test/reader');
  assert.equal(await page.locator('#outcomes').isVisible(),true);assert.equal(await page.locator('#recording').isVisible(),true);
  await context.close();
  console.log('public reader: fragments, tabs, welcome, search, timestamp, 320/390/1440 light/dark, no-JS PASS');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
