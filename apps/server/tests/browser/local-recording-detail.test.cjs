const {chromium, webkit} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch({headless:true});
  try {
    const page = await browser.newPage();
    const errors=[]; page.on('pageerror', e=>errors.push(e.message));
    const meetingId = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
    const html = (state, reason = '', id = meetingId, text = state) => `<main id="cabinet-main" data-meeting-id="${id}" data-playback-poll-url="/meeting" data-playback-poll-active="false"><h1 tabindex="-1">Synthetic</h1><p data-playback-live-status>${text}</p><section data-playback-transcript>Synthetic transcript</section></main><section class="detail-playback" data-playback-state="${state}" data-playback-reason="${reason}"><p>${text}</p></section>`;
    let nextHtml = html('unavailable', 'storage_capacity_exceeded');
    let delayedPoll = null;
    await page.route('https://graf.test/**', async route => {
      if (delayedPoll && route.request().headers()['hx-request'] === 'true') {
        const pending = delayedPoll;
        pending.started();
        const result = await pending.result;
        if (result.networkError) return route.abort('failed');
        return route.fulfill({status:result.status, contentType:result.contentType, body:result.body});
      }
      return route.fulfill({contentType:'text/html', body:nextHtml});
    });
    await page.goto('https://graf.test/meeting');
    const source = fs.readFileSync(path.join(__dirname,'../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js'), 'utf8');
    const hook = '  const initPlaybackRecoveryPolling = () => {';
    assert.equal(source.split(hook).length, 2, 'test exports the actual recovery function once');
    await page.addScriptTag({content:source.replace(hook, `  window.recoverDetailTest = recoverMeetingDetailFromResponse;
    window.refreshLocalPlaybackTest = () => {
      document.querySelector('main').dataset.playbackPollActive = 'true';
      return refreshPlaybackRecovery();
    };
${hook}`)});
    const row={id:'local-a',meetingId:'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',canOpen:true};
    const publish=rows=>page.evaluate(rows=>window.GRAFLocalRecordings.update(rows),rows);
    const button=page.locator('[data-graf-local-recording-action="open"]');
    assert.equal(await button.count(),0,'ordinary browser has no local action');
    await publish([row]);
    assert.equal(await button.count(),1,'authorized local copy is available from detail');
    assert.equal(await button.textContent(),'Слушать запись с этого Mac');
    await button.focus();
    await publish([row]);
    assert.equal(await button.evaluate(e=>e===document.activeElement),true,'polling retains keyboard focus');
    await page.evaluate(()=>{document.querySelector('[data-playback-state]').dataset.playbackReason='access_denied';});
    await publish([row]);
    assert.equal(await button.count(),0,'server access denial hides stale native row');
    await page.evaluate(()=>{document.querySelector('[data-playback-state]').dataset.playbackReason='storage_capacity_exceeded';});
    await publish([row]);
    assert.equal(await button.count(),1,'authorized quota fallback returns');
    await publish([{...row,canOpen:false}]);
    assert.equal(await button.count(),0,'access loss removes action');
    await publish([{...row,meetingId:'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'}]);
    assert.equal(await button.count(),0,'another meeting cannot be opened');
    await publish([row]);
    await page.evaluate(()=>{document.querySelector('main').dataset.meetingId='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'; document.body.dispatchEvent(new CustomEvent('htmx:afterSwap'));});
    assert.equal(await button.count(),0,'navigation removes stale action');
    await page.evaluate(()=>{document.querySelector('main').dataset.meetingId='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'; document.body.dispatchEvent(new CustomEvent('htmx:afterSwap'));});
    assert.equal(await button.count(),1,'fragment navigation reconciles local row');
    // Poll the real recovery function without emitting an htmx swap or a native update.
    nextHtml = html('preparing');
    await page.evaluate(() => window.refreshLocalPlaybackTest());
    assert.equal(await page.locator('.detail-playback').getAttribute('data-playback-state'), 'preparing');
    assert.equal(await button.count(),1,'preparing replacement retains the authorized local action');
    nextHtml = html('unavailable', 'storage_capacity_exceeded');
    await page.evaluate(() => window.refreshLocalPlaybackTest());
    assert.equal(await page.locator('.detail-playback').getAttribute('data-playback-reason'), 'storage_capacity_exceeded');
    assert.equal(await button.count(),1,'direct preparing-to-quota polling restores local playback');
    await button.focus();
    await page.evaluate(() => { window.savedLocalButton = document.querySelector('[data-detail-local-playback]'); window.savedLocalPlayback = document.querySelector('.detail-playback'); });
    await page.evaluate(() => window.refreshLocalPlaybackTest());
    assert.equal(await button.evaluate(e=>e===window.savedLocalButton && e===document.activeElement),true,'unchanged server polling retains the same local button and keyboard focus');
    assert.equal(await page.evaluate(() => window.savedLocalPlayback === document.querySelector('.detail-playback')),true,'native-only action is excluded from server change detection');
    // The reason can change while the state and visible text remain identical.
    nextHtml = html('unavailable', 'access_denied');
    await page.evaluate(() => window.refreshLocalPlaybackTest());
    assert.equal(await button.count(),0,'unchanged-state polling removes a stale local action on access denial');
    nextHtml = html('unavailable', 'storage_capacity_exceeded');
    await page.evaluate(() => window.refreshLocalPlaybackTest());
    assert.equal(await button.count(),1,'unchanged-state polling restores an authorized local action');
    nextHtml = html('unavailable', 'access_denied', meetingId, 'Доступ закрыт');
    await page.evaluate(() => window.refreshLocalPlaybackTest());
    assert.equal(await button.count(),0,'replacement polling also removes local action on access denial');
    nextHtml = html('unavailable', 'storage_capacity_exceeded');
    await page.evaluate(() => window.refreshLocalPlaybackTest());
    assert.equal(await button.count(),1,'authorized replacement restores local action');
    nextHtml = html('unavailable', 'access_denied', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb');
    await page.evaluate(() => window.refreshLocalPlaybackTest());
    assert.equal(await page.locator('.detail-playback').getAttribute('data-playback-reason'), 'storage_capacity_exceeded','a response for another route cannot replace current playback');
    assert.equal(await button.count(),1,'another meeting response cannot remove current meeting local action');
    for (const state of ['deleting', 'deleted']) {
      nextHtml = html(state);
      await page.evaluate(() => window.refreshLocalPlaybackTest());
      assert.equal(await button.count(),0,`${state} polling removes a stale local action`);
    }
    nextHtml = html('unavailable', 'storage_capacity_exceeded');
    await page.evaluate(() => window.refreshLocalPlaybackTest());
    assert.equal(await button.count(),1,'authorized current meeting action returns before native deletion update');
    await publish([]);
    assert.equal(await button.count(),0,'deletion or account change removes action');
    // A 403 may finish decoding after fragment navigation has installed another meeting.
    const recoveryTemplate = '<template data-meeting-detail-recovery-template><main tabindex="-1"><section data-cabinet-state><h1 id="recovery-title"></h1><p class="cabinet-state__description"></p><div class="cabinet-state__action"><a></a></div></section></main></template>';
    const nextMeetingId = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
    // Suspend the real poll before fetch resolves, then reuse the same main for
    // another meeting. Delayed body reading is a separate asynchronous boundary.
    for (const mode of ['fetch-403', 'fetch-404', 'fetch-500', 'fetch-success', 'fetch-network-error', 'body-success']) {
      const bodyDelay = mode === 'body-success';
      await page.evaluate(({markup, recoveryTemplate, meetingId, bodyDelay}) => {
        document.body.innerHTML = markup + recoveryTemplate;
        history.replaceState({}, '', `/desktop/meetings/${meetingId}`);
        document.title = 'Synthetic old meeting';
        window.originalPollDetail = document.querySelector('main');
        if (bodyDelay) {
          window.originalPollFetch = window.fetch;
          window.pollBodyReadStarted = false;
          const bodyReady = new Promise(resolve => { window.releasePollBody = resolve; });
          window.fetch = async (...args) => {
            const response = await window.originalPollFetch(...args);
            const readText = response.text.bind(response);
            response.text = async () => {
              window.pollBodyReadStarted = true;
              await bodyReady;
              return readText();
            };
            return response;
          };
        }
      }, {markup:html('unavailable', 'storage_capacity_exceeded'), recoveryTemplate, meetingId, bodyDelay});
      let releasePoll, markStarted;
      const started = new Promise(resolve => { markStarted = resolve; });
      delayedPoll = {started:markStarted, result:new Promise(resolve => { releasePoll = resolve; })};
      await page.evaluate(() => { window.pendingPlaybackPoll = window.refreshLocalPlaybackTest(); });
      await started;
      const status = mode === 'fetch-403' ? 403 : mode === 'fetch-404' ? 404 : mode === 'fetch-500' ? 500 : 200;
      const result = {
        status,
        networkError:mode === 'fetch-network-error',
        contentType:status === 200 ? 'text/html' : 'application/json',
        body:status === 200 ? html('available', '', meetingId, 'Old response')
          : JSON.stringify({code:status === 403 ? 'access_denied' : status === 404 ? 'meeting_not_found' : 'internal_error'}),
      };
      if (bodyDelay) {
        releasePoll(result);
        await page.waitForFunction(() => window.pollBodyReadStarted === true);
      }
      await page.evaluate(({markup, nextMeetingId, row}) => {
        const currentDetail = document.querySelector('main');
        const fragment = new DOMParser().parseFromString(markup, 'text/html');
        const newDetail = fragment.querySelector('main');
        currentDetail.dataset.meetingId = nextMeetingId;
        currentDetail.dataset.playbackPollUrl = '/new-meeting';
        currentDetail.dataset.playbackPollActive = 'false';
        currentDetail.innerHTML = newDetail.innerHTML;
        currentDetail.nextElementSibling.replaceWith(newDetail.nextElementSibling);
        history.replaceState({}, '', `/desktop/meetings/${nextMeetingId}`);
        document.title = 'Synthetic new meeting';
        window.GRAFLocalRecordings.update([{...row,id:'local-b',meetingId:nextMeetingId}]);
        window.newPollDetail = currentDetail;
        window.newPollButton = document.querySelector('[data-graf-local-recording-action="open"]');
        window.newPollButton.focus();
        window.newPollMarkup = document.body.innerHTML;
      }, {markup:html('unavailable', 'storage_capacity_exceeded', nextMeetingId, 'New meeting'), nextMeetingId, row});
      if (bodyDelay) await page.evaluate(() => window.releasePollBody());
      else releasePoll(result);
      await page.evaluate(async bodyDelay => {
        await window.pendingPlaybackPoll;
        if (bodyDelay) window.fetch = window.originalPollFetch;
      }, bodyDelay);
      delayedPoll = null;
      assert.equal(new URL(page.url()).pathname, `/desktop/meetings/${nextMeetingId}`, `${mode}: stale response retains the new private route`);
      assert.equal(await page.title(), 'Synthetic new meeting', `${mode}: stale response retains the new title`);
      assert.deepEqual(await page.evaluate(() => [
        window.originalPollDetail === window.newPollDetail,
        window.newPollDetail === document.querySelector('main') && window.newPollDetail.isConnected,
        document.body.innerHTML === window.newPollMarkup,
        window.newPollButton === document.querySelector('[data-graf-local-recording-action="open"]'),
        window.newPollButton === document.activeElement,
      ]), [true,true,true,true,true], `${mode}: reused main, new contents, local action and keyboard focus stay intact`);
      assert.equal(await page.locator('[data-playback-recovery-copy]').count(),0,`${mode}: stale response cannot add an error to the new meeting`);
    }
    for (const {mode, reuseDetail} of [
      {mode:'json', reuseDetail:false}, {mode:'read-error', reuseDetail:false},
      {mode:'json', reuseDetail:true}, {mode:'read-error', reuseDetail:true},
    ]) {
      const label = `${mode}, ${reuseDetail ? 'same main' : 'replaced main'}`;
      await page.evaluate(({markup, recoveryTemplate, meetingId, mode}) => {
        document.body.innerHTML = markup + recoveryTemplate;
        history.replaceState({}, '', `/desktop/meetings/${meetingId}`);
        document.title = 'Synthetic old meeting';
        window.delayedProblemReadStarted = false;
        const problem = new Promise((resolve, reject) => {
          window.finishDelayedProblemRead = () => mode === 'json'
            ? resolve({code:'access_denied'}) : reject(new Error('Synthetic body read failure'));
        });
        const response = {status:403, redirected:false, headers:new Headers(), clone:() => ({json:() => {
          window.delayedProblemReadStarted = true;
          return problem;
        }})};
        window.delayedRecovery = window.recoverDetailTest(response).then(consumed => {
          if (!consumed) document.querySelector('main').dataset.staleCallerApplied = 'true';
          return consumed;
        });
      }, {markup:html('unavailable', 'storage_capacity_exceeded'), recoveryTemplate, meetingId, mode});
      assert.equal(await page.evaluate(() => window.delayedProblemReadStarted),true,'the old response is suspended in clone().json()');
      await page.evaluate(({markup, nextMeetingId, reuseDetail}) => {
        if (reuseDetail) document.querySelector('main').dataset.meetingId = nextMeetingId;
        else document.querySelector('main').replaceWith(new DOMParser().parseFromString(markup, 'text/html').querySelector('main'));
        history.replaceState({}, '', `/desktop/meetings/${nextMeetingId}`);
        document.title = 'Synthetic new meeting';
        window.newMeetingDetail = document.querySelector('main');
        window.finishDelayedProblemRead();
      }, {markup:html('unavailable', 'storage_capacity_exceeded', nextMeetingId), nextMeetingId, reuseDetail});
      assert.equal(await page.evaluate(() => window.delayedRecovery),true,`${label}: discarded recovery consumes the stale response`);
      assert.equal(new URL(page.url()).pathname, `/desktop/meetings/${nextMeetingId}`, `${label}: old 403 must retain the new private detail route`);
      assert.equal(await page.title(), 'Synthetic new meeting', `${label}: old 403 must retain the new title`);
      assert.equal(await page.evaluate(() => window.newMeetingDetail === document.querySelector('main') && window.newMeetingDetail.isConnected),true,`${label}: the new meeting remains connected`);
      assert.equal(await page.locator('[data-stale-caller-applied]').count(),0,`${label}: the caller must not apply a discarded response`);
    }
    // A current denial still clears its own meeting and private URL.
    assert.equal(await page.evaluate(() => window.recoverDetailTest({status:403, redirected:false, headers:new Headers(), clone:() => ({json:async () => ({code:'access_denied'})})})),true);
    assert.equal(new URL(page.url()).pathname,'/desktop/meetings','current denial still neutralizes its own private route');
    assert.equal(await page.locator('main[data-meeting-id]').count(),0,'current denial still removes private meeting detail');
    // The same denial through an active real poll must still enforce access.
    await page.evaluate(({markup, recoveryTemplate, meetingId}) => {
      document.body.innerHTML = markup + recoveryTemplate;
      history.replaceState({}, '', `/desktop/meetings/${meetingId}`);
    }, {markup:html('unavailable', 'storage_capacity_exceeded'), recoveryTemplate, meetingId});
    delayedPoll = {started:() => {},result:Promise.resolve({
      status:403,contentType:'application/json',body:JSON.stringify({code:'access_denied'}),
    })};
    await page.evaluate(() => window.refreshLocalPlaybackTest());
    delayedPoll = null;
    assert.equal(new URL(page.url()).pathname,'/desktop/meetings','current poll denial still neutralizes its own private route');
    assert.equal(await page.locator('main[data-meeting-id]').count(),0,'current poll denial still removes private meeting detail');
    assert.deepEqual(errors,[]);
    console.log('detail local playback: production sibling, direct polling transitions, delayed fetch/body/navigation, identity, focus, access, deletion and fragment refresh PASS');
  } finally {await browser.close();}
})().catch(error => { console.error(error); process.exitCode = 1; });
