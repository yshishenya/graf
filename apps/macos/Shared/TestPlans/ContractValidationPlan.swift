struct DesktopDriverContractTestPlan {
    static let validationCommand = "swift run --package-path apps/macos ContractValidation"

    static let requiredEvents = [
        "driver.status_changed",
        "route.verification_result",
        "audio.passthrough_changed",
        "audio.continuity_event",
        "capture.frame_available"
    ]

    static let forbiddenFields = [
        "rawAudio",
        "transcriptText",
        "credentials",
        "tokens",
        "signedUrls"
    ]
}

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
