import Foundation
import TwoBrainRecShared

public final class MacOSAudioOwnershipLogStream: @unchecked Sendable {
    private let configuration: MacOSAudioOwnershipLogStreamConfiguration
    private let parser: MacOSAudioOwnershipParser
    private let stateQueue = DispatchQueue(label: "pro.2brain.graf.audio-ownership-log-stream")
    private var process: Process?

    public init(
        configuration: MacOSAudioOwnershipLogStreamConfiguration = MacOSAudioOwnershipLogStreamConfiguration(),
        parser: MacOSAudioOwnershipParser = MacOSAudioOwnershipParser()
    ) {
        self.configuration = configuration
        self.parser = parser
    }

    public func events() -> AsyncStream<MacOSAudioOwnershipEvent> {
        AsyncStream { continuation in
            let process = Process()
            let output = Pipe()
            process.executableURL = configuration.executableURL
            process.arguments = configuration.arguments
            process.standardOutput = output
            process.standardError = Pipe()

            stateQueue.sync {
                self.process = process
            }

            do {
                try process.run()
            } catch {
                continuation.finish()
                return
            }

            let reader = output.fileHandleForReading
            let parser = parser
            let readTask = Task.detached(priority: .utility) {
                var pending = ""
                while !Task.isCancelled {
                    let data = reader.availableData
                    if data.isEmpty {
                        break
                    }
                    pending += String(decoding: data, as: UTF8.self)
                    let lines = pending.split(separator: "\n", omittingEmptySubsequences: false)
                    pending = lines.last.map(String.init) ?? ""
                    for line in lines.dropLast() {
                        if let event = parser.parse(line: String(line)) {
                            continuation.yield(event)
                        }
                    }
                }
                if let event = parser.parse(line: pending) {
                    continuation.yield(event)
                }
                continuation.finish()
            }

            continuation.onTermination = { [weak self] _ in
                readTask.cancel()
                try? reader.close()
                self?.stop()
            }
        }
    }

    public func stop() {
        stateQueue.sync {
            guard let process else { return }
            if process.isRunning {
                process.terminate()
            }
            self.process = nil
        }
    }
}
