const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, webkit } = require(require.resolve('playwright', {
  paths: [process.env.GRAF_NODE_MODULES || process.cwd()],
}));
const script = fs.readFileSync(process.env.GRAF_CABINET_SCRIPT || path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js'));
const meeting = '20000000-0000-0000-0000-000000000001';
const workspace = '20000000-0000-0000-0000-000000000002';
const origin = 'https://graf.test';
const detail = '/shared-meetings/' + meeting + '?workspace_id=' + workspace;
const before = 'a'.repeat(24);
const after = 'b'.repeat(24);
const fragment = '#recording?position_ms=1500';
const wav = Buffer.alloc(44 + 80000, 128);
wav.write('RIFF', 0); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8);
wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
wav.writeUInt32LE(8000, 24); wav.writeUInt32LE(8000, 28); wav.writeUInt16LE(1, 32);
wav.writeUInt16LE(8, 34); wav.write('data', 36); wav.writeUInt32LE(wav.length - 44, 40);
const audio = 'data:audio/wav;base64,' + wav.toString('base64');
const fixture = (version, pending, source = audio, turn = "Turn", replaceDetail = false) => [
  '<meta charset="utf-8"><script defer src="/cabinet.js"></script><button id="keep">Keep focus</button>',
  '<main class="detail-page-main" data-meeting-id="' + meeting + '" data-share-media-version="' + version + '"',
  ' data-playback-poll-url="' + detail.replaceAll('&', '&amp;') + '" data-playback-poll-active="' + pending + '"',
  replaceDetail ? ' data-processing-status-url="/processing" data-processing-transcript-content-ready="false" data-processing-summary-content-ready="true"' : '',
  '>',
  replaceDetail ? '<aside data-processing-recovery></aside>' : '',
  '<button role="tab" data-detail-tab="outcomes" aria-selected="true">Outcomes</button>',
  '<button role="tab" data-detail-tab="recording" aria-selected="false">Recording</button>',
  '<section data-detail-panel="outcomes"></section><section data-detail-panel="recording" hidden>',
  '<div data-playback-transcript><article data-transcript-turn data-start-seconds="1" data-end-seconds="2" tabindex="-1">' + turn + '</article></div>',
  '</section></main><section class="detail-playback" data-playback-shell data-playback-state="available" data-media-revision-id="' + version + '">',
  '<audio data-playback-player preload="metadata" src="' + source + '"></audio>',
  '<input type="range" data-playback-progress aria-label="Position" min="0" max="10" step="0.1"></section>',
].join('');


