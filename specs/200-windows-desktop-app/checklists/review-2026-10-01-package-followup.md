# Независимый preflight development MSIX — 2026-10-01

**PASS / ALLOW NARROW — качество требований для подготовки development-пакета T096/#7239.**
Полоса: существующий high-risk-product Spec Kit; запись рецензента — docs-only, не понижение риска упаковки.
Только canonical /Users/yshishenya/.codex/worktrees/200-windows-followup/crisp; Git/HEAD заново не проверялись по запрету пользователя.
Допускается предложенный Identity Version 0.1.0.11→0.1.0.12, затем штатная Release x64 упаковка/подпись/статическая проверка main.
Фактического нового diff ещё нет: перед продолжением отдельно проверить ровно одну строку Package.appxmanifest; Name/Publisher/API/capabilities/dependencies/paths неизменны.

| Текущий checklist | Checked | Unchecked | Всего |
| --- | ---: | ---: | ---: |
| advanced-routing.md | 14 | 0 | 14 |
| audio-capture.md | 24 | 0 | 24 |
| requirements.md (built-in) | 22 | 0 | 22 |
| security.md | 27 | 0 | 27 |
| ux.md | 25 | 0 | 25 |
| Итого | 112 | 0 | 112 |

Все 112 критериев перечитаны; SHA-256 пяти checklist, constitution/spec/plan/tasks/quickstart/research/data-model/трёх contracts/parity-matrix совпали с собственным предыдущим review.
Конкретные основания каждого критерия сохраняются в review-2026-10-01-ui-parity.md и review-2026-10-01-release-custody.md; непроверенных требований в этом узком gate нет.
Отметки readonly, ничего не переотмечено. Это requirements quality, не 112 runtime PASS. Tasks: 91 checked/22 unchecked/113; T096 и остальные открытые задачи не закрываются.
Заново сверены текущие AGENTS/constitution I, III–VI, spec FR-019/020/021 и SC-008/010, plan открытая Phase0, tasks T094–T097/T101, quickstart §8, guidance README/worktrees/flow/product-gates/release-and-validation и Windows scripts README.
Security CHK016/019/020/021: обязательны сохранность данных при обновлении, происхождение pinned AEC3, подпись/архитектура/runtime и обычный пользователь; версия не отменяет эти требования.
Advanced-routing CHK002/004/008/014 и audio CHK005/007/012/019: нет нового routing/clock/storage решения, изменения §5, порога или заявления SC-003 PASS.
Requirements CHK019/022 и UX CHK020/021: существующий task/контракт, честная граница installed/package evidence; нет новой серверной функции, приёмки интерфейса или одобрения всего dirty дерева.

Round125: собственный post-implementation review одобрил только allocation-before-release repair; validation-2026-10-01.md фиксирует MSVC CTest32/32 и solution build exit0, но installed0.1.0.11 без исправления.
Текущие SHA-256 совпали: worker 80b06e4b04845608cb70379bdb2ac5026f8d81e0a9a3845756b478de5a9f83a6; fixture 9b957d67a9d660623aa5e695489f5915c6862fc29676c99eeba790134270ca0c.
Main обязан связать точные source/build inputs и pinned AEC3 provenance с новым package SHA, manifest identity и payload EXE SHA; прежний build-output/installed пакет этого не доказывает.
Подписывать только существующим CN=GRAF сертификатом с проверенной точной identity; не создавать сертификат, не менять truststore. Static smoke требует Valid signature на проверяющем host, не просто embedded certificate; при отсутствии доверия STOP без обхода.
Development0.1.0.12 — внутренний четырёхкомпонентный MSIX build identity по существующему dev-sign lane quickstart §8, не SemVer/public release. Публичные продуктовые версии/tag остаются CalVer vYYYY.MM.DD.N с отдельными approval/CI/release gates.
Установка лишь после свежих package/signature/dependency/architecture proof и exact idle/process guard непосредственно перед действием; locked экран/старый inventory не доказывают idle. Не принуждать завершение активной сессии, не обходить блокировку, не uninstall/purge/менять данные или доверие.
README self-check после допустимой установки требует точный зарегистрированный install path, независимый EXE SHA равный MSIX payload, отсутствие GRAF процесса, активацию AppUserModelID и именно exit73; build-folder EXE/exit0/static smoke не PASS. До этого installed self-check NOT_RUN.
Phase0/Phase1 нового clock/protected-storage остаются NOT READY; §5 неизменен. Real audio/AEC3/60min, installed UI, clean-image/update/rollback и публичная подпись не приняты; предыдущие четыре теста не одобряют остальные dirty изменения.
Рецензент не вызывал VM/UI/mic/build/test/Git/GitHub/сеть, не менял product/spec/plan/tasks/markers/старые отчёты; единственная запись — этот новый отчёт. После записи totals и неизменность прежних источников проверены чтением.

## Post-change review — 2026-10-01

APPROVED NARROW (code-reviewer): фактический diff -u содержит ровно одну удалённую/добавленную строку Identity, Version 0.1.0.11→0.1.0.12; замечаний нет.
Baseline прочитан из /Users/yshishenya/Documents/graf-windows-followup-200/apps/windows/Installer/Package.appxmanifest, не из HEAD0.1.0.5; canonical — apps/windows/Installer/Package.appxmanifest:3.
SHA-256 baseline0.11: 2348c3f0fedc8344b25bc6fd4b9ed843259e3cae84dfb53f58617afa1537109b.
SHA-256 canonical0.12: 95bea5c39f980228a5238ab9384ff68c051bff8b79765a9e945b1be21c12ceed.
Все остальные байты двух manifest совпадают: Name/Publisher, capabilities, dependencies, OS bounds, entrypoint/protocol/assets/paths неизменны. Это монотонное увеличение внутренней development MSIX версии, не публичный CalVer release.
Main сообщил свежие CTest32/32, ASan/UBSan CaptureFault1/1 и pinned AEC VerifyBuildArtifacts exit0; reviewer их не запускал. Live MSBuild baseline0.11/session44290 не является final0.12 package proof.
Одобрен только этот version diff; кандидат0.12 должен собираться отдельно после завершения baseline и иметь собственные hashes/signature/static proof. Install/self-check/idle guards, Phase0, T096/T097 и прочие acceptance открыты; product/checklists/tasks/Git/VM/UI/mic не менялись.
