import Foundation
import TwoBrainRecShared

/// One raw queue item kept as bytes so a lossy decode can never rewrite the
/// document. This is the shared read-only snapshot for the dry run, cleanup,
/// eviction and status probes.
struct LocalCacheRawQueueItem: Sendable {
    let rawData: Data
    let rawDirectoryId: String?
    let rawId: String?

    var fingerprintIdentity: String? {
        rawDirectoryId ?? rawId
    }

    func decodeItem() -> DesktopUploadQueueItem? {
        guard !rawData.isEmpty else { return nil }
        return try? Self.decoder.decode(DesktopUploadQueueItem.self, from: rawData)
    }

    private static var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}

struct LocalCacheRawQueueSnapshot: Sendable {
    /// SHA-256 of the exact bytes read. Cleanup compares it before acting so a
    /// queue mutation cannot silently change deletion/purge/conflict authority.
    let fingerprint: String
    let updatedAt: Date?
    let items: [LocalCacheRawQueueItem]
    let deletionOperations: [RecordingDeletionOperation]
    let lastAuthenticatedContext: RecordingAuthenticatedContext?

    func persistedScope(matching sessionFingerprint: String?) -> RecordingDeletionScope? {
        guard let context = lastAuthenticatedContext else { return nil }
        guard let sessionFingerprint else { return context.scope }
        return context.sessionFingerprint == sessionFingerprint ? context.scope : nil
    }

    func item(withID id: String) -> DesktopUploadQueueItem? {
        for raw in items {
            guard let item = raw.decodeItem(), item.id == id else { continue }
            return item
        }
        return nil
    }

    static func read(from url: URL) throws -> LocalCacheRawQueueSnapshot {
        let data = try Data(contentsOf: url, options: [.mappedIfSafe])
        guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let rawItems = root["items"] as? [Any] else {
            throw LocalCacheQueueSnapshotError.unreadable
        }

        let items = rawItems.map { element -> LocalCacheRawQueueItem in
            let dictionary = element as? [String: Any]
            let encoded = (try? JSONSerialization.data(withJSONObject: element)) ?? Data()
            return LocalCacheRawQueueItem(
                rawData: encoded,
                rawDirectoryId: dictionary?["directoryId"] as? String,
                rawId: dictionary?["id"] as? String
            )
        }

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let operations = try (root["deletionOperations"] as? [Any] ?? []).map { element -> RecordingDeletionOperation in
            guard let encoded = try? JSONSerialization.data(withJSONObject: element),
                  let operation = try? decoder.decode(RecordingDeletionOperation.self, from: encoded) else {
                throw LocalCacheQueueSnapshotError.deletionOperationsUndecodable
            }
            return operation
        }
        let context: RecordingAuthenticatedContext? = {
            guard let raw = root["lastAuthenticatedContext"],
                  let encoded = try? JSONSerialization.data(withJSONObject: raw) else { return nil }
            return try? decoder.decode(RecordingAuthenticatedContext.self, from: encoded)
        }()
        let updatedAt = (root["updatedAt"] as? String).flatMap(ServerTimestamp.parse)

        return LocalCacheRawQueueSnapshot(
            fingerprint: LocalCacheFingerprint.sha256Hex(data),
            updatedAt: updatedAt,
            items: items,
            deletionOperations: operations,
            lastAuthenticatedContext: context
        )
    }
}

enum LocalCacheQueueSnapshotError: Error {
    case unreadable
    case deletionOperationsUndecodable
}
