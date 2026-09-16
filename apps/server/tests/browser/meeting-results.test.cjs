const { chromium, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const server = path.resolve(__dirname, '../..');
const assets = path.join(server, 'src/twobrain_rec_server/cabinet/static/cabinet');
const output = path.resolve(server, '../../output/playwright/f267');
const pages = JSON.parse(execFileSync(path.join(server, '.venv/bin/python'),
  ['-m', 'tests.fixtures.meeting_results'], { cwd: server, maxBuffer: 16 * 1024 * 1024 }));
fs.mkdirSync(output, { recursive: true });

async function checkLayout(page, label) {
  const defects = await page.evaluate(() => {
    const main = document.querySelector('#cabinet-main');
    const issues = [];
    for (const element of [document.documentElement, main, main.querySelector('.detail-main')].filter(Boolean)) {
      if (element.scrollWidth > element.clientWidth + 1) issues.push(`overflow ${element.className}: ${element.scrollWidth}/${element.clientWidth}`);
    }
    if (issues.length) issues.push(...[...main.querySelectorAll('*')].filter(node => node.checkVisibility() && node.clientWidth && node.scrollWidth > node.clientWidth + 1).slice(0, 12).map(node => `overflow child: ${node.tagName}.${node.className} ${node.scrollWidth}/${node.clientWidth} ${node.textContent.slice(0, 40)}`));
    const header = main.querySelector('[data-meeting-detail-header]');
    if (header && header.offsetHeight > main.clientHeight / 2 && getComputedStyle(header).position === 'sticky') issues.push('oversized sticky header');
    for (const table of main.querySelectorAll('.notes-action-table')) {
      if (getComputedStyle(table).display !== 'table') continue;
      for (const cell of table.querySelectorAll('th')) {
        const range = document.createRange();
        range.selectNodeContents(cell);
        if (new Set([...range.getClientRects()].map(rect => rect.top)).size > 1) issues.push(`wrapped task heading: ${cell.textContent}`);
      }
    }
    const luminance = color => {
      const rgb = color.match(/[\d.]+/g).slice(0, 3).map(Number).map(v => v / 255);
      return rgb.map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
        .reduce((total, v, i) => total + v * [0.2126, 0.7152, 0.0722][i], 0);
    };
    for (const node of main.querySelectorAll('.meeting-about, .meeting-participants, .outcome-item-text, .notes-source-link, .notes-topic > summary')) {
      if (!node.checkVisibility()) continue;
      const style = getComputedStyle(node);
      let parent = node;
      while (parent.parentElement && ['rgba(0, 0, 0, 0)', 'transparent'].includes(getComputedStyle(parent).backgroundColor)) parent = parent.parentElement;
      const values = [luminance(style.color), luminance(getComputedStyle(parent).backgroundColor)].sort((a, b) => b - a);
      const contrast = (values[0] + 0.05) / (values[1] + 0.05);
      if (contrast < 4.5) issues.push(`contrast ${contrast.toFixed(2)}: ${node.className}`);
      if (node.matches('.outcome-item-text, .meeting-about') && parseFloat(style.lineHeight) / parseFloat(style.fontSize) < 1.45) issues.push('tight text');
      if (node.matches('button, summary') && node.getBoundingClientRect().height < 24) issues.push('small target');
    }
    return issues;
  });
  assert.deepEqual(defects, [], label);
}

async function doubleText(page) {
  await page.evaluate(() => {
    // Text-only enlargement, not device pixel ratio or a smaller screenshot.
    const styles = [...document.querySelectorAll('#cabinet-main, #cabinet-main *')].map(node => {
      const style = getComputedStyle(node);
      return [node, parseFloat(style.fontSize), parseFloat(style.lineHeight)];
    });
    for (const [node, size, line] of styles) {
      node.style.fontSize = `${size * 2}px`;
      if (Number.isFinite(line)) node.style.lineHeight = `${line * 2}px`;
    }
  });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function checkFocus(page) {
  assert.equal(await page.evaluate(() => {
    const focus = document.activeElement.getBoundingClientRect();
    const main = document.querySelector('#cabinet-main').getBoundingClientRect();
    const header = document.querySelector('[data-meeting-detail-header]');
    const top = header && getComputedStyle(header).position === 'sticky' ? header.getBoundingClientRect().bottom : main.top;
    return focus.top >= top - 1 && focus.bottom <= main.bottom + 1;
  }), true, 'focused control is not covered by the header or player');
}

(async () => {
  let checks = 0;
  for (const [engine, type] of [['chromium', chromium], ['webkit', webkit]]) {
    if (process.env.GRAF_BROWSER && process.env.GRAF_BROWSER !== engine) continue;
    const browser = await type.launch({ headless: true });
    try {
      for (const theme of ['light', 'dark']) for (const surface of ['browser', 'embedded', 'shared']) {
        const context = await browser.newContext({ colorScheme: theme, timezoneId: 'Asia/Yekaterinburg' });
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        let current = `normal-${surface}`;
        await page.route('**/*', async route => {
          const url = new URL(route.request().url());
          if (route.request().resourceType() === 'document') return route.fulfill({ contentType: 'text/html', body: pages[current] });
          if (url.pathname.includes('/static/')) {
            const file = path.join(assets, path.basename(url.pathname));
            if (fs.existsSync(file)) return route.fulfill({ path: file });
            return route.fulfill({ status: 404, body: '' });
          }
          return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ candidates: [], items: [], templates: [] }) });
        });
        const load = async variant => {
          current = `${variant}-${surface}`;
          await page.goto(`https://graf.test/meetings/synthetic?case=${variant}`);
          await page.waitForFunction(() => document.documentElement.dataset.cabinetJs === 'ready');
          await page.evaluate(theme => { document.documentElement.dataset.theme = theme; }, theme);
        };
        try {
          for (const width of [320, 390, 720, 768, 1024, 1440]) {
            await page.setViewportSize({ width, height: 1000 });
            await load('normal');
            assert.equal(await page.locator('#cabinet-main h1').count(), 1);
            assert.match(await page.locator('.meeting-about').textContent(), /О чём встреча:/);
            assert.match(await page.locator('#cabinet-main time').first().textContent(), /08.09.2026, 12:05/);
            assert.equal(await page.locator('.notes-topic[open], .notes-protocol-notes[open]').count(), 0);
            const headings = await page.locator('.notes-full-protocol > .notes-section > h2, .notes-full-protocol > .notes-section > h3, .notes-protocol-notes > summary').allTextContents();
            assert.deepEqual(headings, ['Главное', 'Принятые решения', 'Задачи', 'Открытые вопросы и следующие шаги', 'Ключевые обсуждения', 'Примечания']);
            assert.equal(await page.locator('.notes-full-protocol').getByText('Цели встречи', { exact: true }).count(), 0);
            await checkLayout(page, `${engine} ${theme} ${surface} ${width}`); checks++;
            if (width === 1440 && surface !== 'shared') {
              const flow = await page.locator('.outcome-item').first().evaluate(item => {
                const range = document.createRange();
                range.selectNodeContents(item.querySelector('.outcome-item-text'));
                const lastLine = [...range.getClientRects()].at(-1);
                const sources = item.querySelector('.notes-item-sources').getBoundingClientRect();
                const next = item.nextElementSibling.getBoundingClientRect();
                return {
                  inline: sources.left >= lastLine.right && sources.top < lastLine.bottom && sources.bottom > lastLine.top,
                  nextParagraph: next.top > Math.max(lastLine.bottom, sources.bottom),
                };
              });
              assert.deepEqual(flow, { inline: true, nextParagraph: true }, 'sources finish the current thought; the next thought starts a new paragraph');
            }
            if (width === 1440 || width === 390) await page.screenshot({ path: path.join(output, `${engine}-${theme}-${surface}-${width}.png`), fullPage: true });
            if (width === 390 || width === 720) {
              await page.locator('.notes-action-table').scrollIntoViewIfNeeded();
              await page.screenshot({ path: path.join(output, `${engine}-${theme}-${surface}-${width}-tasks.png`), fullPage: true });
            }
            await doubleText(page);
            await checkLayout(page, `${engine} ${theme} ${surface} ${width} text200`); checks++;
          }
          if (engine === 'chromium') for (const variant of ['long', 'empty', 'legacy', 'categories', 'readonly', 'stale']) {
            await page.setViewportSize({ width: 320, height: 1000 });
            await load(variant);
            await doubleText(page);
            await checkLayout(page, `${engine} ${theme} ${surface} ${variant} text200`); checks++;
            if (variant === 'empty') {
              assert.equal(await page.locator('.notes-action-table, .notes-protocol-notes').count(), 0);
              assert.match(await page.locator('.meeting-participants').textContent(), /Не определено/);
            }
            if (variant === 'legacy') assert.match(await page.locator('.meeting-about').textContent(), /Тип встречи:/);
            if (variant === 'categories') assert.equal(await page.locator('.notes-full-protocol').count(), 0);
            if (variant === 'stale') assert.equal(await page.locator('.notes-source-link').count(), 0);
          }
          await page.setViewportSize({ width: 1024, height: 1000 });
          await load('normal');
          const topic = page.locator('.notes-topic').last();
          const summary = topic.locator('summary');
          await summary.focus(); await page.keyboard.press('Enter');
          assert.equal(await topic.getAttribute('open'), '');
          assert.deepEqual(await topic.locator('.notes-topic-part > h4, .notes-topic-part > h5').allTextContents(), ['Итог', 'Контекст', 'Обсуждение', 'Предложения']);
          assert.notEqual(await summary.evaluate(node => getComputedStyle(node).outlineStyle), 'none');
          await checkFocus(page);
          await checkLayout(page, 'expanded topic');
          if (surface !== 'shared') {
            await topic.locator('.notes-source-link').first().click();
            assert.equal(await topic.getAttribute('open'), '');
            await page.locator('[data-source-return]').click();
            await page.waitForFunction(() => document.activeElement.closest('.notes-topic') !== null);
            await summary.focus();
          }
          await page.screenshot({ path: path.join(output, `${engine}-${theme}-${surface}-topic.png`), fullPage: true });
          await page.keyboard.press('Space');
          assert.equal(await topic.getAttribute('open'), null);
          if (surface === 'shared') assert.equal(await page.locator('.notes-source-link').count(), 0);
          else {
            const first = page.locator('.outcome-item').first();
            assert.equal(await first.locator('.notes-source-link:visible').count(), 1);
            const more = first.locator('.notes-source-more > summary');
            await more.focus(); await page.keyboard.press('Enter');
            await checkFocus(page);
            await checkLayout(page, 'source dropdown');
            const links = first.locator('.notes-source-list .notes-source-link');
            const boxes = await links.evaluateAll(nodes => nodes.map(node => { const box = node.getBoundingClientRect(); return { x: box.x, y: box.y, height: box.height }; }));
            assert.equal(boxes.length, 3);
            assert.ok(boxes.every((box, i) => !i || box.y >= boxes[i - 1].y + boxes[i - 1].height));
            // WebKit on macOS uses Option-Tab to include links/buttons with the default keyboard preference.
            await page.keyboard.press(engine === 'webkit' ? 'Alt+Tab' : 'Tab');
            assert.equal(await links.first().evaluate(node => node === document.activeElement), true);
            await page.keyboard.press('Enter');
            assert.equal(await page.locator('[data-detail-panel="recording"]').isVisible(), true);
            await page.waitForFunction(() => document.activeElement.dataset.sourceSegments === '00000000-0000-0000-0000-000000000003');
            await page.locator('[data-source-return]').click();
            await page.waitForFunction(() => document.activeElement === document.querySelector('.notes-source-list .notes-source-link'));
            assert.equal(await links.first().evaluate(node => node === document.activeElement), true);
            assert.equal(await page.locator('[data-detail-panel="outcomes"]').isVisible(), true);
          }
          assert.deepEqual(errors, [], 'browser errors');
        } catch (error) {
          await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true });
          console.error({ engine, theme, surface, current, focus: await page.evaluate(() => document.activeElement.outerHTML.slice(0, 800)) });
          throw error;
        } finally { await context.close(); }
      }
      console.log(`PASS ${engine}: layout, text200, disclosure, sources, keyboard and contrast (${checks} cumulative checks)`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
