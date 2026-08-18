import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

struct ValidationError: Error, CustomStringConvertible {
    let description: String
}

struct ForbiddenFixtureFile: Decodable {
    let schemaVersion: String
    let forbiddenKeys: [String]
    let forbiddenPatterns: [String]
}

struct RecordingSessionEvidenceFixtureFile: Decodable {
    let schema: String
    let requiredEventTypes: [String]
    let requiredFields: [String]
    let forbiddenFields: [String]
    let forbiddenExternalActivity: [String]
}

struct LocalRecordingManifestFixtureFile: Decodable {
    let schema: String
    let requiredFields: [String]
    let requiredTrackRoles: [String]
    let allowedStatuses: [String]
    let allowedReadinessStates: [String]
    let requiredTrackFields: [String]
    let forbiddenFields: [String]
    let forbiddenExternalActivity: [String]
}

struct RecordingArtifactFormatFixtureFile: Decodable {
    struct Package: Decodable {
        let manifestSchemaVersion: String
        let manifestFileName: String
        let requiredFiles: [String]
        let exactFinalMembers: [String]
        let mediaScribeSourceMode: String
        let serverSourceKind: String
        let transportRoles: [String]
        let externalEgressStarted: Bool
        let transcriptionStarted: Bool
    }

    struct Track: Decodable {
        let role: String
        let transportRole: String
        let sourceKind: String
        let mediaScribeField: String
        let fileName: String
        let format: String
        let sampleRate: Int
        let channelCount: Int
        let bitsPerSample: Int
        let timelineStartMs: Int
        let timelineAligned: Bool
        let aacPresentationFrameDelta: Int?
        let asrInput: Bool
    }

    let schemaVersion: String
    let package: Package
    let tracks: [Track]
    let forbiddenFields: [String]
}

func findRepositoryRoot(startingAt startURL: URL) throws -> URL {
    var candidate = startURL.standardizedFileURL

    while true {
        let fixture = candidate.appendingPathComponent("tests/macos/contract/recording-session-evidence.json")
        if FileManager.default.fileExists(atPath: fixture.path) {
            return candidate
        }

        let parent = candidate.deletingLastPathComponent()
        if parent.path == candidate.path {
            throw ValidationError(description: "Could not locate repository root from \(startURL.path)")
        }
        candidate = parent
    }
}

let repositoryRoot = try findRepositoryRoot(startingAt: URL(fileURLWithPath: FileManager.default.currentDirectoryPath))
let forbiddenFixtureURL = repositoryRoot.appendingPathComponent("tests/macos/contract/diagnostic-forbidden-fields.json")
let activeV5ProductSourcePaths = [
    "apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift",
    "apps/macos/RecApp/Sources/Capture/CanonicalRecordingWriter.swift",
    "apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift",
    "apps/macos/RecApp/Sources/Capture/LocalRecordingStore.swift",
    "apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift",
    "apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift",
    "apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleCoreService.swift",
    "apps/macos/RecApp/App/TwoBrainRecApp.swift"
]

func decode<T: Decodable>(_ type: T.Type, from url: URL) throws -> T {
    let data = try Data(contentsOf: url)
    return try JSONDecoder().decode(type, from: data)
}

func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() {
        throw ValidationError(description: message)
    }
}

func validateV5ProductSurface() throws {
    let retiredProcessingTerms = [
        ["A", "EC"].joined(),
        ["Apple", "Voice", "Processing"].joined(),
        ["Web", "RTC"].joined(),
        ["Leak", "age"].joined(),
        ["echo", "-cleanup"].joined()
    ]

    for relativePath in activeV5ProductSourcePaths {
        let source = try String(
            contentsOf: repositoryRoot.appendingPathComponent(relativePath),
            encoding: .utf8
        )
        for retiredTerm in retiredProcessingTerms {
            try require(
                !source.contains(retiredTerm),
                "Active v5 product source must not retain retired capture processing: \(relativePath)"
            )
        }
    }

    let writerPath = "apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift"
    let writer = try String(contentsOf: repositoryRoot.appendingPathComponent(writerPath), encoding: .utf8)
    try require(
        writer.contains("meeting-transcription.wav") && writer.contains("meeting-review.m4a"),
        "Active v5 writer must publish the canonical WAV and review M4A artifacts"
    )
    for historicalArtifactName in [["mic", ".wav"].joined(), ["incoming", ".wav"].joined()] {
        try require(
            !writer.contains(historicalArtifactName),
            "Active v5 writer must not publish a historical per-source artifact"
        )
    }

    let artifactValidatorPath = "apps/macos/Scripts/validate-system-audio-capture-pivot.sh"
    let artifactValidator = try String(
        contentsOf: repositoryRoot.appendingPathComponent(artifactValidatorPath),
        encoding: .utf8
    )
    try require(
        artifactValidator.contains("meeting-transcription.wav") &&
            artifactValidator.contains("meeting-review.m4a"),
        "Active v5 artifact validator must require the canonical final members"
    )
    for historicalArtifactName in [["mic", ".wav"].joined(), ["incoming", ".wav"].joined()] {
        try require(
            !artifactValidator.contains(historicalArtifactName),
            "Active v5 artifact validator must not accept historical per-source artifacts"
        )
    }
}

