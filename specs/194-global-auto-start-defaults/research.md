# Research: Глобальный автозапуск и defaults

## Решения

1. **Явный global scope**. Existing `assisted_auto_start_workspace_id` остаётся
   точным scoped режимом. Новый `assisted_auto_start_all_workspaces` включается
   только вместе с `assisted_auto_start_all_workspaces_approved`; отсутствие
   approval или одновременная передача workspace ID отклоняются валидатором.
2. **Без wildcard через пустое значение**. API вычисляет scope явно и строит
   `policyRef` из `all_workspaces|policy_version` либо из
   `workspace|workspace_id|policy_version`. `subjectRef` и `deviceRef` всегда
   включают текущие user/workspace/device значения до хэширования.
3. **Prompt вместо отдельного pre-consent окна**. На новой установке detection и
   target selection включаются после первого registry. При отсутствии
   acknowledgement detector всё равно выдаёт обычный prompt, но timeout и saved
   target не могут стартовать; `Записать сейчас` остаётся явным текущим ручным
   действием. Галочка «Всегда писать это приложение» вместе с действием prompt
   создаёт существующий acknowledgement.
4. **Однократные defaults**. Settings store отличает отсутствие файла (fresh
   install) от существующего файла. Legacy JSON без marker считается уже
   управляемым пользователем, поэтому обновление не переписывает его targets.
5. **Только verified native targets**. Defaults используют текущий registry и
   выбирают только `macos` + `native_app` + `prompt_enabled`; browser/manual,
   diagnostic и unknown targets остаются вне auto-record.

## Отвергнутые варианты

- Пустой `workspace_id` как wildcard: неоднозначен и опасен при env-ошибке.
- Автоматическая запись без prompt/acknowledgement: нарушает прозрачность и
  Feature 145.
- Автоматическое копирование acknowledgement между workspace: binding должен
  оставаться user/workspace/device-bound.
- Новая таблица policy или endpoint: текущий registry response и deployment env
  достаточны для этой конфигурационной границы.

## Проверенные точки потока

- Server: `Settings` → `/desktop/meeting-detection/target-registry` → strict
  `AssistedAutoStartPolicy` schema.
- Desktop: registry resolution → settings defaults → detector policy snapshot →
  prompt consumer → final `currentMeetingDetectionStartDecision` and capture gate.
- Cached registry remains backward compatible when `scope` is absent.
