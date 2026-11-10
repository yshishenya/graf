import Foundation
import TwoBrainRecShared

/// Decides whether a microphone disconnect must become a visible capture
/// degradation instead of silently leaving a stale "recording" status.
public enum RecordingMicrophoneDisconnectPolicy {
    public static func shouldMarkDegraded(
        disconnectedDeviceID: String?,
        selectedDeviceID: String?,
        sessionState: CaptureSessionState?
    ) -> Bool {
        guard let disconnectedDeviceID,
              let selectedDeviceID,
              !selectedDeviceID.isEmpty,
              disconnectedDeviceID == selectedDeviceID
        else {
            return false
        }
        return sessionState == .active || sessionState == .paused
    }

    public static let recoveryAction =
        "Системный звук продолжает записываться. Остановите запись и выберите микрофон снова."
}
