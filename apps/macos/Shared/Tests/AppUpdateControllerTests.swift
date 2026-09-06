import Foundation
import AppKit
import SwiftUI
import Sparkle
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

@MainActor
final class AppUpdateControllerTests: XCTestCase {
    func testTrustedConfigurationRequiresCompleteHTTPSSignedFeedSettings() throws {
        let configuration = try XCTUnwrap(AppUpdateConfiguration(infoDictionary: validInfoDictionary()))

        XCTAssertEqual(configuration.feedURL.absoluteString, "https://rec.2brain.pro/static/public/downloads/graf-appcast.xml")
        XCTAssertEqual(configuration.installedVersion, "2026.07.17.1")

        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["CFBundleIdentifier": "example.invalid"])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["CFBundleName": "Other"])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUFeedURL": "http://rec.2brain.pro/graf-appcast.xml"])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUFeedURL": "https:///graf-appcast.xml"])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUFeedURL": "https://rec.2brain.pro/latest.xml"])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUFeedURL": "https://token@rec.2brain.pro/graf-appcast.xml"])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUPublicEDKey": ""])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SURequireSignedFeed": false])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUVerifyUpdateBeforeExtraction": false])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUSignedFeedFailureExpirationInterval": 86_400])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUEnableAutomaticChecks": false])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUScheduledCheckInterval": 3_600])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUAutomaticallyUpdate": true])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUAllowsAutomaticUpdates": true])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["SUEnableSystemProfiling": true])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["CFBundleVersion": "1.0"])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["CFBundleVersion": "2026.02.29.1", "CFBundleShortVersionString": "2026.02.29.1"])))
        XCTAssertNil(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["CFBundleShortVersionString": "2026.07.16.1"])))
        XCTAssertTrue(AppUpdateConfiguration.isValidCalVer("2024.02.29.1"))
    }

    func testOnlyTrustworthyAvailableStatesShowSidebarBadge() {
        for phase in AppUpdatePhase.allCases {
            let presentation = AppUpdatePresentation(
                phase: phase,
                availableVersion: phase == .available || phase == .deferredForCapture ? "2026.07.18.1" : nil,
                isUserInitiated: false,
                message: nil
            )

            XCTAssertEqual(
                presentation.showsSidebarBadge,
                phase == .available || phase == .deferredForCapture,
                "Unexpected badge behavior for \(phase)"
            )
        }
    }

    func testOverlappingManualCheckKeepsKnownUpdateAndMarksUserIntent() {
        let available = AppUpdatePolicy.available(
            version: "2026.07.18.1",
            userInitiated: false,
            protectedWork: .idle
        )

        let focused = AppUpdatePolicy.beginCheck(from: available, userInitiated: true)

        XCTAssertEqual(focused.phase, .available)
        XCTAssertEqual(focused.availableVersion, "2026.07.18.1")
        XCTAssertTrue(focused.isUserInitiated)
        XCTAssertTrue(focused.showsSidebarBadge)

        let checking = AppUpdatePolicy.beginCheck(from: .idle, userInitiated: false)
        let overlapping = AppUpdatePolicy.beginCheck(from: checking, userInitiated: true)
        XCTAssertEqual(overlapping.phase, .checking)
        XCTAssertTrue(overlapping.isUserInitiated)
    }

    func testDismissAndSkipKeepBadgeWhileWithdrawalClearsIt() {
        let available = AppUpdatePolicy.available(
            version: "2026.07.18.1",
            userInitiated: true,
            protectedWork: .idle
        )

        let dismissed = AppUpdatePolicy.userChoice(.dismiss, from: available, protectedWork: .idle)
        XCTAssertEqual(dismissed.phase, .available)
        XCTAssertTrue(dismissed.showsSidebarBadge)

        let skipped = AppUpdatePolicy.userChoice(.skip, from: available, protectedWork: .idle)
        XCTAssertEqual(skipped.phase, .available)
        XCTAssertTrue(skipped.showsSidebarBadge)

        let withdrawn = AppUpdatePolicy.noUpdate(userInitiated: false, incompatible: false)
        XCTAssertEqual(withdrawn.phase, .current)
        XCTAssertFalse(withdrawn.showsSidebarBadge)
    }

    func testProtectedWorkMovesKnownUpdateBetweenAvailableAndDeferred() {
        let available = AppUpdatePolicy.available(
            version: "2026.07.18.1",
            userInitiated: false,
            protectedWork: .idle
        )
        let protected = ProtectedUpdateWork(captureActive: true)

        let deferred = AppUpdatePolicy.protectedWorkChanged(from: available, protectedWork: protected)
        XCTAssertEqual(deferred.phase, .deferredForCapture)
        XCTAssertEqual(deferred.availableVersion, "2026.07.18.1")

        let resumed = AppUpdatePolicy.protectedWorkChanged(from: deferred, protectedWork: .idle)
        XCTAssertEqual(resumed.phase, .available)
        XCTAssertEqual(resumed.availableVersion, "2026.07.18.1")
    }

    func testInstallChoiceDefersDuringCaptureAndInstallsWhenIdle() {
        let available = AppUpdatePolicy.available(
            version: "2026.07.18.1",
            userInitiated: true,
            protectedWork: .idle
        )

        let deferred = AppUpdatePolicy.userChoice(
            .install,
            from: available,
            protectedWork: ProtectedUpdateWork(recordingFinalizing: true)
        )
        XCTAssertEqual(deferred.phase, .deferredForCapture)

        let installing = AppUpdatePolicy.userChoice(.install, from: available, protectedWork: .idle)
        XCTAssertEqual(installing.phase, .installing)
    }

    func testEveryProtectedLifecycleKindDefersAnAvailableUpdate() {
        let available = AppUpdatePolicy.available(
            version: "2026.07.18.1",
            userInitiated: false,
            protectedWork: .idle
        )
        let protectedWork: [ProtectedUpdateWork] = [
            ProtectedUpdateWork(captureActive: true),
            ProtectedUpdateWork(captureTransitioning: true),
            ProtectedUpdateWork(recordingFinalizing: true),
            ProtectedUpdateWork(terminationCleanupPending: true)
        ]

        for work in protectedWork {
            XCTAssertTrue(work.isProtected)
            XCTAssertEqual(
                AppUpdatePolicy.protectedWorkChanged(from: available, protectedWork: work).phase,
                .deferredForCapture
            )
        }
    }

    func testApplicationMenuAndLifecycleRouteThroughTheSingleUpdateController() throws {
        let source = try Self.readRepositoryFile("apps/macos/RecApp/App/TwoBrainRecApp.swift")

        XCTAssertTrue(source.contains("withTitle: \"Проверить обновления…\""))
        XCTAssertTrue(source.contains("action: #selector(AppLifecycleDelegate.checkForUpdates(_:))"))
        XCTAssertTrue(source.contains("updateItem.target = zoomTarget"))
        XCTAssertTrue(source.contains("NSMenuItemValidation"))
        XCTAssertTrue(source.contains("appUpdateController.isManualCheckActionEnabled"))
        XCTAssertTrue(source.contains("private let appUpdateController: AppUpdateController"))
        XCTAssertTrue(source.contains("appUpdateController.start()"))
        XCTAssertTrue(source.contains("appUpdateController.updateProtectedWork(protectedUpdateWork)"))
        XCTAssertTrue(source.contains("captureActive: captureSession.map { CaptureStatusItem.showsStopButton"))
        XCTAssertTrue(source.contains("captureTransitioning: recordingStartInProgress || recordingStopInProgress"))
        XCTAssertTrue(source.contains("recordingFinalizing: recordingStopInProgress"))
        XCTAssertTrue(source.contains("terminationCleanupPending: terminationCleanupInProgress"))
        XCTAssertTrue(source.contains("ProtectedUpdateWork(terminationCleanupPending: true)"))
        XCTAssertTrue(source.contains("appUpdateController.updateProtectedWork(.idle)"))
        XCTAssertTrue(source.contains("Проверка обновлений недоступна"))
    }

    func testIncompatibleManualResultIsDistinctFromCurrentResult() {
        let current = AppUpdatePolicy.noUpdate(userInitiated: true, incompatible: false)
        let incompatible = AppUpdatePolicy.noUpdate(userInitiated: true, incompatible: true)

        XCTAssertEqual(current.phase, .current)
        XCTAssertEqual(incompatible.phase, .current)
        XCTAssertNotEqual(current.message, incompatible.message)
        XCTAssertTrue(incompatible.message?.contains("не поддерживает") == true)
    }

    func testGentleReminderClearsDeferredOfferAfterUserAttention() throws {
        let source = try Self.readRepositoryFile(
            "apps/macos/RecApp/Sources/Updates/AppUpdateController.swift"
        )

        XCTAssertTrue(source.contains("standardUserDriverDidReceiveUserAttention(forUpdate"))
        XCTAssertTrue(source.contains("app_update.offer_received_attention"))
    }

    func testRelaunchGateRetainsAtMostOneContinuationAndInvokesItOnce() {
        let gate = AppUpdateRelaunchGate(protectedWork: ProtectedUpdateWork(captureTransitioning: true))
        var firstInvocationCount = 0
        var secondInvocationCount = 0

        XCTAssertTrue(gate.postponeIfNeeded { firstInvocationCount += 1 })
        XCTAssertTrue(gate.postponeIfNeeded { secondInvocationCount += 1 })
        XCTAssertTrue(gate.hasRetainedContinuation)

        XCTAssertTrue(gate.updateProtectedWork(.idle))
        XCTAssertEqual(firstInvocationCount, 1)
        XCTAssertEqual(secondInvocationCount, 0)
        XCTAssertFalse(gate.hasRetainedContinuation)

        XCTAssertFalse(gate.updateProtectedWork(.idle))
        XCTAssertEqual(firstInvocationCount, 1)
    }

    func testKnownVersionRemainsVisibleDuringFailureAndProgress() {
        let available = AppUpdatePolicy.available(version: "2026.07.18.1", userInitiated: false, protectedWork: .idle)
        let failed = AppUpdatePolicy.failure(userInitiated: false, from: available)
        XCTAssertEqual(failed.availableVersion, available.availableVersion)
        XCTAssertTrue(failed.showsSidebarBadge)
        XCTAssertTrue(AppUpdatePolicy.beginCheck(from: failed, userInitiated: true).showsSidebarBadge)
        for phase in [AppUpdatePhase.downloading, .readyToInstall, .installing] {
            XCTAssertTrue(AppUpdatePresentation(phase: phase, availableVersion: "2026.07.18.1", isUserInitiated: true, message: nil).showsSidebarBadge)
        }
    }

    func testReminderRoundTripRejectsChangedTrustInstalledVersionAndCorruption() throws {
        let config = try XCTUnwrap(AppUpdateConfiguration(infoDictionary: validInfoDictionary()))
        let reminder = try XCTUnwrap(AppUpdateReminder(buildVersion: "2026.07.18.10", displayVersion: "2026.07.18.10", configuration: config, systemVersion: "test-os"))
        let data = try JSONEncoder().encode(reminder)
        XCTAssertEqual(AppUpdateReminder.restore(data, configuration: config, systemVersion: "test-os"), reminder)
        XCTAssertNil(AppUpdateReminder.restore(data, configuration: config, systemVersion: "new-os"))
        for overrides: [String: Any] in [
            ["CFBundleVersion": "2026.07.18.10", "CFBundleShortVersionString": "2026.07.18.10"],
            ["CFBundleVersion": "2026.07.19.1", "CFBundleShortVersionString": "2026.07.19.1"],
            ["SUFeedURL": "https://example.com/graf-appcast.xml"],
            ["SUPublicEDKey": Data(repeating: 1, count: 32).base64EncodedString()]
        ] {
            let changed = try XCTUnwrap(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: overrides)))
            XCTAssertNil(AppUpdateReminder.restore(data, configuration: changed, systemVersion: "test-os"))
        }
        XCTAssertNil(AppUpdateReminder.restore(Data("invalid".utf8), configuration: config, systemVersion: "test-os"))
        XCTAssertNil(AppUpdateReminder.restore(Data(repeating: 0, count: 4097), configuration: config, systemVersion: "test-os"))
        XCTAssertNil(AppUpdateReminder(buildVersion: "2026.07.17.1", displayVersion: "2026.07.17.1", configuration: config))
        XCTAssertNil(AppUpdateReminder(buildVersion: "2026.07.16.1", displayVersion: "2026.07.16.1", configuration: config))
        XCTAssertNil(AppUpdateReminder(buildVersion: "2026.07.18.1", displayVersion: "<script>", configuration: config))
        let later = try XCTUnwrap(AppUpdateConfiguration(infoDictionary: validInfoDictionary(overrides: ["CFBundleVersion": "2026.07.18.9", "CFBundleShortVersionString": "2026.07.18.9"])))
        XCTAssertNotNil(AppUpdateReminder(buildVersion: "2026.07.18.10", displayVersion: "2026.07.18.10", configuration: later))
    }

    func testNoUpdateKeepsSkippedOfferUnlessThatVersionIsIncompatible() {
        let available = AppUpdatePolicy.available(version: "2026.07.18.1", userInitiated: false, protectedWork: .idle)
        let skipped = AppUpdatePolicy.userChoice(.skip, from: available, protectedWork: .idle)
        XCTAssertEqual(AppUpdatePolicy.noUpdate(userInitiated: false, incompatible: false, from: skipped), skipped)
        XCTAssertFalse(AppUpdatePolicy.noUpdate(userInitiated: true, incompatible: true, from: skipped).showsSidebarBadge)
    }

    func testOnlyVerifiedRemovalWithdrawsTheKnownBuild() throws {
        let config = try XCTUnwrap(AppUpdateConfiguration(infoDictionary: validInfoDictionary()))
        let reminder = try XCTUnwrap(AppUpdateReminder(buildVersion: "2026.07.18.1", displayVersion: "2026.07.18.1", configuration: config))
        XCTAssertFalse(reminder.isWithdrawn(from: [], signatureVerified: false))
        XCTAssertFalse(reminder.isWithdrawn(from: ["2026.07.18.1"], signatureVerified: true))
        XCTAssertTrue(reminder.isWithdrawn(from: ["2026.07.17.1"], signatureVerified: true))
    }

    func testControllerRestoresReminderAndClearsItAfterApplicationUpgrade() throws {
        let suiteName = "AppUpdateControllerTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let config = try XCTUnwrap(AppUpdateConfiguration(infoDictionary: validInfoDictionary()))
        let reminder = try XCTUnwrap(AppUpdateReminder(buildVersion: "2026.07.18.1", displayVersion: "2026.07.18.1", configuration: config))
        defaults.set(try JSONEncoder().encode(reminder), forKey: AppUpdateController.reminderDefaultsKey)
        let controller = AppUpdateController(infoDictionary: validInfoDictionary(), defaults: defaults)
        XCTAssertTrue(controller.presentation.showsSidebarBadge)
        XCTAssertEqual(controller.presentation.availableVersion, "2026.07.18.1")
        XCTAssertTrue(controller.presentation.message?.contains("проверит") == true)
        let upgraded = AppUpdateController(infoDictionary: validInfoDictionary(overrides: [
            "CFBundleVersion": "2026.07.18.1", "CFBundleShortVersionString": "2026.07.18.1"
        ]), defaults: defaults)
        XCTAssertFalse(upgraded.presentation.showsSidebarBadge)
        XCTAssertNil(defaults.data(forKey: AppUpdateController.reminderDefaultsKey))
    }

    func testSparkleOfferPersistsThroughFailureCancellationAndRestart() throws {
        let suiteName = "AppUpdateControllerTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let controller = AppUpdateController(infoDictionary: validInfoDictionary(), defaults: defaults)
        let updater = SPUStandardUpdaterController(startingUpdater: false, updaterDelegate: nil, userDriverDelegate: nil).updater
        let item = try XCTUnwrap(SUAppcastItem(dictionary: [
            "sparkle:version": "2026.07.18.1",
            "sparkle:shortVersionString": "2026.07.18.1",
            "enclosure": ["url": "https://example.com/update.zip", "sparkle:version": "2026.07.18.1"]
        ]))
        controller.updater(updater, didFindValidUpdate: item)
        XCTAssertNotNil(defaults.data(forKey: AppUpdateController.reminderDefaultsKey))
        controller.updater(updater, failedToDownloadUpdate: item, error: URLError(.notConnectedToInternet))
        XCTAssertEqual(controller.presentation.phase, .failed)
        XCTAssertEqual(controller.presentation.availableVersion, item.displayVersionString)
        controller.userDidCancelDownload(updater)
        XCTAssertEqual(controller.presentation.phase, .available)
        controller.updaterDidNotFindUpdate(updater, error: NSError(domain: SUSparkleErrorDomain, code: Int(SUError.noUpdateError.rawValue)))
        XCTAssertTrue(controller.presentation.showsSidebarBadge)
        let restarted = AppUpdateController(infoDictionary: validInfoDictionary(), defaults: defaults)
        XCTAssertEqual(restarted.presentation.availableVersion, item.displayVersionString)
        controller.updaterDidNotFindUpdate(updater, error: NSError(domain: SUSparkleErrorDomain, code: Int(SUError.noUpdateError.rawValue), userInfo: [
            SPUNoUpdateFoundReasonKey: NSNumber(value: SPUNoUpdateFoundReason.systemIsTooOld.rawValue),
            SPULatestAppcastItemFoundKey: item
        ]))
        XCTAssertFalse(controller.presentation.showsSidebarBadge)
        XCTAssertNil(defaults.data(forKey: AppUpdateController.reminderDefaultsKey))
    }

    func testNoticeRendersAtMainWindowAndTrayWidths() throws {
        for width: CGFloat in [360, 900] {
            for scheme in [ColorScheme.light, .dark] {
                for phase in [AppUpdatePhase.available, .deferredForCapture, .failed] {
                    let presentation = AppUpdatePresentation(
                        phase: phase, availableVersion: "2026.09.06.10", isUserInitiated: false,
                        message: phase == .deferredForCapture
                            ? "Обновление установится после завершения записи."
                            : phase == .failed ? "Не удалось загрузить обновление. Повторите попытку."
                            : "Обновите GRAF, чтобы получить последние улучшения."
                    )
                    let renderer = ImageRenderer(content:
                        AppUpdateNotice(presentation: presentation, isActionEnabled: true, onUpdate: {})
                            .frame(width: width)
                            .background(Color(nsColor: .windowBackgroundColor))
                            .environment(\.colorScheme, scheme)
                    )
                    renderer.scale = 2
                    let image = try XCTUnwrap(renderer.cgImage)
                    XCTAssertEqual(image.width, Int(width * 2))
                    XCTAssertGreaterThan(image.height, 80)
                    XCTAssertLessThan(image.height, 440, "Notice should fit without hiding the workspace")
                    if let directory = ProcessInfo.processInfo.environment["GRAF_UPDATE_PREVIEW_DIR"] {
                        let url = URL(fileURLWithPath: directory)
                        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
                        let data = try XCTUnwrap(NSBitmapImageRep(cgImage: image).representation(using: .png, properties: [:]))
                        try data.write(to: url.appendingPathComponent("update-\(Int(width))-\(scheme)-\(phase.rawValue).png"))
                    }
                }
            }
        }
    }

    private func validInfoDictionary(overrides: [String: Any] = [:]) -> [String: Any] {
        var values: [String: Any] = [
            "CFBundleIdentifier": "pro.2brain.graf",
            "CFBundleName": "GRAF",
            "CFBundleDisplayName": "GRAF",
            "CFBundleVersion": "2026.07.17.1",
            "CFBundleShortVersionString": "2026.07.17.1",
            "SUFeedURL": "https://rec.2brain.pro/static/public/downloads/graf-appcast.xml",
            "SUPublicEDKey": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "SURequireSignedFeed": true,
            "SUVerifyUpdateBeforeExtraction": true,
            "SUSignedFeedFailureExpirationInterval": 0,
            "SUEnableAutomaticChecks": true,
            "SUScheduledCheckInterval": 14_400,
            "SUAutomaticallyUpdate": false,
            "SUAllowsAutomaticUpdates": false,
            "SUEnableSystemProfiling": false
        ]
        for (key, value) in overrides {
            values[key] = value
        }
        return values
    }

    private static func readRepositoryFile(_ relativePath: String) throws -> String {
        try String(
            contentsOf: repositoryRoot().appendingPathComponent(relativePath),
            encoding: .utf8
        )
    }

    private static func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            let marker = candidate.appendingPathComponent("apps/macos/Package.swift")
            if FileManager.default.fileExists(atPath: marker.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "AppUpdateControllerTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
#endif
