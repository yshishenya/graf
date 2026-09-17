import subprocess
from pathlib import Path


def test_copy_and_download_requests_omit_sources_but_preserve_transcript_options():
    script = Path(__file__).resolve().parents[2] / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    harness = r"""
const assert = require('node:assert/strict');
const source = require('node:fs').readFileSync(process.argv[1], 'utf8');
const start = source.indexOf('    const include = (name) => form.querySelector');
const end = source.indexOf('    const setBusy =', start);
assert.ok(start >= 0 && end > start);
let checked = true;
const form = {
  dataset: {processingResultId:'saved-result', outcomeSetId:'saved-outcomes',
    csrfToken:'synthetic-csrf', endpoint:'/synthetic/content-exports'},
  querySelector:() => ({checked}),
};
const scope = {value:'summary'}, format = {value:'txt'};
const available = () => true;
const recoverMeetingDetailFromResponse = async () => false;
const fetch = async (url, options) => {
  assert.equal(url, form.dataset.endpoint);
  assert.equal(options.headers['X-CSRF-Token'], 'synthetic-csrf');
  return {ok:true, payload:JSON.parse(options.body)};
};
let request;
eval(source.slice(start, end) + '\nrequest = requestExport;');
(async () => {
  for (checked of [true, false]) {
    for (const selectedScope of ['summary', 'combined', 'transcript']) {
      for (const selectedFormat of ['txt', 'md', 'xlsx', 'json']) {
        const {payload} = await request(selectedFormat, selectedScope);
        assert.equal(payload.include_evidence, false, 'sources are UI-only for every export');
        assert.equal(payload.include_timestamps, checked);
        assert.equal(payload.include_speaker_labels, checked);
        assert.equal(payload.content_scope, selectedScope);
        assert.equal(payload.format, selectedFormat);
        assert.equal(payload.processing_result_id, 'saved-result');
        assert.equal(payload.outcome_set_id, selectedScope === 'transcript' ? null : 'saved-outcomes');
      }
    }
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
"""
    result = subprocess.run(["node", "-e", harness, str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
