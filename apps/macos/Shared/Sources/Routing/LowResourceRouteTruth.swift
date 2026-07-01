public enum LowResourceRouteTruthEvaluator {
    public static func readinessState(for snapshot: RouteTruthSnapshot) -> AudioResourceState {
        if snapshot.resourceState == .fallback {
            return .fallback
        }
        if !snapshot.publication.microphoneVisible || !snapshot.publication.speakerVisible || snapshot.publication.hidden {
            return .blocked
        }
        if !snapshot.appBridgeHealth.isFresh {
            return .stale
        }
        if !snapshot.physicalDevices.isReleaseReady {
            return .blocked
        }
        if !snapshot.recordingTrigger.isSafeFor006 {
            return .blocked
        }
        if snapshot.clientActivity.hasOpenStream {
            return .active
        }
        return .ready
    }

    public static func canPromoteP1Gates(validationRun: LowResourceValidationRun) -> Bool {
        validationRun.result == .passed &&
            validationRun.startupAttempts.allSatisfy(\.isWithinAcceptedWindow) &&
            validationRun.realtimeSafety.result == .passed &&
            validationRun.routeTruthSnapshots.allSatisfy { snapshot in
                let state = readinessState(for: snapshot)
                return state != .blocked && state != .failed
            }
    }

    public static func hasMetadataOnlyRecordingBoundary(_ snapshot: RouteTruthSnapshot) -> Bool {
        snapshot.recordingTrigger.isSafeFor006
    }
}
