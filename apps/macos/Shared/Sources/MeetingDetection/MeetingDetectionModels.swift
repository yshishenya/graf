import Foundation

public enum MeetingDetectionMode: String, Codable, Sendable {
    case detectOnly = "detect_only"
    case detectAndAsk = "detect_and_ask"
}

public enum MeetingDetectionUploadMode: String, Codable, Sendable {
    case localOnly = "local_only"
    case manualExport = "manual_export"
    case workspaceOptIn = "workspace_opt_in"
    case dogfoodOptIn = "dogfood_opt_in"
    case automaticCandidateUpload = "automatic_candidate_upload"
}

public enum MeetingDetectionSupportMode: String, Codable, Sendable {
    case promptEnabled = "prompt_enabled"
    case diagnosticOnly = "diagnostic_only"
    case blockedMissingBundle = "blocked_missing_bundle"
    case manualOrBrowserOnly = "manual_or_browser_only"
    case disabled
}

public enum MeetingDetectionTargetFamily: String, Codable, Sendable {
    case nativeApp = "native_app"
    case browserMeeting = "browser_meeting"
    case provider
    case manualOnly = "manual_only"
}

public enum MeetingDetectionPlatform: String, Codable, Sendable {
    case macos
    case windows
    case browser
    case crossPlatform = "cross_platform"
}

public enum MeetingDetectionMarket: String, Codable, Sendable {
    case global
    case russia
    case enterprise
    case unknown
}

public enum MeetingDetectionEvidence: String, Codable, Sendable {
    case runtimeVerified = "runtime_verified"
    case runtimeStartVerified = "runtime_start_verified"
    case packageVerified = "package_verified"
    case installedVerified = "installed_verified"
    case confirmed
    case seed
    case verifyRequired = "verify_required"
    case futureWindows = "future_windows"
}

public enum MeetingDetectionSignal: String, Codable, Sendable {
    case macOSAudioHALAssertion = "macos_audio_hal_assertion"
    case browserMetadata = "browser_metadata"
    case calendarOrJoinIntent = "calendar_or_join_intent"
    case windowsFutureAdapter = "windows_future_adapter"
    case calendarOverlap = "calendar_overlap"
    case joinIntent = "join_intent"
    case systemAudioActivity = "system_audio_activity"
    case manualRecordNearby = "manual_record_nearby"
    case adapterHealth = "adapter_health"
}

public enum BrowserMeetingPageState: String, Codable, Hashable, Sendable {
    case joinedMeeting = "joined_meeting"
    case landingPage = "landing_page"
    case newMeeting = "new_meeting"
    case joinPage = "join_page"
    case waitingRoom = "waiting_room"
    case prejoin
    case settings
    case deviceTest = "device_test"
    case mediaPlayback = "media_playback"
    case voiceSearch = "voice_search"
    case unknown
}

public enum MeetingDetectionCalendarJoinIntentSource: String, Codable, Sendable {
    case calendarJoinPrompt = "calendar_join_prompt"
    case calendarRecordPrompt = "calendar_record_prompt"
}

public struct MeetingDetectionCalendarJoinIntentHint: Codable, Equatable, Sendable {
    public let serviceFamily: String
    public let source: MeetingDetectionCalendarJoinIntentSource
    public let matchingEventCount: Int
    public let isAmbiguous: Bool

    public init(
        serviceFamily: String,
        source: MeetingDetectionCalendarJoinIntentSource,
        matchingEventCount: Int,
        isAmbiguous: Bool = false
    ) {
        self.serviceFamily = serviceFamily
        self.source = source
        self.matchingEventCount = matchingEventCount
        self.isAmbiguous = isAmbiguous
    }
}

