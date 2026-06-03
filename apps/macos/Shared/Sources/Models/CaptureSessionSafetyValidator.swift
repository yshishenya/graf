public enum CaptureSessionSafetyValidator {
    public static func validate(_ session: CaptureSession) -> Bool {
        if requiresVisibleStop(session.state) {
            return [.ready, .active, .paused, .degraded].contains(session.visibleIndicatorState) &&
                session.stopActionAvailable
        }

        return true
    }

    private static func requiresVisibleStop(_ state: CaptureSessionState) -> Bool {
        switch state {
        case .starting, .active, .paused, .degraded, .stopping:
            return true
        case .idle, .detecting, .ready, .stopped, .failed, .finalized:
            return false
        }
    }
}
