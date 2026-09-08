"""Execute the real browser helpers with a deterministic clock/transport."""
import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(not os.environ.get("GRAF_NODE_MODULES"), reason="Explicit installed Playwright path required")
def test_first_transcript_refresh_keeps_live_audio_and_comment_draft() -> None:
    script = Path(__file__).parents[1] / "browser/playback-refresh.test.cjs"
    subprocess.run(["node", str(script)], check=True, capture_output=True, text=True, timeout=60)


def test_partial_summary_is_available_with_limits_in_detail_and_list() -> None:
    script = Path(__file__).parents[2] / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    subprocess.run(["node", "-e", r'''
const fs = require('fs'), assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8');
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const processingProjectionMatchesDetail = () => true, processingProjectionIsStale = () => false;
const processingTimestamp = () => null, processingTerminalFailure = () => false;
const processingTranscriptReady = () => true, processingArtifactState = () => 'available';
const processingArtifactVisible = () => true, updateProcessingExportVisibility = () => {};
const processingSummaryState = (projection) => projection.summary_status;
const processingSummaryPending = () => false;
const stages = new Map(), updateProcessingStage = (_, name, state, label) => stages.set(name, {state, label});
const detail = {dataset: {}, querySelector() {return null;}};
const document = {activeElement: null, querySelector() {return null;}};
const rowText = {dataset: {}, textContent: ''};
const row = {isConnected: true, dataset: {meetingId: 'synthetic'}, contains() {return false;}, querySelector() {return rowText;}};
const currentList = () => ({contains: () => true}), requestMeetingListRefresh = () => false;
const meetingListRequestGeneration = 1, processingListProjectionStates = new Map();
eval(section('const processingSummaryCopy =', 'const processingTerminalReasonCopy')
  + section('const renderProcessingProjection =', 'const focusProcessingRecovery')
  + section('const renderProcessingListProjection =', 'const requestProcessingListProjection') + `
  for (const summary_status of ['partial', 'available', 'generating']) {
    const projection = {meeting_id: 'synthetic', state: 'processed', summary_status};
    renderProcessingProjection(detail, projection);
    renderProcessingListProjection(row, projection, 1);
    if (summary_status === 'partial') {
      assert.deepStrictEqual(stages.get('summary'), {state: 'ready', label: 'Доступно частично'});
      assert(rowText.textContent.includes('итоги доступны частично'));
    } else if (summary_status === 'available') {
      assert.deepStrictEqual(stages.get('summary'), {state: 'ready', label: 'Готово'});
      assert(rowText.textContent.includes('итоги готовы'));
    } else {
      assert.strictEqual(stages.get('summary').state, 'active');
    }
  }
`);
''', str(script)], check=True, capture_output=True, text=True)


