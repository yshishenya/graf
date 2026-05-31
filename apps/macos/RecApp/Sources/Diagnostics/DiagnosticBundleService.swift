import CryptoKit
import Foundation
import TwoBrainRecShared

public struct DiagnosticBundleInput: Sendable {
    public let schemaVersion: String
    public let createdAt: Date
    public let manifest: [String: DiagnosticFieldValue]

    public init(
        schemaVersion: String,
        createdAt: Date,
        manifest: [String: DiagnosticFieldValue]
    ) {
        self.schemaVersion = schemaVersion
        self.createdAt = createdAt
        self.manifest = manifest
    }
}

public struct DiagnosticBundle: Sendable {
    public let schemaVersion: String
    public let createdAt: Date
    public let redactionState: DiagnosticRedactionStatus
    public let contentHash: String
    public let manifest: [String: DiagnosticFieldValue]
    public let removedFields: [String]
}

public struct DiagnosticBundleService: Sendable {
    private let redactor: DiagnosticRedactor
    private static let defaultFailureFamily = "general"

    public init(redactor: DiagnosticRedactor = DiagnosticRedactor()) {
        self.redactor = redactor
    }

    public func buildFailureBundle(
        failureFamily: String,
        failureReason: String? = nil,
        relatedSessionId: String? = nil,
        manifestOverrides: [String: DiagnosticFieldValue] = [:]
    ) throws -> DiagnosticBundle {
        var manifest = manifestOverrides
        manifest["failureFamily"] = .string(failureFamily)
        manifest["failureReason"] = .string(failureReason ?? "unknown")

        if let relatedSessionId {
            manifest["sessionId"] = .string(relatedSessionId)
        }

        return try buildBundle(
            DiagnosticBundleInput(
                schemaVersion: "1",
                createdAt: Date(),
                manifest: manifest
            )
        )
    }

    public func buildTrackEvidenceBundle(
        sessionId: String,
        tracks: [AudioTrack],
        streamHealth: [StreamHealthEvidence] = []
    ) throws -> DiagnosticBundle {
        var manifest: [String: DiagnosticFieldValue] = [
            "sessionId": .string(sessionId),
            "trackCount": .int(tracks.count),
            "trackRoles": .array(tracks.map { .string($0.role.rawValue) }),
            "trackStates": .array(tracks.map { .string($0.state.rawValue) }),
            "hardFailureCount": .int(streamHealth.filter(\.hardFailure).count)
        ]

        let emptyBuffers = streamHealth.reduce(UInt64(0)) { $0 + $1.emptyBufferCount }
        let droppedFrames = streamHealth.reduce(UInt64(0)) { $0 + $1.droppedFrameCount }
        manifest["emptyBufferCount"] = .int(Int(emptyBuffers))
        manifest["droppedFrameCount"] = .int(Int(droppedFrames))

        return try buildBundle(
            schemaVersion: "1",
            manifest: manifest,
            failureFamily: "track_evidence"
        )
    }

    public func buildLiveRouteReadinessBundle(
        result: LiveRouteReadinessResult
    ) throws -> DiagnosticBundle {
        var manifest: [String: DiagnosticFieldValue] = [
            "liveRouteReadiness": .object([
                "status": .string(result.status.rawValue),
                "checkedAt": .string(Self.formatDate(result.checkedAt)),
                "recoveryAction": .string(result.recoveryAction ?? "none")
            ]),
            "microphonePathEvidence": .object([
                "selectedPhysicalDeviceName": .string(result.microphoneEvidence.selectedPhysicalDeviceName),
                "status": .string(result.microphoneEvidence.status.rawValue),
                "validFrameCount": .int(Int(result.microphoneEvidence.validFrameCount)),
                "emptyBufferCount": .int(Int(result.microphoneEvidence.emptyBufferCount)),
                "selfRoutingRejected": .bool(result.microphoneEvidence.selfRoutingRejected),
                "failureReason": .string(result.microphoneEvidence.failureReason ?? "none")
            ]),
            "speakerPathEvidence": .object([
                "selectedPhysicalOutputName": .string(result.speakerEvidence.selectedPhysicalOutputName),
                "status": .string(result.speakerEvidence.status.rawValue),
                "stimulusObserved": .bool(result.speakerEvidence.stimulusObserved),
                "validFrameCount": .int(Int(result.speakerEvidence.validFrameCount)),
                "emptyBufferCount": .int(Int(result.speakerEvidence.emptyBufferCount)),
                "selfRoutingRejected": .bool(result.speakerEvidence.selfRoutingRejected),
                "failureReason": .string(result.speakerEvidence.failureReason ?? "none")
            ]),
            "routeStatus": .string(result.status.rawValue),
            "recoveryActionId": .string(result.recoveryAction ?? "none")
        ]

        if let latency = result.latencyMeasurement {
            manifest["latencyMeasurement"] = .object([
                "routeClass": .string(latency.routeClass.rawValue),
                "addedLatencyMs": .double(latency.addedLatencyMs),
                "thresholdMs": .double(latency.thresholdMs),
                "status": .string(latency.status.rawValue)
            ])
        }

        if let leakage = result.leakageMeasurement {
            manifest["leakageMeasurement"] = .object([
                "speakerReferenceDb": .double(leakage.speakerReferenceDb),
                "virtualMicLeakageDb": .double(leakage.virtualMicLeakageDb),
                "relativeLeakageDb": .double(leakage.relativeLeakageDb),
                "intelligibilityStatus": .string(leakage.intelligibilityStatus.rawValue),
                "status": .string(leakage.status.rawValue)
            ])
        }

        return try buildBundle(
            schemaVersion: "1",
            manifest: manifest,
            failureFamily: "live_route_readiness"
        )
    }

