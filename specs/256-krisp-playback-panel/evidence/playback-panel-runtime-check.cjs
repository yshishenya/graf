// Run from the repository root; GRAF_NODE_MODULES selects the installed Playwright.
// All content is synthetic. Audio is generated in memory and is never saved.
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium, webkit } = require(process.env.GRAF_NODE_MODULES
  ? path.join(process.env.GRAF_NODE_MODULES, 'playwright') : 'playwright');
const root = process.cwd();
const serverDir = path.join(root, 'apps/server');
const assets = path.join(serverDir, 'src/twobrain_rec_server/cabinet/static/cabinet');
const python = String.raw`
import json
from uuid import UUID
from tests.unit.test_cabinet_web_shell import _review
from twobrain_rec_server.api.schemas import PlaybackReviewState, TranscriptReviewState, TranscriptSpeakerTurnView, SpeakerReviewState, SpeakerLane, SpeakerLaneSegment
from twobrain_rec_server.cabinet.rendering import render_meeting_detail_page
from twobrain_rec_server.cabinet.view_models import AccountProfileView

review = _review()
review.meeting.title = "Синтетическая проверка панели"
review.meeting.duration_seconds = 40
review.provenance.media_revision_id = UUID('00000000-0000-4000-8000-000000000002')
review.processing = review.processing.model_copy(update=dict(state="ready", content_available=True, transcript_available=True, diarization_available=True))
rows = [('alpha', 2, 6), ('beta', 5, 9), ('alpha', 12, 16), ('gamma', 20, 22), ('beta', 25, 29), ('alpha', 34, 38)]
names = dict(alpha='Спикер Альфа', beta='Спикер Бета', gamma='Спикер Гамма')
turns = [TranscriptSpeakerTurnView(turn_id=f'turn-{i}', sequence=i, start_seconds=start, end_seconds=end,
    timestamp_label=f'00:{start:02}', speaker_label=names[key], source_role='canonical_mixed',
    text=f'Синтетическая реплика {i}', speaker_key=key, source_segment_ids=[f'segment-{i}'],
    seekable=True, seek_seconds=start) for i, (key, start, end) in enumerate(rows)]
review.transcript = TranscriptReviewState(available=True, search_enabled=True, language='ru', speaker_turns=turns)
review.speakers = SpeakerReviewState(available=True, assignment_state='available', turns=turns, can_rename=True,
    speakers=[SpeakerLane(speaker_key=key, label=names[key], talk_time_percent=percent,
        segments=[SpeakerLaneSegment(start_seconds=start, end_seconds=end) for who, start, end in rows if who == key])
        for key, percent in [('gamma', 9), ('beta', 36), ('alpha', 55)]])
review.playback = PlaybackReviewState(available=True, duration_seconds=40,
    playback_path='/synthetic.wav', source_mode='stored_review_m4a', included_sources=['canonical_mixed'])
print(json.dumps({surface: render_meeting_detail_page(review, embedded=(surface == 'embedded'),
    csrf_token='synthetic-csrf', profile=AccountProfileView(display_name='Тестовый пользователь', primary_email='synthetic@example.invalid'))
    for surface in ('web', 'embedded')}, ensure_ascii=False))
`;

