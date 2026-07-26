# Research: полный egress внешнего приглашения

## Findings

1. `shared_meeting_detail_page` строит `ShareRecipientAccessProof` и передаёт
   его в `get_cabinet_meeting_review`; поэтому страница и её readiness-модель
   могут корректно показать полный grant.
2. API shared routes получают тот же proof через
   `_authorized_shared_meeting`, но возвращали только `(meeting, decision)`.
3. Общие egress-функции `playback_artifact`, `download_artifact` и финальная
   проверка `create_content_export` вызывают `_refresh_egress_access` без proof.
   Для accepted external invitation это повторная проверка уже в неполном
   контексте и источник отказа после успешного открытия страницы.
4. Канонический контракт уже существует: review M4A, text transcript и
   content exports с scope `transcript`, `summary`, `combined`.
5. Existing full-invitation integration test покрывает page, playback и audio
   download, но не проверяет transcript download и фактический content export;
   его нужно расширить, чтобы downstream regression была видна.

## Decision

Добавить optional `recipient_proof` в существующий egress call chain и вернуть
proof из shared authorization helper. Owner/team/admin callers продолжат
передавать `None`; shared routes будут передавать тот же уже проверенный proof.
Это сохраняет единую ACL-проверку, recheck на egress boundary и не добавляет
новую модель доступа.

## Rejected Alternatives

- Не выдавать storage URL напрямую: это обходит текущие audit, deletion и
  storage-size проверки.
- Не повторять проверку только на странице: кнопки являются отдельными
  запросами и должны fail-closed при revoke/deletion.
- Не расширять summary-only grant: это нарушает выбранный scope.
- Не добавлять новый пакетный endpoint: существующий content-export contract
  уже описывает нужные отчёты.
