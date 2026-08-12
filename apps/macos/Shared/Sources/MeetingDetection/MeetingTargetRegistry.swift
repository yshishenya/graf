import Foundation

public enum MeetingTargetRegistryError: Error, Equatable, CustomStringConvertible, Sendable {
    case invalidSchemaVersion
    case invalidRegistryVersion
    case emptyTargets
    case duplicateTarget(String)
    case duplicateBundleID(String)
    case invalidTarget(String)
    case unsafePromptTarget(String)
    case unsafeBrowserTarget(String)
    case invalidNonTargetRule
    case invalidAssistedAutoStartPolicy
    case expired
    case noUsableRegistry

    public var description: String {
        switch self {
        case .invalidSchemaVersion:
            "invalid_schema_version"
        case .invalidRegistryVersion:
            "invalid_registry_version"
        case .emptyTargets:
            "empty_targets"
        case .duplicateTarget(let id):
            "duplicate_target:\(id)"
        case .duplicateBundleID(let id):
            "duplicate_bundle_id:\(id)"
        case .invalidTarget(let id):
            "invalid_target:\(id)"
        case .unsafePromptTarget(let id):
            "unsafe_prompt_target:\(id)"
        case .unsafeBrowserTarget(let id):
            "unsafe_browser_target:\(id)"
        case .invalidNonTargetRule:
            "invalid_non_target_rule"
        case .invalidAssistedAutoStartPolicy:
            "invalid_assisted_auto_start_policy"
        case .expired:
            "expired"
        case .noUsableRegistry:
            "no_usable_registry"
        }
    }
}

public struct MeetingTargetRegistryResolution: Equatable, Sendable {
    public let document: MeetingTargetRegistryDocument
    public let source: MeetingDetectionRegistrySource
    public let etag: String?

    public init(
        document: MeetingTargetRegistryDocument,
        source: MeetingDetectionRegistrySource,
        etag: String?
    ) {
        self.document = document
        self.source = source
        self.etag = etag
    }
}

public struct MeetingTargetRegistryCacheDocument: Codable, Equatable, Sendable {
    public let downloadedAt: Date
    public let etag: String?
    public let source: MeetingDetectionRegistrySource
    public let registry: MeetingTargetRegistryDocument

    public init(
        downloadedAt: Date,
        etag: String?,
        source: MeetingDetectionRegistrySource,
        registry: MeetingTargetRegistryDocument
    ) {
        self.downloadedAt = downloadedAt
        self.etag = etag
        self.source = source
        self.registry = registry
    }
}

