const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, webkit } = require('playwright');
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
const publicAssets = path.join(__dirname, '../../src/twobrain_rec_server/public/static/public');
const adminAssets = path.join(__dirname, '../../src/twobrain_rec_server/admin/static/admin');
const pages = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const adminPage = fs.readFileSync(process.argv[3], 'utf8');
const visualDirectory = process.env.BILLING_VISUAL_OUTPUT_DIR;
if (visualDirectory) {
  fs.mkdirSync(visualDirectory, { recursive: true });
  fs.copyFileSync(process.argv[2], path.join(visualDirectory, 'pages.json'));
}

async function checkTextContrast(page, label) {
  const failures = await page.evaluate(() => {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const rgba = color => {
      ctx.clearRect(0, 0, 1, 1);
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, 1, 1);
      return [...ctx.getImageData(0, 0, 1, 1).data].map((v, i) => i === 3 ? v / 255 : v);
    };
    const composite = (a, b) => [0, 1, 2].map(i => a[i] * a[3] + b[i] * (1 - a[3]));
    const luminance = color => color.map(v => v / 255)
      .map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
      .reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
    const issues = [];
    for (const element of document.querySelectorAll('main *')) {
      if (!element.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }) ||
          element.matches(':disabled, option') ||
          ![...element.childNodes].some(node => node.nodeType === 3 && node.textContent.trim())) continue;
      const ancestors = [];
      for (let node = element; node; node = node.parentElement) ancestors.unshift(node);
      let background = [255, 255, 255];
      for (const node of ancestors) background = composite(rgba(getComputedStyle(node).backgroundColor), background);
      const style = getComputedStyle(element);
      const light = [luminance(composite(rgba(style.color), background)), luminance(background)].sort((a, b) => b - a);
      const contrast = (light[0] + 0.05) / (light[1] + 0.05);
      const large = parseFloat(style.fontSize) >= 24 || (parseFloat(style.fontSize) >= 18.667 && Number(style.fontWeight) >= 700);
      if (contrast < (large ? 3 : 4.5) - 0.01) issues.push(`${contrast.toFixed(2)}: ${element.textContent.trim()}`);
    }
    return issues;
  });
  assert.deepEqual(failures, [], `${label}: text contrast`);
}

async function checkCopyEnhancement(browser, tabKey) {
  for (const [name, expected, sourceSelector] of [
    ['invoice-future', 'INV-SYNTHETIC', 'details dd'],
    ['history', 'support@example.test', 'a[href="mailto:support@example.test"]'],
    ['referrals', 'https://graf.test/r/synthetic', '#referral-link'],
    ['fair-use', 'FU-SYNTHETIC', '#fair-use-support-synthetic'],
  ]) {
    for (const javaScriptEnabled of [false, true]) {
      const page = await browser.newPage({ javaScriptEnabled });
      page.setDefaultTimeout(5000);
      const requests = [];
      await page.route('https://graf.test/**', route => {
        requests.push(route.request().method());
        return route.fulfill({ contentType: 'text/html; charset=utf-8',
          body: `<html lang="ru"><meta charset="utf-8"><style>${fs.readFileSync(path.join(assets, 'cabinet.css'), 'utf8')}</style><body data-surface-mode="standalone_browser">${pages[name]}</body></html>` });
      });
      await page.goto('https://graf.test/billing');
      const copy = page.locator('[data-copy-value], [data-copy-target]');
      assert.equal(await copy.count(), 1, `${name}: existing copy caller exercised`);
      assert.equal(await copy.getAttribute('hidden'), '', `${name}: HTML hides the unbound action`);
      if (name === 'invoice-future') await page.locator('summary', { hasText: 'Сведения о платеже' }).click();
      const source = page.locator(sourceSelector).filter({ hasText: name === 'referrals' ? undefined : expected }).first();
      assert(await source.isVisible(), `${name}: manual copy source visible`);
      assert.equal(await source.evaluate(el => {
        if (el instanceof HTMLInputElement) { el.select(); return el.value.slice(el.selectionStart, el.selectionEnd); }
        const range = document.createRange(); range.selectNodeContents(el);
        const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
        return selection.toString();
      }), expected, `${name}: original value remains selectable`);
      if (!javaScriptEnabled) {
        assert.equal(await copy.isVisible(), false, `${name}: no dead copy button without JS`);
        // Even an explicit focus attempt cannot enter a hidden action.
        await copy.evaluate(el => el.focus());
        assert.equal(await copy.evaluate(el => el === document.activeElement), false);
        await page.keyboard.press(tabKey);
        assert.equal(await copy.evaluate(el => el === document.activeElement), false, `${name}: no dead tab stop`);
      } else {
        await page.addScriptTag({ path: path.join(assets, 'cabinet.js') });
        assert(await copy.isVisible(), `${name}: bound copy action visible`);
        await copy.focus();
        await page.evaluate(() => {
          document.body.dispatchEvent(new CustomEvent('htmx:afterSwap'));
          document.body.dispatchEvent(new CustomEvent('htmx:afterSwap'));
        });
        assert(await copy.evaluate(el => el === document.activeElement), `${name}: re-init preserves focus`);
        for (const mode of ['clipboard', 'fallback', 'failure']) {
          await page.evaluate(mode => {
            window.copyAttempts = []; window.fallbackValues = [];
            Object.defineProperty(navigator, 'clipboard', { configurable: true,
              value: { writeText: async value => {
                window.copyAttempts.push(value);
                if (mode !== 'clipboard') throw new DOMException('Denied', 'NotAllowedError');
              } } });
            document.execCommand = command => {
              if (command !== 'copy') throw new Error('Unexpected clipboard command');
              window.fallbackValues.push(document.activeElement.value);
              return mode === 'fallback';
            };
            const status = document.querySelector('[data-copy-status]');
            if (status) status.textContent = '';
          }, mode);
          await copy.focus();
          await page.keyboard.press('Enter');
          const message = mode === 'failure' ? 'Не удалось скопировать. Выделите текст вручную.' : 'Скопировано.';
          await page.waitForFunction(message => document.querySelector('[data-copy-status]')?.textContent === message, message);
          assert.deepEqual(await page.evaluate(() => window.copyAttempts), [expected], `${name}: one bound handler after repeated init`);
          assert.deepEqual(await page.evaluate(() => window.fallbackValues), mode === 'clipboard' ? [] : [expected], `${name}: native fallback receives the safe value`);
          assert.equal(await page.locator('[data-copy-status]').getAttribute('role'), 'status');
          assert.equal(await page.locator('[data-copy-status]').getAttribute('aria-live'), 'polite');
          assert(await copy.evaluate(el => el === document.activeElement), `${name}: ${mode} preserves keyboard focus`);
          assert(await source.isVisible(), `${name}: manual source survives ${mode}`);
        }
      }
      assert.deepEqual(requests, ['GET'], `${name}: local copying sends no request`);
      await page.close();
    }
  }
  console.log('copy: four callers, NoJS selection/tab order, JS success/fallback/failure, focus and repeated init passed');
}