public enum BrowserMeetingServiceFamilyResolver {
    public static func serviceFamily(for url: URL) -> String? {
        guard let host = url.host?.lowercased() else {
            return nil
        }
        if host == "telemost.yandex.ru" || host.hasSuffix(".telemost.yandex.ru") {
            return "yandex_telemost"
        }
        if host == "meet.google.com" {
            return "google_meet"
        }
        if host == "zoom.us" || host.hasSuffix(".zoom.us") {
            return "zoom"
        }
        if host == "teams.microsoft.com" || host.hasSuffix(".teams.microsoft.com") {
            return "microsoft_teams"
        }
        if host == "pruffme.com" || host.hasSuffix(".pruffme.com") {
            return "pruffme"
        }
        return nil
    }
}

public enum BrowserMeetingTargetEvaluationKind: Equatable, Sendable {
    case safeJoinedTarget(targetID: String, mode: MeetingDetectionSupportMode)
    case manualOnly(targetID: String?, reason: String)
}

public struct BrowserMeetingTargetEvaluation: Equatable, Sendable {
    public let kind: BrowserMeetingTargetEvaluationKind
    public let serviceFamily: String?
    public let signals: [MeetingDetectionSignal]

    public init(
        kind: BrowserMeetingTargetEvaluationKind,
        serviceFamily: String?,
        signals: [MeetingDetectionSignal] = []
    ) {
        self.kind = kind
        self.serviceFamily = serviceFamily
        self.signals = signals
    }
}

public struct BrowserMeetingServiceMatcher: Sendable {
    public init() {}

    public func evaluate(
        evidence: BrowserTargetEvidence,
        registry: MeetingTargetRegistryDocument
    ) -> BrowserMeetingTargetEvaluation {
        guard evidence.metadataAvailable == true else {
            return BrowserMeetingTargetEvaluation(
                kind: .manualOnly(targetID: nil, reason: "browser_metadata_unavailable"),
                serviceFamily: nil
            )
        }
        guard let serviceFamily = normalized(evidence.serviceFamily) else {
            return BrowserMeetingTargetEvaluation(
                kind: .manualOnly(targetID: nil, reason: "browser_service_family_missing"),
                serviceFamily: nil
            )
        }

        let target = registry.targets.first { target in
            guard target.targetFamily == .browserMeeting ||
                target.platform == .browser ||
                target.platform == .crossPlatform else {
                return false
            }
            return target.browserServicePatterns.contains { pattern in
                normalized(pattern.serviceFamily) == serviceFamily
            }
        }

        guard let target else {
            return BrowserMeetingTargetEvaluation(
                kind: .manualOnly(targetID: nil, reason: "unsupported_browser_service"),
                serviceFamily: serviceFamily
            )
        }

        let metadataSignals: [MeetingDetectionSignal] = [.browserMetadata]
        guard evidence.pageState == .joinedMeeting else {
            return BrowserMeetingTargetEvaluation(
                kind: .manualOnly(targetID: target.id, reason: "unsupported_browser_metadata"),
                serviceFamily: serviceFamily,
                signals: metadataSignals
            )
        }
        guard evidence.calendarOrJoinIntentPresent == true else {
            return BrowserMeetingTargetEvaluation(
                kind: .manualOnly(targetID: target.id, reason: "calendar_or_join_intent_missing"),
                serviceFamily: serviceFamily,
                signals: metadataSignals
            )
        }
        guard matchesPromptQualityPattern(evidence: evidence, target: target, serviceFamily: serviceFamily) else {
            return BrowserMeetingTargetEvaluation(
                kind: .manualOnly(targetID: target.id, reason: "unsupported_browser_metadata"),
                serviceFamily: serviceFamily,
                signals: metadataSignals + [.calendarOrJoinIntent]
            )
        }

        return BrowserMeetingTargetEvaluation(
            kind: .safeJoinedTarget(targetID: target.id, mode: target.mode),
            serviceFamily: serviceFamily,
            signals: metadataSignals + [.calendarOrJoinIntent]
        )
    }

