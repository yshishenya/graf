import Foundation

public enum LiveRouteClientActivityStatus: String, Codable, Sendable {
    case active
    case oneSided
    case naturalSilence
    case stale
    case closed
}

public struct LiveRouteClientActivityPolicy: Sendable {
    public var freshWindowMs: Int

    public init(freshWindowMs: Int = 5_000) {
        self.freshWindowMs = freshWindowMs
    }

    public func status(for snapshot: ClientActivitySnapshot) -> LiveRouteClientActivityStatus {
        guard snapshot.freshnessMs >= 0 && snapshot.freshnessMs <= freshWindowMs else {
            return .stale
        }

        let microphoneStillVirtual = snapshot.stillUsesVirtualMicrophone != false
        let speakerStillVirtual = snapshot.stillUsesVirtualSpeaker != false
        guard microphoneStillVirtual || speakerStillVirtual else {
            return .closed
        }

        let microphoneActive = snapshot.microphoneOpen || snapshot.microphoneRunning
        let speakerActive = snapshot.speakerOpen || snapshot.speakerRunning

        if microphoneActive && speakerActive {
            return .active
        }

        if microphoneActive || speakerActive {
            return .oneSided
        }

        return snapshot.naturalSilenceAllowed ? .naturalSilence : .closed
    }

    public func shouldPreserveRoute(for snapshot: ClientActivitySnapshot) -> Bool {
        switch status(for: snapshot) {
        case .active, .oneSided, .naturalSilence:
            return true
        case .stale, .closed:
            return false
        }
    }
}
