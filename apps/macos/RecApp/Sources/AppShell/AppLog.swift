import Foundation

enum AppLog {
    private static let writer = BoundedLogFileWriter(fileURL: fileURL)
    private static let queue = DispatchQueue(label: "pro.2brain.graf.log", qos: .utility)
    nonisolated(unsafe) private static let formatter = ISO8601DateFormatter()

    static let fileURL: URL = {
        if let override = ProcessInfo.processInfo.environment["GRAF_LOG_DIRECTORY"],
           !override.isEmpty {
            return URL(fileURLWithPath: override, isDirectory: true)
                .appendingPathComponent("graf.log")
        }
        let base = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/GRAF", isDirectory: true)
        return base.appendingPathComponent("graf.log")
    }()

    static func writeRaw(event: String, detail: String) {
        let safeDetail = sanitize(detail)
        queue.async {
            writeLine("\(timestamp()) event=\(event) detail=\(safeDetail)\n")
        }
    }

    static func writeCaptureTiming(_ detail: String) {
        let event = detail.hasPrefix("recording_writer_progress ")
            ? "capture.writer_progress" : "capture.timing_anomaly"
        writeRaw(event: event, detail: detail)
    }

    static func flush() {
        queue.sync {}
    }

    private static func sanitize(_ detail: String) -> String {
        String(detail.prefix(4_096))
            .replacingOccurrences(of: "\n", with: " ")
            .replacingOccurrences(of: "\r", with: " ")
            .split(separator: " ")
            .map { token in
                let value = String(token)
                let lowered = value.lowercased()
                if value.hasPrefix("/") || value.contains("=/") || value.contains("file://") ||
                    lowered.contains("http://") || lowered.contains("https://") ||
                    lowered.hasPrefix("www.") {
                    return "<redacted-path>"
                }
                if lowered.hasPrefix("authorization=") ||
                    lowered.hasPrefix("cookie=") ||
                    lowered.hasPrefix("token=") ||
                    lowered.hasPrefix("password=") ||
                    lowered.contains("bearer ") ||
                    lowered.contains("-----begin") {
                    return "<redacted-secret>"
                }
                return value
            }
            .joined(separator: " ")
    }

    private static func writeLine(_ line: String) {
        do {
            try writer.append(line)
        } catch {
            print("GRAF log write failed: \(error)")
        }
    }

    private static func timestamp() -> String {
        formatter.string(from: Date())
    }
}
