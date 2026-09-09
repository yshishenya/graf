import subprocess
from pathlib import Path


def test_source_text_fits_the_document_above_the_player_at_high_zoom():
    script = Path(__file__).resolve().parents[2] / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    harness = r"""
const assert = require('node:assert/strict');
const source = require('node:fs').readFileSync(process.argv[1], 'utf8');
const implementation = source.slice(source.indexOf('  const scrollTranscriptTurnIntoView ='), source.indexOf('  const initSourceNavigation ='));
const getComputedStyle = element => ({position:element.position});
let reveal;
eval(implementation + '\nreveal = scrollTranscriptTurnIntoView;');
for (const [mainTop, mainHeight, headerBottom, turnTop, turnHeight, textTop, textHeight] of [
  [0, 104, 0, -18.5, 141.4, 38.9, 84], // 200%: text fits, speaker + text do not.
  [57, 36, 0, 18.5, 113.4, 75.9, 56], // Text exceeds the viewport: show its beginning.
  [0, 355, 166, 100, 220, 157, 163], // Only the space below the sticky header is readable.
]) {
  let shift = 0;
  const header = {position:headerBottom ? 'sticky' : 'static', getBoundingClientRect:() => ({bottom:headerBottom})};
  const main = {scrollTop:400, querySelector:() => header,
    getBoundingClientRect:() => ({top:mainTop, bottom:mainTop + mainHeight}),
    scrollTo:options => {shift = options.top - main.scrollTop; assert.equal(options.behavior, 'auto');}};
  const text = {getBoundingClientRect:() => ({top:textTop, height:textHeight})};
  const turn = {closest:() => main, querySelector:() => text,
    getBoundingClientRect:() => ({top:turnTop, height:turnHeight}),
    scrollIntoView:() => assert.fail('do not scroll outer containers')};
  reveal(turn);
  const visibleTop = Math.max(mainTop, headerBottom);
  assert.ok(textTop - shift >= visibleTop, 'the first line is below the header');
  if (textHeight <= mainTop + mainHeight - visibleTop) {
    assert.ok(textTop - shift + textHeight <= mainTop + mainHeight, 'the last line is above the player');
  } else assert.ok(Math.abs(textTop - shift - visibleTop) < 1e-7, 'a long source starts at its first line');
}
let resize, observed = [], scrolls = false;
const detail = {clientHeight:196};
const header = {offsetHeight:166, classList:{toggle:(_name, value) => {scrolls = value;}}};
const form = {dataset:{}, isConnected:true, closest:key => key === '[data-meeting-id]' ? detail : header};
const document = {querySelector:() => form, documentElement:{}};
const window = {innerHeight:450};
class ResizeObserver {constructor(callback) {resize = callback;} observe(element) {observed.push(element);} disconnect() {}}
let meetingTitleHeaderObserver = null;
const editorStart = source.slice(source.indexOf('  const initMeetingTitleEditor ='), source.indexOf('    const input = form.querySelector("[data-meeting-title-input]");'));
eval(editorStart + '\n}; initMeetingTitleEditor();');
assert.ok(observed.includes(detail), 'player resize must update the header without resizing the window');
resize(); assert.equal(scrolls, true, 'the header yields space in a short document');
detail.clientHeight = 720;
resize(); assert.equal(scrolls, false, 'the header remains sticky when space is available');
(() => {
  const frames = [];
  let layoutReady = false, revealed = false;
  const turn = {dataset:{sourceSegments:'current-segment', startSeconds:'2'}, focus:() => {}};
  const document = {body:{dataset:{}}, addEventListener:() => {},
    querySelectorAll:selector => selector === '[data-transcript-turn]' ? [turn] : [], querySelector:() => null};
  const window = {location:{hash:'#graf-source=current-segment'}, requestAnimationFrame:fn => frames.push(fn)};
  const activateDetailTab = () => {};
  const scrollTranscriptTurnIntoView = target => {
    assert.equal(target, turn);
    assert.ok(layoutReady, 'initial source waits for the header/player resize delivery');
    revealed = true;
  };
  eval(source.slice(source.indexOf('  const initSourceNavigation ='), source.indexOf('  const DEFAULT_TIMELINE_HEIGHT =')) + '\ninitSourceNavigation();');
  frames.shift()();
  layoutReady = true; // Browsers deliver the first ResizeObserver after animation callbacks.
  while (frames.length) frames.shift()();
  assert.ok(revealed, 'the current segment opens after initial layout');
})();
"""
    result = subprocess.run(["node", "-e", harness, str(script)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
