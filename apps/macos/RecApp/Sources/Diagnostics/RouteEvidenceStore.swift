import Foundation
import TwoBrainRecShared

public struct RouteEvidenceStore {
    private let directoryURL: URL
    private let fileManager: FileManager

    public init(directoryURL: URL, fileManager: FileManager = .default) {
        self.directoryURL = directoryURL
        self.fileManager = fileManager
    }

    @discardableResult
    public func append(_ event: RouteEvidenceEvent, fileName: String = "route-evidence.jsonl") throws -> URL {
        try fileManager.createDirectory(at: directoryURL, withIntermediateDirectories: true)
        let fileURL = directoryURL.appendingPathComponent(fileName)
        let line = try event.jsonLine()
        let data = Data(line.utf8)

        if fileManager.fileExists(atPath: fileURL.path) {
            let handle = try FileHandle(forWritingTo: fileURL)
            defer { try? handle.close() }
            try handle.seekToEnd()
            try handle.write(contentsOf: data)
        } else {
            try data.write(to: fileURL, options: [.atomic])
        }

        return fileURL
    }

    @discardableResult
    public func write(_ events: [RouteEvidenceEvent], fileName: String = "route-evidence.jsonl") throws -> URL {
        try fileManager.createDirectory(at: directoryURL, withIntermediateDirectories: true)
        let fileURL = directoryURL.appendingPathComponent(fileName)
        let payload = try events.map { try $0.jsonLine() }.joined()
        try Data(payload.utf8).write(to: fileURL, options: [.atomic])
        return fileURL
    }

    public static func releaseDecisionEvent(
        sessionId: String,
        decision: RouteReleaseDecision,
        clientActivity: ClientActivitySnapshot,
        eventId: String = UUID().uuidString
    ) -> RouteEvidenceEvent {
        RouteEvidenceEvent(
            eventId: eventId,
            sessionId: sessionId,
            family: .releaseDecision,
            name: Self.releaseDecisionEventName(decision),
            observedAt: decision.decidedAt,
            source: .routeEngine,
            routeState: decision.outcome == .released ? .released : .preserved,
            clientActivity: clientActivity,
            releaseDecision: decision
        )
    }

    private static func releaseDecisionEventName(_ decision: RouteReleaseDecision) -> String {
        switch (decision.outcome, decision.reason) {
        case (.released, .meetingClientClosed):
            return "idle_release.released_after_client_closed"
        case (.keepActive, .deniedActiveClient):
            return "idle_release.release_denied_client_active"
        case (.denied, .deniedAmbiguousEvidence), (.denied, .deniedStaleEvidence):
            return "idle_release.release_denied_unknown_state"
        case (.keepActive, _):
            return "idle_release.keep_active"
        case (.released, _):
            return "idle_release.released_after_client_closed"
        case (.denied, _):
            return "idle_release.release_denied_unknown_state"
        }
    }
}
