import subprocess
from pathlib import Path


def test_copy_uses_authorized_captured_scope_and_discards_obsolete_responses():
    script = Path(__file__).resolve().parents[2] / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    harness = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
const projection = source.slice(source.indexOf('  const updateProcessingExportVisibility ='), source.indexOf('  const stopProcessingRecoveryCountdown ='));
const implementation = source.slice(source.indexOf('  const initContentExport ='), source.indexOf('  const initMeetingDeleteDialog ='));
class Element {
  constructor() { this.dataset = {}; this.nodes = {}; this.listeners = {}; this.children = []; this.isConnected = true; this.disabled = false; this.hidden = false; this.value = ''; }
  querySelector(key) { return this.nodes[key] || null; }
  querySelectorAll() { return []; }
  closest() { return this.main; }
  addEventListener(key, fn) { (this.listeners[key] ||= []).push(fn); }
  dispatchEvent(event) { for (const fn of this.listeners[event.type] || []) fn(event); }
  async emit(key) { for (const fn of this.listeners[key] || []) await fn({preventDefault() {}}); }
  setAttribute(key, value) { this[key] = value; }
  removeAttribute(key) { delete this[key]; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  focus() { this.focusCount = (this.focusCount || 0) + 1; }
}
const deferred = () => { let resolve; const promise = new Promise(r => {resolve = r;}); return {promise, resolve}; };
const tick = () => new Promise(resolve => setImmediate(resolve));
function setup({tab = 'outcomes', denied = false, missing = false, clipboard = true, error = null, recovered = false} = {}) {
  const main = new Element(), dialog = new Element(), form = new Element();
  const scope = new Element(), format = new Element(), copy = new Element(), direct = new Element(), submit = new Element(), status = new Element(), directStatus = new Element();
  const selectedTab = new Element(); selectedTab.dataset.detailTab = tab;
  main.nodes['[data-detail-tab][aria-selected="true"]'] = selectedTab;
  main.nodes['[data-detail-copy]'] = direct;
  main.nodes['[data-detail-copy-status]'] = directStatus;
  form.main = main;
  scope.value = 'combined'; format.value = 'txt';
  scope.options = ['transcript', 'summary', 'combined'].filter(v => !(missing && v === 'summary')).map(value => ({value, dataset:{}, disabled: denied && value === 'summary'}));
  scope.querySelector = key => scope.options.find(option => key === `option[value="${option.value}"]`);
  Object.defineProperty(scope, 'selectedOptions', {get: () => scope.options.filter(option => option.value === scope.value)});
  form.dataset = {endpoint:'/synthetic/export', csrfToken:'synthetic-csrf', processingResultId:'source-revision', outcomeSetId:'summary-revision', exportFormatsTranscript:'txt,srt', exportFormatsSummary:'txt', exportFormatsCombined:'txt'};
  for (const [key, el] of Object.entries({'scope':scope, 'format':format, 'copy':copy, 'submit':submit, 'status':status})) form.nodes[`[data-export-${key}]`] = el;
  dialog.nodes['[data-content-export-form]'] = form;
  const fetchGate = deferred(), textGate = deferred(); const writes = [], requests = [];
  const document = {querySelector: key => key === '[data-content-export-dialog]' ? dialog : main.nodes[key] || null, querySelectorAll: key => key === '[data-content-export-form]' ? [form] : [], createElement: () => new Element(), activeElement:null};
  const navigator = {clipboard: clipboard ? {writeText: async text => writes.push(text)} : undefined};
  const fetch = async (url, options) => { requests.push({url, ...options}); await fetchGate.promise; return {ok:!error, json:async () => ({code:error}), text:() => textGate.promise}; };
  const recoverMeetingDetailFromResponse = async () => recovered;
  const restoreMeetingActionFocus = () => {}, trapModalFocus = () => {}, csrfToken = '';
  const window = {};
  let project;
  eval(projection + '\nproject = updateProcessingExportVisibility;');
  eval(implementation + '\ninitContentExport();');
  return {project, main, form, scope, copy, direct, submit, status, directStatus, selectedTab, requests, writes, fetchGate, textGate};
}
async function finish(env, pending) { env.fetchGate.resolve(); await tick(); env.textGate.resolve('synthetic exported text'); await pending; }
(async () => {
  for (const [tab, expected] of [['outcomes','summary'], ['recording','transcript']]) {
    const env = setup({tab}); const pending = env.direct.emit('click');
    assert.equal(env.requests.length, 1);
    const req = env.requests[0]; const payload = JSON.parse(req.body);
    assert.equal(payload.content_scope, expected); assert.equal(payload.format, 'txt');
    assert.equal(payload.processing_result_id, 'source-revision');
    assert.equal(payload.outcome_set_id, expected === 'summary' ? 'summary-revision' : null);
    assert.equal(req.cache, 'no-store'); assert.equal(req.headers['X-CSRF-Token'], 'synthetic-csrf');
    assert.equal(env.scope.value, 'combined');
    await env.direct.emit('click'); await env.copy.emit('click'); await env.form.emit('submit');
    assert.equal(env.requests.length, 1, 'one pending gate for all export entry points');
    env.selectedTab.dataset.detailTab = tab === 'outcomes' ? 'recording' : 'outcomes';
    await env.main.emit('detail-tab-change');
    await finish(env, pending);
    assert.deepEqual(env.writes, ['synthetic exported text']);
    assert.equal(env.direct.disabled, false);
    assert.match(env.directStatus.textContent, /скопирован/);
  }
  for (const config of [{denied:true}, {missing:true}]) {
    const env = setup(config); assert.equal(env.direct.disabled, true);
    await env.direct.emit('click'); assert.equal(env.requests.length, 0);
  }
  for (const mutation of [
    env => {env.form.isConnected = false;},
    env => {env.direct.isConnected = false;},
    env => {env.main.dataset.processingReplacementActive = 'true';},
    env => {env.scope.options.find(x => x.value === 'summary').disabled = true;},
  ]) {
    const env = setup(); const pending = env.direct.emit('click');
    env.fetchGate.resolve(); await tick(); mutation(env); // Includes change while response.text() is pending.
    env.textGate.resolve('obsolete private text'); await pending;
    assert.deepEqual(env.writes, []);
    assert.equal(env.direct.focusCount || 0, 0, 'late completion must not steal focus');
    if (env.main.dataset.processingReplacementActive === 'true') {
      assert.equal(env.direct.disabled, true); assert.equal(env.copy.disabled, true); assert.equal(env.submit.disabled, true);
    }
    if (env.scope.options.find(x => x.value === 'summary')?.disabled) assert.equal(env.direct.disabled, true);
  }
  for (const config of [{clipboard:false}, {error:'export_revision_stale'}, {error:'export_policy_denied'}, {recovered:true}]) {
    const env = setup(config); const pending = env.direct.emit('click'); await finish(env, pending);
    assert.deepEqual(env.writes, []); assert.equal(env.direct.disabled, false);
    if (!config.recovered) assert.equal(env.directStatus.dataset.state, 'error');
  }
  {
    const env = setup({tab:'recording'}); env.scope.value = 'summary';
    env.project(false); assert.equal(env.direct.disabled, true);
    assert.equal(env.copy.disabled, false); assert.equal(env.submit.disabled, false);
    assert.match(env.directStatus.textContent, /недоступно/);
    env.project(true); assert.equal(env.direct.disabled, false);
    const pending = env.direct.emit('click');
    env.project(false); env.project(true);
    assert.equal(env.direct.disabled, true); assert.equal(env.copy.disabled, true); assert.equal(env.submit.disabled, true);
    assert.equal(env.directStatus.dataset.state, 'progress');
    await finish(env, pending);
    assert.equal(env.direct.disabled, false); assert.equal(env.scope.value, 'summary');
  }
  const env = setup(); const pending = env.copy.emit('click');
  assert.equal(JSON.parse(env.requests[0].body).content_scope, 'combined');
  await finish(env, pending); assert.deepEqual(env.writes, ['synthetic exported text']);
  console.log('copy runtime PASS');
})().catch(error => {console.error(error); process.exitCode = 1;});
"""
    result = subprocess.run(["node", "-e", harness, str(script)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def test_source_return_survives_entering_detail_and_replacing_main():
    script = Path(__file__).resolve().parents[2] / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    harness = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
const implementation = source.slice(source.indexOf('  const initSourceNavigation ='), source.indexOf('  const DEFAULT_TIMELINE_HEIGHT ='));
const listeners = {};
let button = null, selected = null;
const document = {
  body:{dataset:{}},
  querySelector:key => key === '[data-source-return]' ? button : null,
  querySelectorAll:() => [],
  addEventListener:(key, fn) => (listeners[key] ||= []).push(fn)
};
const window = {location:{hash:''}, requestAnimationFrame:fn => fn()};
const activateDetailTab = tab => {selected = tab;};
eval(implementation + '\ninitSourceNavigation();'); // First mount can be a meeting list.
for (const scrollTop of [500, 900]) {
  const old = button;
  button = {hidden:true, closest:key => key === '[data-source-return]' ? button : null};
  const main = {scrollTop};
  const control = {
    isConnected:true, dataset:{seekSeconds:'12', sourceSegment:'synthetic'},
    hasAttribute:key => key === 'data-source-segment',
    closest:key => key === '.detail-page-main' ? main : key === '[data-seek-seconds]' ? control : null,
    focus:() => {control.focused = true;}
  };
  for(const fn of listeners.click) fn({target:control});
  assert.equal(selected, 'recording'); assert.equal(button.hidden, false);
  if(old) assert.equal(old.hidden, true, 'detached previous button stays untouched');
  main.scrollTop = 0;
  for(const fn of listeners.click) fn({target:button});
  assert.equal(selected, 'outcomes'); assert.equal(button.hidden, true);
  assert.equal(main.scrollTop, scrollTop); assert.equal(control.focused, true);
}
assert.equal(listeners.click.length, 1, 'one delegated click handler');
"""
    result = subprocess.run(["node", "-e", harness, str(script)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
