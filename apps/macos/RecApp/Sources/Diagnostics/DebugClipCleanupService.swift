import Foundation

public struct DebugClipRecord: Codable, Equatable, Sendable {
    public var id: String
    public var path: String
    public var createdAt: Date
    public var developmentOnly: Bool
}

public struct DebugClipCleanupResult: Codable, Equatable, Sendable {
    public var removedIds: [String]
    public var remainingIds: [String]
    public var releaseEnabled: Bool
}

public struct DebugClipCleanupService: Sendable {
    public var releaseBuildAllowsDebugClips: Bool

    public init(releaseBuildAllowsDebugClips: Bool = false) {
        self.releaseBuildAllowsDebugClips = releaseBuildAllowsDebugClips
    }

    public func cleanup(records: [DebugClipRecord]) -> DebugClipCleanupResult {
        let removable = records.filter(\.developmentOnly)
        let remaining = records.filter { !$0.developmentOnly }
        return DebugClipCleanupResult(
            removedIds: removable.map(\.id),
            remainingIds: remaining.map(\.id),
            releaseEnabled: releaseBuildAllowsDebugClips
        )
    }
}
