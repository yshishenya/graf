# UI Contract: Верхняя навигация кабинета

## Shared controls

| Control | Enabled when | Action | Disabled/loading behavior |
|---|---|---|---|
| Домой | Есть безопасный fallback списка встреч и текущий URL не fallback | Открыть канонический список встреч | Недоступна на списке встреч и во время загрузки |
| Назад | Есть safe back candidate с URL, отличным от текущего, или разрешён fallback | Открыть выбранный safe history item или fallback | Не открывает дубликаты, auth, external, POST или protected route после истечения сессии |
| Вперёд | Есть safe forward candidate с URL, отличным от текущего | Открыть выбранный safe history item | Отключена, если такого кандидата нет; не делает no-op |
| Обновить | Текущий документ безопасен и нет активной загрузки | Перезагрузить текущий документ | Недоступна во время загрузки и на unsafe/non-document route |

## State contract

- При любом controller-owned переходе `isLoading = true` до finish, cancel или
  fail обработки.
- После finish/cancel/fail state пересчитывается из текущего WebKit URL и
  history list.
- Accessibility labels, hints, keyboard shortcuts and identifiers remain the
  current stable values from `DesktopCabinetNavigationControls`.

## Security boundary

Back/forward never opens auth callback/provider, external, artifact download,
unsafe history, or protected meeting route after the session is expired. The
existing fallback and session-boundary behavior remains authoritative.
