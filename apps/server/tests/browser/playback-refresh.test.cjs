const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, webkit } = require(require.resolve('playwright', { paths: [process.env.GRAF_NODE_MODULES || process.cwd()] }));
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
const source = fs.readFileSync(path.join(assets, 'cabinet.js'), 'utf8');
const section = (start, end) => source.includes(start) ? source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start))) : '';
const wav = Buffer.alloc(44 + 160000, 128);
wav.write('RIFF', 0); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8);
wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
wav.writeUInt32LE(8000, 24); wav.writeUInt32LE(8000, 28); wav.writeUInt16LE(1, 32);
wav.writeUInt16LE(8, 34); wav.write('data', 36); wav.writeUInt32LE(160000, 40);
const audioSource = `data:audio/wav;base64,${wav.toString('base64')}`;
const html = ready => `<meta charset="utf-8"><button id="outside">Вне формы</button>
<main data-playback-poll-url="/meeting" data-summary-rendered-state="processing" data-processing-transcript-content-ready="${ready}">
<div data-playback-transcript>${ready ? [2, 6].map((start, i) => `<article data-transcript-turn data-speaker-key="s${i}" data-source-segments="seg${i}" data-start-seconds="${start}" data-end-seconds="${start + 3}" tabindex="-1">Синтетическая реплика</article>`).join('') : ''}</div></main>
<section class="detail-playback" data-playback-shell data-meeting-id="meeting" data-workspace-id="workspace" data-media-revision-id="media" data-processing-result-id="${ready ? 'result' : ''}" data-source-mode="archive">
<audio data-playback-player src="${audioSource}"></audio>
<div class="speaker-timeline-resize-row" ${ready ? '' : 'hidden'}><div data-speaker-timeline-resize></div></div>
<div class="playback-tools"><button data-playback-timeline-toggle ${ready ? '' : 'disabled'}>Дорожки</button>
<div class="playback-menu-anchor" ${ready ? '' : 'hidden'}><button data-playback-listen-toggle>Слушать</button><div data-playback-listen-menu hidden><input data-listen-all type="checkbox" checked>${ready ? '<input type="checkbox" data-listen-speaker="s0"><input type="checkbox" data-listen-speaker="s1">' : ''}</div></div>
<button data-playback-comment>Комментарий</button>${ready ? '<div data-speaker-manager>Спикеры</div>' : ''}</div>
<button data-playback-toggle>Воспроизвести</button><button data-playback-next ${ready ? '' : 'disabled'}>Следующая</button>
<div data-playback-carousel ${ready ? '' : 'hidden'}><button data-avatar-scroll="-1">Назад</button><div data-playback-avatars>${ready ? '<button data-playback-avatar="s0">S0</button><button data-playback-avatar="s1">S1</button>' : ''}</div><button data-avatar-scroll="1">Вперёд</button></div>
<input data-playback-progress type="range" max="20"><span data-playback-current></span><span data-playback-duration></span><span data-playback-listen-status></span>
<span class="playback-speaker-overview">${ready ? '<span class="playback-speaker-interval" data-speaker-key="s0"></span>' : ''}</span>
${ready ? '<div data-speaker-timeline-shell>' : ''}<div data-speaker-timeline data-speaker-timeline-count="${ready ? '2' : '0'}">${ready ? [2, 6].map((start, i) => `<div data-speaker-lane data-speaker-key="s${i}"><div data-timeline-track tabindex="0"><button data-lane-segment data-start-seconds="${start}" data-end-seconds="${start + 3}" data-source-segments="seg${i}">Отрезок ${i}</button></div></div>`).join('') : ''}</div>${ready ? '</div>' : ''}</section>`;

