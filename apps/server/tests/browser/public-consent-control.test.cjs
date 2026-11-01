/* Real vendored CookieConsent + loopback control API. No external delivery. */
const assert = require('node:assert/strict');
const http = require('node:http');
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
  const requests = [], events = [], rows = new Map();
  let intercept = null;
  const server = http.createServer(async (req, res) => {
    if (req.method !== 'POST') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
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
    document.querySelector('[data-consent-retry]').hidden === false);
  const ready = page => page.waitForFunction(() =>
    window.GRAFPublicAnalytics.currentConsentState !== 'unknown' &&
    window.GRAFPublicAnalytics.consentPending === false);
  const open = async (cfg = config, seed) => {
    const page = await context.newPage(); await page.goto(origin);
    await page.evaluate(({ key, seed }) => seed
      ? localStorage.setItem(key, JSON.stringify(seed)) : localStorage.removeItem(key), { key: KEY, seed });
    await loadController(page, cfg); return page;
  };
  try {
    const page = await open();
    await page.locator('.cm__btns [data-role="all"]').click();
    await ready(page);
    const accepted = await cookie(page);
    assert.equal(accepted.data.graf_public_consent_epoch, rows.get(accepted.consentId).epoch);
    assert.deepEqual(requests.map(r => r.action), ['revoke', 'grant']);
    assert.equal(requests[1].expected_epoch !== accepted.data.graf_public_consent_epoch, true);
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
    console.log('public_consent_control_browser=pass');
  } finally {
    await context.close(); await browser.close();
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
