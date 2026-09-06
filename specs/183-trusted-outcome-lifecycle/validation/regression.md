# Feature 183 regression receipt

Дата проверки: 2026-08-25. Disposable PostgreSQL matrix завершён без
ошибок.

Текущий rerun выполнен после синхронизации с `origin/master` SHA `a502b472`;
миграционный worker читает единственную head
`0080_merge_summary_state_processing_recovery`.

| Набор | Passed | Failed | Warnings |
|---|---:|---:|---:|
| Feature 183 focused | 138 | 0 | 2 |
| Outcomes/cabinet/share/export/deletion expanded (до sync master) | 184 | 0 | 2 |
| Deletion + slot RLS targeted rerun | 12 | 0 | 2 |

Warnings относятся только к уже существующим pytest/httpx deprecation
предупреждениям и не меняют результат проверок.
