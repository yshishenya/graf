# Clarifications: Пострелизная очистка интерфейса

### Session 2026-08-19

- Критических неоднозначностей нет: пользователь разрешил исправить все подтверждённые findings при обязательном сохранении принятого поведения.
- Feature 172 остаётся визуальным baseline: `64px / 176px`, controls `40×40px`, общий compact axis и допуск центра `1px`.
- Feature 174 supersedes только неиспользуемый standalone fallback Feature 173; production settings остаются внутри outer cabinet shell с одной навигацией.
- Поведенческие проверки должны воспроизводить узкий embedded viewport и вычислять реальную видимость/геометрию, а не закреплять строки реализации.
- Native inspector сохраняет верхний toggle и текущую геометрию; удаляется только wrapper без используемых данных и дублирующая проверка структуры.
- Маршруты, auth/CSRF/role boundaries, данные, capture, billing, release и deployment остаются вне scope.

No formal question was required; user intent, accepted Features 172–173 and the measured regression fix every high-impact choice.
