# Ponytail review

`apps/server/src/twobrain_rec_server/support/incidents.py:L610-L612` —
`shrink`: `_upsert_incident` дважды присваивал correlation number и делал
лишний flush; финальный caller уже владеет этой операцией. Удалены 2 строки,
поведение проверено focused server suite; полный canonical CI был зелёным
непосредственно перед этим механическим упрощением.

Остальные дополнительные границы (WebKit bridge, pending state, private Issue,
RLS runner и legacy-audio guard) имеют отдельные потребители или security/
privacy-критерии; их сокращение ухудшило бы проверяемый контракт.

net: -2 lines possible.
