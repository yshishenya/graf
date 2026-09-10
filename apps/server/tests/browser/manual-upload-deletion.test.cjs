// Run with NODE_PATH pointing at the existing Playwright installation.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('playwright');

const meetingId = '00000000-0000-0000-0000-000000000262';
const cabinetScript = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js');
const fixture = `<meta name="csrf-token" content="synthetic-csrf">
  <h1 data-list-title tabindex="-1">Встречи</h1>
  <button data-manual-upload-open>Загрузить запись</button>
  <div id="meeting-list-region"><section data-meeting-list><ol class="meeting-list">
    <li data-meeting-row data-meeting-id="${meetingId}">
      <span class="meeting-title">Synthetic</span><input type="checkbox" data-meeting-select>
      <form action="/meetings/${meetingId}/delete" data-row-delete-form>
        <button type="button" data-row-delete>Удалить</button>
      </form>
    </li>
  </ol></section></div>
  <div data-selection-toolbar><span data-selection-count></span></div>
  <div id="delete-feedback-region"></div><div data-meeting-result-announcer></div>
  <dialog data-delete-dialog><h2 data-delete-title></h2><p data-delete-count></p>
    <p data-delete-error hidden></p><button data-delete-cancel>Отмена</button>
    <button data-delete-confirm>Удалить</button>
  </dialog>
  <div data-upload-activity-announcer></div>
  <dialog data-manual-upload-dialog data-upload-available="true">
    <form data-manual-upload-form><input type="file" data-manual-upload-file>
      <input data-manual-upload-title><input data-manual-upload-duration><input data-manual-upload-local-id>
      <input type="checkbox" data-manual-upload-archive checked>
      <button data-manual-upload-submit>Загрузить</button>
    </form>
  </dialog>`;

// One second of synthetic silence exercises the real file-duration reader.
const wav = Buffer.alloc(44 + 16000 * 2);
wav.write('RIFF'); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8);
wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
wav.writeUInt32LE(16000, 24); wav.writeUInt32LE(32000, 28);
wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34);
wav.write('data', 36); wav.writeUInt32LE(wav.length - 44, 40);

async function scenario(browser, action) {
  const page = await browser.newPage();
  const errors = [];
  const requests = { deletes: 0, lifecycle: [] };
  let lifecycleState = 'allowed';
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.route('https://synthetic.invalid/**', async route => {
      const request = route.request();
      const pathname = new URL(request.url()).pathname;
      if (pathname === '/api/v1/desktop/recordings/lifecycle') {
        const ids = request.postDataJSON().meeting_ids;
        requests.lifecycle.push(ids);
        return route.fulfill({ json: ids.map(id => ({ target_type: 'meeting', target_id: id, state: lifecycleState })) });
      }
      if (pathname === `/meetings/${meetingId}/delete`) {
        assert.equal(request.method(), 'POST');
        requests.deletes += 1;
        return route.fulfill({ status: 200, contentType: 'text/html', body: '' });
      }
      return route.fulfill({ contentType: 'text/html', body: '<html><body></body></html>' });
    });
    await page.goto('https://synthetic.invalid/meetings');
    await page.setContent(fixture);
    await page.evaluate(id => {
      // Hold only the upload transport; production DOM and event handlers remain intact.
      window.XMLHttpRequest = class {
        upload = {}; status = 200;
        responseText = JSON.stringify({ meeting: { meeting_id: id }, workflow_started: true });
        open() {} setRequestHeader() {} getResponseHeader() { return ''; }
        send() { window.pendingSyntheticUpload = this; }
        abort() { this.onabort?.(); }
      };
    }, meetingId);
    await page.addScriptTag({ path: cabinetScript });
    await page.locator('[data-manual-upload-open]').click();
    await page.locator('[data-manual-upload-file]').setInputFiles({ name: 'F262.wav', mimeType: 'audio/wav', buffer: wav });
    await page.waitForFunction(() => document.querySelector('[data-manual-upload-duration]').value === '1');
    await page.locator('[data-manual-upload-submit]').click();
    assert.equal(await page.locator('[data-upload-activity-row]').count(), 1);
    assert.equal(await page.locator('[data-manual-upload-dialog]').evaluate(dialog => dialog.open), false);

    if (action === 'late-upload-after-web-delete') {
      await page.locator('[data-row-delete]').click();
      await page.locator('[data-delete-confirm]').click();
      await page.waitForFunction(() => document.querySelectorAll('[data-meeting-row]').length === 0);
      assert.equal(requests.deletes, 1);
      // Server committed the upload before delete, but its success arrived afterwards.
      await page.evaluate(() => window.pendingSyntheticUpload.onload());
    } else {
      await page.evaluate(() => window.pendingSyntheticUpload.onload());
      assert.equal(await page.locator('[data-upload-activity-detail]').getAttribute('href'), `/meetings/${meetingId}`);
      assert.equal(await page.locator('[data-upload-activity-detail]').isVisible(), true);
      // A filter/pagination change can leave the upload card as the only alias on screen.
      await page.locator('[data-meeting-row]').evaluate(row => row.remove());
      lifecycleState = action;
      const previousPolls = requests.lifecycle.length;
      await page.evaluate(() => window.dispatchEvent(new Event('focus')));
      await page.waitForFunction(() => document.querySelectorAll('[data-upload-activity-row]').length === 0);
      assert.ok(requests.lifecycle.length > previousPolls);
      assert.deepEqual(requests.lifecycle.at(-1), [meetingId]);
      assert.equal(requests.deletes, 0, 'remote access revocation does not issue a delete command');
    }
    assert.equal(await page.locator('[data-meeting-row]').count(), 0);
    assert.equal(await page.locator('[data-upload-activity-row]').count(), 0);
    assert.equal(await page.locator('[data-upload-activity-detail]').count(), 0);
    assert.equal(await page.locator('[data-upload-activity-announcer]').textContent(), '');
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const action of ['late-upload-after-web-delete', 'deletion_accepted', 'unavailable']) {
      await scenario(browser, action);
      console.log(`manual upload deletion: ${action} passed`);
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
