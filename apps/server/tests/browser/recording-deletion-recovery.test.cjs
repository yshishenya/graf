// Run with NODE_PATH pointing at the existing Playwright installation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { chromium } = require('playwright');

const cabinetScript = fs.readFileSync(path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js'));
const offlineMeetingId = '00000000-0000-0000-0000-000000000262';
const rowHTML = id => `<li data-meeting-row data-meeting-id="${id}">
  <span class="meeting-title">Synthetic</span><input type="checkbox" data-meeting-select>
  <form action="/meetings/${id}/deletion-requests" data-row-delete-form>
    <input name="confirmation_boundary" value="Delete this meeting everywhere GRAF controls." type="hidden">
    <button type="button" data-row-delete>Удалить</button>
  </form></li>`;
const fixture = rows => `<!doctype html><meta charset="utf-8"><meta name="csrf-token" content="synthetic-csrf">
  <h1 data-list-title tabindex="-1">Встречи</h1><button data-manual-upload-open>Загрузить запись</button>
  <div id="meeting-list-region"><section data-meeting-list><ol class="meeting-list">${rows}</ol></section></div>
  <div data-selection-toolbar><span data-selection-count></span></div>
  <div id="delete-feedback-region"></div><div data-meeting-result-announcer></div>
  <dialog data-delete-dialog><h2 data-delete-title></h2><p data-delete-count></p><p data-delete-error hidden></p>
    <button data-delete-cancel>Отмена</button><button data-delete-confirm>Удалить</button>
  </dialog><div data-upload-activity-announcer></div>
  <dialog data-manual-upload-dialog data-upload-available="true"><form data-manual-upload-form>
    <input type="file" data-manual-upload-file><input data-manual-upload-title>
    <input data-manual-upload-duration><input data-manual-upload-local-id>
    <input type="checkbox" data-manual-upload-archive checked><button data-manual-upload-submit>Загрузить</button>
  </form></dialog><script src="/cabinet.js"></script>`;

const wav = Buffer.alloc(44 + 16000 * 2);
wav.write('RIFF'); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8);
wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
wav.writeUInt32LE(16000, 24); wav.writeUInt32LE(32000, 28);
wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34);
wav.write('data', 36); wav.writeUInt32LE(wav.length - 44, 40);

