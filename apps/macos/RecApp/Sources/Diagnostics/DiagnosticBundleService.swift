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
            "routeVerificationResults": .object([
                "microphoneStatus": .string(result.microphoneEvidence.status.rawValue),
                "microphoneFailureReason": .string(result.microphoneEvidence.failureReason ?? "none"),
                "speakerStatus": .string(result.speakerEvidence.status.rawValue),
                "speakerFailureReason": .string(result.speakerEvidence.failureReason ?? "none")
            ]),
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

    public func buildRecordingEvidenceBundle(
        events: [RecordingEvidenceEvent],
        prerequisites: [RecordingPrerequisiteSnapshot] = [],
        indicatorSnapshots: [CaptureIndicatorSnapshot] = [],
        manifestOverrides: [String: DiagnosticFieldValue] = [:]
    ) throws -> DiagnosticBundle {
        var manifest = manifestOverrides
        manifest["recordingEvidence"] = .array(events.map(Self.diagnosticValue))
        manifest["recordingPrerequisites"] = .array(prerequisites.map(Self.diagnosticValue))
        manifest["recordingIndicatorState"] = .array(indicatorSnapshots.map(Self.diagnosticValue))
        manifest["routeStatus"] = .string(events.last?.routeState.rawValue ?? "unknown")
        manifest["recoveryActionId"] = .string(events.last?.recoveryAction ?? "none")

        return try buildBundle(
            schemaVersion: "1",
            manifest: manifest,
            failureFamily: "recording_evidence"
        )
    }

    public func buildLocalRecordingBundle(
        manifest: LocalRecordingManifest,
        manifestOverrides: [String: DiagnosticFieldValue] = [:]
    ) throws -> DiagnosticBundle {
        var bundleManifest = manifestOverrides
        bundleManifest["localRecordingManifest"] = Self.diagnosticValue(manifest)
        bundleManifest["localRecordingTracks"] = .array(manifest.tracks.map(Self.diagnosticValue))
        bundleManifest["localRecordingEvidence"] = .object([
            "sessionId": .string(manifest.sessionId),
            "status": .string(manifest.status.rawValue),
            "directoryId": .string(manifest.directoryId),
            "manifestFileName": .string(manifest.manifestFileName),
            "diagnosticSafe": .bool(manifest.diagnosticSafe),
            "leakageStatus": .string(manifest.leakageFinalization?.status.rawValue ?? "not_measured"),
            "transcriptionGate": .string(manifest.leakageFinalization?.transcriptionGate.rawValue ?? "blocked_not_measured")
        ])
        if let leakageFinalization = manifest.leakageFinalization {
            bundleManifest["leakageFinalization"] = Self.diagnosticValue(leakageFinalization)
            bundleManifest["leakageRouteMetadata"] = Self.diagnosticValue(leakageFinalization.routeMetadata)
            bundleManifest["leakageMeasurement"] = leakageFinalization.measurement.map(Self.diagnosticValue) ?? .null
            bundleManifest["directLoopbackSuspicion"] = .bool(leakageFinalization.measurement?.directLoopbackSuspicion ?? false)
            bundleManifest["acousticLeakageSuspicion"] = .bool(leakageFinalization.measurement?.acousticLeakageSuspicion ?? false)
            bundleManifest["thresholdVersion"] = .string(leakageFinalization.thresholdVersion)
            bundleManifest["alignmentStatus"] = .string(leakageFinalization.alignmentStatus.rawValue)
            bundleManifest["transcriptionGate"] = .string(leakageFinalization.transcriptionGate.rawValue)
        }
        bundleManifest["privacySegments"] = .array((manifest.privacySegments ?? []).map(Self.diagnosticValue))
        bundleManifest["meetingMuteTruth"] = manifest.meetingMuteTruth.map(Self.diagnosticValue) ?? .null
        bundleManifest["meetingMuteTruthEvidence"] = .array((manifest.meetingMuteTruthEvidence ?? []).map(Self.diagnosticValue))
        bundleManifest["targetMuteCapability"] = manifest.targetMuteCapability.map(Self.diagnosticValue) ?? .null
        bundleManifest["limitationCopyShownAt"] = .string(manifest.limitationCopyShownAt.map(Self.formatDate) ?? "none")
        bundleManifest["sessionId"] = .string(manifest.sessionId)
        bundleManifest["trackCount"] = .int(manifest.tracks.count)
        bundleManifest["trackRoles"] = .array(manifest.tracks.map { .string($0.role.rawValue) })
        bundleManifest["trackStates"] = .array(manifest.tracks.map { .string($0.status.rawValue) })

        return try buildBundle(
            schemaVersion: "1",
            manifest: bundleManifest,
            failureFamily: "local_recording"
        )
    }

    public func buildReleaseHardeningBundle(
        run: ReleaseHardeningRun,
        shortSmokeEvidence: [ShortSmokeEvidence] = [],
        noHangEvidence: [CoreAudioNoHangEvidence] = [],
        routeRecoveryEvidence: [RouteRecoveryEvidence] = [],
        installerLifecycleEvidence: [InstallerLifecycleEvidence] = [],
        uxReadinessEvidence: [UXReadinessEvidence] = [],
        deferredRecordingAcceptance: DeferredRecordingAcceptanceState? = nil
    ) throws -> DiagnosticBundle {
        try buildBundle(
            schemaVersion: "1",
            manifest: [
                "releaseHardeningRun": .object([
                    "runId": .string(run.runId),
                    "createdAt": .string(Self.formatDate(run.createdAt)),
                    "macOSVersion": .string(run.macOSVersion),
                    "appBuild": .string(run.appBuild),
                    "driverBuild": .string(run.driverBuild),
                    "result": .string(run.result.rawValue),
                    "notes": .string(run.notes)
                ]),
                "releaseHardeningEvidenceFamilies": .array(
                    run.evidenceFamilies.map { .string($0.rawValue) }
                ),
                "shortSmokeEvidence": .array(shortSmokeEvidence.map(Self.diagnosticValue)),
                "coreAudioNoHangEvidence": .array(noHangEvidence.map(Self.diagnosticValue)),
                "routeRecoveryEvidence": .array(routeRecoveryEvidence.map(Self.diagnosticValue)),
                "installerLifecycleEvidence": .array(installerLifecycleEvidence.map(Self.diagnosticValue)),
                "uxReadinessEvidence": .array(uxReadinessEvidence.map(Self.diagnosticValue)),
                "deferredRecordingAcceptance": deferredRecordingAcceptance.map(Self.diagnosticValue) ?? .null
            ],
            failureFamily: "release_hardening"
        )
    }

    public func buildLowResourceRouteTruthBundle(
        snapshot: RouteTruthSnapshot,
        startupAttempts: [StartupAttemptEvidence] = [],
        validationRun: LowResourceValidationRun? = nil,
        recoveryEvents: [LowResourceRecoveryEvent] = []
    ) throws -> DiagnosticBundle {
        try buildBundle(
            schemaVersion: "1",
            manifest: [
                "lowResourceRouteTruth": Self.diagnosticValue(snapshot),
                "lowResourceStartupAttempts": .array(startupAttempts.map(Self.diagnosticValue)),
                "lowResourceValidationRun": validationRun.map(Self.diagnosticValue) ?? .null,
                "lowResourceRecoveryEvents": .array(recoveryEvents.map(Self.diagnosticValue)),
                "routeStatus": .string(snapshot.resourceState.rawValue),
                "recoveryActionId": .string(snapshot.appBridgeHealth.recoveryAction)
            ],
            failureFamily: "low_resource_audio"
        )
    }

    public func buildLowResourceRecoveryBundle(
        events: [LowResourceRecoveryEvent]
    ) throws -> DiagnosticBundle {
        try buildBundle(
            schemaVersion: "1",
            manifest: [
                "lowResourceRecoveryEvents": .array(events.map(Self.diagnosticValue)),
                "routeStatus": .string(events.last?.newState.rawValue ?? AudioResourceState.stale.rawValue),
                "recoveryActionId": .string(events.last?.recoveryAction ?? "none")
            ],
            failureFamily: "low_resource_recovery"
        )
    }

    public func buildLowResourcePromotionBundle(
        decision: LowResourcePromotionDecision
    ) throws -> DiagnosticBundle {
        try buildBundle(
            schemaVersion: "1",
            manifest: [
                "lowResourcePromotionDecision": Self.diagnosticValue(decision),
                "routeStatus": .string(decision.status == .promoted ? "ready" : "fallback"),
                "recoveryActionId": .string(decision.shouldUseFallback ? "use_005_fallback" : "none")
            ],
            failureFamily: "low_resource_promotion"
        )
    }

    public func buildRouteEvidenceBundle(
        events: [RouteEvidenceEvent],
        manifestOverrides: [String: DiagnosticFieldValue] = [:]
    ) throws -> DiagnosticBundle {
        var manifest = manifestOverrides
        manifest["routeEvidenceEvents"] = .array(events.map(Self.diagnosticValue))

        if let validationRun = events.compactMap(\.validationRun).last {
            manifest["validationRunEvidence"] = Self.diagnosticValue(validationRun)
        }

        if let timelineEvidence = events.compactMap(\.recordingTimeline).last {
            manifest["recordingTimelineEvidence"] = Self.diagnosticValue(timelineEvidence)
        }

        if let releaseDecision = events.compactMap(\.releaseDecision).last {
            manifest["routeReleaseDecision"] = Self.diagnosticValue(releaseDecision)
        }

        manifest["routeEvidenceFile"] = .string("route-evidence.jsonl")
        manifest["routeStatus"] = .string(events.last?.routeState?.rawValue ?? "unknown")

        return try buildBundle(
            schemaVersion: "1",
            manifest: manifest,
            failureFamily: "live_route_stability"
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

    private static func diagnosticValue(_ evidence: ShortSmokeEvidence) -> DiagnosticFieldValue {
        .object([
            "targetApp": .string(evidence.targetApp),
            "selectedInput": .string(evidence.selectedInput),
            "selectedOutput": .string(evidence.selectedOutput),
            "localSpeechObserved": boolOrUnknown(evidence.localSpeechObserved),
            "remoteAudioObserved": boolOrUnknown(evidence.remoteAudioObserved),
            "loopbackObserved": boolOrUnknown(evidence.loopbackObserved),
            "recordingStarted": .bool(evidence.recordingStarted),
            "result": .string(evidence.result.rawValue)
        ])
    }

    private static func diagnosticValue(_ evidence: CoreAudioNoHangEvidence) -> DiagnosticFieldValue {
        .object([
            "targetSurface": .string(evidence.targetSurface),
            "openedWithinSeconds": .double(evidence.openedWithinSeconds),
            "coreaudiodCPUPeakPercent": .double(evidence.coreaudiodCPUPeakPercent),
            "coreaudiodCPUSustainedPercent": .double(evidence.coreaudiodCPUSustainedPercent),
            "routeStateBefore": .string(evidence.routeStateBefore.rawValue),
            "routeStateAfter": .string(evidence.routeStateAfter.rawValue),
            "result": .string(evidence.result.rawValue),
            "failureReason": .string(evidence.failureReason ?? "none")
        ])
    }

    private static func diagnosticValue(_ evidence: RouteRecoveryEvidence) -> DiagnosticFieldValue {
        .object([
            "trigger": .string(evidence.trigger),
            "detectedWithinSeconds": .double(evidence.detectedWithinSeconds),
            "expectedState": .string(evidence.expectedState.rawValue),
            "actualState": .string(evidence.actualState.rawValue),
            "recoveryAction": .string(evidence.recoveryAction),
            "result": .string(evidence.result.rawValue)
        ])
    }

    private static func diagnosticValue(_ event: LowResourceRecoveryEvent) -> DiagnosticFieldValue {
        .object([
            "trigger": .string(event.trigger.rawValue),
            "previousState": .string(event.previousState.rawValue),
            "newState": .string(event.newState.rawValue),
            "detectedAt": .string(Self.formatDate(event.detectedAt)),
            "recoveryAction": .string(event.recoveryAction),
            "publicDeviceAvailability": .string(event.publicDeviceAvailability.rawValue)
        ])
    }

    private static func diagnosticValue(_ decision: LowResourcePromotionDecision) -> DiagnosticFieldValue {
        .object([
            "status": .string(decision.status.rawValue),
            "decidedAt": .string(Self.formatDate(decision.decidedAt)),
            "reason": .string(decision.reason),
            "fallbackBaseline": .string(decision.fallbackBaseline)
        ])
    }

    private static func diagnosticValue(_ evidence: InstallerLifecycleEvidence) -> DiagnosticFieldValue {
        .object([
            "operation": .string(evidence.operation),
            "preState": .string(evidence.preState),
            "postState": .string(evidence.postState),
            "coreAudioRefreshRequired": .bool(evidence.coreAudioRefreshRequired),
            "runtimeProbeResult": .string(evidence.runtimeProbeResult),
            "result": .string(evidence.result.rawValue)
        ])
    }

    private static func diagnosticValue(_ evidence: UXReadinessEvidence) -> DiagnosticFieldValue {
        .object([
            "state": .string(evidence.state.rawValue),
            "copyClaim": .string(evidence.copyClaim),
            "nonRecordingExplicit": .bool(evidence.nonRecordingExplicit),
            "recordingImplied": .bool(evidence.recordingImplied),
            "accessibilityNotes": .string(evidence.accessibilityNotes),
            "result": .string(evidence.result.rawValue)
        ])
    }

    private static func diagnosticValue(_ state: DeferredRecordingAcceptanceState) -> DiagnosticFieldValue {
        .object([
            "blockedUntil": .string(state.blockedUntil),
            "retentionPolicyRequired": .bool(state.retentionPolicyRequired),
            "deletionPolicyRequired": .bool(state.deletionPolicyRequired),
            "result": .string(state.result.rawValue)
        ])
    }

    private static func diagnosticValue(_ event: RecordingEvidenceEvent) -> DiagnosticFieldValue {
        .object([
            "eventId": .string(event.eventId),
            "sessionId": .string(event.sessionId),
            "eventType": .string(event.eventType.rawValue),
            "occurredAt": .string(Self.formatDate(event.occurredAt)),
            "initiator": .string(event.initiator.rawValue),
            "routeState": .string(event.routeState.rawValue),
            "indicatorState": .string(event.indicatorState.rawValue),
            "stopActionAvailable": .bool(event.stopActionAvailable),
            "blockedReason": .string(event.blockedReason.rawValue),
            "recoveryAction": .string(event.recoveryAction ?? "none"),
            "durationMs": .int(event.durationMs ?? -1),
            "diagnosticSafe": .bool(event.diagnosticSafe)
        ])
    }

    private static func diagnosticValue(_ snapshot: RecordingPrerequisiteSnapshot) -> DiagnosticFieldValue {
        .object([
            "routeState": .string(snapshot.routeState.rawValue),
            "routeEvidenceKind": .string(snapshot.routeEvidenceKind.rawValue),
            "policyAllowsRecording": .bool(snapshot.policyAllowsRecording),
            "microphonePermissionGranted": .bool(snapshot.microphonePermissionGranted),
            "storageRisk": .string(snapshot.storageRisk.rawValue),
            "indicatorAvailable": .bool(snapshot.indicatorAvailable),
            "sourceAppEligibility": .string(snapshot.sourceAppEligibility.rawValue),
            "blockedReason": .string(snapshot.blockedReason.rawValue),
            "recoveryAction": .string(snapshot.recoveryAction ?? "none"),
            "evaluatedAt": .string(Self.formatDate(snapshot.evaluatedAt))
        ])
    }

    private static func diagnosticValue(_ snapshot: CaptureIndicatorSnapshot) -> DiagnosticFieldValue {
        .object([
            "surface": .string(snapshot.surface),
            "state": .string(snapshot.state.rawValue),
            "visible": .bool(snapshot.visible),
            "stopActionAvailable": .bool(snapshot.stopActionAvailable),
            "accessibilityLabelPresent": .bool(!snapshot.accessibilityLabel.isEmpty),
            "lastVerifiedAt": .string(Self.formatDate(snapshot.lastVerifiedAt))
        ])
    }

    private static func diagnosticValue(_ manifest: LocalRecordingManifest) -> DiagnosticFieldValue {
        .object([
            "schemaVersion": .string(manifest.schemaVersion),
            "sessionId": .string(manifest.sessionId),
            "createdAt": .string(Self.formatDate(manifest.createdAt)),
            "startedAt": .string(Self.formatDate(manifest.startedAt)),
            "stoppedAt": .string(Self.formatDate(manifest.stoppedAt)),
            "finalizedAt": .string(manifest.finalizedAt.map(Self.formatDate) ?? "none"),
            "status": .string(manifest.status.rawValue),
            "directoryId": .string(manifest.directoryId),
            "manifestFileName": .string(manifest.manifestFileName),
            "transcriptionReadiness": .string(manifest.transcriptionReadiness.rawValue),
            "mediaScribeSourceMode": .string(manifest.mediaScribeSourceMode),
            "tracks": .array(manifest.tracks.map(Self.diagnosticValue)),
            "externalEgressStarted": .bool(manifest.externalEgressStarted),
            "transcriptionStarted": .bool(manifest.transcriptionStarted),
            "diagnosticSafe": .bool(manifest.diagnosticSafe),
            "localDeletionRegistered": .bool(manifest.localDeletionRegistered),
            "leakageFinalization": manifest.leakageFinalization.map(Self.diagnosticValue) ?? .null,
            "failureReason": .string(manifest.failureReason.rawValue),
            "privacySegments": .array((manifest.privacySegments ?? []).map(Self.diagnosticValue)),
            "meetingMuteTruth": manifest.meetingMuteTruth.map(Self.diagnosticValue) ?? .null,
            "meetingMuteTruthEvidence": .array((manifest.meetingMuteTruthEvidence ?? []).map(Self.diagnosticValue)),
            "targetMuteCapability": manifest.targetMuteCapability.map(Self.diagnosticValue) ?? .null,
            "limitationCopyShownAt": .string(manifest.limitationCopyShownAt.map(Self.formatDate) ?? "none")
        ])
    }

    private static func diagnosticValue(_ segment: ProductPrivacySegment) -> DiagnosticFieldValue {
        .object([
            "segmentId": .string(segment.segmentId),
            "sessionId": .string(segment.sessionId),
            "control": .string(segment.control.rawValue),
            "startedAt": .string(Self.formatDate(segment.startedAt)),
            "endedAt": .string(segment.endedAt.map(Self.formatDate) ?? "none"),
            "startMonotonicMs": .int(segment.startMonotonicMs),
            "endMonotonicMs": .int(segment.endMonotonicMs ?? -1),
            "durationMs": .int(segment.durationMs),
            "localMicTreatment": .string(segment.localMicTreatment.rawValue),
            "initiator": .string(segment.initiator.rawValue),
            "diagnosticSafe": .bool(segment.diagnosticSafe)
        ])
    }

    private static func diagnosticValue(_ decision: MuteTruthDecision) -> DiagnosticFieldValue {
        .object([
            "sessionId": .string(decision.sessionId),
            "decision": .string(decision.decision.rawValue),
            "reason": .string(decision.reason.rawValue),
            "privacySegmentIds": .array(decision.privacySegmentIds.map { .string($0) }),
            "targetEvidenceIds": .array(decision.targetEvidenceIds.map { .string($0) }),
            "safeForDiagnostics": .bool(decision.safeForDiagnostics),
            "decidedAt": .string(Self.formatDate(decision.decidedAt))
        ])
    }

    private static func diagnosticValue(_ capability: TargetMuteCapability) -> DiagnosticFieldValue {
        .object([
            "targetId": .string(capability.targetId),
            "targetDisplayName": .string(capability.targetDisplayName),
            "targetFamily": .string(capability.targetFamily.rawValue),
            "productPauseSupported": .bool(capability.productPauseSupported),
            "meetingAppMuteAdapterSupported": .bool(capability.meetingAppMuteAdapterSupported),
            "firstMatrixStatus": .string(capability.firstMatrixStatus.rawValue),
            "releaseClaim": .string(capability.releaseClaim)
        ])
    }

    private static func diagnosticValue(_ evidence: MeetingMuteTruthEvidence) -> DiagnosticFieldValue {
        .object([
            "evidenceId": .string(evidence.evidenceId),
            "sessionId": .string(evidence.sessionId),
            "targetId": .string(evidence.targetId),
            "targetDisplayName": .string(evidence.targetDisplayName),
            "source": .string(evidence.source.rawValue),
            "status": .string(evidence.status.rawValue),
            "freshness": .string(evidence.freshness.rawValue),
            "limitationCopyShown": .bool(evidence.limitationCopyShown),
            "recordedAt": .string(Self.formatDate(evidence.recordedAt)),
            "adapterId": .string(evidence.adapterId ?? "none"),
            "diagnosticSafe": .bool(evidence.diagnosticSafe)
        ])
    }

    private static func diagnosticValue(_ track: LocalRecordingTrack) -> DiagnosticFieldValue {
        .object([
            "trackId": .string(track.trackId),
            "role": .string(track.role.rawValue),
            "mediaScribeField": .string(track.mediaScribeField.rawValue),
            "status": .string(track.status.rawValue),
            "evidenceRole": .string(track.evidenceRole.rawValue),
            "fileName": .string(track.fileName),
            "format": .string(track.format),
            "sampleRate": .double(track.sampleRate),
            "channelCount": .int(track.channelCount),
            "bitsPerSample": .int(track.bitsPerSample),
            "durationMs": .int(track.durationMs),
            "byteCount": .int(Int(track.byteCount)),
            "frameCount": .int(Int(track.frameCount)),
            "timelineStartMs": .int(track.timelineStartMs),
            "timelineAligned": .bool(track.timelineAligned),
            "residualLeakageStatus": .string(track.residualLeakageStatus?.rawValue ?? "not_applicable"),
            "eligibleForTranscription": .bool(track.eligibleForTranscription ?? false),
            "failureReason": .string(track.failureReason.rawValue)
        ])
    }

    private static func diagnosticValue(_ finalization: LeakageFinalization) -> DiagnosticFieldValue {
        .object([
            "status": .string(finalization.status.rawValue),
            "evaluatedAt": .string(Self.formatDate(finalization.evaluatedAt)),
            "thresholdVersion": .string(finalization.thresholdVersion),
            "measurementAttempted": .bool(finalization.measurementAttempted),
            "measurementApplicable": .bool(finalization.measurementApplicable),
            "alignmentStatus": .string(finalization.alignmentStatus.rawValue),
            "confidence": .double(finalization.confidence),
            "failureReason": .string(finalization.failureReason.rawValue),
            "originalEvidenceStatus": .string(finalization.originalEvidenceStatus.rawValue),
            "derivedArtifactStatus": .string(finalization.derivedArtifactStatus?.rawValue ?? "not_applicable"),
            "transcriptionGate": .string(finalization.transcriptionGate.rawValue),
            "routeMetadata": Self.diagnosticValue(finalization.routeMetadata),
            "measurement": finalization.measurement.map(Self.diagnosticValue) ?? .null
        ])
    }

    private static func diagnosticValue(_ route: RecordingRouteMetadata) -> DiagnosticFieldValue {
        .object([
            "inputRouteClass": .string(route.inputRouteClass ?? "unknown"),
            "outputRouteClass": .string(route.outputRouteClass ?? "unknown"),
            "outputVolumeBucket": .string(route.outputVolumeBucket.rawValue),
            "muteState": .string(route.muteState.rawValue),
            "browserTarget": .string(route.browserTarget ?? "unknown"),
            "routeChangeCount": .int(route.routeChangeCount),
            "coreaudiodState": .string(route.coreaudiodState ?? "unknown"),
            "sleepWakeObserved": .bool(route.sleepWakeObserved),
            "selfRoutingRejected": .bool(route.selfRoutingRejected)
        ])
    }

    private static func diagnosticValue(_ measurement: LeakageMeasurement) -> DiagnosticFieldValue {
        .object([
            "measurementId": .string(measurement.measurementId ?? "unknown"),
            "windowCount": .int(measurement.windowCount ?? 0),
            "farEndOnlyWindowMs": .int(measurement.farEndOnlyWindowMs ?? 0),
            "doubleTalkExcludedWindowMs": .int(measurement.doubleTalkExcludedWindowMs ?? 0),
            "alignmentOffsetMs": .int(measurement.alignmentOffsetMs ?? 0),
            "alignmentDriftMs": .int(measurement.alignmentDriftMs ?? 0),
            "leakageLevelDb": .double(measurement.leakageLevelDb ?? measurement.relativeLeakageDb),
            "correlationPeak": .double(measurement.correlationPeak ?? 0),
            "correlationLagMs": .int(measurement.correlationLagMs ?? 0),
            "directLoopbackSuspicion": .bool(measurement.directLoopbackSuspicion ?? false),
            "acousticLeakageSuspicion": .bool(measurement.acousticLeakageSuspicion ?? false),
            "clippingObserved": .bool(measurement.clippingObserved ?? false),
            "dropoutObserved": .bool(measurement.dropoutObserved ?? false),
            "confidence": .double(measurement.confidence ?? 0),
            "status": .string(measurement.status.rawValue)
        ])
    }

    private static func diagnosticValue(_ snapshot: RouteTruthSnapshot) -> DiagnosticFieldValue {
        .object([
            "snapshotId": .string(snapshot.snapshotId),
            "recordedAt": .string(Self.formatDate(snapshot.recordedAt)),
            "resourceState": .string(snapshot.resourceState.rawValue),
            "result": .string(snapshot.result.rawValue),
            "publication": .object([
                "microphoneVisible": .bool(snapshot.publication.microphoneVisible),
                "speakerVisible": .bool(snapshot.publication.speakerVisible),
                "microphoneAlive": .string(snapshot.publication.microphoneAlive.map(String.init) ?? "unknown"),
                "speakerAlive": .string(snapshot.publication.speakerAlive.map(String.init) ?? "unknown"),
                "microphoneRunning": .string(snapshot.publication.microphoneRunning.map(String.init) ?? "unknown"),
                "speakerRunning": .string(snapshot.publication.speakerRunning.map(String.init) ?? "unknown"),
                "hidden": .bool(snapshot.publication.hidden),
                "runtimeProbeResult": .string(snapshot.publication.runtimeProbeResult.rawValue)
            ]),
            "clientActivity": .object([
                "microphoneClientCount": .int(snapshot.clientActivity.microphoneClientCount),
                "speakerClientCount": .int(snapshot.clientActivity.speakerClientCount),
                "microphoneRunning": .bool(snapshot.clientActivity.microphoneRunning),
                "speakerRunning": .bool(snapshot.clientActivity.speakerRunning),
                "source": .string(snapshot.clientActivity.source.rawValue),
                "naturalSilenceAllowed": .bool(snapshot.clientActivity.naturalSilenceAllowed)
            ]),
            "appBridge": .object([
                "heartbeatState": .string(snapshot.appBridgeHealth.heartbeatState.rawValue),
                "timeoutMs": .int(snapshot.appBridgeHealth.timeoutMs),
                "driverFailClosed": .bool(snapshot.appBridgeHealth.driverFailClosed),
                "publicDeviceAvailability": .string(snapshot.appBridgeHealth.publicDeviceAvailability),
                "recoveryAction": .string(snapshot.appBridgeHealth.recoveryAction)
            ]),
            "physicalDevices": .object([
                "inputDeviceName": .string(snapshot.physicalDevices.inputDeviceName),
                "outputDeviceName": .string(snapshot.physicalDevices.outputDeviceName),
                "inputKind": .string(snapshot.physicalDevices.inputKind.rawValue),
                "outputKind": .string(snapshot.physicalDevices.outputKind.rawValue),
                "selectionResult": .string(snapshot.physicalDevices.selectionResult.rawValue),
                "rejectionReason": .string(snapshot.physicalDevices.rejectionReason ?? "none")
            ]),
            "recordingTrigger": .object([
                "recordingTriggerState": .string(snapshot.recordingTrigger.recordingTriggerState.rawValue),
                "driverRecordingOwner": .bool(snapshot.recordingTrigger.driverRecordingOwner),
                "appRecordingOwner": .bool(snapshot.recordingTrigger.appRecordingOwner),
                "recordingArtifactsCreated": .bool(snapshot.recordingTrigger.recordingArtifactsCreated),
                "externalEgressStarted": .bool(snapshot.recordingTrigger.externalEgressStarted)
            ])
        ])
    }

    private static func diagnosticValue(_ attempt: StartupAttemptEvidence) -> DiagnosticFieldValue {
        .object([
            "attemptId": .string(attempt.attemptId),
            "trigger": .string(attempt.trigger.rawValue),
            "startedAt": .string(Self.formatDate(attempt.startedAt)),
            "completedAt": .string(Self.formatDate(attempt.completedAt)),
            "durationMs": .int(attempt.durationMs),
            "outcome": .string(attempt.outcome.rawValue),
            "blockedReason": .string(attempt.blockedReason ?? "none"),
            "fallbackUsed": .bool(attempt.fallbackUsed)
        ])
    }

    private static func diagnosticValue(_ run: LowResourceValidationRun) -> DiagnosticFieldValue {
        .object([
            "runId": .string(run.runId),
            "createdAt": .string(Self.formatDate(run.createdAt)),
            "appBuild": .string(run.appBuild),
            "driverBuild": .string(run.driverBuild),
            "baseline": .string(run.baseline),
            "result": .string(run.result.rawValue),
            "routeTruthCount": .int(run.routeTruthSnapshots.count),
            "startupAttemptCount": .int(run.startupAttempts.count),
            "realtimeSafetyResult": .string(run.realtimeSafety.result.rawValue)
        ])
    }

    private static func diagnosticValue(_ event: RouteEvidenceEvent) -> DiagnosticFieldValue {
        var object: [String: DiagnosticFieldValue] = [
            "eventId": .string(event.eventId),
            "sessionId": .string(event.sessionId),
            "family": .string(event.family.rawValue),
            "name": .string(event.name),
            "observedAt": .string(Self.formatDate(event.observedAt)),
            "source": .string(event.source.rawValue),
            "redactionState": .string(event.redactionState.rawValue)
        ]
        if let routeState = event.routeState {
            object["routeState"] = .string(routeState.rawValue)
        }
        if let target = event.target {
            object["target"] = .string(target.rawValue)
        }
        if let validationRun = event.validationRun {
            object["validationRun"] = diagnosticValue(validationRun)
        }
        if let releaseDecision = event.releaseDecision {
            object["releaseDecision"] = diagnosticValue(releaseDecision)
        }
        if let frameContinuity = event.frameContinuity {
            object["frameContinuity"] = diagnosticValue(frameContinuity)
        }
        if let recordingTimeline = event.recordingTimeline {
            object["recordingTimeline"] = diagnosticValue(recordingTimeline)
        }
        return .object(object)
    }

    private static func diagnosticValue(_ evidence: ValidationRunEvidence) -> DiagnosticFieldValue {
        .object([
            "runId": .string(evidence.runId),
            "durationGate": .string(evidence.durationGate.rawValue),
            "result": .string(evidence.result.rawValue),
            "targetsCovered": .array(evidence.targetsCovered.map { .string($0.rawValue) }),
            "deviceClassesCovered": .array(evidence.deviceClassesCovered.map { .string($0.rawValue) }),
            "userActionCount": .int(evidence.userActionCount),
            "startedAt": .string(Self.formatDate(evidence.startedAt)),
            "completedAt": .string(evidence.completedAt.map(Self.formatDate) ?? "none")
        ])
    }

    private static func diagnosticValue(_ evidence: RecordingTimelineIntegrityEvidence) -> DiagnosticFieldValue {
        .object([
            "routeSessionId": .string(evidence.routeSessionId),
            "autorepairAttemptIds": .array(evidence.autorepairAttemptIds.map { .string($0) }),
            "micDurationSeconds": .double(evidence.micDurationSeconds),
            "incomingDurationSeconds": .double(evidence.incomingDurationSeconds),
            "durationDifferenceSeconds": .double(evidence.durationDifferenceSeconds),
            "alignmentBand": .string(evidence.alignmentBand.rawValue),
            "interruptionCategory": .string(evidence.interruptionCategory.rawValue)
        ])
    }

    private static func diagnosticValue(_ decision: RouteReleaseDecision) -> DiagnosticFieldValue {
        .object([
            "outcome": .string(decision.outcome.rawValue),
            "reason": .string(decision.reason.rawValue),
            "clientEvidenceFresh": .bool(decision.clientEvidenceFresh),
            "decidedAt": .string(Self.formatDate(decision.decidedAt))
        ])
    }

    private static func diagnosticValue(_ snapshot: FrameContinuitySnapshot) -> DiagnosticFieldValue {
        .object([
            "microphoneFramesObserved": .int(snapshot.microphoneFramesObserved),
            "incomingFramesObserved": .int(snapshot.incomingFramesObserved),
            "missingFrameCount": .int(snapshot.missingFrameCount),
            "dropoutCount": .int(snapshot.dropoutCount),
            "windowMs": .int(snapshot.windowMs)
        ])
    }

    private static func boolOrUnknown(_ value: Bool?) -> DiagnosticFieldValue {
        value.map { .bool($0) } ?? .string("unknown")
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