func validateDiagnosticForbiddenFixtures() throws {
    let fixture = try decode(ForbiddenFixtureFile.self, from: forbiddenFixtureURL)
    let forbiddenKeys = Set(fixture.forbiddenKeys)
    let redactorKeys = DiagnosticRedactor.forbiddenKeys

    try require(
        forbiddenKeys.isSubset(of: redactorKeys),
        "DiagnosticRedactor is missing forbidden keys from fixture: \(forbiddenKeys.subtracting(redactorKeys))"
    )

    try require(
        fixture.forbiddenPatterns.contains("-----BEGIN PRIVATE KEY-----"),
        "Forbidden pattern fixture must include private-key marker"
    )
    try require(
        fixture.forbiddenPatterns.contains("Authorization: Bearer "),
        "Forbidden pattern fixture must include bearer-token marker"
    )

    let redactor = DiagnosticRedactor()
    let redactionResult = redactor.redact([
        "sessionToken": "abc",
        "safeStatus": "route_failed",
        "leakyHeader": "Authorization: Bearer abc",
        "leakyPrivateKey": "-----BEGIN PRIVATE KEY-----",
        "leakyApiHeader": "X-API-Key: abc",
        "leakySignedUrl": "https://example.presigned/upload"
    ])
    try require(
        redactionResult.status == .blockedSensitiveContent,
        "DiagnosticRedactor must report blocked sensitive content"
    )
    try require(
        redactionResult.manifest["sessionToken"] == nil,
        "DiagnosticRedactor must remove forbidden keys"
    )
    try require(
        redactionResult.manifest["leakyHeader"] == nil,
        "DiagnosticRedactor must remove forbidden value patterns"
    )
    try require(
        redactionResult.manifest["leakyPrivateKey"] == nil,
        "DiagnosticRedactor must remove private-key markers"
    )
    try require(
        redactionResult.manifest["leakyApiHeader"] == nil,
        "DiagnosticRedactor must remove API-key header patterns"
    )
    try require(
        redactionResult.manifest["leakySignedUrl"] == nil,
        "DiagnosticRedactor must remove presigned URL patterns"
    )
    try require(
        redactionResult.manifest["safeStatus"] == "route_failed",
        "DiagnosticRedactor must keep allowed manifest fields"
    )

    let recursiveResult = redactor.redact([
        "appVersion": .string("0.1.0"),
        "capturePermissions": .object([
            "microphone": .string("granted"),
            "systemAudio": .string("granted"),
            "sessionToken": .string("nested-secret"),
            "samples": .array([
                .object([
                    "source": .string("system_audio"),
                    "temporaryUploadUrl": .string("https://example.presigned/upload")
                ]),
                .object([
                    "source": .string("microphone"),
                    "status": .string("granted")
                ])
            ])
        ]),
        "contactName": .string("Not allowed in default diagnostics")
    ])

    try require(
        recursiveResult.status == .blockedSensitiveContent,
        "Recursive DiagnosticRedactor must report blocked nested or non-allowlisted content"
    )
    try require(
        recursiveResult.manifest["contactName"] == nil,
        "Recursive DiagnosticRedactor must drop non-allowlisted top-level fields"
    )
    guard case .object(let capturePermissions)? = recursiveResult.manifest["capturePermissions"] else {
        throw ValidationError(description: "Recursive DiagnosticRedactor must preserve allowed object fields")
    }
    try require(
        capturePermissions["sessionToken"] == nil,
        "Recursive DiagnosticRedactor must remove nested forbidden keys"
    )
    guard case .array(let samples)? = capturePermissions["samples"],
          case .object(let firstSample)? = samples.first else {
        throw ValidationError(description: "Recursive DiagnosticRedactor must preserve safe array objects")
    }
    try require(
        firstSample["temporaryUploadUrl"] == nil,
        "Recursive DiagnosticRedactor must remove forbidden keys inside arrays"
    )
}

func validateRecordingSessionEvidenceFixture() throws {
    let url = repositoryRoot.appendingPathComponent("tests/macos/contract/recording-session-evidence.json")
    let fixture = try decode(RecordingSessionEvidenceFixtureFile.self, from: url)

    try require(
        fixture.schema == "recording-session-evidence-v1",
        "Recording session evidence fixture must use v1 schema"
    )
    try require(
        Set(fixture.requiredEventTypes).isSuperset(of: [
            RecordingEvidenceEventType.startRequested.rawValue,
            RecordingEvidenceEventType.startBlocked.rawValue,
            RecordingEvidenceEventType.started.rawValue,
            RecordingEvidenceEventType.stopRequested.rawValue,
            RecordingEvidenceEventType.stopped.rawValue,
            RecordingEvidenceEventType.failed.rawValue,
            RecordingEvidenceEventType.indicatorLost.rawValue,
            RecordingEvidenceEventType.storageBlocked.rawValue
        ]),
        "Recording evidence fixture must require all lifecycle and fail-closed events"
    )
    try require(
        Set(fixture.requiredFields).isSuperset(of: [
            "sessionId",
            "eventType",
            "occurredAt",
            "initiator",
            "captureState",
            "indicatorState",
            "stopActionAvailable",
            "blockedReason",
            "recoveryAction",
            "diagnosticSafe"
        ]),
        "Recording evidence fixture must require safe lifecycle fields"
    )
    try require(
        Set(fixture.forbiddenFields).isSuperset(of: [
            "rawAudio",
            "transcriptText",
            "meetingContent",
            "credentials",
            "tokens",
            "signedUrls",
            "password",
            "mediaScribeCredentials",
            "langfuseContentTrace"
        ]),
        "Recording evidence fixture must forbid raw content, secrets, and external trace content"
    )
    try require(
        Set(fixture.forbiddenExternalActivity) == ["upload", "mediascribe", "langfuse", "dashboard_publish"],
        "Recording evidence fixture must forbid external activity in this slice"
    )
}

