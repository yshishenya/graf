# Iconography And Expression

## Rules

- Use familiar action icons for Stop, upload, retry, browser handoff, transcript, notes, access, and delete.
- Icons require text labels when meaning is privacy/security critical.
- Do not use icons copied from Krisp or OS recording indicators.
- Active recording indicator must be distinct from macOS system indicator while still unmistakable.
- Prefer lucide-style simple line icons in web prototypes and native SF Symbols
  equivalents in macOS implementation.
- Use icons inside buttons when an established symbol exists; use text buttons
  for ambiguous commands such as `Regenerate notes` or `Open in browser`.
- Risky menu items use icon plus text plus confirmation, not color alone.

## Expression

- Calm operational surfaces.
- Warning and deletion copy is factual, not alarming.
- Empty states are useful and compact.
- Recording language is direct: `Recording`, `Stopping`, `Saved locally`,
  `Uploading`, `Upload failed`.
- AI language is scoped: `Ask this meeting`, `Ask all visible meetings`, `No
  answer from this transcript`.
- Recovery language names the next action: `Grant microphone access`, `Retry
  upload`, `Open billing in browser`, `Choose another file`.

## Suggested Icon Map

| Meaning | Icon family direction | Label required |
|---|---|---|
| Start recording | circle-dot / mic | Yes |
| Stop recording | square | Yes |
| Local package | hard drive | Yes |
| Upload | upload cloud | Yes |
| Retry | rotate clockwise | Yes |
| Browser handoff | external link | Yes |
| Search | search | No when in search input |
| Filter | list filter | No with active chips nearby |
| Transcript | file text | Yes |
| Notes | notebook tabs | Yes |
| AI drawer | sparkles or message circle | Yes, because scope matters |
| Access/share | users or link | Yes |
| Delete | trash | Yes |
| Warning | triangle alert | Yes |
| Ready/success | check circle | Yes in status badges |
