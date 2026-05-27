public enum CaptureSessionSafetyValidator {
    public static func validate(_ session: CaptureSession) -> Bool {
        if requiresVisibleStop(session.state) {
            return session.visibleIndicatorState != .hidden &&
                session.stopActionAvailable
        }

        return true
    }

    private static func requiresVisibleStop(_ state: CaptureSessionState) -> Bool {
        switch state {
        case .active, .paused, .degraded, .stopping:
            return true
        case .idle, .detecting, .ready, .starting, .stopped, .failed, .finalized:
            return false
        }
    }
}