    private func matchesPromptQualityPattern(
        evidence: BrowserTargetEvidence,
        target: MeetingTargetRegistryTarget,
        serviceFamily: String
    ) -> Bool {
        guard let hostCategory = normalized(evidence.hostCategory),
              let patternClass = normalized(evidence.patternClass)
        else {
            return false
        }
        return target.browserServicePatterns.contains { pattern in
            normalized(pattern.serviceFamily) == serviceFamily &&
                normalized(pattern.hostCategory) == hostCategory &&
                normalized(pattern.patternClass) == patternClass
        }
    }

    private func normalized(_ value: String?) -> String? {
        guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased(),
              !trimmed.isEmpty
        else {
            return nil
        }
        return trimmed
    }
}

public enum MeetingDetectionCandidateReason: String, Codable, Hashable, Sendable {
    case stableMicDuration = "stable_mic_duration"
    case repeatedObservation = "repeated_observation"
    case manualRecordNearby = "manual_record_nearby"
    case calendarOrJoinHint = "calendar_or_join_hint"
    case vksNameToken = "vks_name_token"
    case knownVKSVendor = "known_vks_vendor"
    case knownRegistryNeighbor = "known_registry_neighbor"
    case longDurationBucket = "long_duration_bucket"
}

public enum MeetingDetectionSuppressionReason: String, Codable, Hashable, Sendable {
    case lowScore = "low_score"
    case shortDuration = "short_duration"
    case browserBundle = "browser_bundle"
    case audioUtility = "audio_utility"
    case systemService = "system_service"
    case mediaPlayer = "media_player"
    case audioEditor = "audio_editor"
    case game
    case screenRecorder = "screen_recorder"
    case knownNonTarget = "known_non_target"
    case workspaceUploadDisabled = "workspace_upload_disabled"
    case unsafeMetadata = "unsafe_metadata"
}

public enum MeetingDetectionNonTargetRuleKind: String, Codable, Sendable {
    case bundleID = "bundle_id"
    case bundlePrefix = "bundle_prefix"
    case displayNameToken = "display_name_token"
    case category
    case windowsProcessName = "windows_process_name"
    case browserServiceFamily = "browser_service_family"
}

public struct MeetingTargetBrowserServicePattern: Codable, Equatable, Sendable {
    public let serviceFamily: String
    public let hostCategory: String
    public let patternClass: String

    public init(serviceFamily: String, hostCategory: String, patternClass: String) {
        self.serviceFamily = serviceFamily
        self.hostCategory = hostCategory
        self.patternClass = patternClass
    }
}

public struct MeetingDetectionNonTargetRule: Codable, Equatable, Sendable {
    public let platform: MeetingDetectionPlatform
    public let ruleKind: MeetingDetectionNonTargetRuleKind
    public let ruleValue: String
    public let reasonCode: String

    public init(
        platform: MeetingDetectionPlatform,
        ruleKind: MeetingDetectionNonTargetRuleKind,
        ruleValue: String,
        reasonCode: String
    ) {
        self.platform = platform
        self.ruleKind = ruleKind
        self.ruleValue = ruleValue
        self.reasonCode = reasonCode
    }
}

public struct MeetingTargetRegistryTarget: Codable, Equatable, Sendable {
    public let id: String
    public let displayName: String
    public let market: MeetingDetectionMarket
    public let platform: MeetingDetectionPlatform
    public let targetFamily: MeetingDetectionTargetFamily
    public let mode: MeetingDetectionSupportMode
    public let evidence: MeetingDetectionEvidence
    public let requiredSignals: [MeetingDetectionSignal]
    public let nativeBundleIds: [String]
    public let windowsProcessNames: [String]
    public let browserServicePatterns: [MeetingTargetBrowserServicePattern]
    public let comments: String?

    public var isVerifiedNativePromptTarget: Bool {
        platform == .macos &&
            targetFamily == .nativeApp &&
            mode == .promptEnabled &&
            !nativeBundleIds.isEmpty &&
            evidence != .verifyRequired &&
            evidence != .futureWindows
    }