func validateLocalRecordingManifestFixture() throws {
    let url = repositoryRoot.appendingPathComponent("tests/macos/contract/local-recording-manifest.json")
    let fixture = try decode(LocalRecordingManifestFixtureFile.self, from: url)

    try require(
        fixture.schema == LocalRecordingManifest.schemaVersion,
        "Local recording manifest fixture must use current local recording manifest schema"
    )
    try require(
        Set(fixture.requiredFields).isSuperset(of: [
            "sessionId",
            "createdAt",
            "startedAt",
            "stoppedAt",
            "status",
            "directoryId",
            "manifestFileName",
            "transcriptionReadiness",
            "mediaScribeSourceMode",
            "tracks",
            "externalEgressStarted",
            "transcriptionStarted",
            "diagnosticSafe"
        ]),
        "Local recording manifest must require safe session fields"
    )
    try require(
        Set(fixture.requiredTrackRoles) == Set([
            AudioTrackRole.mixedMeetingAudio.rawValue,
            AudioTrackRole.reviewPlayback.rawValue
        ]),
        "Current local recording manifests must require canonical transcription and playback roles"
    )
    try require(
        Set(fixture.allowedStatuses) == Set([
            LocalRecordingSessionStatus.saved.rawValue,
            LocalRecordingSessionStatus.degraded.rawValue,
            LocalRecordingSessionStatus.blocked.rawValue,
            LocalRecordingSessionStatus.failed.rawValue
        ]),
        "Local recording manifest must allow saved, degraded, blocked, and failed terminal statuses"
    )
    try require(
        Set(fixture.allowedReadinessStates) == Set([
            TranscriptionReadinessState.ready.rawValue,
            TranscriptionReadinessState.degraded.rawValue,
            TranscriptionReadinessState.failed.rawValue
        ]),
        "Current local recording manifests must allow only current readiness states"
    )
    try require(
        Set(fixture.requiredTrackFields).isSuperset(of: [
            "mediaScribeField",
            "sourceKind",
            "format",
            "sampleRate",
            "channelCount",
            "bitsPerSample",
            "timelineStartMs",
            "timelineAligned",
            "sha256"
        ]),
        "Local recording manifest must require MediaScribe-ready track metadata"
    )
    try require(
        Set(fixture.forbiddenFields).isSuperset(of: [
            "rawAudio",
            "transcriptText",
            "meetingContent",
            "credentials",
            "tokens",
            "signedUrls",
            "password",
            "apiKey",
            "absolutePath",
            "liveSecretPath"
        ]),
        "Local recording manifest must forbid raw content, secrets, and live paths"
    )
    try require(
        Set(fixture.forbiddenExternalActivity) == ["upload", "mediascribe", "langfuse", "dashboard_publish"],
        "Local recording manifest must forbid external activity in this slice"
    )
}

func validateRecordingArtifactFormatFixture() throws {
    let url = repositoryRoot.appendingPathComponent("tests/macos/contract/recording-artifact-format.json")
    let fixture = try decode(RecordingArtifactFormatFixtureFile.self, from: url)

    try require(
        fixture.schemaVersion == "recording-artifact-format.v2",
        "Recording artifact format fixture must use v2 schema"
    )
    try require(
        fixture.package.manifestSchemaVersion == LocalRecordingManifest.schemaVersion &&
            fixture.package.manifestFileName == "manifest.json" &&
            Set(fixture.package.requiredFiles) == Set(["meeting-transcription.wav", "meeting-review.m4a"]) &&
            Set(fixture.package.exactFinalMembers) == Set([
                "manifest.json",
                "meeting-transcription.wav",
                "meeting-review.m4a"
            ]) &&
            fixture.package.mediaScribeSourceMode == "single_wav_v1" &&
            fixture.package.serverSourceKind == "initial_mixed_recording" &&
            fixture.package.transportRoles == ["manifest", "media", "playback"] &&
            fixture.package.externalEgressStarted == false &&
            fixture.package.transcriptionStarted == false,
        "Current recording package must define exactly the v5 manifest, canonical WAV, playback M4A, and no egress"
    )
    let tracksByRole = Dictionary(uniqueKeysWithValues: fixture.tracks.map { ($0.role, $0) })
    try require(
        fixture.tracks.count == 2 &&
            tracksByRole[AudioTrackRole.mixedMeetingAudio.rawValue]?.transportRole == DesktopUploadTransportRole.media.rawValue &&
            tracksByRole[AudioTrackRole.mixedMeetingAudio.rawValue]?.mediaScribeField == MediaScribeTrackField.mediaFile.rawValue &&
            tracksByRole[AudioTrackRole.mixedMeetingAudio.rawValue]?.sourceKind == AudioCaptureSourceKind.canonicalMix.rawValue &&
            tracksByRole[AudioTrackRole.mixedMeetingAudio.rawValue]?.fileName == "meeting-transcription.wav" &&
            tracksByRole[AudioTrackRole.mixedMeetingAudio.rawValue]?.asrInput == true,
        "Canonical WAV must be the one and only v5 ASR input"
    )
    try require(
        tracksByRole[AudioTrackRole.reviewPlayback.rawValue]?.transportRole == DesktopUploadTransportRole.playback.rawValue &&
            tracksByRole[AudioTrackRole.reviewPlayback.rawValue]?.mediaScribeField == MediaScribeTrackField.playbackFile.rawValue &&
            tracksByRole[AudioTrackRole.reviewPlayback.rawValue]?.sourceKind == AudioCaptureSourceKind.canonicalMix.rawValue &&
            tracksByRole[AudioTrackRole.reviewPlayback.rawValue]?.fileName == "meeting-review.m4a" &&
            tracksByRole[AudioTrackRole.reviewPlayback.rawValue]?.asrInput == false,
        "Playback M4A must be required for v5 package playback and never be an ASR input"
    )
    let media = tracksByRole[AudioTrackRole.mixedMeetingAudio.rawValue]
    let playback = tracksByRole[AudioTrackRole.reviewPlayback.rawValue]
    try require(
        media?.format == "wav-pcm-s16le" &&
            media?.sampleRate == 16_000 &&
            media?.channelCount == 1 &&
            media?.bitsPerSample == 16 &&
            media?.timelineStartMs == 0 &&
            media?.timelineAligned == true,
        "Canonical ASR artifact must be PCM16 mono 16k from the common timeline"
    )
    try require(
        playback?.format == "m4a-aac-lc" &&
            playback?.sampleRate == 48_000 &&
            playback?.channelCount == 1 &&
            playback?.aacPresentationFrameDelta.map {
                abs($0) <= Int(LocalRecordingTrack.maximumAACPresentationDeltaFrames)
            } == true &&
            playback?.timelineStartMs == 0 &&
            playback?.timelineAligned == true,
        "Playback artifact must record bounded AAC presentation compensation from the common timeline"
    )
    try require(
        Set(fixture.forbiddenFields).isSuperset(of: [
            "rawAudio",
            "transcriptText",
            "meetingContent",
            "credentials",
            "tokens",
            "signedUrls",
            "password",
            "apiKey",
            "mediaScribeCredentials",
            "langfuseContentTrace"
        ]),
        "Recording artifact fixture must forbid raw content, secrets, and trace content"
    )
}

