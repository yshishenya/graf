import Foundation

public enum DiagnosticFieldValue: Equatable, Sendable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)
    case object([String: DiagnosticFieldValue])
    case array([DiagnosticFieldValue])
    case null
}

public struct DiagnosticRedactionResult: Sendable {
    public let manifest: [String: DiagnosticFieldValue]
    public let status: DiagnosticRedactionStatus
    public let removedFields: [String]
}

public struct DiagnosticRedactor: Sendable {
    public static let forbiddenKeys: Set<String> = [
        "rawAudio",
        "audioSnippet",
        "rawSamples",
        "audioClip",
        "audioDownloadUrl",
        "audio_download_url",
        "debugWav",
        "debugWAV",
        "webrtcLogDump",
        "webrtcDebugLog",
        "webrtcTrace",
        "debugLog",
        "unboundedLog",
        "transcriptText",
        "meetingContent",
        "meetingNotes",
        "participantSpeech",
        "participantNames",
        "speakerDiarizationText",
        "rawTranscript",
        "mediaScribeApiKey",
        "apiKey",
        "credentialPath",
        "liveCredentialPath",
        "absolutePath",
        "password",
        "sessionToken",
        "refreshToken",
        "deviceToken",
        "signedUrl",
        "signed_url",
        "signedURL",
        "signedUrls",
        "token",
        "privateLocalPath",
        "private_local_path",
        "localAbsolutePath",
        "temporaryUploadUrl",
        "temporaryDownloadUrl",
        "mediaScribeCredentials",
        "mediaScribeJobId",
        "minioCredentials",
        "objectStorageCredentials",
        "objectStorageKey",
        "storageObjectKey",
        "storage_object_key",
        "uploadToken",
        "bearerToken",
        "uploadBearerToken",
        "authBearerToken",
        "authorization"
    ]

    public static let forbiddenValuePatterns: [String] = [
        "-----BEGIN PRIVATE KEY-----",
        "X-API-Key:",
        "Authorization: Bearer ",
        "Bearer ",
        "presigned",
        "http://",
        "https://",
        "www.",
        "token=",
        "password"
    ]