    public init(
        id: String,
        displayName: String,
        market: MeetingDetectionMarket,
        platform: MeetingDetectionPlatform,
        targetFamily: MeetingDetectionTargetFamily,
        mode: MeetingDetectionSupportMode,
        evidence: MeetingDetectionEvidence,
        requiredSignals: [MeetingDetectionSignal],
        nativeBundleIds: [String] = [],
        windowsProcessNames: [String] = [],
        browserServicePatterns: [MeetingTargetBrowserServicePattern] = [],
        comments: String? = nil
    ) {
        self.id = id
        self.displayName = displayName
        self.market = market
        self.platform = platform
        self.targetFamily = targetFamily
        self.mode = mode
        self.evidence = evidence
        self.requiredSignals = requiredSignals
        self.nativeBundleIds = nativeBundleIds
        self.windowsProcessNames = windowsProcessNames
        self.browserServicePatterns = browserServicePatterns
        self.comments = comments
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case displayName
        case market
        case platform
        case targetFamily
        case mode
        case evidence
        case requiredSignals
        case nativeBundleIds
        case windowsProcessNames
        case browserServicePatterns
        case comments
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        displayName = try container.decode(String.self, forKey: .displayName)
        market = try container.decode(MeetingDetectionMarket.self, forKey: .market)
        platform = try container.decode(MeetingDetectionPlatform.self, forKey: .platform)
        targetFamily = try container.decode(MeetingDetectionTargetFamily.self, forKey: .targetFamily)
        mode = try container.decode(MeetingDetectionSupportMode.self, forKey: .mode)
        evidence = try container.decode(MeetingDetectionEvidence.self, forKey: .evidence)
        requiredSignals = try container.decode([MeetingDetectionSignal].self, forKey: .requiredSignals)
        nativeBundleIds = try container.decodeIfPresent([String].self, forKey: .nativeBundleIds) ?? []
        windowsProcessNames = try container.decodeIfPresent([String].self, forKey: .windowsProcessNames) ?? []
        browserServicePatterns = try container.decodeIfPresent(
            [MeetingTargetBrowserServicePattern].self,
            forKey: .browserServicePatterns
        ) ?? []
        comments = try container.decodeIfPresent(String.self, forKey: .comments)
    }
}

public enum MeetingDetectionStartReason: String, Codable, Equatable, Sendable {
    case promptButton = "prompt_button"
    case promptTimeout = "prompt_timeout"
    case savedTargetPolicy = "saved_target_policy"

    public var isAutomatic: Bool { self != .promptButton }
}

public enum AutomaticRecordingRule: String, Codable, CaseIterable, Equatable, Sendable {
    case always
    case ask
    case never

    public var displayName: String {
        switch self {
        case .always: return "Всегда"
        case .ask: return "Спрашивать"
        case .never: return "Никогда"
        }
    }
}

public enum MeetingDetectionPromptAction: Equatable, Sendable {
    case start
    case skip
    case timeout
}

public struct MeetingDetectionPromptDecision: Equatable, Sendable {
    public let action: MeetingDetectionPromptAction
    public let rememberChoice: Bool

    public init(action: MeetingDetectionPromptAction, rememberChoice: Bool) {
        self.action = action
        self.rememberChoice = rememberChoice
    }

    public var startReason: MeetingDetectionStartReason? {
        switch action {
        case .start: return .promptButton
        case .timeout: return .promptTimeout
        case .skip: return nil
        }
    }

    public var persistedRule: AutomaticRecordingRule? {
        guard rememberChoice else { return nil }
        switch action {
        case .start: return .always
        case .skip: return .never
        case .timeout: return nil
        }
    }
}

public struct MeetingDetectionCountdown: Equatable, Sendable {
    public let startedAt: Date
    public let duration: TimeInterval
    public private(set) var isResolved = false

    public init(startedAt: Date, duration: TimeInterval = 8) {
        self.startedAt = startedAt
        self.duration = duration
    }

    public func remainingWholeSeconds(at now: Date) -> Int {
        max(0, Int(ceil(duration - now.timeIntervalSince(startedAt))))
    }

