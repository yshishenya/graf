// Real rendered guides/Help HTML and local production assets; external network is blocked.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../../src/twobrain_rec_server');
const fixtures = process.argv[2];
const pages = JSON.parse(fs.readFileSync(path.join(fixtures, 'pages.json'), 'utf8'));
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({javaScriptEnabled: false});
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname !== 'graf-help.test') return route.abort();
      if (url.pathname.startsWith('/static/public/')) {
        const file = path.join(root, 'public/static/public', url.pathname.slice('/static/public/'.length));
        const range = /^bytes=(\d+)-(\d*)$/.exec(route.request().headers().range || '');
        if (file.endsWith('.mp4') && range) {
          const data = fs.readFileSync(file), start = Number(range[1]), end = Math.min(Number(range[2] || data.length - 1), data.length - 1);
          return route.fulfill({status: 206, contentType: 'video/mp4', body: data.subarray(start, end + 1), headers: {
            'Accept-Ranges': 'bytes', 'Content-Range': `bytes ${start}-${end}/${data.length}`,
          }});
        }
        return route.fulfill({path: file});
      }
      if (url.pathname.startsWith('/static/cabinet/')) {
        const file = path.join(root, 'cabinet/static/cabinet', url.pathname.slice('/static/cabinet/'.length));
        if (fs.existsSync(file)) return route.fulfill({path: file});
        return route.abort();
      }
      if (!Object.hasOwn(pages, url.pathname)) return route.abort();
      return route.fulfill({body: pages[url.pathname], contentType: 'text/html'});
    });
    const page = await context.newPage();
    let cases = 0;
    for (const width of [320, 360, 390, 768, 1440]) {
      await page.setViewportSize({width, height: 900});
      for (const url of Object.keys(pages)) {
        await page.goto('http://graf-help.test' + url);
        assert.ok(await page.evaluate(async () => {
          const fonts = await document.fonts.load('16px Onest', 'Руководства');
          await document.fonts.ready;
          return fonts.length > 0 && fonts.every(font => font.status === 'loaded');
        }), `${url} Onest must load`);
        assert.equal(await page.locator('h1').count(), 1);
        assert.equal(await page.locator('.content-header-nav a[href="/help"]').isVisible(), true);
        if (url === '/guides/protokol-vstrechi-iz-zapisi') {
          const video = await page.locator('video').boundingBox();
          assert.ok(video.width <= width && Math.abs(video.width / video.height - 9 / 16) < .01);
        }
        for (const scale of [1, 2]) {
          await page.evaluate(scale => {
            // Snapshot first: inherited sizes must not compound into 4x, 8x, ...
            const sizes = Array.from(document.querySelectorAll('body,body *'))
              .filter(e => e instanceof HTMLElement)
              .map(e => [e, parseFloat(getComputedStyle(e).fontSize)]);
            if (scale === 2) for (const [e, size] of sizes) e.style.fontSize = `${size * 2}px`;
          }, scale);
          const geometry = await page.evaluate(() => {
            const clipped = [];
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            while (walker.nextNode()) {
              const node = walker.currentNode;
              if (!node.textContent.trim() || node.parentElement.closest('.skip-link,svg,script,style')) continue;
              const card = node.parentElement.closest('.guide-card');
              const column = card || node.parentElement.closest('.guides-intro')?.firstElementChild;
              let left = 0, right = innerWidth;
              if (column) {
                const box = column.getBoundingClientRect(), css = getComputedStyle(column);
                left = Math.max(left, box.left + parseFloat(css.borderLeftWidth) + parseFloat(css.paddingLeft));
                right = Math.min(right, box.right - parseFloat(css.borderRightWidth) - parseFloat(css.paddingRight));
              }
              const range = document.createRange();
              range.selectNodeContents(node);
              if (Array.from(range.getClientRects()).some(rect => rect.width > 0 && (rect.left < left - 1 || rect.right > right + 1))) {
                clipped.push(node.textContent.trim());
              }
            }
            return {width: innerWidth, scroll: document.documentElement.scrollWidth, clipped};
          });
          assert.ok(geometry.scroll <= geometry.width + 1, `${url} width=${width} text=${scale} overflow=${geometry.scroll}`);
          assert.deepEqual(geometry.clipped, [], `${url} width=${width} text=${scale} clipped text`);
          cases++;
        }
        // Reload before checking keyboard and screenshots at normal size.
        await page.goto('http://graf-help.test' + url);
        await page.keyboard.press('Tab');
        assert.equal(await page.locator(':focus').getAttribute('href'), '#main');
        await page.keyboard.press('Enter');
        await page.waitForURL('**/*#main');
        assert.ok(page.url().endsWith('#main'));
        if (process.env.GRAF_HELP_SCREENSHOTS && url.startsWith('/help')) {
          await page.goto('http://graf-help.test' + url);
          await page.screenshot({path: path.join(process.env.GRAF_HELP_SCREENSHOTS, `${url === '/help' ? 'help' : 'audio'}-${width}.png`), fullPage: true});
          if (width === 390) await page.screenshot({path: path.join(process.env.GRAF_HELP_SCREENSHOTS, `${url === '/help' ? 'help' : 'audio'}-390-first.png`)});
        }
      }
    }
    const mediaRequests = [];
    page.on('request', request => { if (new URL(request.url()).pathname.endsWith('.mp4')) mediaRequests.push(request.url()); });
    await page.emulateMedia({reducedMotion: 'reduce'});
    await page.setViewportSize({width: 390, height: 900});
    await page.goto('http://graf-help.test/guides/protokol-vstrechi-iz-zapisi');
    const video = page.locator('video');
    await video.scrollIntoViewIfNeeded();
    await page.waitForLoadState('networkidle');
    assert.equal(mediaRequests.length, 0, 'MP4 must not load before Play, even when visible');
    for (let tabs = 0; tabs < 80 && !await video.evaluate(v => document.activeElement === v); tabs++) {
      await page.keyboard.press('Tab');
    }
    assert.ok(await video.evaluate(v => document.activeElement === v), 'native player is keyboard reachable');
    await video.scrollIntoViewIfNeeded();
    // Disabled page JavaScript also disables waitForFunction's page timers.
    const waitForMedia = async check => {
      for (let attempt = 0; attempt < 100; attempt++) {
        if (await video.evaluate(check)) return;
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      assert.fail(`Media condition timed out: ${check}`);
    };
    await page.keyboard.press('Space');
    await waitForMedia(v => {
      return v.currentTime > .1 && v.getVideoPlaybackQuality().totalVideoFrames > 0;
    });
    assert.ok(mediaRequests.length > 0);
    await page.keyboard.press('Space');
    await waitForMedia(v => v.paused);
    await video.evaluate(v => { v.textTracks[0].mode = 'hidden'; });
    await waitForMedia(v => v.textTracks[0].cues?.length === 6);
    const cues = await video.evaluate(v => Array.from(v.textTracks[0].cues, c => [c.startTime, c.endTime, c.text]));
    assert.deepEqual(cues.map(c => c.slice(0, 2)), [[0, 8], [8, 20], [20, 34], [34, 48], [48, 62], [62, 72]]);
    assert.match(cues[2][2], /не назван утверждённым/);
    assert.match(cues[3][2], /Отсутствующий срок нужно уточнить/);
    assert.match(cues[4][2], /Процент точности не измерялся/);
    assert.match(cues[5][2], /а не отзыв клиента/);
    assert.equal(await video.evaluate(v => v.duration), 72);
    await video.evaluate(v => { v.currentTime = 65; });
    await waitForMedia(v => {
      return !v.seeking && v.readyState >= 2 && Math.abs(v.currentTime - 65) < .1;
    });
    console.log('public_protocol_video=pass no-preload keyboard-play decoded seek captions=6 noJS');
    console.log(`public_audio_help_browser=pass cases=${cases} widths=320,360,390,768,1440 text=100%,200% noJS keyboard`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
