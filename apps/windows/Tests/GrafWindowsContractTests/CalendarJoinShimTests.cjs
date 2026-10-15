// Real browser input, synthetic document/channel only. Not installed WebView evidence.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const {chromium, webkit} = createRequire(path.resolve(__dirname, '../../../server/tests/browser/package.json'))('playwright');
const source = fs.readFileSync(path.resolve(__dirname, '../../RecApp/Web/WebView2Host.cpp'), 'utf8');
const declaration = source.match(/constexpr wchar_t kDesktopBridgeScript\[\] = ([\s\S]*?)\)JS";/)[0];
const chunks = [...declaration.matchAll(/LR"JS\(([\s\S]*?)\)JS"/g)].map(match => match[1]);
assert(chunks.length && chunks.every(chunk => chunk.length * 2 <= 16380), 'MSVC wide literal size limit');
const script = chunks.join('');
const timeScript = source.slice(source.indexOf('nativeReadUserTime_ = [this, alive, dispatcher, core]'))
  .match(/constexpr auto script = LR"JS\(([\s\S]*?)\)JS";/)[1];
const eventId = 'abcdefab-1234-4567-89ab-abcdefabcdef';
const otherId = 'abcdefab-1234-4567-89ab-abcdefabcdea';
const row = id => `<article><a href="#" data-calendar-join="${id}">Подключиться</a><span data-calendar-join-status role="status" aria-live="polite"></span></article>`;