func validatePlatformGate() throws {
    let minimum = OperatingSystemVersion(majorVersion: 14, minorVersion: 5, patchVersion: 0)
    try require(
        PlatformSupport.minimumSupportedMacOS.majorVersion == minimum.majorVersion &&
            PlatformSupport.minimumSupportedMacOS.minorVersion == minimum.minorVersion &&
            PlatformSupport.minimumSupportedMacOS.patchVersion == minimum.patchVersion,
        "PlatformSupport minimum macOS must be 14.5"
    )
    try require(
        PlatformSupport.currentArchitecture != .unknown,
        "This validation command must run on a supported macOS architecture"
    )
}

func validateCaptureSafetyInvariant() throws {
    let unsafeActiveSession = CaptureSession(
        id: "session-1",
        mode: .audioRecording,
        state: .active,
        sourceAppEligibility: .eligible,
        policySnapshotRef: "policy-1",
        triggerEvidence: [:],
        visibleIndicatorState: .hidden,
        stopActionAvailable: false,
        bufferSummaryId: nil,
        startedAt: nil,
        stoppedAt: nil
    )

    try require(
        !CaptureSessionSafetyValidator.validate(unsafeActiveSession),
        "Active capture must not validate when hidden and missing one-action stop"
    )
}

func validateDiagnosticBundleService() throws {
    let bundle = try DiagnosticBundleService().buildBundle(
        DiagnosticBundleInput(
            schemaVersion: "0.1.0",
            createdAt: Date(timeIntervalSince1970: 1_777_777_777),
            manifest: [
                "appVersion": .string("0.1.0"),
                "capturePermissions": .object([
                    "microphone": .string("granted"),
                    "systemAudio": .string("granted"),
                    "password": .string("should-be-removed")
                ]),
                "meetingTitle": .string("should-be-removed")
            ]
        )
    )

    try require(
        bundle.redactionState == .blockedSensitiveContent,
        "DiagnosticBundleService must record blocked_sensitive_content when redaction removes fields"
    )
    try require(
        bundle.manifest["schemaVersion"] == .string("0.1.0"),
        "DiagnosticBundleService must include schemaVersion"
    )
    try require(
        bundle.manifest["contentHash"] != nil,
        "DiagnosticBundleService must include contentHash"
    )
    try require(
        bundle.manifest["meetingTitle"] == nil,
        "DiagnosticBundleService must remove non-allowlisted top-level content"
    )
    guard case .object(let capturePermissions)? = bundle.manifest["capturePermissions"] else {
        throw ValidationError(description: "DiagnosticBundleService must preserve safe capture permission metadata")
    }
    try require(
        capturePermissions["password"] == nil,
        "DiagnosticBundleService must remove nested forbidden fields"
    )
}

