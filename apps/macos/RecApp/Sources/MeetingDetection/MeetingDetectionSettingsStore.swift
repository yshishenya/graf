import Foundation
import TwoBrainRecShared

public extension Notification.Name {
    static let twoBrainRecMeetingDetectionSettingsDidChange = Notification.Name(
        "pro.2brain.graf.meetingDetectionSettingsDidChange"
    )
    static let twoBrainRecMeetingTargetRegistryDidChange = Notification.Name(
        "pro.2brain.graf.meetingTargetRegistryDidChange"
    )
}

public struct MeetingDetectionSettings: Codable, Equatable, Sendable {
    public var uploadMode: MeetingDetectionUploadMode
    public var unknownIdentityUploadAllowed: Bool
    public var automaticRecordingRules: [String: AutomaticRecordingRule]

    public init(
        uploadMode: MeetingDetectionUploadMode = .automaticCandidateUpload,
        unknownIdentityUploadAllowed: Bool = true,
        automaticRecordingRules: [String: AutomaticRecordingRule] = [:]
    ) {
        self.uploadMode = uploadMode
        self.unknownIdentityUploadAllowed = unknownIdentityUploadAllowed
        self.automaticRecordingRules = automaticRecordingRules
    }

    private enum CodingKeys: String, CodingKey {
        case uploadMode
        case unknownIdentityUploadAllowed
        case autoRecordTargetIds
        case automaticRecordingRules
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        uploadMode = try container.decodeIfPresent(
            MeetingDetectionUploadMode.self,
            forKey: .uploadMode
        ) ?? .automaticCandidateUpload
        unknownIdentityUploadAllowed = try container.decodeIfPresent(
            Bool.self,
            forKey: .unknownIdentityUploadAllowed
        ) ?? true
        let decodedRules = try container.decodeIfPresent(
            [String: AutomaticRecordingRule].self,
            forKey: .automaticRecordingRules
        ) ?? [:]
        let legacyTargetIDs = try container.decodeIfPresent(
            Set<String>.self,
            forKey: .autoRecordTargetIds
        ) ?? []
        // ponytail: legacy keys are read once as safe `ask`; remove this decoder
        // only after supported installs can no longer contain the old document.
        automaticRecordingRules = decodedRules.isEmpty
            ? Dictionary(uniqueKeysWithValues: legacyTargetIDs.map { ($0, .ask) })
            : decodedRules
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(uploadMode, forKey: .uploadMode)
        try container.encode(unknownIdentityUploadAllowed, forKey: .unknownIdentityUploadAllowed)
        try container.encode(automaticRecordingRules, forKey: .automaticRecordingRules)
    }

    public var policySummary: MeetingDetectionPolicySummary {
        MeetingDetectionPolicySummary(
            detectionMode: .detectAndAsk,
            uploadMode: uploadMode,
            unknownIdentityUploadAllowed: unknownIdentityUploadAllowed
        )
    }

    public func allowsDetectorAssistedStart(
        reason: MeetingDetectionStartReason,
        targetID: String
    ) -> Bool {
        guard recordingRule(for: targetID) != .never else { return false }
        guard reason == .savedTargetPolicy else { return true }
        return recordingRule(for: targetID) == .always
    }

    public func recordingRule(for targetID: String) -> AutomaticRecordingRule {
        if let rule = automaticRecordingRules[targetID] {
            return rule
        }
        return .ask
    }

    public mutating func setRecordingRule(_ rule: AutomaticRecordingRule, for targetID: String) {
        automaticRecordingRules[targetID] = rule
    }
}

public final class MeetingDetectionSettingsStore: @unchecked Sendable {
    private let settingsURL: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder
    private let queue = DispatchQueue(label: "pro.2brain.graf.meeting-detection-settings", qos: .utility)

    public init(
        settingsURL: URL? = nil,
        channel: GrafAppChannel = .current,
        encoder: JSONEncoder = MeetingDetectionCoding.encoder(),
        decoder: JSONDecoder = MeetingDetectionCoding.decoder()
    ) {
        self.settingsURL = settingsURL ?? Self.defaultSettingsURL(channel: channel)
        self.encoder = encoder
        self.decoder = decoder
    }

    public static func defaultSettingsURL(channel: GrafAppChannel = .current) -> URL {
        MeetingDetectionAppModule.settingsURL(channel: channel)
    }

    public func load() throws -> MeetingDetectionSettings {
        try queue.sync { try loadLocked() }
    }

    public func save(_ settings: MeetingDetectionSettings) throws {
        try queue.sync { try saveLocked(settings) }
    }

    /// Adds only missing verified applications as `ask` and preserves every
    /// existing explicit rule. This also creates the first-install document.
    public func applyFirstInstallDefaults(targetIDs: Set<String>) throws -> MeetingDetectionSettings? {
        guard !targetIDs.isEmpty else { return nil }
        return try queue.sync {
            let current = try loadLocked()
            var updated = current
            for targetID in targetIDs where updated.automaticRecordingRules[targetID] == nil {
                updated.automaticRecordingRules[targetID] = .ask
            }
            guard updated != current else { return nil }
            try saveLocked(updated)
            return updated
        }
    }

    private func loadLocked() throws -> MeetingDetectionSettings {
        guard FileManager.default.fileExists(atPath: settingsURL.path) else {
            return MeetingDetectionSettings()
        }
        return try decoder.decode(
            MeetingDetectionSettings.self,
            from: Data(contentsOf: settingsURL)
        )
    }

    private func saveLocked(_ settings: MeetingDetectionSettings) throws {
        try FileManager.default.createDirectory(
            at: settingsURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try encoder.encode(settings).write(to: settingsURL, options: [.atomic])
    }
}
