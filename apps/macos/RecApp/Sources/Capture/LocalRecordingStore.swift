import Foundation
import TwoBrainRecShared

public struct LocalRecordingStore: Sendable {
    public static let appSupportFolderName = "GRAF"
    public static let legacyAppSupportFolderName = "2brain Rec"

    public let rootURL: URL

    public init(rootURL: URL? = nil) {
        if let rootURL {
            self.rootURL = rootURL
        } else {
            self.rootURL = Self.defaultRootURL()
        }
    }

    public static func defaultRootURL(fileManager: FileManager = .default) -> URL {
        let base = fileManager.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first ?? fileManager.temporaryDirectory
        let current = currentRootURL(baseURL: base)
        let legacy = legacyRootURL(baseURL: base)
        if !fileManager.fileExists(atPath: current.path),
           fileManager.fileExists(atPath: legacy.path) {
            return legacy
        }
        return current
    }

    public static func currentRootURL(fileManager: FileManager = .default) -> URL {
        let base = fileManager.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first ?? fileManager.temporaryDirectory
        return currentRootURL(baseURL: base)
    }

    public static func legacyRootURL(fileManager: FileManager = .default) -> URL {
        let base = fileManager.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first ?? fileManager.temporaryDirectory
        return legacyRootURL(baseURL: base)
    }

    public static func currentRootURL(baseURL: URL) -> URL {
        recordingRootURL(baseURL: baseURL, appSupportFolderName: appSupportFolderName)
    }

    public static func legacyRootURL(baseURL: URL) -> URL {
        recordingRootURL(baseURL: baseURL, appSupportFolderName: legacyAppSupportFolderName)
    }

    private static func recordingRootURL(baseURL: URL, appSupportFolderName: String) -> URL {
        baseURL
            .appendingPathComponent(appSupportFolderName, isDirectory: true)
            .appendingPathComponent("Recordings", isDirectory: true)
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