func validateLocalRecordingDiagnosticBundleNoEgressTruth() throws {
    let manifest = LocalRecordingManifest(
        schemaVersion: LocalRecordingManifest.schemaVersion,
        sessionId: "contract-local-recording-diagnostics",
        createdAt: Date(timeIntervalSince1970: 1),
        startedAt: Date(timeIntervalSince1970: 1),
        stoppedAt: Date(timeIntervalSince1970: 2),
        status: .saved,
        directoryId: "contract-safe-dir",
        transcriptionReadiness: .ready,
        mediaScribeSourceMode: "single_wav_v1",
        canonicalMixProfile: LocalRecordingManifest.canonicalMixProfileVersion,
        tracks: [
            LocalRecordingTrack(
                trackId: "canonical-media",
                role: .mixedMeetingAudio,
                sourceKind: .canonicalMix,
                mediaScribeField: .mediaFile,
                status: .saved,
                fileName: "meeting-transcription.wav",
                format: "wav-pcm-s16le",
                sampleRate: 16_000,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 1000,
                byteCount: 100,
                sha256: String(repeating: "0", count: 64),
                frameCount: 16_000,
                timelineStartMs: 0,
                timelineAligned: true
            ),
            LocalRecordingTrack(
                trackId: "review-playback",
                role: .reviewPlayback,
                sourceKind: .canonicalMix,
                mediaScribeField: .playbackFile,
                status: .saved,
                fileName: "meeting-review.m4a",
                format: "m4a-aac-lc",
                sampleRate: 48_000,
                channelCount: 1,
                bitsPerSample: 0,
                durationMs: 1000,
                byteCount: 100,
                sha256: String(repeating: "0", count: 64),
                frameCount: 48_000,
                aacPresentationFrameDelta: 0,
                timelineStartMs: 0,
                timelineAligned: true
            )
        ]
    )

    let bundle = try DiagnosticBundleService().buildLocalRecordingBundle(
        manifest: manifest,
        manifestOverrides: [
            "rawAudio": .string("not allowed"),
            "signedUrl": .string("not allowed")
        ]
    )

    try require(
        bundle.redactionState == .blockedSensitiveContent,
        "Local recording diagnostic bundle must report blocked sensitive content when overrides include forbidden fields"
    )
    try require(
        bundle.manifest["rawAudio"] == nil && bundle.manifest["signedUrl"] == nil,
        "Local recording diagnostic bundle must remove raw audio and signed URL fields"
    )

    guard case .object(let diagnosticManifest)? = bundle.manifest["localRecordingManifest"] else {
        throw ValidationError(description: "Local recording diagnostic bundle must include localRecordingManifest")
    }
    guard case .object(let summary)? = bundle.manifest["localRecordingEvidence"] else {
        throw ValidationError(description: "Local recording diagnostic bundle must include localRecordingEvidence")
    }

    try require(
        diagnosticManifest["externalEgressStarted"] == .bool(false) &&
            diagnosticManifest["transcriptionStarted"] == .bool(false) &&
            diagnosticManifest["diagnosticSafe"] == .bool(true),
        "Local recording diagnostic manifest must preserve no-egress and diagnosticSafe truth"
    )
    try require(
        summary["diagnosticSafe"] == .bool(true),
        "Local recording diagnostic summary must preserve diagnosticSafe truth"
    )
}


func validateSystemAudioPermissionFailClosed() async throws {
    let gate = SystemAudioPermissionGate(clock: { Date(timeIntervalSince1970: 1) })
    let deniedSystemAudio = gate.evaluate(microphone: .granted, systemAudio: .denied)
    try require(
        !deniedSystemAudio.allowsAcceptedRecording &&
            deniedSystemAudio.outcome == .blocked &&
            deniedSystemAudio.manifestFailureReason == .permissionDenied,
        "Permission gate must block accepted recording when system-audio permission is denied"
    )

    let deniedMicrophone = gate.evaluate(microphone: .denied, systemAudio: .granted)
    try require(
        !deniedMicrophone.allowsAcceptedRecording &&
            deniedMicrophone.outcome == .blocked &&
            deniedMicrophone.manifestFailureReason == .permissionDenied,
        "Permission gate must block accepted recording when microphone permission is denied"
    )

    let service = SystemAudioCaptureService(runtime: NoopSystemAudioCaptureRuntime())
    do {
        _ = try await service.start(
            sessionId: "contract-permission-denied",
            permissionState: .denied,
            scopeApproval: contractScopeApproval()
        )
        throw ValidationError(description: "SystemAudioCaptureService must not start when permission is denied")
    } catch SystemAudioCaptureServiceError.permissionDenied {
        let running = await service.isRunning
        try require(!running, "Denied system-audio start must leave service stopped")
    }

}

func validateSystemAudioStartTimeoutCleanupOrdering() async throws {
    let failingService = SystemAudioCaptureService(
        runtime: FailingContractRuntime(),
        runtimeStartTimeoutSeconds: 1
    )
    do {
        _ = try await failingService.start(
            sessionId: "contract-immediate-failure",
            permissionState: .granted,
            scopeApproval: contractScopeApproval()
        )
        throw ValidationError(description: "Immediate system-audio runtime failure must not become an accepted start")
    } catch SystemAudioCaptureServiceError.runtimeStartFailed {
        let runningAfterImmediateFailure = await failingService.isRunning
        try require(
            !runningAfterImmediateFailure,
            "Immediate runtime start failure must leave service stopped"
        )
    }

    let runtime = RecoveringSlowStartingContractRuntime(firstStartDelaySeconds: 0.2)
    let service = SystemAudioCaptureService(
        runtime: runtime,
        runtimeStartTimeoutSeconds: 0.05
    )

    do {
        _ = try await service.start(
            sessionId: "contract-first-timeout",
            permissionState: .granted,
            scopeApproval: contractScopeApproval()
        )
        throw ValidationError(description: "Slow system-audio runtime start must fail with runtimeStartFailed")
    } catch SystemAudioCaptureServiceError.runtimeStartFailed {
        let runningAfterTimeout = await service.isRunning
        try require(
            !runningAfterTimeout,
            "Timed-out system-audio start must leave service stopped"
        )
    }

    let retry = Task {
        try await service.start(
            sessionId: "contract-second-start",
            permissionState: .granted,
            scopeApproval: contractScopeApproval()
        )
    }
    try? await Task.sleep(nanoseconds: 100_000_000)
    try require(
        runtime.startCount == 1,
        "Retry must wait for timed-out runtime start cleanup before starting a new runtime"
    )
    let runningWhileCleanupPending = await service.isRunning
    try require(
        !runningWhileCleanupPending,
        "Retry must not mark service running while timed-out runtime cleanup is pending"
    )

    let secondSession = try await retry.value
    try require(
        secondSession.sessionId == "contract-second-start",
        "Retry after timed-out runtime cleanup must start the requested second session"
    )
    try require(
        runtime.startCount == 2 && runtime.stopCount >= 2,
        "Timed-out runtime cleanup must stop the stale runtime before retry starts"
    )
    let stopCountBeforeAcceptedStop = runtime.stopCount
    let runningAfterRetry = await service.isRunning
    try require(
        runningAfterRetry,
        "Retry after timed-out runtime cleanup must leave the second session running"
    )

    _ = try await service.stop()
    try require(
        runtime.stopCount == stopCountBeforeAcceptedStop + 1,
        "Stopping the accepted retry session must stop exactly that active runtime"
    )
}