function render() {
  const result = spawnSync('uv', ['run', '--extra', 'dev', 'python', '-c', python], {
    cwd: serverDir, env: { ...process.env, PYTHONPATH: 'src:.' }, encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

function syntheticWav() {
  const rate = 8000, samples = 40 * rate;
  const wav = Buffer.alloc(44 + samples * 2);
  wav.write('RIFF'); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8);
  wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(rate, 24); wav.writeUInt32LE(rate * 2, 28);
  wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34); wav.write('data', 36);
  wav.writeUInt32LE(samples * 2, 40);
  for (let i = 0; i < samples; i++) wav.writeInt16LE(Math.round(100 * Math.sin(i * 2 * Math.PI * 220 / rate)), 44 + i * 2);
  return wav;
}

function serve(pages) {
  const wav = syntheticWav();
  return http.createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    if (url.pathname.endsWith('/processing')) {
      res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify({ state: 'processed', transcript_ready: true, diarization_ready: true,
        summary_state: 'not_requested', transcript_available: true, diarization_available: true,
        attempt_ordinal: 1, attempt_in_flight: false, retry_class: 'none' })); return;
    }
    if (url.pathname === '/synthetic.wav') {
      const range = /^bytes=(\d+)-(\d*)$/.exec(req.headers.range || '');
      const start = range ? Number(range[1]) : 0;
      const end = range && range[2] ? Math.min(Number(range[2]), wav.length - 1) : wav.length - 1;
      if (start > end || start >= wav.length) { res.writeHead(416, { 'Content-Range': `bytes */${wav.length}` }); res.end(); return; }
      res.writeHead(range ? 206 : 200, { 'Content-Type': 'audio/wav', 'Accept-Ranges': 'bytes',
        'Content-Length': end - start + 1, ...(range ? { 'Content-Range': `bytes ${start}-${end}/${wav.length}` } : {}) });
      res.end(wav.subarray(start, end + 1)); return;
    }
    if (pages[url.pathname.slice(1)]) {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); res.end(pages[url.pathname.slice(1)]); return;
    }
    if (url.pathname.includes('/static/')) {
      const file = path.join(assets, path.basename(url.pathname));
      if (fs.existsSync(file) && fs.statSync(file).isFile()) {
        res.writeHead(200, { 'Content-Type': file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'application/octet-stream' });
        res.end(fs.readFileSync(file)); return;
      }
    }
    res.writeHead(404, { 'Content-Type': 'application/json' }); res.end('{"detail":"synthetic route unavailable"}');
  });
}

async function settle(page) {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function position(page, seconds) {
  await page.evaluate(seconds => { const audio = document.querySelector('audio'); audio.pause(); audio.currentTime = seconds; }, seconds);
  await page.waitForFunction(seconds => Math.abs(document.querySelector('audio').currentTime - seconds) < 0.1, seconds);
}

async function geometry(page, width, theme, zoom, surface) {
  await page.setViewportSize({ width, height: 900 });
  await page.evaluate(({ theme, zoom }) => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.zoom = String(zoom);
  }, { theme, zoom });
  await settle(page);
  const metrics = await page.evaluate(() => {
    const bar = document.querySelector('[data-playback-shell]');
    const rect = bar.getBoundingClientRect();
    const main = document.querySelector('.detail-page-main').getBoundingClientRect();
    const buttons = [...bar.querySelectorAll('.playback-toolbar button')].filter(button => {
      const box = button.getBoundingClientRect(); return box.width && box.height && getComputedStyle(button).visibility !== 'hidden';
    });
    const visibleRect = (button) => {
      const box = button.getBoundingClientRect();
      const rect = { left: box.left, top: box.top, right: box.right, bottom: box.bottom };
      for (let node = button.parentElement; node; node = node.parentElement) {
        const style = getComputedStyle(node), clip = node.getBoundingClientRect();
        if (/(hidden|auto|scroll|clip)/.test(style.overflowX)) { rect.left = Math.max(rect.left, clip.left); rect.right = Math.min(rect.right, clip.right); }
        if (/(hidden|auto|scroll|clip)/.test(style.overflowY)) { rect.top = Math.max(rect.top, clip.top); rect.bottom = Math.min(rect.bottom, clip.bottom); }
      }
      return rect;
    };
    const overlap = [];
    for (let i = 0; i < buttons.length; i++) for (let j = i + 1; j < buttons.length; j++) {
      const a = visibleRect(buttons[i]), b = visibleRect(buttons[j]);
      if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 2 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 2)
        overlap.push([buttons[i].getAttribute('aria-label'), buttons[j].getAttribute('aria-label')]);
    }
    const scale = Number(document.documentElement.style.zoom) || 1;
    const referenceDimensions = [['[data-playback-toggle]', 'width', 32], ['[data-playback-toggle]', 'height', 32],
      ['[data-playback-toggle] .ui-icon', 'width', 20], ['.timeline-lane', 'height', 33], ['.timeline-track', 'height', 5]]
      .map(([selector, dimension, expected]) => ({ selector, dimension, expected, actual: bar.querySelector(selector).getBoundingClientRect()[dimension] / scale }));
    return { audioCount: document.querySelectorAll('audio').length, overlap, referenceDimensions,
      overflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
      mainOverlap: Math.max(0, main.bottom - rect.top),
      controlsOutside: buttons.filter(button => { const box = button.closest('[data-playback-avatars]') ? visibleRect(button) : button.getBoundingClientRect(); return box.left < rect.left - 2 || box.right > rect.right + 2; }).map(button => button.getAttribute('aria-label') || button.textContent.trim()) };
  });
  assert.equal(metrics.audioCount, 1);
  assert.ok(metrics.referenceDimensions.every(item => Math.abs(item.actual - item.expected) <= 2), JSON.stringify(metrics.referenceDimensions));
  assert.deepEqual(metrics.overlap, [], JSON.stringify({ width, theme, zoom, surface, metrics }));
  assert.ok(metrics.overflow <= 2 && metrics.mainOverlap <= 2 && !metrics.controlsOutside.length,
    JSON.stringify({ width, theme, zoom, surface, metrics }));
  return { width, theme, zoom, surface, ...metrics };
}

