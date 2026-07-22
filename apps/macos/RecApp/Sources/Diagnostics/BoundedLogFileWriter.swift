import Foundation

public final class BoundedLogFileWriter: @unchecked Sendable {
    public static let defaultMaximumBytes = 4 * 1_024 * 1_024

    private let fileURL: URL
    private let maximumBytes: Int
    private let fileManager: FileManager
    private let lock = NSLock()

    public init(
        fileURL: URL,
        maximumBytes: Int = BoundedLogFileWriter.defaultMaximumBytes,
        fileManager: FileManager = .default
    ) {
        self.fileURL = fileURL
        self.maximumBytes = max(1, maximumBytes)
        self.fileManager = fileManager
    }

    public func append(_ line: String) throws {
        lock.lock()
        defer { lock.unlock() }

        try fileManager.createDirectory(
            at: fileURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        let data = Data(line.utf8.suffix(maximumBytes))
        let currentBytes = fileSize(at: fileURL)
        if currentBytes + data.count > maximumBytes {
            try rotate()
        }
        if fileManager.fileExists(atPath: fileURL.path) {
            let handle = try FileHandle(forWritingTo: fileURL)
            defer { try? handle.close() }
            try handle.seekToEnd()
            try handle.write(contentsOf: data)
        } else {
            try data.write(to: fileURL, options: .atomic)
        }
    }

    private func rotate() throws {
        guard fileManager.fileExists(atPath: fileURL.path) else { return }
        let backupURL = fileURL.appendingPathExtension("1")
        if fileManager.fileExists(atPath: backupURL.path) {
            try fileManager.removeItem(at: backupURL)
        }
        try fileManager.moveItem(at: fileURL, to: backupURL)
        if fileSize(at: backupURL) > maximumBytes {
            let tail = try Data(contentsOf: backupURL).suffix(maximumBytes)
            try Data(tail).write(to: backupURL, options: .atomic)
        }
    }

    private func fileSize(at url: URL) -> Int {
        let attributes = try? fileManager.attributesOfItem(atPath: url.path)
        return (attributes?[.size] as? NSNumber)?.intValue ?? 0
    }
}
