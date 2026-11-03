# T114: права известного публичного ключа CI

Reviewer владеет отметками; до кода.

- [x] Фактический mode0777 и неизвестность hash/причины отделены; официальный эталон имеет точные HTTPS источники/hash/size/mode, новый пакет не подменяет старый.
- [x] Исключение ограничено fixed keyring/root:root/regular/0777/3607 и точным pin, parent защищён; неизвестное/source/прочие modes/type/owner/group/size отказывают без нового доверия.
- [x] Snapshot ограничен/no-follow/fingerprint; atomic new inode0644, повторная identity/parent проверка, fsync/readback/cleanup закрывают races/failure; chmod неизвестного ключа нет.
- [x] Уже безопасный путь no-op и прежние guards/callers/package tuples сохранены; runtime без загрузок/новых зависимостей/продуктовых изменений.
- [x] Existing test RED→whole GREEN, static/process, code review/converge и actual native pin обязательны; draft failure не merge, exact gates/Full/T0/коммерческие результаты отдельно.

## Независимое ревью требований до кода — 01.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Ветка `codex/f211-ci-native-metadata-20261101`, HEAD
`ebb720844e9a52f4c80b535fc9f8050508a8729e`.
**PASS качества требований T114: 5 отмечены / 0 открыты;
P1/P2/HIGH — 0/0/0.** Основания и хеши — в
[отчёте](../validation-ci-keyring-permissions-review-20261101.md).

Уточнение порядка принято: key snapshot проверяется без записи, source
полностью проверяется и canonical ограничен; только затем допускается
атомарная замена известного keyring. Малформатный/небезопасный source не
вызывает key write. Отметки принимают только проект: реализация, фактический
hash runner, native success, merge, Full/T0 и коммерческие AC не приняты.
До кода сохраняются актуальные analyze и issue-sync ворота.
