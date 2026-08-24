# Research: Yandex ID account selection

## Decision: Add Yandex-only `force_confirm=1`

The Yandex authorization request will ask the provider to require an
interactive confirmation/login step. The parameter is added only by the
Yandex adapter, not by the shared provider builder and not by VK ID.

## Rationale

The current Yandex flow reuses the active provider session and gives GRAF no
opportunity to choose an account. Yandex OAuth owns the account UI, so GRAF
must request that interaction without receiving or storing a list of Yandex
accounts. The existing server-side callback verification and provider subject
mapping remain unchanged.

## Evidence and limits

- Official Yandex OAuth documentation describes authorization against a
  specific Yandex ID account but does not document a standard
  `prompt=select_account` or `login_hint` parameter.
- Yandex's Android SDK issue documents `force_confirm` as the expected way to
  avoid reusing a remembered login and require login input:
  https://github.com/yandexmobile/yandex-login-sdk-android/issues/22
- The real acceptance gate is a browser test with two Yandex accounts. A
  redirect assertion alone cannot prove that the provider displayed account
  selection or that the selected account reached GRAF.

## Alternatives rejected

- Implementing a GRAF-side account selector: rejected because GRAF cannot
  enumerate or safely custody Yandex account choices.
- Applying the parameter to every provider: rejected because VK ID has a
  separate authorization contract and the user requested Yandex only.
- Logging out from Yandex inside GRAF: rejected because it mutates the
  provider session outside GRAF's ownership boundary.
