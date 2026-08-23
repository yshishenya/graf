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
    public var detectionMode: MeetingDetectionMode
    public var uploadMode: MeetingDetectionUploadMode
    public var unknownIdentityUploadAllowed: Bool
    public var targetScopedAutoRecordEnabled: Bool
    public var autoRecordTargetIds: Set<String>
    public var assistedAutoStartAcknowledgement: AssistedAutoStartAcknowledgement?
    public var automaticRecordingDefaultsApplied: Bool

    public init(
        detectionMode: MeetingDetectionMode = .detectAndAsk,
        uploadMode: MeetingDetectionUploadMode = .automaticCandidateUpload,
        unknownIdentityUploadAllowed: Bool = true,
        targetScopedAutoRecordEnabled: Bool = false,
        autoRecordTargetIds: Set<String> = [],
        assistedAutoStartAcknowledgement: AssistedAutoStartAcknowledgement? = nil,
        automaticRecordingDefaultsApplied: Bool = false
    ) {
        self.detectionMode = detectionMode
        self.uploadMode = uploadMode
        self.unknownIdentityUploadAllowed = unknownIdentityUploadAllowed
        self.targetScopedAutoRecordEnabled = targetScopedAutoRecordEnabled
        self.autoRecordTargetIds = autoRecordTargetIds
        self.assistedAutoStartAcknowledgement = assistedAutoStartAcknowledgement
        self.automaticRecordingDefaultsApplied = automaticRecordingDefaultsApplied
    }

    private enum CodingKeys: String, CodingKey {
        case detectionMode
        case uploadMode
        case unknownIdentityUploadAllowed
        case targetScopedAutoRecordEnabled
        case autoRecordTargetIds
        case assistedAutoStartAcknowledgement
        case automaticRecordingDefaultsApplied
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        detectionMode = try container.decode(MeetingDetectionMode.self, forKey: .detectionMode)
        uploadMode = try container.decode(MeetingDetectionUploadMode.self, forKey: .uploadMode)
        unknownIdentityUploadAllowed = try container.decode(Bool.self, forKey: .unknownIdentityUploadAllowed)
        targetScopedAutoRecordEnabled = try container.decode(Bool.self, forKey: .targetScopedAutoRecordEnabled)
        autoRecordTargetIds = try container.decode(Set<String>.self, forKey: .autoRecordTargetIds)
        assistedAutoStartAcknowledgement = try container.decodeIfPresent(
            AssistedAutoStartAcknowledgement.self,
            forKey: .assistedAutoStartAcknowledgement
        )
        // A file written before this feature is already user-controlled. Never
        // reinterpret its existing target selection as a fresh-install default.
        automaticRecordingDefaultsApplied = try container.decodeIfPresent(
            Bool.self,
            forKey: .automaticRecordingDefaultsApplied
        ) ?? true
    }

    public var policySummary: MeetingDetectionPolicySummary {
        MeetingDetectionPolicySummary(
            detectionMode: detectionMode,
            uploadMode: uploadMode,
            unknownIdentityUploadAllowed: unknownIdentityUploadAllowed
        )
    }

    public func allowsAssistedAutoStart(
        policy: AssistedAutoStartPolicySnapshot?,
        at now: Date = Date()
    ) -> Bool {
        guard let policy, let assistedAutoStartAcknowledgement else { return false }
        return assistedAutoStartAcknowledgement.matches(policy, at: now)
    }

    public func allowsDetectorAssistedStart(
        reason: MeetingDetectionStartReason,
        targetID: String
    ) -> Bool {
        guard detectionMode == .detectAndAsk else { return false }
        guard reason == .savedTargetPolicy else { return true }
        return targetScopedAutoRecordEnabled && autoRecordTargetIds.contains(targetID)
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

    /// Applies clean-install defaults once, without touching an existing
    /// user-controlled settings file or creating policy acknowledgement.
    public func applyFirstInstallDefaults(targetIDs: Set<String>) throws -> MeetingDetectionSettings? {
        guard !targetIDs.isEmpty else { return nil }
        return try queue.sync {
            // A missing file is the only unambiguous fresh-install signal. A
            // file with marker=false may already contain an explicit user edit.
            guard !FileManager.default.fileExists(atPath: settingsURL.path) else { return nil }
            let current = try loadLocked()
            guard !current.automaticRecordingDefaultsApplied else { return nil }
            var updated = current
            updated.detectionMode = .detectAndAsk
            updated.targetScopedAutoRecordEnabled = true
            updated.autoRecordTargetIds = targetIDs
            updated.automaticRecordingDefaultsApplied = true
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