async function checkAdminNavigation(browser, tabKey) {
  for (const width of [320, 360, 980, 1280]) for (const theme of ['light', 'dark']) {
    for (const javaScriptEnabled of [false, true]) {
      const label = `admin: ${width}px, ${theme}, JS=${javaScriptEnabled}`;
      const page = await browser.newPage({ javaScriptEnabled, viewport: { width, height: 900 } });
      page.setDefaultTimeout(5000);
      const documents = [];
      const styles = new Set();
      await page.route('https://graf.test/**', route => {
        const request = route.request();
        if (request.resourceType() === 'document') {
          documents.push({ url: request.url(), method: request.method() });
          return route.fulfill({ contentType: 'text/html; charset=utf-8', body: adminPage });
        }
        const filename = path.basename(new URL(request.url()).pathname);
        const asset = [assets, adminAssets, publicAssets].map(dir => path.join(dir, filename))
          .find(file => fs.existsSync(file) && fs.statSync(file).isFile());
        if (request.resourceType() === 'stylesheet' && asset) styles.add(filename);
        return asset ? route.fulfill({ path: asset }) : route.fulfill({ status: 204 });
      });
      await page.goto('https://graf.test/admin');
      await page.evaluate(theme => { document.documentElement.dataset.theme = theme; }, theme);
      assert(styles.has('cabinet.css') && styles.has('admin.css'), `${label}: actual shared and admin styles loaded`);
      assert.equal(await page.locator('[data-cabinet-shell], html[data-cabinet-js], script[src*="cabinet.js"]').count(), 0,
        `${label}: admin does not use cabinet readiness or initialization`);
      assert(await page.locator('[data-admin-shell] > .sidebar').isVisible(), `${label}: admin sidebar visible`);
      const links = page.getByRole('navigation', { name: 'Админ-навигация', exact: true }).getByRole('link');
      assert.equal(await links.count(), 7, `${label}: all real admin links available`);
      for (const link of await links.all()) {
        assert(await link.isVisible(), `${label}: admin link visible`);
        for (let index = 0; index < 20 && !await link.evaluate(el => el === document.activeElement); index++) {
          await page.keyboard.press(tabKey);
        }
        assert(await link.evaluate(el => el === document.activeElement), `${label}: keyboard reaches each admin link`);
        assert(await link.evaluate(el => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return rect.left >= 0 && rect.right <= innerWidth && rect.top >= 0 && rect.bottom <= innerHeight &&
            style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0 &&
            el.contains(document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2));
        }), `${label}: focused admin link is visible, unobscured and fits viewport`);
      }
      const users = page.getByRole('link', { name: 'Пользователи', exact: true });
      for (let index = 0; index < 20 && !await users.evaluate(el => el === document.activeElement); index++) {
        await page.keyboard.press(tabKey);
      }
      assert(await users.evaluate(el => el === document.activeElement), `${label}: keyboard reaches users navigation`);
      await Promise.all([page.waitForURL('https://graf.test/admin/users'), page.keyboard.press('Enter')]);
      assert.deepEqual(documents, [
        { url: 'https://graf.test/admin', method: 'GET' },
        { url: 'https://graf.test/admin/users', method: 'GET' },
      ], `${label}: one native keyboard navigation without mutation`);
      assert(await page.locator('[data-admin-shell] > .sidebar').isVisible(), `${label}: admin shell survives navigation`);
      await page.close();
    }
  }
  console.log('admin: 16 real-base cases, 320/360/980/1280, both themes, JS/NoJS, seven links and keyboard navigation passed');
}

async function checkPeriodReflow(browser, tabKey) {
  for (const name of ['shell-checkout', 'shell-checkout-first-annual', 'shell-checkout-discount', 'shell-plans']) {
    for (const width of [320, 360, 1280]) for (const theme of ['light', 'dark']) {
      for (const zoom of [2, 1]) for (const javaScriptEnabled of [false, true]) {
        const label = `${name} period: ${width}px, ${theme}, ${zoom * 100}%, JS=${javaScriptEnabled}`;
        const page = await browser.newPage({ javaScriptEnabled, viewport: { width, height: 900 } });
        page.setDefaultTimeout(5000);
        await page.route('https://graf.test/**', route => {
          if (route.request().resourceType() === 'document') {
            return route.fulfill({ contentType: 'text/html; charset=utf-8', body: pages[name] });
          }
          const filename = path.basename(new URL(route.request().url()).pathname);
          const asset = [assets, publicAssets].map(dir => path.join(dir, filename))
            .find(file => fs.existsSync(file) && fs.statSync(file).isFile());
          return asset ? route.fulfill({ path: asset }) : route.fulfill({ status: 204 });
        });
        await page.goto('https://graf.test/billing');
        await page.evaluate(({ theme, zoom }) => {
          document.documentElement.dataset.theme = theme;
          document.body.style.zoom = String(zoom);
        }, { theme, zoom });
        const controls = page.locator('.billing-period-switch :is(a, button)');
        assert.equal(await controls.count(), 2, `${label}: both existing period controls present`);
        if (name !== 'shell-plans') {
          assert.equal(await controls.locator('small').textContent(), 'Экономия 2 000 ₽ (17%)',
            `${label}: actual annual-saving fixture is exercised`);
        }
        const focusFailures = [];
        for (const control of await controls.all()) {
          for (let index = 0; index < 90 && !await control.evaluate(el => el === document.activeElement); index++) {
            await page.keyboard.press(tabKey);
          }
          assert(await control.evaluate(el => el === document.activeElement), `${label}: keyboard reaches period`);
          const bounds = await control.evaluate(el => {
            const rect = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            const lines = [];
            while (walker.nextNode()) {
              if (!walker.currentNode.textContent.trim()) continue;
              const range = document.createRange();
              range.selectNodeContents(walker.currentNode);
              lines.push(...[...range.getClientRects()].map(line => ({
                left: line.left, right: line.right, top: line.top, bottom: line.bottom,
              })));
            }
            return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, lines,
              outline: style.outlineStyle, outlineWidth: parseFloat(style.outlineWidth),
              exposed: el.contains(document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)) };
          });
          assert(bounds.left >= -1 && bounds.right <= width + 1 && bounds.top >= -1 && bounds.bottom <= 901,
            `${label}: focused period fits viewport ${JSON.stringify(bounds)}`);
          assert(bounds.lines.length && bounds.lines.every(line => line.left >= bounds.left - 1
            && line.right <= bounds.right + 1 && line.left >= -1 && line.right <= width + 1
            && line.top >= bounds.top - 1 && line.bottom <= bounds.bottom + 1),
          `${label}: every period text line fits control and viewport ${JSON.stringify(bounds)}`);
          if (!bounds.exposed || bounds.outline === 'none' || bounds.outlineWidth <= 0) focusFailures.push(bounds);
        }
        assert.deepEqual(focusFailures, [], `${label}: period focus is visible and unobscured`);
        if (name !== 'shell-plans') {
          const amount = name === 'shell-checkout-first-annual' ? '10 000 ₽'
            : name === 'shell-checkout-discount' ? '711 ₽' : '1 000 ₽';
          assert.equal(await page.locator('.billing-order-summary__total dd').textContent(), amount,
            `${label}: real payable amount is exercised`);
          const submit = page.getByRole('button', { name: `Оплатить ${amount} в ЮKassa`, exact: true });
          for (let index = 0; index < 90 && !await submit.evaluate(el => el === document.activeElement); index++) {
            await page.keyboard.press(tabKey);
          }
          assert(await submit.evaluate(el => el === document.activeElement), `${label}: keyboard reaches pay action`);
          const bounds = await submit.evaluate((el, amount) => {
            const rect = el.getBoundingClientRect(), style = getComputedStyle(el);
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            const lines = [], characters = [];
            while (walker.nextNode()) {
              const node = walker.currentNode, range = document.createRange();
              range.selectNodeContents(node);
              lines.push(...[...range.getClientRects()].map(r => ({ left: r.left, right: r.right, top: r.top, bottom: r.bottom })));
              for (let i = 0; i < node.length; i++) {
                range.setStart(node, i); range.setEnd(node, i + 1);
                const r = range.getBoundingClientRect();
                characters.push({ value: node.textContent[i], top: r.top, bottom: r.bottom, left: r.left, right: r.right });
              }
            }
            const start = el.textContent.indexOf(amount);
            return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, lines,
              amount: characters.slice(start, start + amount.length).filter(c => c.value.trim()),
              outline: style.outlineStyle, outlineWidth: parseFloat(style.outlineWidth),
              exposed: el.contains(document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)) };
          }, amount);
          assert(bounds.amount.length && bounds.amount.every(c => Math.abs(c.top - bounds.amount[0].top) <= 1),
            `${label}: monetary amount stays on one line ${JSON.stringify(bounds)}`);
          assert(bounds.left >= -1 && bounds.right <= width + 1 && bounds.top >= -1 && bounds.bottom <= 901,
            `${label}: pay action fits viewport ${JSON.stringify(bounds)}`);
          assert(bounds.lines.length && bounds.lines.every(line => line.left >= bounds.left - 1
            && line.right <= bounds.right + 1 && line.left >= -1 && line.right <= width + 1
            && line.top >= bounds.top - 1 && line.bottom <= bounds.bottom + 1),
          `${label}: every pay text line fits action and viewport ${JSON.stringify(bounds)}`);
          assert(bounds.exposed && bounds.outline !== 'none' && bounds.outlineWidth > 0,
            `${label}: pay focus is visible and unobscured`);
          if (visualDirectory && [320, 360].includes(width) && zoom === 2) {
            await page.screenshot({ path: path.join(visualDirectory, `${name}-pay-${width}-${theme}-200-js${javaScriptEnabled}.png`) });
          }
        }
        if (visualDirectory && [320, 360].includes(width) && zoom === 2) {
          await page.screenshot({ path: path.join(visualDirectory, `${name}-period-${width}-${theme}-200-js${javaScriptEnabled}.png`) });
        }
        await page.close();
      }
    }
  }
  console.log('period: 96 full-shell cases, checkout month/year/discount buttons and plan links; 72 atomic payable amount cases; JS/NoJS, 320/360/1280, both themes, 100/200%, keyboard and every text line passed');
}