    public mutating func resolveStart(
        reason: MeetingDetectionStartReason,
        at now: Date,
        startIsTemporarilyDisabled: Bool = false
    ) -> MeetingDetectionStartReason? {
        guard !isResolved else { return nil }
        guard reason == .promptTimeout || !startIsTemporarilyDisabled else { return nil }
        if reason == .promptTimeout,
           now.timeIntervalSince(startedAt) < duration {
            return nil
        }
        isResolved = true
        return reason
    }

    public mutating func cancel() -> Bool {
        guard !isResolved else { return false }
        isResolved = true
        return true
    }
}

public struct MeetingTargetRegistryDocument: Codable, Equatable, Sendable {
    public let schemaVersion: Int
    public let registryVersion: String
    public let generatedAt: Date
    public let expiresAt: Date?
    public let targets: [MeetingTargetRegistryTarget]
    public let nonTargetRules: [MeetingDetectionNonTargetRule]
    public let etag: String?

    public init(
        schemaVersion: Int = 1,
        registryVersion: String,
        generatedAt: Date,
        expiresAt: Date? = nil,
        targets: [MeetingTargetRegistryTarget],
        nonTargetRules: [MeetingDetectionNonTargetRule] = [],
        etag: String? = nil
    ) {
        self.schemaVersion = schemaVersion
        self.registryVersion = registryVersion
        self.generatedAt = generatedAt
        self.expiresAt = expiresAt
        self.targets = targets
        self.nonTargetRules = nonTargetRules
        self.etag = etag
    }

    private enum CodingKeys: String, CodingKey {
        case schemaVersion
        case registryVersion
        case generatedAt
        case expiresAt
        case targets
        case nonTargetRules
        case etag
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        registryVersion = try container.decode(String.self, forKey: .registryVersion)
        generatedAt = try container.decode(Date.self, forKey: .generatedAt)
        expiresAt = try container.decodeIfPresent(Date.self, forKey: .expiresAt)
        targets = try container.decode([MeetingTargetRegistryTarget].self, forKey: .targets)
        nonTargetRules = try container.decodeIfPresent(
            [MeetingDetectionNonTargetRule].self,
            forKey: .nonTargetRules
        ) ?? []
        etag = try container.decodeIfPresent(String.self, forKey: .etag)
    }

    public func target(forBundleID bundleID: String) -> MeetingTargetRegistryTarget? {
        let normalizedBundleID = bundleID.lowercased()
        return targets.first { target in
            target.nativeBundleIds.contains { $0.lowercased() == normalizedBundleID }
        }
    }
}

public enum MeetingDetectionRegistrySource: String, Codable, Sendable {
    case remote
    case remoteCache = "remote_cache"
    case bundled
}

public struct MeetingDetectionAppObservation: Equatable, Sendable {
    public let bundleID: String
    public let displayName: String
    public let signingTeamID: String?
    public let version: String?
    public let stableObservationCount: Int
    public let activeDurationSeconds: TimeInterval
    public let manualRecordNearbyCount: Int
    public let calendarOrJoinHintCount: Int

    public init(
        bundleID: String,
        displayName: String,
        signingTeamID: String? = nil,
        version: String? = nil,
        stableObservationCount: Int,
        activeDurationSeconds: TimeInterval,
        manualRecordNearbyCount: Int = 0,
        calendarOrJoinHintCount: Int = 0
    ) {
        self.bundleID = bundleID
        self.displayName = displayName
        self.signingTeamID = signingTeamID
        self.version = version
        self.stableObservationCount = stableObservationCount
        self.activeDurationSeconds = activeDurationSeconds
        self.manualRecordNearbyCount = manualRecordNearbyCount
        self.calendarOrJoinHintCount = calendarOrJoinHintCount
    }
}

public enum MeetingDetectionCandidateDecisionKind: Equatable, Sendable {
    case knownTarget(targetID: String, mode: MeetingDetectionSupportMode)
    case candidateUpload
    case suppressed
}

