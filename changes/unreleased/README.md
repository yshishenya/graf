# Changelog fragments

Feature agents write one file per Feature ID under this directory, for example
`F216.yaml`. The root `CHANGELOG.md` is assembled only by the release operator
when a release candidate is frozen.

Required fields:

```yaml
schema_version: 1
feature_id: 216
category: Changed
summary: "Русское описание пользовательского или операционного результата"
issue: 6090
tasks: [T001]
compatibility: "Изменения совместимости или `нет`"
known_limitations: ["Ограничение, если есть"]
release_notes: "Русские заметки для release train"
```

Fragments must contain metadata only: no secrets, credentials, raw audio,
transcript text, signed URLs, private meeting data or machine-specific absolute
paths. A fragment is owned by its feature; duplicate Feature IDs are invalid.
