const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../src/twobrain_rec_server/public/static/public/metrica.js'), 'utf8');
function page(options = {}) {
  const data = new Map(Object.entries(options.storage || {}));
  const handlers = {}, scripts = [], calls = [];
  const button = {textContent: '', addEventListener(n, f) { this[n] = f; }, setAttribute() {}};
  const config = {automatic_enabled: true, external_counter_allowed: true, page_path: '/', surface: 'public_landing',
    yandex_metrica_id: '12345678', replay_allowed: true, map_frame_origins: ['https://metrika.yandex.ru','https://metrika.yandex.by','https://metrica.yandex.com','https://metrica.yandex.com.tr','https://webvisor.com','https://*.webvisor.com'], campaign_attribution: {utm_source: 'yandex'},
    consent_storage_key: 'graf_public_cookie_consent', stable_labels: {cta_location: ['hero_download'], target_kind: ['download_page']},
    event_catalog: [{event_name: 'public_landing_cta_clicked', stable_fields: ['cta_location', 'target_kind']},
      {event_name: 'public_landing_viewed', surface: 'public_landing', stable_fields: []},
      {event_name: 'public_download_viewed', surface: 'public_download', stable_fields: []}]};
  const add = (name, fn) => { (handlers[name] ||= []).push(fn); };
  const cta = {dataset: {analyticsCta:'hero_download',analyticsTarget:'download_page'}, addEventListener(n,f) {this[n]=f;}};
  const document = {referrer: options.referrer || 'https://example.org/private?secret=1',
    getElementById() { return {textContent: JSON.stringify({...config, ...options.config})}; },
    querySelectorAll(selector) {return selector === '[data-metrica-toggle]' ? [button] : selector === '[data-analytics-cta]' ? [cta] : [];},
    addEventListener: add, createElement() {return {remove() {this.removed = true;}};},
    head: {appendChild(s) {scripts.push(s);}}};
  const window = {location: new URL(options.url || 'https://rec.example/'), top: null, self: null,
    addEventListener: add, localStorage: {getItem(k) {if(options.unavailable) throw Error(); return data.get(k) ?? null;},
    setItem(k,v) {if(options.unavailable) throw Error(); data.set(k,v);}, removeItem(k) {data.delete(k);}}};
  window.self = window; window.top = options.framed ? {} : window;
  vm.runInNewContext(source, {window, document, URL, Set, Date});
  const fire = (name, arg = {}) => (handlers[name] || []).forEach(f => f(arg));
  const load = () => {window.ym = (...args) => calls.push(args); scripts[0]?.onload();};
  return {window, button, cta, data, scripts, calls, fire, load};
}
test('new visitor loads one native counter, replay/maps and one hit without consent writes', () => {
  const p = page(); assert.equal(p.scripts.length, 1); p.load();
  p.fire('pageshow'); p.fire('focus');
  assert.equal(p.calls.filter(c => c[1] === 'init').length, 1);
  const init = p.calls[0][2]; assert.equal(init.defer, true); assert.equal(init.webvisor, true); assert.equal(init.clickmap, true);
  assert.equal(init.trackLinks, false); assert.equal(init.disableYtm, true);
  const hit = p.calls.find(c => c[1] === 'hit'); assert.equal(hit[2], 'https://rec.example/');
  assert.equal(hit[3].referer, 'https://example.org/');
  assert.equal(p.data.has('graf_public_cookie_consent'), false);
});
test('previous refusal, corruption, unavailable storage, frame or unsafe address prevent loading', () => {
  for(const options of [
    {storage:{graf_public_cookie_consent: JSON.stringify({categories:['necessary']})}},
    {storage:{graf_public_cookie_consent:'oops'}}, {storage:{graf_public_metrica_choice:'broken'}},
    {unavailable:true}, {framed:true}, {url:'https://rec.example/login'},
    {url:'https://rec.example/?email=private'}, {url:'https://rec.example/#secret'},
    {config:{external_counter_allowed:false}},
  ]) assert.equal(page(options).scripts.length, 0, JSON.stringify(options));
});
test('previous replay refusal permits only page measurement', () => {
  const p = page({storage:{graf_public_cookie_consent:JSON.stringify({categories:['necessary','analytics']})}});
  p.load(); assert.equal(p.calls[0][2].webvisor, false); assert.equal(p.calls[0][2].clickmap, false);
});
test('persistent refusal destroys active counter and resume does not restart it', () => {
  const p = page(); p.load(); p.button.click(); p.fire('pageshow');
  assert.equal(p.data.get('graf_public_metrica_choice'), 'disabled');
  assert.equal(p.calls.at(-1)[1], 'destruct');
  assert.equal(p.calls.filter(c=>c[1] === 'init').length, 1);
});
test('refusal in another tab before script load prevents delayed init and hit', () => {
  const p = page(); p.data.set('graf_public_metrica_choice','disabled'); p.fire('storage', {key:'graf_public_metrica_choice'}); p.load();
  assert.equal(p.calls.length, 0);
});
test('resume rechecks categories and stops replay when another tab withdraws it', () => {
  const p = page(); p.load(); p.data.set('graf_public_cookie_consent',JSON.stringify({categories:['necessary','analytics']}));
  p.fire('focus'); assert.equal(p.calls.at(-1)[1], 'destruct');
});
test('campaign parameters use server-normalized allowlist; unknown values are blocked', () => {
  assert.equal(page({url:'https://rec.example/?utm_source=yandex&yclid=12345'}).scripts.length, 1);
  assert.equal(page({url:'https://rec.example/?utm_source=someone'}).scripts.length, 0);
  assert.equal(page({url:'https://rec.example/?utm_source=yandex&utm_source=yandex'}).scripts.length, 0);
});
test('initial hit retains only accepted normalized campaign parameters and click IDs', () => {
  const p = page({url:'https://rec.example/?utm_source=YaNdEx&utm_medium=cpc&utm_campaign=launch&yclid=12345&ysclid=abc123',
    config:{campaign_attribution:{utm_source:'yandex',utm_medium:'cpc',utm_campaign:'launch'}}});
  p.load();
  const hit = p.calls.find(c => c[1] === 'hit');
  assert.equal(hit[2], 'https://rec.example/?utm_source=yandex&utm_medium=cpc&utm_campaign=launch&yclid=12345&ysclid=abc123');
});
test('each public page preserves its existing entry goal exactly once', () => {
  for (const [path, surface, event] of [['/', 'public_landing', 'public_landing_viewed'],
    ['/download', 'public_download', 'public_download_viewed']]) {
    const p = page({url:'https://rec.example'+path, config:{page_path:path,surface}});
    p.load(); p.fire('pageshow'); p.fire('focus');
    const goals = p.calls.filter(c => c[1] === 'reachGoal');
    assert.equal(goals.length, 1);
    assert.equal(goals[0][2], event);
    assert.equal(p.calls.filter(c => c[1] === 'hit').length, 1);
  }
});

