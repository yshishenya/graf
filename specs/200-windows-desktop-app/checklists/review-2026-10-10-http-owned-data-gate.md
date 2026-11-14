# T116 — owned HTTP data: construction gate336 / группа337

SCOPED CONSTRUCTION / REQUIREMENTS / ANALYZE GO; ACTUAL RED336 ACCEPTED.
Допуск только к заявленной общей группе result/truth/remote/account и её GREEN.
Это не SOURCE/GREEN337 PASS, не ALL HTTP, не result adoption и не готовность Windows.
Lane high-risk-product прежний; construction blockers C0/H0/M0.

## Основание и неизменность норм

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty bytes.
Прочитаны AGENTS/guidance, текущие gates и применимые нормы; code-reviewer,
ponytail-review и scoped speckit-analyze: correctness/lifetime, минимум кода, трассировка.
FR-012/013/014/022 → T116:568 → plan:1995–2105 → model:597–617 → quickstart:902–934.
Прежний analyze gate `review-2026-10-10-protected-http-integration-gate.md` SHA-256
`51af545d0cc8a4dc31c5ea0d65595f08dcb6be2c8a4e2194ee3c3d8da90174e0`; все9 норм совпадают:

| Файл (пути относительно feature, кроме constitution) | SHA-256 |
| --- | --- |
| spec.md | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan.md | 9cdc5200419b6264d8e0c6a8c01aca5956b225661e674bba49acecbc4b90cf21 |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| research.md | 4a7a1f9d8f7606a106b68e5b6194a0de8d75243508232c191f945f0fc0faa90e |
| data-model.md | c24b9d10bf5b935bcf51bb12034a0bb9ccef4a0b3719a138b48a26cbaa0d3bc7 |
| quickstart.md | 44c93c6558e8564aefe15a2180fd22d117f6368307d865b02253f9e0dffdf0b9 |
| contracts/windows-protected-local-custody.md | 598223854ea7e614694167c4019ef199e30c82b3ac1c44b33fcefa94fbe27fee |
| contracts/windows-protected-packed-custody.md | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| .specify/memory/constitution.md (от repo root) | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |

Prerequisites supported flags PASS; spec отдельно проверен. YAML разобран: оба analyze hooks disabled, не запускались.
Live read-only #7444 OPEN: feature:200/priority:P0/area:storage/gate:pr-blocker/type:hardening,
Spec tasks:T116; assignees отсутствуют. Existing T116 владеет работой, новая задача не требуется.
Проверены все29 файлов с420 отметками:0 открытых; старые177 Markdown неизменны, их runtime не переутверждался.
Tasks120/93/27 прежние. Принятый335 report SHA `080d0528d61f2743633c309d9acacc966a5de5966bfbcf7e23c6b72e44005d82` сохранён.

## Actual RED336: исходники, harness, завершённые доказательства

Evidence `/Users/yshishenya/Documents/graf-f200-owned336.LfGc8H`;209 frozen/canonical hashes exact.
От335 отличается только NativeCaptureStorageIntegrationTests.cpp:+36 строк:979–1014; production неизменен.
Actual3000 → protected adoption → release → cold read → тот же upload; подменена только сеть.
Confirmed snapshot исключает account GET; первый sync GET возвращает один и тот же charged finalized JSON.
Pressure оставляет ровно измеренный move allowance; ReturnProbe доказывает успешный возврат response.
Healthy: returned1/calls1/retryable0/truth1/finalized1. Pressured: тот же ошибочный результат.
Assert:1010 требует pressured retryable1/noTruth; executable exit3, completed=true, stage sync_owned_red_verified.
Configure/build0, terminal/native_completed=true; это ожидаемый RED, не crash до целевой ветки.
Harness проверяет335 terminal10/account_parser_green_verified, source209 до/после, idle, unique TEMP336,
exit3 + точный wrong-result marker + assertion; никаких second GET/mutation/READY setters в новом случае.
Прочитаны configure/build/test/stdout/stderr и receipt; исполнение main, не reviewer; VM/jobs/polling не запускались.
source.json `e126b4563aca365baf22287fb19f0d7c4ff153819c6f17fc9b852ceda74c4acc`;
native.json `a040294a925d053c8b59a714b82224d206637c15c430dbfff106194e0c780d2b`;
validate.ps1 `49a8455ca6e9cb691af0e45242e442ad559fda72e78cfe2f223f07b5c1e14bd0`;
test.log `3d1f9c717cf3e11922b275f144d36790c951a7503961b425615c9c2def1aad8c`.

## Допущенная конструкция и обязательные условия GREEN

Reuse BasicUploadCustodyItem/String/allocator pattern: BasicUploadServerTruth, BasicDesktopTransportResult,
BasicDesktopRemoteUploadState, BasicDesktopAccountIdentity/BasicIdentityResult; std aliases прежние, protected CustodyString.
Protected upload возвращает charged shared owner ProtectedDesktopTransportResult, включая вложенную truth/строки/control/Debug.
Один uploadPrepared/uploadFile/resetUploadStatus/uploadResponse и полный sync decoder по actual String/Result;
ordinary decoder wrapper/std UploadSend/aggregate field order/defaults/caller semantics сохраняются.
JSON markers/decoded fields/normalization/classification/account DTO/remote→truth copies charged с первого allocation,
не std scratch с поздним копированием. Root400 использует existing Reader по ResultString, без второго parser.
from_chars: проверить пустое/overflow/границы токена и прежнюю числовую семантику; whitespace-only status обрабатывать безопасно.
Borrowed fields живут только внутри response; root-only UUID, escaped duplicate keys, nullable getter,
confirmed snapshot zero-GET, cancellation до/после GET и owner/account checks не ослаблять.
CustodyString concat без Base operator+ и скрытого std результата; throwing construction/move не объявлять noexcept.
Terminal owner/truth заранее до wire; catch/reset не выделяет память и не создаёт новый result; после PUT ACK
acceptedBytes/known server progress сохраняются при следующем allocation failure, без повторного PUT/create/finalize.
Новый RED обязан стать GREEN в Debug/Release: healthy uploaded/finalized, pressured returned1/calls1/retryable1/noTruth;
повторить335 account zero-quota, preowned admission, after-ACK/terminal cuts и ordinary calendar/upload/deletion compatibility.

## Severity, минимальность и предел решения

H1 — доказанный runtime gap335: retained sync/result std allocations обходят quota; исправление и source/runtime приёмка OPEN.
Это основание RED→GREEN, не препятствие выбранной конструкции. P3 unused set include: net−1 line, сейчас не менять.
Ponytail: общие typed models/helpers достаточны; второй wire flow/parser/adapter framework не нужен.
Config/request/API create/idempotency/finalize/hash/ranges/localtracks/прочая serialization остаются ALL OPEN.
Protected scheduler/worker result commit/adoption, T116/#7444, T117/T118/T120, global admission, installed/hardware/release OPEN.
Reviewer создал только этот zero-checkbox отчёт; production/norms/tasks/старые markers/GitHub/VM/commits не менял.