async function main() {
  const deleted = new Set();
  const deletions = [];
  const uploads = [];
  const lifecycleQueries = [];
  const errors = [];
  // Real loopback HTTP lets Chromium's offline mode fail fetch at the network boundary.
  const server = http.createServer(async (request, response) => {
    try {
      const pathname = new URL(request.url, 'http://localhost').pathname;
      const body = Buffer.concat(await Array.fromAsync(request));
      if (pathname === '/cabinet.js') {
        response.setHeader('Content-Type', 'application/javascript');
        response.end(cabinetScript);
      } else if (pathname.endsWith('/deletion-requests') && request.method === 'POST') {
        const id = pathname.split('/')[2];
        deletions.push(id); deleted.add(id);
        response.writeHead(202, { 'Content-Type': 'text/html' }); response.end();
      } else if (pathname === '/api/v1/desktop/recordings/lifecycle') {
        const ids = JSON.parse(body).meeting_ids;
        lifecycleQueries.push(ids);
        response.setHeader('Content-Type', 'application/json');
        response.end(JSON.stringify(ids.map(id => ({ target_type: 'meeting', target_id: id,
          state: deleted.has(id) ? 'deletion_accepted' : 'allowed' }))));
      } else if (pathname === '/api/v1/cabinet/media-uploads') {
        const boundary = request.headers['content-type'].split('boundary=')[1];
        const parts = body.toString('latin1').split(`--${boundary}`);
        const value = name => {
          const part = parts.find(part => part.includes(`name="${name}"`));
          assert.ok(part, `multipart ${name}`);
          return part.slice(part.indexOf('\r\n\r\n') + 4, -2);
        };
        const origin = value('local_recording_id');
        assert.ok(origin);
        assert.equal(uploads.some(upload => upload.origin === origin), false, 'explicit reimport must not reuse a previous origin');
        const meetingId = `00000000-0000-0000-0000-${String(263 + uploads.length).padStart(12, '0')}`;
        uploads.push({ origin, meetingId, fileHash: createHash('sha256').update(Buffer.from(value('file'), 'latin1')).digest('hex') });
        response.setHeader('Content-Type', 'application/json');
        response.end(JSON.stringify({ meeting: { meeting_id: meetingId }, workflow_started: true }));
      } else {
        response.setHeader('Content-Type', 'text/html');
        response.end(fixture(pathname === '/offline' && !deleted.has(offlineMeetingId) ? rowHTML(offlineMeetingId) : ''));
      }
    } catch (error) {
      errors.push(error.message);
      response.writeHead(500); response.end();
    }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  context.on('page', page => page.on('pageerror', error => errors.push(error.message)));
  try {
    const offline = await context.newPage();
    await offline.goto(`${origin}/offline`);
    await offline.locator('[data-row-delete]').click();
    await context.setOffline(true);
    await offline.locator('[data-delete-confirm]').click();
    await offline.locator('[data-delete-error]').waitFor({ state: 'visible' });
    assert.equal(await offline.locator('[data-meeting-row]').count(), 1);
    assert.equal(await offline.locator('[data-delete-dialog]').evaluate(dialog => dialog.open), true);
    assert.match(await offline.locator('[data-delete-error]').textContent(), /Не удалось удалить 1 запись\. Попробуйте ещё раз\./);
    assert.equal(await offline.locator('[data-delete-confirm]').textContent(), 'Повторить');
    assert.equal(await offline.locator('[data-delete-confirm]').isEnabled(), true);
    assert.doesNotMatch(await offline.locator('#delete-feedback-region').textContent(), /сохран[её]н|Ожидают подтверждения|удалена из списка/);
    assert.deepEqual(deletions, [], 'offline request never reached the server');
    await context.setOffline(false);
    assert.equal(await offline.locator('[data-meeting-row]').count(), 1, 'reconnect alone does not imply deletion');
    await offline.locator('[data-delete-confirm]').click();
    await offline.waitForFunction(() => !document.querySelector('[data-meeting-row]'));
    assert.deepEqual(deletions, [offlineMeetingId]);
    assert.equal(await offline.locator('[data-delete-dialog]').evaluate(dialog => dialog.open), false);
    assert.equal(await offline.locator('[data-meeting-result-announcer]').textContent(), 'Запись удалена из списка.');
    await offline.close();
    console.log('recording deletion recovery: S09 offline error preserves row; explicit reconnect retry passed');

    const reimport = await context.newPage();
    await reimport.goto(`${origin}/reimport`);
    async function uploadSameFile() {
      await reimport.locator('[data-manual-upload-open]').click();
      await reimport.locator('[data-manual-upload-file]').setInputFiles({ name: 'Exported-F262.wav', mimeType: 'audio/wav', buffer: wav });
      await reimport.waitForFunction(() => document.querySelector('[data-manual-upload-duration]').value === '1');
      await reimport.locator('[data-manual-upload-submit]').click();
      await reimport.locator('[data-upload-activity-detail]').waitFor({ state: 'visible' });
    }
    await uploadSameFile();
    assert.equal(uploads.length, 1);
    const first = uploads[0];
    assert.equal(await reimport.locator('[data-upload-activity-detail]').getAttribute('href'), `/meetings/${first.meetingId}`);
    // Simulate the server-rendered row arriving after the upload, preserving the same page.
    await reimport.locator('ol.meeting-list').evaluate((list, html) => list.insertAdjacentHTML('beforeend', html), rowHTML(first.meetingId));
    await reimport.locator('[data-row-delete]').click();
    await reimport.locator('[data-delete-confirm]').click();
    await reimport.waitForFunction(() => !document.querySelector('[data-upload-activity-row]'));
    assert.equal(deleted.has(first.meetingId), true);
    await uploadSameFile();
    assert.equal(uploads.length, 2);
    const second = uploads[1];
    assert.notEqual(second.origin, first.origin);
    assert.notEqual(second.meetingId, first.meetingId);
    assert.equal(second.fileHash, first.fileHash, 'same bytes are a separate explicit import');
    assert.equal(second.fileHash, createHash('sha256').update(wav).digest('hex'));
    assert.equal(await reimport.locator('[data-upload-activity-row]').count(), 1);
    assert.equal(await reimport.locator('[data-upload-activity-detail]').getAttribute('href'), `/meetings/${second.meetingId}`);
    const polled = reimport.waitForResponse(response => response.url().endsWith('/api/v1/desktop/recordings/lifecycle'));
    await reimport.evaluate(() => window.dispatchEvent(new Event('focus')));
    await polled;
    assert.deepEqual(lifecycleQueries.at(-1), [second.meetingId]);
    assert.equal(await reimport.locator('[data-upload-activity-detail]').isVisible(), true);
    assert.equal(await reimport.locator(`[href="/meetings/${first.meetingId}"]`).count(), 0);
    assert.deepEqual(deletions, [offlineMeetingId, first.meetingId]);
    assert.deepEqual(errors, []);
    console.log('recording deletion recovery: S48 same file reimport has a new origin and survives old deletion passed');
  } finally {
    await context.close();
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
