/** Functional regression with production templates/assets and synthetic calendars.
 * Run with SERVER_PYTHON=<server venv python> PLAYWRIGHT_MODULE=<playwright module>
 * CHROMIUM_EXECUTABLE=<chromium executable> node tests/browser/calendar_refresh.mjs.
 * No real account, provider, database, or network data is used.
 */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const serverRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const html = JSON.parse(execFileSync(process.env.SERVER_PYTHON || 'python', ['-c', `
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID
from tests.fixtures.calendar_settings import calendar_settings_source, calendar_settings_calendar, calendar_settings_snapshot
from tests.fixtures.calendar_visual_ui_harness import _meeting_response
from twobrain_rec_server.cabinet.rendering import render_meeting_list_page, render_calendar_settings_page
from twobrain_rec_server.cabinet.view_models import calendar_settings_surface
from twobrain_rec_server.calendar.capabilities import provider_preset_payloads
now=datetime.now(UTC)
source=calendar_settings_source(provider_family="google_calendar", sync_state="syncing", last_successful_sync_at=now)
source.id=UUID(int=251)
calendar=calendar_settings_calendar(source, selected=True)
calendar.id=UUID(int=252)
second=calendar_settings_calendar(source, provider_calendar_id="second", display_label="Второй", selected=False)
event=calendar_settings_snapshot(source, calendar, title="Новая встреча alice@example.test <script>bad()</script>", starts_at=now+timedelta(minutes=10), safe_to_show=False, open_meeting_available=True)
def surface(events=()):
 return calendar_settings_surface(provider_payloads=provider_preset_payloads(google_available=True), sources=[source], calendars_by_source={source.id:[calendar,second]}, preview_events=events, now=now)
empty=surface()
source.sync_state="synced"
ready=surface([event])
failed=calendar_settings_source(sync_state="credential_failed", last_successful_sync_at=now)
failed.id=UUID(int=253)
mixed=calendar_settings_surface(provider_payloads=[], sources=[source,failed], calendars_by_source={source.id:[calendar,second]}, preview_events=[event], now=now)
catalog_pending=calendar_settings_surface(provider_payloads=provider_preset_payloads(google_available=True), sources=[source], calendars_by_source={}, now=now)
disconnected=calendar_settings_surface(provider_payloads=provider_preset_payloads(google_available=True), sources=[], now=now)
result={}
for embedded in [False,True]:
 prefix="desktop" if embedded else "web"
 for name,value in [("empty",empty),("ready",ready),("mixed",mixed)]:
  result[prefix+"-home-"+name]=render_meeting_list_page(_meeting_response(),calendar_surface=value,embedded=embedded,csrf_token="synthetic")
 for name,value in [("syncing",empty),("ready",ready),("disconnected",disconnected),("catalog-pending",catalog_pending)]:
  result[prefix+"-settings-"+name]=render_calendar_settings_page(value,embedded=embedded,csrf_token="synthetic")
print(json.dumps(result))
`], { cwd: serverRoot, env: { ...process.env, PYTHONPATH: path.join(serverRoot, 'src') }, encoding: 'utf8' }));
let current = 'web-home-empty';
let fetches = 0;
let fail = false;
const server = createServer((req, res) => {
  if (req.url.startsWith('/static/cabinet/')) {
    const filename = path.basename(req.url.split('?')[0]);
    try {
      const data = readFileSync(path.join(serverRoot, 'src/twobrain_rec_server/cabinet/static/cabinet', filename));
      res.setHeader('Content-Type', filename.endsWith('.js') ? 'text/javascript' : filename.endsWith('.css') ? 'text/css' : 'application/octet-stream');
      res.end(data);
    } catch { res.writeHead(404); res.end(); }
    return;
  }
  if (req.url.includes('favicon')) { res.writeHead(204); res.end(); return; }
  if (req.method === "POST" && req.url.endsWith("/sync")) current = current.replace("-ready", "-syncing");
  if (req.method === "POST" && (req.url.endsWith("/disconnect") || req.url.endsWith("/connect"))) {
    current = current.split('-settings-')[0] + (req.url.endsWith('/disconnect') ? '-settings-disconnected' : '-settings-ready');
    res.writeHead(303, {Location: req.url.startsWith('/desktop/') ? '/desktop/settings/integrations/calendar' : '/settings/integrations/calendar'}); res.end(); return;
  }
  fetches++;
  res.writeHead(fail ? 503 : 200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(html[current]);
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {}) });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on('pageerror', error => errors.push(String(error)));
await page.clock.install();
async function tick() {
  const before = fetches;
  await page.clock.runFor(30001);
  await assertEventually(async () => assert.ok(fetches > before));
  await page.waitForTimeout(20);
}
async function assertEventually(check) {
  for (let i=0; i<100; i++) {
    try { await check(); return; } catch (error) { if(i===99) throw error; }
    await new Promise(resolve=>setTimeout(resolve,20));
  }
}
try {
  for (const prefix of ['web','desktop']) {
    const route = prefix === 'desktop' ? '/desktop' : '';
    current = `${prefix}-home-empty`;
    await page.goto(base + route + '/meetings');
    assert.match(await page.title(), /Мои встречи/);
    assert.equal(await page.locator('[data-calendar-live="upcoming"]').count(),1);
    assert.match(await page.locator('[data-calendar-live="upcoming"]').innerText(), /Ближайших встреч нет/);
    await page.evaluate(()=>{ window.__retained = 'alive'; });
    current = `${prefix}-home-ready`;
    await tick();
    await assertEventually(async()=>assert.match(await page.locator('[data-calendar-live="upcoming"]').innerText(), /Новая встреча alice@example.test <script>/));
    assert.equal(await page.evaluate(()=>window.__retained),'alive');
    assert.equal(await page.locator('[data-calendar-live="upcoming"] script').count(),0);
    assert.equal(await page.locator('[data-calendar-live="upcoming"] a:has-text("Подключиться")').count(),1);
    await page.screenshot({path:`/tmp/graf-251-calendar-${prefix}-home.png`});
    current = `${prefix}-home-mixed`;
    await tick();
    assert.match(await page.locator('[data-calendar-live="upcoming"]').innerText(), /Новая встреча/);
    assert.match(await page.locator('[data-calendar-live="upcoming"]').innerText(), /переподключить/);
    current = `${prefix}-home-empty`;
    await page.evaluate(()=>window.dispatchEvent(new Event('online')));
    await assertEventually(async()=>assert.match(await page.locator('[data-calendar-live="upcoming"]').innerText(), /Ближайших встреч нет/));
    current = `${prefix}-settings-catalog-pending`;
    await page.goto(base + route + '/settings/integrations/calendar');
    assert.equal(await page.locator('.calendar-selection-form').count(),0);
    current = `${prefix}-settings-ready`;
    await tick();
    await assertEventually(async()=>assert.equal(await page.locator('.calendar-selection-form').count(),1));
    current = `${prefix}-settings-syncing`;
    await page.goto(base + route + '/settings/integrations/calendar');
    await page.locator('.calendar-source-details--picker').evaluate(el=>el.open=true);
    const dirty = page.locator('.calendar-selection-form input[value="second"]');
    await dirty.check();
    await page.locator('[data-calendar-provider-open="calendar-provider-dialog-caldav_yandex"]').click();
    const dialog = page.locator('#calendar-provider-dialog-caldav_yandex');
    const field = dialog.locator('input:not([type="hidden"])').first();
    await field.fill('synthetic-owner');
    const beforeInvalid = fetches;
    await dialog.locator('button[type="submit"]').click();
    assert.equal(await dialog.locator('input[name="credential_input"]').evaluate(el=>el.validity.valueMissing),true);
    assert.equal(fetches,beforeInvalid);
    await field.focus();
    await page.evaluate(()=>{ window.__retained = 'alive'; });
    for(let i=0;i<6;i++) await tick();
    assert.equal(await page.evaluate(()=>window.__retained),'alive');
    assert.equal(await dirty.isChecked(),true);
    assert.equal(await field.inputValue(),'synthetic-owner');
    assert.equal(await field.evaluate(el=>el===document.activeElement),true);
    assert.equal(await dialog.evaluate(el=>el.open),true);
    await page.screenshot({path:`/tmp/graf-251-calendar-${prefix}-dialog.png`});
    current = `${prefix}-settings-ready`;
    await tick();
    await assertEventually(async()=>assert.match(await page.locator('[data-calendar-live^="states-"]').innerText(), /синхронизация актуальна/));
    assert.equal(await dirty.isChecked(),true);
    assert.equal(await field.inputValue(),'synthetic-owner');
    assert.equal(await field.evaluate(el=>el===document.activeElement),true);
    await page.keyboard.press('Escape');
    assert.equal(await dialog.evaluate(el=>el.open),false);
    assert.equal(await page.locator('[data-calendar-mutation="sync"] button').isDisabled(),false);
    await page.locator('[data-calendar-mutation="sync"] button').click();
    await assertEventually(async()=>assert.equal(await page.locator('[data-calendar-mutation="sync"]').getAttribute("data-sync-pending"),"true"));
    await assertEventually(async()=>assert.equal(await page.locator('[data-calendar-mutation="sync"] button').isDisabled(),true));
    assert.equal(await dirty.isChecked(),true);
    assert.equal(await page.evaluate(()=>window.__retained),'alive');
    current = `${prefix}-settings-ready`;
    await tick();
    await assertEventually(async()=>assert.match(await page.locator('[data-calendar-mutation="sync"] [role="status"]').innerText(), /Календарь обновлён/));
    fail=true;
    await tick();
    assert.equal(await dirty.isChecked(),true);
    await assertEventually(async()=>assert.equal(await page.locator("[data-calendar-refresh-status]").isVisible(),true));
    fail=false;
    await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
    await assertEventually(async()=>assert.equal(await page.locator("[data-calendar-refresh-status]").isVisible(),false));
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth + 1));
    await page.screenshot({path:`/tmp/graf-251-calendar-${prefix}-mobile.png`});
    await page.setViewportSize({width:1280,height:900});
    await page.screenshot({path:`/tmp/graf-251-calendar-${prefix}-desktop.png`});
    await page.locator('[data-calendar-provider-open="calendar-provider-dialog-google_calendar"]').click();
    const google = page.locator('#calendar-provider-dialog-google_calendar');
    assert.match(await google.innerText(), /только на чтение/);
    await google.getByRole('button',{name:'Отмена',exact:true}).click();
    const disconnectButton = page.locator('[data-calendar-provider-open^="calendar-disconnect-dialog-"]');
    await disconnectButton.click();
    const disconnect = page.locator('dialog.calendar-disconnect-dialog');
    await disconnect.getByRole('button',{name:'Отмена',exact:true}).click();
    assert.equal(await page.locator('[data-calendar-source]').count(),1);
    await disconnectButton.click();
    await disconnect.locator('button[type="submit"]').click();
    await assertEventually(async()=>assert.equal(await page.locator('[data-calendar-source]').count(),0));
    await page.locator('[data-calendar-provider-open="calendar-provider-dialog-caldav_yandex"]').click();
    const reconnect = page.locator('#calendar-provider-dialog-caldav_yandex');
    await reconnect.locator('input[name="username"]').fill('synthetic-owner');
    await reconnect.locator('input[name="credential_input"]').fill('synthetic-password');
    await reconnect.locator('button[type="submit"]').click();
    await assertEventually(async()=>assert.equal(await page.locator('[data-calendar-source]').count(),1));
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: web/embedded empty→new→mixed-error→deleted; 6+ polls; dirty selection/dialog/focus; recovery; manual ack; catalog appearance; invalid/cancel/disconnect/reconnect controls; links/escaping; narrow layout; no runtime errors');
} finally { await browser.close(); server.closeAllConnections(); await new Promise(resolve=>server.close(resolve)); }