def test_summary_polling_survives_delay_and_partial_is_ready() -> None:
    script = Path(__file__).parents[2] / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    subprocess.run(["node", "-e", r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8');
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
vm.runInThisContext(section('const processingSummaryPending', 'const processingTranscriptReady'));
assert(processingSummaryPending('blocked_dependency'));
let candidateRequestGeneration = 1, pollingTimer = null, pollAttempts = 100, pollDeadline = 1, pollDelay = 1200;
let delay = null;
const controls = {isConnected: true};
const document = {hidden: false};
const window = {clearTimeout(){}, setTimeout(fn, ms){delay = ms; return 1;}};
const setBusy = () => {}, showStatus = () => {}, resumeCandidatePolling = () => {}, dismissStatus = () => {};
const pollCandidate = () => {};
eval(section('const schedulePoll =', 'const pollCandidate =') + ';schedulePoll({poll_url:"/safe"}, 1);');
assert(delay > 0 && delay <= 15000, 'long preparation must continue automatically');
assert(section('const refreshProcessingDetailContentOnce', 'const renderProcessingProjection').includes('"partial"'));
''', str(script)], check=True, capture_output=True, text=True)


def test_summary_refresh_retries_network_and_keeps_request_baseline() -> None:
    script = Path(__file__).parents[2] / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    subprocess.run(["node", "-e", r'''
const fs = require('fs'), assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8');
const start = source.indexOf('const pollSummaryRefresh =');
const section = source.slice(start, source.indexOf('const requestSummaryRefresh =', start));
let candidateRequestGeneration = 1, currentOutcomeSetId = 'old', refreshBaselineOutcomeSetId = 'old';
let pollingTimer, candidateRequestInFlightGeneration = 1, pollDeadline = 1;
let timers = [], messages = [], refreshed = [];
const controls = {isConnected:true}, document = {hidden:false};
const window = {setTimeout(fn, ms){timers.push({fn, ms}); return timers.length;}};
const recoverMeetingDetailFromResponse = async () => false, summaryActionProblemCodes = [];
const isMeetingDetailRecoveredError = () => false, setBusy = () => {};
const showStatus = (message) => messages.push(message);
const reloadAfterSummaryChange = (template) => refreshed.push(template.key);
const meetingId = 'synthetic', template = {key:'outline'};
let replies = [new TypeError('offline'), {current_outcome_set_id:'new', catalog_entry:{generation_state:'updating'}},
  {current_outcome_set_id:'new', catalog_entry:{generation_state:'idle'}}];
const fetch = async () => {
  const reply = replies.shift();
  if (reply instanceof Error) throw reply;
  return {ok:true, json: async () => reply};
};
eval(section + ';global.pollSummaryRefresh = pollSummaryRefresh;');
(async () => {
  await global.pollSummaryRefresh(template, 1);
  assert(timers[0].ms === 15000 && refreshed.length === 0);
  await timers.shift().fn();
  assert(currentOutcomeSetId === 'new' && refreshed.length === 0);
  await timers.shift().fn();
  await timers.shift().fn();
  assert.deepEqual(refreshed, ['outline'], 'publication must compare with request baseline, not previous poll');
  controls.isConnected = false;
  await global.pollSummaryRefresh(template, 1);
  assert(timers.length === 0, 'detached screen must stop polling');
})().catch(error => {console.error(error); process.exitCode = 1;});
''', str(script)], check=True, capture_output=True, text=True)


def test_selected_partial_fragment_waits_for_real_content_without_reloading_player() -> None:
    script = Path(__file__).parents[2] / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    subprocess.run(["node", "-e", r'''
const fs = require('fs'), assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8');
const section = source.slice(source.indexOf('const refreshProcessingDetailContentOnce'), source.indexOf('const renderProcessingProjection'));
let processingRecoveryGeneration = 1, processingRecoveryPollTimer = null;
let calls = 0, replacements = 0, timers = [];
const window = {location:{href:'http://localhost/desktop/meetings/synthetic', reload(){throw Error('reload forbidden');}},
  setTimeout(fn){timers.push(fn); return timers.length;}};
const document = {activeElement:null};
const titleEditorActive = () => false, processingTranscriptReady = () => false;
const processingSummaryState = p => p.summary_status, processingSummaryPending = () => false;
const processingProjectionMatchesDetail = () => true, recoverMeetingDetailFromResponse = async () => false;
const stopProcessingRecoveryCountdown = () => {}, stopProcessingRecoveryPolling = () => {};
const detail = {dataset:{playbackPollUrl:'/desktop/meetings/synthetic', summaryRenderedState:'deferred'},
  isConnected:true, querySelector:()=>null, contains:()=>false,
  nextElementSibling:{matches:()=>true, querySelector(){throw Error('player must not be touched');}},
  replaceWith(){this.isConnected=false; replacements++;}};
const next = {dataset:{summaryRenderedState:'available'}, querySelector:()=>({dataset:{currentTemplateKey:'outline'}})};
const fetch = async (url, options) => {
  assert(new URL(url).searchParams.get('summary_format') === 'outline');
  assert(options.cache === 'no-store'); calls++;
  return {ok:true, text:async()=>String(calls)};
};
const DOMParser = class {parseFromString(text){return {querySelector(selector){
  if (selector === '.detail-playback') return null;
  return text === '1' ? {...next, dataset:{summaryRenderedState:'processing'}} : next;
}};}};
eval(section + ';global.refreshDetail = refreshProcessingDetailContentOnce;');
(async()=>{
  await global.refreshDetail(detail, {summary_status:'partial'}, {forceSummary:true, summaryTemplate:'outline'});
  assert(replacements === 0 && timers.length === 1, 'pending fragment is not marked ready');
  await global.refreshDetail(detail, {summary_status:'available'});
  assert(calls === 1, 'generic default poll cannot replace selected format');
  timers.shift()(); await new Promise(setImmediate);
  assert(replacements === 1 && calls === 2 && next.dataset.processingSummaryContentReady === 'true');
})().catch(error=>{console.error(error);process.exitCode=1;});
''', str(script)], check=True, capture_output=True, text=True)
