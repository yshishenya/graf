import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DesktopCabinetWorkspaceTests: XCTestCase {
    func testDefaultWorkspaceOpensMeetingsList() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))

        XCTAssertEqual(DesktopCabinetWorkspace.defaultRoute(configuration: configuration).absoluteString, "https://rec.2brain.dev/desktop/meetings")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.workspace, "desktop-cabinet-workspace")
        XCTAssertFalse(DesktopCabinetWorkspace.defaultRoute(configuration: configuration).path.localizedCaseInsensitiveContains("diagnostic"))
        XCTAssertFalse(DesktopCabinetWorkspace.defaultRoute(configuration: configuration).path.localizedCaseInsensitiveContains("settings"))
    }

    func testWorkspaceOpensMeetingDetailDestination() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))

        XCTAssertEqual(
            DesktopCabinetWorkspace.detailRoute(meetingId: "meeting-033", configuration: configuration).absoluteString,
            "https://rec.2brain.dev/desktop/meetings/meeting-033"
        )
    }

    func testShellInvariantKeepsStopReachableDuringActiveRecordingForEveryCabinetState() {
        for state in DesktopCabinetState.allCases {
            let invariant = NativeShellInvariant(
                recordVisible: true,
                stopVisible: true,
                uploadTruthVisible: true,
                focusCanReachStop: true,
                embeddedSurfaceLoaded: state == .ready
            )

            XCTAssertTrue(invariant.satisfiesActiveRecordingSafety(cabinetState: state), "\(state)")
        }
    }

    func testActiveRecordingInvariantFailsWhenStopIsHiddenOrFocusTrapped() {
        let hiddenRecord = NativeShellInvariant(
            recordVisible: false,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: true
        )
        let hiddenStop = NativeShellInvariant(
            recordVisible: true,
            stopVisible: false,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: true
        )
        let focusTrap = NativeShellInvariant(
            recordVisible: true,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: false,
            embeddedSurfaceLoaded: true
        )

        XCTAssertFalse(hiddenRecord.satisfiesActiveRecordingSafety(cabinetState: .ready))
        XCTAssertFalse(hiddenStop.satisfiesActiveRecordingSafety(cabinetState: .ready))
        XCTAssertFalse(focusTrap.satisfiesActiveRecordingSafety(cabinetState: .ready))
    }

    func testNativeAndEmbeddedRegionsHaveStableAccessibilityBoundaries() {
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.captureRegion, "desktop-native-capture-region")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.uploadTruthRegion, "desktop-native-upload-truth-region")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.nativeShellRegion, "desktop-native-shell-region")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.embeddedSurface, "desktop-cabinet-embedded-surface")
    }

    func testUnavailableStatesHaveBoundedMessages() {
        let states: [DesktopCabinetState] = [.notConfigured, .offline, .timeout, .expiredSession, .accessDenied, .notFound, .malformedResponse, .blockedRoute]

        for state in states {
            XCTAssertFalse(state.userMessage.isEmpty, "\(state)")
            XCTAssertLessThanOrEqual(state.userMessage.count, 180, "\(state)")
            XCTAssertFalse(state.userMessage.contains("/Users/"), "\(state)")
        }
    }

    func testDeniedAndNotFoundStatesDoNotConfirmMeetingExistence() {
        for state in [DesktopCabinetState.accessDenied, .notFound] {
            XCTAssertFalse(state.userMessage.localizedCaseInsensitiveContains("this meeting"), "\(state)")
            XCTAssertFalse(state.userMessage.localizedCaseInsensitiveContains("meeting exists"), "\(state)")
            XCTAssertTrue(state.userMessage.localizedCaseInsensitiveContains("не удалось подтвердить"), "\(state)")
        }
    }
}
#endif