func validateAppStopFailureFailClosedSourceInvariant() throws {
    let appSourceURL = repositoryRoot.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift")
    let source = try String(contentsOf: appSourceURL, encoding: .utf8)
    let permissionSourceURL = repositoryRoot.appendingPathComponent("apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift")
    let permissionSource = try String(contentsOf: permissionSourceURL, encoding: .utf8)

    try require(
        source.contains("private func recordingStopFailureCategory(for error: Error) -> RecordingStartBlocker"),
        "App stop failure path must classify stop failures separately from start failures"
    )
    try require(
        source.contains("await finalizeLocalRecordingForFailure(") &&
            source.contains("reason: \"stop_failure_cleanup\"") &&
            source.contains("failureReason: releasedSystemAudioSession?.failureReason ?? .none"),
        "App stop failure path must attempt fail-closed local writer cleanup"
    )
    try require(
        source.contains("reason: \"start_failure_cleanup\"") &&
            source.contains("let releasedSystemAudioSession = try? await systemAudioCaptureService.stop()") &&
            source.contains("failureReason: releasedSystemAudioSession?.failureReason ?? .none"),
        "App start failure cleanup must preserve system-audio stop failure truth"
    )
    try require(
        source.contains("private func releaseCaptureResourcesForAppExit() async") &&
            source.contains("let releasedSystemAudioSession = await systemAudioCaptureService.releaseForTermination()") &&
            source.contains("await finalizeLocalRecordingForAppExit(") &&
            source.contains("failureReason: releasedSystemAudioSession?.failureReason ?? .none"),
        "App exit cleanup must preserve system-audio termination failure truth"
    )
    try require(
        source.contains("try await localRecordingWriter.stopAsync(failureReason: failureReason)"),
        "Local failure finalization must pass forced failure reason into manifest creation"
    )
    try require(
        source.contains("failureReason=\\(manifest.failureReason.rawValue)"),
        "App cleanup logging must include manifest failureReason"
    )
    try require(
        source.contains("localRecordingActive = false") &&
            !source.contains("localRecordingActive = await localRecordingWriter.isRecordingAsync()"),
        "App stop failure path must not leave UI recording state active after failed stop"
    )
    try require(
        source.contains("detail: \"category=\\(failureCategory.rawValue) error=\\(error)\""),
        "App stop failure logging must include the classified failure category"
    )
    try require(
        source.contains("private func presentPermissionRecoveryAfterSystemAudioRuntimeFailure(_ error: Error)") &&
            source.contains("captureError == .runtimeStartFailed") &&
            source.contains("systemAudioPermissionAuthorizer.currentPermissionState() == .granted") &&
            source.contains("presentPermissionRecoveryAfterSystemAudioRuntimeFailure(error)"),
        "A granted-but-failed system-audio runtime must offer relaunch recovery"
    )
    try require(
        permissionSource.contains("func verifyCurrentPermission() async -> CapturePermissionState") &&
            permissionSource.contains("SCShareableContent.excludingDesktopWindows") &&
            permissionSource.contains("return await verifyCurrentPermission()"),
        "System-audio permission recovery must verify the functional ScreenCaptureKit path"
    )

    guard let clearBlockerRange = source.range(of: "recordingBlocker = nil"),
          let beginPreparingRange = source.range(of: "let preparing = if let meetingDetectionTarget"),
          let microphonePromptRange = source.range(of: "let microphoneSession = await microphoneCaptureService.requestPermissionAndPreflight"),
          let systemAudioPromptRange = source.range(of: "let observedSystemAudioPermissionState = await systemAudioPermissionAuthorizer.requestPermission()"),
          source.contains("try captureController.beginDetectorAssistedPreparing"),
          source.contains("try captureController.beginPreparing")
    else {
        throw ValidationError(description: "App start path must expose blocker clearing, preparing state, and permission prompts")
    }
    try require(
        clearBlockerRange.lowerBound < beginPreparingRange.lowerBound &&
            beginPreparingRange.lowerBound < microphonePromptRange.lowerBound &&
            microphonePromptRange.lowerBound < systemAudioPromptRange.lowerBound,
        "App start path must clear stale blockers and show preparing state before permission prompts"
    )
}

