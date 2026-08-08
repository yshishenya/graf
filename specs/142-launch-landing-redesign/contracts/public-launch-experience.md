# Public Launch Experience Contract

## Route contract

| Route | Primary purpose | Primary action | Secondary action |
|---|---|---|---|
| `/` | Explain GRAF and prove current value | `/download` | existing login path or first proof anchor |
| `/download` | Explain platform availability and installation | release-gated macOS package | existing login path |

## Landing information contract

The page order is:

1. Minimal header.
2. Platform-neutral hero.
3. `01 / В привычных сервисах` — truthful recording scope and visible Pause/Stop state.
4. `02 / После встречи` — real outcome UI and source-backed value.
5. `03 / Управляемый контур` — Russian and locally deployed models without unsupported locality claims.
6. Final download/login CTA and muted platform note.

The selected visual reference is `../design/selected-direction-3.png`. Its generated product panels are not runtime evidence and MUST NOT ship as screenshots.

## Final copy matrix

| Surface | Published copy | Evidence / boundary |
|---|---|---|
| Hero | `Встреча закончится` / `Главное останется` | Two balanced display lines without terminal punctuation; platform-neutral product promise with no auto-record or universal-service claim. |
| Capture | `Запись не зависит от сервиса встречи` | Manual system-audio capture works without a service-specific integration. |
| Service rail | Curated native targets from registry `2026.07.21.1` | Text pills indicate where GRAF may suggest recording; they are not partner logos or a universal compatibility matrix. |
| Browser note | `Google Meet и другие браузерные встречи — с ручным стартом записи.` | Browser targets remain `manual_or_browser_only`. |
| Outcome | `Сразу понятно, что делать дальше` | Real accepted-outcome UI proves `Кратко`, `Действия`, `Решения`, `Источник`. |
| AI | `Российские и локальные модели` | Supporting copy preserves the exact boundary: Russian and locally deployed models operate in a managed GRAF contour; no fully local or zero-egress promise. |
| Control | `Состояние, пауза и остановка всегда рядом` | Rendered from the current `CaptureStatusItem` with a synthetic active session. |
| Platforms | `macOS — доступно сейчас · Windows и Linux — скоро` | Product owner explicitly accepted the undated roadmap status; only macOS is actionable. |
| Payment | Not published | Price and YooKassa remain blocked until the approved catalog and checkout are live. |

## Copy boundary

Allowed current claims:

- GRAF records meeting audio on the computer without a bot in the call.
- Manual system-audio recording does not require a service-specific integration.
- Approved supported targets may use the existing policy-gated auto-recording flow.
- After processing, GRAF provides transcript, concise outcome, decisions and next actions that can be checked against source timestamps.
- Active recording is visible and can be paused or stopped.
- The landing remains platform-neutral; `/download` shows macOS now and undated Windows/Linux `Скоро` statuses.
- GRAF uses Russian and locally deployed models in a managed processing contour, without claiming that every content-bearing route is local or Russia-only.

Blocked until separate evidence exists:

- universal capture or auto-recording in every app;
- `за рубеж ничего не уходит`, Russia-only processing or fully local processing;
- public naming or guarantee of any model/provider;
- ruble payment, YooKassa checkout, tariff amount or auto-renewal;
- Apple verification for a package without authoritative Developer ID/notarization evidence;
- Windows/Linux dates.

## Product proof contract

- Every shipped product screenshot is captured from current GRAF runtime.
- Content is synthetic and contains no names of real people or companies, email, phone, meeting URL, secret, credential path or customer material.
- Each proof has visible HTML copy explaining the value and an adjacent demonstration-data label.
- Desktop and mobile may use separate captures; a full desktop screen is not reduced into unreadable mobile decoration.
- Screenshot failure never removes the text explanation.

## Platform availability contract

- macOS is the only interactive download choice while it is the only supported public platform; release/deploy gates remain responsible for proving the mounted package is the verified public artifact.
- Windows and Linux are static status rows, not disabled controls.
- No release date appears without an approved release slice.
- Installer trust copy is limited to `Подписано разработчиком и проверено Apple`, backed by the current signed, notarized, stapled and Gatekeeper-accepted public package. Version-specific metadata remains in the release receipt rather than hard-coded into the page.
- The active macOS link remains the existing runtime-mounted package URL; the release process owns Developer ID/notarization verification before deployment.

## Accessibility and resilience contract

- One `h1`; ordered `h2` chapters; a working skip link; semantic navigation and sections.
- All actions have visible `:focus-visible` state and at least 44×44 CSS px target size.
- No horizontal scrolling at 320 CSS px.
- Meaning does not depend on color, image loading, motion or JavaScript.
- `prefers-reduced-motion: reduce` disables smooth scrolling and decorative transforms/transitions.
- Decorative images use empty alternatives; product proofs have concise, value-oriented alternatives.

## Analytics contract

Existing consent-aware event names and locations remain stable:

- sections: `hero`, `platforms`, `outcomes`, `trust`, `final_cta`;
- CTAs: existing labels stay allowlisted; the hero proof anchor adds `hero_product`, while `header_download`, `hero_download`, `final_download`, `final_login`, `download_page_installer` and `download_page_login` remain active.

No meeting content, screenshot content, price, payment identifier or personal data is added to analytics payloads.
