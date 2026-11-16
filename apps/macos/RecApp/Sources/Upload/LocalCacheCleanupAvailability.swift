import Foundation
import TwoBrainRecShared

/// Read-only availability probe for the manual cleanup buttons. It runs
/// off-main and hides the action when the transcription WAV is not a regular
/// file inside the recordings root or when a completed receipt already exists
/// for either action.
public struct LocalCacheCleanupAvailabilityProbe: Sendable {
    private let queueURL: URL
    private let recordingsRootURL: URL
    private let receiptDirectoryURL: URL?

    public init(
        queueURL: URL,
        recordingsRootURL: URL,
        receiptDirectoryURL: URL? = nil
    ) {
        self.queueURL = queueURL
        self.recordingsRootURL = recordingsRootURL
        self.receiptDirectoryURL = receiptDirectoryURL
    }

    public func offerableItemIDs(
        among items: [DesktopUploadQueueItem]
    ) async -> Set<String> {
        let recordingsRootURL = recordingsRootURL
        let receiptDirectory = receiptDirectoryURL
            ?? queueURL.deletingLastPathComponent()
                .appendingPathComponent("LocalCacheEviction/receipts", isDirectory: true)
        let candidates = items.filter {
            LocalCacheCleanupCandidatePolicy.cleanupBytes(for: $0) != nil
        }
        return await Task.detached(priority: .utility) {
            var result: Set<String> = []
            for item in candidates {
                guard LocalCacheArtifactProbe.isInside(
                    item.transcriptionAudioPath,
                    root: recordingsRootURL
                ),
                    case .regular = LocalCacheFileIdentity.state(
                        atPath: item.transcriptionAudioPath
                    ) else {
                    continue
                }
                if Self.hasCompletedReceipt(item: item, receiptDirectory: receiptDirectory) {
                    continue
                }
                result.insert(item.id)
            }
            return result
        }.value
    }

    private static func hasCompletedReceipt(
        item: DesktopUploadQueueItem,
        receiptDirectory: URL
    ) -> Bool {
        let localFingerprint = LocalCacheFingerprint.recording(item.directoryId)
        let mediaFingerprint = LocalCacheFingerprint.revision(item.localMediaRevisionId)
        for action in LocalCacheCleanupAction.allCases {
            let store = LocalCacheCleanupReceiptStore(
                receiptDirectoryURL: receiptDirectory,
                action: action,
                localRecordingFingerprint: localFingerprint,
                mediaRevisionFingerprint: mediaFingerprint
            )
            guard let receipt = try? store.load() else {
                // A present but unreadable receipt is not trustworthy evidence;
                // hide the action rather than offering another cleanup.
                if FileManager.default.fileExists(atPath: store.fileURL.path) {
                    return true
                }
                continue
            }
            if receipt.state == .completed || receipt.state == .noop {
                return true
            }
        }
        return false
    }
}
