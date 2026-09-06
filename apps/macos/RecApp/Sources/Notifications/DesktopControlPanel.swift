import AppKit
import Combine
import SwiftUI
import TwoBrainRecShared

public enum DesktopControlAction: Equatable { case start, pause, resume, stop, settings, localRecordings, permissions }

public struct DesktopControlSnapshot: Equatable {
    public var session: CaptureSession?
    public var transitioning = false
    public var startAvailable = false
    public var blocker: String?
    public var microphone = "Проверяем доступ"
    public var systemAudio = "Проверяем доступ"
    public var uploadItems: [DesktopUploadQueueItem] = []
    public init() {}
    public var active: Bool { session.map { CaptureStatusItem.showsStopButton(for: $0) } == true }
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
    public var onAction: (DesktopControlAction) -> Void = { _ in }
    private var pausedAt: Date?
    private var pausedSeconds: TimeInterval = 0
    public init() {}
    public func update(_ value: DesktopControlSnapshot, now: Date = Date()) {
        if value.session?.id != snapshot.session?.id { pausedAt = nil; pausedSeconds = 0 }
        if value.session?.state == .paused && pausedAt == nil { pausedAt = now }
        if value.session?.state != .paused, let pause = pausedAt {
            pausedSeconds += max(0, now.timeIntervalSince(pause)); pausedAt = nil
        }
        snapshot = value
    }
    public func elapsed(now: Date = Date()) -> String {
        guard let start = snapshot.session?.startedAt else { return "0:00" }
        let end = snapshot.session?.stoppedAt ?? pausedAt ?? now
        let seconds = Int(max(0, end.timeIntervalSince(start) - pausedSeconds))
        return String(format: "%d:%02d", seconds / 60, seconds % 60)
    }
    public func send(_ action: DesktopControlAction) { onAction(action) }
}

@MainActor
public struct DesktopControlPanel: View {
    @ObservedObject var model: DesktopControlModel
    var compact = false
    public init(model: DesktopControlModel, compact: Bool = false) { self.model = model; self.compact = compact }
    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("GRAF").font(.headline)
                Spacer()
                if model.snapshot.active {
                    TimelineView(.periodic(from: .now, by: 1)) { context in
                        Text(model.elapsed(now: context.date)).monospacedDigit().accessibilityHidden(true)
                    }
                }
                if !compact {
                    Button { model.send(.settings) } label: { Image(systemName: "gearshape") }
                        .accessibilityLabel("Настройки").help("Настройки")
                }
            }
            if model.snapshot.active {
                CaptureStatusItem(session: model.snapshot.session,
                    stopDisabled: model.snapshot.transitioning, pauseDisabled: model.snapshot.transitioning,
                    onStop: { model.send(.stop) }, onPause: { model.send(.pause) }, onResume: { model.send(.resume) })
            } else {
                Text(model.snapshot.transitioning ? "Подготавливаем запись…" : model.snapshot.startAvailable ? "Готово к записи" : "Проверьте доступ к записи")
                Button("Начать запись") { model.send(.start) }
                    .disabled(!model.snapshot.startAvailable || model.snapshot.transitioning)
            }
            if !compact || model.snapshot.active {
                Label("Микрофон: \(model.snapshot.microphone)", systemImage: "mic")
                Label("Системный звук: \(model.snapshot.systemAudio)", systemImage: "speaker.wave.2")
                if let blocker = model.snapshot.blocker, !blocker.isEmpty {
                    Text(blocker).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                    Button("Проверить запись") { model.send(.permissions) }
                }
                if let issue = model.snapshot.localIssues.first {
                    Divider()
                    Text("На этом Mac").font(.headline)
                    Text(issue.title)
                    Text(issue.detail).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                    Button("Открыть локальные записи") { model.send(.localRecordings) }
                }
            }
        }.font(.callout).padding(16).frame(width: compact ? 290 : 360)
        .background(.regularMaterial).accessibilityElement(children: .contain)
    }
}

@MainActor
public final class DesktopRecordingWidget {
    private let panel: NSPanel
    private var observation: AnyCancellable?
    private var screensObservation: AnyCancellable?
    private func keepVisible() {
        guard let screen = NSScreen.screens.first(where: { $0.visibleFrame.intersects(panel.frame) }) ?? NSScreen.main else { return }
        let bounds = screen.visibleFrame
        panel.setFrameOrigin(NSPoint(x: max(bounds.minX, min(panel.frame.minX, bounds.maxX - panel.frame.width)),
                                     y: max(bounds.minY, min(panel.frame.minY, bounds.maxY - panel.frame.height))))
    }
    public init(model: DesktopControlModel) {
        panel = NSPanel(contentRect: NSRect(x: 30, y: 80, width: 290, height: 140),
            styleMask: [.titled, .fullSizeContentView, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.title = "Управление записью GRAF"
        panel.titleVisibility = .hidden
        panel.titlebarAppearsTransparent = true
        panel.isMovableByWindowBackground = true
        panel.isFloatingPanel = true
        panel.hidesOnDeactivate = false
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isReleasedWhenClosed = false
        panel.setFrameAutosaveName("graf-recording-control-widget")
        panel.contentViewController = NSHostingController(rootView: DesktopControlPanel(model: model, compact: true))
        screensObservation = NotificationCenter.default.publisher(for: NSApplication.didChangeScreenParametersNotification).sink { [weak self] _ in self?.keepVisible() }
        observation = model.$snapshot.sink { [weak self] snapshot in
            guard let self else { return }
            if snapshot.active {
                self.keepVisible()
                self.panel.orderFrontRegardless()
            } else { self.panel.orderOut(nil) }
        }
    }
}

public extension Notification.Name {
    static let grafOpenLocalRecordingControls = Notification.Name("pro.graf.openLocalRecordingControls")
}
