const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js'), 'utf8');
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const listeners = {};
const document = { activeElement: null };
const button = () => ({ matches: () => false, focus() { document.activeElement = this; }, addEventListener() {} });
const cancel = button(), confirm = button(), opener = button();
const dialog = {
  open: true, dataset: {},
  querySelectorAll: () => [cancel, confirm],
  querySelector: () => cancel,
  addEventListener: (name, handler) => { listeners[name] = handler; },
};
document.querySelector = selector => selector === '[data-meeting-delete-dialog]' ? dialog : opener;
vm.runInNewContext(`
  ${section('const modalFocusTargets =', 'const updateSelection =')}
  ${section('const initMeetingDeleteDialog =', 'const initShareDialogs =')}
  initMeetingDeleteDialog();
`, { document, isUsableFocusTarget: () => true });

// WebKit may skip buttons in its native Tab order: every transition must be handled.
for (const [from, shiftKey, to] of [
  [null, false, cancel], [cancel, false, confirm], [confirm, false, cancel],
  [cancel, true, confirm], [confirm, true, cancel],
]) {
  document.activeElement = from;
  let prevented = false;
  listeners.keydown({ key: 'Tab', shiftKey, preventDefault() { prevented = true; } });
  assert.equal(prevented, true, 'Tab must not escape into native app controls');
  assert.equal(document.activeElement, to);
}
console.log('meeting delete keyboard focus passed');
