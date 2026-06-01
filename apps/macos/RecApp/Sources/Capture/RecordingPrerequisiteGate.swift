import Foundation
import TwoBrainRecShared

public struct RecordingPrerequisiteGate: Sendable {
    public init() {}

    public func evaluate(_ snapshot: RecordingPrerequisiteSnapshot) -> RecordingPrerequisiteSnapshot {
        var updated = snapshot

        if snapshot.sourceAppEligibility == .policyBlocked {
            return blocked(snapshot, reason: .policyDisabled, action: "Review workspace recording policy")
        }
        if snapshot.sourceAppEligibility != .eligible {
            return blocked(snapshot, reason: .sourceAppIneligible, action: "Use an approved meeting target")
        }
        if !snapshot.policyAllowsRecording {
            return blocked(snapshot, reason: .policyDisabled, action: "Enable recording policy before starting")
        }
        if !snapshot.microphonePermissionGranted {
            return blocked(snapshot, reason: .permissionDenied, action: "Grant microphone permission in System Settings")
        }
        if snapshot.storageRisk != .healthy {
            return blocked(snapshot, reason: .storageUnsafe, action: "Free local storage or reduce retention before recording")
        }
        if !snapshot.indicatorAvailable {
            return blocked(snapshot, reason: .indicatorUnavailable, action: "Restore visible capture indicator before recording")
        }
        if snapshot.routeEvidenceKind == .publicationOnly {
            return blocked(snapshot, reason: .publicationOnly, action: "Run route readiness before recording")
        }
        if snapshot.routeEvidenceKind == .stale || snapshot.routeState == .stale {
            return blocked(snapshot, reason: .routeNotReady, action: "Recheck audio route before recording")
        }
        if snapshot.routeEvidenceKind == .unknown {
            return blocked(snapshot, reason: .routeNotReady, action: "Confirm audio route evidence before recording")
        }
        if ![LivePassthroughStatus.ready, .active].contains(snapshot.routeState) {
            return blocked(snapshot, reason: .routeNotReady, action: "Wait for audio route to become ready")
        }

        updated.blockedReason = .none
        updated.recoveryAction = nil
        return updated
    }

    public func canStartRecording(_ snapshot: RecordingPrerequisiteSnapshot) -> Bool {
        evaluate(snapshot).allowsRecording
    }

    private func blocked(
        _ snapshot: RecordingPrerequisiteSnapshot,
        reason: RecordingStartBlocker,
        action: String
    ) -> RecordingPrerequisiteSnapshot {
        var updated = snapshot
        updated.blockedReason = reason
        updated.recoveryAction = action
        return updated
    }
}