    public static let allowedTopLevelKeys: Set<String> = [
        "schemaVersion",
        "createdAt",
        "contentHash",
        "redactionState",
        "appVersion",
        "driverVersion",
        "audioComponentVersion",
        "installerPackageVersion",
        "macOSVersion",
        "cpuArchitecture",
        "entitlementStatus",
        "notarizationStatus",
        "virtualDeviceAvailability",
        "routeStatus",
        "physicalDeviceClass",
        "permissionStatus",
        "recoveryActionId",
        "routeVerificationResults",
        "liveRouteReadiness",
        "microphonePathEvidence",
        "speakerPathEvidence",
        "latencyMeasurement",
        "leakageMeasurement",
        "leakageFinalization",
        "leakageRouteMetadata",
        "leakageFinalizationEvents",
        "leakageDependencyDecisions",
        "directLoopbackSuspicion",
        "acousticLeakageSuspicion",
        "thresholdVersion",
        "alignmentStatus",
        "transcriptionGate",
        "browserTargetEvidence",
        "livePassthrough",
        "microphonePassthroughPath",
        "speakerPassthroughPath",
        "passthroughBrowserEvidence",
        "passthroughRecoveryEvents",
        "releaseHardeningRun",
        "releaseHardeningEvidenceFamilies",
        "lowResourceValidationRun",
        "lowResourceRouteTruth",
        "lowResourceStartupAttempts",
        "lowResourceRecoveryEvents",
        "lowResourceRealtimeSafety",
        "lowResourcePromotionDecision",
        "recordingEvidence",
        "recordingPrerequisites",
        "recordingIndicatorState",
        "localRecordingManifest",
        "localRecordingTracks",
        "localRecordingEvidence",
        "systemAudioCaptureSession",
        "microphoneCaptureSession",
        "microphoneSelection",
        "microphoneStream",
        "microphoneStreamHealth",
        "appleProcessingOutcome",
        "appleProcessingValidationRows",
        "processedMicrophoneEvidence",
        "appleProcessingRouteClass",
        "appleProcessingLineageStatus",
        "appleProcessingPrimaryOutcome",
        "appleProcessingFailureReason",
        "appleProcessingCPUPeakPercent",
        "appleProcessingCPUSustainedPercent",
        "appleProcessingLatencyMs",
        "appleProcessingLifecycle",
        "webRTCAEC3Candidate",
        "webRTCAEC3Outcome",
        "webRTCAEC3Decision",
        "webRTCAEC3ValidationRows",
        "webRTCAEC3ValidationCorpus",
        "webRTCAEC3ThresholdProfile",
        "webRTCAEC3ThresholdSummary",
        "webRTCAEC3EchoDelaySummary",
        "webRTCAEC3AppStatus",
        "webRTCAEC3Rollback",
        "webRTCAEC3RollbackEvents",
        "webRTCAEC3RollbackTrigger",
        "webRTCAEC3Diagnostics",
        "webRTCAEC3RouteClass",
        "webRTCAEC3PromotionScope",
        "webRTCAEC3DependencyReadiness",
        "webRTCAEC3ReferenceStatus",
        "webRTCAEC3TimingConfidence",
        "webRTCAEC3SpeechPreservationStatus",
        "webRTCAEC3ResidualLeakageStatus",
        "webRTCAEC3StabilityStatus",
        "webRTCAEC3LineageStatus",
        "webRTCAEC3PrimaryOutcome",
        "webRTCAEC3FailureReason",
        "webRTCAEC3LicenseReadiness",
        "webRTCAEC3PackagingReadiness",
        "webRTCAEC3SigningStatus",
        "captureScopeApproval",
        "capturePermissions",
        "captureHealthSnapshot",
        "privacySegments",
        "meetingMuteTruth",
        "meetingMuteTruthEvidence",
        "targetMuteCapability",
        "limitationCopyShownAt",
        "systemAudioCaptureEvidence",
        "shortSmokeEvidence",
        "coreAudioNoHangEvidence",
        "routeRecoveryEvidence",
        "installerLifecycleEvidence",
        "uxReadinessEvidence",
        "deferredRecordingAcceptance",
        "appHeartbeatStatus",
        "routeInvalidationEvents",
        "passthroughHealth",
        "dropoutCount",
        "driftSummary",
        "timingAggregates",
        "localBufferCounts",
        "localBufferSizes",
        "localBufferThresholdState",
        "routeEvidence",
        "routeEvidenceEvent",
        "routeEvidenceEvents",
        "routeEvidenceFile",
        "liveRouteSession",
        "clientActivitySnapshot",
        "macOSDefaultRouteSnapshot",
        "frameContinuitySnapshot",
        "autorepairAttempt",
        "routeReleaseDecision",
        "recordingTimelineEvidence",
        "validationRunEvidence",
        "acceptanceMatrix",
        "userActionAudit",
        "retentionDeadlines",
        "uploadReadiness",
        "uploadFailureCategory",
        "uploadQueue",
        "uploadQueueItems",
        "custodyIncident",
        "uploadAttempt",
        "localMediaRevisionId",
        "mediaRevisionId",
        "mediaRevisionStatus",
        "mediaRevisionSourceKind",
        "mediaRevision",
        "recordingSyncState",
        "desktopSyncState",
        "syncGeneration",
        "lastReconciledAt",
        "syncConflictState",
        "syncConflictReason",
        "acceptedBytesByTrack",
        "retryMode",
        "serverTruth",
        "redactionEngineVersion",
        "diagnosticSchemaVersion",
        "failureFamily",
        "failureReason",
        "sessionId",
        "trackCount",
        "trackRoles",
        "trackStates",
        "hardFailureCount",
        "emptyBufferCount",
        "droppedFrameCount"
    ]

