"""Execute notification navigation with the cabinet's existing Node harness pattern."""

import shutil
import subprocess
from pathlib import Path


def test_navigation_acknowledges_only_the_opened_revision():
    script = Path(__file__).resolve().parents[2] / 'src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js'
    harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const source = require('node:fs').readFileSync(process.argv[1], 'utf8');
(async () => {
  const id = '00000000-0000-0000-0000-000000000001';
  const meeting = '00000000-0000-0000-0000-000000000002';
  const path = '/meetings/' + meeting;
  const store = new Map(), requests = [];
  let detail = null, shared = null;
  const context = {
    sessionStorage: {getItem:key => store.get(key), setItem:(key,value) => store.set(key,value), removeItem:key => store.delete(key)},
    location: {pathname:'/meetings', search:''},
    document: {querySelector:selector => selector.includes('data-meeting-id') ? detail : shared},
    fetch:async (url, options) => { requests.push({url, options}); return {ok:true, redirected:false}; },
    URLSearchParams, Date, root:{isConnected:true}, load:async () => {},
    link:{pathname:path, search:''}, card:{isConnected:true},
    item:{id, revision:3, unseen:true}, csrf:'synthetic-source-session-token',
  };
  vm.createContext(context);
  const start = source.indexOf("  const openedNoticeKey =");
  vm.runInContext(source.slice(start, source.indexOf("  let filter = 'important'", start))
    + '\nglobalThis.consume = consumeOpenedNotice;', context);
  const click = source.indexOf('    link.onclick = event => {', start);
  vm.runInContext(source.slice(click, source.indexOf('    if (item.requires_action && item.unseen)', click)), context);
  const event = {button:0};
  const prepare = () => {
    store.clear(); requests.length = 0;
    context.location.pathname = '/meetings'; context.location.search = '';
    context.link.pathname = path; context.link.search = '';
    context.item.revision = 3; detail = null; shared = null;
    context.link.onclick(event);
    assert.equal(requests.length, 0, 'click does not acknowledge before navigation');
  };
  prepare();
  assert.equal(store.size, 1);
  context.location.pathname = path;
  detail = {dataset:{meetingId:meeting}};
  context.item.revision = 4; // A new feed version must not replace the shown revision.
  await context.consume();
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, '/api/v1/notifications/' + id + '/read');
  assert.equal(requests[0].options.body.get('revision'), '3');
  assert.equal(requests[0].options.headers['X-CSRF-Token'], 'synthetic-source-session-token');
  await context.consume();
  assert.equal(requests.length, 1, 'pageshow/settle must not duplicate the read');
  for (const failure of ['no-navigation', 'error-page', 'wrong-meeting', 'expired', 'future', 'malformed']) {
    prepare();
    if (failure !== 'no-navigation') context.location.pathname = path;
    if (failure !== 'error-page') detail = {dataset:{meetingId:meeting}};
    if (failure === 'wrong-meeting') detail.dataset.meetingId = id;
    if (['expired', 'future'].includes(failure)) {
      const key = [...store.keys()][0], pending = JSON.parse(store.get(key));
      pending.createdAt = Date.now() + (failure === 'expired' ? -31000 : 10000);
      store.set(key, JSON.stringify(pending));
    }
    if (failure === 'malformed') store.set([...store.keys()][0], '{');
    await context.consume();
    assert.equal(requests.length, 0, failure);
  }
  prepare();
  context.link.pathname = '/desktop' + path; context.link.onclick(event);
  context.location.pathname = context.link.pathname; detail = {dataset:{meetingId:meeting}};
  await context.consume(); assert.equal(requests.length, 1, 'embedded page');
  prepare();
  context.link.pathname = '/shared-meetings/' + meeting;
  context.link.search = '?workspace_id=' + id;
  context.link.onclick(event);
  context.location.pathname = context.link.pathname; context.location.search = context.link.search;
  shared = {};
  await context.consume(); assert.equal(requests.length, 1, 'authorized shared summary');
  prepare();
  context.link.pathname = '/shared-meetings/' + meeting; context.link.search = '?workspace_id=' + id;
  context.link.onclick(event);
  context.location.pathname = context.link.pathname; context.location.search = '?workspace_id=' + meeting;
  shared = {};
  await context.consume(); assert.equal(requests.length, 0, 'different source workspace');
  for (const modified of [{button:1}, {button:0,metaKey:true}, {button:0,ctrlKey:true}, {button:0,shiftKey:true}]) {
    store.clear(); context.link.onclick(modified); assert.equal(store.size, 0, 'new tab has no current-tab read intent');
  }
  context.sessionStorage.setItem = () => { throw new Error('disabled'); };
  assert.doesNotThrow(() => context.link.onclick(event), 'disabled storage must preserve navigation');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    node = shutil.which('node')
    assert node, 'Node is required for executable notification navigation checks'
    subprocess.run([node, '-e', harness, str(script)], check=True, capture_output=True, text=True)


def test_inbox_clears_revoked_content_and_reopens_important():
    script = Path(__file__).resolve().parents[2] / 'src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js'
    harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const source = require('node:fs').readFileSync(process.argv[1], 'utf8');
(async () => {
  let cleared = 0;
  const context = {
    read:{}, scopeEpoch:0, card:{isConnected:true}, item:{id:'synthetic',revision:1},
    csrf:'synthetic', URLSearchParams, status:{textContent:''},
    clear:() => { cleared++; context.card.isConnected = false; },
    heading:{focus:()=>{}}, link:{focus:()=>{}}, load:async()=>{},
    fetch:async()=>({ok:false,status:404,redirected:false}),
  };
  vm.createContext(context);
  const start = source.indexOf('      read.onclick = async () => {', source.indexOf('const openedNoticeKey'));
  vm.runInContext(source.slice(start, source.indexOf('      }; card.append(read);', start)) + '      };', context);
  for (const code of [401,403,404,410]) {
    context.card.isConnected = true;
    context.fetch = async()=>({ok:false,status:code,redirected:false});
    await context.read.onclick();
    assert.equal(context.card.isConnected,false);
  }
  assert.equal(cleared,4);
  context.card.isConnected=true;
  context.fetch=async()=>({ok:false,status:500,redirected:false});
  await context.read.onclick();
  assert.equal(cleared,4); assert.equal(context.read.disabled,false);
  const filters = ['important','history'].map(value=>({dataset:{notificationFilter:value},setAttribute:(name,v)=>{ if(name==='aria-pressed') context[value]=v; }}));
  Object.assign(context,{bell:{setAttribute:()=>{}},panel:{hidden:true},filter:'history',root:{querySelectorAll:()=>filters}});
  const open=source.indexOf('  bell.onclick = event => {',start);
  vm.runInContext(source.slice(open,source.indexOf("  root.querySelector('[data-notification-close]')",open)),context);
  context.bell.onclick({preventDefault:()=>{}});
  assert.equal(context.filter,'important'); assert.equal(context.important,'true'); assert.equal(context.history,'false');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    subprocess.run([shutil.which('node'), '-e', harness, str(script)], check=True, capture_output=True, text=True)
