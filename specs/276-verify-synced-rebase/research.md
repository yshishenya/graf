# Research

Decision: доказать каждый replay после одного terminal sync. PR #7257 head
c0e63780576968d97ede7d4eda29c156e36c3561: три изменения плюс sync с
46ecd45ba9d4edd5348c634a837fb688f7ffb723. Merge
a057e29f502dd09cb33118f329ece30d1ea2a40e: три линейных replay.
Деревья равны, прежний predecessor(head,4) отклоняет sync. Это не shallow checkout.

Rationale: per-step merge-tree доказывает содержание и порядок без checkout.
Git 2.44.0 поддерживает --merge-base. Новых зависимостей нет.
Alternatives rejected: final-tree-only, вычитание всех merges, allowlist PR,
перезапись shared history — не доказывают состав или излишне меняют состояние.
API base может продвинуться, recovered base далее проверяется общим CI verifier.
