// Run with NODE_PATH pointing at the existing Playwright installation.
// Uses the production 30-second timer; no fake clock or replacement lifecycle handler.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const script = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js');
const id = n => `00000000-0000-0000-0000-${String(n).padStart(12, '0')}`;
const row = n => `<li data-meeting-row data-meeting-id="${id(n)}" data-sort-title="Synthetic ${n}"><input type="checkbox" data-meeting-select><button data-meeting-open>Synthetic ${n}</button><span class="row-meta"></span></li>`;
const fixture = content => `<meta name="csrf-token" content="synthetic-csrf">
<h1 data-list-title tabindex="-1">Встречи</h1><form class="cabinet-list-controls"><input id="meeting-search"></form>
<div data-selection-toolbar hidden><span data-selection-count></span><button data-selection-delete>Удалить выбранные</button></div>
<div id="delete-feedback-region"></div><div data-meeting-result-announcer></div>
<div id="meeting-list-region"><div data-meeting-result-count>Найдено: ${(content.match(/data-meeting-row/g) || []).length}</div><section data-meeting-list><ol class="meeting-list">${content}</ol></section></div>
<dialog data-delete-dialog data-title-one="Удаление" data-title-many="Удаление"><h2 data-delete-title></h2><p data-delete-count></p><p data-delete-error hidden></p><button data-delete-cancel>Отмена</button><button data-delete-confirm>Удалить</button></dialog>`;

async function openPage(browser, content, state = {}) {
  const page = await browser.newPage();
  state.calls = [];
  state.errors = [];
  page.on('pageerror', error => state.errors.push(error.message));
  await page.route('https://synthetic.invalid/**', async route => {
    if (!route.request().url().endsWith('/desktop/recordings/lifecycle')) {
      await route.fulfill({contentType: 'text/html', body: '<html></html>'}); return;
    }
    const ids = route.request().postDataJSON().meeting_ids;
    state.calls.push({at: Date.now(), ids, offline: !!state.offline});
    if (state.offline) { await route.abort('internetdisconnected'); return; }
    if (ids.some(meetingID => state.failedIDs?.has(meetingID))) {
      await route.fulfill({status: 503, contentType: 'application/json', body: '{"code":"temporarily_unavailable"}'}); return;
    }
    await route.fulfill({contentType: 'application/json', body: JSON.stringify(ids.map(meetingID => ({
      target_type: 'meeting', target_id: meetingID,
      state: state.deleted?.has(meetingID) ? 'deletion_accepted' : 'allowed',
    })))});
  });
  await page.goto('https://synthetic.invalid/meetings');
  await page.setContent(fixture(content));
  await page.evaluate(() => document.querySelector('form.cabinet-list-controls').addEventListener('submit', event => {
    event.preventDefault();
    window.listRefreshCount = (window.listRefreshCount || 0) + 1;
    document.querySelector('[data-meeting-result-count]').textContent = `Найдено: ${document.querySelectorAll('[data-meeting-row]').length}`;
  }));
  await page.addScriptTag({path: path.join(path.dirname(script), 'user-time.js')});
  return page;
}

async function mixedFrozenSelection(browser, hideSelected = false) {
  const state = {};
  const page = await openPage(browser, row(1), state);
  try {
    await page.addScriptTag({path: script});
    const local = {id: 'local-a', title: 'Synthetic local A', durationSeconds: 1, canOpen: true, canDelete: true};
    await page.evaluate(local => {
      window.GRAFRecordingDeletionBridgeVersion = 1;
      window.webkit = {messageHandlers: {grafLocalRecording: {postMessage(message) {
        window.deletionSent = message;
        window.GRAFLocalRecordings.deletionCompleted(message.requestId, {saved: true, accepted: 0, pending: 2, rejected: 0});
      }}}};
      window.GRAFLocalRecordings.update([local]);
    }, local);
    await page.locator('[data-graf-local-recording-id="local-a"] [data-meeting-select]').check();
    await page.locator(`[data-meeting-id="${id(1)}"] [data-meeting-select]`).check();
    await page.locator('[data-selection-delete]').click();
    // A new local item and an HTMX swap arrive while the confirmation is still open.
    await page.evaluate(local => {
      window.GRAFLocalRecordings.update([local, {...local, id: 'local-new', title: 'New unselected item'}]);
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {detail: {target: document.querySelector('#meeting-list-region')}}));
    }, local);
    if (hideSelected) {
      await page.evaluate(local => {
        document.querySelector('#meeting-search').value = 'Synthetic 1';
        window.GRAFLocalRecordings.update([local]);
        document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {detail: {target: document.querySelector('#meeting-list-region')}}));
      }, local);
      assert.equal(await page.locator('[data-graf-local-recording-row]').count(), 0, 'filter hides the selected local row behind the open confirmation');
    }
    await page.locator('[data-delete-confirm]').click();
    const sent = await page.evaluate(() => window.deletionSent);
    assert.deepEqual(sent.localIds, ['local-a'], 'a late local row must never join the confirmed selection');
    assert.deepEqual(sent.meetingIds, [id(1)]);
    assert.deepEqual(state.errors, []);
  } finally { await page.close(); }
}