test('storage refresh is read-only and unrelated probe notifications are ignored', () => {
  const p = page(); let writes = 0;
  p.window.localStorage.setItem = () => { writes++; };
  p.fire('storage', {key:'graf_public_metrica_choice.probe'});
  p.fire('storage', {key:'graf_public_cookie_consent'});
  p.fire('focus'); assert.equal(writes,0);
});
test('explicit re-enable never overrides a later legacy refusal', () => {
  const legacy = JSON.stringify({categories:['necessary']});
  const p = page({storage:{graf_public_cookie_consent:legacy,
    graf_public_metrica_choice:JSON.stringify({enabled:true,legacy})}});
  p.load(); assert.equal(p.calls[0][1],'init');
  p.data.set('graf_public_cookie_consent', JSON.stringify({categories:['necessary'],data:{graf_consent_state:'revoked'}}));
  p.fire('storage', {key:'graf_public_cookie_consent'});
  assert.equal(p.calls.at(-1)[1],'destruct');
});

test('only catalogued goals with stable labels leave the page, none after refusal', () => {
  const p = page(); p.load(); p.cta.click();
  const goal = p.calls.at(-1); assert.equal(goal[1], 'reachGoal');
  assert.equal(goal[2], 'public_landing_cta_clicked');
  assert.deepEqual(Object.keys(goal[3]), ['cta_location','target_kind']);
  p.cta.dataset.analyticsCta = 'private@example.invalid';
  p.cta.click(); assert.equal(p.calls.at(-1), goal);
  p.button.click(); const count=p.calls.length; p.cta.click(); assert.equal(p.calls.length,count);
});
test('explicit enable can reverse a refusal without changing legacy consent', () => {
  const raw=JSON.stringify({categories:['necessary']});
  const p=page({storage:{graf_public_cookie_consent:raw}});
  assert.equal(p.scripts.length,0); p.button.click(); assert.equal(p.scripts.length,1); p.load();
  assert.equal(p.calls[0][2].webvisor,true); assert.equal(p.data.get('graf_public_cookie_consent'),raw);
});

test('official HTTPS map frames allowed, deceptive domains and nonstandard ports blocked', () => {
  for(const referrer of ['https://metrika.yandex.ru/maps', 'https://metrica.yandex.com.tr/', 'https://viewer.webvisor.com/']) {
    assert.equal(page({framed:true,referrer}).scripts.length,1,referrer);
  }
  for(const referrer of ['http://metrika.yandex.ru/', 'https://metrika.yandex.ru:8443/',
    'https://metrika.yandex.ru.evil.invalid/', 'https://evilwebvisor.com/', 'https://webvisor.com.evil.invalid/']) {
    assert.equal(page({framed:true,referrer}).scripts.length,0,referrer);
  }
  assert.equal(page({framed:true,referrer:'https://metrika.yandex.ru/',config:{replay_allowed:false}}).scripts.length,0);
});
