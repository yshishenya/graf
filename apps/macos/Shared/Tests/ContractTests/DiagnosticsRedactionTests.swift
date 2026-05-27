struct DiagnosticsRedactionTestPlan {
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
