# Research: Боковая навигация настроек

## Evidence

- The existing canonical model is `settings_category_navigation()` in
  `apps/server/src/twobrain_rec_server/cabinet/view_models.py`. It already
  defines five actionable safe, explicit categories and builds
  browser/embedded prefixes; the overview remains a separate `/settings`
  entry point.
- `settings_navigation.html` is imported by all settings pages and by the
  calendar/provider-link surfaces. A shared macro is therefore the smallest
  parity-preserving change.
- The existing CSS uses a horizontal flex row with `overflow-x: auto`, which
  makes the information architecture undiscoverable on narrow windows.
- The global cabinet sidebar is a separate navigation landmark. The requested
  menu is an inner settings rail and must not replace or broaden the global
  shell navigation.
- The supplied Krisp screenshots are a structural reference for grouped left
  navigation, selected state and density. They are not a source for GRAF copy,
  icons or branding.

## Decisions

1. Add presentation-only group metadata to the existing view model. Route
   identity, href construction, scope and authorization remain unchanged.
2. Render visible group headings in the existing semantic `nav`; links remain
   ordinary anchors, not tabs or a client-side application router.
3. Use a desktop CSS grid with a fixed-width inner rail and a flexible content
   column. At `max-width: 640px`, switch to one column and keep the complete
   menu as a normal vertical block.
4. Keep scope labels in page content, where they explain impact without making
   the rail too wide. The overview does not repeat the category links because
   the rail is the primary navigation mechanism.
5. Reuse existing focus-visible styles, spacing variables and color tokens. No
   new dependency, icon system or JavaScript behavior is needed.

## Alternatives rejected

- A new client-side settings router would duplicate the server route map and
  create browser/embedded drift.
- Duplicating a custom menu in every template would make calendar and
  provider-link parity fragile.
- A horizontal scroller would preserve the current discoverability problem and
  fail the 320px reachability requirement.
- Moving scopes into groups would conflate where a setting applies with what
  user task it supports.
- Replacing the global cabinet sidebar would broaden this slice into unrelated
  meeting navigation and route-policy work.

## Open limitation

The production in-app browser navigation timed out during audit setup. The
implementation will therefore use server render contracts, local focused tests,
CSS inspection and the repository CI gate as evidence until a reachable local or
deployed browser target is available.