func validateRecordingMetersUseLocalWriterInvariant() throws {
    let appSourceURL = repositoryRoot.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift")
    let source = try String(contentsOf: appSourceURL, encoding: .utf8)

    try require(
        source.contains("let recordingLevels = await writer.currentLevelsAsync()") &&
            source.contains("liveRecordingLevels = recordingLevels"),
        "Recording UI meters must be driven by LocalRecordingWriter levels"
    )
    try require(
        source.contains("guard localRecordingActive, !recordingStartInProgress, !recordingStopInProgress else") &&
            source.contains("liveRecordingLevels = .inactive"),
        "Recording UI meters must reset to inactive outside active local recording"
    )
}

func validateManualGateExitCleanupInvariant() throws {
    let scriptURL = repositoryRoot.appendingPathComponent("apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh")
    let source = try String(contentsOf: scriptURL, encoding: .utf8)

    try require(
        source.contains("cleanup_runtime()") &&
            source.contains("trap - EXIT") &&
            source.contains("quit_app") &&
            source.contains("stop_caffeinate"),
        "Manual gate cleanup must quit the packaged app and stop caffeinate on early exits"
    )
    try require(
        source.contains("trap 'cleanup_runtime' EXIT"),
        "Manual gate must install the full runtime cleanup trap after holding the wake assertion"
    )
    try require(
        source.contains("baselineCoreaudiodCpuGate") &&
            source.contains("maxCoreaudiodCpuPercent") &&
            source.contains("beforeAppLaunch=true"),
        "Manual gate must block hot coreaudiod baseline before launching the packaged app"
    )
    guard let baselineRange = source.range(of: "run_baseline_cpu"),
          let launchRange = source.range(of: "launch_packaged_app")
    else {
        throw ValidationError(description: "Manual gate must define baseline and packaged app launch steps")
    }
    try require(
        baselineRange.lowerBound < launchRange.lowerBound,
        "Manual gate must evaluate baseline CPU before launching the packaged app"
    )
}


func contractScopeApproval() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "contract-scope",
        scopeKind: .display,
        sourceDisplayName: "Current Display",
        approvedAt: Date(timeIntervalSince1970: 9),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private final class InfiniteContractSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        guard capacity > 0 else { return 0 }
        for index in 0..<capacity {
            destination[index] = 0.25
        }
        return capacity
    }
}

private final class FiniteContractSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    private let lock = NSLock()
    private var samples: [Float]
    private var offset = 0

    init(samples: [Float]) {
        self.samples = samples
    }

    func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        lock.withLock {
            guard capacity > 0, offset < samples.count else { return 0 }
            let count = min(capacity, samples.count - offset)
            for index in 0..<count {
                destination[index] = samples[offset + index]
            }
            offset += count
            return count
        }
    }
}

private final class RecoveringSlowStartingContractRuntime: SystemAudioCaptureRuntime, @unchecked Sendable {
    private let firstStartDelaySeconds: TimeInterval
    private let lock = NSLock()
    private var protectedStartCount = 0
    private var protectedStopCount = 0

    init(firstStartDelaySeconds: TimeInterval) {
        self.firstStartDelaySeconds = firstStartDelaySeconds
    }

    var startCount: Int {
        lock.withLock { protectedStartCount }
    }

    var stopCount: Int {
        lock.withLock { protectedStopCount }
    }

    func start() async throws {
        let currentStart = lock.withLock {
            protectedStartCount += 1
            return protectedStartCount
        }

        if currentStart == 1 {
            try? await Task.sleep(nanoseconds: UInt64(firstStartDelaySeconds * 1_000_000_000))
        }
    }

    func stop() async {
        lock.withLock {
            protectedStopCount += 1
        }
    }
}

private final class FailingContractRuntime: SystemAudioCaptureRuntime, @unchecked Sendable {
    func start() async throws {
        throw SystemAudioCaptureServiceError.runtimeStartFailed
    }

    func stop() async {}
}

func validateDesktopUploadQueueContract() throws {
    try require(
        DesktopUploadTransportRole.role(forLocalTrackRole: .mixedMeetingAudio) == .media,
        "Desktop upload queue must map the canonical WAV to the backend media role"
    )
    try require(
        DesktopUploadTransportRole.role(forLocalTrackRole: .reviewPlayback) == .playback,
        "Desktop upload queue must map the review M4A to the backend playback role"
    )
    try require(
        DiagnosticRedactor.forbiddenKeys.isSuperset(of: [
            "rawAudio",
            "transcriptText",
            "meetingContent",
            "signedUrl",
            "uploadToken",
            "bearerToken",
            "uploadBearerToken",
            "authorization",
            "mediaScribeCredentials",
            "objectStorageCredentials"
        ]),
        "Desktop upload diagnostics must forbid raw content, credentials, tokens, and signed URLs"
    )

    let profile = ArtifactCompletenessProfile(
        schemaVersion: LocalRecordingManifest.schemaVersion,
        manifestPresent: true,
        microphonePresent: true,
        systemAudioPresent: true,
        manifestSha256: String(repeating: "a", count: 64),
        microphoneSha256: String(repeating: "b", count: 64),
        systemAudioSha256: String(repeating: "c", count: 64),
        manifestSizeBytes: 128,
        microphoneSizeBytes: 256,
        systemAudioSizeBytes: 512,
        durationSeconds: 1,
        trackCompleteness: [
            UploadTrackCompleteness(
                transportRole: .manifest,
                fileName: "manifest.json",
                present: true,
                byteCount: 128,
                sha256: String(repeating: "a", count: 64)
            ),
            UploadTrackCompleteness(
                transportRole: .media,
                fileName: "meeting-transcription.wav",
                present: true,
                byteCount: 256,
                sha256: String(repeating: "b", count: 64)
            ),
            UploadTrackCompleteness(
                transportRole: .playback,
                fileName: "meeting-review.m4a",
                present: true,
                byteCount: 512,
                sha256: String(repeating: "c", count: 64)
            )
        ],
        isUploadable: true
    )
    try require(profile.isV5Package, "Desktop upload contract fixture must be a v5 package")
    let terminal = DesktopUploadQueueItem(
        id: "queue",
        sessionId: "session",
        directoryId: "directory",
        directoryPath: "/private/directory",
        manifestPath: "/private/directory/manifest.json",
        microphonePath: "/private/directory/meeting-transcription.wav",
        systemAudioPath: "/private/directory/meeting-review.m4a",
        state: .uploaded,
        retryMode: .terminal,
        retentionDeadline: Date(timeIntervalSince1970: 100),
        createdAt: Date(timeIntervalSince1970: 1),
        updatedAt: Date(timeIntervalSince1970: 1),
        artifactProfile: profile,
        retentionDecision: RetentionDecision(
            decision: .terminalUploaded,
            decidedAt: Date(timeIntervalSince1970: 1),
            reason: "server_finalized_upload",
            localArtifactsRetained: true,
            policyReference: "server_truth.finalized"
        )
    )
    try require(
        terminal.withTransition(to: .retrying, now: Date(timeIntervalSince1970: 2)).state == .uploaded,
        "Desktop upload terminal truth must not regress to retrying"
    )
}

