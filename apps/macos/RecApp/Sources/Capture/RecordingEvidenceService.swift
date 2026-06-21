import Foundation
import TwoBrainRecShared

public struct RecordingEvidenceService: Sendable {
    public typealias Clock = @Sendable () -> Date
    public typealias IdFactory = @Sendable () -> String

    private let clock: Clock
    private let idFactory: IdFactory

    public init(
        clock: @escaping Clock = Date.init,
        idFactory: @escaping IdFactory = { UUID().uuidString }
    ) {
        self.clock = clock
        self.idFactory = idFactory
    }

    public func event(
        for session: CaptureSession,
        type: RecordingEvidenceEventType,
        initiator: RecordingEvidenceInitiator,
        routeState: LivePassthroughStatus,
        blockedReason: RecordingStartBlocker = .none,
        recoveryAction: String? = nil
    ) -> RecordingEvidenceEvent {
        RecordingEvidenceEvent(
            eventId: idFactory(),
            sessionId: session.id,
            eventType: type,
            occurredAt: clock(),
            initiator: initiator,
            routeState: routeState,
            indicatorState: session.visibleIndicatorState,
            stopActionAvailable: session.stopActionAvailable,
            blockedReason: blockedReason,
            recoveryAction: recoveryAction,
            durationMs: durationMs(for: session),
            diagnosticSafe: true
        )
    }

    public func startBlocked(
        session: CaptureSession,
        prerequisite: RecordingPrerequisiteSnapshot
    ) -> RecordingEvidenceEvent {
        event(
            for: session,
            type: .startBlocked,
            initiator: .user,
            routeState: prerequisite.routeState,
            blockedReason: prerequisite.blockedReason,
            recoveryAction: prerequisite.recoveryAction
        )
    }

    public func localRecordingEvidence(for manifest: LocalRecordingManifest) -> [String: String] {
        let graphSafetyValues = [
            manifest.microphoneSelection?.diagnosticSafe,
            manifest.microphoneStream?.diagnosticSafe,
            manifest.microphoneStreamHealth?.diagnosticSafe
        ].compactMap { $0 }
        let graphDiagnosticSafe = graphSafetyValues.isEmpty ? "" : String(graphSafetyValues.allSatisfy { $0 })

        return [
            "sessionId": manifest.sessionId,
            "status": manifest.status.rawValue,
            "transcriptionReadiness": manifest.transcriptionReadiness.rawValue,
            "mediaScribeSourceMode": manifest.mediaScribeSourceMode,
            "directoryId": manifest.directoryId,
            "manifestFileName": manifest.manifestFileName,
            "failureReason": manifest.failureReason.rawValue,
            "durationDifferenceSeconds": String(format: "%.3f", manifest.durationDifferenceSeconds),
            "trackRoles": manifest.tracks.map(\.role.rawValue).joined(separator: ","),
            "trackSourceKinds": manifest.tracks.map { $0.sourceKind?.rawValue ?? "unknown" }.joined(separator: ","),
            "mediaScribeFields": manifest.tracks.map(\.mediaScribeField.rawValue).joined(separator: ","),
            "trackStates": manifest.tracks.map(\.status.rawValue).joined(separator: ","),
            "trackFormats": manifest.tracks.map(\.format).joined(separator: ","),
            "externalEgressStarted": String(manifest.externalEgressStarted),
            "transcriptionStarted": String(manifest.transcriptionStarted),
            "diagnosticSafe": String(manifest.diagnosticSafe),
            "scopeApprovalId": manifest.scopeApproval?.scopeApprovalId ?? "",
            "microphonePermissionState": manifest.permissions?.microphone.rawValue ?? "",
            "systemAudioPermissionState": manifest.permissions?.systemAudio.rawValue ?? "",
            "captureHealthGateStatus": manifest.captureHealth?.gateStatus.rawValue ?? "",
            "captureHealthFailureReason": manifest.captureHealth?.failureReason.rawValue ?? "",
            "recordingMicrophoneSelectionMode": manifest.microphoneSelection?.mode.rawValue ?? "",
            "recordingMicrophoneSelectionResult": manifest.microphoneSelection?.selectionResult.rawValue ?? "",
            "recordingMicrophoneRejectionReason": manifest.microphoneSelection?.rejectionReason?.rawValue ?? "",
            "recordingMicrophoneInputDisplayName": manifest.microphoneSelection?.inputDisplayName ?? "",
            "recordingMicrophoneDeviceClass": manifest.microphoneSelection?.deviceClass?.rawValue ?? "",
            "recordingMicrophoneWorkingDeviceKind": manifest.microphoneSelection?.workingDeviceKind?.rawValue ?? "",
            "microphoneStreamKind": manifest.microphoneStream?.streamKind.rawValue ?? "",
            "microphoneStreamPermissionState": manifest.microphoneStream?.permissionState.rawValue ?? "",
            "microphoneStreamFailureReason": manifest.microphoneStream?.failureReason.rawValue ?? "",
            "microphoneStreamFramesObserved": manifest.microphoneStreamHealth.map { String($0.framesObserved) } ?? "",
            "microphoneStreamGateStatus": manifest.microphoneStreamHealth?.gateStatus.rawValue ?? "",
            "microphoneStreamTimingConfidence": manifest.microphoneStreamHealth?.timingConfidence.rawValue ?? "",
            "microphoneStreamSilenceStatus": manifest.microphoneStreamHealth?.silenceStatus.rawValue ?? "",
            "microphoneFutureProcessingReadiness": manifest.microphoneStreamHealth?.cleanupReadiness.rawValue ?? "",
            "microphoneGraphDiagnosticSafe": graphDiagnosticSafe,
            "routeSessionId": manifest.recordingTimelineEvidence?.routeSessionId ?? "",
            "alignmentBand": manifest.recordingTimelineEvidence?.alignmentBand.rawValue ?? "",
            "routeInterruptionCategory": manifest.recordingTimelineEvidence?.interruptionCategory.rawValue ?? ""
        ]
    }

    private func durationMs(for session: CaptureSession) -> Int? {
        guard let startedAt = session.startedAt else {
            return nil
        }
        let end = session.stoppedAt ?? clock()
        return max(0, Int(end.timeIntervalSince(startedAt) * 1000))
    }
}
