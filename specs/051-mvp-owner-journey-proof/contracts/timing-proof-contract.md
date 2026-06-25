# Contract: Processing Timing Proof

## Required Fields

Timing proof must record:

- redacted production candidate reference;
- recording duration in seconds, or `unknown`;
- queue/wait duration, or `unknown`;
- workflow processing duration, or `unknown`;
- provider processing duration, or `unknown`;
- finalize-to-review duration, or `unknown`;
- target of `180` seconds per one hour of audio;
- result: `pass`, `fail`, or `unproven`;
- a metadata-only note explaining which intervals were measured.

## Target Rule

- A direct representative one-hour or near-one-hour production run may pass or
  fail the target.
- A short production run may prove pipeline health, but must not be extrapolated
  into a timing pass.
- If queue or dependency wait dominates owner-visible wait, the evidence must
  state that separately.

## Privacy Rule

Timing evidence must not include transcript text, private meeting names, raw
audio, object keys, account identifiers, cookies, tokens, or signed URLs.
