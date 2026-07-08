import Foundation

public struct MeetingDetectionCandidateFilter: Sendable {
    public static let version = "vks-filter-1"
    public let minimumUploadScore: Int
    public let minimumDurationSeconds: TimeInterval

    public init(minimumUploadScore: Int = 5, minimumDurationSeconds: TimeInterval = 30) {
        self.minimumUploadScore = minimumUploadScore
        self.minimumDurationSeconds = minimumDurationSeconds
    }

    public func evaluate(
        observation: MeetingDetectionAppObservation,
        registry: MeetingTargetRegistryDocument,
        uploadMode: MeetingDetectionUploadMode = .automaticCandidateUpload
    ) -> MeetingDetectionCandidateDecision {
        if let target = registry.target(forBundleID: observation.bundleID) {
            return MeetingDetectionCandidateDecision(
                kind: .knownTarget(targetID: target.id, mode: target.mode),
                candidateScore: 0
            )
        }

        var suppressionReasons = suppressionReasonsForKnownNonTargets(
            observation: observation,
            rules: registry.nonTargetRules
        )
        suppressionReasons.append(contentsOf: builtInSuppressionReasons(for: observation))
        if uploadMode != .automaticCandidateUpload {
            suppressionReasons.append(.workspaceUploadDisabled)
        }
        if hasUnsafeMetadata(observation) {
            suppressionReasons.append(.unsafeMetadata)
        }
        if observation.activeDurationSeconds < minimumDurationSeconds {
            suppressionReasons.append(.shortDuration)
        }
        if !suppressionReasons.isEmpty {
            return MeetingDetectionCandidateDecision(
                kind: .suppressed,
                candidateScore: 0,
                suppressionReasons: Array(Set(suppressionReasons)).sorted { $0.rawValue < $1.rawValue }
            )
        }

        let scoreResult = candidateScore(for: observation, registry: registry)
        if scoreResult.score < minimumUploadScore {
            return MeetingDetectionCandidateDecision(
                kind: .suppressed,
                candidateScore: scoreResult.score,
                candidateReasons: scoreResult.reasons,
                suppressionReasons: [.lowScore]
            )
        }
        return MeetingDetectionCandidateDecision(
            kind: .candidateUpload,
            candidateScore: scoreResult.score,
            candidateReasons: scoreResult.reasons
        )
    }

    private func candidateScore(
        for observation: MeetingDetectionAppObservation,
        registry: MeetingTargetRegistryDocument
    ) -> (score: Int, reasons: [MeetingDetectionCandidateReason]) {
        var score = 0
        var reasons: [MeetingDetectionCandidateReason] = []
        if observation.stableObservationCount >= 2 {
            score += 2
            reasons.append(.stableMicDuration)
        }
        if observation.stableObservationCount >= 3 {
            score += 1
            reasons.append(.repeatedObservation)
        }
        if observation.activeDurationSeconds >= 300 {
            score += 2
            reasons.append(.longDurationBucket)
        }
        if observation.manualRecordNearbyCount > 0 {
            score += 1
            reasons.append(.manualRecordNearby)
        }
        if observation.calendarOrJoinHintCount > 0 {
            score += 1
            reasons.append(.calendarOrJoinHint)
        }
        if containsVKSToken(observation) {
            score += 2
            reasons.append(.vksNameToken)
        }
        if knownVendorHint(observation) {
            score += 1
            reasons.append(.knownVKSVendor)
        }
        if sharesVendorNamespace(observation, registry: registry) {
            score += 1
            reasons.append(.knownRegistryNeighbor)
        }
        return (score, Array(Set(reasons)).sorted { $0.rawValue < $1.rawValue })
    }

    private func suppressionReasonsForKnownNonTargets(
        observation: MeetingDetectionAppObservation,
        rules: [MeetingDetectionNonTargetRule]
    ) -> [MeetingDetectionSuppressionReason] {
        let bundle = observation.bundleID.lowercased()
        let name = observation.displayName.lowercased()
        return rules.compactMap { rule in
            guard rule.platform == .macos || rule.platform == .crossPlatform else {
                return nil
            }
            let value = rule.ruleValue.lowercased()
            switch rule.ruleKind {
            case .bundleID:
                return bundle == value ? .knownNonTarget : nil
            case .bundlePrefix:
                return bundle.hasPrefix(value) ? .knownNonTarget : nil
            case .displayNameToken:
                return name.contains(value) ? .knownNonTarget : nil
            case .category:
                return value == "audio_utility" ? .audioUtility : .knownNonTarget
            case .windowsProcessName, .browserServiceFamily:
                return nil
            }
        }
    }

    private func builtInSuppressionReasons(
        for observation: MeetingDetectionAppObservation
    ) -> [MeetingDetectionSuppressionReason] {
        let bundle = observation.bundleID.lowercased()
        let name = observation.displayName.lowercased()
        if bundle.hasPrefix("com.apple.safari") ||
            bundle.hasPrefix("com.google.chrome") ||
            bundle.hasPrefix("org.mozilla.firefox") ||
            bundle.hasPrefix("com.microsoft.edgemac") ||
            bundle.hasPrefix("ru.yandex.desktop.yandex-browser") ||
            bundle.hasPrefix("com.yandex.browser") ||
            bundle.hasPrefix("com.operasoftware.opera") {
            return [.browserBundle]
        }
        if bundle.contains("krisp") || name.contains("krisp") {
            return [.audioUtility]
        }
        if bundle.hasPrefix("com.apple.") &&
            !bundle.contains("facetime") {
            return [.systemService]
        }
        return []
    }

    private func containsVKSToken(_ observation: MeetingDetectionAppObservation) -> Bool {
        let haystack = "\(observation.bundleID) \(observation.displayName)".lowercased()
        return [
            "meet",
            "meeting",
            "telemost",
            "trueconf",
            "webinar",
            "vks",
            "teams",
            "zoom",
            "conference",
            "conf",
            "video",
            "talk",
            "звон",
            "сферум"
        ].contains { haystack.contains($0) }
    }

    private func knownVendorHint(_ observation: MeetingDetectionAppObservation) -> Bool {
        let haystack = "\(observation.bundleID) \(observation.displayName)".lowercased()
        return [
            "yandex",
            "vk",
            "mail",
            "mts",
            "kontur",
            "sber",
            "iva",
            "trueconf",
            "webinar",
            "zoom",
            "microsoft",
            "cisco"
        ].contains { haystack.contains($0) }
    }

    private func sharesVendorNamespace(
        _ observation: MeetingDetectionAppObservation,
        registry: MeetingTargetRegistryDocument
    ) -> Bool {
        let bundleParts = observation.bundleID.split(separator: ".")
        guard bundleParts.count >= 2 else {
            return false
        }
        let prefix = bundleParts.prefix(2).joined(separator: ".").lowercased()
        return registry.targets.flatMap(\.nativeBundleIds).contains { knownBundle in
            knownBundle.lowercased().hasPrefix(prefix)
        }
    }

    private func hasUnsafeMetadata(_ observation: MeetingDetectionAppObservation) -> Bool {
        let values = [observation.bundleID, observation.displayName, observation.signingTeamID, observation.version]
            .compactMap { $0?.lowercased() }
        return values.contains { value in
            value.contains("://") ||
                value.contains("@") ||
                value.contains("/users/") ||
                value.contains("passcode") ||
                value.contains("secret") ||
                value.contains("token")
        }
    }
}
