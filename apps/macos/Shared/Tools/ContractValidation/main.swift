import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

struct ValidationError: Error, CustomStringConvertible {
    let description: String
}

struct EventFixture: Decodable {
    let name: String
    let requiredFields: [String]
    let forbiddenFields: [String]
}

struct EventFixtureFile: Decodable {
    let schemaVersion: String
    let events: [EventFixture]
}

struct ForbiddenFixtureFile: Decodable {
    let schemaVersion: String
    let forbiddenKeys: [String]
    let forbiddenPatterns: [String]
}

struct ReleaseHardeningFixtureFile: Decodable {
    let schema: String
    let requiredFields: [String]?
    let allowedResult: [String]?
    let forbiddenFields: [String]
}

struct LowResourceValidationFixtureFile: Decodable {
    let schema: String
    let feature: String?
    let baseline: String?
    let allowedResult: [String]?
    let requiredFields: [String]?
    let requiredGates: [String]?
    let thresholds: [String: Int]?
    let forbiddenFields: [String]
}

struct LowResourceRouteTruthFixtureFile: Decodable {
    let schema: String
    let allowedResourceStates: [String]
    let requiredPlanes: [String]
    let forbiddenFields: [String]
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
        let manifestFileName: String
        let requiredFiles: [String]
        let mediaScribeSourceMode: String
        let externalEgressStarted: Bool
        let transcriptionStarted: Bool
    }

    struct Track: Decodable {
        let role: String
        let sourceKind: String
        let mediaScribeField: String
        let fileName: String
        let format: String
        let sampleRate: Int
        let channelCount: Int
        let bitsPerSample: Int
        let timelineStartMs: Int
        let timelineAligned: Bool
    }

    let schemaVersion: String
    let package: Package
    let tracks: [Track]
    let forbiddenFields: [String]
}

