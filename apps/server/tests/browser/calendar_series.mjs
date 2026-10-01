/** Production renderer/assets and native document script, synthetic calendars only. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { readFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { release as osRelease } from 'node:os';
const serverRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const {chromium,webkit}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const rendered=JSON.parse(execFileSync(process.env.SERVER_PYTHON || 'python',['-c',`
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from tests.fixtures.calendar_settings import calendar_settings_source, calendar_settings_calendar, calendar_settings_snapshot
from tests.fixtures.calendar_visual_ui_harness import _meeting_response
from twobrain_rec_server.cabinet.view_models import calendar_settings_surface, upcoming_preview_item
from twobrain_rec_server.cabinet.rendering import render_meeting_list_page
from twobrain_rec_server.cabinet.user_time import apply_user_time_preference
apply_user_time_preference(user_id="synthetic",session_id="synthetic",timezone="Europe/Istanbul")
source=calendar_settings_source(selected_calendar_count=1,last_successful_sync_at=datetime.now(UTC))
calendar=calendar_settings_calendar(source,selected=True)
event=calendar_settings_snapshot(source,calendar,title='Планирование команды',starts_at=datetime(2026,10,5,12,tzinfo=UTC),open_meeting_available=True)
surface=calendar_settings_surface(provider_payloads=[],sources=[source],calendars_by_source={source.id:[calendar]},preview_events=[event])
surface=replace(surface,overview_loaded=True,overview=(replace(upcoming_preview_item(event),series_key='v2-'+('a'*64)),))
def render(value):
    return render_meeting_list_page(_meeting_response(),calendar_surface=value,embedded=True,display_timezone='Europe/Istanbul',csrf_token='synthetic')
masked=replace(surface,preferences=replace(surface.preferences,show_upcoming_title=False,show_upcoming_time=False))
print(json.dumps({'normal':render(surface),'masked':render(masked)}))
`],{cwd:serverRoot,env:{...process.env,PYTHONPATH:path.join(serverRoot,'src')},encoding:'utf8'}));
const html=rendered.normal;
const bridge=readFileSync(path.join(serverRoot,'../macos/RecApp/Sources/Cabinet/EmbeddedCabinetCalendarJoinBridge.swift'),'utf8').split('static let documentScript = #"""')[1].split('"""#')[0];
async function assertContrast(page) {
  const ratios=await page.locator('.calendar-series').evaluate(panel=>{
    const light=color=>{
      const channels=color.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
      return channels[0]*.2126+channels[1]*.7152+channels[2]*.0722;
    };
    const contrast=(a,b)=>{const x=light(a),y=light(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
    return [...panel.querySelectorAll('.calendar-series__views button,.calendar-series__scope,.calendar-series__date time,.calendar-series__date > span,.calendar-series__actions > span,.calendar-series__recording,.calendar-series__help > summary')]
      .filter(node=>node.textContent.trim() && node.getClientRects().length)
      .map(node=>{
        let parent=node,bg;
        do {bg=getComputedStyle(parent).backgroundColor;parent=parent.parentElement;} while(parent && (bg==='rgba(0, 0, 0, 0)' || bg==='transparent'));
        return {text:node.textContent.trim().slice(0,32),ratio:contrast(getComputedStyle(node).color,bg)};
      });
  });
  assert.ok(ratios.every(item=>item.ratio>=4.5),JSON.stringify(ratios));
}
let failure=false;
let scenario="normal";
const screenshotDir=process.env.CALENDAR_SCREENSHOTS || "/tmp/f283-calendar-ux";mkdirSync(screenshotDir,{recursive:true});
let revised=false;
let invalidCursor=false;
let holdNext=false;
let delayedResponse;
const selectedID=html.match(/data-calendar-join="([0-9a-f-]+)"/)[1];
let requests=0;
let joinRequests=0,joinConfirmations=0,joinResponse,holdConfirmation=false,confirmationResponse;
const server=createServer((req,res)=>{
  if(req.url.startsWith('/static/cabinet/')) {
    try {const name=path.basename(req.url.split('?')[0]);res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'application/octet-stream');res.end(readFileSync(path.join(serverRoot,'src/twobrain_rec_server/cabinet/static/cabinet',name)));}catch{res.writeHead(404);res.end();}return;
  }
  if(req.url.endsWith('/join-target')) {
    if(req.method==='POST') {
      joinConfirmations++;assert.equal(req.headers['x-csrf-token'],'synthetic');
      if(holdConfirmation) {holdConfirmation=false;confirmationResponse=res;return;}
      const changed=req.headers.cookie?.includes('f279-session=changed');
      res.writeHead(changed?403:200,{'Content-Type':'application/json'});
      res.end(JSON.stringify(changed?{}:{event_id:selectedID,https_url:'https://meet.example.test/join?pwd=synthetic#context'}));
    } else {joinRequests++;joinResponse=res;}return;
  }
  if(req.url.startsWith('/api/v1/calendar/series/')) {
    requests++;res.setHeader('Content-Type','application/json');
    if(holdNext) {holdNext=false;delayedResponse=res;return;}
    if(failure) {res.writeHead(503);res.end('{}');return;}
    const query=new URL(req.url,'http://localhost').searchParams;
    const history=query.get('view')==='history';
    const second=query.get('cursor')==='second';
    if(second&&invalidCursor){invalidCursor=false;res.writeHead(422);res.end('{}');return;}
    const offset=second?5:0;
    const occurrences=scenario==='empty'?[]:Array.from({length:second?7:5},(_,n)=>({
      event_id:offset+n===0?selectedID:`00000000-0000-0000-0000-${String(offset+n+1).padStart(12,'0')}`,
      title:scenario==='masked'?'Название скрыто настройкой':n===1?'Планирование команды: отдельная повестка '+(scenario==='long'?'очень длинное название '.repeat(14):''):'Планирование команды',
      starts_at:scenario==='masked'?null:scenario==='dst'?new Date(Date.UTC(2026,2,29,n%2,30)).toISOString():new Date(Date.UTC(2026,9,history?-offset-n:5+offset+n,12)).toISOString(),
      all_day:scenario==='all-day',cancelled:(revised&&n===0)||n===2,
      open_meeting_available:!(revised&&n===0)&&n!==1&&n!==2,
      temporal_state:history?'history':['ongoing','masked'].includes(scenario)&&n===0?'ongoing':'upcoming',
      recordings_partial:true,
      recordings:(!revised&&n===0)?[{meeting_id:'00000000-0000-0000-0000-000000000099'},{meeting_id:'00000000-0000-0000-0000-000000000098'}]:[]
    }));
    res.end(JSON.stringify({occurrences,next_cursor:second||!occurrences.length?null:'second',coverage_range:{from:'2026-04-01T00:00:00Z',to:'2026-11-01T00:00:00Z'},coverage_note:'Показаны сохранённые доступные даты.'}));return;
  }
  res.setHeader('Content-Type','text/html; charset=utf-8');res.end(scenario==='masked'?rendered.masked:html);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const browser=await (process.env.CALENDAR_ENGINE==='webkit'?webkit:chromium).launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});
try {
 const page=await browser.newPage({viewport:{width:1100,height:850},colorScheme:"dark"});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.addInitScript(()=>{window.joinMessages=[];window.webkit={messageHandlers:{grafCalendarJoin:{postMessage:p=>window.joinMessages.push(p)}}};});
 await page.goto(`http://127.0.0.1:${server.address().port}/desktop/meetings`);
 await page.evaluate(bridge);
 const button=page.locator('[data-calendar-join]').first();
 await button.click();await button.click({force:true});
 assert.equal(await page.evaluate(()=>window.joinMessages.length),1);
 assert.equal(await button.getAttribute('aria-disabled'),'true');
 await page.evaluate(()=>window.GRAFCalendarJoin.reply(window.joinMessages[0].requestId,'cancelled'));
 assert.match(await page.locator('[data-calendar-join-status]').first().textContent(),/Действие отменено/);
 await button.click();assert.equal(await page.evaluate(()=>window.joinMessages.length),2);
 await page.evaluate(()=>window.GRAFCalendarJoin.reply(window.joinMessages[1].requestId,'handed_off'));
 assert.match(page.url(),/desktop\/meetings$/);
 const summary=page.locator('.calendar-series > summary');await summary.focus();await page.keyboard.press('Space');
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);
 await page.locator('[data-calendar-series-more]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===12);
 assert.equal(requests,2);
 assert.equal(await page.locator('.calendar-series__occurrence a[href="/desktop/meetings"]').count(),0);
 assert.equal(await page.getByText('Здесь показана ограниченная выборка записей.',{exact:true}).count(),0);
 assert.equal(await page.locator('.calendar-series__recording').count(),0);
 assert.equal(await page.locator('.calendar-series__exception').count(),2);
 assert.equal(await page.getByText('Идёт сейчас',{exact:true}).count(),0);
 assert.ok(await page.getByText('Без ссылки',{exact:true}).count()>0);
 const historyButton=page.locator('[data-calendar-series-view="history"]');
 await historyButton.click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);
 assert.equal(await historyButton.getAttribute('aria-pressed'),'true');
 assert.equal(await page.locator('.calendar-series__occurrence [data-calendar-join]').count(),0);
 assert.equal(await page.locator('.calendar-series__recording').count(),2);
 assert.equal(await page.getByRole('link',{name:/Открыть запись 1 ·/}).count(),1);
 assert.equal(await page.getByRole('link',{name:/Открыть запись 2 ·/}).count(),1);
 assert.ok(await page.getByLabel('В выборке нет связанной записи',{exact:true}).count()>0);
 assert.equal(await page.locator('.calendar-series__help').count(),1);
 assert.equal(await page.locator('.calendar-series__help a').getAttribute('href'),'/desktop/meetings');
 await page.evaluate(()=>document.documentElement.dataset.theme='dark');
 await page.locator('.calendar-home-upcoming').screenshot({path:path.join(screenshotDir,'history-dark.png')});
 await page.locator('[data-calendar-series-more]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===12);
 assert.equal(await page.locator('[data-calendar-series-view="history"]').getAttribute('aria-pressed'),'true');
 await page.locator('[data-calendar-series-view="upcoming"]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);
 await page.locator('[data-calendar-series-more]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===12);
 const rowJoin=page.locator('.calendar-series__occurrence [data-calendar-join]').first();
 await rowJoin.click();
 assert.equal(await rowJoin.getAttribute('aria-disabled'),'true');
 assert.match(await page.locator('.calendar-series__occurrence [data-calendar-join-status]').first().textContent(),/Открываем/);
 await page.evaluate(()=>window.GRAFCalendarJoin.reply(window.joinMessages.at(-1).requestId,'failed'));
 assert.match(await page.locator('.calendar-series__occurrence [data-calendar-join-status]').first().textContent(),/Не удалось/);
 revised=true;
 const retainedFocus=page.locator('.calendar-series__occurrence [data-calendar-join]').nth(1);
 const focusedHref=await retainedFocus.getAttribute('href');
 await retainedFocus.focus();
 const beforeRefresh=requests;
 await page.evaluate(()=>window.dispatchEvent(new Event('online')));
 await page.waitForFunction(()=>document.querySelector('.calendar-series__occurrence').textContent.includes('Отменена') && !document.querySelector('[data-calendar-series-rows]').inert);
 assert.equal(requests,beforeRefresh+2);
 assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('href')),focusedHref);
 assert.equal(await page.locator('.calendar-series__occurrence a[href$="/00000000-0000-0000-0000-000000000099"]').count(),0);
 assert.match(await page.locator('.calendar-series__occurrence').first().textContent(),/Отменена/);
 assert.equal(await page.locator('[data-calendar-series]').getAttribute('open'),'');

 assert.equal(await page.locator('[data-calendar-series-more]').isVisible(),false);
 await page.setViewportSize({width:480,height:850});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
 await page.locator('.calendar-home-upcoming').screenshot({path:path.join(screenshotDir,'upcoming-narrow.png')});
 assert.deepEqual(errors,[]);
 assert.equal(joinRequests,0);assert.equal(page.context().pages().length,1);
 // Failure remains local and can be retried.
 failure=true;await page.reload();await page.locator('.calendar-series > summary').click();
 await page.waitForFunction(()=>document.querySelector('[data-calendar-series-status]').textContent.includes('Не удалось'));
 failure=false;await page.locator('[data-calendar-series-more]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);
 invalidCursor=true;
 await page.locator('[data-calendar-series-more]').click();
 await page.waitForFunction(()=>document.querySelector('[data-calendar-series-status]').textContent.includes('устарел'));
 assert.equal(await page.locator('.calendar-series__occurrence').count(),0);
 await page.locator('[data-calendar-series-more]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);
 // A late failure from a closed panel must not erase a newer successful load.
 await page.locator('.calendar-series > summary').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===0);
 holdNext=true;
 await page.locator('.calendar-series > summary').click();
 await page.waitForFunction(()=>document.querySelector('[data-calendar-series-more]').disabled);
 assert.ok(delayedResponse);
 await page.locator('.calendar-series > summary').click();
 await page.waitForFunction(()=>!document.querySelector('[data-calendar-series-more]').disabled);
 await page.locator('.calendar-series > summary').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);

 delayedResponse.writeHead(422);delayedResponse.end('{}');

 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 assert.equal(await page.locator('.calendar-series__occurrence').count(),5);
 assert.equal(await page.locator('[data-calendar-series-status]').textContent(),'');

 // F283 production UI scenarios. No data from another view survives a late response.
 await page.setViewportSize({width:1280,height:850});
 revised=false;await page.reload();await page.locator('.calendar-series > summary').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);
 await page.evaluate(()=>document.documentElement.dataset.theme='dark');
 await assertContrast(page);
 await page.locator('.calendar-home-upcoming').screenshot({path:path.join(screenshotDir,'upcoming-dark.png')});
 await page.evaluate(()=>document.documentElement.dataset.theme='light');
 await page.locator('.calendar-home-upcoming').screenshot({path:path.join(screenshotDir,'upcoming-light.png')});
 for(const width of [641,700,760]) {
   await page.setViewportSize({width,height:850});
   assert.equal(await page.locator('.calendar-series').evaluate(panel=>{
     const parent=panel.parentElement,style=getComputedStyle(parent),bounds=panel.getBoundingClientRect(),row=parent.getBoundingClientRect();
     return Math.abs(bounds.left-row.left-parseFloat(style.paddingLeft))<=1
       && Math.abs(bounds.right-row.right+parseFloat(style.paddingRight))<=1
       && parent.scrollWidth<=parent.clientWidth+1;
   }),true,`series fills the collapsed parent grid at ${width}px`);
 }
 await page.locator('.calendar-home-upcoming').screenshot({path:path.join(screenshotDir,'upcoming-medium.png')});
 await page.setViewportSize({width:1100,height:850});
 await page.locator('[data-calendar-series-view="history"]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__recording').length===2);
 await assertContrast(page);
 await page.locator('.calendar-home-upcoming').screenshot({path:path.join(screenshotDir,'history-light.png')});
 await page.locator('[data-calendar-series-view="upcoming"]').focus();await page.keyboard.press('Enter');
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__recording').length===0 && document.querySelectorAll('.calendar-series__occurrence').length===5);
 assert.equal(await page.evaluate(()=>document.activeElement.dataset.calendarSeriesView),'upcoming');
 holdNext=true;await page.locator('[data-calendar-series-view="history"]').click();
 await page.waitForFunction(()=>document.querySelector('[data-calendar-series-more]').disabled);
 const switchedResponse=delayedResponse;
 await page.locator('[data-calendar-series-view="upcoming"]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);
 switchedResponse.end(JSON.stringify({occurrences:[],next_cursor:null,coverage_range:{from:'2026-04-01T00:00:00Z',to:'2026-11-01T00:00:00Z'}}));
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 assert.equal(await page.locator('[data-calendar-series-view="upcoming"]').getAttribute('aria-pressed'),'true');
 assert.equal(await page.locator('.calendar-series__occurrence').count(),5);
 for(const kind of ['empty','all-day','masked','long','ongoing','dst']) {
   scenario=kind;await page.reload();
   if(kind==='dst') await page.evaluate(()=>window.GRAFTime.setTimezone('Europe/Berlin'));
   await page.locator('.calendar-series > summary').click();
   await page.waitForFunction(()=>!document.querySelector('[data-calendar-series-more]').disabled);
   if(kind==='empty') {
     assert.match(await page.locator('[data-calendar-series-status]').textContent(),/ближайшие 30/);
     await page.locator('[data-calendar-series-view="history"]').click();
     await page.waitForFunction(()=>document.querySelector('[data-calendar-series-status]').textContent.includes('180'));
   } else if(kind==='all-day') assert.equal(await page.getByText('Весь день',{exact:true}).count(),5);
   else if(kind==='dst') {
     assert.match(await page.locator('.calendar-series__date').nth(0).textContent(),/01:30/);
     assert.match(await page.locator('.calendar-series__date').nth(1).textContent(),/03:30/);
   }
   else if(kind==='ongoing') assert.equal(await page.getByText('Идёт сейчас',{exact:true}).count(),1);
   else if(kind==='masked') {
     assert.equal(await page.getByText('Идёт сейчас',{exact:true}).count(),0);
     assert.equal(await page.locator('.calendar-series__date time').count(),0);
     assert.equal(await page.locator('.calendar-series__date').getByText('Время скрыто настройкой',{exact:true}).count(),5);
     assert.equal(await page.locator('.calendar-home-upcoming [datetime]').count(),0);
     assert.equal(await page.locator('.calendar-home-upcoming').getByText(/Планирование команды/).count(),0);
   }
   await page.setViewportSize({width:320,height:850});
   assert.equal(await page.locator('.calendar-home-upcoming').evaluate(node=>node.scrollWidth<=node.clientWidth+1),true);
   await page.locator('.calendar-home-upcoming').screenshot({path:path.join(screenshotDir,kind+'-narrow.png')});
   await page.setViewportSize({width:640,height:850});await page.evaluate(()=>document.documentElement.style.zoom='2');
   assert.equal(await page.locator('.calendar-home-upcoming').evaluate(node=>node.scrollWidth<=node.clientWidth+1),true);
   await page.evaluate(()=>document.documentElement.style.zoom='');
 }
 scenario='normal';await page.reload();
 await page.locator('.calendar-series > summary').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);
 // A failed rights refresh removes visible recording actions and retains the selected view.
 await page.locator('[data-calendar-series-view="history"]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__recording').length===2);
 failure=true;await page.evaluate(()=>window.dispatchEvent(new Event('online')));
 await page.waitForFunction(()=>document.querySelector('[data-calendar-series-status]').textContent.includes('Не удалось'));
 assert.equal(await page.locator('.calendar-series__occurrence').count(),0);
 assert.equal(await page.locator('[data-calendar-series-view="history"]').getAttribute('aria-pressed'),'true');
 failure=false;await page.locator('[data-calendar-series-more]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__recording').length===2);
 await page.locator('.calendar-series > summary').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===0);
 // SC-007: production assets, trusted input, local synthetic API; no native app launch.
 await page.setViewportSize({width:1100,height:850});
 await page.evaluate(bridge);
 await page.evaluate(()=>{
   window.calendarTiming={join:[],series:[]};
   window.addEventListener('click',event=>{
     if(!event.isTrusted) return;
     const started=performance.now();
     const button=event.target.closest('[data-calendar-join]');
     if(button) {
       requestAnimationFrame(()=>requestAnimationFrame(()=>{
         const status=button.parentElement.querySelector('[data-calendar-join-status]');
         if(button.getAttribute('aria-disabled')==='true' && status?.textContent==='Открываем…' && status.getClientRects().length)
           window.calendarTiming.join.push(performance.now()-started);
       }));
     }
     const summary=event.target.closest('.calendar-series > summary');
     if(summary && !summary.parentElement.open) {
       const ready=()=>{
         const rows=summary.parentElement.querySelectorAll('.calendar-series__occurrence');
         if(rows.length===5 && rows[0].getClientRects().length)
           requestAnimationFrame(()=>requestAnimationFrame(()=>window.calendarTiming.series.push(performance.now()-started)));
         else if(performance.now()-started<5000) requestAnimationFrame(ready);
       };requestAnimationFrame(ready);
     }
   },true);
 });
 const warmup=3,samples=30;
 for(let n=0;n<warmup+samples;n++) {
   await page.locator('[data-calendar-join]').first().click();
   await page.waitForFunction(n=>window.calendarTiming.join.length>n,n,{timeout:5000});
   await page.evaluate(()=>window.GRAFCalendarJoin.reply(window.joinMessages.at(-1).requestId,'handed_off'));
   if(await page.locator('.calendar-series').getAttribute('open')!==null) {
     await page.locator('.calendar-series > summary').click();
     await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===0);
   }
   await page.locator('.calendar-series > summary').click();
   await page.waitForFunction(n=>window.calendarTiming.series.length>n,n,{timeout:5000});
 }
 const timing=await page.evaluate(warmup=>Object.fromEntries(Object.entries(window.calendarTiming).map(([key,all])=>{
   const values=all.slice(warmup).sort((a,b)=>a-b);
   return [key,{samples:values.length,p95_ms:values[Math.ceil(values.length*0.95)-1],max_ms:values.at(-1)}];
 })),warmup);
 console.log('SC-007 '+JSON.stringify({sha:execFileSync('git',['rev-parse','HEAD'],{cwd:serverRoot,encoding:'utf8'}).trim(),os:process.platform,os_release:osRelease(),arch:process.arch,engine:process.env.CALENDAR_ENGINE || "chromium",browser:browser.version(),viewport:page.viewportSize(),warmup,p95_rule:'nearest rank ceil(n*0.95)',timing}));
 assert.equal(timing.join.samples,samples);
 assert.equal(timing.series.samples,samples);
 assert.ok(timing.join.max_ms<=200,`Join feedback maximum ${timing.join.max_ms}ms exceeds 200ms`);
 assert.ok(timing.series.p95_ms<=500,`Series p95 ${timing.series.p95_ms}ms exceeds 500ms`);
 // Standalone browser uses the same production asset with fresh JSON resolution.
 const webContext=await browser.newContext();
 const web=await webContext.newPage();
 const original=`http://127.0.0.1:${server.address().port}/meetings`;
 await webContext.addCookies([{name:'f279-session',value:'original',url:original}]);
 await web.goto(original);
 let popups=0;web.on('popup',()=>popups++);
 const webJoin=web.locator('[data-calendar-join]').first();
 const firstPopup=web.waitForEvent('popup');await webJoin.click();const failedTab=await firstPopup;
 await web.waitForFunction(()=>document.querySelector('[data-calendar-join]').getAttribute('aria-disabled')==='true');
 await webJoin.click({force:true});assert.equal(joinRequests,1);assert.equal(popups,1);
 const closed=failedTab.waitForEvent('close');joinResponse.writeHead(404,{'Content-Type':'application/json'});joinResponse.end('{}');await closed;
 await web.waitForFunction(()=>document.querySelector('[data-calendar-join-status]').textContent.includes('Не удалось открыть'));
 assert.equal(web.url(),original);assert.equal(await webJoin.getAttribute('aria-disabled'),null);
 let externalHeaders;
 await webContext.route('https://meet.example.test/**',async route=>{externalHeaders=route.request().headers();await route.fulfill({contentType:'text/html',body:'<p>Synthetic conference</p>'});});
 const nextPopup=web.waitForEvent('popup');await webJoin.click();const joinedTab=await nextPopup;
 while(joinRequests<2) await new Promise(resolve=>setTimeout(resolve,5));
 // Production calendar refresh replaces the original action while resolution waits.
 await web.evaluate(()=>{window.oldJoin=document.querySelector('[data-calendar-join]');window.dispatchEvent(new Event('online'));});
 await web.waitForFunction(()=>!window.oldJoin.isConnected && document.querySelector('[data-calendar-join]').getAttribute('aria-disabled')==='true');
 joinResponse.writeHead(200,{'Content-Type':'application/json'});joinResponse.end(JSON.stringify({event_id:selectedID,https_url:'https://stale.example.test/old'}));
 await joinedTab.waitForURL('https://meet.example.test/join?pwd=synthetic#context');
 assert.equal(await joinedTab.evaluate(()=>window.opener),null);
 assert.equal(externalHeaders.referer,undefined);assert.equal(externalHeaders['x-auth-session'],undefined);assert.equal(externalHeaders.cookie,undefined);
 assert.equal(web.url(),original);assert.equal(popups,2);assert.equal(joinConfirmations,1);
 // A cookie changed by another tab invalidates the original page's confirmation.
 const stalePopup=web.waitForEvent('popup');await webJoin.click();const staleTab=await stalePopup;
 while(joinRequests<3) await new Promise(resolve=>setTimeout(resolve,5));
 await webContext.addCookies([{name:'f279-session',value:'changed',url:original}]);
 const staleClosed=staleTab.waitForEvent('close');
 joinResponse.writeHead(200,{'Content-Type':'application/json'});joinResponse.end(JSON.stringify({event_id:selectedID,https_url:'https://stale.example.test/old'}));
 await staleClosed;assert.equal(joinConfirmations,2);
 await web.waitForFunction(()=>document.querySelector('[data-calendar-join-status]').textContent.includes('Не удалось открыть'));
 assert.equal(web.url(),original);

 // Even an already-authorized POST response cannot outlive a cookie generation change.
 await webContext.addCookies([{name:'f279-session',value:'original',url:original},{name:'graf_dev_session_epoch',value:'before',url:original}]);
 holdConfirmation=true;
 const latePopup=web.waitForEvent('popup');await webJoin.click();const lateTab=await latePopup;
 while(joinRequests<4) await new Promise(resolve=>setTimeout(resolve,5));
 joinResponse.writeHead(200,{'Content-Type':'application/json'});joinResponse.end(JSON.stringify({event_id:selectedID,https_url:'https://stale.example.test/old'}));
 while(!confirmationResponse) await new Promise(resolve=>setTimeout(resolve,5));
 await webContext.addCookies([{name:'graf_dev_session_epoch',value:'after',url:original}]);
 const lateClosed=lateTab.waitForEvent('close');
 confirmationResponse.writeHead(200,{'Content-Type':'application/json'});confirmationResponse.end(JSON.stringify({event_id:selectedID,https_url:'https://stale.example.test/late'}));
 await lateClosed;assert.equal(joinConfirmations,3);
 await web.waitForFunction(()=>document.querySelector('[data-calendar-join-status]').textContent.includes('Не удалось открыть'));
 // Closing the cabinet cancels only the reserved tab and cannot open a late result.
 const cancelledPopup=web.waitForEvent('popup');await webJoin.click();const cancelledTab=await cancelledPopup;
 while(joinRequests<5) await new Promise(resolve=>setTimeout(resolve,5));
 const abandonedResponse=joinResponse;
 const cancelledClose=cancelledTab.waitForEvent('close');await web.goto(original+'?new-document');await cancelledClose;
 abandonedResponse.end('{}');
 await webContext.close();
 // Before isolated-world injection a desktop click cannot leak into browser routing.
 const desktopContext=await browser.newContext({userAgent:'Synthetic GRAFDesktop/1.0'});
 const earlyDesktop=await desktopContext.newPage();await earlyDesktop.goto(original);
 await earlyDesktop.locator('[data-calendar-join]').first().click();
 assert.match(await earlyDesktop.locator('[data-calendar-join-status]').first().textContent(),/Календарь загружается/);
 assert.equal(joinRequests,5);assert.equal(desktopContext.pages().length,1);
 await desktopContext.close();
 console.log('PASS: standalone stale 404 stays local, explicit retry, duplicate suppression, single HTTPS popup without opener/referrer/auth, pagehide cancellation, desktop pre-injection guard, production DOM refresh during join, changed-session confirmation and late authorized POST cancellation');
 console.log('PASS: production series UI, keyboard, pagination 12 dates, inline retry, real calendar refresh focus, stale failure isolation, narrow viewport, exact native script double-click/retry/no-navigation');
} finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