async function threeTypesOneConfirmation(browser) {
  const state = {};
  const page = await openPage(browser, row(1) + row(2), state);
  try {
    await page.addScriptTag({path: script});
    await page.evaluate(meetingID => {
      window.GRAFRecordingDeletionBridgeVersion = 1;
      window.deletionMessages = [];
      window.webkit = {messageHandlers: {grafLocalRecording: {postMessage(message) {
        window.deletionMessages.push(message);
        window.GRAFLocalRecordings.deletionCompleted(message.requestId, {saved: true, accepted: 1, pending: 2, rejected: 0});
      }}}};
      window.GRAFLocalRecordings.update([
        {id: 'local-only', title: 'Synthetic local', durationSeconds: 1, canOpen: true, canDelete: true, deletionIsLocalOnly: true},
        {id: 'uploaded-alias', meetingId: meetingID, title: 'Synthetic uploaded alias', durationSeconds: 1, canDelete: true, uploadComplete: true},
      ]);
    }, id(1));
    assert.equal(await page.locator('[data-meeting-row]').count(), 3, 'local/server alias counts once');
    for (const checkbox of await page.locator('[data-meeting-select]').all()) await checkbox.check();
    assert.match(await page.locator('[data-selection-count]').textContent(), /3/);
    await page.locator('[data-selection-delete]').click();
    assert.equal(await page.locator('dialog[open]').count(), 1);
    assert.match(await page.locator('[data-delete-count]').textContent(), /Вы удаляете 3 записи/);
    assert.match(await page.locator('[data-delete-count]').textContent(), /Только на этом Mac: 1/);
    assert.match(await page.locator('[data-delete-count]').textContent(), /На сервере или ожидают его подтверждения: 2/);
    await page.locator('[data-delete-confirm]').click();
    const messages = await page.evaluate(() => window.deletionMessages);
    assert.equal(messages.length, 1);
    assert.deepEqual(messages[0].localIds, ['local-only']);
    assert.deepEqual(messages[0].meetingIds.sort(), [id(1), id(2)]);
    for (const provenLocal of [true, undefined]) {
      for (const checkbox of await page.locator('[data-meeting-select]').all()) await checkbox.uncheck();
      await page.evaluate(provenLocal => window.GRAFLocalRecordings.update([
        {id: 'local-only', title: 'Synthetic local', durationSeconds: 1, canOpen: true, canDelete: true, deletionIsLocalOnly: provenLocal},
      ]), provenLocal);
      await page.locator('[data-graf-local-recording-row] [data-meeting-select]').check();
      await page.locator('[data-selection-delete]').click();
      const copy = await page.locator('[data-delete-count]').textContent();
      if (provenLocal) assert.match(copy, /Только на этом Mac: 1.*ещё не отправлялись на сервер/);
      else {
        assert.doesNotMatch(copy, /Только на этом Mac|ещё не отправлялись/);
        assert.match(copy, /На сервере или ожидают его подтверждения: 1/);
      }
      await page.locator('[data-delete-cancel]').click();
    }
    assert.deepEqual(state.errors, []);
  } finally { await page.close(); }
}