func findRepositoryRoot(startingAt startURL: URL) throws -> URL {
    var candidate = startURL.standardizedFileURL

    while true {
        let fixture = candidate.appendingPathComponent("tests/macos/contract/desktop-driver-events.json")
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
let eventFixtureURL = repositoryRoot.appendingPathComponent("tests/macos/contract/desktop-driver-events.json")
let forbiddenFixtureURL = repositoryRoot.appendingPathComponent("tests/macos/contract/diagnostic-forbidden-fields.json")

func decode<T: Decodable>(_ type: T.Type, from url: URL) throws -> T {
    let data = try Data(contentsOf: url)
    return try JSONDecoder().decode(type, from: data)
}

func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() {
        throw ValidationError(description: message)
    }
}

func validateDesktopDriverEvents() throws {
    let fixture = try decode(EventFixtureFile.self, from: eventFixtureURL)
    let eventsByName = Dictionary(uniqueKeysWithValues: fixture.events.map { ($0.name, $0) })

    let expectedEvents: [String: Set<String>] = [
        "driver.status_changed": [
            "driverInstallationState",
            "driverVersion",
            "macOSVersion",
            "appleSilicon",
            "requiresRestart",
            "recoveryAction"
        ],
        "route.verification_result": [
            "path",
            "validationType",
            "target",
            "status",
            "failureReason",
            "recoveryAction",
            "timestamp"
        ],
        "audio.passthrough_changed": [
            "path",
            "passthroughStatus",
            "physicalDeviceClass",
            "sampleRate",
            "channelLayout",
            "timestamp"
        ],
        "audio.continuity_event": [
            "trackRole",
            "eventType",
            "monotonicTime",
            "durationMs",
            "driftEstimateMs",
            "severity"
        ],
        "capture.frame_available": [
            "trackRole",
            "monotonicTimestamp",
            "sampleRate",
            "channelLayout",
            "frameCount",
            "continuitySequence"
        ]
    ]

    for (eventName, requiredFields) in expectedEvents {
        guard let event = eventsByName[eventName] else {
            throw ValidationError(description: "Missing desktop-driver fixture event: \(eventName)")
        }

        let actualFields = Set(event.requiredFields)
        try require(
            requiredFields.isSubset(of: actualFields),
            "Event \(eventName) does not include required fields: \(requiredFields.subtracting(actualFields))"
        )

        try require(
            Set(event.forbiddenFields).isSuperset(of: ["rawAudio", "transcriptText", "credentials", "tokens", "signedUrls"]),
            "Event \(eventName) must forbid raw content and secret fields"
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
        "routeVerificationResults": .object([
            "failureCode": .string("speaker_missing"),
            "sessionToken": .string("nested-secret"),
            "samples": .array([
                .object([
                    "path": .string("speaker_passthrough"),
                    "temporaryUploadUrl": .string("https://example.presigned/upload")
                ]),
                .object([
                    "path": .string("mic_to_virtual_input"),
                    "status": .string("failed")
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
    guard case .object(let routeResults)? = recursiveResult.manifest["routeVerificationResults"] else {
        throw ValidationError(description: "Recursive DiagnosticRedactor must preserve allowed object fields")
    }
    try require(
        routeResults["sessionToken"] == nil,
        "Recursive DiagnosticRedactor must remove nested forbidden keys"
    )
    guard case .array(let samples)? = routeResults["samples"],
          case .object(let firstSample)? = samples.first else {
        throw ValidationError(description: "Recursive DiagnosticRedactor must preserve safe array objects")
    }
    try require(
        firstSample["temporaryUploadUrl"] == nil,
        "Recursive DiagnosticRedactor must remove forbidden keys inside arrays"
    )
}

func validateReleaseHardeningFixtures() throws {
    let fixtureNames = [
        "release-hardening-evidence",
        "core-audio-no-hang-evidence",
        "route-recovery-evidence",
        "installer-lifecycle-evidence",
        "ux-readiness-evidence"
    ]

    for name in fixtureNames {
        let url = repositoryRoot.appendingPathComponent("tests/macos/contract/\(name).json")
        let fixture = try decode(ReleaseHardeningFixtureFile.self, from: url)
        try require(
            fixture.schema.hasPrefix("2brain.rec."),
            "Release-hardening fixture \(name) must use a 2brain.rec schema"
        )
        try require(
            Set(fixture.forbiddenFields).isSuperset(of: ["rawAudio", "transcriptText", "meetingContent", "credentials", "tokens", "signedUrls"]),
            "Release-hardening fixture \(name) must forbid raw content and secret fields"
        )

        if let allowedResult = fixture.allowedResult {
            try require(
                Set(allowedResult) == ["passed", "blocked", "not_accepted"],
                "Release-hardening fixture \(name) must use common result values"
            )
        }
    }
}

func validateLowResourceFixtures() throws {
    let validationURL = repositoryRoot.appendingPathComponent("tests/macos/contract/low-resource-validation-evidence.json")
    let validation = try decode(LowResourceValidationFixtureFile.self, from: validationURL)

    try require(
        validation.schema == "2brain.rec.low_resource_validation_evidence.v1",
        "Low-resource validation fixture must use the v1 schema"
    )
    try require(
        validation.feature == "006-low-resource-audio",
        "Low-resource validation fixture must identify feature 006"
    )
    try require(
        validation.baseline == "005-macos-passthrough-release-hardening",
        "Low-resource validation fixture must preserve the accepted 005 baseline"
    )
    try require(
        Set(validation.allowedResult ?? []) == ["passed", "blocked", "not_accepted"],
        "Low-resource validation fixture must use common result values"
    )
    try require(
        validation.thresholds?["startup_timeout_ms"] == 3000,
        "Low-resource startup threshold must be 3000 ms"
    )
    try require(
        validation.thresholds?["target_surface_usable_within_seconds"] == 5,
        "Low-resource no-hang threshold must be 5 seconds"
    )
    try require(
        Set(validation.forbiddenFields).isSuperset(of: ["rawAudio", "transcriptText", "meetingContent", "credentials", "tokens", "signedUrls", "password"]),
        "Low-resource validation fixture must forbid raw content and secret fields"
    )

    let routeURL = repositoryRoot.appendingPathComponent("tests/macos/contract/low-resource-route-truth.json")
    let route = try decode(LowResourceRouteTruthFixtureFile.self, from: routeURL)
    try require(
        Set(route.requiredPlanes) == ["publication", "client_io", "app_bridge", "physical_devices", "recording_trigger"],
        "Low-resource route truth fixture must require separate readiness planes"
    )
    try require(
        route.allowedResourceStates.contains("fallback") && route.allowedResourceStates.contains("active"),
        "Low-resource route truth fixture must include active and fallback states"
    )

    let startupURL = repositoryRoot.appendingPathComponent("tests/macos/contract/low-resource-startup-attempt.json")
    let startup = try decode(LowResourceValidationFixtureFile.self, from: startupURL)
    try require(
        startup.thresholds?["maximum_duration_ms"] == 3000,
        "Low-resource startup attempt fixture must cap duration at 3000 ms"
    )
    try require(
        Set(startup.forbiddenFields).isSuperset(of: ["rawAudio", "transcriptText", "meetingContent", "credentials", "tokens", "signedUrls", "password"]),
        "Low-resource startup fixture must forbid raw content and secret fields"
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
            RecordingEvidenceEventType.routeInvalidated.rawValue,
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
            "routeState",
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
        Set(fixture.requiredTrackRoles) == Set([AudioTrackRole.localMic.rawValue, AudioTrackRole.remoteSpeaker.rawValue]),
        "Local recording manifest must require local mic and remote speaker roles"
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
            TranscriptionReadinessState.failed.rawValue,
            TranscriptionReadinessState.legacyNotReady.rawValue
        ]),
        "Local recording manifest must allow all transcription readiness states"
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
            "timelineAligned"
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
        fixture.schemaVersion == "recording-artifact-format.v1",
        "Recording artifact format fixture must use v1 schema"
    )
    try require(
        fixture.package.manifestFileName == "manifest.json" &&
            Set(fixture.package.requiredFiles) == Set(["mic.wav", "incoming.wav"]) &&
            fixture.package.mediaScribeSourceMode == "dual" &&
            fixture.package.externalEgressStarted == false &&
            fixture.package.transcriptionStarted == false,
        "Recording artifact package must define manifest, dual files, and no egress"
    )
    let tracksByRole = Dictionary(uniqueKeysWithValues: fixture.tracks.map { ($0.role, $0) })
    try require(
        tracksByRole[AudioTrackRole.localMic.rawValue]?.mediaScribeField == MediaScribeTrackField.micFile.rawValue &&
            tracksByRole[AudioTrackRole.localMic.rawValue]?.sourceKind == AudioCaptureSourceKind.microphone.rawValue &&
            tracksByRole[AudioTrackRole.localMic.rawValue]?.fileName == "mic.wav",
        "Local mic track must map to microphone source, MediaScribe mic_file, and mic.wav"
    )
    try require(
        tracksByRole[AudioTrackRole.remoteSpeaker.rawValue]?.mediaScribeField == MediaScribeTrackField.incomingFile.rawValue &&
            tracksByRole[AudioTrackRole.remoteSpeaker.rawValue]?.sourceKind == AudioCaptureSourceKind.systemAudio.rawValue &&
            tracksByRole[AudioTrackRole.remoteSpeaker.rawValue]?.fileName == "incoming.wav",
        "Remote speaker track must map to systemAudio source, MediaScribe incoming_file, and incoming.wav"
    )
    for track in fixture.tracks {
        try require(
            track.format == "wav-pcm-s16le" &&
                track.sampleRate == 16_000 &&
                track.channelCount == 1 &&
                track.bitsPerSample == 16 &&
                track.timelineStartMs == 0 &&
                track.timelineAligned,
            "Every recording artifact track must be WAV PCM16 mono 16k with aligned timeline"
        )
    }
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
        PlatformSupport.isSupported(),
        "This MVP validation command requires macOS 14.5+ on Apple Silicon or Intel"
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

func validateSystemAudioMVPHealthCanRecordIgnoresParkedDriverDiagnostics() throws {
    let state = AudioHealthState(
        driverState: .needsRepair,
        virtualMicState: .missing,
        virtualSpeakerState: .missing,
        microphonePermission: .granted,
        outputPermission: .granted,
        routeVerification: nil,
        passthroughStatus: .failed,
        bufferRisk: .healthy,
        livePassthroughStatus: .blocked,
        recoveryActions: [
            "Driver diagnostics are parked for system audio recording",
            "Review parked passthrough diagnostics before future driver experiments"
        ]
    )

    try require(
        state.canRecord,
        "System-audio MVP health state must not block recording on parked driver or passthrough diagnostics"
    )
    try require(
        state.requiresAttention,
        "Parked driver or passthrough diagnostics should remain visible as attention, not as a recording blocker"
    )

    let missingPermission = AudioHealthState(
        microphonePermission: .denied,
        outputPermission: .granted,
        passthroughStatus: .healthy,
        bufferRisk: .healthy
    )
    let unsafeBuffer = AudioHealthState(
        microphonePermission: .granted,
        outputPermission: .granted,
        passthroughStatus: .healthy,
        bufferRisk: .mustDegradeOrStop
    )

    try require(
        !missingPermission.canRecord && !unsafeBuffer.canRecord,
        "System-audio MVP health state must still block missing permissions and unsafe local buffer"
    )
}

func validateDiagnosticBundleService() throws {
    let bundle = try DiagnosticBundleService().buildBundle(
        DiagnosticBundleInput(
            schemaVersion: "0.1.0",
            createdAt: Date(timeIntervalSince1970: 1_777_777_777),
            manifest: [
                "appVersion": .string("0.1.0"),
                "routeVerificationResults": .object([
                    "failureCode": .string("route_failed"),
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
    guard case .object(let routeResults)? = bundle.manifest["routeVerificationResults"] else {
        throw ValidationError(description: "DiagnosticBundleService must preserve safe route verification object")
    }
    try require(
        routeResults["password"] == nil,
        "DiagnosticBundleService must remove nested forbidden fields"
    )
}

func validateLocalRecordingDiagnosticBundleNoEgressTruth() throws {
    let manifest = LocalRecordingManifest(
        sessionId: "contract-local-recording-diagnostics",
        createdAt: Date(timeIntervalSince1970: 1),
        startedAt: Date(timeIntervalSince1970: 1),
        stoppedAt: Date(timeIntervalSince1970: 2),
        status: .saved,
        directoryId: "contract-safe-dir",
        transcriptionReadiness: .ready,
        mediaScribeSourceMode: "dual",
        tracks: [
            LocalRecordingTrack(
                trackId: "mic",
                role: .localMic,
                status: .saved,
                fileName: "mic.wav",
                format: "wav-pcm-s16le",
                sampleRate: 16_000,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 1000,
                byteCount: 100,
                frameCount: 16_000,
                timelineStartMs: 0,
                timelineAligned: true
            ),
            LocalRecordingTrack(
                trackId: "remote",
                role: .remoteSpeaker,
                status: .saved,
                fileName: "incoming.wav",
                format: "wav-pcm-s16le",
                sampleRate: 16_000,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 1000,
                byteCount: 100,
                frameCount: 16_000,
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

func validateLocalRecordingWriterBoundedDrain() throws {
    let root = FileManager.default.temporaryDirectory
        .appendingPathComponent("contract-validation-bounded-drain-\(UUID().uuidString)", isDirectory: true)
    defer { try? FileManager.default.removeItem(at: root) }

    let writer = LocalRecordingWriter(
        store: LocalRecordingStore(rootURL: root),
        incomingSampleSourceFactory: { InfiniteContractSampleSource() },
        recordMicrophone: false
    )
    _ = try writer.start(
        sessionId: "contract-bounded-drain",
        startedAt: Date(timeIntervalSince1970: 10)
    )

    let startedAt = Date()
    let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))
    let elapsed = Date().timeIntervalSince(startedAt)
    guard let incoming = manifest.tracks.first(where: { $0.role == .remoteSpeaker }) else {
        throw ValidationError(description: "Bounded drain validation must produce incoming track")
    }

    try require(
        elapsed < 2,
        "LocalRecordingWriter must bound drain time for non-terminating sample sources"
    )
    try require(
        incoming.failureReason == .writeFailed && incoming.status == .failed,
        "Bounded drain overflow must fail the incoming track truthfully"
    )
    try require(
        manifest.status != .saved,
        "Bounded drain overflow must not produce a clean saved manifest"
    )
    try require(
        !writer.isRecording,
        "Bounded drain overflow must release writer recording state"
    )
}

func validateLocalRecordingWriterForcedFailureTruth() throws {
    let root = FileManager.default.temporaryDirectory
        .appendingPathComponent("contract-validation-forced-failure-\(UUID().uuidString)", isDirectory: true)
    defer { try? FileManager.default.removeItem(at: root) }

    let microphoneSource = FiniteContractSampleSource(samples: Array(repeating: 0.35, count: 96_000))
    let incomingSource = FiniteContractSampleSource(samples: Array(repeating: 0.25, count: 96_000))
    let writer = LocalRecordingWriter(
        store: LocalRecordingStore(rootURL: root),
        microphoneSampleSourceFactory: { microphoneSource },
        incomingSampleSourceFactory: { incomingSource },
        recordMicrophone: false
    )
    _ = try writer.start(
        sessionId: "contract-forced-failure",
        startedAt: Date(timeIntervalSince1970: 10),
        scopeApproval: contractScopeApproval(),
        permissions: SystemAudioPermissionSnapshot(
            microphone: .granted,
            systemAudio: .granted,
            evaluatedAt: Date(timeIntervalSince1970: 9)
        )
    )

    let manifest = try writer.stop(
        stoppedAt: Date(timeIntervalSince1970: 11),
        failureReason: .captureFailed
    )
    guard let microphone = manifest.tracks.first(where: { $0.role == .localMic }),
          let incoming = manifest.tracks.first(where: { $0.role == .remoteSpeaker }) else {
        throw ValidationError(description: "Forced failure validation must produce both required tracks")
    }

    try require(
        microphone.frameCount > 0 && incoming.frameCount > 0,
        "Forced failure validation must use complete-looking mic and incoming tracks"
    )
    try require(
        manifest.failureReason == .captureFailed,
        "Forced system-audio failure must be preserved as manifest failureReason"
    )
    try require(
        manifest.status == .failed && !manifest.isComplete,
        "Forced system-audio failure must not produce a clean saved manifest"
    )
}

func validateLocalRecordingWriterPartialIncomingPaddingIsNotSaved() throws {
    let root = FileManager.default.temporaryDirectory
        .appendingPathComponent("contract-validation-partial-incoming-\(UUID().uuidString)", isDirectory: true)
    defer { try? FileManager.default.removeItem(at: root) }

    let microphoneSource = FiniteContractSampleSource(samples: Array(repeating: 0.35, count: 96_000))
    let partialIncomingSource = FiniteContractSampleSource(samples: Array(repeating: 0.25, count: 4_800))
    let writer = LocalRecordingWriter(
        store: LocalRecordingStore(rootURL: root),
        microphoneSampleSourceFactory: { microphoneSource },
        incomingSampleSourceFactory: { partialIncomingSource },
        recordMicrophone: false
    )
    _ = try writer.start(
        sessionId: "contract-partial-incoming",
        startedAt: Date(timeIntervalSince1970: 10),
        scopeApproval: contractScopeApproval(),
        permissions: SystemAudioPermissionSnapshot(
            microphone: .granted,
            systemAudio: .granted,
            evaluatedAt: Date(timeIntervalSince1970: 9)
        )
    )

    let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))
    guard let incoming = manifest.tracks.first(where: { $0.role == .remoteSpeaker }) else {
        throw ValidationError(description: "Partial incoming validation must produce incoming track")
    }

    try require(
        incoming.durationMs >= 990 && manifest.durationDifferenceSeconds <= 3,
        "Partial incoming validation must keep timeline-padded file shape for review"
    )
    try require(
        incoming.failureReason == .timelineMisaligned && incoming.status == .degraded,
        "Partial incoming frames padded with silence must be marked degraded timeline truth"
    )
    try require(
        manifest.captureHealth?.failureReason == .timelineMisaligned &&
            manifest.captureHealth?.gateStatus == .failed,
        "Partial incoming manifest and captureHealth must agree on timeline misalignment"
    )
    try require(
        manifest.status != .saved && !manifest.isComplete,
        "Partial incoming frames must not produce a clean saved manifest"
    )
}

func validateLocalRecordingWriterSmallStopTailPaddingIsSaved() throws {
    let root = FileManager.default.temporaryDirectory
        .appendingPathComponent("contract-validation-small-stop-tail-\(UUID().uuidString)", isDirectory: true)
    defer { try? FileManager.default.removeItem(at: root) }

    let microphoneSource = FiniteContractSampleSource(samples: Array(repeating: 0.35, count: 48_000))
    let incomingSource = FiniteContractSampleSource(samples: Array(repeating: 0.25, count: 46_080))
    let writer = LocalRecordingWriter(
        store: LocalRecordingStore(rootURL: root),
        microphoneSampleSourceFactory: { microphoneSource },
        incomingSampleSourceFactory: { incomingSource },
        recordMicrophone: false
    )
    _ = try writer.start(
        sessionId: "contract-small-stop-tail",
        startedAt: Date(timeIntervalSince1970: 10),
        scopeApproval: contractScopeApproval(),
        permissions: SystemAudioPermissionSnapshot(
            microphone: .granted,
            systemAudio: .granted,
            evaluatedAt: Date(timeIntervalSince1970: 9)
        )
    )

    let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))
    guard let incoming = manifest.tracks.first(where: { $0.role == .remoteSpeaker }) else {
        throw ValidationError(description: "Small stop-tail validation must produce incoming track")
    }

    try require(
        incoming.durationMs == 1000 && incoming.timelineAligned,
        "Small stop-tail padding must preserve aligned one-second incoming track shape"
    )
    try require(
        incoming.failureReason == .none && incoming.status == .saved,
        "Small stop-tail padding must not falsely degrade an otherwise complete incoming track"
    )
    try require(
        manifest.captureHealth?.failureReason == LocalRecordingFailureReason.none &&
            manifest.captureHealth?.gateStatus == .passed,
        "Small stop-tail manifest and captureHealth must agree on clean saved truth"
    )
    try require(
        manifest.status == .degraded &&
            manifest.failureReason == .leakageUnproven &&
            !manifest.isComplete,
        "Small stop-tail padding must keep captureHealth clean while leakage finalization blocks transcription without enough proof (status=\(manifest.status.rawValue) reason=\(manifest.failureReason.rawValue) complete=\(manifest.isComplete) leakage=\(manifest.leakageFinalization?.failureReason.rawValue ?? "none"))"
    )
}

func validateLocalRecordingManifestFailureReasonFailClosed() throws {
    let manifest = LocalRecordingManifest(
        sessionId: "contract-manifest-failure-reason",
        createdAt: Date(timeIntervalSince1970: 30),
        startedAt: Date(timeIntervalSince1970: 10),
        stoppedAt: Date(timeIntervalSince1970: 20),
        status: .saved,
        directoryId: "dir",
        transcriptionReadiness: .ready,
        tracks: [
            contractCompleteTrack(role: .localMic),
            contractCompleteTrack(role: .remoteSpeaker)
        ],
        failureReason: .captureFailed,
        scopeApproval: contractScopeApproval(),
        permissions: SystemAudioPermissionSnapshot(
            microphone: .granted,
            systemAudio: .granted,
            evaluatedAt: Date(timeIntervalSince1970: 9)
        )
    )

    try require(
        !manifest.isComplete,
        "LocalRecordingManifest.isComplete must fail closed when failureReason is not none"
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

    let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
        .manifest(
            sessionId: "contract-denied-manifest",
            directoryId: "dir",
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            tracks: [
                contractCompleteTrack(role: .localMic),
                contractCompleteTrack(role: .remoteSpeaker)
            ],
            scopeApproval: contractScopeApproval(),
            permissions: SystemAudioPermissionSnapshot(
                microphone: .granted,
                systemAudio: .denied,
                evaluatedAt: Date(timeIntervalSince1970: 1)
            )
        )
    try require(
        manifest.status != .saved &&
            manifest.failureReason == .permissionDenied &&
            !manifest.isComplete,
        "Denied permissions must not produce a saved or complete local recording manifest"
    )
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

    guard let clearBlockerRange = source.range(of: "recordingBlocker = nil"),
          let beginPreparingRange = source.range(of: "try captureController.beginPreparing"),
          let microphonePromptRange = source.range(of: "let microphoneSession = await microphoneCaptureService.requestPermissionAndPreflight"),
          let systemAudioPromptRange = source.range(of: "let systemAudioPermissionState = await systemAudioPermissionAuthorizer.requestPermission()")
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

func validateLiveAudioSignalMonitorFreshnessInvariant() throws {
    let monitorSourceURL = repositoryRoot.appendingPathComponent("apps/macos/RecApp/Sources/Capture/LiveAudioSignalMonitor.swift")
    let monitorSource = try String(contentsOf: monitorSourceURL, encoding: .utf8)
    let testsSourceURL = repositoryRoot.appendingPathComponent("apps/macos/Shared/Tests/LiveAudioSignalMonitorTests.swift")
    let testsSource = try String(contentsOf: testsSourceURL, encoding: .utf8)

    try require(
        monitorSource.contains("let age = now.timeIntervalSince(date)") &&
            monitorSource.contains("return age >= 0 && age <= Self.staleLevelResetInterval"),
        "LiveAudioSignalMonitor freshness must reject future timestamps so meters cannot show false live bars"
    )
    try require(
        testsSource.contains("testFutureMonitorFrameTimestampResetsInsteadOfHoldingFalseLiveBars"),
        "LiveAudioSignalMonitor tests must cover future timestamp false-live regression"
    )
}

func validateRecordingMetersUseLocalWriterInvariant() throws {
    let appSourceURL = repositoryRoot.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift")
    let source = try String(contentsOf: appSourceURL, encoding: .utf8)

    try require(
        source.contains("let recordingLevels = await writer.currentLevelsAsync()") &&
            source.contains("microphoneLevel: recordingLevels.microphoneLevel") &&
            source.contains("speakerLevel: recordingLevels.incomingLevel"),
        "Recording UI meters must be driven by LocalRecordingWriter levels, not legacy passthrough levels"
    )
    try require(
        source.contains("guard localRecordingActive, !recordingStartInProgress, !recordingStopInProgress else") &&
            source.contains("liveRouteSignalLevels = .inactive"),
        "Recording UI meters must reset to inactive outside active local recording"
    )
    try require(
        !source.contains("liveRouteSignalLevels = PassthroughRouteEngine.shared.currentSignalLevels"),
        "Recording UI meters must not be assigned from parked passthrough route levels"
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

func validateLocalRecordingWriterTimerWriteFailureInvariant() throws {
    let writerSourceURL = repositoryRoot.appendingPathComponent("apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift")
    let writerSource = try String(contentsOf: writerSourceURL, encoding: .utf8)

    try require(
        !writerSource.contains("try? microphoneWriter.write(samples: active.scratch") &&
            !writerSource.contains("try? active.remoteWriter.write(samples: active.scratch"),
        "LocalRecordingWriter timer writes must not silently discard WAV write failures"
    )
    try require(
        writerSource.contains("active.microphoneWriteFailed = true") &&
            writerSource.contains("active.incomingWriteFailed = true"),
        "LocalRecordingWriter timer write failures must be recorded on active recording state"
    )
    try require(
        writerSource.contains("drainResult.microphoneTruncated || active.microphoneWriteFailed ? .writeFailed : nil") &&
            writerSource.contains("drainResult.incomingTruncated || active.incomingWriteFailed ? .writeFailed : nil"),
        "LocalRecordingWriter timer write failures must force writeFailed track truth in the manifest"
    )
}

func validateSystemAudioIncomingQualityInvariant() throws {
    let systemAudioSourceURL = repositoryRoot.appendingPathComponent("apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift")
    let writerSourceURL = repositoryRoot.appendingPathComponent("apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift")
    let extractorTestsURL = repositoryRoot.appendingPathComponent("apps/macos/Shared/Tests/SystemAudioSampleExtractorTests.swift")
    let writerTestsURL = repositoryRoot.appendingPathComponent("apps/macos/Shared/Tests/LocalRecordingWriterTests.swift")
    let systemAudioSource = try String(contentsOf: systemAudioSourceURL, encoding: .utf8)
    let writerSource = try String(contentsOf: writerSourceURL, encoding: .utf8)
    let extractorTests = try String(contentsOf: extractorTestsURL, encoding: .utf8)
    let writerTests = try String(contentsOf: writerTestsURL, encoding: .utf8)

    try require(
        systemAudioSource.contains("private static let captureChannelCount = 1") &&
            systemAudioSource.contains("configuration.channelCount = 1") &&
            systemAudioSource.contains("extractMonoFloatSamples(from: sampleBuffer)") &&
            systemAudioSource.contains("downmixInterleavedSamples"),
        "System audio incoming capture must request mono from ScreenCaptureKit and downmix unexpected multi-channel buffers before recording"
    )
    try require(
        writerSource.contains("PCM16MonoDownsampler") &&
            writerSource.contains("windowFrameCount") &&
            writerSource.contains("monoSum") &&
            writerSource.contains("inputChannelCount: Int = 1"),
        "Incoming WAV writer must use a mono-aware downsampler instead of dropping every third stereo frame"
    )
    try require(
        extractorTests.contains("testDownmixesInterleavedStereoSamplesToMonoForSystemAudioWriter") &&
            writerTests.contains("testDownsamplerAveragesWindowBeforeReducingSystemAudioTo16k") &&
            writerTests.contains("testDownsamplerTreatsMonoSystemAudioSamplesAsFrames"),
        "Incoming audio quality guard tests must cover SCK downmixing and mono-aware 48k-to-16k downsampling"
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

func contractCompleteTrack(role: AudioTrackRole) -> LocalRecordingTrack {
    LocalRecordingTrack(
        trackId: role.rawValue,
        role: role,
        status: .saved,
        fileName: role == .localMic ? "mic.wav" : "incoming.wav",
        format: "wav-pcm-s16le",
        sampleRate: 16_000,
        channelCount: 1,
        bitsPerSample: 16,
        durationMs: 1000,
        byteCount: 32_044,
        frameCount: 16_000,
        timelineStartMs: 0,
        timelineAligned: true
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
        DesktopUploadTransportRole.role(forLocalTrackRole: .localMic) == .microphone,
        "Desktop upload queue must map local mic to backend microphone role"
    )
    try require(
        DesktopUploadTransportRole.role(forLocalTrackRole: .remoteSpeaker) == .system,
        "Desktop upload queue must map remote/system incoming audio to backend system role"
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
        trackCompleteness: [],
        isUploadable: true
    )
    let terminal = DesktopUploadQueueItem(
        id: "queue",
        sessionId: "session",
        directoryId: "directory",
        directoryPath: "/private/directory",
        manifestPath: "/private/directory/manifest.json",
        microphonePath: "/private/directory/mic.wav",
        systemAudioPath: "/private/directory/incoming.wav",
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
    try validateDesktopDriverEvents()
    try validateDiagnosticForbiddenFixtures()
    try validateReleaseHardeningFixtures()
    try validateLowResourceFixtures()
    try validateRecordingSessionEvidenceFixture()
    try validateLocalRecordingManifestFixture()
    try validateRecordingArtifactFormatFixture()
    try validatePlatformGate()
    try validateCaptureSafetyInvariant()
    try validateSystemAudioMVPHealthCanRecordIgnoresParkedDriverDiagnostics()
    try validateDiagnosticBundleService()
    try validateLocalRecordingDiagnosticBundleNoEgressTruth()
    try validateLocalRecordingWriterBoundedDrain()
    try validateLocalRecordingWriterForcedFailureTruth()
    try validateLocalRecordingWriterPartialIncomingPaddingIsNotSaved()
    try validateLocalRecordingWriterSmallStopTailPaddingIsSaved()
    try validateLocalRecordingManifestFailureReasonFailClosed()
    try await validateSystemAudioPermissionFailClosed()
    try await validateSystemAudioStartTimeoutCleanupOrdering()
    try validateAppStopFailureFailClosedSourceInvariant()
    try validateLiveAudioSignalMonitorFreshnessInvariant()
    try validateRecordingMetersUseLocalWriterInvariant()
    try validateManualGateExitCleanupInvariant()
    try validateLocalRecordingWriterTimerWriteFailureInvariant()
    try validateSystemAudioIncomingQualityInvariant()
    try validateDesktopUploadQueueContract()
    try validateMeetingMuteTruthContract()
    print("ContractValidation: PASS")
} catch {
    fputs("ContractValidation: FAIL - \(error)\n", stderr)
    exit(1)
}
