import Foundation
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

do {
    try validateDesktopDriverEvents()
    try validateDiagnosticForbiddenFixtures()
    try validatePlatformGate()
    try validateCaptureSafetyInvariant()
    print("ContractValidation: PASS")
} catch {
    fputs("ContractValidation: FAIL - \(error)\n", stderr)
    exit(1)
}