func validateMeetingMuteTruthContract() throws {
    try require(
        DiagnosticRedactor.forbiddenKeys.isSuperset(of: [
            "rawAudio",
            "audioSnippet",
            "transcriptText",
            "meetingContent",
            "meetingNotes",
            "participantSpeech",
            "signedUrl",
            "authorization"
        ]),
        "Meeting mute-truth diagnostics must forbid raw content, credentials, and signed URLs"
    )

    let pauseSegment = ProductPrivacySegment(
        segmentId: "contract-segment",
        sessionId: "contract-session",
        control: .pause,
        startedAt: Date(timeIntervalSince1970: 10),
        endedAt: Date(timeIntervalSince1970: 12),
        startMonotonicMs: 1000,
        endMonotonicMs: 3000
    )
    let evidence = MeetingMuteTruthEvidence(
        evidenceId: "contract-evidence",
        sessionId: "contract-session",
        targetId: TargetMuteCapability.chromeTelemost.targetId,
        targetDisplayName: TargetMuteCapability.chromeTelemost.targetDisplayName,
        source: .productPause,
        status: .meetingMuteUnproven,
        freshness: .unavailable,
        limitationCopyShown: true,
        recordedAt: Date(timeIntervalSince1970: 10)
    )
    let pauseDecision = MuteTruthDecision.mvpDecision(
        sessionId: "contract-session",
        privacySegments: [pauseSegment],
        targetEvidence: [evidence],
        targetCapability: .chromeTelemost,
        decidedAt: Date(timeIntervalSince1970: 12)
    )
    try require(
        pauseDecision.decision == .meetingMuteUnproven,
        "Product Pause must not become a meeting-app mute-respecting claim"
    )
    try require(
        pauseDecision.reason == .productPauseSegmentsPresent,
        "Product Pause decision must preserve product-owned privacy segment reason"
    )

    let unsupportedDecision = MuteTruthDecision.mvpDecision(
        sessionId: "contract-session",
        privacySegments: [],
        targetEvidence: [],
        targetCapability: .unknown,
        decidedAt: Date(timeIntervalSince1970: 12)
    )
    try require(
        unsupportedDecision.decision == .unsupported,
        "Unsupported meeting targets must fail closed"
    )

    let redaction = DiagnosticRedactor().redact([
        "privacySegments": .array([
            .object([
                "segmentId": .string("contract-segment"),
                "rawAudio": .string("forbidden")
            ])
        ]),
        "meetingMuteTruth": .object([
            "decision": .string("meeting_mute_unproven"),
            "meetingContent": .string("forbidden")
        ])
    ])
    try require(
        redaction.status == .blockedSensitiveContent,
        "Mute-truth redaction must report blocked sensitive nested content"
    )
    try require(
        redaction.manifest["privacySegments"] != nil && redaction.manifest["meetingMuteTruth"] != nil,
        "Mute-truth redaction must preserve metadata top-level fields"
    )
}

do {
    try validateV5ProductSurface()
    try validateDiagnosticForbiddenFixtures()
    try validateRecordingSessionEvidenceFixture()
    try validateLocalRecordingManifestFixture()
    try validateRecordingArtifactFormatFixture()
    try validatePlatformGate()
    try validateCaptureSafetyInvariant()
    try validateDiagnosticBundleService()
    try validateLocalRecordingDiagnosticBundleNoEgressTruth()
    try await validateSystemAudioPermissionFailClosed()
    try await validateSystemAudioStartTimeoutCleanupOrdering()
    try validateAppStopFailureFailClosedSourceInvariant()
    try validateRecordingMetersUseLocalWriterInvariant()
    try validateManualGateExitCleanupInvariant()
    try validateDesktopUploadQueueContract()
    try validateMeetingMuteTruthContract()
    print("ContractValidation: PASS")
} catch {
    fputs("ContractValidation: FAIL - \(error)\n", stderr)
    exit(1)
}