async function checkRenewalTimingReflow(browser) {
  const explanation = 'Первая попытка списания планируется за 3 дня до конца оплаченного срока.';
  for (const name of ['shell-subscription', 'shell-overview-renewal']) {
    for (const width of [320, 360, 1280]) for (const theme of ['light', 'dark']) {
      for (const zoom of [2, 1]) for (const javaScriptEnabled of [false, true]) {
        const label = `${name} renewal timing: ${width}px, ${theme}, ${zoom * 100}%, JS=${javaScriptEnabled}`;
        const page = await browser.newPage({ javaScriptEnabled, viewport: { width, height: 900 } });
        await page.route('https://graf.test/**', route => {
          if (route.request().resourceType() === 'document') {
            return route.fulfill({ contentType: 'text/html; charset=utf-8', body: pages[name] });
          }
          const filename = path.basename(new URL(route.request().url()).pathname);
          const asset = [assets, publicAssets].map(dir => path.join(dir, filename))
            .find(file => fs.existsSync(file) && fs.statSync(file).isFile());
          return asset ? route.fulfill({ path: asset }) : route.fulfill({ status: 204 });
        });
        await page.goto('https://graf.test/billing');
        await page.evaluate(({ theme, zoom }) => {
          document.documentElement.dataset.theme = theme;
          document.body.style.zoom = String(zoom);
        }, { theme, zoom });
        const copy = page.getByText(explanation, { exact: true });
        assert.equal(await copy.count(), 1, `${label}: one ordinary first-attempt explanation`);
        assert(await copy.isVisible(), `${label}: explanation visible without expanding details`);
        const lines = await copy.evaluate(el => {
          const range = document.createRange();
          range.selectNodeContents(el);
          return [...range.getClientRects()].map(rect => ({ left: rect.left, right: rect.right }));
        });
        assert(lines.length && lines.every(line => line.left >= -1 && line.right <= width + 1),
          `${label}: complete explanation fits viewport ${JSON.stringify(lines)}`);
        if (visualDirectory && [320, 360].includes(width) && zoom === 2) {
          await copy.scrollIntoViewIfNeeded();
          await page.screenshot({ path: path.join(visualDirectory, `${name}-renewal-${width}-${theme}-200-js${javaScriptEnabled}.png`) });
        }
        await page.close();
      }
    }
  }
  for (const name of Object.keys(pages).filter(name => /^shell-(overview|subscription)-missed-/.test(name))) {
    for (const theme of ['light', 'dark']) for (const javaScriptEnabled of [false, true]) {
      const page = await browser.newPage({ javaScriptEnabled, viewport: { width: 360, height: 900 } });
      await page.route('https://graf.test/**', route => {
        if (route.request().resourceType() === 'document') {
          return route.fulfill({ contentType: 'text/html; charset=utf-8', body: pages[name] });
        }
        const filename = path.basename(new URL(route.request().url()).pathname);
        const asset = [assets, publicAssets].map(dir => path.join(dir, filename))
          .find(file => fs.existsSync(file) && fs.statSync(file).isFile());
        return asset ? route.fulfill({ path: asset }) : route.fulfill({ status: 204 });
      });
      await page.goto('https://graf.test/billing');
      await page.evaluate(theme => {
        document.documentElement.dataset.theme = theme;
        document.body.style.zoom = '2';
      }, theme);
      assert.equal(await page.getByText(explanation, { exact: true }).count(), 0,
        `${name}/${theme}/JS=${javaScriptEnabled}: missed window does not claim nominal first date`);
      const date = page.locator('p, dd').filter({ hasText: 'в ближайшее время' }).first();
      assert(await date.isVisible(), `${name}: existing next-charge label preserved`);
      if (visualDirectory && name.endsWith('-60')) {
        await date.scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(visualDirectory, `${name}-${theme}-200-js${javaScriptEnabled}.png`) });
      }
      await page.close();
    }
  }
  console.log('renewal missed windows: 40 full-shell cases, both surfaces at72/60/48/24/12h,360px/200%,themes,JS/NoJS passed');
  console.log('renewal timing: 48 full-shell subscription/overview cases, JS/NoJS, 320/360/1280, both themes, 100/200%, complete visible explanation passed');
}

async function checkCancellationReflow(browser, tabKey) {
  for (const width of [320, 360, 1280]) for (const theme of ['light', 'dark']) {
    for (const zoom of [2, 1]) for (const javaScriptEnabled of [false, true]) {
      const label = `cancel: ${width}px, ${theme}, ${zoom * 100}%, JS=${javaScriptEnabled}`;
      const page = await browser.newPage({ javaScriptEnabled, viewport: { width, height: 900 } });
      page.setDefaultTimeout(5000);
      const posts = [];
      await page.route('https://graf.test/**', route => {
        const request = route.request();
        if (request.resourceType() !== 'document') {
          const filename = path.basename(new URL(request.url()).pathname);
          const asset = [assets, publicAssets].map(dir => path.join(dir, filename))
            .find(file => fs.existsSync(file) && fs.statSync(file).isFile());
          return asset ? route.fulfill({ path: asset }) : route.fulfill({ status: 204 });
        }
        if (request.method() === 'POST') posts.push(request);
        return route.fulfill({ contentType: 'text/html; charset=utf-8', body: request.method() === 'POST'
          ? '<meta charset="utf-8"><p>Синтетическая отправка принята</p>' : pages['shell-subscription'] });
      });
      await page.goto('https://graf.test/billing/subscription');
      await page.evaluate(({ theme, zoom }) => {
        document.documentElement.dataset.theme = theme;
        document.body.style.zoom = String(zoom);
      }, { theme, zoom });
      const cancel = page.getByRole('button', { name: 'Отключить автопродление', exact: true });
      for (let index = 0; index < 90 && !await cancel.evaluate(el => el === document.activeElement); index++) {
        await page.keyboard.press(tabKey);
      }
      assert(await cancel.evaluate(el => el === document.activeElement), `${label}: keyboard reaches cancellation`);
      const bounds = await cancel.evaluate(el => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom,
          outline: style.outlineStyle, outlineWidth: parseFloat(style.outlineWidth),
          exposed: document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2) === el };
      });
      assert(bounds.left >= -1 && bounds.right <= width + 1 && bounds.top >= -1 && bounds.bottom <= 901,
        `${label}: focused cancellation fits viewport ${JSON.stringify(bounds)}`);
      assert(bounds.exposed && bounds.outline !== 'none' && bounds.outlineWidth > 0, `${label}: focus visible and unobscured`);
      const buttonText = await cancel.evaluate(el => {
        const range = document.createRange();
        range.selectNodeContents(el);
        const rect = el.getBoundingClientRect();
        return { left: rect.left, right: rect.right, lines: [...range.getClientRects()]
          .map(line => ({ left: line.left, right: line.right })) };
      });
      assert(buttonText.lines.length && buttonText.lines.every(line => line.left >= buttonText.left - 1
        && line.right <= buttonText.right + 1 && line.left >= -1 && line.right <= width + 1),
      `${label}: cancellation label fits button and viewport ${JSON.stringify(buttonText)}`);
      const consequence = page.getByText('Оплаченный доступ сохранится. Возврат не оформляется.', { exact: true });
      assert(await consequence.isVisible(), `${label}: cancellation consequences visible`);
      // scrollWidth misses clipped grid tracks; check each rendered text line too.
      const lines = await consequence.evaluate(el => {
        const range = document.createRange();
        range.selectNodeContents(el);
        return [...range.getClientRects()].map(rect => ({ left: rect.left, right: rect.right }));
      });
      assert(lines.length && lines.every(rect => rect.left >= -1 && rect.right <= width + 1),
        `${label}: paid-access and refund text fits viewport ${JSON.stringify(lines)}`);
      if (visualDirectory && width === 320 && zoom === 2) {
        await page.screenshot({ path: path.join(visualDirectory, `cancel-320-${theme}-200-js${javaScriptEnabled}.png`) });
      }
      await Promise.all([
        page.waitForURL('https://graf.test/billing/subscription/cancel'),
        page.keyboard.press('Enter'),
      ]);
      assert.equal(posts.length, 1, `${label}: one native synthetic submit`);
      const fields = new URLSearchParams(posts[0].postData());
      assert.equal(fields.get('csrf_token'), 'synthetic');
      assert.equal(fields.get('expected_authority_version'), '1');
      await page.close();
    }
  }
  console.log('cancel: 24 full-shell keyboard/native-submit cases, JS/NoJS, 320/360/1280, both themes, 100/200% passed');
}

