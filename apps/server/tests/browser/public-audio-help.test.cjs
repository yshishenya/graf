// Real rendered Help HTML and local production assets; external network is blocked.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../../src/twobrain_rec_server');
const fixtures = process.argv[2];
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({javaScriptEnabled: false});
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname !== 'graf-help.test') return route.abort();
      if (url.pathname.startsWith('/static/public/')) {
        const file = path.join(root, 'public/static/public', url.pathname.slice('/static/public/'.length));
        return route.fulfill({path: file});
      }
      if (url.pathname.startsWith('/static/cabinet/')) {
        const file = path.join(root, 'cabinet/static/cabinet', url.pathname.slice('/static/cabinet/'.length));
        if (fs.existsSync(file)) return route.fulfill({path: file});
        return route.abort();
      }
      const name = url.pathname === '/help' ? 'help' : url.pathname.startsWith('/help/') ? 'audio' : url.pathname === '/guides' ? 'hub' : 'guide';
      return route.fulfill({path: path.join(fixtures, name + '.html'), contentType: 'text/html'});
    });
    const page = await context.newPage();
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({width, height: 900});
      for (const url of ['/help', '/help/na-mac-slyshno-tolko-odnu-storonu', '/guides', '/guides/zapis-vstrechi-na-mac-bez-bota']) {
        await page.goto('http://graf-help.test' + url);
        await page.evaluate(() => document.fonts.ready);
        assert.equal(await page.locator('h1').count(), 1);
        assert.equal(await page.locator('.content-header-nav a[href="/help"]').isVisible(), true);
        for (const scale of [1, 2]) {
          await page.evaluate(({scale, help}) => {
            const selector = help ? 'h1,h2,h3,p,li,a,aside' : '.content-site-header a';
            const sizes = Array.from(document.querySelectorAll(selector), e => [e, parseFloat(getComputedStyle(e).fontSize)]);
            if (scale === 2) for (const [e, size] of sizes) e.style.fontSize = `${size * 2}px`;
          }, {scale, help: url.startsWith('/help')});
          const geometry = await page.evaluate(() => ({width: innerWidth, scroll: document.documentElement.scrollWidth}));
          assert.ok(geometry.scroll <= geometry.width + 1, `${url} width=${width} text=${scale} overflow=${geometry.scroll}`);
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
    console.log('public_audio_help_browser=pass widths=320,390,768,1440 text=100%,200% noJS keyboard');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
