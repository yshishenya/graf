# Research F242

- Decision: theme-only partial update. Rationale: hidden locale/timezone плюс missing profile сбрасывают настройки; stale вкладка опасна даже после передачи profile. Reuse handler, validate set first. Rejected: новый theme endpoint.
- Decision: native details + отдельная submit кнопка, один macro для overview/plans. Рationale: клавиатура/no-JS без нового controller. Предварительные даты явно помечены, реальные даты после запуска. Rejected: stale прошлый старт, reservation/signing protocol без бизнес-нужды.
- Decision: history anchor + configured mailto или unavailable copy. Не выдумывать канал; checkout config validation неизменна.
- Decision: decimal labels и отдельные exact bytes; квоты не округлять.
- Decision: краткий pending без изменения DOM hook/state machine/preserved results/recovery.

Основания: F140 contracts/account-ia-ux-ui-cx.md, F210 contracts/ui-contract.md и текущие routes/templates.
