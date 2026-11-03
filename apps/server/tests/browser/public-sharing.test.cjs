const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const script = path.join(__dirname,'../../src/twobrain_rec_server/cabinet/static/cabinet/public-sharing.js');
const {parseFragment} = require(script);
assert.deepEqual(parseFragment('#recording?position_ms=14000'),{tab:'recording',position:14000});
for(const hash of ['#recording?position_ms=-1','#recording?position_ms=86400001','#outcomes?position_ms=1','#recording?position_ms=1&x=1','#evil']) assert.deepEqual(parseFragment(hash),{tab:'outcomes',position:null});
const {chromium,webkit} = require(require.resolve('playwright',{paths:[process.env.GRAF_NODE_MODULES || process.cwd()]}));
(async()=>{
 const browser=await (process.env.GRAF_BROWSER==='webkit'?webkit:chromium).launch({headless:true});
 try {
  for(const width of [320,390,1440]) for(const colorScheme of ['light','dark']){
   const context=await browser.newContext({viewport:{width,height:900},colorScheme});
   const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',route=>{const url=new URL(route.request().url());if(url.pathname==='/reader')return route.fulfill({contentType:'text/html',body:fs.readFileSync(process.argv[2],'utf8')});if(url.pathname.endsWith('cabinet.css'))return route.fulfill({contentType:'text/css',body:fs.readFileSync(path.join(path.dirname(script),'cabinet.css'),'utf8')});if(url.pathname.endsWith('public-sharing.js'))return route.fulfill({contentType:'text/javascript',body:fs.readFileSync(script,'utf8')});return route.fulfill({status:204});});
   await page.goto('https://graf.test/reader');
   await page.getByRole('button',{name:'Посмотреть встречу',exact:true}).click();
   await page.getByRole('link',{name:'Расшифровка',exact:true}).click();
   const search=page.getByRole('searchbox');await search.fill('неттакогослова');
   assert.equal(await page.locator('[data-public-turn]:visible').count(),0);
   await search.fill('Проверка');assert.equal(await page.locator('[data-public-turn]:visible').count(),1);
   await search.fill('');await page.locator('[data-public-seek]').first().click();
   assert.equal(new URL(page.url()).hash,'#recording?position_ms=14000');
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