// Hold the real WAV response until after the actual background refresh. Native
// metadata/currentTime remain real; instrumentation records calls without faking them.
const delayedRefresh = async (browser, replaceDetail, cancel = '') => {
  const page = await browser.newPage();
  let releaseAudio, releaseStatus;
  const audioGate = new Promise(resolve => { releaseAudio = resolve; });
  const statusGate = new Promise(resolve => { releaseStatus = resolve; });
  let polls = 0;
  let version = before;
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    window.playCalls = 0;
    window.seekCalls = [];
    const play = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function (...args) {
      ++window.playCalls;
      return play.apply(this, args);
    };
    const time = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime');
    Object.defineProperty(HTMLMediaElement.prototype, 'currentTime', {
      ...time,
      set(value) {
        window.seekCalls.push({ player: this, value });
        return time.set.call(this, value);
      },
    });
  });
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== origin) return route.abort();
    if (url.pathname === '/cabinet.js') return route.fulfill({ contentType: 'application/javascript', body: script });
    if (url.pathname === '/delayed.wav') {
      await audioGate;
      const range = /^bytes=(\d+)-(\d*)$/.exec(route.request().headers().range || '');
      const start = range ? Number(range[1]) : 0;
      const end = range?.[2] ? Math.min(Number(range[2]), wav.length - 1) : wav.length - 1;
      return route.fulfill({
        status: range ? 206 : 200, contentType: 'audio/wav', body: wav.subarray(start, end + 1),
        headers: { 'Accept-Ranges': 'bytes', ...(range ? { 'Content-Range': `bytes ${start}-${end}/${wav.length}` } : {}) },
      });
    }
    if (url.pathname === '/processing') {
      await statusGate;
      return route.fulfill({ json: {
        meeting_id: meeting, state: 'processed', retry_class: 'none',
        artifacts: {
          transcript: { state: 'available', visible: true },
          diarization: { state: 'available', visible: true },
          summary: { state: 'available', visible: true },
        },
      } });
    }
    const poll = route.request().headers()['hx-request'] === 'true';
    if (poll) ++polls;
    let body = fixture(version, !replaceDetail && !poll, '/delayed.wav', 'Turn ' + polls, replaceDetail);
    if (replaceDetail && poll) body = body.replace('data-processing-transcript-content-ready="false"', 'data-processing-transcript-content-ready="true"');
    return route.fulfill({ contentType: 'text/html', body });
  });
  const refresh = async (first = false) => {
    const nextPoll = polls + 1;
    if (replaceDetail && first) releaseStatus();
    else await page.evaluate(replace => {
      const detail = document.querySelector('main');
      if (replace) detail.dataset.processingTranscriptContentReady = 'false';
      else detail.dataset.playbackPollActive = 'true';
      window.dispatchEvent(new Event('online'));
    }, replaceDetail);
    await page.waitForFunction(text => document.querySelector('[data-transcript-turn]')?.textContent === text, 'Turn ' + nextPoll);
    // Replacement schedules initCabinet; wait for its actual initialization.
    if (replaceDetail) await page.waitForFunction(() => document.querySelector('[data-processing-recovery]').dataset.processingRecoveryReady === 'true');
  };
  try {
    await page.goto(origin + detail + '&media_version=' + before + fragment, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelector('audio')?.readyState === 0 && document.querySelector('[data-detail-tab="recording"]').getAttribute('aria-selected') === 'true');
    await page.addStyleTag({ content: '.detail-page-main { height: 200px; overflow-y: auto; } [data-transcript-turn] { margin-top: 500px; margin-bottom: 500px; }' });
    await page.locator('#keep').focus();
    await page.evaluate(() => {
      window.oldPlayer = document.querySelector('audio');
      window.oldDetail = document.querySelector('main');
      window.oldTurn = document.querySelector('[data-transcript-turn]');
    });
    if (cancel === 'version') version = after;
    if (cancel === 'navigation') await page.evaluate(() => new Promise(resolve => {
      window.addEventListener('hashchange', resolve, { once: true });
      location.hash = '#outcomes';
    }));
    if (cancel === 'manual') await page.locator('[data-playback-progress]').evaluate(control => {
      control.value = '0';
      control.dispatchEvent(new Event('input', { bubbles: true }));
    });
    if (cancel === 'tab') {
      await page.locator('[data-detail-tab="outcomes"]').click();
      await page.locator('#keep').focus();
    }
    await refresh(true);
    assert.equal(await page.locator('audio').evaluate(player => player.readyState), 0, 'metadata must still be held after refresh');
    assert.deepEqual(await page.evaluate(() => [oldDetail.isConnected, oldTurn.isConnected, oldPlayer === document.querySelector('audio')]),
      [!replaceDetail, false, !replaceDetail && cancel !== 'version'], 'exercise the real retained/replaced detail path');
    // Install the event barrier before releasing real metadata to the current player.
    await page.evaluate(() => {
      const player = document.querySelector('audio');
      window.metadataReady = player.readyState >= 1 ? Promise.resolve()
        : new Promise(resolve => player.addEventListener('loadedmetadata', resolve, { once: true }));
    });
    releaseAudio();
    await page.evaluate(() => metadataReady);
    await page.waitForFunction(() => !document.querySelector("audio").seeking);
    await page.evaluate(() => { if (!oldPlayer.isConnected) oldPlayer.dispatchEvent(new Event('loadedmetadata')); });
    const addressedSeeks = () => page.evaluate(() => seekCalls.filter(call => call.value === 1.5).length);
    assert.equal(await page.locator('audio').evaluate(player => player.currentTime), cancel ? 0 : 1.5,
      `${replaceDetail ? 'replaced' : 'retained'} detail: ${cancel || 'pending seek survives transcript refresh'}`);
    assert.equal(await addressedSeeks(), cancel ? 0 : 1, 'apply the original intent only once, or cancel it');
    if (!cancel) assert.equal(await page.locator('main').evaluate(node => node.scrollTop > 0), true, 'follow the current transcript');
    assert.equal(await page.locator('audio').evaluate(player => player.paused), true);
    assert.equal(await page.evaluate(() => playCalls), 0);
    assert.equal(await page.locator('#keep').evaluate(node => node === document.activeElement), true);
    if (cancel === 'version') assert.equal(await page.locator('[data-shared-version-notice]').count(), 1);
    const count = await addressedSeeks();
    await refresh();
    assert.equal(await addressedSeeks(), count, 'a subsequent refresh must not revive a consumed/cancelled intent');
    if (replaceDetail || cancel === 'version') assert.equal(await page.evaluate(() => oldPlayer.currentTime), 0, 'detached player must not receive the original seek');
    // A genuinely new valid URL navigation still applies its own position.
    await page.evaluate(currentVersion => new Promise(resolve => {
      const target = new URL(location.href);
      target.searchParams.set('media_version', currentVersion);
      history.replaceState(null, '', target);
      window.addEventListener('hashchange', resolve, { once: true });
      location.hash = '#recording?position_ms=2500';
    }), version);
    assert.equal(await page.locator('audio').evaluate(player => player.currentTime), 2.5);
    assert.equal(await page.evaluate(() => playCalls), 0);
    assert.equal(await page.locator('#keep').evaluate(node => node === document.activeElement), true);
    assert.deepEqual(errors, []);
    console.log(`PASS delayed metadata: ${replaceDetail ? 'replaced' : 'retained'} detail / ${cancel || 'preserve once'}`);
  } finally {
    releaseStatus(); releaseAudio();
    await page.close();
  }
};

