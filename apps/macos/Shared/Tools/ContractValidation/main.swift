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
    let forbiddenFields: [String]
    let forbiddenExternalActivity: [String]
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
        "Local recording manifest fixture must use local-recording-manifest.v1 schema"
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
            LocalRecordingSessionStatus.failed.rawValue
        ]),
        "Local recording manifest must allow saved, degraded, and failed terminal statuses"
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

func validatePlatformGate() throws {
    let minimum = OperatingSystemVersion(majorVersion: 14, minorVersion: 5, patchVersion: 0)
    try require(
        PlatformSupport.minimumSupportedMacOS.majorVersion == minimum.majorVersion &&
            PlatformSupport.minimumSupportedMacOS.minorVersion == minimum.minorVersion &&
            PlatformSupport.minimumSupportedMacOS.patchVersion == minimum.patchVersion,
        "PlatformSupport minimum macOS must be 14.5"
    )
    try require(
        PlatformSupport.currentArchitecture == .appleSilicon,
        "This MVP validation command must run on Apple Silicon"
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

do {
    try validateDesktopDriverEvents()
    try validateDiagnosticForbiddenFixtures()
    try validateReleaseHardeningFixtures()
    try validateLowResourceFixtures()
    try validateRecordingSessionEvidenceFixture()
    try validateLocalRecordingManifestFixture()
    try validatePlatformGate()
    try validateCaptureSafetyInvariant()
    try validateDiagnosticBundleService()
    print("ContractValidation: PASS")
} catch {
    fputs("ContractValidation: FAIL - \(error)\n", stderr)
    exit(1)
}
