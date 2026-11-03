# Независимое ревью требований F291

Дата: 2026-10-23. Рецензент: f291_requirements_review. Область: качество требований security/infra перед генерацией tasks, без проверки реализации или production.

## Результат

Requirements-quality gate: PASS. Security: 4 checked / 0 unchecked. Infra: 4 checked / 0 unchecked. Оба чеклиста перечитаны после изменения маркеров. Исправленное основным исполнителем требование FR-001 и план теперь обязательно задают нижнюю границу certifi в pyproject вместе с lock/constraints; прежняя неопределённость устранена фактическим перечитыванием.

## Доказательства по пунктам

| Чеклист / пункт | Основание |
|---|---|
| security CHK001 | Spec FR-001/002/003; plan Project Structure перечисляет pyproject, uv.lock, constraints, оба workflow, governance test, Dockerfile; minima 2026.10.19/22.23.4. Read-only rg подтвердил четыре старых Node pins именно в двух указанных workflow. |
| security CHK002 | Spec FR-004, SC-001, Edge Cases; quickstart §5: два адреса, обычный HTTPS-контроль, 15 секунд, без redirects, DNS/timeout не засчитываются. |
| security CHK003 | Spec FR-003/004/006; plan Constraints: без ручного trust change, TLS weakening, секретов, содержимого встреч, изменений данных/прав/сети/аналитики. |
| security CHK004 | Spec FR-005/008, SC-003; plan Release Gate/Validation; quickstart §3–6: exact-source PR/Full CI/candidate/decision, отдельный runtime readback, ограничения явно сообщаются. |
| infra CHK001 | Spec FR-006/008 и US2; research различает master, remote checkout, опубликованный .22.1 и draft .22.2, сохраняет чужие изменения и одного оператора. |
| infra CHK002 | Spec FR-005/007 и US2 scenario 2; quickstart §4: применимое backup-разрешение и restore evidence обязательны, иначе execute блокирован; исходные исправления независимы. |
| infra CHK003 | Spec FR-005, Edge Cases; quickstart §6: штатный rollback без удаления томов/автоотката данных, health/smoke и повторная Temporal/worker readiness. |
| infra CHK004 | Spec FR-008; research и quickstart §6: серверный выпуск сохраняет существующие macOS assets/appcast; новый клиент требует собственных trust gates. |

## Проверенные инструкции

AGENTS.md, guidance index, spec-kit-flow.md, release-and-validation.md, product-gates.md, constitution 7.1.0; спецификация, план, research, quickstart и data-model F291. Product baseline/current status консультировались по server/deploy scope; этот отчёт не утверждает приёмку их прочих продуктовых требований.

Хеши проверенного содержания:

- spec.md: `2ea5ae13a85826542e7c079e2e732fb09280e5a1878428b4908fef2b472cc5e2`
- plan.md: `f1028b5c148dd836db15f2c3d0bb47f65f50dc9f9f77966ca5f60d8a8d456bd7`
- research.md: `3063e484e61ca8bfcd5adaf3ce181829b4f440316c2b3b5cd3cc8e41fbddd6d3`
- quickstart.md: `254e709c0ea3064226b52a8ae12fa2fc72b7604d01af1bb4957ef8c7d600adbe`
- data-model.md: `78cdf7e46f31a9a036babf12450b45bd25bdba1016c2d865405bbfcb71ec9c1e`
- constitution: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`
- release-and-validation.md: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`

## Оставшиеся границы

Первоначальный этап выполнен до генерации tasks по обязательному порядку. Затем созданный tasks.md независимо перечитан; результат и трассировка приведены ниже. Этот контроль не заменяет analyze, issue sync или любые проверки реализации/выпуска. Применимость backup-разрешения и restore readiness остаётся production gate оператора. Чеклист не выдаёт разрешения на резервирование.

Изменены только два reviewer-owned чеклиста и этот отчёт. Код, spec/plan/tasks, инструкции, GitHub и production этим рецензентом не изменялись.

## Перечитывание tasks перед implementation — 2026-10-23

Результат: PASS по полноте требований, порядку и сохранению ограничений. Tasks SHA-256: `9a1ced728a90a954f98589259ad9fff9c885679372ec9e7aab6a1e9eaa0241eb`. Spec, plan, research, quickstart, constitution и release guidance совпали с указанными выше хешами; оба чеклиста перечитаны. Security: 4 checked / 0 unchecked; Infra: 4 checked / 0 unchecked.

| Требование | Задачи и ограничения |
|---|---|
| FR-001 | T003: обязательный pyproject floor, targeted lock и воспроизводимый export; quickstart §1 проверяет diff и повторный export. |
| FR-002 | T004: оба workflow, существующий governance test и его запуск. |
| FR-003/004 | T005: штатный Docker CA package, оба runtime/media пути и bounded HTTPS controls; T008 повторяет readback в production для пакетов/TLS. |
| FR-005 | T002 завершает reviewer/analyze/issue gates до реализации; T006 три exact PR checks до merge; T007 candidate/train/Full CI/decision/dry-run и все существующие процессы; T008 только после gates, health/smoke и repeated readiness. |
| FR-006 | T001 сохраняет чужие изменения и ownership; T006/007 сверяют PR и release owner/range; Dependencies исключают параллельную реализацию и дополнительные финансовые/SMTP/analytics действия. |
| FR-007 | T007 явно проверяет применимость backup authority/restore и сохраняет execute blocked при отсутствии; T008 зависит от T007. |
| FR-008 | T007/008 сохраняют отдельный серверный релиз и опубликованные macOS assets; inherited quickstart и release guidance требуют tag/GitHub Release/readback и не считают draft production. |
| SC-001/002/003 | T005 и T008 требуют клиентские проверки/обычный контроль и фактические версии/состояние; T008 требует metadata-only receipt и rollback outcome. |

Порядок T001 → T002 → T003/004/005 → T006 → T007 → T008 корректен. T003/004/005 независимы по файлам, но явно остаются в одном процессе реализации. Все задачи имеют ID и точные пути; story-scoped задачи содержат US1/US2 и критерии независимой проверки. Новые требования не добавлены. Блокеров качества требований и task coverage не обнаружено. Implementation всё ещё зависит от фактического завершения analyze/issue sync в T002; данный рецензент их не исполнял и не удостоверял.

Эксплуатационная заметка без блокировки исходных исправлений: T001 отмечена исполнителем завершённой; текущие package/image inventories зафиксированы им в отдельном PROGRESS.txt. Перед финальным закрытием следует убедиться, что требуемая T001 ссылка на research содержит эту инвентаризацию либо явную ссылку на итоговый metadata-only receipt. Это не подтверждение runtime со стороны рецензента.
