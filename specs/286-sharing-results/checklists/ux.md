# UX requirements review — F286

Reviewer-owned. Requirements quality, not prototype acceptance.

- [x] CHK001 Are two sections/actions and plain success/failure/unknown copy consistent with approved prototype? [FR-001,008,011; contracts]
- [x] CHK002 Are default ASK, explicit rule scope, queue/delay/time, per-instance cancel and global pause distinguished? [FR-012–019]
- [x] CHK003 Are forwarding, no-JS, keyboard/focus/mobile/themes, unavailable and Clipboard fallbacks defined? [FR-004,010,022; quickstart]
- [x] CHK004 Does recipient own-use path avoid author membership, mandatory account before public reading, unsolicited subscription and false platform promises? [FR-007,023,024]
- [x] CHK005 Are reference fidelity and independently written code/GRAF-owned assets covered? [plan Constitution Check; research]

## Независимая проверка — 2026-10-06

Проверены требования проектирования, не работа реализации. `tasks.md` и `analysis.md` перечитаны до реализации; задачи T001–T018 покрывают требования и последующие проверки.

- CHK002: spec FR-012–019; plan Design 3; contracts строки 8–9; data-model строки 19,27: предложения/правила/область/очередь/пауза разделены.
- CHK003: spec FR-004,010,022; quickstart пункт 3; spec Edge Cases: пересылка, буфер, отказ доступа, отсутствие JS, клавиатура, ширина и темы заданы.
- CHK004: spec FR-007,023,024; plan Design 6; spec Assumptions: чтение без входа, добровольный собственный путь, отсутствие чужого членства и честная платформа заданы.
- CHK005: plan Constitution Check и Design 5; research строка 10; product-gates UX Reference Fidelity: согласованный образец, собственные компоненты и запрет сторонних assets заданы.

CHK001: первоначальное замечание устранено. contracts/sharing.md строка 15: неизвестный исход без известного отказа получает «Проверьте отправку»; подтверждённый успех и известный отказ отделены.

Итоговое чтение перед реализацией: 5 [x], 0 [ ]. Уточнения auto_epoch, устойчивого requires_review, Google <=15 минут/organizer.self и исключения дубликатов прочитаны в plan/data-model; покрытие — T011–T013 и T017.
