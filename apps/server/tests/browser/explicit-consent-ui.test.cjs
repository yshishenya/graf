const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require(require.resolve('playwright', {
  paths: [process.env.GRAF_NODE_MODULES || path.join(__dirname, 'node_modules')],
}));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const origin = process.argv[2];
  const control = async (data) => (await page.request.post(origin + '/__scenario', { data })).json();
  const context = async () => (await page.request.get(origin + '/api/v1/product-analytics/explicit-context')).json();
  const stats = async () => (await page.request.get(origin + '/__stats')).json();
  const choice = async (role) => page.locator('#cc-main button[data-role="' + role + '"]:visible').first().click();
  const preferences = async () => {
    await page.locator('[data-cc="show-preferencesModal"]').click();
    await page.locator('#cc-main .pm:visible').waitFor();
  };
  const saved = async (text) => {
    await page.waitForFunction((text) => document.querySelector('#graf-explicit-consent-status')?.textContent === text, text);
  };
  try {
    await control({ reset: true });
    await page.goto(origin + '/meetings');
    await page.locator('#cc-main .cm:visible').waitFor();
    assert.equal((await stats()).writes, 0, 'hydration cannot grant consent');
    await choice('all');
    await saved('Выбор аналитики сохранён.');
    assert.equal((await context()).telemetry_gate_state, 'accepted');
    assert.equal((await stats()).writes, 1);
    assert.deepEqual(await page.evaluate(() => window.__consentSignals), ['pending', 'changed']);
    await page.reload();
    await page.waitForFunction(() => window.CookieConsent && window.__GRAF_ANALYTICS_CONTROLLER_LOADED__);
    assert.equal((await stats()).writes, 1, 'persisted choice cannot grant consent again');
    await preferences();
    await choice('save');
    await saved('Выбор аналитики сохранён.');
    assert.equal((await stats()).writes, 2, 'unchanged save is still an explicit action');
    await preferences();
    await choice('necessary');
    await saved('Согласие на аналитику отозвано.');
    assert.equal((await context()).telemetry_gate_state, 'withdrawn');

    await preferences();
    await choice('all');
    await saved('Выбор аналитики сохранён.');
    await control({ stale: true });
    await preferences();
    await choice('necessary');
    await saved('Согласие на аналитику отозвано.');
    assert.equal((await context()).telemetry_gate_state, 'withdrawn', 'stale notice still permits withdrawal');
    const beforeStaleAccept = (await stats()).writes;
    await preferences();
    await choice('all');
    await saved('Сохранение согласия не подтверждено. Повторите выбор в настройках cookies.');
    assert.equal((await stats()).writes, beforeStaleAccept);
    await control({ stale: false, identityChanged: true });
    await preferences();
    await choice('all');
    await saved('Сохранение согласия не подтверждено. Повторите выбор в настройках cookies.');
    assert.equal((await stats()).writes, beforeStaleAccept, 'old page cannot accept for a new account');

    await control({ identityChanged: false, failWrite: true });
    await preferences();
    await choice('all');
    await saved('Сохранение согласия не подтверждено. Повторите выбор в настройках cookies.');
    assert.equal((await context()).telemetry_gate_state, 'withdrawn');
    await control({ failWrite: false });
    await preferences();
    await choice('all');
    await saved('Выбор аналитики сохранён.');

    await control({ loseReply: true });
    await page.evaluate(() => { window.__consentSignals = []; });
    await preferences();
    await choice('necessary');
    await saved('Отзыв согласия не подтвержден. Повторите выбор в настройках cookies.');
    assert.equal((await context()).telemetry_gate_state, 'withdrawn', 'lost response is not failed server commit');
    assert.deepEqual(await page.evaluate(() => window.__consentSignals), ['pending']);
    await control({ loseReply: false });
    await preferences();
    await choice('necessary');
    await saved('Согласие на аналитику отозвано.');

    await control({ delay: true });
    const beforeDouble = (await stats()).writes;
    await preferences();
    await page.locator('#cc-main button[data-role="all"]:visible').first().dblclick();
    await saved('Выбор аналитики сохранён.');
    assert.equal((await stats()).writes, beforeDouble + 1, 'double click does not duplicate the in-flight choice');
    await preferences();
    await choice('necessary');
    await saved('Согласие на аналитику отозвано.');
    const beforeRace = (await stats()).writes;
    await page.evaluate(() => { window.__consentSignals = []; });
    await preferences();
    await choice('all');
    // Genuine second click while the accept response is still in flight.
    await preferences();
    await choice('necessary');
    await saved('Согласие на аналитику отозвано.');
    assert.equal((await context()).telemetry_gate_state, 'withdrawn');
    assert.equal((await stats()).writes, beforeRace + 2, 'pending revoke must not be dropped');
    assert.deepEqual(await page.evaluate(() => window.__consentSignals), ['pending', 'pending', 'changed']);
    const beforeSynthetic = (await stats()).writes;
    await page.evaluate(() => document.querySelector('#cc-main button[data-role="all"]').click());
    await page.waitForTimeout(100);
    assert.equal((await stats()).writes, beforeSynthetic, 'untrusted click cannot grant consent');
    await control({ switchAccount: "B", delay: false });
    await preferences();
    await choice('all');
    await saved('Сохранение согласия не подтверждено. Повторите выбор в настройках cookies.');
    assert.equal((await stats()).writes, beforeSynthetic, 'old account page cannot write new account consent');
    assert.equal((await context()).telemetry_gate_state, 'not_seen');
    await page.reload();
    const accountConfig = await page.evaluate(() => JSON.parse(document.querySelector('#graf-product-analytics-provider-config').textContent));
    assert.equal(accountConfig.explicit_funnel.user_pseudonym, (await context()).stable_pseudonymous_user_id, 'render must use current account');
    await page.locator('#cc-main .cm:visible').waitFor({ timeout: 5000 }).catch(async error => {
      console.error(JSON.stringify(await page.evaluate(() => ({ key: JSON.parse(document.querySelector('#graf-product-analytics-provider-config').textContent).consent_storage_key, keys: Object.keys(localStorage), modal: document.querySelector('#cc-main')?.textContent.slice(0,80) }))));
      throw error;
    });
    assert.equal((await stats()).writes, beforeSynthetic, 'new account hydration does not import old cookie');
    await choice('all');
    await saved('Выбор аналитики сохранён.');
    assert.equal((await context()).telemetry_gate_state, 'accepted');
    await control({ switchAccount: "A" });
    assert.equal((await context()).telemetry_gate_state, 'withdrawn', 'account B choice must not alter A');
    assert.equal((await stats()).providerCalls, 0, 'consent UI sends no capture');
    console.log('PASS real vendored notice → authenticated API → disposable PostgreSQL; accept/save/revoke/reload/stale/account mismatch/error/lost reply/pending revoke/untrusted click');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