async function playback(page) {
  await page.waitForFunction(() => document.querySelector('audio').readyState >= 1);
  assert.equal(await page.locator('[data-transcript-turn]').count(), 6);
  await page.locator('[data-playback-toggle]').click();
  await page.waitForFunction(() => !document.querySelector('audio').paused && document.querySelector('audio').currentTime > 0.1);
  await page.locator('[data-playback-toggle]').click();
  assert.equal(await page.locator('audio').evaluate(audio => audio.paused), true);
  for (const [start, selector, expected] of [[2, '[data-playback-skip="15"]', 17], [17, '[data-playback-skip="-15"]', 2], [35, '[data-playback-skip="15"]', 40]]) {
    await position(page, start); await page.locator(selector).click();
    await page.waitForFunction(expected => { const audio = document.querySelector('audio'); return Math.abs(audio.currentTime - expected) < 0.1 || expected === audio.duration && audio.currentTime === 0 && audio.paused; }, expected);
  }
  await position(page, 5);
  await page.locator('[data-playback-speed-toggle]').click();
  assert.equal(await page.locator('[data-playback-speed-option]').count(), 5);
  await page.keyboard.press('Escape');
  for (const rate of [0.75, 1, 1.25, 1.5, 2]) {
    await page.locator('[data-playback-speed-toggle]').click();
    await page.locator(`[data-playback-speed-option="${rate}"]`).click();
    assert.equal(await page.locator('audio').evaluate(audio => audio.playbackRate), rate);
    assert.ok(Math.abs(await page.locator('audio').evaluate(audio => audio.currentTime) - 5) < 0.1);
    assert.equal(await page.locator('[data-playback-speed-menu]').isVisible(), false);
  }
  await page.locator('audio').evaluate(audio => { audio.playbackRate = 1; });
  await page.locator('[data-playback-next]').click();
  assert.equal(await page.locator('audio').evaluate(audio => audio.currentTime), 12);
  await page.locator('body').click({ position: { x: 3, y: 3 } });
  await page.keyboard.press('Shift+ArrowLeft');
  assert.equal(await page.locator('audio').evaluate(audio => audio.currentTime), 5);
  await page.keyboard.press('ArrowRight');
  assert.equal(await page.locator('audio').evaluate(audio => audio.currentTime), 20);
  await page.keyboard.press('ArrowLeft');
  assert.equal(await page.locator('audio').evaluate(audio => audio.currentTime), 5);
  await page.locator('[data-playback-progress]').focus();
  await page.keyboard.press('ArrowRight');
  assert.ok(await page.locator('audio').evaluate(audio => audio.currentTime) < 6, 'native range must not also apply global +15');
  await page.locator('[data-speaker-key="beta"] [data-lane-segment]').first().click();
  assert.equal(await page.locator('audio').evaluate(audio => audio.currentTime), 5);
  assert.equal(await page.locator('[data-source-segments="segment-1"]').first().getAttribute('class').then(value => value.includes('is-source-highlight')), true);
  assert.equal(await page.locator('[data-transcript-turn].is-current').getAttribute('data-source-segments'), 'segment-1', 'explicit selected turn wins during overlapping speech');
  await position(page, 39);
  await page.locator('[data-playback-next]').click();
  assert.equal(await page.locator('audio').evaluate(audio => audio.currentTime), 39, 'next must not wrap');

  await position(page, 7);
  await page.locator('[data-playback-listen-toggle]').click();
  await page.locator('[data-listen-speaker="alpha"]').check();
  await page.waitForFunction(() => { const audio = document.querySelector('audio'); return !audio.paused && audio.currentTime >= 12 && audio.currentTime < 13; });
  assert.equal(await page.locator('[data-speaker-lane="beta"]').evaluate(lane => lane.classList.contains('is-unselected')), true);
  await position(page, 15.85);
  await page.keyboard.press('Escape');
  await page.locator('[data-playback-toggle]').click();
  await page.waitForFunction(() => document.querySelector('audio').currentTime >= 34);
  await position(page, 37.9);
  await page.locator('[data-playback-toggle]').click();
  await page.waitForFunction(() => { const audio = document.querySelector('audio'); return audio.paused && audio.currentTime >= 38; });
  assert.ok(await page.locator('audio').evaluate(audio => audio.currentTime) < 39, 'last selected interval stops playback');
  await position(page, 1);
  await page.locator('[data-playback-avatar="beta"]').click();
  await page.waitForFunction(() => { const audio = document.querySelector('audio'); return !audio.paused && audio.currentTime >= 5 && audio.currentTime < 6; });
  assert.equal(await page.locator('[data-listen-all]').isChecked(), true);
  await position(page, 7);
  await page.locator('[data-playback-listen-toggle]').click();
  await page.locator('[data-listen-speaker="alpha"]').check();
  await page.locator('[data-listen-speaker="beta"]').check();
  await position(page, 8.85);
  await page.keyboard.press('Escape');
  await page.locator('[data-playback-toggle]').click();
  await page.waitForFunction(() => document.querySelector('audio').currentTime >= 12);
  assert.ok(await page.locator('audio').evaluate(audio => audio.currentTime) < 13, 'overlapping selection skips once to the next union');
  await page.locator('[data-playback-listen-toggle]').click();
  await page.locator('[data-listen-all]').check();
  await page.keyboard.press('Escape');
  await position(page, 39.85);
  await page.locator('[data-playback-toggle]').click();
  await page.waitForFunction(() => { const audio = document.querySelector('audio'); return audio.paused && audio.currentTime === 0; });

  const handle = page.locator('[data-speaker-timeline-resize]');
  await handle.focus(); await page.keyboard.press('Home');
  await page.waitForFunction(() => document.querySelector('[data-speaker-timeline]').getBoundingClientRect().height <= 35);
  const beforeDrag = await page.locator('[data-speaker-timeline]').evaluate(node => node.getBoundingClientRect().height);
  const grip = await handle.boundingBox();
  const hit = await page.evaluate(({x,y,width,height}) => document.elementFromPoint(x + width / 2, y + height / 2)?.outerHTML.slice(0,220), grip);
  await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2);
  await page.mouse.down(); await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2 - 40); await page.mouse.up();
  await page.waitForFunction(before => document.querySelector('[data-speaker-timeline]').getBoundingClientRect().height > before + 20, beforeDrag);
  assert.ok(await page.locator('[data-speaker-timeline]').evaluate(node => node.getBoundingClientRect().height) > beforeDrag + 20, JSON.stringify({beforeDrag, grip, hit, after: await page.locator('[data-speaker-timeline]').evaluate(node => node.getBoundingClientRect().height)}));
  await handle.focus(); await page.keyboard.press('End');
  await page.waitForFunction(() => Math.abs(document.querySelector('[data-speaker-timeline]').getBoundingClientRect().height - Number(document.querySelector('[data-speaker-timeline-resize]').getAttribute('aria-valuenow'))) <= 2);
  const expanded = await page.locator('[data-speaker-timeline]').evaluate(node => node.getBoundingClientRect().height);
  await page.locator('[data-playback-timeline-toggle]').click();
  assert.equal(await page.locator('[data-playback-progress]').isVisible(), true);
  assert.equal(await page.locator('[data-playback-toggle]').isVisible(), true);
  await page.locator('[data-playback-timeline-toggle]').click();
  await settle(page);
  assert.ok(Math.abs(await page.locator('[data-speaker-timeline]').evaluate(node => node.getBoundingClientRect().height) - expanded) <= 2);

  // The retained player must navigate new transcript DOM after a main refresh.
  await position(page, 12);
  await page.evaluate(() => {
    window.syntheticPlayer = document.querySelector('audio');
    const turn = document.querySelector('[data-transcript-turn][data-start-seconds="20.0"]')
      || [...document.querySelectorAll('[data-transcript-turn]')].find(node => Number(node.dataset.startSeconds) === 20);
    const replacement = turn.cloneNode(true); replacement.dataset.startSeconds = '21'; turn.replaceWith(replacement);
  });
  await page.locator('[data-playback-next]').click();
  assert.equal(await page.locator('audio').evaluate(audio => audio.currentTime), 21);
  assert.equal(await page.evaluate(() => window.syntheticPlayer === document.querySelector('audio')), true);
  // Explicitly injected failure is supplemental; all success paths above used native play.
  await page.locator('audio').evaluate(audio => { audio.pause(); audio.play = () => Promise.reject(new Error('synthetic rejection')); });
  await page.locator('[data-playback-toggle]').click();
  await page.waitForFunction(() => !document.querySelector('[data-playback-error]').hidden);
  assert.equal(await page.locator('[data-playback-toggle]').getAttribute('aria-label'), 'Воспроизвести');
  await page.locator('audio').evaluate(audio => { delete audio.play; });
}