    public func buildBrowserTargetEvidenceBundle(
        evidence: [BrowserTargetEvidence]
    ) throws -> DiagnosticBundle {
        let values = evidence.map { item in
            DiagnosticFieldValue.object([
                "target": .string(item.target),
                "status": .string(item.status.rawValue),
                "microphoneSelected": .string(item.microphoneSelected),
                "speakerSelected": .string(item.speakerSelected),
                "localSpeechUsable": .bool(item.localSpeechUsable),
                "remoteAudioUsable": .bool(item.remoteAudioUsable),
                "failureReason": .string(item.failureReason ?? "none"),
                "checkedAt": .string(Self.formatDate(item.checkedAt))
            ])
        }

        return try buildBundle(
            schemaVersion: "1",
            manifest: [
                "browserTargetEvidence": .array(values),
                "routeStatus": .string("browser_target_evidence_recorded")
            ],
            failureFamily: "browser_target_evidence"
        )
    }

    public func buildRouteInvalidationBundle(
        events: [RouteInvalidationEvent]
    ) throws -> DiagnosticBundle {
        let values = events.map { event in
            DiagnosticFieldValue.object([
                "source": .string(event.source.rawValue),
                "previousReadinessStatus": .string(event.previousReadinessStatus.rawValue),
                "newReadinessStatus": .string(event.newReadinessStatus.rawValue),
                "detectedAt": .string(Self.formatDate(event.detectedAt)),
                "recoveryAction": .string(event.recoveryAction)
            ])
        }

        return try buildBundle(
            schemaVersion: "1",
            manifest: [
                "routeInvalidationEvents": .array(values),
                "recoveryActionId": .string("rerun_readiness_check")
            ],
            failureFamily: "route_invalidation"
        )
    }

