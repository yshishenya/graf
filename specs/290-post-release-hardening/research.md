# F290: исследование 2026-10-17

Два независимых исследования только чтением выполнены по speckit-plan Phase0
на c6c5441c930b8c1ecffed6de9b80773aa0e757e5. Сервер не читался и не менялся.

## Actions

Decision: поддерживаемые стабильные Node24 действия, точные commits:

| Repository | Release | Commit |
|---|---|---|
| actions/checkout | v7.0.1 | 3d3c42e5aac5ba805825da76410c181273ba90b1 |
| actions/cache | v6.1.0 | 55cc8345863c7cc4c66a329aec7e433d2d1c52a9 |
| actions/setup-node | v7.1.0 | 949feb2413d6458794dcd2491c4babbbce0c15c1 |
| actions/setup-python | v7.0.0 | 5fda3b95a4ea91299a34e894583c3862153e4b97 |
| actions/upload-artifact | v7.0.2 | cf430e030ddbb5b0abf93d22962f4752f3646cd9 |
| actions/download-artifact | v8.0.2 | 9000827ccba6bdab643e8b6fd33ac0654aef8333 |

Rationale: [Node20 удалён с runners](https://github.blog/changelog/2026-09-23-node-20-is-no-longer-available-in-github-actions/).
Проверены upstream release refs и action.yml; blob SHA action.yml не commit pin.
Runner minimum2.327.1; hosted runners, Docker checkout здесь не используется.
[checkout v7](https://github.com/actions/checkout/releases/tag/v7.0.0): fork checkout
на pull_request_target запрещён, текущий trusted github.workflow_sha сохраняется.
[setup-node](https://github.com/actions/setup-node/blob/v7.1.0/README.md):
package-manager-cache:false сохраняет отсутствие автоматического npm cache.
[setup-python](https://github.com/actions/setup-python/releases/tag/v7.0.0):
удалённый pip-install здесь не используется.
[upload](https://github.com/actions/upload-artifact/releases/tag/v7.0.0):
archive:false игнорирует name, поэтому сохранить ZIP и archive:true.
[download](https://github.com/actions/download-artifact/releases/tag/v8.0.0):
сохранить digest-mismatch:error и распаковку. Небезопасные opt-out flags исключены.

## Swift

Decision: native Xcode16.2 bin, строгая semantic version6.0.3; SDK не переключать.
[setup-swift v2.4.0](https://github.com/swift-actions/setup-swift/blob/v2.4.0/action.yml)
ещё Node20; простой bump не решает задачу.
[Текущий installer](https://github.com/swift-actions/setup-swift/blob/7ca6abe6b3b0e8b5421b88be48feee39cbf52c6a/src/macos-install.ts)
скачивает Swift.org и экспортирует TOOLCHAINS, но не DEVELOPER_DIR/xcode-select.
[macos14 image](https://github.com/actions/runner-images/blob/main/images/macos/macos-14-Readme.md)
содержит Xcode16.2; default15.4. Apple build6.0.3.1.10 отличается от Swift.org,
поэтому кэш не переиспользовать между builds.
[SwiftPM6.0.3](https://github.com/swiftlang/swift-package-manager/blob/swift-6.0.3-RELEASE/Sources/PackageModel/SwiftSDKs/SwiftSDK.swift#L522-L550)
берёт SDKROOT или xcrun --sdk macosx --show-sdk-path независимо от bin directory.
Сохранность SDK и реальную компиляцию доказать отдельно.
Альтернативы: новый setup-swift всё ещё Node20; переключение Xcode меняет SDK;
force flags скрывают проблему. Новый helper для трёх коротких шагов не нужен.
[macos14 retirement](https://github.com/actions/runner-images/issues/13518):
2026-11-02 и временные отключения до этой даты. Миграция image — отдельная работа,
этот фикс не доказывает долгую поддержку macos14.

## Сохранённая работа backup

Принятый infra/scripts/backup-rec-stack.sh создаёт dump/MinIO mirror, ротации
не содержит. docs/deployments/2brain-rec/release-v2026.10.16.6.md описывает
пять файлов другого владельца; это историческое evidence, не текущий сервер.
Decision: сначала инвентаризация stash с index/untracked parent и сопоставление
с чужой копией; не apply/pop/drop, не выводить приватный diff. Не придумывать
срок хранения. Использовать существующий Git, новый сервис не нужен.

## Четыре post-deploy результата

infra/scripts/cd-remote-runtime.sh:1454–1457 пока печатает required_post_deploy.
PlaybackNormalizationDeploymentEvidence в apps/server/src/twobrain_rec_server/deployment.py
не принимает ready без четырёх pass; cleanup_result — имя поля модели.

| Сценарий | Существующий путь | Что ещё доказать |
|---|---|---|
| automatic_retry | normalization/service.py, pickup.py, worker.py; integration/test_playback_normalization_retry.py и restart.py | синтетический временный отказ и автоматическое восстановление без ручного retry |
| backfill_inventory | inventory_playback_backfill_page, test_playback_normalization_backfill.py | полнота/blocked reasons; функция inventory пишет, не read-only |
| range_playback | api/cabinet.py, cabinet/egress.py; test_cabinet_playback_route.py | авторизация, 200/206/416, браузерная перемотка на разрешённой синтетике |
| normalization_cleanup | cleanup_unpublished_normalization_attempts, cleanup_normalization_attempt, test_playback_normalization_deletion.py | БД/objects/temp residues, сохранность active lease и accepted source |

Переиспользовать apps/server/scripts/run_local_postgres_tests.sh --focused,
infra/scripts/test-playback-normalization-container.sh и существующие F099
quickstart/contracts; новый retry/backfill API запрещён F099. Исторический
образец: specs/099-review-m4a-normalization/validation/release-closeout.md,
синтетика/Range/retry/inventory, но не текущее исполнение.
verify_playback_normalization_worker_ready.py --control создаёт workflow;
capability/poller check не заменяет четыре сценария.

US2/US3 требуют фактов и отдельного design/review до кода или разрешения на
изменение сервера. Это запланированные исследовательские задачи, а не скрытые
предположения, разрешающие первый CI-срез.
