# Contract: web and embedded desktop billing parity

- Web and macOS render the same server templates, data, actions and state copy.
- No new billing route is introduced. Existing exact desktop allowlist remains
  authoritative and unknown billing siblings fail closed.
- `/offer` remains external with canonical sanitized same-origin URL. Provider
  navigation remains limited to the existing checkout-origin and HTTPS host
  allowlist policy.
- Desktop window coverage: 1040×680, 1280×760 and 1440 fullscreen; native
  inspector collapsed/expanded produces approximate WebView widths 987/731,
  1227/971 and 1387/1131 px.
- Required web coverage: 390×844, 768×1024, 1024×768, 1280×720 and 1440×900.
- Critical minimum desktop and mobile states are repeated at 200% zoom/text.
- Primary action, plan price, period choice, coupon disclosure, consent and
  status remain visible/reachable without overlapping the native inspector.
- Native Record/Stop and shell navigation remain available while billing is
  open. Billing must not replace, cover or trap focus away from native controls.
- The installed-app path covers overview → plans → checkout preview → history;
  no final payment/provider mutation is part of parity QA.
