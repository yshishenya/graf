// Synthetic settings_visual_ui_harness only; use the existing Playwright install.
const {chromium, webkit} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const origin = process.env.SETTINGS_PREVIEW_URL || 'http://127.0.0.1:8897';
assert(['localhost', '127.0.0.1'].includes(new URL(origin).hostname));
const repo = path.resolve(__dirname, '../../../..');
const bootstrap = fs.readFileSync(path.join(repo, 'apps/windows/RecApp/Web/WebView2Host.cpp'), 'utf8')
  .split('constexpr wchar_t kDesktopBridgeScript[] = LR"JS(')[1].split(')JS";')[0];
const shim = fs.readFileSync(path.join(repo, 'apps/windows/RecApp/Web/NativeSettingsBridge.cpp'), 'utf8')
  .split('return R"JS(')[1].split(')JS";')[0];
const userText = 'На этом Mac обсуждали Настройки macOS — синтетическое название';
// The settings harness omits the public stylesheet and the notification-history API.
// Supply the real local asset and an empty synthetic history, not masked console errors.
const prepareHarness = async page => {
  await page.route('**/static/public/cookieconsent.css?*', route => route.fulfill({
    contentType: 'text/css',
    path: path.join(repo, 'apps/server/src/twobrain_rec_server/public/static/public/cookieconsent.css')
  }));
  await page.route('**/api/v1/notifications?*', route => route.fulfill({json: {
    items: [], next_cursor: null, has_unseen_action_required: false
  }}));
};