(async () => {
  const isWebKit = process.env.GRAF_BROWSER === 'webkit';
  const browser = await (isWebKit ? webkit : chromium).launch({ headless: true });
  // WebKit on macOS follows the system preference; Option-Tab reaches every control.
  const tabKey = isWebKit ? 'Alt+Tab' : 'Tab';
  try {
    await checkAdminNavigation(browser, tabKey);
    await checkPeriodReflow(browser, tabKey);
    await checkRenewalTimingReflow(browser);
    await checkCancellationReflow(browser, tabKey);
    await checkCopyEnhancement(browser, tabKey);
    for (const [name, html] of Object.entries(pages)) {
      const page = await browser.newPage();
      page.setDefaultTimeout(5000);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      const fullShell = name.startsWith('shell-');
      await page.route('https://graf.test/**', route => {
        if (route.request().resourceType() !== 'document') {
          const filename = path.basename(new URL(route.request().url()).pathname);
          const asset = [assets, publicAssets].map(dir => path.join(dir, filename)).find(file => fs.existsSync(file) && fs.statSync(file).isFile());
          return asset ? route.fulfill({ path: asset }) : route.fulfill({ status: 204 });
        }
        return route.fulfill({
          contentType: 'text/html; charset=utf-8', body: fullShell ? html : `<html lang="ru"><meta charset="utf-8"><body data-surface-mode="standalone_browser">${html}</body></html>`,
        });
      });
      await page.goto('https://graf.test/billing');
      if (!fullShell) {
        await page.addStyleTag({ path: path.join(assets, 'cabinet.css') });
        await page.addScriptTag({ path: path.join(assets, 'cabinet.js') });
      }
      for (const link of await page.locator('.billing-page a:not(.button):visible').all()) {
        assert(await link.evaluate(el => getComputedStyle(el).textDecorationLine.includes('underline')), `${name}: text link distinguishable`);
      }
      const target = await page.getByRole('alert').count()
        ? page.getByRole('alert').first() : page.getByRole('heading', { level: 1 });
      if (!['referrals', 'fair-use'].includes(name)) {
        assert(await target.evaluate(el => el === document.activeElement), `${name}: initial focus`);
      }
      await page.keyboard.press(tabKey);
      const focus = await page.evaluate(() => document.activeElement.outerHTML);
      assert(!focus.startsWith('<body'), `${name}: keyboard can leave initial focus`);
      await page.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap')));
      assert.equal(await page.evaluate(() => document.activeElement.outerHTML), focus, 're-init must not steal focus');
      if (name.startsWith('overview') || name.startsWith('shell-overview')) {
        const state = name.replace('shell-', '');
        const blocked = ['overview-pending', 'overview-expired-pending', 'overview-member', 'overview-unavailable'].includes(state);
        assert.equal(await page.locator('form[action="/billing/storage/preview"]').count(), blocked ? 0 : 1);
        assert.equal(await page.locator('main [data-billing-primary]').count(), state === 'overview-member' || state === 'overview-unavailable' ? 0 : 1);
        assert.equal(await page.getByRole('link', { name: 'INV-SYNTHETIC', exact: true }).count(), 0);
        if (!blocked) {
          const editor = page.locator('#billing-storage-editor');
          assert.equal(await editor.evaluate(el => el.open), ['overview-editor', 'overview-error'].includes(state));
          if (!await editor.evaluate(el => el.open)) {
            await editor.locator('summary').first().focus();
            await page.keyboard.press('Space');
          }
          const select = page.getByLabel('Общий объем хранения', { exact: true });
          assert(await select.isVisible());
          await select.selectOption('2');
          assert(await page.locator('#storage-package-summary').isVisible(), `${name}: selected price immediately visible`);
          assert.match(await page.locator('#storage-package-summary').innerText(), /5000 ₽ за год.*15000 ₽ за год/);
          const form = page.locator('form[action="/billing/storage/preview"]');
          assert.equal(await form.evaluate(el => new FormData(el).get('return_to')), 'overview');
          assert.equal(await form.locator('[name="purchase_consent"], [name="recurring_consent"]').count(), 0);
          if (state === 'overview-error') {
            assert.equal(await page.getByLabel('Промокод', { exact: true }).inputValue(), 'DEMO');
            assert.equal(await page.getByLabel('Промокод', { exact: true }).getAttribute('aria-invalid'), 'true');
          }
          // Restore initial collapsed state for honest default screenshots.
          if (!['overview-editor', 'overview-error'].includes(state)) await editor.locator('summary').first().click();
        }
      }
      if (name === 'packages') {
        await page.getByText('Условия и оплаченные периоды', { exact: true }).click();
        const select = page.getByLabel('Общий объем хранения', { exact: true });
        await page.getByRole('button', {name: 'Выбрать больший объем'}).click();
        assert.equal(await select.inputValue(), '2');
        assert.match(await page.locator('#storage-package-summary').innerText(), /Дополнительное место — 500 ₽ за месяц.*Вместе с тарифом — 1500 ₽ за месяц/);
        await select.selectOption('0');
        assert(await page.getByRole('button', {name: 'Выбрать меньший объем'}).isDisabled());
        await select.selectOption('99');
        assert(await page.getByRole('button', {name: 'Выбрать больший объем'}).isDisabled());
        assert.match(await page.locator('#storage-package-summary').innerText(), /Дополнительное место — 24750 ₽ за месяц.*Вместе с тарифом — 25750 ₽/);
        await select.selectOption('1');
        await page.getByRole('button', {name: 'Выбрать больший объем'}).focus();
        await page.keyboard.press('Space');
        assert.equal(await select.inputValue(), '2');
        const form = page.locator('form[action="/billing/storage/preview"]');
        assert.equal(await form.evaluate(el => new FormData(el).get('package_count')), '2');
        await select.selectOption('0');
        await select.locator('option[value="1"]').evaluate(el => el.remove());
        await page.getByRole('button', {name: 'Выбрать больший объем'}).click();
        assert.equal(await select.inputValue(), '2', 'skip unavailable catalog volume without promising a fixed step');
      }
      if (name === 'packages-timeline-year') {
        const periods = page.getByText('Условия и оплаченные периоды', { exact: true });
        assert.equal(await page.getByText('15.10.2026, 23:50', { exact: false }).isVisible(), false);
        assert(await page.getByText('Следующий неоплаченный период после', { exact: false }).isVisible());
        await periods.focus();
        await page.keyboard.press('Space');
        assert(await page.getByText('бонусный срок', { exact: false }).isVisible());
        assert.match(await page.locator('#storage-package-summary').innerText(), /2500 ₽ за год.*12500 ₽ за год/);
      }
      if (name.startsWith('usage-')) {
        assert.equal(await page.getByRole('progressbar').count(), name === 'usage-unavailable' ? 0 : 1);
        assert.equal(await page.getByText('35 мин 39 сек', { exact: false }).isVisible(), false);
        if (name !== 'usage-unavailable') {
          assert.equal(await page.locator('main .button.primary:visible').count(), 1);
          assert(await page.getByRole('link', { name: 'Увеличить хранилище', exact: true }).isVisible());
        }
      }
      if (name === 'checkout' || name === 'error') {
        assert.equal(await page.locator('details.billing-coupon').evaluate(el => el.open), false);
        const form = page.locator('form[action="/billing/checkout/start"]');
        assert.equal(await form.evaluate(el => el.checkValidity()), false, 'empty consent prevents payment');
        const consents = page.getByRole('checkbox');
        assert.equal(await consents.count(), 2);
        for (let index = 0; index < 2; index++) {
          assert.equal(await consents.nth(index).isChecked(), index === 1);
          assert.equal(await consents.nth(index).evaluate(el => el.required), index === 0);
          await consents.nth(index).focus();
          await page.keyboard.press('Space');
          assert.equal(await consents.nth(index).isChecked(), index === 0);
        }
        assert(await page.getByText('Отключено — автоматического списания не будет.', { exact: true }).isVisible());
        assert.equal(await page.locator('[data-billing-next-attempt]').isVisible(), false);
        await page.keyboard.press(tabKey);
        assert(await page.getByRole('button', { name: /^Оплатить/ }).evaluate(el => el === document.activeElement));
        await page.keyboard.press(isWebKit ? 'Shift+Alt+Tab' : 'Shift+Tab');
        assert(await consents.nth(1).evaluate(el => el === document.activeElement));
        assert(await form.evaluate(el => el.checkValidity()), 'accepted offer permits a one-period payment');
        assert.equal(await form.evaluate(el => new FormData(el).get('recurring_consent')), null);
      } else if (name.startsWith('status-')) {
        assert.equal(await page.getByRole('status').count(), 1, 'one payment status announcement region');
      } else if (name === 'invoice') {
        const help = page.locator('summary', { hasText: 'Помощь и возврат' });
        await help.focus();
        await page.keyboard.press('Space');
        assert(await page.getByText('Результат возврата уточняйте у поддержки:', { exact: false }).isVisible());
        assert(await page.getByRole('link', { name: 'Управлять автопродлением' }).isVisible());
      } else if (name === 'discounts-error') {
        const promo = page.getByRole('textbox', { name: 'Промокод', exact: true });
        assert.equal(await promo.inputValue(), 'DEMO');
        assert.equal(await promo.getAttribute('aria-invalid'), 'true');
        assert(await page.getByRole('alert').isVisible());
      } else if (name === 'subscription-expired-pending') {
        assert(await page.getByRole('button', { name: 'Отключить автопродление' }).isVisible());
        assert.equal(await page.getByRole('link', { name: 'Выбрать тариф' }).count(), 0);
        assert(await page.locator('a[href="/billing/checkout/status/INV-SYNTHETIC"]').isVisible());
      } else if (name === 'overview-expired-pending') {
        await page.locator('#billing-renewal-settings > summary').click();
        assert(await page.getByRole('button', { name: 'Отключить автопродление', exact: true }).isVisible());
        assert(await page.getByRole('link', { name: 'Проверить оплату', exact: true }).isVisible());
        assert.equal(await page.locator('main .button.primary:visible').count(), 1);
      } else if (name === 'subscription-prepared') {
        assert(!(await page.locator('main').innerText()).includes('Уже отправленный платеж'));
        const early = page.locator('summary', { hasText: 'Оплатить следующий период заранее' });
        await early.focus();
        await page.keyboard.press('Space');
        assert(await page.locator('form[action="/billing/subscription/early-preview"]').isVisible());
      } else if (['storage_upgrade', 'early_renewal', 'storage_schedule', 'storage-price-confirmation'].includes(name)) {
        const consent = page.getByRole('checkbox');
        assert.equal(await consent.count(), 1, 'one-time purchase must not imply recurring consent');
        assert.equal(await consent.isChecked(), false);
        await consent.focus();
        await page.keyboard.press('Space');
        assert(await consent.isChecked());
        assert(await page.getByRole('button', { name: /^(Оплатить|Сохранить выбор)/ }).isVisible());
      }
      if (name.startsWith('subscription') || name.startsWith('shell-subscription')) {
        const facts = page.locator('.billing-subscription-facts');
        for (const value of await facts.locator('dd:visible').all()) {
          assert.equal(await value.evaluate(el => getComputedStyle(el).marginInlineStart), '0px', `${name}: no browser-default dd indentation`);
        }
        if (name.includes('off-no-card')) {
          assert.equal(await page.getByText('Возобновление пока недоступно.', { exact: false }).count(), 0);
          assert.equal(await page.locator('main [data-billing-primary]:visible').count(), 1);
          const renew = page.getByRole('link', { name: 'Продлить подписку', exact: true });
          assert(await renew.isVisible());
          assert.equal(await renew.getAttribute('href'), '/billing/checkout?cycle=month');
          const conditions = page.locator('summary', { hasText: 'Способ оплаты, условия и история' });
          assert.equal(await conditions.locator('..').getAttribute('open'), null);
          assert.equal(await page.getByText('03.11.2026, 12:19 (UTC+03:00)', { exact: true }).isVisible(), false);
          await conditions.focus();
          await page.keyboard.press('Space');
          assert(await page.getByText('03.11.2026, 12:19 (UTC+03:00)', { exact: true }).isVisible());
          await page.keyboard.press('Space');
        }
        if (name.includes('off-ready')) {
          const disclosure = page.locator('summary', { hasText: 'Включить автопродление' });
          const form = page.locator('form[action="/billing/subscription/resume"]');
          assert.equal(await form.isVisible(), false);
          await disclosure.focus();
          await page.keyboard.press('Space');
          assert(await form.isVisible());
          const consent = form.getByRole('checkbox');
          assert.equal(await consent.isChecked(), false);
          assert.equal(await form.evaluate(el => el.checkValidity()), false);
          assert(await page.getByText('31.10.2026, 12:19 (UTC+03:00)', { exact: false }).isVisible());
          await consent.focus();
          await page.keyboard.press('Space');
          assert(await consent.isChecked());
          assert(await form.evaluate(el => el.checkValidity()));
          const serialized = await form.evaluate(el => Object.fromEntries(new FormData(el)));
          assert.equal(serialized.csrf_token, 'synthetic');
          assert.equal(serialized.expected_authority_version, '1');
          assert.equal(serialized.resume_quote_id, 'synthetic-resume');
          assert.equal(serialized.resume_consent, 'true');
          await disclosure.focus();
          await page.keyboard.press('Space');
        }
        if (name.includes('uncertain-')) {
          assert.equal(await page.locator('a[href="/billing/checkout?cycle=month"]').count(), 0);
          assert.equal(await page.locator('form[action="/billing/subscription/resume"], form[action="/billing/subscription/early-preview"]').count(), 0);
          assert(await page.getByRole('status').first().isVisible());
        }
        if (name === 'subscription-key-expired') {
          assert(await page.getByRole('link', { name: 'Продлить подписку', exact: true }).isVisible());
          assert(!(await page.locator('main').innerText()).includes('Повторно платить не нужно'));
        }
        if (name === 'subscription-ambiguous-payment' || name.includes('uncertain-')) {
          const text = await page.locator('main').innerText();
          assert(text.includes('Результат платежа'));
          assert(text.includes('еще может завершиться'));
          assert(!text.includes('Уже отправленный'));
          assert.equal(await page.locator('a[href="/billing/checkout?cycle=month"]').count(), 0);
          assert.equal(await page.locator('form[action="/billing/subscription/resume"], form[action="/billing/subscription/early-preview"]').count(), 0);
          if (name === 'subscription-ambiguous-payment') {
            const status = page.getByRole('link', { name: 'Проверить платеж', exact: true });
            assert(await status.isVisible());
            assert.equal(await status.getAttribute('href'), '/billing/checkout/status/INV-SYNTHETIC');
          }
        }
        if (name.startsWith('subscription-method-pending')) {
          const recovery = page.getByRole('link', { name: 'Проверить способ оплаты', exact: true });
          assert(await recovery.isVisible());
          assert.equal(await recovery.getAttribute('href'), '/billing/payment-method');
          await recovery.focus();
          assert(await recovery.evaluate(el => el === document.activeElement));
          assert(await page.getByRole('link', { name: 'Проверить платеж', exact: true }).isVisible());
          assert.equal(await page.locator('a[href="/billing/checkout?cycle=month"]').count(), 0);
          assert.equal(await page.locator('form[action="/billing/subscription/resume"], form[action="/billing/subscription/early-preview"]').count(), 0);
          assert(!(await page.locator('main').innerText()).includes('Уже отправленный'));
          if (name.endsWith('-on')) assert(await page.getByRole('button', { name: 'Отключить автопродление', exact: true }).isVisible());
        }
        if (name === 'subscription-trial') {
          assert(!(await page.locator('main').innerText()).includes('Сейчас действует бесплатный тариф'));
          assert(await page.getByText('03.11.2026', { exact: false }).first().isVisible());
        }
        const period = page.getByText('Период оплаты', { exact: true });
        if (['subscription-free', 'subscription-trial', 'subscription-expired', 'subscription-expired-pending', 'subscription-unknown-cycle'].includes(name)) {
          assert.equal(await period.count(), 0, 'inactive or unknown-cycle access must not invent a paid period');
          assert(!/за месяц|за год/.test(await page.locator('main').innerText()));
        } else if (name === 'subscription-year') {
          const conditions = page.locator('summary', { hasText: 'Способ оплаты, условия и история' });
          await conditions.focus();
          await page.keyboard.press('Space');
          assert.equal(await period.locator('..').locator('dd').innerText(), 'год');
          assert.match(await facts.innerText(), /за год/);
          assert.match(await page.getByText('Цена следующего периода', { exact: true }).locator('..').innerText(), /за год/);
          await page.keyboard.press('Space');
        }
        if (name.startsWith('subscription-restriction-')) {
          const reason = name.replace('subscription-restriction-', '');
          const mainText = await page.locator('main').innerText();
          const primary = page.locator('[data-billing-primary]');
          assert.equal(await primary.count(), 1);
          assert.equal(await primary.getAttribute('href'), '/billing/checkout/status/INV-SYNTHETIC');
          assert(!mainText.includes('Подтверждение оплаты получено'));
          assert.equal(await page.locator('a[href^="/billing/checkout?"], form[action="/billing/subscription/resume"], form[action="/billing/subscription/early-preview"]').count(), 0);
          if (reason === 'price_changed') {
            const recovery = page.getByRole('link', { name: 'Проверить новую цену', exact: true });
            assert(await recovery.isVisible());
            assert.equal(await recovery.getAttribute('href'), '/billing/storage');
            await recovery.focus();
            assert(await recovery.evaluate(el => el === document.activeElement));
          } else if (reason === 'receipt_contact_required') {
            assert(mainText.includes('нужен адрес для чека'));
            assert(!/Оплатите|Оплатить следующий период вручную/.test(mainText));
            assert(await page.locator('.notice a[href="/billing/history#billing-help"]').isVisible());
          } else if (reason !== 'late_success') {
            assert(mainText.includes('Автопродление приостановлено'));
          }
        }
      }
      if (name.includes('discounts')) {
        const promo = page.getByRole('textbox', { name: 'Промокод', exact: true });
        assert(await promo.isVisible());
        await promo.focus();
        assert(await promo.evaluate(el => el === document.activeElement));
        await page.keyboard.press(tabKey);
        assert(await page.getByRole('button', { name: 'Применить и проверить цену' }).evaluate(el => el === document.activeElement));
        assert.equal(await page.getByText('Действующие предложения', { exact: true }).count(), 0);
        if (name.includes('history-year')) assert.match(await page.locator('[aria-label="История скидок"]').innerText(), /Применён · Год/);
        if (name.includes('history-unknown')) {
          const history = await page.locator('[aria-label="История скидок"]').innerText();
          assert(history.includes('Скидка 10%') && history.includes('Применён'));
          assert(!/Год|Месяц|·/.test(history));
        }
      }
      if (name.includes('invoice-')) {
        assert(await page.getByText('03.11.2026 — 03.12.2026', { exact: true }).isVisible(), `${name}: compact paid period on view`);
        const exactPeriod = page.getByText('03.11.2026, 12:19 (UTC+03:00) — 03.12.2026, 12:19 (UTC+03:00)', { exact: true });
        const information = page.locator('summary', { hasText: 'Сведения о платеже' });
        assert.equal(await exactPeriod.isVisible(), false, `${name}: exact period is a secondary detail`);
        if (name.includes('service-gap')) {
          assert(await page.getByText('Оплата подтверждена; услуга требует сверки', { exact: false }).isVisible());
          assert.equal(await page.getByText('Оплата подтверждена; услуга требует сверки', { exact: false }).evaluate(el => Boolean(el.closest('details'))), false, 'service gap must not be hidden in disclosure');
        }
        await information.focus();
        await page.keyboard.press('Space');
        assert(await exactPeriod.isVisible(), `${name}: native keyboard disclosure reveals precise dates`);
        assert(await page.getByText('Дата создания платежа', { exact: true }).isVisible());
        assert(await page.getByText('04.10.2026, 12:19 (UTC+03:00)', { exact: true }).isVisible());
        const copy = page.getByRole('button', { name: 'Скопировать номер платежа', exact: true });
        assert.equal(await copy.getAttribute('data-copy-value'), 'INV-SYNTHETIC');
        await page.evaluate(() => {
          window.syntheticClipboard = [];
          Object.defineProperty(navigator, 'clipboard', { configurable: true,
            value: { writeText: async value => window.syntheticClipboard.push(value) } });
        });
        await copy.click();
        assert.deepEqual(await page.evaluate(() => window.syntheticClipboard), ['INV-SYNTHETIC'], 'real copy handler passes only safe number to synthetic clipboard');
        const help = page.locator('summary', { hasText: 'Помощь и возврат' });
        await help.focus();
        await page.keyboard.press('Space');
        const question = page.getByRole('link', { name: 'Вопрос об оплате', exact: true });
        const refund = page.getByRole('link', { name: 'Запросить возврат', exact: true });
        for (const [link, subject] of [[question, 'Вопрос об оплате INV-SYNTHETIC'], [refund, 'Возврат по платежу INV-SYNTHETIC']]) {
          assert(await link.isVisible());
          const destination = new URL(await link.getAttribute('href'));
          assert.equal(destination.protocol, 'mailto:');
          assert.equal(destination.pathname, 'support@example.test');
          assert.equal(destination.searchParams.get('subject'), subject);
          await link.focus();
          assert(await link.evaluate(el => el === document.activeElement));
        }
        assert(await page.getByText('Открытие письма не отправляет запрос и не оформляет возврат', { exact: false }).isVisible());
        const receipt = page.getByRole('link', { name: 'Открыть чек', exact: true });
        if (name.endsWith('invoice-receipt')) {
          assert(await receipt.isVisible());
          assert.equal(await receipt.getAttribute('href'), 'https://graf.test/synthetic-receipt');
        } else assert.equal(await receipt.count(), 0, `${name}: no fabricated document action`);
        if (name.includes('intervals')) {
          assert(await page.getByText('03.01.2027, 12:19 (UTC+03:00): 10 ГБ', { exact: false }).isVisible());
        }
        for (const value of await page.locator('main dd:visible').all()) {
          assert.equal(await value.evaluate(el => getComputedStyle(el).marginInlineStart), '0px', `${name}: no browser-default dd indentation`);
        }
      }
      for (const width of [320, 360, 390, 768, 1280]) {
        await page.setViewportSize({ width, height: 900 });
        for (const theme of ['light', 'dark']) {
          for (const zoom of [1, 2]) {
            await page.evaluate(({ theme, zoom }) => {
              document.documentElement.dataset.theme = theme;
              document.body.style.zoom = String(zoom);
            }, { theme, zoom });
            const overflow = await page.evaluate(() => {
              const main = document.querySelector('main');
              return main.scrollWidth > main.clientWidth + 1 ||
                document.documentElement.scrollWidth > window.innerWidth + 1;
            });
            assert(!overflow, `${name}: content clipped at ${width}px, ${theme}, ${zoom * 100}%`);
            if (name.includes('invoice-') && width === 1280 && zoom === 1) {
              const contentWidth = await page.locator('main .settings-page__content').evaluate(el => el.getBoundingClientRect().width);
              assert.equal(Math.round(contentWidth), 720, `${name}: invoice uses the agreed subscription content width`);
            }
            const smallTargets = await page.evaluate(() => [...document.querySelectorAll(
              'main button, main .button, main summary, main select, main input[type=text], main label.billing-consent',
            )].filter(el => el.checkVisibility() && !el.matches(':disabled')).filter(el => {
              const rect = el.getBoundingClientRect();
              return rect.width < 24 || rect.height < 24;
            }).map(el => el.textContent.trim()));
            assert.deepEqual(smallTargets, [], `${name}: main control target size`);
            if (width === 1280 && zoom === 1) await checkTextContrast(page, `${name}, ${theme}`);
            if (visualDirectory && zoom === 1 && [320, 1280].includes(width)) {
              await page.screenshot({ path: path.join(visualDirectory, `${name}-${width}-${theme}.png`), fullPage: true });
            }
            const primary = page.locator('main .button.primary:visible').first();
            if (await primary.count()) {
              await primary.scrollIntoViewIfNeeded();
              const reachable = await primary.evaluate(el => {
                const rect = el.getBoundingClientRect();
                return rect.left >= -1 && rect.right <= innerWidth + 1 && rect.top >= -1 && rect.bottom <= innerHeight + 1;
              });
              assert(reachable, `${name}: primary action reachable at ${width}px, ${theme}, ${zoom * 100}%`);
              if (visualDirectory && zoom === 2 && width === 320 && name === 'shell-checkout') {
                await page.screenshot({ path: path.join(visualDirectory, `${name}-320-${theme}-200-action.png`) });
              }
              await page.locator('main').evaluate(el => el.scrollTop = 0);
            }
          }
        }
      }
      assert.deepEqual(errors, []);
      await page.close();
    }
    // Reuse the checkout HTML to isolate tab/scope persistence from server money state.
    const preferenceContext = await browser.newContext();
    let scope = { user: 'synthetic-user', workspace: 'synthetic-workspace', session: 'synthetic-session' };
    const originalScope = { ...scope };
    await preferenceContext.route('https://graf.test/**', route => {
      const filename = path.basename(new URL(route.request().url()).pathname);
      if (route.request().resourceType() !== 'document') {
        return route.fulfill({ path: path.join(assets, filename) });
      }
      const meta = Object.entries(scope).map(([name, value]) =>
        `<meta name="${name === 'workspace' ? 'graf-workspace' : `graf-time-${name}`}" content="${value}">`).join('');
      return route.fulfill({contentType: 'text/html; charset=utf-8', body:
        `<html lang="ru"><meta charset="utf-8">${meta}<link rel="stylesheet" href="/cabinet.css"><script src="/cabinet.js" defer></script><body data-surface-mode="standalone_browser">${pages.checkout}</body></html>`});
    });
    const preferencePage = await preferenceContext.newPage();
    const renewal = preferencePage.getByRole('checkbox', { name: /Разрешаю автоматические списания/ });
    const off = preferencePage.getByText('Отключено — автоматического списания не будет.', { exact: true });
    await preferencePage.goto('https://graf.test/billing/checkout');
    assert(await renewal.isChecked(), 'new tab defaults to recurring enabled');
    await renewal.uncheck();
    assert(await off.isVisible());
    const preference = await preferencePage.evaluate(() => Object.entries(sessionStorage)
      .filter(([key]) => key.startsWith('graf-checkout-renewal:')));
    assert.equal(preference.length, 1);
    assert.equal(preference[0][1], 'false', 'only the boolean preference is stored');
    for (let index = 0; index < 2; index++) {
      await preferencePage.reload();
      assert.equal(await renewal.isChecked(), false);
      assert(await off.isVisible());
      assert.equal(await preferencePage.getByRole('checkbox', { name: /Принимаю/ }).isChecked(), false);
    }
    await renewal.check();
    await preferencePage.reload();
    assert(await renewal.isChecked(), 'explicitly enabling renewal replaces the previous off choice');
    assert.equal(await preferencePage.evaluate(key => sessionStorage.getItem(key), preference[0][0]), 'true');
    await renewal.uncheck();
    await preferencePage.evaluate(html => {
      document.querySelector('main').outerHTML = html;
      document.body.dispatchEvent(new CustomEvent('htmx:afterSwap'));
    }, pages.checkout);
    assert.equal(await renewal.isChecked(), false, 'HTMX replacement restores this tab choice');
    await renewal.evaluate(el => { el.checked = true; });
    await preferencePage.evaluate(() => window.dispatchEvent(new Event('pageshow')));
    assert.equal(await renewal.isChecked(), false, 'pageshow reconciles native restored state');
    const anotherTab = await preferenceContext.newPage();
    await anotherTab.goto('https://graf.test/billing/checkout');
    assert(await anotherTab.getByRole('checkbox', { name: /Разрешаю/ }).isChecked(), 'a tab without opener has independent choice');
    await anotherTab.close();
    for (const part of ['user', 'workspace', 'session']) {
      scope = { ...originalScope, [part]: `another-${part}` };
      await preferencePage.reload();
      assert(await renewal.isChecked(), `choice is isolated by ${part}`);
      scope = { ...originalScope };
      await preferencePage.reload();
      assert.equal(await renewal.isChecked(), false);
    }
    await preferencePage.evaluate(key => sessionStorage.setItem(key, 'invalid'), preference[0][0]);
    await preferencePage.reload();
    assert(await renewal.isChecked(), 'unknown stored value cannot become an inherited choice');
    scope = { ...originalScope, session: '' };
    await preferencePage.reload();
    await renewal.uncheck();
    await preferencePage.evaluate(() => document.body.dispatchEvent(new CustomEvent('htmx:afterSwap')));
    assert.equal(await renewal.isChecked(), false, 'missing scope still permits a live one-period choice');
    assert(await off.isVisible());
    assert.equal(await preferencePage.evaluate(key => sessionStorage.getItem(key), preference[0][0]), 'invalid');
    scope = { ...originalScope };
    await preferencePage.addInitScript(() => {
      for (const method of ['getItem', 'setItem']) Storage.prototype[method] = () => { throw new DOMException('blocked', 'SecurityError'); };
    });
    await preferencePage.reload();
    await renewal.uncheck();
    await preferencePage.evaluate(() => window.dispatchEvent(new Event('pageshow')));
    assert.equal(await renewal.isChecked(), false, 'storage failure cannot undo the current native choice');
    assert(await off.isVisible());
    await preferencePage.getByRole('checkbox', { name: /Принимаю/ }).check();
    assert(await preferencePage.locator('form[action="/billing/checkout/start"]').evaluate(el => el.checkValidity()));
    await preferenceContext.close();

    // Submit the actual native form with scripting disabled. The intercepted
    // request proves browser validation and serialization, not provider success.
    for (const recurring of [true, false]) {
      const noScriptPage = await browser.newPage({ javaScriptEnabled: false });
      noScriptPage.setDefaultTimeout(5000);
      const posts = [];
      await noScriptPage.route('https://graf.test/**', route => {
        const request = route.request();
        if (request.method() === 'POST') posts.push(request);
        return route.fulfill({contentType: 'text/html; charset=utf-8', body: request.method() === 'POST'
          ? '<meta charset="utf-8"><p>Синтетическая отправка принята</p>' : `<html lang="ru"><meta charset="utf-8"><body>${pages.checkout}</body></html>`});
      });
      await noScriptPage.goto('https://graf.test/billing/checkout');
      assert(await noScriptPage.getByText('При автопродлении', { exact: true }).isVisible());
      assert(await noScriptPage.getByText('Списание при автопродлении', { exact: true }).isVisible());
      await noScriptPage.getByRole('button', {name: /^Оплатить/}).click();
      assert.equal(posts.length, 0, 'native validation requires offer acceptance without JS');
      await noScriptPage.getByRole('checkbox', { name: /Принимаю/ }).check();
      await noScriptPage.getByRole('checkbox', { name: /Разрешаю/ }).setChecked(recurring);
      await Promise.all([
        noScriptPage.waitForURL('https://graf.test/billing/checkout/start'),
        noScriptPage.getByRole('button', {name: /^Оплатить/}).click(),
      ]);
      assert.equal(posts.length, 1);
      const submitted = new URLSearchParams(posts[0].postData());
      assert.equal(submitted.get('quote_id'), 'synthetic-quote');
      assert.equal(submitted.get('cycle'), 'month');
      assert.equal(submitted.get('offer_consent'), 'true');
      assert.equal(submitted.get('recurring_consent'), recurring ? 'true' : null);
      await noScriptPage.close();
    }
    // Native disclosure and consent work without page scripting; no provider is called.
    for (const name of ['subscription-off-ready', 'subscription']) {
      const page = await browser.newPage({ javaScriptEnabled: false });
      const posts = [];
      await page.route('https://graf.test/**', route => {
        const request = route.request();
        if (request.method() === 'POST') posts.push(request);
        return route.fulfill({ contentType: 'text/html; charset=utf-8', body: request.method() === 'POST'
          ? '<meta charset="utf-8"><p>Синтетическая отправка принята</p>'
          : `<html lang="ru"><meta charset="utf-8"><body>${pages[name]}</body></html>` });
      });
      await page.goto('https://graf.test/billing/subscription');
      const resuming = name === 'subscription-off-ready';
      if (resuming) {
        await page.locator('summary', { hasText: 'Включить автопродление' }).focus();
        await page.keyboard.press('Space');
        await page.getByRole('button', { name: 'Включить автопродление', exact: true }).click();
        assert.equal(posts.length, 0, 'native resume consent is required without JavaScript');
        const consent = page.getByRole('checkbox');
        assert.equal(await consent.isChecked(), false);
        await consent.check();
      }
      const action = resuming ? 'resume' : 'cancel';
      await Promise.all([
        page.waitForURL(`https://graf.test/billing/subscription/${action}`),
        page.getByRole('button', { name: resuming ? 'Включить автопродление' : 'Отключить автопродление', exact: true }).click(),
      ]);
      assert.equal(posts.length, 1);
      const fields = new URLSearchParams(posts[0].postData());
      assert.equal(fields.get('csrf_token'), 'synthetic');
      assert.equal(fields.get('expected_authority_version'), '1');
      assert.equal(fields.get('resume_consent'), resuming ? 'true' : null);
      assert.equal(fields.get('resume_quote_id'), resuming ? 'synthetic-resume' : null);
      await page.close();
    }
    for (const name of Object.keys(pages).filter(name => name.startsWith('subscription-restriction-') || name.startsWith('overview') ||
      ['packages-timeline-year', 'subscription-free', 'subscription-trial', 'subscription-expired', 'subscription-unknown-cycle', 'subscription-year'].includes(name))) {
      const page = await browser.newPage({ javaScriptEnabled: false, viewport: { width: 320, height: 900 } });
      const requests = [];
      await page.route('https://graf.test/**', route => {
        if (route.request().resourceType() !== 'document') {
          const filename = path.basename(new URL(route.request().url()).pathname);
          const asset = [assets, publicAssets].map(dir => path.join(dir, filename)).find(file => fs.existsSync(file) && fs.statSync(file).isFile());
          return asset ? route.fulfill({ path: asset }) : route.fulfill({ status: 204 });
        }
        requests.push(route.request());
        const shell = name.startsWith('overview') && pages[`shell-${name}`];
        return route.fulfill({ contentType: 'text/html; charset=utf-8', body: shell || `<html lang="ru"><meta charset="utf-8"><style>${fs.readFileSync(path.join(assets, 'cabinet.css'), 'utf8')}</style><body>${pages[name]}</body></html>` });
      });
      await page.goto('https://graf.test/billing/subscription');
      if (name.startsWith('overview')) {
        const blocked = ['overview-pending', 'overview-expired-pending', 'overview-member', 'overview-unavailable'].includes(name);
        assert.equal(await page.locator('form[action="/billing/storage/preview"]').count(), blocked ? 0 : 1);
        if (!blocked) {
          const editor = page.locator('#billing-storage-editor');
          if (!await editor.evaluate(el => el.open)) await editor.locator('summary').first().click();
          const select = page.getByLabel('Общий объем хранения', { exact: true });
          await select.selectOption('2');
          assert.match(await select.locator('option:checked').innerText(), /15 ГБ.*5000 ₽/);
          assert.equal(await page.locator('[data-package-step]:visible').count(), 0);
          for (const width of [320, 360, 1280]) for (const theme of ['light', 'dark']) for (const zoom of [1, 2]) {
            await page.setViewportSize({ width, height: 900 });
            await page.evaluate(({theme, zoom}) => {
              document.documentElement.dataset.theme = theme;
              document.body.style.zoom = String(zoom);
            }, {theme, zoom});
            assert(await page.evaluate(() => {
              const main = document.querySelector('main');
              return main.scrollWidth <= main.clientWidth + 1 && document.documentElement.scrollWidth <= innerWidth + 1;
            }), `${name}: NoJS editor fits ${width}px/${theme}/${zoom * 100}%`);
            assert(await page.getByRole('button', { name: 'Проверить изменение', exact: true }).isVisible());
          }
          await page.evaluate(() => { document.body.style.zoom = '1'; });
          await page.setViewportSize({ width: 320, height: 900 });
          await Promise.all([
            page.waitForURL('https://graf.test/billing/storage/preview'),
            page.getByRole('button', { name: 'Проверить изменение', exact: true }).click(),
          ]);
          const posts = requests.filter(request => request.method() === 'POST');
          assert.equal(posts.length, 1);
          const fields = new URLSearchParams(posts[0].postData());
          assert.equal(fields.get('package_count'), '2');
          assert.equal(fields.get('return_to'), 'overview');
          assert.equal(fields.get('csrf_token'), 'synthetic');
          assert.equal(fields.get('purchase_consent'), null);
        } else assert.equal(requests.length, 1);
      } else if (name === 'packages-timeline-year') {
        const select = page.getByLabel('Общий объем хранения', { exact: true });
        await select.selectOption('2');
        assert.match(await select.locator('option:checked').innerText(), /15 ГБ.*5000 ₽ \/ год за хранение/);
        assert.equal(await page.locator('#storage-package-summary').isVisible(), false);
        assert(await page.getByRole('button', { name: 'Проверить изменение', exact: true }).isVisible());
        assert.equal(requests.filter(request => request.method() !== 'GET').length, 0);
      } else if (name.startsWith('subscription-restriction-')) {
        const primary = page.getByRole('link', { name: 'Проверить платеж', exact: true });
        assert(await primary.isVisible());
        await primary.focus();
        assert(await primary.evaluate(el => el === document.activeElement));
        const text = await page.locator('main').innerText();
        assert(!text.includes('Подтверждение оплаты получено'));
        if (name.endsWith('receipt_contact_required')) assert(text.includes('нужен адрес для чека') && !text.includes('Оплатите'));
        else if (!name.endsWith('late_success')) assert(text.includes('Автопродление приостановлено'));
        assert.equal(await page.locator('a[href^="/billing/checkout?"], form[action="/billing/subscription/resume"], form[action="/billing/subscription/early-preview"]').count(), 0);
        await Promise.all([page.waitForURL('https://graf.test/billing/checkout/status/INV-SYNTHETIC'), page.keyboard.press('Enter')]);
        assert.equal(requests.length, 2);
        assert(requests.every(request => request.method() === 'GET'), 'native status navigation must not send money requests');
      } else {
        await page.locator('summary', { hasText: 'Способ оплаты, условия и история' }).focus();
        await page.keyboard.press('Space');
        const period = page.getByText('Период оплаты', { exact: true });
        if (name === 'subscription-year') {
          assert(await period.isVisible());
          assert.equal(await period.locator('..').locator('dd').innerText(), 'год');
        } else assert.equal(await period.count(), 0);
        assert.equal(requests.length, 1);
      }
      await page.close();
    }
    // Invoice disclosures and document/support links are native HTML with JS off.
    // We inspect mailto targets but never invoke an external mail application.
    for (const name of ['invoice-future', 'invoice-receipt', 'invoice-receipt-no-url']) {
      const page = await browser.newPage({ javaScriptEnabled: false });
      const posts = [];
      await page.route('https://graf.test/**', route => {
        if (route.request().method() !== 'GET') posts.push(route.request().method());
        return route.fulfill({ contentType: 'text/html; charset=utf-8', body: `<html lang="ru"><meta charset="utf-8"><body>${pages[name]}</body></html>` });
      });
      await page.goto('https://graf.test/billing/invoices/INV-SYNTHETIC');
      assert(await page.getByText('03.11.2026 — 03.12.2026', { exact: true }).isVisible());
      for (const label of ['Сведения о платеже', 'Помощь и возврат']) {
        const summary = page.locator('summary', { hasText: label });
        await summary.focus();
        await page.keyboard.press('Space');
        assert(await summary.locator('..').evaluate(el => el.open), `${name}: JS-off keyboard disclosure`);
      }
      assert(await page.getByText('Дата создания платежа', { exact: true }).isVisible());
      assert(await page.getByRole('link', { name: 'Вопрос об оплате', exact: true }).isVisible());
      assert(await page.getByRole('link', { name: 'Запросить возврат', exact: true }).isVisible());
      assert.equal(await page.getByRole('link', { name: 'Открыть чек', exact: true }).count(), name === 'invoice-receipt' ? 1 : 0);
      assert.deepEqual(posts, [], 'reading and disclosing invoice sends no mutations');
      await page.close();
    }
    console.log('billing: initial/error focus, native consent keyboard, no focus steal, single status region passed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