    public func buildLivePassthroughBundle(
        session: LivePassthroughSession,
        recoveryEvents: [PassthroughRouteRecoveryEvent] = []
    ) throws -> DiagnosticBundle {
        let browserValues = session.browserEvidence.map { item in
            DiagnosticFieldValue.object([
                "targetName": .string(item.targetName),
                "targetVersion": .string(item.targetVersion ?? "unknown"),
                "selectedMicrophone": .string(item.selectedMicrophone),
                "selectedSpeaker": .string(item.selectedSpeaker),
                "localSpeechUsable": .bool(item.localSpeechUsable),
                "remoteAudioUsable": .bool(item.remoteAudioUsable),
                "status": .string(item.status.rawValue),
                "failureReason": .string(item.failureReason ?? "none"),
                "checkedAt": .string(Self.formatDate(item.checkedAt))
            ])
        }

        let recoveryValues = recoveryEvents.map { event in
            DiagnosticFieldValue.object([
                "eventType": .string(event.eventType.rawValue),
                "detectedAt": .string(Self.formatDate(event.detectedAt)),
                "previousStatus": .string(event.previousStatus.rawValue),
                "newStatus": .string(event.newStatus.rawValue),
                "recoveryAction": .string(event.recoveryAction)
            ])
        }

        return try buildBundle(
            schemaVersion: "1",
            manifest: [
                "livePassthrough": .object([
                    "sessionId": .string(session.sessionId),
                    "status": .string(session.status.rawValue),
                    "recordingState": .string(session.recordingState),
                    "startedAt": .string(session.startedAt.map(Self.formatDate) ?? "none"),
                    "endedAt": .string(session.endedAt.map(Self.formatDate) ?? "none"),
                    "lastRecoveryAction": .string(session.lastRecoveryAction ?? "none")
                ]),
                "microphonePassthroughPath": .object([
                    "physicalInputName": .string(session.microphonePath.physicalInputName),
                    "virtualInputName": .string(session.microphonePath.virtualInputName),
                    "status": .string(session.microphonePath.status.rawValue),
                    "validFrameObserved": .bool(session.microphonePath.validFrameObserved),
                    "failureReason": .string(session.microphonePath.failureReason.rawValue)
                ]),
                "speakerPassthroughPath": .object([
                    "virtualOutputName": .string(session.speakerPath.virtualOutputName),
                    "physicalOutputName": .string(session.speakerPath.physicalOutputName),
                    "status": .string(session.speakerPath.status.rawValue),
                    "stimulusObserved": .bool(session.speakerPath.stimulusObserved),
                    "failureReason": .string(session.speakerPath.failureReason.rawValue)
                ]),
                "passthroughHealth": .object([
                    "appHeartbeatStatus": .string(session.healthEvidence.appHeartbeatStatus.rawValue),
                    "latencyMs": .double(session.healthEvidence.latencyMs ?? -1),
                    "leakageDbBelowReference": .double(session.healthEvidence.leakageDbBelowReference ?? -1),
                    "notIntelligible": .bool(session.healthEvidence.notIntelligible),
                    "diagnosticSafe": .bool(session.healthEvidence.diagnosticSafe)
                ]),
                "passthroughBrowserEvidence": .array(browserValues),
                "passthroughRecoveryEvents": .array(recoveryValues),
                "appHeartbeatStatus": .string(session.healthEvidence.appHeartbeatStatus.rawValue),
                "routeStatus": .string(session.status.rawValue),
                "recoveryActionId": .string(session.lastRecoveryAction ?? "none")
            ],
            failureFamily: "live_passthrough"
        )
    }

    public func buildBundle(
        schemaVersion: String,
        createdAt: Date = Date(),
        manifest: [String: DiagnosticFieldValue],
        failureFamily: String? = nil
    ) throws -> DiagnosticBundle {
        var inputManifest = manifest
        inputManifest["schemaVersion"] = .string(schemaVersion)
        inputManifest["createdAt"] = .string(Self.formatDate(createdAt))
        inputManifest["failureFamily"] = .string(failureFamily ?? Self.defaultFailureFamily)

        return try buildBundle(
            DiagnosticBundleInput(
                schemaVersion: schemaVersion,
                createdAt: createdAt,
                manifest: inputManifest
            )
        )
    }

    public func buildBundle(_ input: DiagnosticBundleInput) throws -> DiagnosticBundle {
        var manifest = input.manifest
        manifest["schemaVersion"] = .string(input.schemaVersion)
        manifest["createdAt"] = .string(Self.formatDate(input.createdAt))

        let redaction = redactor.redact(manifest)
        var finalizedManifest = redaction.manifest
        finalizedManifest["redactionState"] = .string(redaction.status.rawValue)
        finalizedManifest["contentHash"] = .string(try contentHash(for: finalizedManifest))

        return DiagnosticBundle(
            schemaVersion: input.schemaVersion,
            createdAt: input.createdAt,
            redactionState: redaction.status,
            contentHash: finalizedManifest.stringValue(forKey: "contentHash") ?? "",
            manifest: finalizedManifest,
            removedFields: redaction.removedFields
        )
    }

    private func contentHash(for manifest: [String: DiagnosticFieldValue]) throws -> String {
        let jsonObject = manifest.mapValues { $0.jsonCompatibleValue }
        let data = try JSONSerialization.data(
            withJSONObject: jsonObject,
            options: [.sortedKeys, .withoutEscapingSlashes]
        )
        let digest = SHA256.hash(data: data)
        return digest.map { String(format: "%02x", $0) }.joined()
    }

    static func formatDate(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: date)
    }
}

private extension DiagnosticFieldValue {
    var jsonCompatibleValue: Any {
        switch self {
        case .string(let value):
            return value
        case .int(let value):
            return value
        case .double(let value):
            return value
        case .bool(let value):
            return value
        case .object(let object):
            return object.mapValues { $0.jsonCompatibleValue }
        case .array(let values):
            return values.map { $0.jsonCompatibleValue }
        case .null:
            return NSNull()
        }
    }
}

private extension Dictionary where Key == String, Value == DiagnosticFieldValue {
    func stringValue(forKey key: String) -> String? {
        guard case .string(let value) = self[key] else {
            return nil
        }
        return value
    }
}
