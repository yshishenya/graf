/** Production renderer/assets and native document script, synthetic calendars only. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const serverRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const html=execFileSync(process.env.SERVER_PYTHON || 'python',['-c',`
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from tests.fixtures.calendar_settings import calendar_settings_source, calendar_settings_calendar, calendar_settings_snapshot
from tests.fixtures.calendar_visual_ui_harness import _meeting_response
from twobrain_rec_server.cabinet.view_models import calendar_settings_surface, upcoming_preview_item
from twobrain_rec_server.cabinet.rendering import render_meeting_list_page
source=calendar_settings_source(selected_calendar_count=1,last_successful_sync_at=datetime.now(UTC))
calendar=calendar_settings_calendar(source,selected=True)
event=calendar_settings_snapshot(source,calendar,title='Планирование команды',starts_at=datetime.now(UTC)+timedelta(hours=1),open_meeting_available=True)
surface=calendar_settings_surface(provider_payloads=[],sources=[source],calendars_by_source={source.id:[calendar]},preview_events=[event])
surface=replace(surface,overview_loaded=True,overview=(replace(upcoming_preview_item(event),series_key='v2-'+('a'*64)),))
print(render_meeting_list_page(_meeting_response(),calendar_surface=surface,embedded=True,csrf_token='synthetic'))
`],{cwd:serverRoot,env:{...process.env,PYTHONPATH:path.join(serverRoot,'src')},encoding:'utf8'});
const bridge=readFileSync(path.join(serverRoot,'../macos/RecApp/Sources/Cabinet/EmbeddedCabinetCalendarJoinBridge.swift'),'utf8').split('static let documentScript = #"""')[1].split('"""#')[0];
let failure=false;
let revised=false;
let invalidCursor=false;
let holdNext=false;
let delayedResponse;
const selectedID=html.match(/data-calendar-join="([0-9a-f-]+)"/)[1];
let requests=0;
const server=createServer((req,res)=>{
  if(req.url.startsWith('/static/cabinet/')) {
    try {const name=path.basename(req.url.split('?')[0]);res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'application/octet-stream');res.end(readFileSync(path.join(serverRoot,'src/twobrain_rec_server/cabinet/static/cabinet',name)));}catch{res.writeHead(404);res.end();}return;
  }
  if(req.url.startsWith('/api/v1/calendar/series/')) {
    requests++;res.setHeader('Content-Type','application/json');
    if(holdNext) {holdNext=false;delayedResponse=res;return;}
    if(failure) {res.writeHead(503);res.end('{}');return;}
    const second=req.url.includes('cursor=second');
    if(second&&invalidCursor){invalidCursor=false;res.writeHead(422);res.end('{}');return;}
    const offset=second?5:0;
    res.end(JSON.stringify({occurrences:Array.from({length:second?7:5},(_,n)=>({event_id:offset+n===0?selectedID:`00000000-0000-0000-0000-${String(offset+n+1).padStart(12,'0')}`,title:'Планирование команды',starts_at:new Date(Date.UTC(2026,9,1+offset+n,10)).toISOString(),all_day:false,cancelled:revised&&n===0,open_meeting_available:!(revised&&n===0),recordings:(!revised&&n===0)?[{meeting_id:'00000000-0000-0000-0000-000000000099'}]:[]})),next_cursor:second?null:'second',coverage_range:{from:'2026-04-01T00:00:00Z',to:'2026-11-01T00:00:00Z'},coverage_note:'Показаны сохранённые доступные даты.'}));return;
  }
  res.setHeader('Content-Type','text/html; charset=utf-8');res.end(html);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});
try {
 const page=await browser.newPage({viewport:{width:1100,height:850}});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.addInitScript(()=>{window.joinMessages=[];window.webkit={messageHandlers:{grafCalendarJoin:{postMessage:p=>window.joinMessages.push(p)}}};});
 await page.goto(`http://127.0.0.1:${server.address().port}/desktop/meetings`);
 await page.evaluate(bridge);
 const button=page.locator('[data-calendar-join]').first();
 await button.click();await button.click({force:true});
 assert.equal(await page.evaluate(()=>window.joinMessages.length),1);
 assert.equal(await button.getAttribute('aria-disabled'),'true');
 await page.evaluate(()=>window.GRAFCalendarJoin.reply(window.joinMessages[0].requestId,'failed'));
 assert.match(await page.locator('[data-calendar-join-status]').first().textContent(),/Не удалось/);
 await button.click();assert.equal(await page.evaluate(()=>window.joinMessages.length),2);
 await page.evaluate(()=>window.GRAFCalendarJoin.reply(window.joinMessages[1].requestId,'handed_off'));
 assert.match(page.url(),/desktop\/meetings$/);
 const summary=page.locator('.calendar-series summary');await summary.focus();await page.keyboard.press('Space');
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);
 await page.locator('[data-calendar-series-more]').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===12);
 assert.equal(requests,2);
 assert.equal(await page.locator('.calendar-series__occurrence a[href$="/00000000-0000-0000-0000-000000000099"]').count(),2);
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
 await page.screenshot({path:'/tmp/f279-calendar-series.png',fullPage:true});
 assert.deepEqual(errors,[]);
 // Failure remains local and can be retried.
 failure=true;await page.reload();await page.locator('.calendar-series summary').click();
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
 await page.locator('.calendar-series summary').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===0);
 holdNext=true;
 await page.locator('.calendar-series summary').click();
 await page.waitForFunction(()=>document.querySelector('[data-calendar-series-more]').disabled);
 assert.ok(delayedResponse);
 await page.locator('.calendar-series summary').click();
 await page.waitForFunction(()=>!document.querySelector('[data-calendar-series-more]').disabled);
 await page.locator('.calendar-series summary').click();
 await page.waitForFunction(()=>document.querySelectorAll('.calendar-series__occurrence').length===5);
 const oldResponse=page.waitForResponse(response=>response.url().includes('/occurrences')&&response.status()===422);
 delayedResponse.writeHead(422);delayedResponse.end('{}');
 await oldResponse;
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 assert.equal(await page.locator('.calendar-series__occurrence').count(),5);
 assert.match(await page.locator('[data-calendar-series-status]').textContent(),/Показаны сохранённые/);
 console.log('PASS: production series UI, keyboard, pagination 12 dates, inline retry, real calendar refresh focus, stale failure isolation, narrow viewport, exact native script double-click/retry/no-navigation');
} finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
