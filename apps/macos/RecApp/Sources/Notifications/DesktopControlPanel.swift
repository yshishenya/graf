import AppKit
import Combine
import TwoBrainRecShared

public enum DesktopControlAction: Equatable { case start, pause, resume, stop, settings, localRecordings, permissions; case localRecording(String) }

public struct DesktopControlSnapshot: Equatable {
    public var session: CaptureSession?
    public var calendarContextEventID: String?
    public var transitioning = false
    public var stopping = false
    public var blocker: String?
    public var permissionBlocker = false
    public var uploadItems: [DesktopUploadQueueItem] = []
    public init() {}
    public var active: Bool { stopping || session.map { CaptureStatusItem.showsStopButton(for: $0) } == true }
    public var completedRecording: Bool {
        !active && session.map { [.stopped, .finalized, .failed].contains($0.state) } == true
    }
    public var recoveryAction: DesktopControlAction {
        !permissionBlocker && (completedRecording || session?.state == .failed) ? .localRecordings : .permissions
    }
    public var localIssues: [DesktopUploadCustodySummary] {
        DesktopUploadCustodySummary.summaries(for: uploadItems.filter {
            $0.serverTruth.finalizedAt == nil && $0.state != .terminalDeleted
        }).filter { $0.primaryProjection.requiresUserAttention }
    }
}

@MainActor
public final class DesktopControlModel: ObservableObject {
    public static let shared = DesktopControlModel()
    @Published public private(set) var snapshot = DesktopControlSnapshot()
    @Published public private(set) var selectedRecordingSessionID: String?
    @Published public private(set) var recordingNavigationRequest = 0
    public func showRecording(_ sessionID: String?) {
        selectedRecordingSessionID = sessionID
        recordingNavigationRequest += 1
    }
    public var onAction: ((DesktopControlAction) -> Void)?
    public init() {}
    public func update(_ value: DesktopControlSnapshot) { snapshot = value }
    public func elapsed(now: Date = Date()) -> String {
        guard let start = snapshot.session?.startedAt else { return "0:00" }
        let end = snapshot.session?.stoppedAt ?? now
        let seconds = Int(max(0, end.timeIntervalSince(start)))
        return String(format: "%d:%02d", seconds / 60, seconds % 60)
    }
    @discardableResult
    public func send(_ action: DesktopControlAction) -> Bool {
        guard let onAction else { return false }
        onAction(action)
        return true
    }
}

public extension Notification.Name {
    static let grafOpenLocalRecordingControls = Notification.Name("pro.graf.openLocalRecordingControls")
}
