import Foundation
import TwoBrainRecShared

public struct MeetingDetectionTelemetryConfiguration: Equatable, Sendable {
    public let clientVersion: String
    public let osVersionMajor: String
    public let candidateFilterVersion: String

    public init(
        clientVersion: String = "local-macos",
        osVersionMajor: String = ProcessInfo.processInfo.operatingSystemVersion.majorVersion.description,
        candidateFilterVersion: String = MeetingDetectionCandidateFilter.version
    ) {
        self.clientVersion = clientVersion
        self.osVersionMajor = osVersionMajor
        self.candidateFilterVersion = candidateFilterVersion
    }
}

public final class MeetingDetectionTelemetryRollupStore: @unchecked Sendable {
    public typealias Clock = @Sendable () -> Date

    private let directoryURL: URL
    private let configuration: MeetingDetectionTelemetryConfiguration
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder
    private let calendar: Calendar
    private let clock: Clock
    private let queue = DispatchQueue(label: "pro.2brain.graf.meeting-detection-rollups", qos: .utility)

    public init(
        directoryURL: URL? = nil,
        configuration: MeetingDetectionTelemetryConfiguration = MeetingDetectionTelemetryConfiguration(),
        encoder: JSONEncoder = MeetingDetectionCoding.encoder(),
        decoder: JSONDecoder = MeetingDetectionCoding.decoder(),
        calendar: Calendar = Calendar(identifier: .gregorian),
        clock: @escaping Clock = Date.init
    ) {
        self.directoryURL = directoryURL ?? Self.defaultRollupDirectoryURL()
        self.configuration = configuration
        self.encoder = encoder
        self.decoder = decoder
        var utcCalendar = calendar
        utcCalendar.timeZone = TimeZone(secondsFromGMT: 0) ?? .gmt
        self.calendar = utcCalendar
        self.clock = clock
    }