public struct MeetingDetectionCandidateDecision: Equatable, Sendable {
    public let kind: MeetingDetectionCandidateDecisionKind
    public let candidateScore: Int
    public let candidateReasons: [MeetingDetectionCandidateReason]
    public let suppressionReasons: [MeetingDetectionSuppressionReason]

    public init(
        kind: MeetingDetectionCandidateDecisionKind,
        candidateScore: Int,
        candidateReasons: [MeetingDetectionCandidateReason] = [],
        suppressionReasons: [MeetingDetectionSuppressionReason] = []
    ) {
        self.kind = kind
        self.candidateScore = candidateScore
        self.candidateReasons = candidateReasons
        self.suppressionReasons = suppressionReasons
    }

    public var shouldUploadCandidateIdentity: Bool {
        kind == .candidateUpload
    }
}

public struct MeetingDetectionRollupWindow: Codable, Equatable, Sendable {
    public let bucket: String
    public let startedAt: Date
    public let endedAt: Date

    public init(bucket: String = "day", startedAt: Date, endedAt: Date) {
        self.bucket = bucket
        self.startedAt = startedAt
        self.endedAt = endedAt
    }
}

public struct MeetingDetectionPolicySummary: Codable, Equatable, Sendable {
    public let detectionMode: MeetingDetectionMode
    public let uploadMode: MeetingDetectionUploadMode
    public let unknownIdentityUploadAllowed: Bool

    public init(
        detectionMode: MeetingDetectionMode,
        uploadMode: MeetingDetectionUploadMode,
        unknownIdentityUploadAllowed: Bool
    ) {
        self.detectionMode = detectionMode
        self.uploadMode = uploadMode
        self.unknownIdentityUploadAllowed = unknownIdentityUploadAllowed
    }
}

public struct MeetingDetectionDurationBuckets: Codable, Equatable, Sendable {
    public var under5s: Int
    public var from5sTo30s: Int
    public var from30sTo5m: Int
    public var over5m: Int

    public init(
        under5s: Int = 0,
        from5sTo30s: Int = 0,
        from30sTo5m: Int = 0,
        over5m: Int = 0
    ) {
        self.under5s = under5s
        self.from5sTo30s = from5sTo30s
        self.from30sTo5m = from30sTo5m
        self.over5m = over5m
    }

    public static func bucket(for durationSeconds: TimeInterval) -> MeetingDetectionDurationBuckets {
        if durationSeconds < 5 {
            return MeetingDetectionDurationBuckets(under5s: 1)
        }
        if durationSeconds < 30 {
            return MeetingDetectionDurationBuckets(from5sTo30s: 1)
        }
        if durationSeconds < 300 {
            return MeetingDetectionDurationBuckets(from30sTo5m: 1)
        }
        return MeetingDetectionDurationBuckets(over5m: 1)
    }
}

public struct MeetingDetectionUnknownNativeAppRollup: Codable, Equatable, Sendable {
    public let identityMode: String
    public let uploadEligibility: String
    public let candidateScore: Int
    public let candidateReasons: [MeetingDetectionCandidateReason]
    public let suppressionReasons: [MeetingDetectionSuppressionReason]
    public let bundleId: String?
    public let displayName: String?
    public let signingTeamId: String?
    public let version: String?
    public let stableObservationCount: Int
    public let durationBuckets: MeetingDetectionDurationBuckets
    public let manualRecordNearbyCount: Int
    public let calendarOrJoinHintCount: Int

    public init(
        identityMode: String,
        uploadEligibility: String,
        candidateScore: Int,
        candidateReasons: [MeetingDetectionCandidateReason],
        suppressionReasons: [MeetingDetectionSuppressionReason] = [],
        bundleId: String?,
        displayName: String?,
        signingTeamId: String?,
        version: String?,
        stableObservationCount: Int,
        durationBuckets: MeetingDetectionDurationBuckets,
        manualRecordNearbyCount: Int,
        calendarOrJoinHintCount: Int
    ) {
        self.identityMode = identityMode
        self.uploadEligibility = uploadEligibility
        self.candidateScore = candidateScore
        self.candidateReasons = candidateReasons
        self.suppressionReasons = suppressionReasons
        self.bundleId = bundleId
        self.displayName = displayName
        self.signingTeamId = signingTeamId
        self.version = version
        self.stableObservationCount = stableObservationCount
        self.durationBuckets = durationBuckets
        self.manualRecordNearbyCount = manualRecordNearbyCount
        self.calendarOrJoinHintCount = calendarOrJoinHintCount
    }
}

