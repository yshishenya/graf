# UX Review Checklist: Полная переработка кабинета GRAF

**Purpose**: Unit tests for the UX/UI/IA requirements and reference-fidelity gate

**Created**: 2026-09-04

**Feature**: [spec.md](../spec.md)

> Чеклист принадлежит reviewer. Исполнитель не отмечает его пункты как
> выполненные; evidence и решение reviewer фиксируются на review-этапе.

## Information architecture

- [ ] [CHK001] Список, detail, настройки, billing, shared и auth образуют одну
  понятную иерархию, а текущий контекст виден без догадки.
- [ ] [CHK002] Основное действие каждой поверхности визуально приоритетно и не
  конкурирует с вторичными действиями.
- [ ] [CHK003] Навигация standalone и embedded согласована, а различия имеют
  объяснимую причину.

## Visual hierarchy and interaction

- [ ] [CHK004] Типографика, плотность, отступы, границы и состояния controls
  согласованы между крупными поверхностями.
- [ ] [CHK005] Hover, focus, pressed, selected, disabled и error различимы
  без опоры только на цвет.
- [ ] [CHK006] Длинные заголовки, email, ошибки и подписи не ломают обязательные
  действия и сетку.

## Accessibility and responsive behavior

- [ ] [CHK007] Все ключевые controls имеют доступные имена, landmarks и
  корректные relationships tab/tabpanel/dialog/menu.
- [ ] [CHK008] Фокус видим, порядок фокуса логичен, Escape/закрытие возвращают
  фокус, а reduced-motion не ухудшает понимание.
- [ ] [CHK009] Матрица 320/390/768/1024/1440 и обе темы не содержит overflow,
  clipping или нечитаемого текста.

## Reference fidelity and product truth

- [ ] [CHK010] Сравнение с observable Krisp покрывает композицию, IA, density и
  interaction states без извлечения private assets/code/content.
- [ ] [CHK011] Каждое намеренное отклонение объяснено accessibility,
  localization, privacy, deletion truth, product truth или reference defect.
- [ ] [CHK012] Ни одна правка не ослабляет visible capture/stop, consent,
  privacy, deletion wording или truthful degraded states.

## Legacy and regression

- [ ] [CHK013] Каждый удалённый legacy-кандидат имеет доказательство отсутствия
  runtime-ссылок и функциональной ответственности.
- [ ] [CHK014] Все функциональные UI-контракты, маршруты, HTMX hooks, data-hooks
  и existing tests сохранены.
- [ ] [CHK015] До PR есть before/after evidence по каждой изменённой крупной
  поверхности и повторный полный audit.
