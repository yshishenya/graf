# Research: Понятное меню действий со встречей

## Decision 1: `Ещё` is a short contextual action menu

**Decision**: Keep `Поделиться` visible and use `Ещё` for a maximum of four
secondary actions: export, audio download, meeting details and delete. Do not
show the current file/policy/activity dashboard inside the menu.

**Rationale**:

- [Apple Human Interface Guidelines — Menus](https://developer.apple.com/design/human-interface-guidelines/menus)
  describes menus as space-efficient collections of commands related to the
  current context and recommends familiar, concise organization.
- [WAI-ARIA APG — Menu Button](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/)
  defines the expected button state, menu relationship and keyboard entry.
- Feature 121 already establishes the same GRAF IA: `Поделиться` is visible;
  `Экспортировать…`, `Скачать аудио…`, `Сведения о встрече…` and
  `Удалить встречу…` live under `Ещё`.

**Alternatives considered**:

- Retain the large modal: rejected because it mixes commands with operational
  truth and requires scanning a technical dashboard before acting.
- Move all actions into a permanent side panel: rejected because the actions
  are secondary and would compete with transcript/summary review.
- Put audio and content under a nested `Сохранить` submenu: rejected for this
  four-action scope because it adds a step without reducing meaningful load.

## Decision 2: Use a single level with plain labels and two short explanations

**Decision**: The first selected visual concept is authoritative. Use
`Экспортировать…` + `Расшифровка или итоги`, `Скачать аудио…` +
`Исходная запись`, `Сведения о встрече`, divider, then `Удалить встречу…`.

**Rationale**:

- [Otter export guidance](https://help.otter.ai/hc/en-us/articles/39503855767191-Export-Summary)
  keeps export close to the meeting's main actions and uses a single entry into
  the export flow; [Otter sharing guidance](https://help.otter.ai/hc/en-us/articles/360048338793-Share-a-conversation)
  keeps sharing visibly separate.
- [Fireflies download guidance](https://guide.fireflies.ai/articles/3319752033-how-to-download-transcripts-summaries-and-meeting-recordings-from-fireflies)
  exposes only content that exists and clearly distinguishes transcript,
  summary, video and audio outcomes.
- [Krisp sharing](https://help.krisp.ai/hc/en-us/articles/10386573495196-Sharing-your-meetings-with-Krisp)
  and [recording download](https://help.krisp.ai/hc/en-us/articles/11734566901788-Recording-your-meetings-with-Krisp)
  keep sharing and recording download legible as separate tasks.

These are behavior benchmarks only. GRAF keeps its own language, tokens,
spacing, icon source and interaction details.

**Alternatives considered**:

- Group labels such as `Сохранить` and `Встреча`: rejected because four actions
  remain faster to scan without extra headings.
- No helper text: rejected because users need to distinguish text/data export
  from the source audio without opening both flows.
- Long explanations: rejected because they recreate the cockpit problem.

## Decision 3: Keep details reachable, but separate from quick action choice

**Decision**: Move the existing files, deletion/lifecycle truth, revision,
calendar context, speakers and activity into a separate named details dialog.
Do not delete the information or create a new details data source.

**Rationale**: Information remains available in two actions while the quick menu
stays task-oriented. The existing server projection already supplies the
correct capability-filtered information, so moving presentation is smaller and
safer than introducing another route or client model.

**Alternatives considered**:

- Remove operational details: rejected because files, policy truth, provenance
  and deletion reporting are trust surfaces.
- Add a new details page: rejected because it adds navigation, routing and
  context loss for information already present in the meeting response.

## Decision 4: Preserve capability filtering and fail closed at the server

**Decision**: Continue deriving availability from `MeetingReviewResponse` and
the existing export/audio/delete policy projections. Omit unavailable actions
from the menu; do not expose policy/debug reasons there; keep final server-side
authorization and egress rechecks unchanged.

**Rationale**:

- [Zoom cloud recording management](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0062627)
  and [Zoom recording sharing](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0086067)
  bind download/share/delete controls to role and recording state.
- [Fireflies mobile meeting actions](https://guide.fireflies.ai/articles/4488163074-how-to-access-meeting-recordings-and-transcripts-in-the-fireflies-mobile-app)
  places share/download/delete in a short contextual menu and retains owner-only
  deletion.
- Local evidence shows the final export, audio and delete operations are already
  server mediated. Client visibility is presentation, never authorization.

**Alternatives considered**:

- Disabled rows with policy reasons: rejected because the current page becomes
  a technical capability matrix and leaks internal explanation into a simple
  action choice.
- Client-side capability reconstruction: rejected because it duplicates trust
  logic and can drift from the server.

## Decision 5: Keep destructive action last and separately confirmed

**Decision**: Place delete at the bottom after a divider, use both icon/text and
danger color, then invoke the existing confirmation with bounded deletion truth
and report access.

**Rationale**:

- [Fathom delete guidance](https://help.fathom.video/en/articles/4290753)
  places `Delete Call` in the three-dot menu and treats it as an irreversible,
  explicitly confirmed action.
- Existing GRAF constitution requires truthful deletion scope and prohibits
  promises beyond GRAF-controlled systems.

**Alternatives considered**:

- Inline delete confirmation inside the menu: rejected because consequences
  and lifecycle truth need a separate focused surface.
- Hide delete inside details: rejected because it becomes hard to find and mixes
  action with information.

## Decision 6: Implement the complete menu-button keyboard contract

**Decision**: The trigger exposes expanded/menu state. Enter/Space and arrows
open; Up/Down/Home/End move focus; Escape and outside click close; focus returns
to `Ещё`. Dialogs trap focus and return to the visible opener. Action targets
are at least 40 CSS px.

**Rationale**:

- [WAI-ARIA APG — Menu and Menubar](https://www.w3.org/WAI/ARIA/apg/patterns/menubar/)
  specifies arrow/Home/End/Escape behavior and uses an ellipsis for commands
  that open a dialog.
- The current markup declares `role="menu"` but the current script does not
  implement the corresponding arrow-key model; aligning behavior removes the
  semantic mismatch.

**Alternatives considered**:

- Keep a modal dialog for accessibility: rejected because a menu button is the
  correct interaction and can be made fully keyboard accessible.
- Remove ARIA roles but keep a generic disclosure: rejected because these are
  application commands rather than navigation links alone.

## Decision 7: Reuse the existing GRAF surface and icon source

**Decision**: Reuse current cabinet color variables, focus ring, motion/contrast
media queries and `icons.html`. Add an icon to the existing source only if no
current glyph describes an action. Add no UI package.

**Rationale**: [Descript publishing guidance](https://help.descript.com/hc/en-us/articles/10255817744653-Publish-content-with-Descript-web-links)
also keeps export prominent while separating project/share settings, but GRAF
must remain clean-room. Reusing the product's own primitives gives the smallest
brand-safe diff.

**Alternatives considered**:

- New component library: rejected as unnecessary dependency and visual drift.
- Handcrafted one-off SVGs in the fragment: rejected because icons belong in
  the existing reviewed icon source.

## Current Code Evidence

- `meeting_governance.html` currently renders a modal with quick actions,
  `Файлы`, deletion truth, delete confirmation and a details disclosure.
- `cabinet.css` fixes that modal near 560 px wide and dims the entire page.
- `initMeetingContextPanels` already manages trigger state, Escape and focus
  return, but its menu branch needs outside-click and arrow-key behavior.
- Existing export, download and delete flows already provide the required
  policy, audit, revision and lifecycle enforcement; no endpoint change is
  justified.

## Research Conclusion

The selected first concept is also the strongest product choice: one shallow
menu, plain labels, two differentiating explanations, details on demand and a
separated destructive action. It is both simpler for users and the smallest
safe implementation because it reuses every authoritative backend flow.
