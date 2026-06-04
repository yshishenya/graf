import Foundation

public struct RouteEvidenceEvent: Codable, Equatable, Sendable {
    public let eventId: String
    public let sessionId: String
    public let family: RouteEvidenceFamily
    public let name: String
    public let observedAt: Date
    public let source: RouteObservationSource
    public let routeState: LiveRouteState?
    public let target: MeetingTarget?
    public let clientActivity: ClientActivitySnapshot?
    public let defaultRoute: MacOSDefaultRouteSnapshot?
    public let frameContinuity: FrameContinuitySnapshot?
    public let autorepairAttempt: AutorepairAttempt?
    public let releaseDecision: RouteReleaseDecision?
    public let recordingTimeline: RecordingTimelineIntegrityEvidence?
    public let validationRun: ValidationRunEvidence?
    public let userActionKind: UserActionKind?
    public let redactionState: DiagnosticRedactionStatus

    public init(eventId: String, sessionId: String, family: RouteEvidenceFamily, name: String, observedAt: Date, source: RouteObservationSource, routeState: LiveRouteState? = nil, target: MeetingTarget? = nil, clientActivity: ClientActivitySnapshot? = nil, defaultRoute: MacOSDefaultRouteSnapshot? = nil, frameContinuity: FrameContinuitySnapshot? = nil, autorepairAttempt: AutorepairAttempt? = nil, releaseDecision: RouteReleaseDecision? = nil, recordingTimeline: RecordingTimelineIntegrityEvidence? = nil, validationRun: ValidationRunEvidence? = nil, userActionKind: UserActionKind? = nil, redactionState: DiagnosticRedactionStatus = .redacted) {
        self.eventId = eventId
        self.sessionId = sessionId
        self.family = family
        self.name = name
        self.observedAt = observedAt
        self.source = source
        self.routeState = routeState
        self.target = target
        self.clientActivity = clientActivity
        self.defaultRoute = defaultRoute
        self.frameContinuity = frameContinuity
        self.autorepairAttempt = autorepairAttempt
        self.releaseDecision = releaseDecision
        self.recordingTimeline = recordingTimeline
        self.validationRun = validationRun
        self.userActionKind = userActionKind
        self.redactionState = redactionState
    }

    public static func makeEncoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys]
        return encoder
    }

    public func jsonData(encoder: JSONEncoder = RouteEvidenceEvent.makeEncoder()) throws -> Data {
        try encoder.encode(self)
    }

    public func jsonLine(encoder: JSONEncoder = RouteEvidenceEvent.makeEncoder()) throws -> String {
        let data = try jsonData(encoder: encoder)
        guard let line = String(data: data, encoding: .utf8) else {
            throw RouteEvidenceSerializationError.invalidUTF8
        }
        return line + "\n"
    }
}

public enum RouteEvidenceSerializationError: Error, Equatable {
    case invalidUTF8
}