async function offlineNativePendingCopy(browser) {
  const state = {};
  const page = await openPage(browser, row(1), state);
  try {
    await page.addScriptTag({path: script});
    await page.context().setOffline(true);
    await page.evaluate(meetingID => {
      window.GRAFRecordingDeletionBridgeVersion = 1;
      window.deletionMessages = [];
      window.webkit = {messageHandlers: {grafLocalRecording: {postMessage(message) {
        window.deletionMessages.push(message);
        window.pendingOperation = {id: 'offline-operation', target: {meeting: {_0: meetingID}}, phase: 'queued', waitReason: 'connection'};
        window.GRAFLocalRecordings.update([], [window.pendingOperation]);
        window.GRAFLocalRecordings.deletionCompleted(message.requestId, {saved: true, accepted: 0, pending: 1, rejected: 0});
      }}}};
    }, id(1));
    await page.locator('[data-meeting-select]').check();
    await page.locator('[data-selection-delete]').click();
    await page.locator('[data-delete-confirm]').click();
    assert.equal(await page.locator('[data-delete-dialog]').evaluate(node => node.open), false);
    assert.match(await page.locator('#delete-feedback-region').textContent(), /Удалено из списка: 0.*Ожидают подтверждения: 1/);
    assert.match(await page.locator('[data-native-deletion-status]').textContent(), /Ожидаем подключения для подтверждения удаления/);
    assert.doesNotMatch(await page.locator('[data-native-deletion-status]').textContent(), /Запись удалена|Данные этой записи очищены/);
    assert.equal(await page.locator('[data-meeting-select]').isDisabled(), true);
    assert.equal(await page.locator('[data-meeting-open]').isDisabled(), true);
    assert.equal(await page.locator('[data-meeting-row]').count(), 1, 'unconfirmed delete keeps honest pending row');
    await page.evaluate(() => window.GRAFLocalRecordings.update([], [window.pendingOperation]));
    assert.equal(await page.locator('[data-meeting-open]').isDisabled(), true);
    assert.equal(await page.evaluate(() => window.deletionMessages.length), 1);
    assert.deepEqual(state.errors, []);
  } finally { await page.close(); }
}

async function lastRowAndStaleProjection(browser) {
  const state = {};
  const page = await openPage(browser, row(2), state);
  try {
    await page.addScriptTag({path: script});
    await page.evaluate(() => {
      window.GRAFRecordingDeletionBridgeVersion = 1;
      window.webkit = {messageHandlers: {grafLocalRecording: {postMessage(message) {
        const operations = message.meetingIds.map(meetingID => ({id: meetingID, target: {meeting: {_0: meetingID}}, phase: 'accepted'}));
        window.GRAFLocalRecordings.update([], operations);
        window.GRAFLocalRecordings.deletionCompleted(message.requestId, {saved: true, accepted: 1, pending: 0, rejected: 0});
      }}}};
    });
    await page.locator('[data-meeting-select]').check();
    await page.locator('[data-selection-delete]').click();
    await page.locator('[data-delete-confirm]').click();
    assert.equal(await page.locator('[data-meeting-row]').count(), 0);
    assert.equal(await page.locator('[data-meeting-result-count]').textContent(), 'Найдено: 0');
    assert.equal(await page.locator('[data-selection-toolbar]').isHidden(), true);
    assert.match(await page.locator('[data-deletion-empty]').textContent(), /Записей пока нет/);
    assert.equal(await page.locator('[data-list-title]').evaluate(node => document.activeElement === node), true);
    await page.evaluate(html => {
      document.querySelector('ol.meeting-list').innerHTML = html;
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {detail: {target: document.querySelector('#meeting-list-region')}}));
    }, row(2));
    assert.equal(await page.locator('[data-meeting-row]').count(), 0, 'late server HTML cannot republish the accepted meeting');
    assert.deepEqual(state.errors, []);
  } finally { await page.close(); }
}

async function boundedAliasesCannotStarveRows(browser) {
  const state = {deleted: new Set(Array.from({length: 200}, (_, n) => id(n + 1)))};
  const page = await openPage(browser, Array.from({length: 100}, (_, n) => row(n + 101)).join(''), state);
  try {
    await page.evaluate(ids => document.body.insertAdjacentHTML('beforeend', ids.map(meetingID =>
      `<article data-upload-activity-meeting-id="${meetingID}" data-meeting-id="${meetingID}">Synthetic completed upload</article>`).join('')), Array.from({length: 100}, (_, n) => id(n + 1)));
    await page.addScriptTag({path: script});
    await page.waitForFunction(() => document.querySelectorAll('[data-meeting-row], [data-upload-activity-meeting-id]').length === 0, null, {timeout: 5000});
    assert.ok(state.calls.every(call => call.ids.length <= 100), 'each lifecycle request is bounded');
    assert.equal(new Set(state.calls.flatMap(call => call.ids)).size, 200, 'all visible aliases receive lifecycle checks');
    assert.deepEqual(state.errors, []);
  } finally { await page.close(); }
}