public struct MeetingDetectionResourceRollup: Codable, Equatable, Sendable {
    public var cpuP95PercentBucket: String
    public var memoryOverheadBucketMb: String
    public var parserRestartCount: Int
    public var droppedEventCount: Int
    public var diskBytesWritten: Int
    public var uploadAttemptCount: Int

    public init(
        cpuP95PercentBucket: String = "under_1",
        memoryOverheadBucketMb: String = "under_10",
        parserRestartCount: Int = 0,
        droppedEventCount: Int = 0,
        diskBytesWritten: Int = 0,
        uploadAttemptCount: Int = 0
    ) {
        self.cpuP95PercentBucket = cpuP95PercentBucket
        self.memoryOverheadBucketMb = memoryOverheadBucketMb
        self.parserRestartCount = parserRestartCount
        self.droppedEventCount = droppedEventCount
        self.diskBytesWritten = diskBytesWritten
        self.uploadAttemptCount = uploadAttemptCount
    }
}

public struct MeetingDetectionTelemetryDocument: Codable, Equatable, Sendable {
    public let schemaVersion: Int
    public let clientVersion: String
    public let platform: String
    public let osVersionMajor: String
    public let registryVersion: String
    public let candidateFilterVersion: String
    public let createdAt: Date
    public let rollupWindow: MeetingDetectionRollupWindow
    public let policy: MeetingDetectionPolicySummary
    public var targetRollups: [String]
    public var unknownNativeAppRollups: [MeetingDetectionUnknownNativeAppRollup]
    public var resourceRollup: MeetingDetectionResourceRollup

    public init(
        schemaVersion: Int = 1,
        clientVersion: String,
        platform: String = "macos",
        osVersionMajor: String,
        registryVersion: String,
        candidateFilterVersion: String,
        createdAt: Date,
        rollupWindow: MeetingDetectionRollupWindow,
        policy: MeetingDetectionPolicySummary,
        targetRollups: [String] = [],
        unknownNativeAppRollups: [MeetingDetectionUnknownNativeAppRollup] = [],
        resourceRollup: MeetingDetectionResourceRollup = MeetingDetectionResourceRollup()
    ) {
        self.schemaVersion = schemaVersion
        self.clientVersion = clientVersion
        self.platform = platform
        self.osVersionMajor = osVersionMajor
        self.registryVersion = registryVersion
        self.candidateFilterVersion = candidateFilterVersion
        self.createdAt = createdAt
        self.rollupWindow = rollupWindow
        self.policy = policy
        self.targetRollups = targetRollups
        self.unknownNativeAppRollups = unknownNativeAppRollups
        self.resourceRollup = resourceRollup
    }
}

public struct MeetingDetectionDetectorEvidence: Equatable, Sendable {
    public let status: String
    public let registryVersion: String
    public let bundleID: String?
    public let targetID: String?
    public let supportMode: MeetingDetectionSupportMode?
    public let decision: String
    public let reason: String?
    public let observedAt: Date

    public init(
        status: String,
        registryVersion: String,
        bundleID: String?,
        targetID: String?,
        supportMode: MeetingDetectionSupportMode?,
        decision: String,
        reason: String?,
        observedAt: Date
    ) {
        self.status = status
        self.registryVersion = registryVersion
        self.bundleID = bundleID
        self.targetID = targetID
        self.supportMode = supportMode
        self.decision = decision
        self.reason = reason
        self.observedAt = observedAt
    }
}

public enum MeetingDetectionCoding {
    public static func encoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys]
        return encoder
    }

    public static func decoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}
