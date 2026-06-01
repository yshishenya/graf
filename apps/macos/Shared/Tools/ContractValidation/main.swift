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
    try validatePlatformGate()
    try validateCaptureSafetyInvariant()
    try validateDiagnosticBundleService()
    print("ContractValidation: PASS")
} catch {
    fputs("ContractValidation: FAIL - \(error)\n", stderr)
    exit(1)
}
