import Foundation

public struct DiagnosticRedactor: Sendable {
    public static let forbiddenKeys: Set<String> = [
        "rawAudio",
        "audioSnippet",
        "transcriptText",
        "meetingNotes",
        "mediaScribeApiKey",
        "apiKey",
        "password",
        "sessionToken",
        "refreshToken",
        "deviceToken",
        "signedUrl",
        "temporaryUploadUrl",
        "temporaryDownloadUrl"
    ]

    public init() {}

    public func redact(_ manifest: [String: String]) -> (manifest: [String: String], status: DiagnosticRedactionStatus) {
        var redacted = manifest
        var blockedSensitiveContent = false

        for key in Self.forbiddenKeys where redacted[key] != nil {
            redacted.removeValue(forKey: key)
            blockedSensitiveContent = true
        }

        return (
            redacted,
            blockedSensitiveContent ? .blockedSensitiveContent : .redacted
        )
    }
}