async function successfulBatchSurvivesLaterFailure(browser) {
  const state = {deleted: new Set([id(1)]), failedIDs: new Set([id(101)])};
  const page = await openPage(browser, row(1) + row(101), state);
  try {
    await page.evaluate(ids => document.body.insertAdjacentHTML('beforeend', ids.map(meetingID =>
      `<article data-upload-activity-meeting-id="${meetingID}" data-meeting-id="${meetingID}">Synthetic completed upload</article>`).join('')), Array.from({length: 100}, (_, n) => id(n + 1)));
    await page.addScriptTag({path: script});
    await page.waitForFunction(() => document.querySelectorAll('[data-meeting-row]').length === 1);
    assert.equal(await page.locator('[data-meeting-result-count]').textContent(), 'Найдено: 1', 'a later batch failure cannot leave the count of already deleted rows');
    assert.equal(await page.locator(`[data-meeting-id="${id(101)}"]`).count(), 1, 'the failed batch is not deletion evidence');
    assert.deepEqual(state.errors, []);
  } finally { await page.close(); }
}

async function realTimerAndReconnect(browser) {
  const state = {deleted: new Set()};
  const page = await openPage(browser, row(301), state);
  try {
    const initialResponse = page.waitForResponse(response => response.url().endsWith('/desktop/recordings/lifecycle'), {timeout: 5000});
    await page.addScriptTag({path: script});
    await initialResponse;
    const remoteAt = Date.now();
    state.deleted.add(id(301));
    await page.waitForFunction(() => document.querySelectorAll('[data-meeting-row]').length === 0, null, {timeout: 60000});
    const remoteMs = Date.now() - remoteAt;
    assert.ok(remoteMs < 60000, `remote deletion took ${remoteMs}ms`);
    // Restore another visible synthetic target during a real failed request.
    await page.evaluate(html => { document.querySelector('ol.meeting-list').innerHTML = html; }, row(302));
    state.offline = true;
    const failedRequest = page.waitForEvent('requestfailed', {predicate: request => request.url().endsWith('/desktop/recordings/lifecycle'), timeout: 5000});
    await page.evaluate(() => window.dispatchEvent(new Event('online')));
    await failedRequest;
    assert.equal(await page.locator('[data-meeting-row]').count(), 1, 'network failure is not deletion evidence');
    // Wait until the failed fetch has released the in-flight guard, without replacing it.
    await page.waitForTimeout(100);
    state.offline = false;
    state.deleted.add(id(302));
    const onlineAt = Date.now();
    await page.evaluate(() => window.dispatchEvent(new Event('online')));
    await page.waitForFunction(() => document.querySelectorAll('[data-meeting-row]').length === 0, null, {timeout: 5000});
    const reconnectMs = Date.now() - onlineAt;
    assert.ok(reconnectMs < 5000, `reconnect deletion took ${reconnectMs}ms`);
    assert.deepEqual(state.errors, []);
    console.log(JSON.stringify({check: 'SC-003 web timer and online', samples: 1, remoteMs, reconnectMs, timerMs: 30000}));
  } finally { await page.close(); }
}

(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const checks = {threeTypes: threeTypesOneConfirmation, offlineCopy: offlineNativePendingCopy, selection: mixedFrozenSelection, filter: browser => mixedFrozenSelection(browser, true), lastRow: lastRowAndStaleProjection,
      aliases: boundedAliasesCannotStarveRows, partialBatch: successfulBatchSurvivesLaterFailure, timing: realTimerAndReconnect};
    const selected = process.argv[2] ? [process.argv[2]] : Object.keys(checks);
    for (const name of selected) { assert.ok(checks[name], `unknown check: ${name}`); await checks[name](browser); }
    console.log(`recording deletion acceptance PASS: ${selected.join(', ')}`);
  } finally { await browser.close(); }
})();
