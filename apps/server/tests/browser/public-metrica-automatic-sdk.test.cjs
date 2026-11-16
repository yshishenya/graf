/* Isolated native SDK proof: every browser request is intercepted, no live counter. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {parseArgs} = require('node:util');
const {values} = parseArgs({options: {'sdk-file': {type:'string'}, 'sdk-sha256': {type:'string'}}});
assert.ok(values['sdk-file'] && path.isAbsolute(values['sdk-file']));
const sdk = fs.readFileSync(values['sdk-file']);
assert.equal(createHash('sha256').update(sdk).digest('hex'), values['sdk-sha256']);
const {chromium} = require(require.resolve('playwright', {paths:[process.env.GRAF_NODE_MODULES || __dirname]}));
const controller = fs.readFileSync(path.join(__dirname,'../../src/twobrain_rec_server/public/static/public/metrica.js'),'utf8');
async function main() {
  const browser = await chromium.launch({headless:true});
  try {
    for(const pagePath of ['/', '/download']) {
      const context = await browser.newContext({serviceWorkers:'block'});
      const requests = [];
      let phase = 'active';
      await context.routeWebSocket('**/*', socket => socket.close());
      await context.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (url.origin === 'https://graf-test.invalid') return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="ru"><body style="height:4000px"><h1>Учебная страница</h1><input value="MASKED_FIXTURE"><button data-metrica-toggle>Отключить</button></body></html>'});
        if(url.href === 'https://mc.yandex.ru/metrika/tag.js') return route.fulfill({contentType:'text/javascript',body:sdk});
        requests.push({phase,path:url.pathname,host:url.hostname});
        return route.abort('blockedbyclient');
      });
      const page = await context.newPage();
      const errors = []; page.on('pageerror',error => errors.push(String(error)));
      await page.goto('https://graf-test.invalid' + pagePath);
      const config = {automatic_enabled:true, external_counter_allowed:true, replay_allowed:true,
        page_path:pagePath, yandex_metrica_id:'99999999', campaign_attribution:{}, stable_labels:{},event_catalog:[]};
      await page.evaluate(config => {const el=document.createElement('script');el.id='graf-public-analytics-config';el.type='application/json';el.textContent=JSON.stringify(config);document.body.appendChild(el);}, config);
      await page.addScriptTag({content:controller});
      await page.waitForFunction(() => Boolean(window.yaCounter99999999));
      assert.equal(await page.locator('input').evaluate(el => el.classList.contains('ym-hide-content')), true);
      await page.evaluate(() => { const el=document.createElement('textarea');document.body.appendChild(el); });
      await page.waitForFunction(() => document.querySelector('textarea').classList.contains('ym-disable-keys'));
      await page.waitForTimeout(1500);
      assert.ok(requests.some(r=>r.path.includes('/watch/99999999')), 'native positive watch');
      await page.locator('[data-metrica-toggle]').click();
      await page.waitForFunction(() => !window.yaCounter99999999);
      await page.waitForTimeout(500);
      phase = 'stopped';
      await page.mouse.move(50, 100); await page.mouse.wheel(0, 500);
      await page.waitForTimeout(1500);
      assert.equal(requests.filter(r=>r.phase === 'stopped').length,0,'no new SDK requests after destruct');
      assert.equal(await page.evaluate(() => localStorage.getItem('graf_public_metrica_choice')), 'disabled');
      assert.deepEqual(errors, []);
      console.log(`native automatic ${pagePath}: counter created, watch intercepted, fields masked, destruct and quiet window PASS`);
      await context.close();
    }
  } finally {await browser.close();}
}
main().catch(error => {console.error(error);process.exitCode=1;});
