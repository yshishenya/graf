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

    public static let forbiddenValuePatterns: [String] = [
        "-----BEGIN PRIVATE KEY-----",
        "X-API-Key:",
        "Authorization: Bearer ",
        "presigned"
    ]

    public init() {}

    public func redact(_ manifest: [String: String]) -> (manifest: [String: String], status: DiagnosticRedactionStatus) {
        var redacted = manifest
        var blockedSensitiveContent = false
        let lowercasedForbiddenKeys = Set(Self.forbiddenKeys.map { $0.lowercased() })

        for key in redacted.keys where lowercasedForbiddenKeys.contains(key.lowercased()) {
            redacted.removeValue(forKey: key)
            blockedSensitiveContent = true
        }

        for (key, value) in redacted {
            if containsForbiddenPattern(value) {
                redacted.removeValue(forKey: key)
                blockedSensitiveContent = true
            }
        }

        return (
            redacted,
            blockedSensitiveContent ? .blockedSensitiveContent : .redacted
        )
    }

    private func containsForbiddenPattern(_ value: String) -> Bool {
        Self.forbiddenValuePatterns.contains { pattern in
            value.range(of: pattern, options: [.caseInsensitive]) != nil
        }
    }
}
