# UX Requirements Checklist: Связанные способы входа

**Purpose**: Проверить полноту требований к подтверждению, ошибкам, настройкам,
доступности и паритету веба с GRAF Local.
**Created**: 2026-08-16
**Feature**: [spec.md](../spec.md)

## User understanding and consent

- [x] CHK013 Preview явно показывает survivor, сохраняемые данные, отдельные workspaces и причины блокировки до irreversible confirmation [Completeness, Spec §Merge Policy, contracts/merge.md]
- [x] CHK014 Текст различает «вход заблокирован из-за конфликта» и «сервис недоступен», а также даёт повторяемый recovery action [Clarity, Spec §FR-005, FR-018]
- [x] CHK015 Отмена, отказ второго proof, expiry и blocked merge имеют понятные конечные состояния без ложного сообщения об успешном входе [Coverage, Spec §US2, FR-006, contracts/auth-linking.md]
- [x] CHK016 Пароль нигде не появляется как обязательный шаг в email-code сценарии [Consistency, Spec §Assumptions, US1]

## Settings and unlink

- [x] CHK017 Раздел «Способы входа» определяет состав строки, verification state и допустимые действия [Completeness, Spec §US3, contracts/settings.md]
- [x] CHK018 Запрет удаления последнего usable method и требование re-authentication сформулированы без двусмысленности [Clarity, Spec §FR-011–FR-012]
- [x] CHK019 Конфликт provider identity ведёт в recovery/merge, а не в общий экран недоступных встреч [Consistency, Spec §US2–US3, contracts/settings.md]

## Accessibility and surfaces

- [x] CHK020 Keyboard navigation, assistive-technology status announcement и visible localized result states заданы для всех link/merge outcomes [Coverage, Spec §FR-018, contracts/settings.md]
- [x] CHK021 Browser и embedded WebView обязаны иметь одинаковые правила, причины и safe return behavior [Consistency, Spec §FR-016, US4, SC-006]
- [x] CHK022 WebView external-navigation boundary ограничен активным auth flow и явно описан для idle/error состояния [Clarity, Spec §US4]

## Notes

- UX checklist закрыт на уровне требований; визуальная и moderated usability
  проверка выполняются после реализации по `quickstart.md`.
