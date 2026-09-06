import Foundation
import SwiftUI
import AppKit
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

@MainActor
final class SystemAudioPermissionUXTests: XCTestCase {
    func testGrantedPermissionsHaveNoRecoveryPresentation() {
        let result = SystemAudioPermissionGate().evaluate(
            microphone: .granted,
            systemAudio: .granted
        )

        XCTAssertTrue(result.allowsAcceptedRecording)
        XCTAssertNil(result.presentation)
    }

    func testNextPermissionSkipsGrantedStepsAndHistoryNeverGrantsAccess() {
        XCTAssertEqual(DesktopPermissionOnboardingStatus.unknown.nextPermission, .microphone)
        var state = DesktopPermissionOnboardingStatus(microphone: .granted, systemAudio: .unknown)
        XCTAssertEqual(state.nextPermission, .systemAudio)
        XCTAssertEqual(state.completedCount, 1)
        XCTAssertFalse(state.isReady)
        XCTAssertFalse(DesktopPermissionOnboardingStatus.needsSettings(state: .unknown, attempted: false))
        XCTAssertTrue(DesktopPermissionOnboardingStatus.needsSettings(state: .unknown, attempted: true))
        XCTAssertTrue(DesktopPermissionOnboardingStatus.needsSettings(state: .denied, attempted: false))
        XCTAssertFalse(DesktopPermissionOnboardingStatus.needsSettings(state: .granted, attempted: true))
        state.systemAudio = .granted
        XCTAssertTrue(state.isReady)
        XCTAssertNil(state.nextPermission)
        XCTAssertEqual(state.completedCount, 2)
        state.microphone = .denied
        XCTAssertFalse(state.isReady)
        XCTAssertEqual(state.nextPermission, .microphone)
    }

    func testProbeTimesOutAndIgnoresLateOrDuplicateCompletion() async {
        let timedOut = await SystemAudioPermissionProbe.check(timeoutSeconds: 0.01) { completion in
            DispatchQueue.global().asyncAfter(deadline: .now() + 0.04) { completion(true) }
        }
        XCTAssertFalse(timedOut)
        let nextResult = await SystemAudioPermissionProbe.check(timeoutSeconds: 0.1) { completion in
            completion(true)
            completion(false)
        }
        XCTAssertTrue(nextResult)
        try? await Task.sleep(for: .milliseconds(60))
        XCTAssertFalse(timedOut)
    }

    func testUnverifiedSystemAudioBlocksRecordingUntilRecovery() {
        let result = SystemAudioPermissionGate().evaluate(
            microphone: .granted,
            systemAudio: .stale
        )

        XCTAssertFalse(result.allowsAcceptedRecording)
        XCTAssertEqual(result.presentation?.title, "Права нужно проверить заново")
        XCTAssertEqual(result.presentation?.recoveryAction, .retryPermissionCheck)
    }

    func testMissingBothPermissionsUsesSpecificRecoveryCopy() {
        let result = SystemAudioPermissionGate().evaluate(
            microphone: .denied,
            systemAudio: .denied
        )

        XCTAssertEqual(result.presentation?.title, "Нужны права на запись")
        XCTAssertTrue(result.presentation?.message.contains("микрофону") == true)
        XCTAssertTrue(result.presentation?.message.contains("системного звука") == true)
        XCTAssertTrue(result.presentation?.message.contains("повторите запись") == true)
        XCTAssertFalse(result.presentation?.message.localizedCaseInsensitiveContains("run the check") == true)
        XCTAssertEqual(result.presentation?.recoveryAction, .grantBoth)
    }

    func testSystemAudioCopyDoesNotMentionVirtualDevices() {
        let result = SystemAudioPermissionGate().evaluate(
            microphone: .granted,
            systemAudio: .restricted
        )

        XCTAssertTrue(result.presentation?.message.contains("системного звука") == true)
        XCTAssertFalse(result.presentation?.message.localizedCaseInsensitiveContains("virtual") == true)
        XCTAssertFalse(result.presentation?.message.localizedCaseInsensitiveContains("driver") == true)
    }

    func testPermissionRecoveryActionsStaySeparateAndRussian() {
        XCTAssertEqual(DesktopPermissionOnboardingView.openSettingsTitle, "Открыть настройки macOS")
        XCTAssertEqual(DesktopPermissionOnboardingView.retryTitle, "Проверить снова")
        XCTAssertEqual(DesktopPermissionOnboardingView.restartTitle, "Перезапустить GRAF")
        XCTAssertTrue(DesktopPermissionOnboardingView.microphoneDeniedDetail.contains("повторный запрос"))
        XCTAssertTrue(DesktopPermissionOnboardingView.microphoneRestrictedDetail.contains("не может обойти"))
        XCTAssertNotEqual(
            DesktopPermissionOnboardingAccessibilityIdentifier.microphoneButton,
            DesktopPermissionOnboardingAccessibilityIdentifier.systemAudioButton
        )
        XCTAssertNotEqual(
            DesktopPermissionOnboardingAccessibilityIdentifier.restartButton,
            DesktopPermissionOnboardingAccessibilityIdentifier.finishButton
        )
        let devCopy = DesktopPermissionOnboardingView.systemAudioStepDetail(for: "GRAF Dev")
        XCTAssertTrue(devCopy.contains("GRAF Dev"))
        XCTAssertTrue(devCopy.contains("отдельно"))
    }

