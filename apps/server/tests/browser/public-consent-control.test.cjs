/* Real vendored CookieConsent + loopback control API. No external delivery. */
const assert = require('node:assert/strict');
const http = require('node:http');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const { chromium } = require(require.resolve('playwright', {
  paths: [process.env.GRAF_NODE_MODULES || __dirname + '/node_modules'],
}));
const { readConfig, loadController } = require('./public-analytics-consent-modal.test.cjs');
const KEY = 'graf_public_cookie_consent';
const CONTROL = '/analytics/public-consent';

async function main() {
  const config = readConfig('/download');
  assert.equal(config.consent_control_endpoint, CONTROL);
  assert.equal(config.external_counter_allowed, false);
  assert.equal(config.replay_allowed, false);
  const authHtml = execFileSync(path.resolve(__dirname, '../../.venv/bin/python'), ['-c', `
import json, sys
from twobrain_rec_server.cabinet.templates import render_template
print(render_template('cabinet/auth/analytics.html', public_analytics=json.loads(sys.argv[1])))
`, JSON.stringify(config)], { cwd: path.resolve(__dirname, '../..'), encoding: 'utf8' });
  const requests = [], events = [], rows = new Map();
  let intercept = null;
  const server = http.createServer(async (req, res) => {
    if (req.method !== 'POST') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      if (['/login', '/sign-up'].includes(req.url)) {
        res.end('<!doctype html><html lang="ru"><body>' + authHtml.replace(/<script\b[^>]*>[\s\S]*?<\/script>/g, '') + '</body></html>');
        return;
      }
      res.end('<!doctype html><html lang="ru"><body>' +
        '<button type="button" data-cc="show-preferencesModal">Настройки cookies</button>' +
        '<div id="graf-public-consent-status" role="status" aria-live="polite" hidden>' +
        '<span data-consent-message></span> <button type="button" data-consent-retry hidden></button></div>' +
        '</body></html>');
      return;
    }
    let text = ''; for await (const chunk of req) text += chunk;
    const body = JSON.parse(text);
    res.setHeader('Content-Type', 'application/json');
    if (req.url !== CONTROL) { events.push(body); res.end('{}'); return; }
    requests.push(body);
    const reply = (status, value) => { res.statusCode = status; res.end(JSON.stringify(value)); };
    if (intercept && await intercept(body, reply)) return;
    if (body.action === 'read') {
      reply(200, rows.has(body.consent_id) ? { state: 'known', ...rows.get(body.consent_id) } : { state: 'unknown' });
      return;
    }
    if (body.action === 'grant' && rows.get(body.consent_id)?.epoch !== body.expected_epoch) {
      reply(409, { accepted: false, reason: 'choice_stale' }); return;
    }
    const row = { epoch: randomUUID(), categories: body.action === 'grant' ? body.categories : ['necessary'],
      copy_version: body.action === 'grant' ? body.copy_version : null };
    rows.set(body.consent_id, row);
    reply(200, { accepted: true, state: body.action === 'grant' ? 'granted' : 'revoked', ...row });
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  context.setDefaultTimeout(5000);
  await context.route('**/*', route => route.request().url().startsWith(origin + '/')
    ? route.continue() : route.abort());
  const cookie = page => page.evaluate(key => JSON.parse(localStorage.getItem(key)), KEY);
  const pending = page => page.waitForFunction(() =>
    document.querySelector('[data-consent-retry]')?.hidden === false);
  const ready = page => page.waitForFunction(() =>
    window.GRAFPublicAnalytics.currentConsentState !== 'unknown' &&
    window.GRAFPublicAnalytics.consentPending === false);
  const hold = action => {
    let entered, release;
    const arrived = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('control request not reached: ' + action)), 8000);
      entered = () => { clearTimeout(timer); resolve(); };
    });
    const gate = new Promise(resolve => { release = resolve; });
    intercept = async body => {
      if (body.action !== action) return false;
      entered(); await gate; return false;
    };
    return { arrived, release };
  };
  const resume = (page, type) => page.evaluate(type =>
    (type === 'visibilitychange' ? document : window).dispatchEvent(new Event(type)), type);
  const noTraffic = async page => {
    assert.equal(await page.evaluate(() => window.GRAFPublicAnalytics.sentEvents.length), 0);
    assert.equal(await page.evaluate(() =>
      window.GRAFPublicAnalytics.dispatchEvent('public_download_viewed', {})), false);
  };
  const open = async (cfg = config, seed) => {
    const page = await context.newPage(); await page.goto(origin);
    await page.evaluate(({ key, seed }) => seed
      ? localStorage.setItem(key, JSON.stringify(seed)) : localStorage.removeItem(key), { key: KEY, seed });
    await loadController(page, cfg); return page;
  };
  try {
    for (const authPath of ['/login', '/sign-up']) for (const event of ['focus', 'visibilitychange']) {
      const auth = await context.newPage(); await auth.goto(origin + authPath);
      await auth.evaluate(key => localStorage.removeItem(key), KEY);
      await loadController(auth, readConfig(authPath));
      // Wait for the real modal's delayed initial focus before the keyboard retry.
      await auth.waitForFunction(() => document.querySelector('.cm').contains(document.activeElement));
      intercept = async (body, reply) => {
        if (body.action !== 'revoke') return false;
        reply(503, { accepted: false, reason: 'choice_unavailable' }); return true;
      };
      await auth.locator('.cm__btns [data-role="necessary"]').click();
      await pending(auth);
      assert.match(await auth.locator('#graf-public-consent-status').innerText(), /Серверное сохранение отказа пока не подтверждено/);
      assert.equal(await auth.evaluate(() => window.GRAFPublicAnalytics.sentEvents.length), 0);
      const held = hold('revoke');
      const retryStart = requests.length;
      await auth.locator('[data-consent-retry]').focus(); await auth.keyboard.press('Enter');
      await held.arrived;
      await resume(auth, event);
      await noTraffic(auth);
      assert.equal(await auth.evaluate(() => window.GRAFPublicAnalytics.consentPending), true);
      held.release(); intercept = null;
      await ready(auth);
      assert.deepEqual(requests.slice(retryStart).map(r => r.action), ['revoke']);
      assert.deepEqual(rows.get((await cookie(auth)).consentId).categories, ['necessary']);
      await auth.close();
      console.log('ok_actual_auth_template_refusal_retry ' + authPath + ' ' + event);
    }
    requests.length = 0; events.length = 0;
    const page = await open();
    await page.locator('.cm__btns [data-role="all"]').click();
    await ready(page);
    const accepted = await cookie(page);
    assert.equal(accepted.data.graf_public_consent_epoch, rows.get(accepted.consentId).epoch);
    // A queued focus/read from a closing auth page may arrive after reset.
    // Every mutation must still belong to this explicit choice, in order.
    const writes = requests.filter(r => r.action !== 'read');
    assert.deepEqual(writes.map(r => [r.action, r.consent_id]),
      [['revoke', accepted.consentId], ['grant', accepted.consentId]]);
    assert.equal(writes[1].expected_epoch !== accepted.data.graf_public_consent_epoch, true);
    await page.waitForFunction(() => window.GRAFPublicAnalytics.sentEvents.length > 0);
    await new Promise(resolve => setImmediate(resolve));
    assert.ok(events.length > 0);
    assert.equal(events[0].consent_id, accepted.consentId);
    assert.equal(events[0].consent_epoch, accepted.data.graf_public_consent_epoch);
    assert.notEqual(events[0].view_id, accepted.consentId);
    assert.equal(await page.locator('script[data-graf-provider]').count(), 0);
    const start = requests.length;
    await page.reload(); await loadController(page, config); await ready(page);
    assert.ok(requests.length > start);
    assert.ok(requests.slice(start).every(r => r.action === 'read'));
    console.log('ok explicit_revoke_cas_grant_and_read_only_reload');

    // Missing server epoch never grants on load. The ordinary retry button is
    // required even when the library sees no category change.
    const noEpoch = structuredClone(accepted); delete noEpoch.data.graf_public_consent_epoch;
    await page.close();
    const missing = await open(config, noEpoch); await pending(missing);
    assert.equal(await missing.evaluate(() => window.GRAFPublicAnalytics.sentEvents.length), 0);
    const beforeRetry = requests.length;
    await missing.locator('[data-consent-retry]').click(); await ready(missing);
    assert.deepEqual(requests.slice(beforeRetry).map(r => r.action), ['revoke', 'grant']);
    console.log('ok_same_category_explicit_retry_only');

    // Failed revoke remains visible and optional traffic stops immediately.
    intercept = async (body, reply) => {
      if (body.action !== 'revoke') return false;
      reply(503, { accepted: false, reason: 'choice_unavailable' }); return true;
    };
    await missing.locator('[data-cc]').click();
    await missing.locator('.pm [data-role="necessary"]').click();
    await pending(missing);
    assert.match(await missing.locator('[role="status"]').innerText(), /Серверное сохранение отказа пока не подтверждено/);
    assert.equal(await missing.evaluate(() => window.GRAFPublicAnalytics.dispatchEvent('public_download_viewed', {})), false);
    intercept = null;
    await missing.locator('[data-consent-retry]').focus(); await missing.keyboard.press('Enter');
    await ready(missing);
    assert.deepEqual(rows.get((await cookie(missing)).consentId).categories, ['necessary']);
    console.log('ok_pending_revoke_is_accessible_and_retryable');
    await missing.close();

    // A refusal-labelled retry after a failed positive choice must never grant.
    intercept = async (body, reply) => {
      if (body.action !== 'revoke') return false;
      reply(503, { accepted: false, reason: 'choice_unavailable' }); return true;
    };
    const positiveFailure = await open();
    await positiveFailure.locator('.cm__btns [data-role="all"]').click();
    await pending(positiveFailure);
    assert.equal(await positiveFailure.locator('[data-consent-retry]').innerText(), 'Повторить сохранение отказа');
    intercept = null;
    const refusalRetryStart = requests.length;
    await positiveFailure.locator('[data-consent-retry]').click(); await ready(positiveFailure);
    assert.deepEqual(requests.slice(refusalRetryStart).map(r => r.action), ['revoke']);
    assert.equal(await positiveFailure.evaluate(() => window.GRAFPublicAnalytics.sentEvents.length), 0);
    assert.equal(await positiveFailure.locator('[data-consent-retry]').innerText(), 'Подтвердить выбранное разрешение');
    const explicitGrantStart = requests.length;
    await positiveFailure.locator('[data-consent-retry]').click(); await ready(positiveFailure);
    assert.deepEqual(requests.slice(explicitGrantStart).map(r => r.action), ['revoke', 'grant']);
    await positiveFailure.close();
    console.log('ok_refusal_retry_never_grants_a_previous_positive_choice');

    // Disabled measurement still offers refusal settings, with no automatic
    // banner, read-to-grant promotion or positive grant even after a click.
    const disabled = await open({ ...config, enabled: false }, accepted);
    await pending(disabled);
    assert.equal(await disabled.evaluate(() => document.documentElement.classList.contains('show--consent')), false);
    const disabledStart = requests.length;
    await disabled.locator('[data-consent-retry]').click(); await ready(disabled);
    assert.deepEqual(requests.slice(disabledStart).map(r => r.action), ['revoke']);
    assert.equal(await disabled.evaluate(() => window.GRAFPublicAnalytics.sentEvents.length), 0);
    await disabled.close();
    console.log('ok_disabled_measurement_keeps_refusal_without_grant');

    const other = await open();
    await other.locator('.cm__btns [data-role="all"]').click(); await ready(other);
    const refusingTab = await context.newPage(); await refusingTab.goto(origin);
    await loadController(refusingTab, config); await ready(refusingTab);
    await refusingTab.locator('[data-cc]').click();
    await refusingTab.locator('.pm [data-role="necessary"]').click(); await ready(refusingTab);
    await other.waitForFunction(() => window.GRAFPublicAnalytics.currentConsentState === 'revoked');
    assert.deepEqual((await cookie(other)).categories, ['necessary']);
    assert.equal((await cookie(other)).data.graf_public_consent_epoch,
      rows.get((await cookie(other)).consentId).epoch);
    await refusingTab.close();
    console.log('ok_cross_tab_read_preserves_the_real_library_refusal');
    const incomplete = { ...await cookie(other), data: {
      graf_public_consent_epoch: rows.get((await cookie(other)).consentId).epoch,
    } };
    const writer = await context.newPage(); await writer.goto(origin);
    await writer.evaluate(({ key, value }) => localStorage.setItem(key, JSON.stringify(value)),
      { key: KEY, value: incomplete });
    await pending(other);
    assert.deepEqual(await cookie(other), incomplete, 'a read cannot repair or overwrite a malformed decision');
    await other.locator('[data-consent-retry]').click(); await ready(other);
    assert.deepEqual((await cookie(other)).categories, ['necessary'], 'retry must refresh the cached library cookie');
    assert.deepEqual(rows.get((await cookie(other)).consentId).categories, ['necessary']);
    await writer.close(); await other.close();
    console.log('ok_read_is_nonmutating_and_retry_refreshes_library_cache');

    // A late grant callback cannot replace a newer local refusal. Cross-tab
    // changes invalidate both the active epoch and a pending choice.
    let release, entered;
    const gate = new Promise(resolve => { release = resolve; });
    const arrived = new Promise(resolve => { entered = resolve; });
    intercept = async body => { if (body.action !== 'grant') return false; entered(); await gate; return false; };
    const late = await open(); await late.locator('.cm__btns [data-role="all"]').click();
    await arrived;
    const old = await cookie(late);
    const tab = await context.newPage(); await tab.goto(origin);
    const refusal = { ...old, categories: ['necessary'], data: { ...old.data, graf_public_consent_epoch: null } };
    await tab.evaluate(({ key, refusal }) => localStorage.setItem(key, JSON.stringify(refusal)), { key: KEY, refusal });
    await pending(late); release(); intercept = null;
    await late.waitForFunction(() => window.GRAFPublicAnalytics.consentPending === false);
    assert.equal(await late.evaluate(() => window.GRAFPublicAnalytics.dispatchEvent('public_download_viewed', {})), false);
    assert.deepEqual((await cookie(late)).categories, ['necessary']);
    assert.equal((await cookie(late)).data.graf_public_consent_epoch, null);
    await late.evaluate(() => { dispatchEvent(new Event('pageshow')); dispatchEvent(new Event('focus')); });
    await pending(late);
    assert.equal(await late.evaluate(() => window.GRAFPublicAnalytics.sentEvents.length), 0);
    await tab.close(); await late.close();
    console.log('ok_late_cross_tab_and_resume_do_not_regrant');
    // Resume events preserve only an unchanged, explicit in-flight choice.
    for (const action of ['revoke', 'grant']) for (const event of ['focus', 'visibilitychange']) {
      const choice = await open();
      const held = hold(action);
      const before = requests.length;
      await choice.locator('.cm__btns [data-role="all"]').click(); await held.arrived;
      await resume(choice, event); await noTraffic(choice);
      assert.equal(await choice.evaluate(() => window.GRAFPublicAnalytics.consentPending), true);
      held.release(); intercept = null; await ready(choice);
      assert.deepEqual(requests.slice(before).map(r => r.action), ['revoke', 'grant']);
      await choice.waitForFunction(() => window.GRAFPublicAnalytics.sentEvents.length > 0);
      await choice.close();
    }
    console.log('ok_resume_preserves_explicit_revoke_and_grant');

    for (const action of ['revoke', 'grant']) for (const change of ['storage', 'storage-clear', 'pageshow', 'cross-tab-clear',
      'data', 'data-without-event', 'corrupt', 'deleted', 'unavailable']) {
      const choice = await open();
      const held = hold(action);
      const before = requests.length;
      await choice.locator('.cm__btns [data-role="all"]').click(); await held.arrived;
      let writer;
      if (change === 'cross-tab-clear') {
        writer = await context.newPage(); await writer.goto(origin);
        await writer.evaluate(() => localStorage.clear());
        await choice.waitForFunction(() => !window.GRAFPublicAnalytics.consentPending);
      } else {
        await choice.evaluate(({ key, change }) => {
          if (change === 'data' || change === 'data-without-event') {
            window.CookieConsent.setCookieData({ mode: 'update', value: { graf_consent_copy_version: 'changed' } });
          } else if (change === 'corrupt') localStorage.setItem(key, '{broken');
          else if (change === 'deleted') localStorage.removeItem(key);
          else if (change === 'unavailable') {
            const original = Storage.prototype.getItem;
            Storage.prototype.getItem = function (name) {
              if (name === key) throw new Error('storage unavailable');
              return original.call(this, name);
            };
          }
          if (change === 'storage' || change === 'storage-clear') {
            dispatchEvent(new StorageEvent('storage', { key: change === 'storage' ? key : null }));
          } else if (change !== 'data-without-event') {
            dispatchEvent(new Event(change === 'pageshow' ? 'pageshow' : 'focus'));
          }
        }, { key: KEY, change });
      }
      await noTraffic(choice);
      const response = choice.waitForResponse(r => r.url().endsWith(CONTROL) &&
        r.request().postDataJSON().action === action);
      held.release(); intercept = null;
      await (await response).finished();
      // Let the response continuation run before observing the stable denial.
      await choice.evaluate(() => new Promise(resolve => setTimeout(resolve, 0)));
      await choice.waitForFunction(() => !window.GRAFPublicAnalytics.consentPending);
      await noTraffic(choice);
      const mutations = requests.slice(before).filter(r => r.action !== 'read');
      assert.deepEqual(mutations.map(r => r.action), action === 'grant' ? ['revoke', 'grant'] : ['revoke']);
      assert.equal(await choice.evaluate(() => window.GRAFPublicAnalytics.currentConsentState), 'unknown');
      if (change === 'data-without-event') await pending(choice);
      if (change === 'data' || change === 'data-without-event') {
        assert.equal((await cookie(choice)).data.graf_consent_copy_version, 'changed');
        assert.equal((await cookie(choice)).data.graf_public_consent_epoch, null);
      }
      if (writer) await writer.close();
      await choice.close();
    }
    console.log('ok_changed_storage_and_restore_discard_late_grant');

    for (const status of [503, 409]) {
      const choice = await open();
      intercept = async (body, reply) => {
        if (body.action !== 'grant') return false;
        reply(status, { accepted: false, reason: status === 409 ? 'choice_stale' : 'choice_unavailable' });
        return true;
      };
      const before = requests.length;
      await choice.locator('.cm__btns [data-role="all"]').click(); await pending(choice);
      await noTraffic(choice);
      assert.equal(await choice.locator('[data-consent-retry]').innerText(), 'Подтвердить выбранное разрешение');
      assert.deepEqual(requests.slice(before).map(r => r.action), ['revoke', 'grant']);
      intercept = null;
      const retryStart = requests.length;
      await choice.locator('[data-consent-retry]').click(); await ready(choice);
      assert.deepEqual(requests.slice(retryStart).map(r => r.action), ['revoke', 'grant']);
      await choice.close();
    }
    console.log('ok_grant_errors_require_explicit_retry');

    for (const changed of [false, true]) {
      const choice = await open(config, noEpoch); await pending(choice);
      await choice.evaluate(() => {
        const run = window.CookieConsent.run;
        window.CookieConsent.run = async options => {
          await run(options);
          await new Promise(resolve => { window.__releaseConsentRun = resolve; });
        };
      });
      const before = requests.length;
      await choice.locator('[data-consent-retry]').click();
      await choice.waitForFunction(() => Boolean(window.__releaseConsentRun));
      if (changed) await choice.evaluate(() => window.CookieConsent.setCookieData({
        mode: 'update', value: { graf_consent_copy_version: 'changed-during-run' },
      }));
      else await resume(choice, 'focus');
      await noTraffic(choice);
      assert.equal(await choice.evaluate(() => window.GRAFPublicAnalytics.consentPending), true);
      await choice.evaluate(() => window.__releaseConsentRun());
      await choice.waitForFunction(() => !window.GRAFPublicAnalytics.consentPending);
      if (changed) {
        await noTraffic(choice);
        assert.deepEqual(requests.slice(before), []);
        await pending(choice);
        assert.equal((await cookie(choice)).data.graf_consent_copy_version, 'changed-during-run');
      } else {
        await ready(choice);
        assert.deepEqual(requests.slice(before).map(r => r.action), ['revoke', 'grant']);
      }
      await choice.close();
    }
    console.log('ok_retry_library_run_checks_the_full_choice');

    console.log('public_consent_control_browser=pass');
  } finally {
    await context.close(); await browser.close();
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
