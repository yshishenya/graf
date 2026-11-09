const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, webkit } = require(require.resolve('playwright', { paths: [process.env.GRAF_NODE_MODULES || process.cwd()] }));
const cabinet = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js');
const origin = 'https://graf.test';
const meeting = 'a0000000-0000-4000-8000-000000000007';
const own = '/meetings/' + meeting;
const shared = '/shared-meetings/' + meeting.toUpperCase() + '?workspace_id=00000000-0000-4000-8000-000000000008';
const detail = url => `<meta charset="utf-8"><meta name="csrf-token" content="synthetic">
  <div data-cabinet-shell><main id="cabinet-main" data-meeting-id="${meeting}" data-playback-poll-url="${url}" data-cabinet-embedded="true">
  <h1>Синтетическая расшифровка</h1></main>
  <section class="playback-bar"><audio data-playback-player></audio></section>
  <template data-meeting-detail-recovery-template><main tabindex="-1"><section data-cabinet-state>
  <h1 id="recovery">Ошибка</h1><p class="cabinet-state__description"></p><p class="cabinet-state__action"><a href="/meetings">К списку</a></p></section></main></template></div>`;

(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch();
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(4000);
    let status = 200, summary = false, hold = null, ownerChecks = 0, sharedChecks = 0;
    await page.route(origin + '/**', async route => {
      const request = route.request();
      const url = request.url().slice(origin.length);
      if (url === '/api/v1/desktop/recordings/lifecycle') {
        ownerChecks++;
        return route.fulfill({ json: [{ target_type: 'meeting', target_id: meeting, state: page.url().includes('/shared-meetings/') ? 'unavailable' : 'allowed' }] });
      }
      if (url === shared && !request.isNavigationRequest()) {
        sharedChecks++;
        assert.equal(request.headers()['x-graf-client'], 'desktop');
        if (hold) await hold;
        return route.fulfill({ status, contentType: 'text/html', body: summary ? '<main>Только итоги</main>' : detail(shared) });
      }
      return route.fulfill({ contentType: 'text/html', body: detail(url) });
    });
    const polled = () => page.waitForResponse(response => response.url() === origin + shared && !response.request().isNavigationRequest());
    const focus = () => page.evaluate(() => window.dispatchEvent(new Event('focus')));
    const retain = async () => {
      assert.equal(await page.getByText('Синтетическая расшифровка', { exact: true }).count(), 1);
      assert.equal(await page.locator('audio').count(), 1);
      assert.equal(ownerChecks, 0, 'addressed meeting must never query the personal workspace');
    };
    const openShared = async () => {
      await page.goto(origin + shared);
      const response = polled();
      await page.addScriptTag({ path: cabinet });
      await (await response).finished();
      await retain();
    };
    await openShared();
    status = 503;
    let response = polled();
    await focus();
    assert.equal((await response).status(), 503);
    await retain();
    status = 404;
    response = polled();
    await focus();
    assert.equal((await response).status(), 404);
    await page.getByRole('heading', { name: 'Встреча больше недоступна' }).waitFor();
    assert.equal(await page.locator('audio').count(), 0);

    status = 200;
    await openShared();
    summary = true;
    response = polled();
    await focus();
    assert.equal((await response).status(), 200);
    await page.getByRole('heading', { name: 'Встреча больше недоступна' }).waitFor();
    assert.equal(await page.locator('audio').count(), 0);

    summary = false;
    await openShared();
    let release;
    hold = new Promise(resolve => { release = resolve; });
    const inFlight = page.waitForRequest(request => request.url() === origin + shared);
    response = polled();
    await focus();
    await inFlight;
    await page.evaluate(url => {
      const main = document.querySelector('main');
      const next = main.cloneNode(true);
      next.dataset.playbackPollUrl = url;
      next.querySelector('h1').textContent = 'Своя запись после перехода';
      main.replaceWith(next);
      history.replaceState(null, '', url);
    }, own);
    status = 404;
    release();
    await (await response).finished();
    assert.equal(await page.getByRole('heading', { name: 'Своя запись после перехода' }).count(), 1);
    const ownerResponse = page.waitForResponse(r => r.url().endsWith('/desktop/recordings/lifecycle'));
    await focus();
    await ownerResponse;
    assert.equal(ownerChecks, 1);
    assert.equal(sharedChecks, 7);
    console.log('Addressed lifecycle: retain, transient error, revoke, summary downgrade, stale reply and own scope PASS');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
