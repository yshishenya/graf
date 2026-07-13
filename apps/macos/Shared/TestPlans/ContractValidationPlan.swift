struct DiagnosticsRedactionTestPlan {
    static let validationCommand = "swift run --package-path apps/macos ContractValidation"

    static let defaultForbiddenContent = [
        "raw audio",
        "transcript text",
        "MediaScribe credentials",
        "auth credentials",
        "API keys",
        "session tokens",
        "refresh tokens",
        "device tokens",
        "signed URLs"
    ]
}

struct MeetingMuteTruthContractTestPlan {
    static let validationCommand = "swift run --package-path apps/macos ContractValidation"

    static let allowedDecisions = [
        "meeting_mute_unproven",
        "unsupported",
        "degraded",
        "failed"
    ]

    static let requiredFixtureFiles = [
        "pause-validated.json",
        "unsupported.json",
        "deferred.json",
        "unsafe.json"
    ]
}