(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch({ headless: true });
  try {
    const page = await browser.newPage();
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    let nextHtml = html(true);
    await page.route('https://graf.test/**', route => route.fulfill(route.request().url().includes('/comments')
      ? { json: { items: [], next_cursor: null, media_revision_id: 'media', source_counts: [], capabilities: { can_comment: true, emoji_options: [] } } }
      : { contentType: 'text/html', body: route.request().headers()['hx-request'] ? nextHtml : html(false) }));
    await page.goto('https://graf.test/meeting');
    await page.addScriptTag({ path: path.join(assets, 'playback-comments.js') });
    await page.addScriptTag({ content: `(() => {
      let processingRecoveryGeneration = 1, processingRecoveryPollTimer = null, playbackRecoveryRequest = null;
      const initPlaybackRecoveryPolling = () => {}, initSpeakerNameForms = () => {};
      const titleEditorActive = () => false, processingTranscriptReady = () => true;
      const processingSummaryState = () => 'generating', processingSummaryPending = () => true;
      const processingProjectionMatchesDetail = () => true, recoverMeetingDetailFromResponse = async () => false;
      const stopProcessingRecoveryCountdown = () => {}, stopProcessingRecoveryPolling = () => {};
      const formatTime = value => String(Math.floor(value)), activateDetailTab = () => {};
      const reportPlaybackFailure = () => { throw Error('Playback failed'); };
      const speakerTimelineResizeHandlers = new WeakMap();
      ${section('const refreshPlaybackContent =', 'const refreshProcessingDetailContentOnce =')}
      ${section('const refreshProcessingDetailContentOnce =', 'const renderProcessingProjection =')}
      ${section('const scrollTranscriptTurnIntoView =', 'const initSourceNavigation =')}
      ${section('const DEFAULT_TIMELINE_HEIGHT =', 'const initCalendarSettings =')}
      ${section('const playbackRecoveryCopy =', 'const initPlaybackRecoveryPolling =')}
      const initCabinet = () => { initPlayback(); initSpeakerTimelineResize(); };
      window.refreshTest = () => refreshProcessingDetailContentOnce(document.querySelector('main'), { state: 'processed', attempt_ordinal: 1 });
      window.recoveryTest = () => { document.querySelector('main').dataset.playbackPollActive = 'true'; return refreshPlaybackRecovery(); };
      initCabinet();
    })();` });
    await page.locator('[data-playback-toggle]').click();
    await page.waitForFunction(() => document.querySelector('audio').currentTime > 0.05);
    await page.getByRole('button', { name: 'Комментарий', exact: true }).click();
    const draft = page.getByRole('textbox', { name: 'Текст комментария' });
    await draft.fill('Незавершённый комментарий');
    await page.evaluate(() => {
      window.savedAudio = document.querySelector('audio'); window.savedDraft = document.querySelector('textarea');
      window.pauseEvents = 0; window.loadEvents = 0;
      savedAudio.addEventListener('pause', () => pauseEvents++);
      savedAudio.addEventListener('loadstart', () => loadEvents++);
      window.startTime = savedAudio.currentTime;
    });
    assert.equal(await page.evaluate(() => window.refreshTest()), true);
    await page.waitForFunction(() => document.querySelector('main').dataset.processingTranscriptContentReady === 'true');
    assert.equal(await page.locator('[data-speaker-lane]').count(), 2, 'first transcript must populate retained playback shell');
    assert.equal(await page.locator('[data-playback-avatar]').count(), 2);
    assert.equal(await page.locator('[data-playback-next]').isEnabled(), true);
    assert.equal(await page.locator('[data-playback-shell]').getAttribute('data-processing-result-id'), 'result');
    assert.deepEqual(await page.evaluate(() => [savedAudio === document.querySelector('audio'), !savedAudio.paused, savedAudio.currentTime >= startTime, pauseEvents, loadEvents, savedDraft === document.querySelector('textarea'), savedDraft === document.activeElement]), [true, true, true, 0, 0, true, true]);
    assert.equal(await draft.inputValue(), 'Незавершённый комментарий');
    await page.evaluate(async () => {
      document.querySelector('main').dataset.processingTranscriptContentReady = 'false';
      await window.refreshTest();
    });
    assert.equal(await draft.inputValue(), 'Незавершённый комментарий', 'repeat refresh retains the same draft');
    await page.getByRole('button', { name: 'Отмена', exact: true }).click();
    await page.locator('[data-playback-timeline-toggle]').click();
    assert.equal(await page.locator('[data-playback-timeline-toggle]').getAttribute('aria-expanded'), 'false', 'one collapse handler after repeated refresh');
    await page.locator('[data-playback-timeline-toggle]').click();
    assert.equal(await page.locator('[data-playback-timeline-toggle]').getAttribute('aria-expanded'), 'true');
    await page.evaluate(() => { savedAudio.pause(); savedAudio.currentTime = 2.5; });
    await page.getByRole('button', { name: 'Комментарий', exact: true }).click();
    await page.getByRole('button', { name: 'К реплике', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Отмена', exact: true }).click();
    await page.locator('[data-playback-next]').click();
    assert.equal(await page.evaluate(() => savedAudio.currentTime), 6);
    await page.locator('[data-lane-segment]').first().click();
    assert.equal(await page.evaluate(() => savedAudio.currentTime), 2);
    await page.locator('[data-timeline-track]').first().press('Home');
    assert.equal(await page.evaluate(() => savedAudio.currentTime), 0);
    await page.locator('[data-playback-avatar="s1"]').click();
    assert.equal(await page.evaluate(() => savedAudio.currentTime >= 6 && !savedAudio.paused), true);
    await page.locator('[data-playback-listen-toggle]').click();
    await page.locator('[data-listen-speaker="s0"]').check();
    assert.equal(await page.locator('[data-speaker-key="s1"][data-speaker-lane]').evaluate(node => node.classList.contains('is-unselected')), true);
    nextHtml = html(true).replace('data-media-revision-id="media"', 'data-media-revision-id="other-media"');
    await page.evaluate(async () => {
      document.querySelector('main').dataset.processingTranscriptContentReady = 'false';
      await window.refreshTest();
    });
    assert.deepEqual(await page.evaluate(() => [savedAudio.isConnected, savedAudio.paused, savedAudio === document.querySelector('audio')]), [false, true, false], 'a different media revision must retire the old player');
    // Equal text must not hide a source/context change from the second refresh path.
    await page.evaluate(() => {
      window.savedAudio = document.querySelector('audio');
      window.savedPlayback = document.querySelector('[data-playback-shell]');
      window.stableHtml = document.querySelector('main').outerHTML + savedPlayback.outerHTML;
    });
    nextHtml = (await page.evaluate(() => stableHtml)).replace('data-processing-result-id="result"', 'data-processing-result-id="next-result"');
    await page.evaluate(() => window.recoveryTest());
    assert.equal(await page.locator('[data-playback-shell]').getAttribute('data-processing-result-id'), 'next-result', 'recovery must refresh context even when visible text is unchanged');
    assert.equal(await page.evaluate(() => savedAudio === document.querySelector('audio')), true);
    nextHtml = (await page.evaluate(() => stableHtml)).replace('data-media-revision-id="other-media"', 'data-media-revision-id="third-media"');
    await page.evaluate(() => window.recoveryTest());
    assert.deepEqual(await page.evaluate(() => [savedAudio.isConnected, savedAudio.paused, savedAudio === document.querySelector('audio')]), [false, true, false], 'recovery must retire a changed media revision even when visible text is unchanged');
    assert.deepEqual(errors, []);
    console.log('PASS: first transcript refresh keeps audio and comment draft, updates speakers, source context and working controls');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
