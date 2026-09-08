const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, webkit } = require(require.resolve('playwright', { paths: [process.env.GRAF_NODE_MODULES || process.cwd()] }));
const asset = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/playback-comments.js');
const stylesheet = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/playback-comments.css');

(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const failures = []; page.on('pageerror', error => failures.push(error.message));
    let root = null, failSave = true, saves = [], replyPage = false, failEdit = false, failDelete = false, staleMedia = false, viewer = false, sourceFilterSeen = false;
    const rights = { can_edit: true, can_delete: true, can_resolve: true, can_react: true, can_reply: true };
    const makeComment = (body, id = 'root', parent = null) => ({ id, parent_id: parent, author_user_id: 'author', author_label: 'Тестовый автор', media_revision_id: 'media', start_ms: 12500, body, mentions: [], created_at: '2026-09-08T00:00:00Z', edited_at: null, version: 1, resolved: false, reactions: [], ...rights, replies: [], next_reply_cursor: null });
    await page.route('https://graf.test/**', async route => {
      const req = route.request(), url = new URL(req.url());
      if (!url.pathname.startsWith('/api/')) return route.fulfill({ contentType: 'text/html', body: `<meta charset="utf-8"><meta name="csrf-token" content="synthetic-csrf"><style>:root{--surface:#22252a;--text:#f0f1f4;--line:#555;--muted:#bbb;--accent:#ab99ff}body{margin:0}section[data-playback-shell]{position:fixed;bottom:0;left:12px;width:366px;height:80px}</style><button id="outside">Вне формы</button><article data-transcript-turn data-source-segments="overlapping-earlier" data-start-seconds="0" data-end-seconds="10"></article><article class="is-current" data-transcript-turn data-source-segments="segment" data-start-seconds="0" data-end-seconds="5" tabindex="-1"></article><section class="playback-bar detail-playback" data-playback-shell data-meeting-id="meeting" data-media-revision-id="media" data-processing-result-id="result" data-workspace-id="workspace"><audio data-playback-player></audio><button data-playback-comment>Комментарий</button></section>` });
      assert.equal(url.searchParams.get('workspace_id'), 'workspace');
      if (req.method() !== 'GET') assert.equal(req.headers()['x-csrf-token'], 'synthetic-csrf');
      const send = (json, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(json) });
      if (url.pathname.endsWith('/comment-mention-candidates')) return send({ items: [{ user_id: 'person', display_label: 'Тест' }] });
      if (req.method() === 'GET' && url.pathname.endsWith('/comments')) { sourceFilterSeen ||= url.searchParams.getAll('source_segment_ids').includes('segment'); return send({ items: root ? [root] : [], next_cursor: null, media_revision_id: staleMedia ? 'new-media' : 'media', source_counts: root ? [{source_segment_id: 'segment', count: 53}] : [], total_count: root ? 53 : 0, capabilities: { can_comment: !viewer, can_edit: true, emoji_options: ['👍', '😊'] } }); }
      if (req.method() === 'GET' && url.pathname.endsWith('/replies')) { replyPage = true; return send({ items: [makeComment('Поздний ответ', 'reply2', 'root')], next_cursor: null }); }
      if (req.method() === 'GET') return send(root);
      const body = req.postDataJSON();
      if (req.method() === 'POST') {
        saves.push(body);
        if (failSave) { failSave = false; return send({}, 500); }
        if (url.pathname.endsWith('/replies')) { const reply = makeComment(body.body, 'reply', 'root'); root.replies.push(reply); return send(reply); }
        else { root = makeComment(body.body); root.mentions = body.mentions; }
        return send(root);
      }
      if (req.method() === 'PATCH') { if (failEdit) { failEdit = false; root.version = 2; return send({}, 409); } assert.equal(body.expected_version, root.version); root.body = body.body; root.edited_at = '2026-09-08T00:01:00Z'; root.version++; return send(root); }
      if (url.pathname.endsWith('/reaction')) { root.reactions = body.selected ? [{ emoji: body.emoji, count: 1, selected: true }] : []; return send(root); }
      if (url.pathname.endsWith('/resolution')) { root.resolved = body.resolved; root.version++; return send(root); }
      if (req.method() === 'DELETE') { if (failDelete) { failDelete = false; root.version++; return send({}, 409); } root = null; return send({ deleted_id: 'root', root_id: 'root' }); }
      throw new Error(`Unexpected route ${req.method()} ${url.pathname}`);
    });
    await page.goto('https://graf.test/meeting');
    await page.addStyleTag({ path: path.join(path.dirname(stylesheet), 'cabinet.css') }); await page.addStyleTag({ path: stylesheet }); await page.addScriptTag({ path: asset });
    await page.evaluate(() => { const shell = document.querySelector('[data-playback-shell]'); window.GRAFPlaybackComments.init(shell); window.GRAFPlaybackComments.init(shell); });
    assert.equal(await page.locator('.playback-comments').count(), 1, 'idempotent init');
    await page.getByRole('button', { name: 'Комментарий', exact: true }).click();
    const input = page.getByRole('textbox', { name: 'Текст комментария' });
    assert.equal(await input.evaluate(node => node === document.activeElement), true);
    assert.equal(await page.getByRole('button', { name: 'Отправить', exact: true }).isDisabled(), true);
    await page.getByRole('button', { name: 'К реплике', exact: true }).click();
    await input.fill('  😊 @Те');
    await page.getByRole('button', { name: 'Тест', exact: true }).click();
    await input.press('End'); await input.pressSequentially('<script>bad()</script>');
    await page.getByRole('button', { name: 'Отправить', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Не удалось' }).waitFor();
    assert.match(await input.inputValue(), /<script>bad/);
    await page.getByRole('button', { name: 'Отправить', exact: true }).click();
    await page.getByText('Комментарий сохранён.', { exact: true }).waitFor();
    assert.equal(saves[0].request_id, saves[1].request_id, 'retry reuses request identity');
    assert.equal(saves[1].source_segment_id, 'segment'); assert.equal(saves[1].end_ms, 5000);
    assert.equal(saves[1].mentions[0].start, 4, 'Unicode code points include unchanged leading whitespace');
    assert.equal(saves[1].mentions[0].end, 9);
    assert.equal(await page.locator('.playback-comment-body script').count(), 0, 'body always plain text');
    assert.equal(await page.getByRole('button', { name: 'Обсуждения реплики: 53', exact: true }).count(), 1, 'server aggregate, not the single loaded root');
    await page.getByRole('button', { name: 'Закрыть', exact: true }).click();
    await page.getByRole('button', { name: 'Обсуждения реплики: 53', exact: true }).click();
    await page.getByRole('button', { name: 'Эта реплика ×', exact: true }).waitFor(); assert.equal(sourceFilterSeen, true);
    await page.getByRole('button', { name: 'Эта реплика ×', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('.playback-comments-source').disabled);
    await page.evaluate(() => {
      const turn = document.querySelector('[data-source-segments="segment"]');
      const replacement = turn.cloneNode(true); replacement.querySelector('[data-comment-count]')?.remove(); turn.replaceWith(replacement);
      window.GRAFPlaybackComments.init(document.querySelector('[data-playback-shell]'));
    });
    assert.equal(await page.getByRole('button', { name: 'Обсуждения реплики: 53', exact: true }).count(), 1, 'badge restored when main transcript is replaced');
    assert.equal(await page.locator('.playback-comments').evaluate(node => node.getBoundingClientRect().right <= innerWidth), true);
    await page.getByRole('button', { name: '＋ Реакция' }).click();
    await page.getByRole('button', { name: '👍', exact: true }).click();
    await page.getByRole('button', { name: 'Реакция 👍: 1' }).waitFor();
    await page.getByRole('button', { name: 'Реакция 👍: 1' }).click();
    await page.waitForFunction(() => !document.querySelector('[aria-pressed="true"]'));
    failEdit = true;
    await page.getByRole('button', { name: 'Изменить', exact: true }).click(); await input.fill('Исправленный текст');
    await page.getByRole('button', { name: 'Сохранить', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Обсуждение изменилось' }).waitFor();
    assert.equal(await input.inputValue(), 'Исправленный текст');
    await page.getByRole('button', { name: 'Обновить обсуждение', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Версия обновлена' }).waitFor();
    await page.getByRole('button', { name: 'Сохранить', exact: true }).click();
    await page.getByText('Исправленный текст', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Ответить', exact: true }).first().click();
    await input.fill('Новый ответ');
    await page.getByRole('button', { name: 'Отправить', exact: true }).click();
    await page.getByText('Новый ответ', { exact: true }).waitFor();
    root.next_reply_cursor = 'cursor1';
    await page.getByRole('combobox', { name: 'Состояние обсуждения' }).selectOption('all');
    await page.getByRole('button', { name: 'Ещё ответы' }).click();
    await page.getByText('Поздний ответ', { exact: true }).waitFor(); assert.equal(replyPage, true);
    await page.getByRole('button', { name: 'Завершить', exact: true }).click();
    await page.getByRole('button', { name: 'Возобновить', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Удалить', exact: true }).first().click();
    await page.getByRole('dialog').getByRole('button', { name: 'Отмена', exact: true }).click(); assert.ok(root);
    failDelete = true;
    await page.getByRole('button', { name: 'Удалить', exact: true }).first().click();
    await page.getByRole('dialog').getByRole('button', { name: 'Удалить', exact: true }).click();
    await page.getByRole('button', { name: 'Обновить список', exact: true }).waitFor();
    assert.equal(await page.getByRole('dialog').getByRole('button', { name: 'Удалить', exact: true }).isDisabled(), true);
    await page.getByRole('button', { name: 'Обновить список', exact: true }).click(); assert.ok(root);
    await page.getByRole('button', { name: 'Удалить', exact: true }).first().click();
    await page.getByRole('dialog').getByRole('button', { name: 'Удалить', exact: true }).click();
    await page.getByText('Нет обсуждений с выбранными фильтрами.', { exact: true }).waitFor(); assert.equal(root, null); assert.equal(await page.locator('[data-comment-count]').count(), 0, 'deleted root clears aggregate badge');
    await page.getByRole('button', { name: 'Добавить комментарий', exact: true }).click();
    await page.getByRole('button', { name: 'Добавить emoji', exact: true }).click();
    await page.keyboard.press('Escape'); assert.equal(await input.isVisible(), true);
    await page.keyboard.press('Escape'); assert.equal(await input.count(), 0);
    viewer = true;
    await page.getByRole('button', { name: 'Комментарий', exact: true }).click();
    assert.equal(await input.count(), 0, 'viewer cannot open a writing form');
    staleMedia = true;
    await page.getByRole('button', { name: 'Комментарий', exact: true }).click();
    await page.getByText('Версия записи изменилась. Обновите страницу, чтобы открыть обсуждения.', { exact: true }).waitFor();
    assert.equal(await input.count(), 0);
    staleMedia = false; viewer = false; root = makeComment('Открыто по прямой ссылке');
    await page.goto('https://graf.test/meeting?comment_id=root');
    await page.addStyleTag({ path: stylesheet }); await page.addScriptTag({ path: asset });
    await page.evaluate(() => window.GRAFPlaybackComments.init(document.querySelector('[data-playback-shell]')));
    await page.getByText('Открыто по прямой ссылке', { exact: true }).waitFor();
    await page.addStyleTag({ path: path.join(path.dirname(stylesheet), 'cabinet.css') });
    await page.evaluate(() => {
      document.documentElement.style.zoom = '2';
      document.querySelector('[data-playback-shell]').style.width = 'calc(100% - 24px)';
    });
    for (const selector of ['.playback-comments', '.playback-comment-editor']) {
      if (selector.endsWith('editor')) await page.getByRole('button', { name: 'Добавить комментарий', exact: true }).click();
      const box = await page.locator(selector).boundingBox();
      assert.ok(box && box.x >= 0 && box.x + box.width <= 390, JSON.stringify({ selector, box }));
    }
    root = makeComment('Большое обсуждение');
    root.replies = Array.from({ length: 50 }, (_, i) => makeComment(`Ответ ${i}`, `reply-${i}`, 'root'));
    await page.goto('https://graf.test/meeting?comment_id=reply-49');
    await page.addStyleTag({ path: stylesheet }); await page.addScriptTag({ path: asset });
    await page.evaluate(() => window.GRAFPlaybackComments.init(document.querySelector('[data-playback-shell]')));
    await page.getByText('Ответ 49', { exact: true }).waitFor();
    assert.equal(await page.getByText('Ответ 49', { exact: true }).evaluate(node => {
      const box = node.getBoundingClientRect();
      return box.top >= 0 && box.bottom <= innerHeight && node.closest('article') === document.activeElement;
    }), true, 'direct reply is visible and receives keyboard focus');
    root.next_reply_cursor = 'cursor1';
    await page.getByRole('combobox', { name: 'Состояние обсуждения' }).selectOption('all');
    await page.getByRole('button', { name: 'Ещё ответы' }).click();
    await page.getByText('Поздний ответ', { exact: true }).waitFor();
    const ids = await page.locator('.playback-comment-replies article').evaluateAll(nodes => nodes.map(node => node.dataset.commentCardId));
    assert.deepEqual(ids, [...ids].sort((a, b) => a.localeCompare(b)), 'loaded siblings restore chronological order around the linked reply');
    assert.deepEqual(failures, []);
    console.log('PASS: comments UI; plain text, Unicode mentions, retry identity, stale edit recovery, reactions, reply pagination, resolve, delete confirmation, narrow viewport, focus and idempotent init');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
