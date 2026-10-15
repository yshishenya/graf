# Public measurement contract

Ровно четыре GET из data-model.md сохраняют прежний HTML/status/security/canonical и не добавляют scripts. Ровно один best-effort upsert уровня 1 при разрешённом основании и настройке. Выключение/отзыв/сбой БД сохраняют HTML 200; пропущенная запись — пробел.

Нет чтения cookie для учёта, новых cookies или замены существующего, L2 visit refs, auth handoff, внешних запросов или optional surfaces. UTM текущего URL проходит существующий sanitizer. Unknown/private/help/default provider scope сохраняется. Прежний режим public_page_response неизменен.

F289 меняет только историческую границу уровня 1 F281/F282. Organic→activation остаётся неизвестной. Direct нельзя переименовывать в AI.