    public static func defaultRollupDirectoryURL() -> URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ??
            FileManager.default.temporaryDirectory
        return base
            .appendingPathComponent("GRAF", isDirectory: true)
            .appendingPathComponent(MeetingDetectionAppModule.applicationSupportDirectoryName, isDirectory: true)
            .appendingPathComponent("TelemetryRollups", isDirectory: true)
    }

    public func recordObservation(
        _ observation: MeetingDetectionAppObservation,
        decision: MeetingDetectionCandidateDecision,
        registryVersion: String,
        settings: MeetingDetectionSettings,
        now: Date? = nil
    ) throws -> MeetingDetectionTelemetryDocument {
        try queue.sync {
            let timestamp = now ?? clock()
            var document = try loadOrCreateDocument(
                registryVersion: registryVersion,
                settings: settings,
                day: timestamp
            )
            let rollup = Self.rollup(from: observation, decision: decision)
            document.unknownNativeAppRollups.append(rollup)
            document.resourceRollup.diskBytesWritten += 1
            try save(document, for: timestamp)
            _ = try pruneLocked(now: timestamp, maxAgeDays: 14, maxTotalBytes: 1_000_000)
            return document
        }
    }

    public func pendingDocuments() throws -> [MeetingDetectionTelemetryDocument] {
        try queue.sync {
            try rollupFileURLs().compactMap { url in
                try decoder.decode(MeetingDetectionTelemetryDocument.self, from: Data(contentsOf: url))
            }
        }
    }

    public func pendingDocumentURLs() throws -> [URL] {
        try queue.sync {
            try rollupFileURLs()
        }
    }

    public func removeDocument(at url: URL) throws {
        try queue.sync {
            if FileManager.default.fileExists(atPath: url.path) {
                try FileManager.default.removeItem(at: url)
            }
        }
    }

    @discardableResult
    public func prune(now: Date? = nil, maxAgeDays: Int = 14, maxTotalBytes: Int = 1_000_000) throws -> [URL] {
        try queue.sync {
            try pruneLocked(now: now ?? clock(), maxAgeDays: maxAgeDays, maxTotalBytes: maxTotalBytes)
        }
    }

    public func documentURL(for day: Date) -> URL {
        directoryURL.appendingPathComponent("rollup-\(Self.dayFormatter.string(from: calendar.startOfDay(for: day))).json")
    }

    public static func uploadableCopy(
        of document: MeetingDetectionTelemetryDocument
    ) -> MeetingDetectionTelemetryDocument? {
        var copy = document
        copy.unknownNativeAppRollups = document.unknownNativeAppRollups.filter {
            $0.uploadEligibility == "server_candidate_upload" &&
                $0.identityMode == "raw_candidate_allowed" &&
                $0.bundleId != nil
        }
        guard !copy.unknownNativeAppRollups.isEmpty || !copy.targetRollups.isEmpty else {
            return nil
        }
        return copy
    }

    private func loadOrCreateDocument(
        registryVersion: String,
        settings: MeetingDetectionSettings,
        day: Date
    ) throws -> MeetingDetectionTelemetryDocument {
        let url = documentURL(for: day)
        if FileManager.default.fileExists(atPath: url.path) {
            return try decoder.decode(MeetingDetectionTelemetryDocument.self, from: Data(contentsOf: url))
        }
        let start = calendar.startOfDay(for: day)
        let end = calendar.date(byAdding: .day, value: 1, to: start) ?? day
        return MeetingDetectionTelemetryDocument(
            clientVersion: configuration.clientVersion,
            osVersionMajor: configuration.osVersionMajor,
            registryVersion: registryVersion,
            candidateFilterVersion: configuration.candidateFilterVersion,
            createdAt: day,
            rollupWindow: MeetingDetectionRollupWindow(startedAt: start, endedAt: end),
            policy: settings.policySummary
        )
    }

    private func save(_ document: MeetingDetectionTelemetryDocument, for day: Date) throws {
        try FileManager.default.createDirectory(at: directoryURL, withIntermediateDirectories: true)
        try encoder.encode(document).write(to: documentURL(for: day), options: [.atomic])
    }

    private func rollupFileURLs() throws -> [URL] {
        guard FileManager.default.fileExists(atPath: directoryURL.path) else {
            return []
        }
        return try FileManager.default.contentsOfDirectory(
            at: directoryURL,
            includingPropertiesForKeys: [.contentModificationDateKey, .fileSizeKey],
            options: [.skipsHiddenFiles]
        )
        .filter { $0.lastPathComponent.hasPrefix("rollup-") && $0.pathExtension == "json" }
        .sorted { $0.lastPathComponent < $1.lastPathComponent }
    }

    private func pruneLocked(now: Date, maxAgeDays: Int, maxTotalBytes: Int) throws -> [URL] {
        let cutoff = calendar.date(byAdding: .day, value: -maxAgeDays, to: now) ?? now
        var removed: [URL] = []
        var files = try rollupFileURLs().map { url in
            (url: url, attributes: try FileManager.default.attributesOfItem(atPath: url.path))
        }
        for file in files {
            let fileDay = Self.dayDate(from: file.url) ??
                (file.attributes[.modificationDate] as? Date ?? .distantPast)
            if fileDay < cutoff {
                try FileManager.default.removeItem(at: file.url)
                removed.append(file.url)
            }
        }
        files = try rollupFileURLs().map { url in
            (url: url, attributes: try FileManager.default.attributesOfItem(atPath: url.path))
        }
        var totalBytes = files.reduce(0) { partial, file in
            partial + ((file.attributes[.size] as? NSNumber)?.intValue ?? 0)
        }
        for file in files.sorted(by: { lhs, rhs in
            let left = lhs.attributes[.modificationDate] as? Date ?? .distantPast
            let right = rhs.attributes[.modificationDate] as? Date ?? .distantPast
            return left < right
        }) where totalBytes > maxTotalBytes {
            let size = (file.attributes[.size] as? NSNumber)?.intValue ?? 0
            try FileManager.default.removeItem(at: file.url)
            totalBytes -= size
            removed.append(file.url)
        }
        return removed
    }

    private static func rollup(
        from observation: MeetingDetectionAppObservation,
        decision: MeetingDetectionCandidateDecision
    ) -> MeetingDetectionUnknownNativeAppRollup {
        let isUploadable = decision.shouldUploadCandidateIdentity
        let suppressionReasons = decision.suppressionReasons
        let candidateReasons = decision.candidateReasons.isEmpty ? [.stableMicDuration] : decision.candidateReasons
        return MeetingDetectionUnknownNativeAppRollup(
            identityMode: isUploadable ? "raw_candidate_allowed" : "redacted",
            uploadEligibility: isUploadable ? "server_candidate_upload" : uploadEligibility(for: suppressionReasons),
            candidateScore: decision.candidateScore,
            candidateReasons: candidateReasons,
            suppressionReasons: suppressionReasons,
            bundleId: isUploadable ? observation.bundleID : nil,
            displayName: isUploadable ? observation.displayName : nil,
            signingTeamId: isUploadable ? observation.signingTeamID : nil,
            version: isUploadable ? observation.version : nil,
            stableObservationCount: observation.stableObservationCount,
            durationBuckets: .bucket(for: observation.activeDurationSeconds),
            manualRecordNearbyCount: observation.manualRecordNearbyCount,
            calendarOrJoinHintCount: observation.calendarOrJoinHintCount
        )
    }

    private static func uploadEligibility(
        for suppressionReasons: [MeetingDetectionSuppressionReason]
    ) -> String {
        suppressionReasons.contains(.knownNonTarget) ? "local_only_non_target" : "local_only_low_score"
    }

    private static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    private static func dayDate(from url: URL) -> Date? {
        let name = url.deletingPathExtension().lastPathComponent
        guard name.hasPrefix("rollup-") else {
            return nil
        }
        return dayFormatter.date(from: String(name.dropFirst("rollup-".count)))
    }
}
