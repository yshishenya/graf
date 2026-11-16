const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, webkit } = require(require.resolve('playwright', { paths: [process.env.GRAF_NODE_MODULES || process.cwd()] }));
const asset = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js');
const id = '00000000-0000-0000-0000-000000000010';
const nonce = '00000000-0000-0000-0000-000000000020';
const proof = 'synthetic.' + 'a'.repeat(64);
const renewed = 'synthetic.' + 'b'.repeat(64);
const body = `<p class="outcome-item-text" data-result-view-proof="${proof}">Синтетический результат</p>`;
let cases = 0;

(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch({ headless: true });
  const open = async ({ content = body, embedded = false, pathname, csrf = true, init = '', responses } = {}) => {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    const writes = [], errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('https://graf.test/**', async route => {
      const request = route.request();
      if (request.url().endsWith('/result-viewed')) {
        writes.push({ url: request.url(), method: request.method(), headers: request.headers(), body: request.postDataJSON() });
        const reply = await responses?.(writes.length) || { status: 'accepted' };
        return route.fulfill({ json: reply });
      }
      return route.fulfill({ contentType: 'text/html', body: `<meta charset="utf-8">${csrf ? '<meta name="csrf-token" content="synthetic-csrf">' : ''}
        <script>${init}</script><main id="cabinet-main" data-meeting-id="${id}" data-cabinet-embedded="${embedded}">${content}</main>` });
    });
    await page.goto('https://graf.test' + (pathname || `${embedded ? '/desktop' : ''}/meetings/${id}`));
    await page.bringToFront();
    await page.addScriptTag({ path: asset });
    return { page, writes, errors };
  };
  const settle = page => page.waitForTimeout(120);
  const count = async (fixture, expected) => {
    const until = Date.now() + 4000;
    while (fixture.writes.length < expected && Date.now() < until) await fixture.page.waitForTimeout(20);
    assert.equal(fixture.writes.length, expected);
    assert.deepEqual(fixture.errors, []);
  };
  const close = async fixture => { assert.deepEqual(fixture.errors, []); await fixture.page.close(); cases++; };
  try {
    // A rendered body needs no artificial click or reading timer, but sends only once.
    const visible = await open();
    await count(visible, 1);
    assert.deepEqual(visible.writes[0].body, { proof });
    assert.equal(visible.writes[0].method, 'POST');
    assert.equal(visible.writes[0].headers['x-csrf-token'], 'synthetic-csrf');
    assert.equal(visible.writes[0].url, `https://graf.test/meetings/${id}/result-viewed`);
    await visible.page.evaluate(() => {
      document.dispatchEvent(new Event('htmx:afterSwap'));
      window.dispatchEvent(new Event('resize'));
    });
    await settle(visible.page); assert.equal(visible.writes.length, 1); await close(visible);

    const hidden = [
      `<div hidden>${body}</div>`, `<div inert>${body}</div>`, `<div aria-hidden="true">${body}</div>`,
      `<div style="display:none">${body}</div>`, `<div style="visibility:hidden">${body}</div>`,
      `<div style="opacity:0">${body}</div>`, `<div style="content-visibility:hidden">${body}</div>`,
      `<details><summary>Видимый заголовок</summary>${body}</details>`,
      `<div style="position:absolute;top:2000px">${body}</div>`,
      `<div style="height:0;overflow:hidden">${body}</div>`,
      `<template>${body}</template>`,
      `<p class="outcome-item-text" style="width:0;height:0;overflow:hidden" data-result-view-proof="${proof}">текст</p>`,
      `<p class="outcome-item-text" data-result-view-proof="${proof}"> \n\t </p>`,
      `<h1 data-result-view-proof="${proof}">Заголовок</h1>`,
      `<article data-result-view-proof="${proof}"><p>Контейнер</p></article>`,
      body.replace(proof, 'invalid'), body.replace(proof, 'x'.repeat(1537)),
    ];
    for (const content of hidden) {
      const fixture = await open({ content });
      await settle(fixture.page); assert.equal(fixture.writes.length, 0, content); await close(fixture);
    }
    for (const init of [
      "Object.defineProperty(document,'visibilityState',{get:()=> 'hidden'})",
      "Object.defineProperty(document,'prerendering',{get:()=> true})",
      "document.hasFocus=()=>false",
    ]) {
      const fixture = await open({ init });
      await settle(fixture.page); assert.equal(fixture.writes.length, 0); await close(fixture);
    }
    for (const options of [{ csrf: false }, { pathname: '/shared-meetings/' + id }, { embedded: true }]) {
      const fixture = await open(options);
      await settle(fixture.page); assert.equal(fixture.writes.length, 0); await close(fixture);
    }

    const ready = await open({ content: '<p>Результат готовится</p>' });
    await settle(ready.page); assert.equal(ready.writes.length, 0);
    await ready.page.evaluate(html => {
      const root = document.getElementById('cabinet-main');
      root.innerHTML = '<section hidden>' + html + '</section>';
      document.dispatchEvent(new Event('htmx:afterSwap'));
    }, body);
    await settle(ready.page); assert.equal(ready.writes.length, 0);
    await ready.page.locator('section').evaluate(node => { node.hidden = false; });
    await count(ready, 1);
    await ready.page.evaluate(html => {
      document.getElementById('cabinet-main').innerHTML = html;
      document.dispatchEvent(new Event('htmx:afterSwap'));
    }, body.replace(proof, renewed));
    await count(ready, 2); assert.deepEqual(ready.writes[1].body, { proof: renewed }); await close(ready);

    const failure = await open({ responses: () => ({ status: 'unavailable' }) });
    await count(failure, 1); await settle(failure.page);
    await failure.page.evaluate(() => {
      document.dispatchEvent(new Event('htmx:afterSwap'));
      window.dispatchEvent(new Event('resize'));
    });
    await settle(failure.page); assert.equal(failure.writes.length, 1);
    await failure.page.locator('main').evaluate(node => { node.hidden = true; });
    await settle(failure.page);
    await failure.page.locator('main').evaluate(node => { node.hidden = false; });
    await count(failure, 2); await close(failure);

    const renewal = await open({ responses: index => ({ status: 'renewed', proof: index === 1 ? renewed : proof }) });
    await count(renewal, 2); await settle(renewal.page);
    assert.deepEqual(renewal.writes.map(item => item.body), [{ proof }, { proof: renewed }]);
    assert.equal(renewal.writes.length, 2, 'at most one renewal in one visibility transition');
    await close(renewal);

    let releaseReply;
    const delayedReply = new Promise(resolve => { releaseReply = resolve; });
    const late = await open({ responses: async () => { await delayedReply; return { status: 'renewed', proof: renewed }; } });
    await count(late, 1);
    await late.page.locator('[data-result-view-proof]').evaluate(node => node.remove());
    releaseReply(); await settle(late.page);
    assert.equal(late.writes.length, 1, 'late reply cannot renew a detached body'); await close(late);

    // Actual geometry/focus remains in the browser; only the native reply is synthetic here.
    const nativeInit = `window.nativeCalls=[];window.nativePending=[];window.webkit={messageHandlers:{grafResultVisibility:{postMessage(message){nativeCalls.push(message);return new Promise(resolve=>nativePending.push(resolve));}}}}`;
    const native = await open({ embedded: true, init: nativeInit });
    await native.page.evaluate(value => GRAFResultVisibility.connect(value), nonce);
    await native.page.waitForFunction(() => nativePending.length > 0);
    await native.page.evaluate(() => { nativePending.splice(0).forEach(resolve => resolve({ version: 1, ready: true })); });
    await native.page.waitForFunction(() => nativePending.length > 0);
    await native.page.locator('[data-result-view-proof]').evaluate(node => node.remove());
    await native.page.evaluate(() => { nativePending.splice(0).forEach(resolve => resolve({ version: 1, ready: true })); });
    await settle(native.page); assert.equal(native.writes.length, 0, 'detached while native reply pending');
    await native.page.evaluate(html => { document.querySelector('main').innerHTML = html; }, body);
    await native.page.waitForFunction(() => nativePending.length > 0);
    await native.page.evaluate(() => { nativePending.splice(0).forEach(resolve => resolve({ version: 1, ready: false })); });
    await settle(native.page); assert.equal(native.writes.length, 0, 'inactive native surface');
    await native.page.evaluate(() => { GRAFResultVisibility.refresh(); });
    await native.page.waitForFunction(() => nativePending.length > 0);
    await native.page.evaluate(() => { nativePending.splice(0).forEach(resolve => resolve({ version: 1, ready: true })); });
    await native.page.waitForFunction(() => nativePending.length > 0);
    await native.page.evaluate(() => { nativePending.splice(0).forEach(resolve => resolve({ version: 1, ready: true })); });
    await count(native, 1);
    assert.equal(native.writes[0].url, `https://graf.test/desktop/meetings/${id}/result-viewed`);
    assert.deepEqual(await native.page.evaluate(() => nativeCalls[0]), { version: 1, nonce });
    await close(native);

    const continuous = await open({ embedded: true, responses: () => ({ status: 'unavailable' }),
      init: 'window.webkit={messageHandlers:{grafResultVisibility:{postMessage:async()=>({version:1,ready:true})}}}' });
    await continuous.page.evaluate(value => GRAFResultVisibility.connect(value), nonce);
    await count(continuous, 1); await settle(continuous.page);
    await continuous.page.evaluate(() => {
      GRAFResultVisibility.refresh();
      GRAFResultVisibility.connect('00000000-0000-0000-0000-000000000021');
      document.querySelector('meta[name="csrf-token"]').content = 'fresh-synthetic-csrf';
      history.replaceState(null, '', location.pathname + '?summary_format=synthetic');
    });
    await settle(continuous.page); assert.equal(continuous.writes.length, 1, 'refresh/nonce is not a real new showing');
    await continuous.page.locator('main').evaluate(node => { node.hidden = true; }); await settle(continuous.page);
    await continuous.page.locator('main').evaluate(node => { node.hidden = false; });
    await count(continuous, 2); await close(continuous);

    for (const interruption of ['csrf', 'root', 'nonce', 'focus', 'proof', 'pagehide']) {
      const fixture = await open({ embedded: true, init: nativeInit });
      await fixture.page.evaluate(value => GRAFResultVisibility.connect(value), nonce);
      await fixture.page.waitForFunction(() => nativePending.length > 0);
      await fixture.page.evaluate(() => { nativePending.splice(0).forEach(resolve => resolve({ version: 1, ready: true })); });
      await fixture.page.waitForFunction(() => nativePending.length > 0);
      await fixture.page.evaluate(what => {
        if (what === 'csrf') document.querySelector('meta[name="csrf-token"]').content = 'different';
        if (what === 'root') document.querySelector('main').outerHTML = '<main></main>';
        if (what === 'nonce') GRAFResultVisibility.disconnect();
        if (what === 'focus') { document.hasFocus = () => false; window.dispatchEvent(new Event('blur')); }
        if (what === 'proof') document.querySelector('[data-result-view-proof]').dataset.resultViewProof = '';
        if (what === 'pagehide') window.dispatchEvent(new Event('pagehide'));
        nativePending.splice(0).forEach(resolve => resolve({ version: 1, ready: true }));
      }, interruption);
      await settle(fixture.page); assert.equal(fixture.writes.length, 0, interruption); await close(fixture);
    }
    console.log(`PASS: ${cases} result visibility scenarios; only synthetic own requests, no runtime admission`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