(async () => {
  for (const [name, engine] of Object.entries({chromium, webkit})) {
    const browser = await engine.launch({headless: true});
    try {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('https://graf.test/**', route => route.fulfill({contentType:'text/html', body:`<!doctype html><html lang="ru"><body>${row(eventId)}</body></html>`}));
      const boot = async () => {
        await page.goto('https://graf.test/desktop/meetings');
        await page.evaluate(() => {
          window.messages = []; window.bubbles = 0;
          window.chrome = {webview:{postMessage(message) { window.messages.push(message); }, addEventListener(_, listener) {window.deliver = data => listener({data});}}};
          document.addEventListener('click', event => {if (!event.defaultPrevented) window.bubbles++;});
        });
        await page.addScriptTag({content:script});
      };
      const handshake = async (nonce = 'nonce-1') => page.evaluate(nonce => window.deliver({command:'native_ready',nonce}), nonce);
      const availability = async value => page.evaluate(value => window.__grafSetCalendarJoinAvailable?.(value), value);
      const messages = async () => page.evaluate(() => window.messages.filter(item => item.command.startsWith('calendar_join')));
      const reply = async (request, state, extras = {}) => page.evaluate(({request, state, extras}) => window.deliver({command:'calendar_join_reply',nonce:request.nonce,request_id:request.payload.requestId,state,...extras}), {request,state,extras});
      const button = () => page.locator('[data-calendar-join]').first();
      const status = () => page.locator('[data-calendar-join-status]').first();
      const idle = async () => assert.equal(await button().getAttribute('aria-disabled'), null);
      const mutation = async html => {
        await page.evaluate(html => {document.body.innerHTML=html; document.dispatchEvent(new CustomEvent('htmx:afterSwap'));}, html);
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)));
      };

      await boot();
      await page.evaluate(() => {
        for (const [name, content] of Object.entries({'graf-time-user':'11111111-1111-4111-8111-111111111111',
          'graf-workspace':'22222222-2222-4222-8222-222222222222',
          'graf-time-session':'33333333-3333-4333-8333-333333333333', 'graf-time-preferred':'Asia/Kathmandu'})) {
          const meta = document.createElement('meta'); meta.name = name; meta.content = content; document.head.append(meta);
        }
        const frame = document.createElement('iframe');
        frame.srcdoc = '<meta name="graf-time-preferred" content="America/New_York">'; document.body.append(frame);
        Object.defineProperty(document, 'cookie', {get() {throw new Error('time reader touched cookie');}});
        Object.defineProperty(window, 'GRAFTime', {get() {throw new Error('time reader touched unsaved preference');}});
      });
      assert.deepEqual(await page.evaluate(timeScript), {userId:'11111111-1111-4111-8111-111111111111',
        workspaceId:'22222222-2222-4222-8222-222222222222', sessionId:'33333333-3333-4333-8333-333333333333',
        timeZone:'Asia/Kathmandu', documentURL:'https://graf.test/desktop/meetings'});
      await page.evaluate(() => {document.querySelector('meta[name="graf-time-preferred"]').content='';});
      assert.equal((await page.evaluate(timeScript)).timeZone, '');
      await page.evaluate(() => {document.querySelector('meta[name="graf-time-user"]').remove();});
      assert.equal((await page.evaluate(timeScript)).userId, undefined, 'missing meta cannot invent account authority');
      await boot(); // Isolate subsequent real-input Join checks from the metadata fixture.
      await availability(true); // A setter before handshake must not create pending.
      await button().click(); await idle(); assert.equal((await messages()).length, 0);
      await availability(false); await handshake();
      await button().press('Enter'); await idle(); assert.equal((await messages()).length, 0);
      assert.equal(await page.evaluate(() => window.bubbles), 2);
      await availability(true);
      await button().evaluate(node => node.click()); await idle(); assert.equal((await messages()).length, 0);
      await button().press('Enter');
      let all = await messages();
      assert.equal(all.length, 1, 'trusted keyboard activation sends one intent');
      const first = all[0];
      assert.deepEqual(Object.keys(first.payload).sort(), ['action','eventId','requestId']);
      assert.equal(first.payload.action, 'joinCalendarEvent'); assert.equal(first.payload.eventId, eventId);
      assert.match(first.payload.requestId, /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/);
      assert.equal(await button().getAttribute('aria-disabled'), 'true');
      assert.match(await status().textContent(), /Открываем/);
      const bubbles = await page.evaluate(() => window.bubbles);
      await button().press('Enter'); assert.equal((await messages()).length, 1);
      assert.equal(await page.evaluate(() => window.bubbles), bubbles, 'pending click never escapes to standalone');
      await reply(first, 'handed_off'); // Cannot skip opening.
      assert.equal(await button().getAttribute('aria-disabled'), 'true');
      await reply(first, 'unknown'); await reply(first, 'opening', {nonce:'stale'});
      await reply(first, 'opening', {request_id:otherId});
      await reply(first, 'opening', {reason:'private arbitrary reason'});
      assert.equal(await button().getAttribute('aria-disabled'), 'true');
      await mutation(row(eventId.toUpperCase()));
      assert.equal((await messages()).length, 1, 'same canonical accessible UUID keeps pending');
      assert.equal(await button().getAttribute('aria-disabled'), 'true');
      assert.match(await status().textContent(), /Открываем/);
      await reply(first, 'opening'); await reply(first, 'handed_off'); await idle();
      assert.match(await status().textContent(), /Ссылка передана приложению/);
      await reply(first, 'failed'); assert.match(await status().textContent(), /Ссылка передана/);
      await button().press('Enter');
      const second = (await messages()).at(-1);
      assert.notEqual(first.payload.requestId, second.payload.requestId);
      await reply(first, 'cancelled'); assert.equal(await button().getAttribute('aria-disabled'), 'true');
      await mutation(row(otherId));
      all = await messages();
      assert.equal(all.at(-1).command, 'calendar_join_cancel');
      assert.deepEqual(all.at(-1).payload, {eventId,requestId:second.payload.requestId});
      await idle(); await reply(second, 'opening'); await idle();
      await button().click();
      const third = (await messages()).at(-1);
      await mutation('');
      assert.equal((await messages()).at(-1).command, 'calendar_join_cancel');
      assert.equal((await messages()).at(-1).payload.requestId, third.payload.requestId);
      await mutation(row(eventId)); await button().click();
      const fourth = (await messages()).at(-1);
      await availability(false); await idle();
      assert.equal((await messages()).at(-1).payload.requestId, fourth.payload.requestId);
      assert.match(await status().textContent(), /Действие отменено/);
      await availability(true); await button().click();
      const fifth = (await messages()).at(-1);
      await handshake('nonce-2'); await idle();
      await reply(fifth, 'opening'); await idle();
      await button().click(); const sixth = (await messages()).at(-1);
      assert.equal(sixth.nonce, 'nonce-2');
      await reply(sixth, 'cancelled', {reason:'not_ready'}); await idle();
      assert.match(await status().textContent(), /Повторите/);
      for (const attribute of ['disabled','hidden','inert','data-calendar-join']) {
        await mutation(row(eventId)); await button().click();
        const previous = (await messages()).at(-1);
        await button().evaluate((node, attribute) => {
          node.setAttribute(attribute, attribute==='data-calendar-join'?'abcdefab-1234-4567-89ab-abcdefabcdea':'');
        }, attribute);
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)));
        assert.equal((await messages()).at(-1).command, 'calendar_join_cancel');
        assert.equal((await messages()).at(-1).payload.requestId, previous.payload.requestId);
        await idle();
      }
      await mutation(row(eventId));
      await button().click(); const racing = (await messages()).at(-1);
      await page.evaluate(({request, otherId}) => {
        document.querySelector('[data-calendar-join]').dataset.calendarJoin=otherId;
        window.deliver({command:'calendar_join_reply',nonce:request.nonce,request_id:request.payload.requestId,state:'opening'});
      }, {request:racing,otherId});
      await idle(); assert.equal((await messages()).at(-1).command, 'calendar_join_cancel');
      await mutation(row(eventId));
      await page.evaluate(() => {window.chrome.webview.postMessage=()=>{throw new Error('synthetic-send');};});
      await button().click(); await idle(); assert.match(await status().textContent(), /Не удалось/);
      assert.deepEqual(errors, []);
      console.log(`${name}: CalendarJoinShimTests PASS`);
    } finally {await browser.close();}
  }
})().catch(error => {console.error(error);process.exitCode=1;});