(async () => {
  for (const [name, engine] of Object.entries({chromium, webkit})) {
    const browser = await engine.launch({headless: true});
    let checks = 0;
    try {
      for (const platform of ['windows', 'mac', 'old-mac']) {
        const page = await browser.newPage();
        await prepareHarness(page);
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        page.on('console', message => {if (message.type() === 'error') errors.push(`${message.text()} ${message.location().url}`);});
        await page.addInitScript(({platform, userText}) => {
          if (platform !== 'old-mac') window.GRAFDesktopPlatform = platform === 'windows' ? 'windows' : 'macos';
          window.requests = [];
          window.preferences = {reminders: true, showTitles: false, sound: false, offsetMinutes: 1, quiet: false};
          window.replyVersion = 2;
          window.extraPermission = false;
          window.webkit = {messageHandlers: {
            grafRecordingSettings: {postMessage: async () => ({version: 1, targets: [{id: 'zoom', name: userText, rule: 'ask'}]})},
            grafNotificationSettings: {postMessage: async request => {
              if (request.version !== 2) throw new Error('notification version must be 2');
              window.requests.push(request.action);
              if (request.action === 'set') {
                if (window.failSave) throw new Error('synthetic failure');
                window.preferences[request.field] = request.value;
              }
              return {version: window.replyVersion, preferences: {...window.preferences}, canEdit: true, message: '',
                ...(window.extraPermission ? {permission: 'retired'} : {})};
            }}
          }};
          document.addEventListener('DOMContentLoaded', () => {
            const content = document.createElement('div');
            content.id = 'synthetic-user-content';
            content.textContent = userText;
            content.title = userText;
            document.body.append(content);
            window.GRAFRecordingSettings?.connect('synthetic');
            window.GRAFNotificationSettings?.connect('synthetic');
          });
        }, {platform, userText});
        for (const width of [1080, 375]) {
          await page.setViewportSize({width, height: 720});
          for (const route of ['notifications', 'recording', 'integrations/calendar']) {
            assert.equal((await page.goto(`${origin}/desktop/settings/${route}`)).status(), 200);
            assert(await page.title());
            assert(await page.locator('h1').isVisible());
            assert.equal(await page.locator('#synthetic-user-content').textContent(), userText);
            assert.equal(await page.locator('#synthetic-user-content').getAttribute('title'), userText);
            const windows = platform === 'windows';
            if (route === 'notifications') {
              await page.waitForFunction(() => !document.querySelector('[data-local-notification-controls]').disabled);
              assert.equal(await page.locator('#notification-mac-title').textContent(), windows ? 'На этом компьютере' : 'На этом Mac');
              const system = page.locator('[data-local-notification-action="openSystemSettings"]');
              assert.equal(await system.count(), 0);
              assert.equal(await page.locator('[data-local-notification-action="requestPermission"]').count(), 0);
              await page.locator('[data-local-notification-field="quiet"]').check();
              await page.waitForFunction(() => window.preferences.quiet === true);
              await page.getByRole('button', {name: 'Проверить уведомление', exact: true}).click();
              assert((await page.evaluate(() => window.requests)).includes('test'));
              await page.evaluate(() => {window.failSave = true;});
              await page.locator('[data-local-notification-field="sound"]').check();
              await page.locator('[data-local-notification-settings][data-state="error"]').waitFor();
              const status = await page.locator('[data-local-notification-status]').textContent();
              await page.evaluate(() => {
                window.GRAFPlatform.refresh();
                const root = document.querySelector('[data-local-notification-settings]');
                root.dispatchEvent(new CustomEvent('htmx:afterSwap', {bubbles: true, detail: {target: root}}));
              });
              assert.equal(await page.locator('[data-local-notification-status]').textContent(), status);
              assert(await page.locator('[data-local-notification-field="sound"]').isChecked());
              // An absent platform marker preserves Mac copy, not the retired v1 protocol.
              await page.reload();
              await page.waitForFunction(() => !document.querySelector('[data-local-notification-controls]').disabled);
              await page.evaluate(() => {window.replyVersion = 1; window.GRAFNotificationSettings.refresh();});
              await page.waitForFunction(() => document.querySelector('[data-local-notification-status]').textContent.startsWith('Не удалось загрузить'));
              assert(await page.locator('[data-local-notification-field="sound"]').isDisabled());
              assert.match(await page.locator('[data-local-notification-status]').textContent(), windows ? /этого компьютера/ : /этого Mac/);
              await page.evaluate(() => {window.replyVersion = 2; window.extraPermission = true; window.GRAFNotificationSettings.refresh();});
              await page.waitForFunction(() => document.querySelector('[data-local-notification-controls]').disabled);
              await page.evaluate(() => window.GRAFNotificationSettings.disconnect());
              assert.equal(await system.count(), 0);
            } else if (route === 'recording') {
              await page.locator('[data-recording-target]').waitFor({state: 'attached'});
              assert.equal(await page.locator('[data-recording-settings-targets] .settings-control-row__title').textContent(), userText);
              assert.match(await page.locator('#recording-rules-help').textContent(), windows ? /на этом компьютере/ : /на этом Mac/);
            } else {
              assert.equal(await page.locator('#calendar-prompt-preferences-title').textContent(), windows ? 'Подсказки в Windows' : 'Подсказки на Mac');
            }
            assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
            if (process.env.SCREENSHOT_DIR && route === 'notifications' && platform === 'windows') {
              await page.screenshot({path: `${process.env.SCREENSHOT_DIR}/${name}-windows-${width}.png`, fullPage: true});
            }
            checks++;
          }
        }
        // Deletion copy is composed at render time; the title remains byte-for-byte Mac wording.
        await page.goto(`${origin}/desktop/meetings`);
        await page.evaluate(userText => window.GRAFLocalRecordings.update([
          {id: 'synthetic-local', title: userText, localDeletionPending: true}
        ], [{phase: 'verified'}], false), userText);
        const localCopy = await page.locator('[data-native-deletion-status]').textContent();
        assert(localCopy.includes(userText + (platform === 'windows'
          ? ': очистка файлов на этом компьютере' : ': очистка файлов на этом Mac')));
        checks++;
        assert.deepEqual(errors, []);
        await page.close();
      }
      // Actual native bootstrap, late installation, shim privacy, scoped HTMX root + descendants.
      const page = await browser.newPage();
      await prepareHarness(page);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => {if (message.type() === 'error') errors.push(`${message.text()} ${message.location().url}`);});
      await page.goto(`${origin}/desktop/meetings`);
      await page.evaluate(userText => {
        const node = document.createElement('p'); node.id = 'synthetic-user-content'; node.textContent = userText; node.title = userText;
        document.body.append(node);
        window.chrome = {webview: {postMessage() {}, addEventListener() {}}};
      }, userText);
      assert.equal(await page.evaluate(() => window.GRAFDesktopPlatform), undefined);
      await page.evaluate(bootstrap);
      assert.equal(await page.evaluate(() => window.GRAFDesktopPlatform), 'windows');
      await page.evaluate(shim);
      assert.equal(await page.locator('#synthetic-user-content').textContent(), userText);
      assert.equal(await page.locator('#synthetic-user-content').getAttribute('title'), userText);
      await page.evaluate(() => {
        const root = document.createElement('p'); root.id = 'synthetic-swap';
        root.dataset.platformCopy = 'На этом компьютере'; root.textContent = 'На этом Mac';
        document.body.append(root);
        root.dispatchEvent(new CustomEvent('htmx:afterSwap', {bubbles: true, detail: {target: root}}));
      });
      assert.equal(await page.locator('#synthetic-swap').textContent(), 'На этом компьютере');
      await page.evaluate(() => {
        const root = document.querySelector('#synthetic-swap'); root.removeAttribute('data-platform-copy');
        root.innerHTML = '<span data-platform-copy="Подсказки в Windows">Подсказки на Mac</span>';
        root.dispatchEvent(new CustomEvent('htmx:afterSwap', {bubbles: true, detail: {target: root}}));
      });
      assert.equal(await page.locator('#synthetic-swap').textContent(), 'Подсказки в Windows');
      // Exercise the real HTMX lifecycle as well as the isolated event contract.
      await page.evaluate(() => window.htmx.swap('#synthetic-swap',
        '<p id="synthetic-swap" data-platform-copy="На этом компьютере">На этом Mac</p>',
        {swapStyle: 'outerHTML'}));
      assert.equal(await page.locator('#synthetic-swap').textContent(), 'На этом компьютере');
      await page.evaluate(() => {
        document.querySelector('#synthetic-swap').removeAttribute('data-platform-copy');
        window.htmx.swap('#synthetic-swap',
          '<span data-platform-copy="Подсказки в Windows">Подсказки на Mac</span>',
          {swapStyle: 'innerHTML'});
      });
      assert.equal(await page.locator('#synthetic-swap span').textContent(), 'Подсказки в Windows');
      await page.route('**/synthetic-platform-fragment', route => route.fulfill({
        status: 200, contentType: 'text/html',
        body: '<span data-platform-copy="Подсказки в Windows">Подсказки на Mac</span>'
      }));
      await page.evaluate(() => {
        const trigger = document.createElement('button');
        trigger.type = 'button'; trigger.id = 'synthetic-swap-trigger';
        trigger.textContent = 'Загрузить подпись';
        trigger.setAttribute('hx-get', '/synthetic-platform-fragment');
        trigger.setAttribute('hx-target', '#synthetic-swap');
        trigger.setAttribute('hx-swap', 'innerHTML');
        document.body.append(trigger); window.htmx.process(trigger);
      });
      await page.getByRole('button', {name: 'Загрузить подпись'}).click();
      await page.locator('#synthetic-swap span').waitFor();
      assert.equal(await page.locator('#synthetic-swap span').textContent(), 'Подсказки в Windows');
      checks++;
      await page.evaluate(userText => window.GRAFLocalRecordings.update([
        {id: 'synthetic-local', title: userText, localDeletionPending: true}
      ], [{phase: 'verified'}, {phase: 'queued', waitReason: 'localCleanup'}], false), userText);
      const deletion = await page.locator('[data-native-deletion-status]').textContent();
      assert(deletion.includes(userText + ': очистка файлов на этом компьютере'));
      assert(deletion.includes('Данные этой записи очищены на этом компьютере'));
      assert(deletion.includes('Не удалось очистить файлы на этом компьютере'));
      // Late native bootstrap updates only marked service leaves, not live status or drafts.
      await page.goto(`${origin}/desktop/settings/notifications`);
      await page.evaluate(() => {
        document.querySelector('[data-local-notification-status]').textContent = 'Синтетическая ошибка сохранения';
        document.querySelector('[data-local-notification-field="sound"]').checked = true;
        window.chrome = {webview: {postMessage() {}, addEventListener() {}}};
      });
      await page.evaluate(bootstrap);
      assert.equal(await page.locator('#notification-mac-title').textContent(), 'На этом компьютере');
      assert.equal(await page.locator('[data-local-notification-status]').textContent(), 'Синтетическая ошибка сохранения');
      assert(await page.locator('[data-local-notification-field="sound"]').isChecked());
      assert.equal(await page.locator('[data-local-notification-action="openSystemSettings"]').count(), 0);
      assert.deepEqual(errors, []);
      await page.close(); checks += 7;
      console.log(`${name}: platform copy ${checks} PASS`);
    } finally { await browser.close(); }
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
