const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const {chromium, webkit} = require(require.resolve('playwright', {paths:[process.env.GRAF_NODE_MODULES || process.cwd()]}));
const script = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js');
const host = fs.readFileSync(path.join(__dirname, '../../../../apps/windows/RecApp/Web/WebView2Host.cpp'), 'utf8');
const declaration = host.match(/constexpr wchar_t kDesktopBridgeScript\[\] = ([\s\S]*?)\)JS";/)[0];
const bootstrap = [...declaration.matchAll(/LR"JS\(([\s\S]*?)\)JS"/g)].map(match => match[1]).join('');

async function verifyWindowsAudioDownload(browser) {
  const workspace = '22222222-2222-4222-8222-222222222222';
  const meeting = '11111111-1111-4111-8111-111111111111';
  const routes = [
    ['/api/v1/cabinet/meetings/' + meeting + '/downloads/audio', 'Enter'],
    ['/api/v1/cabinet/shared-meetings/' + meeting + '/downloads/audio?workspace_id=' + workspace, 'click']
  ];
  const wire = [];
  const server = http.createServer((request, response) => {
    if (request.url === '/desktop/meetings') {
      response.setHeader('Content-Type', 'text/html; charset=utf-8');
      response.end('<main id="cabinet-main">' + routes.map(([url]) => '<a href="' + url + '">Скачать аудио</a>').join('') + '</main>');
      return;
    }
    wire.push(request.url);
    response.writeHead(200, {'Content-Type': 'application/octet-stream', 'Content-Disposition': 'attachment; filename="recording.wav"'});
    response.end('Synthetic audio bytes');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const origin = 'http://127.0.0.1:' + server.address().port;
    for (const [index, [base, activate]] of routes.entries()) {
      const page = await browser.newPage();
      try {
        await page.goto(origin + '/desktop/meetings');
        await page.evaluate(() => {
          window.testExportMessages = [];
          window.chrome = {webview: new EventTarget()};
          window.chrome.webview.postMessage = message => {
            if (message.command === 'export_download') window.testExportMessages.push(message.payload.uri);
          };
        });
        await page.addScriptTag({content:bootstrap});
        const ack = async (uri, command = 'export_download_ack') => page.evaluate(([uri, command]) => {
          window.chrome.webview.dispatchEvent(new MessageEvent('message', {data: {command, nonce: 'current', uri, accepted: true}}));
        }, [uri, command]);
        await page.evaluate(() => window.chrome.webview.dispatchEvent(new MessageEvent('message', {
          data: {command: 'native_ready', nonce: 'current', export_authority: 10}
        })));
        const link = page.getByRole('link').nth(index);
        if (activate === 'Enter') await link.press('Enter');
        else await link.click();
        await link.click();
        const [first, second] = await page.evaluate(() => window.testExportMessages);
        assert.notEqual(first, second);
        assert(first.startsWith(origin + base + '#graf-export='));
        assert(second.startsWith(origin + base + '#graf-export='));
        await ack(first);
        assert.equal(wire.filter(url => url === base).length, 0, 'the previous request cannot start the same audio URL');
        const audioDownload = page.waitForEvent('download', {timeout: 5000});
        await ack(second);
        const audio = await audioDownload;
        assert.equal(audio.suggestedFilename(), 'recording.wav');
        assert.equal(fs.readFileSync(await audio.path(), 'utf8'), 'Synthetic audio bytes');
        assert.deepEqual(wire.filter(url => url.includes('/downloads/')), routes.slice(0, index + 1).map(([url]) => url),
          'the server receives the unchanged route and query');
        assert.equal(page.url(), origin + '/desktop/meetings', 'download keeps the cabinet open');
        await ack(second, 'export_download_started');
        await page.evaluate(({first, second}) => {
          const scope = window.GRAFDesktopSaveRoute('current', location.href);
          window.GRAFDesktopSaveResult('current', location.href, scope, 1, false, first, 'name_conflict');
          if (document.querySelector('[data-desktop-save-error]')) throw new Error('stale file conflict surfaced');
          window.GRAFDesktopSaveResult('current', location.href, scope, 2, false, second, 'name_conflict');
        }, {first, second});
        assert.match(await page.getByRole('alert').textContent(), /выберите другое имя/);
      } finally { await page.close(); }
    }
  } finally { await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve())); }
  console.log('Windows audio: two direct attachment routes PASS');
}

