import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class LocalCacheSurfaceTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 1_800_000_000)

    func testManualCleanupCopyMatchesTheContract() {
        XCTAssertEqual(LocalCacheCleanupCopy.actionTitle, "Освободить место")
        XCTAssertEqual(
            LocalCacheCleanupCopy.confirmationTitle,
            "Удалить локальную копию транскрипции?"
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.confirmationBody,
            "Будет удалён только файл транскрипции этой записи. Аудио для прослушивания и описание записи " +
            "останутся на Mac. Встреча на сервере не удалится."
        )
        XCTAssertEqual(LocalCacheCleanupCopy.spaceLine(size: "1,2 ГБ"), "Освободится: 1,2 ГБ.")
        XCTAssertEqual(LocalCacheCleanupCopy.confirmButtonTitle(size: "1,2 ГБ"), "Освободить 1,2 ГБ")
        XCTAssertEqual(LocalCacheCleanupCopy.cancelTitle, "Отмена")
        XCTAssertEqual(
            LocalCacheCleanupCopy.success,
            "Локальная копия транскрипции удалена. Аудио для прослушивания осталось."
        )
        XCTAssertEqual(LocalCacheCleanupCopy.noop, "Эта запись уже очищена.")
        XCTAssertEqual(
            LocalCacheCleanupCopy.unexpectedMissing,
            "Файл уже отсутствует. Проверьте запись перед повторной очисткой."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.accessibilityAction,
            "Освободить место. Будет удалён только локальный файл транскрипции. Аудио и описание записи останутся."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.accessibilityConfirmation,
            "Подтвердите удаление локальной копии транскрипции. Серверная встреча не удаляется."
        )
        XCTAssertFalse(LocalCacheCleanupCopy.confirmationBody.contains("сервер удалит"))
    }

    func testAutomaticEvictionCopyMatchesTheContract() {
        XCTAssertEqual(LocalCacheCleanupCopy.cacheTitle, "Локальный кэш")
        XCTAssertEqual(
            LocalCacheCleanupCopy.cacheExplanation,
            "GRAF может автоматически удалять только локальные файлы транскрипции подтверждённых записей. " +
            "Аудио для прослушивания и описание записи остаются."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.autoEvictionToggle,
            "Автоматически освобождать место"
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.autoEvictionToggleDetail,
            "Удаляются только файлы транскрипции записей, которые уже доступны на сервере."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.autoEvictionDisabled,
            "Автоматическая очистка выключена. Новые файлы не удаляются."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.autoEvictionOperatorOverride,
            "Автоматическая очистка временно отключена администратором."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.evictionResult(size: "0,9 ГБ"),
            "Освобождено 0,9 ГБ. Аудио для прослушивания осталось."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.cacheWarning,
            "Локальный кэш заполняется. Старые подтверждённые файлы транскрипции будут очищены автоматически."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.statusLine(used: "4,1 ГБ", budget: "5 ГБ"),
            "Занято 4,1 ГБ из 5 ГБ."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.accessibilityStatus(used: "4,1 ГБ", budget: "5 ГБ"),
            "Локальный кэш: занято 4,1 ГБ из 5 ГБ."
        )
    }

    func testReasonCopyIsUserFacingAndNeverLeaksInternalCodes() {
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.proofMissing),
            "Серверная копия ещё не подтверждена. Запись оставлена на Mac."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.proofStale),
            "Данные о серверной копии устарели. Повторите проверку позже."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.revisionMismatch),
            "Серверная копия относится к другой версии записи. Запись оставлена на Mac."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.playbackNotAvailable),
            "Сервер пока не может воспроизвести запись. Запись оставлена на Mac."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.playbackNotVerified),
            "Сервер не подтвердил сохранность аудио. Запись оставлена на Mac."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.archiveAudioFalse),
            "Сервер не сохранил аудио для этой записи. Запись оставлена на Mac."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.retentionUnsafe),
            "Срок хранения на сервере скоро истечёт. Запись оставлена на Mac."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.deletionOperationOpen),
            "Встреча удаляется. Дождитесь завершения удаления."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.accountScopeMismatch),
            "Запись относится к другому аккаунту. Переключитесь на нужный аккаунт."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.localArtifactsMissing),
            "Локальные файлы записи неполные. Очистка недоступна."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.localIntegrityUnverified),
            "Локальные файлы не прошли проверку. Очистка недоступна."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.dependencyUnavailable),
            "Не удалось проверить серверную копию. Попробуйте позже."
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.reason(.notUploaded),
            "Очистка сейчас недоступна. Запись оставлена на Mac."
        )

        for code in LocalCacheEligibilityReason.allCases {
            let copy = LocalCacheCleanupCopy.reason(code)
            XCTAssertFalse(copy.isEmpty, "\(code.rawValue)")
            XCTAssertFalse(copy.contains(code.rawValue), "\(code.rawValue) leaked into user copy")
            XCTAssertFalse(copy.contains("_"), "\(code.rawValue) leaked an internal token")
        }
    }

    func testOutcomeCopyCoversTheDefinedCleanupResults() {
        XCTAssertEqual(
            LocalCacheCleanupCopy.outcomeMessage(.completed(bytes: 10)),
            LocalCacheCleanupCopy.success
        )
        XCTAssertEqual(LocalCacheCleanupCopy.outcomeMessage(.noop), LocalCacheCleanupCopy.noop)
        XCTAssertEqual(
            LocalCacheCleanupCopy.outcomeMessage(.unexpectedMissing),
            LocalCacheCleanupCopy.unexpectedMissing
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.outcomeMessage(
                .notEligible(primaryReason: .proofMissing, allReasons: [.proofMissing])
            ),
            LocalCacheCleanupCopy.reason(.proofMissing)
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.outcomeMessage(.failed(code: "unlink_failed")),
            LocalCacheCleanupCopy.defaultUnavailable
        )
        XCTAssertEqual(
            LocalCacheCleanupCopy.outcomeMessage(.scopeChanged),
            LocalCacheCleanupCopy.scopeChanged
        )
    }

    func testLocalRecordingRowExposesFreeSpaceOnlyForEligibleUploads() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("f296-surface-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let scope = try RecordingDeletionScope(
            serverOrigin: "https://sync.invalid",
            workspaceID: "workspace",
            actorUserID: "owner"
        )

        let eligible = makeItem(
            id: "eligible",
            directoryId: "eligible",
            meetingId: "meeting-eligible",
            scope: scope,
            root: root,
            mediaBytes: 1_000
        )
        let localOnly = makeItem(
            id: "local-only",
            directoryId: "local-only",
            meetingId: nil,
            scope: scope,
            root: root,
            mediaBytes: 1_000
        )
        let legacy = makeItem(
            id: "legacy",
            directoryId: "legacy",
            meetingId: "meeting-legacy",
            scope: scope,
            root: root,
            mediaBytes: 1_000,
            schemaVersion: LocalRecordingManifest.legacySchemaVersion
        )
        let deleting = makeItem(
            id: "deleting",
            directoryId: "deleting",
            meetingId: "meeting-deleting",
            scope: scope,
            root: root,
            mediaBytes: 1_000
        ).withConflict(.accessRevoked)

        let rows = EmbeddedCabinetLocalRecordingRow.rows(
            for: [eligible, localOnly, legacy, deleting],
            recordingsRootURL: root
        )

        let eligibleRow = try XCTUnwrap(rows.first { $0.id == "eligible" })
        XCTAssertEqual(eligibleRow.canFreeSpace, true)
        XCTAssertEqual(eligibleRow.spaceToFreeBytes, 1_000)
        XCTAssertNotEqual(try XCTUnwrap(rows.first { $0.id == "local-only" }).canFreeSpace, true)
        XCTAssertNotEqual(try XCTUnwrap(rows.first { $0.id == "legacy" }).canFreeSpace, true)
        XCTAssertNotEqual(try XCTUnwrap(rows.first { $0.id == "deleting" }).canFreeSpace, true)

        XCTAssertEqual(
            EmbeddedCabinetLocalRecordingBridge.allowedAction(
                from: ["action": "freeSpace", "id": "eligible"],
                rows: rows
            )?.action,
            "freeSpace"
        )
        XCTAssertNil(EmbeddedCabinetLocalRecordingBridge.allowedAction(
            from: ["action": "freeSpace", "id": "local-only"],
            rows: rows
        ))
    }

    func testSurfaceAndWiringExposeTheRequiredAccessibilityIdentifiers() throws {
        let root = repositoryRoot()
        let surface = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/LocalCacheSurfaceView.swift"),
            encoding: .utf8
        )
        for identifier in [
            "local-cache-status",
            "local-cache-status-refresh",
            "local-cache-auto-eviction-toggle",
            "local-cache-auto-eviction-disabled",
            "local-cache-warning",
            "local-cache-last-freed",
            "local-cache-cleanup-confirmation",
            "local-cache-cleanup-confirm",
            "local-cache-cleanup-cancel",
            "local-cache-cleanup-result",
        ] {
            XCTAssertTrue(surface.contains(identifier), identifier)
        }
        XCTAssertTrue(surface.contains("LocalCacheCleanupCopy.confirmationTitle"))
        XCTAssertTrue(surface.contains("LocalCacheCleanupCopy.confirmationBody"))
        XCTAssertTrue(surface.contains("LocalCacheCleanupCopy.spaceLine"))

        let shell = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )
        XCTAssertTrue(shell.contains("LocalCacheStatusCardView("))
        XCTAssertTrue(shell.contains("local-cache-cleanup-\\(item.id)"))
        XCTAssertTrue(shell.contains("LocalCacheCleanupConfirmationView("))
        XCTAssertTrue(shell.contains("LocalCacheCleanupCopy.outcomeMessage"))
        XCTAssertTrue(shell.contains("onFreeLocalSpace"))

        let content = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/AppShell/ContentView.swift"),
            encoding: .utf8
        )
        XCTAssertTrue(content.contains("cleanupLocalTranscription(itemID:"))
        XCTAssertTrue(content.contains("onFreeLocalSpace:"))
        XCTAssertTrue(content.contains("onRefreshLocalCacheStatus:"))
        XCTAssertTrue(content.contains("onSetAutoEvictionEnabled:"))
        XCTAssertTrue(content.contains("runLocalCacheEviction(trigger: .launch)"))
        XCTAssertTrue(content.contains("runLocalCacheEviction(trigger: .recordingStopped)"))
        XCTAssertTrue(content.contains("runLocalCacheEviction(trigger: .uploadFinalized)"))
        XCTAssertTrue(content.contains("runLocalCacheEviction(trigger: .footprintRefresh)"))
    }

    func testEvictionPolicyThresholdsAndResolvedReserve() {
        let policy = LocalCacheEvictionPolicy.productBaseline
        XCTAssertEqual(policy.budgetBytes, 5_000_000_000)
        XCTAssertEqual(policy.warningFraction, 0.8)
        XCTAssertEqual(policy.criticalFraction, 0.95)
        XCTAssertEqual(policy.reserveCapBytes, 10_000_000_000)
        XCTAssertEqual(policy.retentionDays, 7)
        XCTAssertEqual(policy.warningBytes, 4_000_000_000)
        XCTAssertEqual(policy.criticalBytes, 4_750_000_000)
        XCTAssertEqual(policy.resolvedReserveBytes(diskCapacityBytes: 50_000_000_000), 5_000_000_000)
        XCTAssertEqual(policy.resolvedReserveBytes(diskCapacityBytes: 200_000_000_000), 10_000_000_000)
        XCTAssertEqual(policy.resolvedReserveBytes(diskCapacityBytes: nil), 10_000_000_000)

        XCTAssertEqual(
            policy.threshold(usedBytes: 3_900_000_000, freeDiskBytes: 100_000_000_000,
                             diskCapacityBytes: 200_000_000_000),
            .normal
        )
        XCTAssertEqual(
            policy.threshold(usedBytes: 4_000_000_000, freeDiskBytes: 100_000_000_000,
                             diskCapacityBytes: 200_000_000_000),
            .warning80
        )
        XCTAssertEqual(
            policy.threshold(usedBytes: 4_800_000_000, freeDiskBytes: 100_000_000_000,
                             diskCapacityBytes: 200_000_000_000),
            .warning95
        )
        XCTAssertEqual(
            policy.threshold(usedBytes: 5_000_000_000, freeDiskBytes: 100_000_000_000,
                             diskCapacityBytes: 200_000_000_000),
            .full
        )
        XCTAssertEqual(
            policy.threshold(usedBytes: 1, freeDiskBytes: 10_000_000_000,
                             diskCapacityBytes: 200_000_000_000),
            .full
        )
        XCTAssertEqual(
            policy.threshold(usedBytes: 1, freeDiskBytes: nil, diskCapacityBytes: 200_000_000_000),
            .unknown
        )
    }

    func testCleanupCandidatePolicyFiltersSortsAndBounds() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("f296-policy-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let scope = try RecordingDeletionScope(
            serverOrigin: "https://sync.invalid",
            workspaceID: "workspace",
            actorUserID: "owner"
        )

        var eligible: [DesktopUploadQueueItem] = []
        for index in 0..<35 {
            var item = makeItem(
                id: "eligible-\(index)",
                directoryId: "eligible-\(index)",
                meetingId: "meeting-\(index)",
                scope: scope,
                root: root,
                mediaBytes: 1_000
            )
            item.createdAt = now.addingTimeInterval(-Double(index) * 60)
            eligible.append(item)
        }
        var localOnly = makeItem(
            id: "local-only", directoryId: "local-only", meetingId: nil,
            scope: scope, root: root, mediaBytes: 1_000
        )
        localOnly.isLocalUnbound = true
        let legacy = makeItem(
            id: "legacy", directoryId: "legacy", meetingId: "meeting-legacy",
            scope: scope, root: root, mediaBytes: 1_000,
            schemaVersion: LocalRecordingManifest.legacySchemaVersion
        )
        let deleting = makeItem(
            id: "deleting", directoryId: "deleting", meetingId: "meeting-deleting",
            scope: scope, root: root, mediaBytes: 1_000
        ).withConflict(.accessRevoked)
        var queued = makeItem(
            id: "queued", directoryId: "queued", meetingId: "meeting-queued",
            scope: scope, root: root, mediaBytes: 1_000
        )
        queued.state = .queued
        let missingSize = makeItem(
            id: "missing-size", directoryId: "missing-size", meetingId: "meeting-size",
            scope: scope, root: root, mediaBytes: 0
        )

        let all = eligible + [localOnly, legacy, deleting, queued, missingSize]
        XCTAssertEqual(LocalCacheCleanupCandidatePolicy.eligibleCandidateCount(for: all), 35)
        for ineligible in [localOnly, legacy, deleting, queued, missingSize] {
            XCTAssertNil(
                LocalCacheCleanupCandidatePolicy.cleanupBytes(for: ineligible),
                ineligible.id
            )
        }
        XCTAssertEqual(
            LocalCacheCleanupCandidatePolicy.cleanupBytes(for: eligible[0]),
            1_000
        )

        let panel = LocalCacheCleanupCandidatePolicy.panelCandidates(for: all)
        XCTAssertEqual(panel.count, LocalCacheCleanupCandidatePolicy.maximumPanelCandidates)
        XCTAssertEqual(panel.first?.itemID, "eligible-34")
        XCTAssertEqual(panel.last?.itemID, "eligible-5")
        XCTAssertEqual(panel.map(\.startedAt), panel.map(\.startedAt).sorted())
        XCTAssertTrue(panel.allSatisfy { $0.bytes == 1_000 })
        XCTAssertTrue(LocalCacheCleanupCandidatePolicy.panelCandidates(for: []).isEmpty)
        XCTAssertTrue(LocalCacheCleanupCandidatePolicy.panelCandidates(for: all, limit: 0).isEmpty)
    }

    func testCleanupCandidatePolicyKeepsPartialContinuityRecording() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("f296-partial-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let scope = try RecordingDeletionScope(
            serverOrigin: "https://sync.invalid",
            workspaceID: "workspace",
            actorUserID: "owner"
        )
        let partial = makeItem(
            id: "partial",
            directoryId: "partial",
            meetingId: "meeting-partial",
            scope: scope,
            root: root,
            mediaBytes: 1_000,
            partialContinuity: true
        )

        XCTAssertTrue(partial.artifactProfile.isUploadable)
        XCTAssertNil(LocalCacheCleanupCandidatePolicy.cleanupBytes(for: partial))
        XCTAssertEqual(LocalCacheCleanupCandidatePolicy.eligibleCandidateCount(for: [partial]), 0)
        XCTAssertTrue(LocalCacheCleanupCandidatePolicy.panelCandidates(for: [partial]).isEmpty)
    }

    func testServerModeShellExposesCachePanelAndReusesConfirmation() throws {
        let root = repositoryRoot()
        let shell = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )
        XCTAssertTrue(shell.contains("local-cache-open"))
        XCTAssertTrue(shell.contains("LocalCachePanelView("))
        XCTAssertTrue(shell.contains("showsLocalCachePanel"))
        XCTAssertTrue(shell.contains("pendingCleanupAfterPanel = prompt"))
        XCTAssertTrue(shell.contains("cleanupPrompt = pending"))
        XCTAssertTrue(shell.contains("await refreshLocalCacheStatus()"))
        XCTAssertTrue(shell.contains("await refreshCleanupAvailability()"))
        XCTAssertTrue(shell.contains(".onChange(of: uploadQueueItems)"))
        XCTAssertTrue(shell.contains("Task { await refreshCleanupAvailability() }"))
        XCTAssertFalse(shell.contains("guard !cabinetConfigured else { return }\n            await refreshLocalCacheStatus"))
        XCTAssertTrue(shell.contains("LocalCacheStatusCardView("))

        let surface = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/LocalCacheSurfaceView.swift"),
            encoding: .utf8
        )
        for identifier in [
            "local-cache-panel",
            "local-cache-panel-close",
            "local-cache-panel-empty",
            "local-cache-panel-cleanup-\\(candidate.itemID)",
        ] {
            XCTAssertTrue(surface.contains(identifier), identifier)
        }
        XCTAssertTrue(surface.contains("LocalCacheStatusCardView("))
        XCTAssertTrue(surface.contains("onRequestCleanup"))
        XCTAssertTrue(surface.contains("LocalCacheCleanupPrompt("))
        XCTAssertFalse(surface.contains("displayTitle"))
        XCTAssertFalse(surface.contains("recordingMetadata"))
    }

    func testAutomaticCleanupWarningIsHiddenWhenDisabled() {
        func presentation(
            _ settings: LocalCacheEvictionSettingSnapshot
        ) -> LocalCacheStatusPresentation {
            LocalCacheStatusPresentation(
                usedBytes: 4_500_000_000,
                budgetBytes: 5_000_000_000,
                freeDiskBytes: 100_000_000_000,
                diskCapacityBytes: 200_000_000_000,
                threshold: .warning80,
                settings: settings
            )
        }

        let enabled = presentation(.init(userEnabled: true, operatorDisabled: false))
        XCTAssertTrue(enabled.showsWarning)
        XCTAssertTrue(enabled.showsAutomaticCleanupWarning)

        let userDisabled = presentation(.init(userEnabled: false, operatorDisabled: false))
        XCTAssertTrue(userDisabled.showsWarning)
        XCTAssertFalse(userDisabled.showsAutomaticCleanupWarning)
        XCTAssertEqual(
            userDisabled.disabledExplanation,
            LocalCacheCleanupCopy.autoEvictionDisabled
        )

        let operatorDisabled = presentation(.init(userEnabled: true, operatorDisabled: true))
        XCTAssertFalse(operatorDisabled.showsAutomaticCleanupWarning)
        XCTAssertEqual(
            operatorDisabled.disabledExplanation,
            LocalCacheCleanupCopy.autoEvictionOperatorOverride
        )
    }

    func testCleanupAvailabilityGatesTheManualAction() throws {
        let root = repositoryRoot()
        let shell = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )
        XCTAssertTrue(shell.contains("cleanupOfferableItemIDs?.contains(item.id)"))
        XCTAssertTrue(shell.contains("onProbeLocalCacheCleanupAvailability"))
        XCTAssertTrue(shell.contains("refreshCleanupAvailability"))

        let surface = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/LocalCacheSurfaceView.swift"),
            encoding: .utf8
        )
        XCTAssertTrue(surface.contains("status.showsAutomaticCleanupWarning"))

        let availability = try String(
            contentsOf: root.appendingPathComponent(
                "apps/macos/RecApp/Sources/Upload/LocalCacheCleanupAvailability.swift"
            ),
            encoding: .utf8
        )
        XCTAssertTrue(availability.contains("LocalCacheFileIdentity.state"))
        XCTAssertTrue(availability.contains("LocalCacheCleanupAction.allCases"))
        XCTAssertTrue(availability.contains("receipt.state == .completed"))
    }

    func testSettingsDefaultOnAndOperatorOverrideIsReadEachTime() throws {
        let suiteName = "LocalCacheSurfaceTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defaults.removePersistentDomain(forName: suiteName)
        defer { defaults.removePersistentDomain(forName: suiteName) }

        XCTAssertTrue(LocalCacheEvictionSettings.userEnabled(defaults: defaults))
        defaults.set(false, forKey: LocalCacheEvictionSettings.userDefaultsKey)
        XCTAssertFalse(LocalCacheEvictionSettings.userEnabled(defaults: defaults))
        defaults.set(true, forKey: LocalCacheEvictionSettings.userDefaultsKey)
        XCTAssertTrue(LocalCacheEvictionSettings.userEnabled(defaults: defaults))

        let enabled = LocalCacheEvictionSettingSnapshot(userEnabled: true, operatorDisabled: false)
        let disabledByOperator = LocalCacheEvictionSettingSnapshot(
            userEnabled: true,
            operatorDisabled: true
        )
        XCTAssertTrue(enabled.effectiveEnabled)
        XCTAssertFalse(disabledByOperator.effectiveEnabled)
        XCTAssertTrue(LocalCacheEvictionSettings.operatorDisabled(
            environment: [LocalCacheEvictionSettings.operatorEnvironmentKey: "1"]
        ))
        XCTAssertTrue(LocalCacheEvictionSettings.operatorDisabled(
            environment: [LocalCacheEvictionSettings.operatorEnvironmentKey: "true"]
        ))
        XCTAssertFalse(LocalCacheEvictionSettings.operatorDisabled(environment: [:]))
        XCTAssertFalse(LocalCacheEvictionSettings.operatorDisabled(
            environment: [LocalCacheEvictionSettings.operatorEnvironmentKey: "0"]
        ))
    }

    // MARK: - Fixtures

    private func makeItem(
        id: String,
        directoryId: String,
        meetingId: String?,
        scope: RecordingDeletionScope,
        root: URL,
        mediaBytes: Int64,
        schemaVersion: String = LocalRecordingManifest.schemaVersion,
        partialContinuity: Bool? = nil
    ) -> DesktopUploadQueueItem {
        let directory = root.appendingPathComponent(directoryId, isDirectory: true)
        let item = DesktopUploadQueueItem(
            id: id,
            sessionId: "session-\(id)",
            directoryId: directoryId,
            localMediaRevisionId: "rev-\(id)",
            directoryPath: directory.path,
            manifestPath: directory.appendingPathComponent("manifest.json").path,
            microphonePath: "metadata-only",
            systemAudioPath: "metadata-only",
            state: .uploaded,
            retryMode: .terminal,
            retentionDeadline: now.addingTimeInterval(300 * 24 * 60 * 60),
            createdAt: now.addingTimeInterval(-400 * 24 * 60 * 60),
            updatedAt: now,
            meetingId: meetingId,
            artifactProfile: ArtifactCompletenessProfile(
                schemaVersion: schemaVersion,
                manifestPresent: true,
                microphonePresent: false,
                systemAudioPresent: false,
                manifestSha256: String(repeating: "a", count: 64),
                microphoneSha256: nil,
                systemAudioSha256: nil,
                manifestSizeBytes: 128,
                microphoneSizeBytes: 0,
                systemAudioSizeBytes: 0,
                durationSeconds: 60,
                trackCompleteness: [
                    UploadTrackCompleteness(
                        transportRole: .manifest,
                        fileName: "manifest.json",
                        present: true,
                        byteCount: 128,
                        sha256: String(repeating: "a", count: 64),
                        durationSeconds: 1
                    ),
                    UploadTrackCompleteness(
                        transportRole: .media,
                        fileName: "meeting-transcription.wav",
                        present: true,
                        byteCount: mediaBytes,
                        sha256: String(repeating: "b", count: 64),
                        durationSeconds: 60
                    ),
                    UploadTrackCompleteness(
                        transportRole: .playback,
                        fileName: "meeting-review.m4a",
                        present: true,
                        byteCount: 500,
                        sha256: String(repeating: "c", count: 64),
                        durationSeconds: 60
                    ),
                ],
                isUploadable: true
            ),
            serverTruth: ServerTruthFingerprint(
                meetingId: meetingId,
                uploadStatus: "finalized"
            ),
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: now,
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            ),
            partialContinuity: partialContinuity
        )
        var result = item
        result.ownerScope = scope
        result.isLocalUnbound = meetingId == nil
        result.serverCreationAttempted = meetingId != nil
        return result
    }

    private func repositoryRoot() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }
}

private extension DesktopUploadQueueItem {
    func withConflict(_ state: DesktopSyncConflictState) -> DesktopUploadQueueItem {
        var copy = self
        copy.syncConflictState = state
        return copy
    }
}
