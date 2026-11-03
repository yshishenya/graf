/* Manual, isolated analytics-only proof. SDK bytes stay outside Git.
 * node public-analytics-sdk-network.test.cjs --sdk-file /abs/tag.js --sdk-sha256 <sha256>
 * No request is forwarded. Local replies and a finite 20s observation do not
 * accept replay, real backend settings, server revocation, runtime or T0.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { parseArgs } = require('node:util');

function sdkInput() {
  const { values } = parseArgs({ options: {
    'sdk-file': { type: 'string' }, 'sdk-sha256': { type: 'string' },
  } });
  assert.ok(values['sdk-file'] && path.isAbsolute(values['sdk-file']), 'absolute SDK file required');
  assert.match(values['sdk-sha256'] || '', /^[a-f0-9]{64}$/, 'SDK SHA-256 required');
  const bytes = fs.readFileSync(values['sdk-file']);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), values['sdk-sha256'], 'SDK hash mismatch');
  return bytes;
}

async function main() {
  // Validate before loading browser dependencies or launching a browser.
  const sdk = sdkInput();
  const { chromium } = require(require.resolve('playwright', {
    paths: [process.env.GRAF_NODE_MODULES || path.join(__dirname, 'node_modules')],
  }));
  const { readConfig, loadController } = require('./public-analytics-consent-modal.test.cjs');
  const origin = 'https://graf-sdk-test.invalid';
  const counter = 99999999;
  const browser = await chromium.launch({ headless: true });
  try {
    for (const pagePath of ['/', '/download']) {
      for (const crossTab of [false, true]) {
        const context = await browser.newContext({ serviceWorkers: 'block' });
        try {
          let phase = 'setup';
          const attempts = [];
          const config = readConfig(pagePath);
          config.yandex_metrica_id = String(counter);
          config.validation_mode = 'provider_smoke';
          await context.routeWebSocket('**/*', (socket) => {
            attempts.push({ phase, kind: 'websocket' });
            socket.close();
          });
          await context.route('**/*', async (route) => {
            const request = route.request();
            const url = new URL(request.url());
            if (url.origin === origin && url.pathname === pagePath && request.isNavigationRequest()) {
              return route.fulfill({ contentType: 'text/html', body:
                '<!doctype html><html lang="ru"><head></head><body style="height:3000px"><button id="exercise">Учебный клик</button></body></html>' });
            }
            const isTag = url.href === 'https://mc.yandex.ru/metrika/tag.js';
            const watch = ['mc.yandex.ru', 'mc.yandex.com'].includes(url.hostname) && url.pathname.startsWith('/watch/');
            const relay = url.origin === origin && url.pathname === config.posthog_capture_endpoint;
            attempts.push({ phase, kind: isTag ? 'sdk' : watch ? 'watch' : relay ? 'relay' : request.resourceType() });
            if (isTag) return route.fulfill({ contentType: 'application/javascript', body: sdk });
            if (watch) return route.fulfill({ contentType: 'application/json',
              headers: { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true' },
              body: JSON.stringify({ settings: { eu: 0 }, userData: {} }) });
            if (relay) return route.fulfill({ contentType: 'application/json', body: '{}' });
            return route.abort('blockedbyclient');
          });
          const pages = [];
          async function openPage() {
            const page = await context.newPage();
            pages.push(page);
            await page.goto(origin + pagePath);
            await loadController(page, config);
            return page;
          }
          const first = await openPage();
          phase = 'granted';
          await first.evaluate(() => window.CookieConsent.acceptCategory(['necessary', 'analytics']));
          const chooser = crossTab ? await openPage() : first;
          for (const page of pages) {
            await page.waitForFunction(() => Boolean(window.yaCounter99999999), null, { timeout: 10000 });
          }
          await first.waitForTimeout(2000);
          assert.ok(attempts.some((a) => a.phase === 'granted' && a.kind === 'watch'), 'positive watch required');
          for (const page of pages) {
            assert.equal(await page.evaluate(() => Boolean(window.yaCounter99999999)), true, 'positive instance required');
          }
          // Negative-control injection point: only a temporary copy alters destruct.
          phase = 'revoked';
          await chooser.evaluate(() => window.CookieConsent.acceptCategory('necessary'));
          // CookieConsent dispatch and cross-tab storage notifications are asynchronous.
          for (const page of pages) {
            await page.waitForFunction(() => !window.yaCounter99999999, null, { timeout: 5000 })
              .catch(async (error) => {
                if (error.name === 'TimeoutError' && await page.evaluate(() => Boolean(window.yaCounter99999999))) {
                  throw new Error('instance-still-present');
                }
                throw error;
              });
            assert.deepEqual(await page.evaluate((key) => JSON.parse(localStorage.getItem(key)).categories,
              config.consent_storage_key), ['necessary']);
            await page.locator('#exercise').click();
            await page.mouse.wheel(0, 800);
            await page.evaluate(() => {
              window.dispatchEvent(new Event('focus'));
              window.dispatchEvent(new Event('resize'));
              document.dispatchEvent(new Event('visibilitychange'));
            });
          }
          await first.waitForTimeout(20000);
          const after = attempts.filter((a) => a.phase === 'revoked');
          assert.equal(after.length, 0, 'optional attempt after revoke');
          console.log(JSON.stringify({ page: pagePath, revoke: crossTab ? 'cross-tab' : 'same-tab',
            beforeWatchAttempts: attempts.filter((a) => a.phase === 'granted' && a.kind === 'watch').length,
            afterAttempts: after.length, observedAfterMs: 20000, verdict: 'pass' }));
        } finally {
          await context.close();
        }
      }
    }
    console.log('public_analytics_sdk_network=pass');
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  // Do not print request URLs, SDK contents or browser state on failure.
  console.error(error.code || error.message || 'sdk-profile-failed');
  process.exitCode = 1;
});
