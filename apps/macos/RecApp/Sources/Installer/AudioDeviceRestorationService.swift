import Foundation
import TwoBrainRecShared

public enum AudioDeviceRestorationState: String, Codable, Sendable {
    case notNeeded = "not_needed"
    case restored = "restored"
    case partial = "partial"
    case failed = "failed"
}

public struct AudioDeviceRestorationAttempt: Equatable, Sendable {
    public let deviceRole: String
    public let deviceId: String?
    public let state: AudioDeviceRestorationState
    public let note: String
}

public struct AudioDeviceRestorationResult: Equatable, Sendable {
    public let attempts: [AudioDeviceRestorationAttempt]
    public let manualRemediation: [String]
    public let isComplete: Bool

    public init(
        attempts: [AudioDeviceRestorationAttempt],
        manualRemediation: [String],
        isComplete: Bool
    ) {
        self.attempts = attempts
        self.manualRemediation = manualRemediation
        self.isComplete = isComplete
    }
}

public protocol AudioDeviceRestorationExecutor: Sendable {
    func restoreInputDevice(id: String) throws
    func restoreOutputDevice(id: String) throws
}

public enum AudioDeviceRestorationError: Error {
    case noIdProvided
    case restoreFailed(String)
}

public final class AudioDeviceRestorationService {
    public typealias InputExecutor = @Sendable (String) throws -> Void
    public typealias OutputExecutor = @Sendable (String) throws -> Void

    private let executeInput: InputExecutor
    private let executeOutput: OutputExecutor

    public init(
        executeInput: @escaping InputExecutor = { _ in },
        executeOutput: @escaping OutputExecutor = { _ in }
    ) {
        self.executeInput = executeInput
        self.executeOutput = executeOutput
    }

    public convenience init(executor: AudioDeviceRestorationExecutor) {
        self.init(
            executeInput: { id in
                try executor.restoreInputDevice(id: id)
            },
            executeOutput: { id in
                try executor.restoreOutputDevice(id: id)
            }
        )
    }

    public func restore(previousInputId: String?, previousOutputId: String?) -> AudioDeviceRestorationResult {
        var attempts: [AudioDeviceRestorationAttempt] = []
        var manual: [String] = []
        var restoredInputs = false
        var restoredOutputs = false

        if let previousInputId, !previousInputId.isEmpty {
            let attempt = attemptRestore(
                role: "input",
                deviceId: previousInputId,
                executor: executeInput
            )
            attempts.append(attempt)
            if attempt.state == .restored {
                restoredInputs = true
            } else {
                manual.append("Set input device to '\(previousInputId)' in system settings.")
            }
        }

        if let previousOutputId, !previousOutputId.isEmpty {
            let attempt = attemptRestore(
                role: "output",
                deviceId: previousOutputId,
                executor: executeOutput
            )
            attempts.append(attempt)
            if attempt.state == .restored {
                restoredOutputs = true
            } else {
                manual.append("Set output device to '\(previousOutputId)' in system settings.")
            }
        }

        let isComplete = (previousInputId == nil || restoredInputs) &&
            (previousOutputId == nil || restoredOutputs)

        if attempts.isEmpty {
            manual.append("No prior devices recorded. Verify defaults manually in System Settings.")
        } else if !isComplete {
            manual.append(
                "Some devices were not restored automatically. Open System Settings > Sound > Output/Input."
            )
        }

        let state: AudioDeviceRestorationState = {
            if isComplete {
                return restoredInputs || restoredOutputs ? .restored : .notNeeded
            }
            if manual.isEmpty {
                return .partial
            }
            return .partial
        }()

        if state == .partial || state == .failed {
            manual.append(contentsOf: attempts
                .filter { $0.state == .failed }
                .map { "Verify access to capture route for \($0.deviceRole) device." })
        }

        return AudioDeviceRestorationResult(
            attempts: attempts,
            manualRemediation: manual,
            isComplete: isComplete
        )
    }

    private func attemptRestore(role: String, deviceId: String, executor: InputExecutor) -> AudioDeviceRestorationAttempt {
        do {
            try executor(deviceId)
            return AudioDeviceRestorationAttempt(
                deviceRole: role,
                deviceId: deviceId,
                state: .restored,
                note: "Restored \(role) '\(deviceId)'"
            )
        } catch {
            return AudioDeviceRestorationAttempt(
                deviceRole: role,
                deviceId: deviceId,
                state: .failed,
                note: "\(role.capitalized) restore failed: \(error.localizedDescription)"
            )
        }
    }
}
