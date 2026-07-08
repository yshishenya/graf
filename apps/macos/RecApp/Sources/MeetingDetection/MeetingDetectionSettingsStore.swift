import Foundation
import TwoBrainRecShared

public struct MeetingDetectionSettings: Codable, Equatable, Sendable {
    public var detectionMode: MeetingDetectionMode
    public var uploadMode: MeetingDetectionUploadMode
    public var unknownIdentityUploadAllowed: Bool
    public var targetScopedAutoRecordEnabled: Bool
    public var autoRecordTargetIds: Set<String>

    public init(
        detectionMode: MeetingDetectionMode = .detectAndAsk,
        uploadMode: MeetingDetectionUploadMode = .automaticCandidateUpload,
        unknownIdentityUploadAllowed: Bool = true,
        targetScopedAutoRecordEnabled: Bool = false,
        autoRecordTargetIds: Set<String> = []
    ) {
        self.detectionMode = detectionMode
        self.uploadMode = uploadMode
        self.unknownIdentityUploadAllowed = unknownIdentityUploadAllowed
        self.targetScopedAutoRecordEnabled = targetScopedAutoRecordEnabled
        self.autoRecordTargetIds = autoRecordTargetIds
    }

    public var policySummary: MeetingDetectionPolicySummary {
        MeetingDetectionPolicySummary(
            detectionMode: detectionMode,
            uploadMode: uploadMode,
            unknownIdentityUploadAllowed: unknownIdentityUploadAllowed
        )
    }
}

public final class MeetingDetectionSettingsStore: @unchecked Sendable {
    private let settingsURL: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder
    private let queue = DispatchQueue(label: "pro.2brain.graf.meeting-detection-settings", qos: .utility)

    public init(
        settingsURL: URL? = nil,
        encoder: JSONEncoder = MeetingDetectionCoding.encoder(),
        decoder: JSONDecoder = MeetingDetectionCoding.decoder()
    ) {
        self.settingsURL = settingsURL ?? Self.defaultSettingsURL()
        self.encoder = encoder
        self.decoder = decoder
    }

    public static func defaultSettingsURL() -> URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ??
            FileManager.default.temporaryDirectory
        return base
            .appendingPathComponent("GRAF", isDirectory: true)
            .appendingPathComponent(MeetingDetectionAppModule.applicationSupportDirectoryName, isDirectory: true)
            .appendingPathComponent("settings.json")
    }

    public func load() throws -> MeetingDetectionSettings {
        try queue.sync {
            guard FileManager.default.fileExists(atPath: settingsURL.path) else {
                return MeetingDetectionSettings()
            }
            return try decoder.decode(
                MeetingDetectionSettings.self,
                from: Data(contentsOf: settingsURL)
            )
        }
    }

    public func save(_ settings: MeetingDetectionSettings) throws {
        try queue.sync {
            try FileManager.default.createDirectory(
                at: settingsURL.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            try encoder.encode(settings).write(to: settingsURL, options: [.atomic])
        }
    }
}
