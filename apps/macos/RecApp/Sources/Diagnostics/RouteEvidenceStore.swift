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
        eventId: String = UUID().uuidString
    ) -> RouteEvidenceEvent {
        RouteEvidenceEvent(
            eventId: eventId,
            sessionId: sessionId,
            family: .releaseDecision,
            name: "release_decision.\(decision.outcome.rawValue)",
            observedAt: decision.decidedAt,
            source: .routeEngine,
            routeState: decision.outcome == .released ? .released : .preserved,
            releaseDecision: decision
        )
    }
}
