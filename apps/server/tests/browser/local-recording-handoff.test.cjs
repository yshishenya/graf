// Run with NODE_PATH pointing at the existing Playwright installation.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');

const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');

const serverRow = (id, title = id) => `
  <li data-meeting-row data-meeting-id="${id}" data-sort-title="${title}"
      data-sort-started="2026-09-15T10:00:00Z" data-sort-updated="2026-09-15T10:00:00Z" data-sort-duration="60">
    <input type="checkbox" data-meeting-select>
    <button data-meeting-open>${title}</button>
    <span class="row-meta">В обработке</span>
  </li>`;

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ timezoneId: 'UTC' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('https://synthetic.invalid/**', route => route.fulfill({
      contentType: 'text/html',
      body: '<html><body></body></html>',
    }));
    await page.goto('https://synthetic.invalid/meetings');
    await page.setContent(`<meta name="graf-timezone" content="UTC"><meta name="graf-time-reload" content="false">
      <h1 data-list-title tabindex="-1">Встречи</h1>
      <form class="cabinet-list-controls" method="get" action="/meetings">
        <input id="meeting-search" name="q" value="handoff">
        <select id="meeting-status" name="status"><option value="">Все</option><option value="processing">В обработке</option></select>
        <select id="meeting-access" name="access"><option value="">Любой</option><option value="owner">Мои</option></select>
        <select id="meeting-sort" name="sort"><option value="started_desc" selected>Новые</option><option value="title_asc">Название</option></select>
      </form>
      <div data-selection-toolbar hidden><span data-selection-count></span><button data-selection-delete>Удалить</button></div>
      <div id="delete-feedback-region"></div><div data-meeting-result-announcer></div>
      <div id="meeting-list-region"><div data-list-loading-state role="status" aria-live="polite" hidden>Загружаем встречи…</div><div data-list-current-content data-meeting-result-complete="true">
        <section data-meeting-list><ol class="meeting-list">${serverRow('server-old', 'Старая встреча')}</ol></section>
      </div></div>
      <dialog data-delete-dialog><h2 data-delete-title></h2><p data-delete-count></p><p data-delete-error hidden></p><button data-delete-cancel>Отмена</button><button data-delete-confirm>Удалить</button></dialog>`);
    await page.addScriptTag({ path: path.join(assets, 'user-time.js') });
    await page.addScriptTag({ path: path.join(assets, 'cabinet.js') });
    await page.evaluate(() => {
      window.handoffRefreshes = [];
      document.querySelector('.cabinet-list-controls').addEventListener('submit', event => {
        event.preventDefault();
        window.handoffRefreshes.push(new URLSearchParams(new FormData(event.currentTarget)).toString());
      });
    });

    const base = {
      id: 'local-handoff', title: 'Новая встреча', startedAt: '2026-09-15T10:00:00Z',
      updatedAt: '2026-09-15T10:00:00Z', durationSeconds: 60, status: 'Отправляется',
      canOpen: true, canSend: false, canDelete: true, uploadComplete: false,
    };
    const publish = rows => page.evaluate(rows => window.GRAFLocalRecordings.update(rows), rows);
    const refreshCount = () => page.evaluate(() => window.handoffRefreshes.length);
    const localRow = id => page.locator(`[data-graf-local-recording-row][data-graf-local-recording-id="${id}"]`);
    const handoffRow = id => page.locator(`[data-meeting-id="${id}"]`);

    await page.fill('#meeting-search', '');
    await page.selectOption('#meeting-status', '');
    await page.selectOption('#meeting-access', '');
    await publish([base]);
    await page.fill('#meeting-search', 'Новая');
    await publish([{ ...base, meetingId: 'server-handoff' }]);
    assert.equal(await refreshCount(), 1, 'one new server identity starts one refresh');
    assert.equal(await localRow('local-handoff').count(), 1, 'placeholder remains before response');
    assert.equal(
      await page.evaluate(() => window.handoffRefreshes[0]),
      'q=%D0%9D%D0%BE%D0%B2%D0%B0%D1%8F&status=&access=&sort=started_desc',
      'refresh submits the current list context',
    );
    await page.evaluate(row => {
      for (let index = 0; index < 100; index += 1) window.GRAFLocalRecordings.update([row]);
    }, { ...base, meetingId: 'server-handoff' });
    assert.equal(await refreshCount(), 1, 'repeated progress does not storm the list');
    await page.evaluate(() => { window.loadingRequest = {}; });
    await page.evaluate(() => {
      const region = document.querySelector('#meeting-list-region');
      const form = document.querySelector('.cabinet-list-controls');
      document.body.dispatchEvent(new CustomEvent('htmx:beforeRequest', {
        detail: { elt: form, target: region, xhr: window.loadingRequest },
      }));
    });
    assert.equal(await page.locator('[data-list-loading-state]').isHidden(), false, 'loading state is announced');
    assert.equal(await page.locator('[data-list-current-content]').isHidden(), false, 'pending alias stays visible while loading');
    assert.equal(await localRow('local-handoff').count(), 1, 'pending alias does not disappear while loading');
    await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterRequest', { detail: { xhr: window.loadingRequest } })));

    await page.evaluate(html => {
      document.querySelector('#meeting-list-region [data-meeting-list] ol').insertAdjacentHTML('afterbegin', html);
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
        detail: { target: document.querySelector('#meeting-list-region') },
      }));
    }, serverRow('server-handoff', 'Новая встреча'));
    assert.equal(await localRow('local-handoff').count(), 0, 'placeholder is removed after authoritative response');
    assert.equal(await handoffRow('server-handoff').count(), 1, 'server row is visible without reload');

    const focusedLocal = {
      ...base, id: 'local-focus', title: 'Фокусная встреча',
    };
    await page.fill('#meeting-search', '');
    await publish([{ ...base, meetingId: 'server-handoff' }, focusedLocal]);
    await localRow('local-focus').locator('[data-meeting-select]').check();
    await localRow('local-focus').locator('[data-meeting-select]').focus();
    await publish([{ ...base, meetingId: 'server-handoff' }, { ...focusedLocal, meetingId: 'server-focus' }]);
    assert.equal(await refreshCount(), 2, 'second handoff gets one refresh');
    assert.equal(await localRow('local-focus').count(), 1, 'focused placeholder remains during refresh');
    await page.evaluate(html => {
      document.querySelector('#meeting-list-region [data-meeting-list] ol').insertAdjacentHTML('afterbegin', html);
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
        detail: { target: document.querySelector('#meeting-list-region') },
      }));
    }, serverRow('server-focus', 'Фокусная встреча'));
    assert.equal(await handoffRow('server-focus').locator('[data-meeting-select]').isChecked(), true, 'selection follows the handoff');
    assert.equal(await handoffRow('server-focus').locator('[data-meeting-select]').evaluate(node => node === document.activeElement), true, 'focus follows the same control after handoff');

    const batchA = { ...base, id: 'local-batch-a', title: 'Пакетная встреча A' };
    const batchB = { ...base, id: 'local-batch-b', title: 'Пакетная встреча B' };
    await publish([{ ...base, meetingId: 'server-handoff' }, { ...focusedLocal, meetingId: 'server-focus' }, batchA, batchB]);
    await publish([
      { ...base, meetingId: 'server-handoff' }, { ...focusedLocal, meetingId: 'server-focus' },
      { ...batchA, meetingId: 'server-batch-a' }, { ...batchB, meetingId: 'server-batch-b' },
    ]);
    assert.equal(await refreshCount(), 3, 'several handoffs share one refresh');
    assert.equal(await localRow('local-batch-a').count(), 1, 'first batch placeholder remains');
    assert.equal(await localRow('local-batch-b').count(), 1, 'second batch placeholder remains');
    await page.evaluate(html => {
      document.querySelector('#meeting-list-region [data-meeting-list] ol').insertAdjacentHTML('afterbegin', html);
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
        detail: { target: document.querySelector('#meeting-list-region') },
      }));
    }, serverRow('server-batch-a', 'Пакетная встреча A') + serverRow('server-batch-b', 'Пакетная встреча B'));
    assert.equal(await localRow('local-batch-a').count(), 0, 'first batch placeholder is replaced');
    assert.equal(await localRow('local-batch-b').count(), 0, 'second batch placeholder is replaced');

    const filtered = { ...base, id: 'local-filtered', title: 'Не совпадёт' };
    await page.fill('#meeting-search', 'нет такого названия');
    await publish([{ ...base, meetingId: 'server-handoff' }, { ...focusedLocal, meetingId: 'server-focus' }, filtered]);
    await publish([{ ...base, meetingId: 'server-handoff' }, { ...focusedLocal, meetingId: 'server-focus' }, { ...filtered, meetingId: 'server-filtered' }]);
    assert.equal(await refreshCount(), 4, 'filtered handoff still performs one authoritative check');
    assert.equal(await localRow('local-filtered').count(), 0, 'non-matching local alias is not shown');
    await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
      detail: { target: document.querySelector('#meeting-list-region') },
    })));
    await publish([{ ...base, meetingId: 'server-handoff' }, { ...focusedLocal, meetingId: 'server-focus' }, { ...filtered, meetingId: 'server-filtered' }]);
    assert.equal(await refreshCount(), 4, 'missing filtered row is not retried on every progress update');
    assert.equal(await localRow('local-filtered').count(), 0, 'missing authoritative row cannot be resurrected');

    const failed = { ...base, id: 'local-failed', title: 'Ожидает проверки' };
    await page.fill('#meeting-search', '');
    await page.selectOption('#meeting-status', '');
    await page.selectOption('#meeting-access', '');
    await publish([{ ...base, meetingId: 'server-handoff' }, { ...focusedLocal, meetingId: 'server-focus' }, { ...failed }]);
    await publish([{ ...base, meetingId: 'server-handoff' }, { ...focusedLocal, meetingId: 'server-focus' }, { ...failed, meetingId: 'server-failed' }]);
    assert.equal(await refreshCount(), 5, 'failed handoff still has one automatic attempt');
    await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:responseError', {
      detail: {
        elt: document.querySelector('.cabinet-list-controls'),
        target: document.querySelector('#meeting-list-region'),
        xhr: { status: 503, responseText: '' },
      },
    })));
    assert.equal(await localRow('local-failed').count(), 1, 'refresh failure keeps local state visible');
    assert.equal(await page.locator('[data-list-retry]').count(), 1, 'existing retry path remains available');
    await page.locator('[data-list-retry]').click();
    assert.equal(await refreshCount(), 6, 'retry uses the existing list form');
    await page.evaluate(html => {
      document.querySelector('#meeting-list-region [data-meeting-list] ol').insertAdjacentHTML('afterbegin', html);
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
        detail: { target: document.querySelector('#meeting-list-region') },
      }));
    }, serverRow('server-failed', 'Ожидает проверки'));
    assert.equal(await handoffRow('server-failed').count(), 1, 'retry can complete the handoff');
    assert.equal(await localRow('local-failed').count(), 0, 'completed retry removes the placeholder');

    // Authorization recovery is a privacy boundary, not a deletion signal:
    // private server rows disappear, while the native projection remains in
    // memory and reconciles to the server row after the next authorized list.
    const auth = { ...base, id: 'local-auth', title: 'После входа', meetingId: 'server-auth' };
    await publish([auth]);
    assert.equal(await localRow('local-auth').count(), 1, 'auth handoff starts with a local alias');
    await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:responseError', {
      detail: {
        elt: document.querySelector('.cabinet-list-controls'),
        target: document.querySelector('#meeting-list-region'),
        xhr: { status: 401, responseText: '' },
      },
    })));
    assert.equal(await page.locator('[data-graf-local-recording-row]').count(), 0, '401 clears private meeting rows from the DOM');
    assert.equal(await page.locator('[data-list-sign-in]').count(), 1, '401 keeps the existing sign-in recovery');
    await publish([auth]);
    await page.evaluate(html => {
      document.querySelector('#meeting-list-region [data-list-current-content]')?.replaceChildren(
        document.createRange().createContextualFragment(`<section data-meeting-list><ol class="meeting-list">${html}</ol></section>`),
      );
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
        detail: { target: document.querySelector('#meeting-list-region') },
      }));
    }, serverRow('server-auth', 'После входа'));
    assert.equal(await handoffRow('server-auth').count(), 1, 'authorized list restores the server row');
    assert.equal(await localRow('local-auth').count(), 0, 'authorization recovery does not create a duplicate');

    const authForbidden = { ...base, id: 'local-auth-forbidden', title: 'После отказа доступа', meetingId: 'server-auth-forbidden' };
    await publish([authForbidden]);
    assert.equal(await refreshCount(), 8, '403 handoff starts one refresh');
    await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:responseError', {
      detail: {
        elt: document.querySelector('.cabinet-list-controls'),
        target: document.querySelector('#meeting-list-region'),
        xhr: { status: 403, responseText: '' },
      },
    })));
    assert.equal(await page.locator('[data-meeting-row]').count(), 0, '403 clears private meeting rows from the DOM');
    assert.equal(await page.locator('[data-list-retry], [data-list-sign-in]').count(), 0, '403 keeps the existing access recovery state');
    await publish([authForbidden]);
    await page.evaluate(html => {
      document.querySelector('#meeting-list-region [data-list-current-content]')?.replaceChildren(
        document.createRange().createContextualFragment(`<section data-meeting-list><ol class="meeting-list">${html}</ol></section>`),
      );
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
        detail: { target: document.querySelector('#meeting-list-region') },
      }));
    }, serverRow('server-auth-forbidden', 'После отказа доступа'));
    assert.equal(await handoffRow('server-auth-forbidden').count(), 1, 'authorized list restores the 403 server row');
    assert.equal(await localRow('local-auth-forbidden').count(), 0, '403 recovery does not create a duplicate');

    // A fresh page can first observe an in-flight linked row after the native
    // transition; it still performs one reconciliation instead of hiding it.
    const coldStart = { ...base, id: 'local-cold-start', title: 'Холодный старт', meetingId: 'server-cold-start' };
    await publish([coldStart]);
    assert.equal(await refreshCount(), 9, 'initial in-flight identity gets one reconciliation');
    assert.equal(await localRow('local-cold-start').count(), 1, 'initial in-flight alias remains until response');
    await page.evaluate(html => {
      document.querySelector('#meeting-list-region [data-meeting-list] ol').insertAdjacentHTML('afterbegin', html);
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
        detail: { target: document.querySelector('#meeting-list-region') },
      }));
    }, serverRow('server-cold-start', 'Холодный старт'));
    assert.equal(await localRow('local-cold-start').count(), 0, 'initial in-flight alias resolves after response');

    // A new document can first observe an already completed linked row while
    // its initial server HTML is stale. It still gets one reconciliation.
    const coldCompleted = { ...base, id: 'local-cold-completed', title: 'Холодный завершённый старт', meetingId: 'server-cold-completed', uploadComplete: true };
    await publish([coldCompleted]);
    assert.equal(await refreshCount(), 10, 'already completed identity gets one cold-start reconciliation');
    assert.equal(await localRow('local-cold-completed').count(), 1, 'completed cold-start alias remains until response');
    await page.evaluate(html => {
      document.querySelector('#meeting-list-region [data-meeting-list] ol').insertAdjacentHTML('afterbegin', html);
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
        detail: { target: document.querySelector('#meeting-list-region') },
      }));
    }, serverRow('server-cold-completed', 'Холодный завершённый старт'));
    assert.equal(await localRow('local-cold-completed').count(), 0, 'completed cold-start alias resolves after response');

    // If deletion confirmation is open during the handoff, the pending
    // selection and return focus follow the server identity.
    const modalLocal = { ...base, id: 'local-modal', title: 'Удаление во время handoff' };
    await publish([coldCompleted, modalLocal]);
    await localRow('local-modal').locator('[data-row-delete]').click();
    assert.equal(await page.locator('[data-delete-dialog]').isVisible(), true, 'delete confirmation is open');
    await publish([{ ...coldCompleted }, { ...modalLocal, meetingId: 'server-modal' }]);
    assert.equal(await refreshCount(), 11, 'modal handoff gets one refresh');
    await page.evaluate(html => {
      document.querySelector('#meeting-list-region [data-meeting-list] ol').insertAdjacentHTML('afterbegin', html);
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
        detail: { target: document.querySelector('#meeting-list-region') },
      }));
    }, serverRow('server-modal', 'Удаление во время handoff'));
    assert.equal(await page.locator('[data-delete-dialog]').isVisible(), true, 'delete confirmation remains open');
    await page.locator('[data-delete-cancel]').click();
    assert.equal(await page.locator('[data-meeting-id="server-modal"] [data-meeting-open]').evaluate(node => node === document.activeElement), true, 'return focus follows the server row');

    // If the native projection arrives while the WebView is on settings, it
    // waits for the normal meeting-list navigation and never touches settings.
    await page.evaluate(() => {
      document.querySelector('.cabinet-list-controls')?.remove();
      document.querySelector('#meeting-list-region')?.remove();
    });
    const settingsRoute = { ...base, id: 'local-settings-route', title: 'Из настроек', meetingId: 'server-settings-route', uploadComplete: true };
    await publish([settingsRoute]);
    assert.equal(await refreshCount(), 11, 'settings route does not submit a list request');
    await page.evaluate(html => document.body.insertAdjacentHTML('beforeend', html), `<form class="cabinet-list-controls" method="get" action="/meetings"><input id="meeting-search" name="q" value=""><select id="meeting-status" name="status"><option value="">Все</option></select><select id="meeting-access" name="access"><option value="">Все</option></select><select id="meeting-sort" name="sort"><option value="started_desc" selected>Новые</option></select></form><div id="meeting-list-region"><div data-list-current-content data-meeting-result-complete="true"><section data-meeting-list><ol class="meeting-list">${serverRow('server-settings-route', 'Из настроек')}</ol></section></div></div>`);
    await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap', {
      detail: { target: document.querySelector('#meeting-list-region') },
    })));
    assert.equal(await handoffRow('server-settings-route').count(), 1, 'settings handoff is reconciled by the next list');
    assert.equal(await localRow('local-settings-route').count(), 0, 'settings handoff does not duplicate the server row');
    assert.deepEqual(errors, []);
    console.log('local recording handoff: one-shot refresh, placeholder, filters, selection, focus, retry and no resurrection PASS');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
