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
const rendered = process.argv.includes('--rendered') ? JSON.parse(fs.readFileSync(0, 'utf8')) : null;
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

      // T088: execute the shared publisher, not a duplicate hint implementation.
      // Only its lexical inputs (the adopted rows and frame latch) are synthetic.
      await boot();
      await mutation('<main><section data-meeting-list><article data-meeting-row data-graf-local-recording-id="visible-local" style="height:40px">generated</article><article data-meeting-row data-graf-local-recording-id="offscreen-local" style="margin-top:3000px;height:40px">generated</article></section><button data-graf-local-recording-action="open" data-graf-local-recording-id="visible-local">Open</button></main>');
      const cabinetSource = fs.readFileSync(path.resolve(__dirname, '../../../server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js'), 'utf8');
      const deletionSource = fs.readFileSync(path.resolve(__dirname, '../../RecApp/Web/RecordingDeletionBridge.cpp'), 'utf8');
      const deletionScript = deletionSource.match(/constexpr std::string_view kDocumentScript = R"JS\(([\s\S]*?)\)JS";/)[1];
      const publisherBegin = cabinetSource.indexOf('  const publishVisibleRecordings =');
      const publisherEnd = cabinetSource.indexOf('  const pendingLocalRecordingHandoffs =', publisherBegin);
      assert(publisherBegin >= 0 && publisherEnd > publisherBegin);
      const listReaders = cabinetSource.match(/  const currentList = [^\n]+\n  const allRows = [^\n]+/)[0];
      await page.addScriptTag({content:deletionScript});
      await page.evaluate(() => {
        const handler = window.webkit.messageHandlers.grafLocalRecording;
        const actualPost = handler.postMessage;
        window.publisherBodies = [];
        handler.postMessage = body => {
          window.publisherBodies.push(JSON.parse(JSON.stringify(body)));
          return actualPost(body); // Observe the actual publisher without replacing the native script.
        };
      });
      await page.addScriptTag({content:`(() => {let visibleRecordingsFrame = null; const localRecordingRows = [{id:'visible-local'},{id:'offscreen-local'}];\n${listReaders}\n${cabinetSource.slice(publisherBegin, publisherEnd)}\n})();`});
      const hints = async () => page.evaluate(() => window.messages.filter(item => item.command === 'visible_recordings'));
      const publish = async () => {
        await page.evaluate(() => document.dispatchEvent(new Event('scroll')));
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      };
      await publish();
      assert.equal((await hints()).length, 0, 'publisher has no nonce before native_ready');
      await handshake(); await publish();
      assert.deepEqual(errors, [], 'fixture must execute both native scripts and the actual publisher without script errors');
      assert.deepEqual(await page.evaluate(() => window.publisherBodies), [
        {action:'visibleRecordings',version:1,ids:['visible-local']},
        {action:'visibleRecordings',version:1,ids:['visible-local']}
      ], 'fixture must prove the actual publisher called the actual document handler before RED0');
      const firstHint = (await hints())[0];
      assert.equal((await hints()).length, 1, 'T088 RED0: actual cabinet publisher must deliver one visible_recordings envelope through both Windows scripts');
      assert.deepEqual(Object.keys(firstHint).sort(), ['command','direction','message_id','nonce','origin','payload','protocol','sent_at_monotonic_ms','version']);
      assert.equal(firstHint.protocol, 'graf.desktop.bridge'); assert.equal(firstHint.version, 1);
      assert.equal(firstHint.direction, 'web_to_native'); assert.equal(firstHint.origin, 'https://graf.test');
      assert.equal(firstHint.nonce, 'nonce-1'); assert(Number.isSafeInteger(firstHint.message_id) && firstHint.message_id > 0);
      assert(Number.isSafeInteger(firstHint.sent_at_monotonic_ms) && firstHint.sent_at_monotonic_ms >= 0);
      assert.deepEqual(firstHint.payload, {action:'visibleRecordings',version:1,ids:['visible-local']});
      await page.locator('[data-graf-local-recording-action="open"]').click();
      const localAction = await page.evaluate(() => window.messages.find(item => item.command === 'local_recording'));
      assert.deepEqual(localAction.payload, {action:'open',id:'visible-local'});
      assert(localAction.message_id > firstHint.message_id, 'hint and local_recording share private monotonic send');
      const beforeInvalidHints = (await hints()).length;
      await page.evaluate(() => {
        const post = body => window.webkit.messageHandlers.grafLocalRecording.postMessage(body);
        for (const body of [
          {action:'visibleRecordings',version:2,ids:[]}, {action:'visibleRecordings',version:1.1,ids:[]},
          {action:'visibleRecordings',version:1,ids:['visible-local','visible-local']},
          {action:'visibleRecordings',version:1,ids:[7]}, {action:'visibleRecordings',version:1,ids:'visible-local'},
          {action:'visibleRecordings',version:1,ids:[],extra:true},
          {action:'visibleRecordings',version:1,ids:Array.from({length:101},(_,i)=>`local-${i}`)}
        ]) post(body);
      });
      assert.equal((await hints()).length, beforeInvalidHints, 'malformed hints are not shortened or partially forwarded');
      await page.evaluate(() => window.webkit.messageHandlers.grafLocalRecording.postMessage({action:'deleteSelection',version:1,requestId:'44444444-4444-4444-8444-444444444444',localIds:['visible-local'],meetingIds:[]}));
      assert.deepEqual(await page.evaluate(() => window.messages.find(item => item.command === 'delete_selection').payload),
        {action:'deleteSelection',version:1,requestId:'44444444-4444-4444-8444-444444444444',localIds:['visible-local'],meetingIds:[]});
      await page.evaluate(() => Object.defineProperty(document, 'hidden', {configurable:true,value:true}));
      await publish(); assert.deepEqual((await hints()).at(-1).payload, {action:'visibleRecordings',version:1,ids:[]});
      assert((await hints()).at(-1).message_id > localAction.message_id);
      await boot(); // All prior calendar cases retain their original document and deadlines.

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
      if (rendered !== null) {
        await boot();
        await mutation(rendered.upcoming);
        assert.equal(await page.locator('[data-calendar-join]').count(), 1, 'actual calendar renderer must expose the native Join action');
        assert.equal(await button().getAttribute('href'), `/api/v1/calendar/events/${eventId}/open`);
        for (const ready of [false, true]) {
          if (ready) await handshake(); // Availability is still false.
          await page.evaluate(() => document.addEventListener('click', event => {
            window.fallbackAllowed = !event.defaultPrevented;
            event.preventDefault(); // Observe ordinary link dispatch without sending a real request.
          }, {once:true}));
          await button().click();
          assert.equal(await page.evaluate(() => window.fallbackAllowed), true);
          assert.equal((await messages()).length, 0);
        }
        await availability(true);
        await button().press('Enter');
        const request = (await messages())[0];
        assert.equal((await messages()).length, 1);
        assert.deepEqual(Object.keys(request.payload).sort(), ['action','eventId','requestId']);
        assert.equal(request.payload.eventId, eventId);
        assert.equal(request.payload.action, 'joinCalendarEvent');
        assert.match(request.payload.requestId, /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/);
        assert.equal(await button().getAttribute('aria-disabled'), 'true');
        await reply(request, 'opening'); await reply(request, 'handed_off'); await idle();
        assert.match(await status().textContent(), /Ссылка передана приложению/);
        assert.equal(await status().getAttribute('aria-live'), 'polite');
        const cabinet = fs.readFileSync(path.resolve(__dirname, '../../../server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js'), 'utf8');
        const platformHelper = cabinet.slice(0, cabinet.indexOf('  const csrfToken =')) + '})();';
        for (const platform of [undefined, 'macos', 'windows']) {
          await page.evaluate(platform => {
            if (platform === undefined) delete window.GRAFDesktopPlatform;
            else window.GRAFDesktopPlatform = platform;
          }, platform);
          await mutation(rendered.empty);
          await page.evaluate(() => {
            const user = document.createElement('p'); user.id = 'synthetic-user-content';
            user.textContent = 'На этом Mac — синтетическое название'; document.body.append(user);
          });
          await page.addScriptTag({content: platformHelper});
          assert.equal(await page.locator('.calendar-home-upcoming__empty p').textContent(), platform === 'windows'
            ? 'GRAF покажет ближайшие встречи здесь и в меню приложения, но не начнет запись автоматически.'
            : 'GRAF покажет ближайшие встречи здесь и в строке меню macOS, но не начнет запись автоматически.');
          assert.equal(await page.locator('#synthetic-user-content').textContent(), 'На этом Mac — синтетическое название');
        }
      }
      assert.deepEqual(errors, []);
      console.log(`${name}: CalendarJoinShimTests PASS`);
    } finally {await browser.close();}
  }
})().catch(error => {console.error(error);process.exitCode=1;});