    public init() {}

    public func redact(_ manifest: [String: String]) -> (manifest: [String: String], status: DiagnosticRedactionStatus) {
        var redacted = manifest
        var blockedSensitiveContent = false
        let lowercasedForbiddenKeys = Set(Self.forbiddenKeys.map { $0.lowercased() })

        for key in redacted.keys where lowercasedForbiddenKeys.contains(key.lowercased()) {
            redacted.removeValue(forKey: key)
            blockedSensitiveContent = true
        }

        for (key, value) in redacted {
            if containsForbiddenPattern(value) {
                redacted.removeValue(forKey: key)
                blockedSensitiveContent = true
            }
        }

        return (
            redacted,
            blockedSensitiveContent ? .blockedSensitiveContent : .redacted
        )
    }

    public func redact(
        _ manifest: [String: DiagnosticFieldValue],
        allowedTopLevelKeys: Set<String> = Self.allowedTopLevelKeys
    ) -> DiagnosticRedactionResult {
        let lowercasedForbiddenKeys = Set(Self.forbiddenKeys.map { $0.lowercased() })
        let allowedKeys = Set(allowedTopLevelKeys.map { $0.lowercased() })
        var redacted: [String: DiagnosticFieldValue] = [:]
        var removedFields: [String] = []

        for (key, value) in manifest {
            let path = key
            if lowercasedForbiddenKeys.contains(key.lowercased()) {
                removedFields.append(path)
                continue
            }

            if !allowedKeys.contains(key.lowercased()) {
                removedFields.append(path)
                continue
            }

            let result = redactValue(value, path: path, forbiddenKeys: lowercasedForbiddenKeys)
            if let value = result.value {
                redacted[key] = value
            }
            removedFields.append(contentsOf: result.removedFields)
        }

        return DiagnosticRedactionResult(
            manifest: redacted,
            status: removedFields.isEmpty ? .redacted : .blockedSensitiveContent,
            removedFields: removedFields.sorted()
        )
    }

    private func containsForbiddenPattern(_ value: String) -> Bool {
        if Self.forbiddenValuePatterns.contains(where: { pattern in
            value.range(of: pattern, options: [.caseInsensitive]) != nil
        }) {
            return true
        }
        return value.range(
            of: #"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"#,
            options: [.regularExpression, .caseInsensitive]
        ) != nil
    }

    private func redactValue(
        _ value: DiagnosticFieldValue,
        path: String,
        forbiddenKeys: Set<String>
    ) -> (value: DiagnosticFieldValue?, removedFields: [String]) {
        switch value {
        case .string(let string):
            if containsForbiddenPattern(string) {
                return (nil, [path])
            }
            return (value, [])
        case .int, .double, .bool, .null:
            return (value, [])
        case .array(let values):
            var redactedValues: [DiagnosticFieldValue] = []
            var removedFields: [String] = []

            for (index, item) in values.enumerated() {
                let result = redactValue(item, path: "\(path)[\(index)]", forbiddenKeys: forbiddenKeys)
                if let value = result.value {
                    redactedValues.append(value)
                }
                removedFields.append(contentsOf: result.removedFields)
            }

            return (.array(redactedValues), removedFields)
        case .object(let object):
            var redactedObject: [String: DiagnosticFieldValue] = [:]
            var removedFields: [String] = []

            for (key, child) in object {
                let childPath = "\(path).\(key)"
                if forbiddenKeys.contains(key.lowercased()) {
                    removedFields.append(childPath)
                    continue
                }

                let result = redactValue(child, path: childPath, forbiddenKeys: forbiddenKeys)
                if let value = result.value {
                    redactedObject[key] = value
                }
                removedFields.append(contentsOf: result.removedFields)
            }

            return (.object(redactedObject), removedFields)
        }
    }
}