public enum MeetingTargetRegistryValidator {
    public static func validate(
        _ document: MeetingTargetRegistryDocument,
        now: Date = Date(),
        allowExpired: Bool = false
    ) throws {
        guard document.schemaVersion == 1 else {
            throw MeetingTargetRegistryError.invalidSchemaVersion
        }
        guard document.registryVersion.range(
            of: #"^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$"#,
            options: .regularExpression
        ) != nil else {
            throw MeetingTargetRegistryError.invalidRegistryVersion
        }
        if let expiresAt = document.expiresAt, expiresAt < now, !allowExpired {
            throw MeetingTargetRegistryError.expired
        }
        guard !document.targets.isEmpty else {
            throw MeetingTargetRegistryError.emptyTargets
        }
        var seenTargets = Set<String>()
        var seenBundleIDs = Set<String>()
        for target in document.targets {
            try validate(
                target: target,
                seenTargets: &seenTargets,
                seenBundleIDs: &seenBundleIDs
            )
        }
        try document.nonTargetRules.forEach(validate(rule:))
        if let policy = document.assistedAutoStartPolicy {
            guard policy.enabled,
                  policy.policyRef.range(of: #"^sha256:[0-9a-f]{64}$"#, options: .regularExpression) != nil,
                  policy.acknowledgementSubjectRef.range(of: #"^sha256:[0-9a-f]{64}$"#, options: .regularExpression) != nil,
                  policy.deviceRef.range(of: #"^sha256:[0-9a-f]{64}$"#, options: .regularExpression) != nil,
                  !policy.policyVersion.isEmpty,
                  !policy.acknowledgementVersion.isEmpty,
                  policy.expiresAt > policy.issuedAt,
                  policy.noticeMode == "internal_no_participant_notice"
            else {
                throw MeetingTargetRegistryError.invalidAssistedAutoStartPolicy
            }
        }
    }

    private static func validate(
        target: MeetingTargetRegistryTarget,
        seenTargets: inout Set<String>,
        seenBundleIDs: inout Set<String>
    ) throws {
        guard target.id.range(
            of: #"^[a-z0-9][a-z0-9_-]{2,80}$"#,
            options: .regularExpression
        ) != nil else {
            throw MeetingTargetRegistryError.invalidTarget(target.id)
        }
        guard !seenTargets.contains(target.id) else {
            throw MeetingTargetRegistryError.duplicateTarget(target.id)
        }
        seenTargets.insert(target.id)
        for bundleID in target.nativeBundleIds {
            let normalizedBundleID = bundleID.lowercased()
            guard seenBundleIDs.insert(normalizedBundleID).inserted else {
                throw MeetingTargetRegistryError.duplicateBundleID(bundleID)
            }
        }
        guard !target.requiredSignals.isEmpty else {
            throw MeetingTargetRegistryError.invalidTarget(target.id)
        }
        if target.platform == .macos,
           target.targetFamily == .nativeApp,
           target.mode == .promptEnabled {
            guard !target.nativeBundleIds.isEmpty,
                  target.evidence != .verifyRequired,
                  target.evidence != .futureWindows
            else {
                throw MeetingTargetRegistryError.unsafePromptTarget(target.id)
            }
        }
        if target.targetFamily == .browserMeeting {
            let requiredSignals = Set(target.requiredSignals)
            guard requiredSignals.contains(.browserMetadata),
                  requiredSignals.contains(.calendarOrJoinIntent),
                  !requiredSignals.contains(.macOSAudioHALAssertion),
                  !target.browserServicePatterns.isEmpty
            else {
                throw MeetingTargetRegistryError.unsafeBrowserTarget(target.id)
            }
        }
    }

    private static func validate(rule: MeetingDetectionNonTargetRule) throws {
        guard !rule.ruleValue.contains("://"),
              !rule.ruleValue.contains("@"),
              !rule.reasonCode.isEmpty,
              rule.ruleValue.count <= 240,
              rule.reasonCode.count <= 120
        else {
            throw MeetingTargetRegistryError.invalidNonTargetRule
        }
        if rule.ruleKind == .bundleID || rule.ruleKind == .bundlePrefix {
            guard rule.ruleValue.range(
                of: #"^[A-Za-z0-9][A-Za-z0-9_.-]{1,200}$"#,
                options: .regularExpression
            ) != nil else {
                throw MeetingTargetRegistryError.invalidNonTargetRule
            }
        }
    }
}

public final class MeetingTargetRegistryStore: @unchecked Sendable {
    public typealias Clock = @Sendable () -> Date

    private let cacheURL: URL
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    private let clock: Clock
    private let queue = DispatchQueue(label: "pro.2brain.graf.meeting-target-registry-store", qos: .utility)

    public init(
        cacheURL: URL,
        decoder: JSONDecoder = MeetingDetectionCoding.decoder(),
        encoder: JSONEncoder = MeetingDetectionCoding.encoder(),
        clock: @escaping Clock = Date.init
    ) {
        self.cacheURL = cacheURL
        self.decoder = decoder
        self.encoder = encoder
        self.clock = clock
    }

    public func resolve(
        remoteData: Data? = nil,
        remoteETag: String? = nil
    ) throws -> MeetingTargetRegistryResolution {
        try queue.sync {
            if let remoteData,
               let remote = try? decodeValidatedRegistry(from: remoteData, now: clock()) {
                try saveCache(registry: remote, etag: remoteETag, downloadedAt: clock())
                return MeetingTargetRegistryResolution(
                    document: remote,
                    source: .remote,
                    etag: remoteETag ?? remote.etag
                )
            }
            if let cache = try? loadCache(now: clock()) {
                return MeetingTargetRegistryResolution(
                    document: cache.registry,
                    source: .remoteCache,
                    etag: cache.etag ?? cache.registry.etag
                )
            }
            throw MeetingTargetRegistryError.noUsableRegistry
        }
    }

    public func loadCache(now: Date? = nil) throws -> MeetingTargetRegistryCacheDocument {
        let data = try Data(contentsOf: cacheURL)
        let cache = try decoder.decode(MeetingTargetRegistryCacheDocument.self, from: data)
        try MeetingTargetRegistryValidator.validate(cache.registry, now: now ?? clock())
        return cache
    }

    public func saveCache(
        registry: MeetingTargetRegistryDocument,
        etag: String?,
        downloadedAt: Date? = nil
    ) throws {
        try MeetingTargetRegistryValidator.validate(registry, now: downloadedAt ?? clock())
        try FileManager.default.createDirectory(
            at: cacheURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        let cache = MeetingTargetRegistryCacheDocument(
            downloadedAt: downloadedAt ?? clock(),
            etag: etag ?? registry.etag,
            source: .remoteCache,
            registry: registry
        )
        try encoder.encode(cache).write(to: cacheURL, options: [.atomic])
    }

    private func decodeValidatedRegistry(
        from data: Data,
        now: Date,
        allowExpired: Bool = false
    ) throws -> MeetingTargetRegistryDocument {
        let document = try decoder.decode(MeetingTargetRegistryDocument.self, from: data)
        try MeetingTargetRegistryValidator.validate(document, now: now, allowExpired: allowExpired)
        return document
    }
}