(async () => {
  const useWebKit = process.env.GRAF_BROWSER === 'webkit';
  const browser = await (useWebKit ? webkit : chromium).launch({headless:true});
  try {
    for (const mode of ['standalone', 'sharing', 'sharing-failure']) {
      const page = await browser.newPage();
      page.setDefaultTimeout(5000);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('https://graf.test/**', route => {
        if (route.request().method() === 'POST') return route.fulfill(mode === 'sharing-failure'
          ? {status:503, json:{code:'export_generation_failed'}}
          : {contentType:'text/plain', headers:{'Content-Disposition':'attachment; filename="synthetic.txt"'}, body:'Synthetic export'});
        return route.fulfill({contentType:'text/html', body:`<meta charset="utf-8">
          <main class="detail-page-main" id="cabinet-main" data-meeting-id="synthetic">
            <header data-meeting-detail-header></header>
            <button data-meeting-panel-open="more">Ещё</button>
            <button data-export-dialog-open>Экспорт</button>
            <dialog data-content-export-dialog>
              <h2 tabindex="-1" data-export-dialog-title>Экспорт</h2>
              <form data-content-export-form data-endpoint="/export" data-export-delivery="save"
                data-export-formats-transcript="txt" data-processing-result-id="synthetic">
                <select data-export-scope><option value="transcript">Расшифровка</option></select>
                <select data-export-format><option value="txt">TXT</option></select>
                <p data-export-status></p><button data-export-submit>Сохранить</button>
              </form>
            </dialog>
            <dialog id="sharing"><h2>Поделиться</h2></dialog>
          </main>`});
      });
      await page.goto('https://graf.test/export');
      await page.addScriptTag({content:fs.readFileSync(script, 'utf8')});
      if (mode === 'standalone') await page.locator('[data-export-dialog-open]').click();
      else await page.evaluate(() => {
        const sharing = document.querySelector('#sharing');
        sharing.append(document.querySelector('[data-content-export-form]'));
        sharing.show();
      });
      const submit = page.locator('[data-export-submit]');
      if (mode === 'sharing-failure') await submit.click();
      else {
        // WebKit can deliver the browser download after the form reports success.
        const [browserDownload] = await Promise.all([page.waitForEvent('download'), submit.click()]);
        assert.equal(browserDownload.suggestedFilename(), 'synthetic.txt');
        assert.equal(fs.readFileSync(await browserDownload.path(), 'utf8'), 'Synthetic export');
      }
      await page.locator(`[data-export-status][data-state=${mode === 'sharing-failure' ? 'error' : 'success'}]`).waitFor({state:'attached'});
      if (mode === 'standalone') {
        assert.equal(await page.locator('[data-content-export-dialog]').evaluate(el => el.open), false);
        assert.equal(await page.locator('[data-export-dialog-open]').evaluate(el => el === document.activeElement), true);
      } else {
        assert.equal(await page.locator('#sharing').evaluate(el => el.open), true);
        assert.equal(await page.locator('[data-export-submit]').evaluate(el => el === document.activeElement), true,
          `${mode}: export must retain focus inside the dialog that owns the reused form`);
      }
      if (mode !== 'sharing-failure') {
        await page.evaluate(() => {
          window.chrome = {webview: new EventTarget()};
          window.chrome.webview.postMessage = () => {};
        });
        await page.addScriptTag({content:bootstrap});
        await page.evaluate(() => {
          window.chrome.webview.dispatchEvent(new MessageEvent('message', {data: {command:'native_ready', nonce:'current', export_authority: 10}}));
          window.GRAFDesktopSaveResult('previous', location.href, 0, 1, false);
        });
        const alert = page.locator('[data-desktop-save-error]');
        assert.equal(await alert.count(), 0, 'a result from the previous document stays invisible');
        await page.evaluate(() => window.GRAFDesktopSaveResult('current', location.href, 0, 1, false));
        assert(await alert.isVisible(), 'the local save error is visible outside the system picker');
        assert.equal(await alert.getAttribute('role'), 'alert');
        assert.match(await alert.textContent(), /выберите другую папку/);
        assert(await alert.evaluate((node, mode) =>
          node.parentElement.matches(mode === 'standalone' ? '[data-meeting-detail-header]' : '#sharing [data-content-export-form]'), mode));
        assert(await page.locator(mode === 'standalone' ? '[data-export-dialog-open]' : '[data-export-submit]')
          .evaluate(el => el === document.activeElement), 'failure does not move focus');
        await page.evaluate(() => window.GRAFDesktopSaveResult('previous', location.href, 0, 1, true));
        assert.equal(await alert.count(), 1);
        await page.evaluate(() => {
          window.GRAFDesktopSaveResult('current', location.href, 0, 2, false);
          window.GRAFDesktopSaveResult('current', location.href, 0, 1, true);
        });
        assert.equal(await alert.getAttribute('data-desktop-save-error'), '2',
          'a success cannot hide a failure reported after that save began');
        await page.evaluate(() => {
          window.GRAFDesktopSaveResult('current', location.href, 0, 2, true);
          window.GRAFDesktopSaveResult('current', location.href, 0, 2, false);
        });
        assert.equal(await alert.count(), 0, 'a delayed copy of a resolved error cannot return');
        await page.evaluate(() => {
          const start = location.href;
          const snapshot = window.GRAFDesktopSaveRoute('current', start);
          for (const url of ['?other=1', start]) {
            history.replaceState(null, '', url);
            if (!window.navigation) dispatchEvent(new PopStateEvent('popstate'));
          }
          window.GRAFDesktopSaveResult('current', start, snapshot, 3, false);
        });
        assert.equal(await alert.count(), 0, 'going away and back cannot resurrect a late result');
        await page.evaluate(() => window.GRAFDesktopSaveResult('current', location.href,
          window.GRAFDesktopSaveRoute('current', location.href), 4, false));
        assert.equal(await alert.getAttribute('data-desktop-save-error'), '4', 'the current route still reports errors');
        if (mode === 'standalone') {
          const filenames = [];
          page.on('download', download => filenames.push(download.suggestedFilename()));
          await page.evaluate(() => {
            window.GRAFDesktopSaveResult('current', location.href, window.GRAFDesktopSaveRoute('current', location.href), 4, true);
            window.testExportMessages = [];
            window.chrome.webview.postMessage = message => {
              if (message.command === 'export_download') window.testExportMessages.push(message);
            };
            const link = document.createElement('a');
            link.href = URL.createObjectURL(new Blob(['old']));
            link.download = 'old.txt';
            link.hidden = true;
            document.body.append(link);
            link.click();
            link.remove();
          });
          await page.locator('[data-export-dialog-open]').click();
          await page.locator('[data-export-submit]').click();
          await page.waitForFunction(() => window.testExportMessages.length === 2);
          const request = await page.evaluate(() => window.testExportMessages);
          assert.deepEqual(filenames, [], 'neither download starts before acknowledgment');
          assert.deepEqual(request.map(message => message.command), ['export_download', 'export_download']);
          assert(request.every(message => message.nonce === 'current' && message.payload.authority === 10));
          const [a, b] = request.map(message => message.payload.uri);
          assert.notEqual(a, b);
          await page.evaluate(([a, b]) => {
            const send = (uri, nonce) => window.chrome.webview.dispatchEvent(new MessageEvent('message', {
              data: {command: 'export_download_ack', nonce, uri, accepted: true}
            }));
            send(a, 'current');
            send(b, 'old-document');
            window.GRAFDesktopSaveResult('current', location.href, window.GRAFDesktopSaveRoute('current', location.href), 5, false, a);
          }, [a, b]);
          assert.equal(await alert.count(), 0, 'late A cannot report an error during B');
          const downloaded = page.waitForEvent('download');
          await page.evaluate(uri => window.chrome.webview.dispatchEvent(new MessageEvent('message', {
            data: {command: 'export_download_ack', nonce: 'current', uri, accepted: true}
          })), b);
          const download = await downloaded;
          assert.equal(download.suggestedFilename(), 'synthetic.txt');
          assert.equal(fs.readFileSync(await download.path(), 'utf8'), 'Synthetic export');
          assert.deepEqual(filenames, ['synthetic.txt'], 'only the acknowledged current download starts');
          await page.evaluate(uri => {
            const scope = window.GRAFDesktopSaveRoute('current', location.href);
            window.GRAFDesktopExportAuthority('current', 9);
            window.GRAFDesktopSaveResult('current', location.href, scope, 6, false, uri);
          }, b);
          assert.equal(await alert.getAttribute('data-desktop-save-error'), '6', 'a late authority update cannot revoke B');
          await page.evaluate(uri => {
            const scope = window.GRAFDesktopSaveRoute('current', location.href);
            window.GRAFDesktopExportAuthority('current', 11);
            window.GRAFDesktopSaveResult('current', location.href, scope, 7, false, uri);
          }, b);
          assert.equal(await alert.count(), 0, 'a revoked URI cannot report a delayed result');
          await page.clock.install();
          await page.locator('[data-export-dialog-open]').click();
          await page.locator('[data-export-submit]').click();
          await page.waitForFunction(() => window.testExportMessages.length === 3);
          const stale = await page.evaluate(() => window.testExportMessages.at(-1));
          assert.equal(stale.payload.authority, 11);
          await page.evaluate(uri => window.chrome.webview.dispatchEvent(new MessageEvent('message', {
            data: {command: 'export_download_ack', nonce: 'current', uri, accepted: false, authority: 12}
          })), stale.payload.uri);
          assert.equal(await alert.count(), 0, 'an already revoked authority is updated without an old error');
          await page.locator('[data-export-dialog-open]').click();
          await page.locator('[data-export-submit]').click();
          await page.waitForFunction(() => window.testExportMessages.length === 4);
          const last = await page.evaluate(() => window.testExportMessages.at(-1));
          assert.equal(last.payload.authority, 12);
          const thirdDownload = page.waitForEvent('download');
          await page.evaluate(uri => window.chrome.webview.dispatchEvent(new MessageEvent('message', {
            data: {command: 'export_download_ack', nonce: 'current', uri, accepted: true}
          })), last.payload.uri);
          await thirdDownload;
          await page.clock.fastForward(8100);
          assert.match(await alert.textContent(), /Не удалось начать сохранение/, 'ACK without a native start is visible');
        }
      }
      assert.deepEqual(errors, []);
      await page.close();
      console.log(`${mode}: export focus PASS`);
    }
    if (!useWebKit) await verifyWindowsAudioDownload(browser);
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