(async () => {
  const server = serve(render());
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const type = process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium;
  const chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  let browser;
  try {
    browser = await type.launch({ headless: true, ...(type === chromium && fs.existsSync(chrome) ? { executablePath: chrome } : {}) });
    const results = [];
    for (const surface of ['web', 'embedded']) {
      const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
      page.setDefaultTimeout(7000);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`http://127.0.0.1:${server.address().port}/${surface}`, { waitUntil: 'networkidle' });
      await playback(page);
      await page.keyboard.press('Escape');
      for (const theme of ['dark', 'light']) for (const zoom of [1, 2])
        for (const width of [390, 768, 787, 788, 991, 992, 1440]) results.push(await geometry(page, width, theme, zoom, surface));
      await geometry(page, 390, 'dark', 2, surface);
      for (const [trigger, popup] of [['[data-playback-speed-toggle]', '[data-playback-speed-menu]'], ['[data-playback-listen-toggle]', '[data-playback-listen-menu]'], ['[data-speaker-manager-toggle]', '#speaker-manager-popover']]) {
        await page.locator(trigger).click();
        const bounds = await page.locator(popup).boundingBox();
        assert.ok(bounds && bounds.x >= -2 && bounds.x + bounds.width <= 392, JSON.stringify({ popup, bounds }));
        await page.keyboard.press('Escape');
      }
      if (process.env.GRAF_PLAYBACK_SCREENSHOT_DIR) {
        fs.mkdirSync(process.env.GRAF_PLAYBACK_SCREENSHOT_DIR, { recursive: true });
        await geometry(page, 1440, 'dark', 1, surface);
        await page.screenshot({ path: path.join(process.env.GRAF_PLAYBACK_SCREENSHOT_DIR, `${type.name()}-${surface}-wide.png`) });
        await geometry(page, 390, 'light', 1, surface);
        await page.screenshot({ path: path.join(process.env.GRAF_PLAYBACK_SCREENSHOT_DIR, `${type.name()}-${surface}-narrow.png`) });
      }
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log(JSON.stringify({ browser: type.name(), realAudio: true, geometryCases: results.length, results }, null, 2));
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
