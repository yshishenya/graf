import Foundation
import TwoBrainRecShared

public struct LocalRecordingStore: Sendable {
    public let rootURL: URL

    public init(rootURL: URL? = nil) {
        if let rootURL {
            self.rootURL = rootURL
        } else {
            let base = FileManager.default.urls(
                for: .applicationSupportDirectory,
                in: .userDomainMask
            ).first ?? FileManager.default.temporaryDirectory
            self.rootURL = base
                .appendingPathComponent("2brain Rec", isDirectory: true)
                .appendingPathComponent("Recordings", isDirectory: true)
        }
    }

    public func createDirectory(sessionId: String) throws -> LocalRecordingDirectory {
        let safeId = Self.safeIdentifier(sessionId)
        let directoryId = "\(Self.timestamp())-\(safeId)"
        let directoryURL = rootURL.appendingPathComponent(directoryId, isDirectory: true)
        try FileManager.default.createDirectory(
            at: directoryURL,
            withIntermediateDirectories: true
        )
        return LocalRecordingDirectory(
            directoryId: directoryId,
            directoryURL: directoryURL,
            manifestURL: directoryURL.appendingPathComponent("manifest.json"),
            localMicURL: directoryURL.appendingPathComponent("mic.wav"),
            remoteSpeakerURL: directoryURL.appendingPathComponent("incoming.wav")
        )
    }

    public static func safeIdentifier(_ value: String) -> String {
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_"))
        let scalars = value.unicodeScalars.map { scalar -> Character in
            allowed.contains(scalar) ? Character(scalar) : "-"
        }
        let cleaned = String(scalars)
            .replacingOccurrences(of: "--", with: "-")
            .trimmingCharacters(in: CharacterSet(charactersIn: "-_"))
        return cleaned.isEmpty ? UUID().uuidString : cleaned
    }

    private static func timestamp() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter.string(from: Date())
    }
}

public struct LocalRecordingDirectory: Equatable, Sendable {
    public let directoryId: String
    public let directoryURL: URL
    public let manifestURL: URL
    public let localMicURL: URL
    public let remoteSpeakerURL: URL
}
