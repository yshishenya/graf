# Research: непрерывная навигация кабинета

**Дата аудита**: 2026-08-17

## Проверенный текущий поток

- `cabinet_navigation()` в `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
  уже является источником маршрутов основного кабинета для browser и embedded
  surfaces.
- `settings_category_navigation()` уже является источником существующих
  category ids, labels, scope labels и href. Features 135 и 151 владеют
  категориями, формами и server-backed semantics.
- `sections.html` уже содержит один общий `cabinet-rail-toggle`, но текущий
  markup/JS contract не закрепляет truthful action label, stable hit target и
  focus return.
- `settings_navigation.html` рендерит отдельную settings rail. При сохранении
  global sidebar это создаёт две конкурирующие левые области; новый срез меняет
  только shell placement/visibility и не переписывает category source или forms.
- `settings_recording_content.html` содержит web-only `/download` CTA; shared
  sidebar пока содержит только embedded update action. Выбранный контракт — одна
  web CTA в sidebar и отсутствие sidebar download CTA в embedded.
- `login.html` одновременно говорит, что новый аккаунт создаётся автоматически,
  и показывает «Зарегистрироваться». Аудит Feature 157/текущих auth routes
  подтверждает обратное для обычного unknown-email login: explicit signup,
  invitation/provider и email-code paths остаются отдельными поддержанными
  входами. Этот срез фиксирует UI-контракт и не меняет auth semantics.
- `AccountSettingsSurface.profile` уже содержит безопасные `display_name` и
  verified `primary_email`; provider subject, internal ids и tokens не являются
  template data.

## Решение по модели навигации

Выбрана модель **одного primary rail с mode switch**:

1. В обычном кабинете primary rail показывает продуктовые разделы встреч.
2. В settings surface та же основная область получает settings categories и
   явный «К встречам».
3. Вложенный `settings_navigation` не остаётся второй видимой или доступной
   навигацией; category links переиспользуются, а forms и URLs сохраняются.

### Рассмотренные варианты

| Вариант | Решение | Причина |
|---|---|---|
| Global rail + inner settings rail | Отклонён | Две одинаково сильные левые области конкурируют за focus и визуальную иерархию. |
| Один primary rail, содержимое заменяется в settings | Выбран | Минимально использует существующие route/view-model contracts и даёт один return-to-meetings path. |
| Settings как горизонтальные tabs в content | Отклонён | Слабее сохраняет доступность длинных labels, narrow layout и существующую settings ownership model. |

## Clean-room и accessibility references

Исследованы 2026-08-17 только публичные принципы, без копирования текстов,
компоновки или иконок:

- [WAI-ARIA APG: Button](https://www.w3.org/WAI/ARIA/apg/patterns/button/) —
  один семантический button, Enter/Space и truthful accessible name/state.
- [WAI-ARIA APG: Menu Button](https://www.w3.org/WAI/ARIA/apg/patterns/menubutton/)
  — profile trigger, Escape и возврат focus; компактное меню не превращается в
  отдельную modal architecture.
- [Apple HIG: Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars)
  — стабильная rail, selected state и понятная иерархия.
- [Krisp](https://krisp.ai/) — только структурный clean-room reference для
  предсказуемого sidebar toggle; GRAF сохраняет собственную композицию, copy и
  icon vocabulary.

## Reused project contracts

- Feature 058: server-rendered Jinja, local CSS/JS, bounded HTMX updates and
  explicit embedded navigation boundary.
- Feature 135: canonical settings categories and browser/embedded route parity.
- Feature 151: settings surface copy, scope labels and accessibility/visual
  expectations.
- Feature 157: passwordless auth, account-linking and recovery boundaries;
  unknown-email login remains fail-closed and explicit signup remains reachable.

## Alternatives rejected

- Новый sidebar state store, localStorage persistence or SPA router — duplicates
  server-owned route truth and creates browser/embedded drift.
- User-Agent sniffing — the shell already passes an explicit `embedded` contract.
- Exposing provider subject or internal IDs in the profile menu — violates safe
  presentation boundary without adding user value.
- Removing signup routes to simplify login copy — would break invitation,
  provider or direct-link callers and changes auth semantics.
- New analytics/onboarding system — unnecessary for a single affordance fix.