    func testRenderSyntheticPermissionStates() throws {
        guard let directory = ProcessInfo.processInfo.environment["GRAF_PERMISSION_PREVIEW_DIR"] else {
            throw XCTSkip("Set GRAF_PERMISSION_PREVIEW_DIR to render synthetic native permission previews")
        }
        let app = NSApplication.shared
        let originalIcon = app.applicationIconImage
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent()
        app.applicationIconImage = NSImage(contentsOf: root.appendingPathComponent("RecApp/Resources/AppIcon.icns"))
        defer { app.applicationIconImage = originalIcon }
        try FileManager.default.createDirectory(atPath: directory, withIntermediateDirectories: true)
        let scenarios: [(String, DesktopPermissionOnboardingStatus)] = [
            ("initial", .unknown),
            ("system-audio", .init(microphone: .granted, systemAudio: .unknown)),
            ("settings", .init(microphone: .granted, systemAudio: .denied)),
            ("compact-settings", .init(microphone: .granted, systemAudio: .denied)),
            ("restricted", .init(microphone: .restricted, systemAudio: .unknown)),
            ("recovery", .init(microphone: .granted, systemAudio: .stale)),
            ("ready", .init(microphone: .granted, systemAudio: .granted)),
        ]
        for scheme in [ColorScheme.light, .dark] {
            for (name, state) in scenarios {
                let view = DesktopPermissionOnboardingView(
                    status: state, applicationName: "GRAF Dev", isRequesting: false,
                    recoverySuggested: state.systemAudio == .stale,
                    onRequestMicrophone: {}, onRequestSystemAudio: {},
                    onOpenMicrophoneSettings: {}, onOpenSystemAudioSettings: {},
                    onRefresh: {}, onDismiss: {}, onFinish: {}, onRestart: {}
                )
                .environment(\.colorScheme, scheme)
                .background(scheme == .dark ? Color(nsColor: .init(white: 0.12, alpha: 1)) : .white)
                let png: Data
                if name == "compact-settings" {
                    // ImageRenderer does not render the AppKit scroll view; exercise an actual host.
                    let host = NSHostingView(rootView: view)
                    let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 520, height: 380),
                        styleMask: [.borderless], backing: .buffered, defer: false)
                    window.isReleasedWhenClosed = false
                    window.contentView = host
                    window.appearance = NSAppearance(named: scheme == .dark ? .darkAqua : .aqua)
                    host.frame = NSRect(x: 0, y: 0, width: 520, height: 380)
                    host.layoutSubtreeIfNeeded()
                    let bitmap = try XCTUnwrap(host.bitmapImageRepForCachingDisplay(in: host.bounds))
                    host.cacheDisplay(in: host.bounds, to: bitmap)
                    png = try XCTUnwrap(bitmap.representation(using: .png, properties: [:]))
                    func findScrollView(_ view: NSView) -> NSScrollView? {
                        if let scroll = view as? NSScrollView { return scroll }
                        return view.subviews.lazy.compactMap { findScrollView($0) }.first
                    }
                    let scroll = try XCTUnwrap(findScrollView(host))
                    let document = try XCTUnwrap(scroll.documentView)
                    XCTAssertGreaterThan(document.bounds.height, scroll.contentView.bounds.height)
                    scroll.contentView.scroll(to: NSPoint(x: 0, y: document.isFlipped ? document.bounds.height - scroll.contentView.bounds.height : 0))
                    scroll.reflectScrolledClipView(scroll.contentView)
                    host.layoutSubtreeIfNeeded()
                    let bottom = try XCTUnwrap(host.bitmapImageRepForCachingDisplay(in: host.bounds))
                    host.cacheDisplay(in: host.bounds, to: bottom)
                    let bottomPNG = try XCTUnwrap(bottom.representation(using: .png, properties: [:]))
                    try bottomPNG.write(to: URL(fileURLWithPath: directory).appendingPathComponent("compact-bottom-\(scheme == .dark ? "dark" : "light").png"))
                    window.close()
                } else {
                    let renderer = ImageRenderer(content: view)
                    renderer.scale = 2
                    let image = try XCTUnwrap(renderer.cgImage)
                    XCTAssertGreaterThan(image.height, 200)
                    XCTAssertLessThanOrEqual(image.height, 1400)
                    png = try XCTUnwrap(NSBitmapImageRep(cgImage: image).representation(using: .png, properties: [:]))
                }
                try png.write(to: URL(fileURLWithPath: directory).appendingPathComponent("\(name)-\(scheme == .dark ? "dark" : "light").png"))
            }
        }
    }

    func testDetectorAssistedPreparingDoesNotStartRecordingAutomatically() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 1_783_440_000) },
            idFactory: { "meeting-detection-session" },
            policySnapshotProvider: { "policy-meeting-detection" }
        )

        let session = try controller.beginDetectorAssistedPreparing(
            targetID: "yandex_telemost",
            bundleID: "ru.yandex.desktop.telemost",
            displayName: "Yandex Telemost",
            startReason: .promptTimeout,
            policySnapshotRef: "sha256:" + String(repeating: "a", count: 64),
            authorizationEvidence: ["meetingDetectionPolicyVersion": "2026.08.12.1"]
        )

        XCTAssertEqual(session.state, .detecting)
        XCTAssertEqual(session.visibleIndicatorState, .ready)
        XCTAssertFalse(session.stopActionAvailable)
        XCTAssertEqual(session.triggerEvidence["trigger"], "meeting_detection")
        XCTAssertEqual(session.triggerEvidence["meetingDetectionStartReason"], "prompt_timeout")
        XCTAssertEqual(session.triggerEvidence["meetingDetectionAutoStart"], "true")
        XCTAssertEqual(session.policySnapshotRef, "sha256:" + String(repeating: "a", count: 64))
        XCTAssertEqual(session.triggerEvidence["meetingDetectionTargetId"], "yandex_telemost")
    }
}
#endif
