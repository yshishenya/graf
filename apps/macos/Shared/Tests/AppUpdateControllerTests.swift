import Foundation
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

    func testDismissKeepsBadgeWhileSkipAndWithdrawalClearIt() {
        let available = AppUpdatePolicy.available(
            version: "2026.07.18.1",
            userInitiated: true,
            protectedWork: .idle
        )

        let dismissed = AppUpdatePolicy.userChoice(.dismiss, from: available, protectedWork: .idle)
        XCTAssertEqual(dismissed.phase, .available)
        XCTAssertTrue(dismissed.showsSidebarBadge)

        let skipped = AppUpdatePolicy.userChoice(.skip, from: available, protectedWork: .idle)
        XCTAssertEqual(skipped.phase, .idle)
        XCTAssertFalse(skipped.showsSidebarBadge)

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

        XCTAssertTrue(source.contains("withTitle: \"Check for Updates…\""))
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
            "SUScheduledCheckInterval": 86_400,
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
