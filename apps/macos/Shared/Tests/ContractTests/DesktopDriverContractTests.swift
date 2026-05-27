struct DesktopDriverContractTestPlan {
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
