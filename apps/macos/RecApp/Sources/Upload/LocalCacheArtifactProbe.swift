import CryptoKit
import Foundation
import TwoBrainRecShared

/// A read-only, player-free projection of the local recording package. It is
/// evidence about files, never a UI authorization or a deletion receipt.
enum LocalCacheArtifactProbe {
    static func inspect(
        item: DesktopUploadQueueItem,
        recordingsRootURL: URL,
        computeHashes: Bool = false
    ) -> LocalArtifactFacts {
        let paths = [
            item.directoryPath,
            item.manifestPath,
            item.reviewAudioPath,
            item.transcriptionAudioPath,
        ]
        guard paths.allSatisfy({ isInside($0, root: recordingsRootURL) }) else {
            return LocalArtifactFacts(error: .outsideRoot)
        }

        var facts = LocalArtifactFacts()
        let manifest = regularFile(at: item.manifestPath)
        let review = regularFile(at: item.reviewAudioPath)
        let transcription = regularFile(at: item.transcriptionAudioPath)

        facts.manifestPresent = manifest.present
        facts.reviewAudioPresent = review.present
        facts.transcriptionAudioPresent = transcription.present
        facts.transcriptionBytes = transcription.bytes
        if computeHashes, transcription.present {
            facts.transcriptionSha256 = sha256Hex(at: item.transcriptionAudioPath)
        }

        if manifest.present, item.artifactProfile.manifestSizeBytes > 0,
           manifest.bytes != item.artifactProfile.manifestSizeBytes {
            facts.error = .integrity
        }
        if (manifest.present && !manifest.readable) ||
            (review.present && !review.readable) ||
            (transcription.present && !transcription.readable) {
            facts.error = .unreadable
        }

        if let expected = LocalCacheEligibility.expectedPlaybackBytes(for: item) {
            facts.reviewPlaybackAvailable = review.present && review.readable && review.bytes == expected
            if review.present, review.bytes != expected {
                facts.error = .integrity
            }
        }

        if let expected = LocalCacheEligibility.expectedTranscriptionBytes(for: item),
           transcription.present, transcription.bytes != expected {
            facts.error = .integrity
        }

        if computeHashes, transcription.present, facts.transcriptionSha256 == nil {
            facts.error = .unreadable
        }

        return facts
    }

    static func isInside(_ path: String, root: URL) -> Bool {
        guard !path.isEmpty, path != "metadata-only" else { return false }
        let resolvedRoot = root.standardizedFileURL.resolvingSymlinksInPath().path
        let resolved = URL(fileURLWithPath: path)
            .standardizedFileURL
            .resolvingSymlinksInPath()
            .path
        if resolved == resolvedRoot { return true }
        let prefix = resolvedRoot.hasSuffix("/") ? resolvedRoot : resolvedRoot + "/"
        return resolved.hasPrefix(prefix)
    }

    private struct FileState {
        let present: Bool
        let readable: Bool
        let bytes: Int64?
    }

    private static func regularFile(at path: String) -> FileState {
        guard !path.isEmpty, path != "metadata-only" else {
            return FileState(present: false, readable: false, bytes: nil)
        }
        let url = URL(fileURLWithPath: path)
        guard let values = try? url.resourceValues(forKeys: [
            .isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey,
        ]),
            values.isRegularFile == true,
            values.isSymbolicLink != true else {
            return FileState(present: false, readable: false, bytes: nil)
        }
        return FileState(
            present: true,
            readable: FileManager.default.isReadableFile(atPath: path),
            bytes: values.fileSize.map { Int64($0) }
        )
    }

    private static func sha256Hex(at path: String) -> String? {
        guard let handle = FileHandle(forReadingAtPath: path) else { return nil }
        defer { try? handle.close() }
        var hasher = SHA256()
        while true {
            let chunk = handle.readData(ofLength: 1 << 20)
            if chunk.isEmpty { break }
            hasher.update(data: chunk)
        }
        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }
}
