"""Production renderer + browser JavaScript + HTTP routes + isolated PostgreSQL.

Set GRAF_NODE_MODULES to the existing Playwright installation to run this gate.
The loopback bridge adds the ordinary synthetic test principal, never real auth.
"""
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet_access import add_retained_playback_m4a, auth_headers_for
from tests.integration.test_meeting_comments import grant, setup_comments
from tests.integration.test_recording_share_public_link import _seed_external_full_summary
from twobrain_rec_server.db.models import MeetingShareGrant


@pytest.mark.browser
def test_browser_comments_use_real_http_and_database(client):
    seeds, comments_url, comment_body = setup_comments(client)
    add_retained_playback_m4a(client, seeds.ready_id)
    client.portal.call(_seed_external_full_summary, client, seeds.ready_id)
    legacy_grant = grant(client, seeds.ready_id)
    grant_id = UUID(legacy_grant["grant"]["grant_id"])

    async def persisted_permissions():
        async with client.app_state["sessionmaker"]() as db:
            return list(await db.execute(
                select(MeetingShareGrant.id, MeetingShareGrant.content_scope,
                       MeetingShareGrant.can_comment, MeetingShareGrant.can_edit)
                .where(MeetingShareGrant.meeting_id == seeds.ready_id)
            ))

    # The summary-only dialog no longer edits legacy recording roles. Their
    # real HTTP/DB contract remains supported independently of that dialog.
    for can_comment, can_edit in ((True, False), (True, True), (False, False)):
        response = client.patch(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{grant_id}/permissions",
            headers=auth_headers(),
            json={"can_comment": can_comment, "can_edit": can_edit},
        )
        assert response.status_code == 200, response.text
        assert response.json()["can_comment"] is can_comment
        assert response.json()["can_edit"] is can_edit
        assert client.portal.call(persisted_permissions) == [
            (grant_id, "full_meeting", can_comment, can_edit)
        ]
        recipient = client.get(comments_url, headers=auth_headers_for())
        assert recipient.status_code == 200, recipient.text
        assert recipient.json()["capabilities"]["can_comment"] is can_comment
        assert recipient.json()["capabilities"]["can_edit"] is can_edit
    assert client.post(
        comments_url, headers=auth_headers_for(), json=comment_body
    ).status_code == 403

    class Bridge(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def forward(self):
            headers = {**auth_headers(), "Content-Type": self.headers.get("Content-Type", "application/json")}
            if self.headers.get("X-CSRF-Token"):
                headers["X-CSRF-Token"] = self.headers["X-CSRF-Token"]
            response = client.request(self.command, self.path, headers=headers,
                content=self.rfile.read(int(self.headers.get("Content-Length", "0"))), follow_redirects=False)
            self.send_response(response.status_code)
            for name in ("content-type", "location", "cache-control"):
                if name in response.headers:
                    self.send_header(name, response.headers[name])
            self.send_header("Content-Length", str(len(response.content)))
            self.end_headers()
            self.wfile.write(response.content)

        do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = forward

    server = ThreadingHTTPServer(("127.0.0.1", 0), Bridge)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    script = r"""
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, webkit } = require(path.join(process.env.GRAF_NODE_MODULES, 'playwright'));
(async () => {
  const type = process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium;
  const browser = await type.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    page.setDefaultTimeout(10000);
    const failures = []; page.on('pageerror', error => failures.push(error.message));
    const commentResponses = []; page.on('response', async res => { if (res.url().includes('/comments')) commentResponses.push([res.request().method(), new URL(res.url()).pathname, res.status(), ...(res.status() >= 400 ? [await res.json(), res.request().postDataJSON()] : [])]); });
    await page.goto(process.env.GRAF_SYNTHETIC_URL);
    await page.locator('[data-detail-tab="recording"]').click();
    await page.locator('[data-share-dialog-open]').click();
    const share = page.getByRole('dialog', { name: 'Поделиться итогами', exact: true });
    await share.waitFor();
    assert.equal(await share.locator('[data-share-existing-role], [data-share-comment-role]').count(), 0);
    assert.equal(await share.locator('audio, [data-playback-comment], [data-detail-tab="recording"]').count(), 0);
    await share.getByRole('tab', { name: 'По почте', exact: true }).click();
    await share.getByText('Получатели увидят только выбранные итоги. Чтобы открыть их, нужно войти с указанной почтой.', { exact: true }).waitFor();
    const previewResponse = page.waitForResponse(res => res.request().method() === 'GET' && res.url().includes('/summary-sharing/preview'));
    await share.locator('[data-summary-share-preview]').click();
    const preview = await previewResponse;
    assert.equal(preview.status(), 200);
    const projection = (await preview.json()).projection;
    assert.ok(projection.protocol || projection.summary_sections.length, 'real preview contains summary');
    for (const key of ['transcript', 'transcript_segments', 'audio_url', 'comments']) {
      assert.equal(Object.hasOwn(projection, key), false, `summary preview excludes ${key}`);
    }
    await share.locator('[data-summary-share-preview-content]').getByText('Сохранённый итог.', { exact: true }).waitFor();
    assert.equal(await share.locator('[data-summary-share-preview-content] audio, [data-summary-share-preview-content] textarea').count(), 0);
    await share.locator('[data-summary-share-close]').click();
    await page.locator('[data-playback-comment]').click();
    await page.getByRole('button', { name: 'К реплике', exact: true }).click();
    await page.getByRole('button', { name: 'К моменту', exact: true }).click();
    const input = page.getByRole('textbox', { name: 'Текст комментария' });
    await input.fill('  Синтетический комментарий 🧪  ');
    await page.getByRole('button', { name: 'Отправить', exact: true }).click();
    await page.getByText('Комментарий сохранен.', { exact: true }).waitFor().catch(async error => { console.error(commentResponses, failures, await page.locator('.playback-comments-status, .playback-comment-editor-error').allTextContents()); throw error; });
    assert.equal(await page.locator('.playback-comment-body').first().textContent(), '  Синтетический комментарий 🧪  ');
    await page.getByRole('button', { name: 'Обсуждения реплики: 1', exact: true }).waitFor();
    const id = await page.locator('[data-comment-id]').first().getAttribute('data-comment-id');
    const link = new URL(page.url()); link.searchParams.set('comment_id', id);
    await page.goto(link.href);
    await page.locator('.playback-comment-body').filter({ hasText: 'Синтетический комментарий' }).waitFor();
    await page.getByRole('button', { name: 'Ответить', exact: true }).first().click();
    await input.fill('Синтетический ответ');
    await page.getByRole('button', { name: 'Отправить', exact: true }).click();
    await page.getByText('Синтетический ответ', { exact: true }).waitFor();
    await page.getByRole('button', { name: '＋ Реакция' }).first().click();
    await page.getByRole('button', { name: '👍', exact: true }).click();
    await page.getByRole('button', { name: 'Реакция 👍: 1' }).waitFor();
    await page.getByRole('button', { name: 'Изменить', exact: true }).first().click();
    await input.fill('Синтетический исправленный комментарий');
    await page.getByRole('button', { name: 'Сохранить', exact: true }).click();
    await page.getByText('Синтетический исправленный комментарий', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Завершить', exact: true }).click();
    await page.getByRole('combobox', { name: 'Состояние обсуждения' }).selectOption('resolved');
    await page.getByRole('button', { name: 'Возобновить', exact: true }).click();
    await page.getByRole('combobox', { name: 'Состояние обсуждения' }).selectOption('open');
    await page.getByText('Синтетический исправленный комментарий', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Удалить', exact: true }).first().click();
    await page.getByRole('dialog', { name: 'Удалить комментарий', exact: true }).getByRole('button', { name: 'Удалить', exact: true }).click();
    await page.waitForFunction(() => !document.querySelector('[data-comment-id]')).catch(async error => {
      console.error(await page.locator('.playback-comment-delete, .playback-comments-status').allTextContents()); throw error;
    });
    const retainedAudio = await page.locator('audio').elementHandle();
    await page.locator('[data-speaker-manager-toggle]').click();
    await page.locator('[data-speaker-name-open]').first().click();
    const renameForm = page.locator('[data-speaker-name-form]:visible').first();
    const speakerKey = await renameForm.getAttribute('data-speaker-key');
    await renameForm.locator('input[name="display_name"]').fill('Тестовое имя');
    await renameForm.getByRole('button', { name: 'Сохранить', exact: true }).click();
    await page.waitForFunction(key => document.querySelector(`[data-speaker-lane="${key}"] [data-lane-segment]`).getAttribute('aria-label').startsWith('Тестовое имя '), speakerKey);
    assert.equal(await retainedAudio.evaluate(audio => audio.isConnected), true, 'rename retains the actual audio');
    await page.goto(process.env.GRAF_SYNTHETIC_URL.replace('/meetings/', '/desktop/meetings/'));
    for (const width of [720, 390]) {
      await page.setViewportSize({ width, height: 800 });
      await page.locator('[data-playback-comment]').click();
      await page.getByRole('button', { name: 'Все комментарии', exact: true }).click();
      const comments = await page.locator('.playback-comments').boundingBox();
      const sidebar = await page.locator('.sidebar').boundingBox();
      assert.ok(comments.x >= sidebar.x + sidebar.width, 'embedded navigation must not cover comments');
      assert.ok(comments.x + comments.width <= width, 'embedded comments stay inside viewport');
      await page.getByRole('button', { name: 'Закрыть', exact: true }).click();
    }
    assert.deepEqual(failures, []);
    console.log('PASS: browser -> production HTTP -> PostgreSQL create/reload/reply/react/edit/resolve/reopen/delete');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    try:
        result = subprocess.run(["node", "-e", script], cwd=Path(__file__).resolve().parents[2],
            env={**os.environ, "GRAF_SYNTHETIC_URL": f"http://127.0.0.1:{server.server_port}/meetings/{seeds.ready_id}"},
            capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        assert client.get(comments_url + "?status=all", headers=auth_headers()).json()["items"] == []
        assert client.portal.call(persisted_permissions) == [
            (grant_id, "full_meeting", False, False)
        ], "opening/previewing summary sharing must preserve the existing recording ACL"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
