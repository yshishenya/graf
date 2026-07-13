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

    public func buildMeetingDetectionDetectorBundle(
        evidence: MeetingDetectionDetectorEvidence
    ) throws -> DiagnosticBundle {
        try buildBundle(
            schemaVersion: "1",
            manifest: [
                "meetingDetectionDetector": .object([
                    "status": .string(evidence.status),
                    "registryVersion": .string(evidence.registryVersion),
                    "bundleId": .string(evidence.bundleID ?? "none"),
                    "targetId": .string(evidence.targetID ?? "none"),
                    "supportMode": .string(evidence.supportMode?.rawValue ?? "unknown"),
                    "decision": .string(evidence.decision),
                    "reason": .string(evidence.reason ?? "none"),
                    "observedAt": .string(Self.formatDate(evidence.observedAt))
                ])
            ],
            failureFamily: "meeting_detection_detector"
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
        manifest["captureState"] = .string(events.last?.captureState.rawValue ?? "unknown")
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
        bundleManifest["microphoneSelection"] = manifest.microphoneSelection.map(Self.diagnosticValue) ?? .null
        bundleManifest["microphoneStream"] = manifest.microphoneStream.map(Self.diagnosticValue) ?? .null
        bundleManifest["microphoneStreamHealth"] = manifest.microphoneStreamHealth.map(Self.diagnosticValue) ?? .null
        bundleManifest["appleProcessingOutcome"] = manifest.appleProcessingOutcome.map(Self.diagnosticValue) ?? .null
        bundleManifest["appleProcessingValidationRows"] = .array(
            (manifest.appleProcessingOutcome?.validationRows ?? []).map(Self.diagnosticValue)
        )
        bundleManifest["webRTCAEC3Outcome"] = manifest.webRTCAEC3Outcome.map(Self.diagnosticValue) ?? .null
        bundleManifest["webRTCAEC3ValidationRows"] = .array(
            (manifest.webRTCAEC3Outcome?.validationRows ?? []).map(Self.diagnosticValue)
        )
        bundleManifest["webRTCAEC3RollbackEvents"] = .array(
            (manifest.webRTCAEC3Outcome?.rollbackEvents ?? []).map(Self.diagnosticValue)
        )
        bundleManifest["webRTCAEC3EchoDelaySummary"] = .string(
            manifest.webRTCAEC3Outcome?.validationRows.first?.thresholdSummary ?? "not_recorded"
        )
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

    private static func diagnosticValue(_ event: RecordingEvidenceEvent) -> DiagnosticFieldValue {
        .object([
            "eventId": .string(event.eventId),
            "sessionId": .string(event.sessionId),
            "eventType": .string(event.eventType.rawValue),
            "occurredAt": .string(Self.formatDate(event.occurredAt)),
            "initiator": .string(event.initiator.rawValue),
            "captureState": .string(event.captureState.rawValue),
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
            "policyAllowsRecording": .bool(snapshot.policyAllowsRecording),
            "microphonePermissionGranted": .bool(snapshot.microphonePermissionGranted),
            "systemAudioPermissionGranted": .bool(snapshot.systemAudioPermissionGranted),
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
            "microphoneSelection": manifest.microphoneSelection.map(Self.diagnosticValue) ?? .null,
            "microphoneStream": manifest.microphoneStream.map(Self.diagnosticValue) ?? .null,
            "microphoneStreamHealth": manifest.microphoneStreamHealth.map(Self.diagnosticValue) ?? .null,
            "appleProcessingOutcome": manifest.appleProcessingOutcome.map(Self.diagnosticValue) ?? .null,
            "webRTCAEC3Outcome": manifest.webRTCAEC3Outcome.map(Self.diagnosticValue) ?? .null,
            "privacySegments": .array((manifest.privacySegments ?? []).map(Self.diagnosticValue)),
            "meetingMuteTruth": manifest.meetingMuteTruth.map(Self.diagnosticValue) ?? .null,
            "meetingMuteTruthEvidence": .array((manifest.meetingMuteTruthEvidence ?? []).map(Self.diagnosticValue)),
            "targetMuteCapability": manifest.targetMuteCapability.map(Self.diagnosticValue) ?? .null,
            "limitationCopyShownAt": .string(manifest.limitationCopyShownAt.map(Self.formatDate) ?? "none"),
            "recordingMetadata": manifest.recordingMetadata.map(Self.diagnosticValue) ?? .null
        ])
    }

    private static func diagnosticValue(_ metadata: RecordingDisplayMetadata) -> DiagnosticFieldValue {
        .object([
            "recordingStartedAt": .string(Self.formatDate(metadata.recordingStartedAt)),
            "recordingStoppedAt": .string(metadata.recordingStoppedAt.map(Self.formatDate) ?? "none"),
            "titlePresent": .bool(!metadata.title.isEmpty),
            "titleStatus": .string(metadata.titleStatus.rawValue),
            "titleSource": .string(metadata.titleSource.rawValue),
            "titleConfidence": .string(metadata.titleConfidence.rawValue),
            "titleLength": .int(metadata.title.count),
            "safeFileBasenamePresent": .bool(!metadata.safeFileBasename.isEmpty),
            "safeFileBasenameLength": .int(metadata.safeFileBasename.count),
            "suppressedSources": .array(metadata.suppressedSources.map { suppression in
                .object([
                    "source": .string(suppression.source.rawValue),
                    "reason": .string(suppression.reason)
                ])
            })
        ])
    }

    private static func diagnosticValue(_ selection: RecordingMicrophoneSelection) -> DiagnosticFieldValue {
        .object([
            "selectionId": .string(selection.selectionId),
            "mode": .string(selection.mode.rawValue),
            "inputDeviceId": .string(selection.inputDeviceId ?? "unknown"),
            "inputDisplayName": .string(selection.inputDisplayName ?? "unknown"),
            "deviceClass": .string(selection.deviceClass?.rawValue ?? "unknown"),
            "workingDeviceKind": .string(selection.workingDeviceKind?.rawValue ?? "unknown"),
            "selectionResult": .string(selection.selectionResult.rawValue),
            "rejectionReason": .string(selection.rejectionReason?.rawValue ?? "none"),
            "resolvedAt": .string(Self.formatDate(selection.resolvedAt)),
            "diagnosticSafe": .bool(selection.diagnosticSafe)
        ])
    }

    private static func diagnosticValue(_ stream: AppOwnedMicrophoneStreamSession) -> DiagnosticFieldValue {
        .object([
            "sessionId": .string(stream.sessionId),
            "selection": Self.diagnosticValue(stream.selection),
            "permissionState": .string(stream.permissionState.rawValue),
            "streamKind": .string(stream.streamKind.rawValue),
            "startedAt": .string(stream.startedAt.map(Self.formatDate) ?? "none"),
            "stoppedAt": .string(stream.stoppedAt.map(Self.formatDate) ?? "none"),
            "sampleRate": .double(stream.sampleRate),
            "channelCount": .int(stream.channelCount),
            "writerSampleRate": .double(stream.writerSampleRate),
            "writerChannelCount": .int(stream.writerChannelCount),
            "frameCount": .int(Int(stream.frameCount)),
            "droppedFrameCount": .int(Int(stream.droppedFrameCount)),
            "silentFrameCount": .int(Int(stream.silentFrameCount)),
            "clippedFrameCount": .int(Int(stream.clippedFrameCount)),
            "routeChangeCount": .int(stream.routeChangeCount),
            "lastFrameAt": .string(stream.lastFrameAt.map(Self.formatDate) ?? "none"),
            "failureReason": .string(stream.failureReason.rawValue),
            "diagnosticSafe": .bool(stream.diagnosticSafe)
        ])
    }

    private static func diagnosticValue(_ health: MicrophoneStreamHealth) -> DiagnosticFieldValue {
        .object([
            "gateStatus": .string(health.gateStatus.rawValue),
            "failureReason": .string(health.failureReason.rawValue),
            "framesObserved": .bool(health.framesObserved),
            "timingConfidence": .string(health.timingConfidence.rawValue),
            "silenceStatus": .string(health.silenceStatus.rawValue),
            "lastLevel": .double(health.lastLevel ?? -1),
            "lastLevelAt": .string(health.lastLevelAt.map(Self.formatDate) ?? "none"),
            "cleanupReadiness": .string(health.cleanupReadiness.rawValue),
            "evidenceCodes": .array(health.evidenceCodes.map { .string($0) }),
            "diagnosticSafe": .bool(health.diagnosticSafe)
        ])
    }

    private static func diagnosticValue(_ outcome: AppleProcessingOutcome) -> DiagnosticFieldValue {
        .object([
            "feature": .string(outcome.feature),
            "candidateId": .string(outcome.candidateId),
            "primaryOutcome": .string(outcome.primaryOutcome.rawValue),
            "nextStepRecommendation": .string(outcome.nextStepRecommendation.rawValue),
            "diagnosticSafe": .bool(outcome.diagnosticSafe),
            "failureReason": .string(outcome.failureReason ?? "none"),
            "canClaimCleanBuiltinSpeakerphone": .bool(outcome.canClaimCleanBuiltinSpeakerphone),
            "validationRowCount": .int(outcome.validationRows.count)
        ])
    }

    private static func diagnosticValue(_ row: AppleProcessingValidationRow) -> DiagnosticFieldValue {
        .object([
            "feature": .string(row.feature),
            "candidateId": .string(row.candidateId),
            "candidateKind": .string(row.candidateKind.rawValue),
            "routeClass": .string(row.routeClass.rawValue),
            "scenario": .string(row.scenario.rawValue),
            "baselineStatus": .string(row.baselineStatus.rawValue),
            "candidateStatus": .string(row.candidateStatus.rawValue),
            "lineageStatus": .string(row.lineageStatus.rawValue),
            "speechPreservationStatus": .string(row.speechPreservationStatus.rawValue),
            "alignmentStatus": .string(row.alignmentStatus.rawValue),
            "stabilityStatus": .string(row.normalizedStabilityStatus.rawValue),
            "diagnosticSafe": .bool(row.diagnosticSafe),
            "failureReason": .string(row.failureReason ?? "none")
        ])
    }

    private static func diagnosticValue(_ outcome: WebRTCAEC3DecisionRecord) -> DiagnosticFieldValue {
        .object([
            "feature": .string(outcome.feature),
            "candidateId": .string(outcome.candidateId),
            "primaryOutcome": .string(outcome.primaryOutcome.rawValue),
            "primaryOutcomeCount": .int(outcome.primaryOutcomeCount),
            "nextStepRecommendation": .string(outcome.nextStepRecommendation.rawValue),
            "thresholdProfileId": .string(outcome.validationRows.first?.thresholdProfileId ?? "not_recorded"),
            "thresholdSummary": .string(outcome.validationRows.first?.thresholdSummary ?? "not_recorded"),
            "appStatusState": .string(outcome.validationRows.first?.appStatusState.rawValue ?? WebRTCAEC3AppStatusState.notEvaluated.rawValue),
            "diagnosticSafe": .bool(outcome.diagnosticSafe),
            "failureReason": .string(outcome.failureReason ?? "none"),
            "canClaimCleanBuiltInSpeakerphone": .bool(outcome.canClaimCleanBuiltInSpeakerphone),
            "validationRowCount": .int(outcome.validationRows.count),
            "supportingRouteRowCount": .int(outcome.supportingRouteRows?.count ?? 0),
            "supportingRoutesCanBroadenPromotionScope": .bool(outcome.supportingRoutesCanBroadenPromotionScope),
            "fallbackFeatureId": .string(outcome.fallbackFeatureId ?? "none"),
            "requiresFallbackPlanning": .bool(outcome.requiresFallbackPlanning),
            "limitations": .array(outcome.decisionLimitations.map { .string($0) }),
            "rollbackEventCount": .int(outcome.rollbackEvents?.count ?? 0)
        ])
    }

    private static func diagnosticValue(_ row: WebRTCAEC3ValidationRow) -> DiagnosticFieldValue {
        .object([
            "feature": .string(row.feature),
            "rowId": .string(row.rowId),
            "candidateId": .string(row.candidateId),
            "corpusId": .string(row.corpusId ?? "none"),
            "scenarioFamily": .string(row.scenarioFamily.rawValue),
            "validationKind": .string(row.validationKind.rawValue),
            "routeClass": .string(row.routeClass.rawValue),
            "baselineStatus": .string(row.baselineStatus.rawValue),
            "candidateStatus": .string(row.candidateStatus.rawValue),
            "lineageStatus": .string(row.lineageStatus.rawValue),
            "speechPreservationStatus": .string(row.speechPreservationStatus.rawValue),
            "residualLeakageStatus": .string(row.residualLeakageStatus.rawValue),
            "timingConfidence": .string(row.timingConfidence.rawValue),
            "referenceStatus": .string(row.referenceStatus.rawValue),
            "stabilityStatus": .string(row.stabilityStatus.rawValue),
            "thresholdProfileId": .string(row.thresholdProfileId),
            "thresholdSummary": .string(row.thresholdSummary),
            "appStatusState": .string(row.appStatusState.rawValue),
            "diagnosticSafe": .bool(row.diagnosticSafe),
            "failureReason": .string(row.failureReason ?? "none")
        ])
    }

    private static func diagnosticValue(_ event: AEC3RollbackEvent) -> DiagnosticFieldValue {
        .object([
            "rollbackId": .string(event.rollbackId),
            "candidateId": .string(event.candidateId),
            "trigger": .string(event.trigger.rawValue),
            "previousLineageStatus": .string(event.previousLineageStatus.rawValue),
            "restoredLineageStatus": .string(event.restoredLineageStatus.rawValue),
            "cleanRecordingClaimRemoved": .bool(event.cleanRecordingClaimRemoved),
            "appStatusShown": .bool(event.appStatusShown),
            "thresholdProfileId": .string(event.thresholdProfileId),
            "occurredAt": .string(Self.formatDate(event.occurredAt)),
            "diagnosticSafe": .bool(event.diagnosticSafe)
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
            "sleepWakeObserved": .bool(route.sleepWakeObserved)
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
