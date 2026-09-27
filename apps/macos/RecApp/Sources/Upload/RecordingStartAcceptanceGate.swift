import Foundation
import TwoBrainRecShared

/// A live local gate. Cached artifact completeness cannot accept a recording start.
enum RecordingStartAcceptanceGate {
    enum Refusal: Error {
        case manifestUnavailable
        case identityMismatch
        case pending
    }

    static func check(_ item: DesktopUploadQueueItem) throws {
        try check(manifestURL: URL(fileURLWithPath: item.manifestPath),
                  sessionId: item.sessionId, directoryId: item.directoryId)
    }

    static func check(manifestURL: URL, sessionId: String, directoryId: String) throws {
        let manifest: LocalRecordingManifest
        do {
            manifest = try LocalRecordingManifestService().read(from: manifestURL)
        } catch {
            // Includes unknown acceptance values; never turn a decoding failure into legacy nil.
            throw Refusal.manifestUnavailable
        }
        guard manifest.sessionId == sessionId, manifest.directoryId == directoryId else {
            throw Refusal.identityMismatch
        }
        guard manifest.startAcceptance != .pending else { throw Refusal.pending }
        // accepted and historical nil only clear this gate; existing eligibility gates still apply.
    }

    static func allows(_ item: DesktopUploadQueueItem) -> Bool {
        do {
            try check(item)
            return true
        } catch {
            return false
        }
    }
}
