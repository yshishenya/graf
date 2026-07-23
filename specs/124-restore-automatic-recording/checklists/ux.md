# UX Requirements Checklist: Восстановление автозаписи встреч

**Purpose**: Проверить, что восстановленный settings/prompt UX однозначен,
доступен и локализован.
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] Settings IA включает detection toggle, раздел приложений, полный список,
  per-target control, «Выбрать все» и «Снять все».
- [x] Prompt включает app identity, capture source/policy copy, opt-in checkbox,
  visible countdown, primary start и dismiss.
- [x] Для loading/error/unavailable registry state описано сохранение настроек и
  fail-closed поведение.
- [x] Для restart, repeated detector event, active session и ended meeting
  определены состояния.

## Requirement Clarity And Accessibility

- [x] Все критические labels заданы точными русскими строками.
- [x] Countdown описан как видимый progress surface, а не скрытая задержка.
- [x] Settings rows и actions имеют независимое состояние и reversible meaning.
- [x] Active capture indicator и Stop доступны без сети и без перехода в web
  cabinet.
- [x] Требования не полагаются только на цвет и не прячут blocked reason.

## Consistency And Boundaries

- [x] Список target-ов определяется canonical registry, а не отдельным списком
  в UI-тексте.
- [x] Prompt labels и settings labels согласованы со старым рабочим UX и
  quickstart.
- [x] UX-упрощение не может удалить четыре обязательные части контракта без
  нового approved feature и product-owner decision.
- [x] Закрытие prompt во время countdown и одновременные события не создают
  скрытый старт или замену видимого пользовательского решения.

## Notes

- Checklist проверяет качество UX-требований; визуальный macOS smoke является
  отдельным acceptance step.
