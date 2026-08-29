# UI matrix

Дата: 2026-08-21

Проверка выполнена на synthetic/local data в browser и `/desktop`; приватный текст встречи в evidence не сохранялся.

## Результат

| Поверхность | Проверка | Результат |
|---|---|---|
| Полный каталог | Форматы 5–9, current marker, фокус текущего формата | pass |
| Личный формат | key/id/version, default/current marker, focus | pass |
| Browser и `/desktop` | одинаковая итоговая структура, одна live-region, console clean | pass |
| Candidate review | empty candidate остаётся actionable; close/reject/accept разделены | pass |
| Acceptance | одно действие отправляет ровно один POST | pass |
| Source navigation | переход к evidence и возврат сохраняют review context | pass |
| Mobile 390×844 | horizontal overflow 0; action container и три кнопки доступны | pass |
| Embedded zoom | Swift boundary и persisted-value tests до 200% | pass |

Размер трёх mobile action buttons в проверенном состоянии: 260 px. Viewport после проверки возвращён к исходному, временные browser/server sessions остановлены.

Санитизированные визуальные артефакты:

- `/Users/yshishenya/.codex/visualizations/2026/08/21/01a02475-baa5-7e70-8565-db44f7bce7ae/07-feature181-candidate-wide.png`
- `/Users/yshishenya/.codex/visualizations/2026/08/21/01a02475-baa5-7e70-8565-db44f7bce7ae/08-feature181-candidate-mobile.png`

Generated `.playwright-cli/` snapshots из authenticated session удалены из worktree и каталог добавлен в `.gitignore`; они не являются release evidence.

## Повторная read-only проверка production web route

Дата: 2026-08-29

- На двух доступных владельцу сохранённых встречах без изменения данных открыты
  вкладки `Итоги` и `Расшифровка`; обе переключаются и сохраняют контекст.
- На встрече с готовыми итогами открыт полный каталог: `Авто` и восемь
  специализированных форматов отображаются с назначением; текущий результат
  остаётся видимым, каталог закрывается отдельной кнопкой.
- Source-jump из итога открыл точный фрагмент расшифровки, после чего возврат
  на вкладку `Итоги` сохранил текущую встречу и результат.
- Кнопки `Поделиться`, `Ещё` и `Обновить итоги` не запускались: первые могут
  раскрыть приватные данные, последняя создаёт внешнюю AI-операцию. Состояние
  генерации проверялось только по отображаемому UI.
- На обеих записях production runtime одновременно показывал сохранённые
  итоги и устаревшее состояние «Проверяем статус обработки…». Это подтверждает
  необходимость выкатки уже подготовленного lineage/status fix; текущая
  проверка не является доказательством production deploy.
