import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RecordingEvidenceTests: XCTestCase {
    func testRecordingEvidenceEventIsMetadataOnlyAndDiagnosticSafe() {
        let service = RecordingEvidenceService(
            clock: { Date(timeIntervalSince1970: 1_777_777_777) },
            idFactory: { "event-1" }
        )
        let session = makeSession(state: .active, indicator: .active, stopAvailable: true)

        let event = service.event(
            for: session,
            type: .started,
            initiator: .user,
            routeState: .active
        )

        XCTAssertEqual(event.eventId, "event-1")
        XCTAssertEqual(event.sessionId, session.id)
        XCTAssertEqual(event.eventType, .started)
        XCTAssertEqual(event.indicatorState, .active)
        XCTAssertTrue(event.stopActionAvailable)
        XCTAssertTrue(event.diagnosticSafe)
    }

    func testBlockedStartEvidenceKeepsReasonAndRecoveryAction() {
        let service = RecordingEvidenceService(
            clock: { Date(timeIntervalSince1970: 1_777_777_777) },
            idFactory: { "blocked-event" }
        )
        let session = makeSession(state: .failed, indicator: .error, stopAvailable: false)
        let prerequisite = RecordingPrerequisiteSnapshot(
            routeState: .inactive,
            routeEvidenceKind: .publicationOnly,
            policyAllowsRecording: true,
            microphonePermissionGranted: true,
            storageRisk: .healthy,
            indicatorAvailable: true,
            sourceAppEligibility: .eligible,
            blockedReason: .publicationOnly,
            recoveryAction: "Run route readiness before recording",
            evaluatedAt: Date(timeIntervalSince1970: 1_777_777_777)
        )

        let event = service.startBlocked(session: session, prerequisite: prerequisite)

        XCTAssertEqual(event.eventType, .startBlocked)
        XCTAssertEqual(event.blockedReason, .publicationOnly)
        XCTAssertEqual(event.recoveryAction, "Run route readiness before recording")
    }

    func testRecordingEvidenceDiagnosticBundleRemovesForbiddenContent() throws {
        let event = RecordingEvidenceEvent(
            eventId: "event",
            sessionId: "session",
            eventType: .started,
            occurredAt: Date(timeIntervalSince1970: 1_777_777_777),
            initiator: .user,
            routeState: .active,
            indicatorState: .active,
            stopActionAvailable: true
        )

        let bundle = try DiagnosticBundleService().buildRecordingEvidenceBundle(
            events: [event],
            manifestOverrides: [
                "rawAudio": .string("not allowed"),
                "meetingContent": .string("not allowed")
            ]
        )

        XCTAssertNotNil(bundle.manifest["recordingEvidence"])
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["meetingContent"])
        XCTAssertEqual(bundle.redactionState, .blockedSensitiveContent)
    }

    private func makeSession(
        state: CaptureSessionState,
        indicator: VisibleIndicatorState,
        stopAvailable: Bool
    ) -> CaptureSession {
        CaptureSession(
            id: "recording-evidence-session",
            mode: .audioRecording,
            state: state,
            sourceAppEligibility: .eligible,
            policySnapshotRef: "policy",
            triggerEvidence: [:],
            visibleIndicatorState: indicator,
            stopActionAvailable: stopAvailable,
            bufferSummaryId: nil,
            startedAt: Date(timeIntervalSince1970: 1_777_777_700),
            stoppedAt: Date(timeIntervalSince1970: 1_777_777_777)
        )
    }
}
#endif
