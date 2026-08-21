# Visual and interaction QA

## Result

PASS for the integrated landing, download page and representative legal pages on the tested responsive matrix. One real issue was found at 280 px: the hero headline and CTA were clipped. A dedicated `max-width: 340px` rule corrected the typography and spacing; the repeated 280 px measurement is exactly within the 252 px content box.

## Viewports

- 1440×1000: hero, all product tabs, pricing and download page.
- 1024×768 and 768×1024: responsive transition and 200%-zoom-equivalent CSS width.
- 390×844: mobile hero, menu, transcript tab, download and legal pages.
- 320×800: narrow mobile hero.
- 280×653: hero, outcomes tab, pricing and download page after remediation.

Every measured viewport has `documentElement.scrollWidth == clientWidth`. Product tabs switch by mouse and keyboard (`ArrowRight`, `End`), update `aria-selected`/`tabindex`, and expose the matching panel. The mobile menu updates `aria-expanded` and closes after navigation. The 390 and 280 screenshots confirm readable wrapping rather than clipped content.

The in-app browser does not expose a native zoom override; the 768 px responsive pass covers the CSS viewport produced by a 1440 px desktop at approximately 200% zoom. Reduced-motion behavior is separately enforced by both CSS and JavaScript contracts. Image-independent copy and meaningful alt text are present; no essential instruction exists only inside a screenshot.

Evidence is stored under `validation/screenshots/`. Full-page animated stitching was deliberately excluded because it duplicated moving sections in the capture artifact; viewport screenshots are the authoritative visual evidence.