(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch();
  try {
    console.log('Browser', process.env.GRAF_BROWSER || 'chromium', browser.version());
    for (const replaceDetail of [false, true]) {
      for (const cancel of ['', 'version', 'navigation', 'manual', 'tab']) await delayedRefresh(browser, replaceDetail, cancel);
    }
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.origin !== origin) return route.abort();
      if (url.pathname === '/cabinet.js') return route.fulfill({ contentType: 'application/javascript', body: script });
      const poll = route.request().headers()['hx-request'] === 'true';
      return route.fulfill({ contentType: 'text/html', body: fixture(poll ? after : before, !poll) });
    });
    const ready = () => page.waitForFunction(() => document.querySelector('audio').readyState >= 1);
    const time = () => page.locator('audio').evaluate(player => player.currentTime);
    const changeHash = hash => page.evaluate(value => new Promise(resolve => {
      window.addEventListener('hashchange', resolve, { once: true });
      location.hash = value;
    }), hash);
    const notice = page.locator('[data-shared-version-notice]');
    await page.goto(origin + detail + fragment);
    await ready();
    assert.equal(await time(), 0, 'a position without a version must not seek');

    await page.goto(origin + detail + '&media_version=' + before + '#outcomes');
    await ready();
    await page.evaluate(() => { window.oldPlayer = document.querySelector('audio'); window.dispatchEvent(new Event('online')); });
    await page.waitForFunction(version => document.querySelector('.detail-playback').dataset.mediaRevisionId === version, after);
    await ready();
    await page.locator('#keep').focus();
    await changeHash(fragment);
    assert.equal(await time(), 0, 'a link for the replaced version must not seek in the new recording');
    assert.equal(await notice.count(), 1);
    assert.equal(await page.locator('#keep').evaluate(node => node === document.activeElement), true);
    assert.deepEqual(await page.evaluate(() => [oldPlayer.isConnected, oldPlayer.currentTime]), [false, 0]);

    await page.evaluate(version => {
      const target = new URL(location.href);
      target.searchParams.set('media_version', version);
      history.replaceState(null, '', target);
    }, after);
    await changeHash('#outcomes');
    await changeHash(fragment);
    assert.equal(await time(), 1.5);
    assert.equal(await notice.count(), 0);
    assert.equal(await page.locator('audio').evaluate(player => player.paused), true);
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
