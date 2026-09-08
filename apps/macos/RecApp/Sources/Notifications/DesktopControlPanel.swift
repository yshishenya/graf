import AppKit
import Combine
import SwiftUI
import TwoBrainRecShared

public enum DesktopControlAction: Equatable { case start, pause, resume, stop, settings, localRecordings, permissions }

public struct DesktopControlSnapshot: Equatable {
    public var session: CaptureSession?
    public var calendarContextEventID: String?
    public var transitioning = false
    public var stopping = false
    public var startAvailable = false
    public var blocker: String?
    public var permissionBlocker = false
    public var microphone = "Проверяем доступ"
    public var systemAudio = "Проверяем доступ"
    public var uploadItems: [DesktopUploadQueueItem] = []
    public init() {}
    public var active: Bool { stopping || session.map { CaptureStatusItem.showsStopButton(for: $0) } == true }
    public var completedRecording: Bool {
        !active && session.map { [.stopped, .finalized, .failed].contains($0.state) } == true
    }
    public var latestCustody: DesktopUploadCustodySummary? {
        guard let id = session?.id else { return nil }
        return DesktopUploadCustodySummary.summaries(for: uploadItems.filter { $0.sessionId == id }).first
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
    @Published private(set) var visibleResultSessionID: String?
    func setVisibleResultSessionID(_ id: String?) { visibleResultSessionID = id }
    public var onAction: (DesktopControlAction) -> Void = { _ in }
    public init() {}
    public func update(_ value: DesktopControlSnapshot) { snapshot = value }
    public func elapsed(now: Date = Date()) -> String {
        guard let start = snapshot.session?.startedAt else { return "0:00" }
        let end = snapshot.session?.stoppedAt ?? now
        let seconds = Int(max(0, end.timeIntervalSince(start)))
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
                        .buttonStyle(.borderless).accessibilityLabel("Настройки").help("Настройки")
                }
            }
            if model.snapshot.stopping {
                Text("Останавливаем запись…").fontWeight(.medium)
                Text("Сохраняем запись на этом Mac.").font(.caption).foregroundStyle(.secondary)
            } else if model.snapshot.active {
                CaptureStatusItem(session: model.snapshot.session,
                    stopDisabled: model.snapshot.transitioning, pauseDisabled: model.snapshot.transitioning,
                    onStop: { model.send(.stop) }, onPause: { model.send(.pause) }, onResume: { model.send(.resume) })
            } else {
                if model.snapshot.completedRecording {
                    Text("Запись остановлена").fontWeight(.medium)
                    if let custody = model.snapshot.latestCustody {
                        Text(custody.title).font(.callout).foregroundStyle(.secondary)
                            .accessibilityLabel(custody.title + ". " + custody.detail).help(custody.detail)
                    }
                    Button("Открыть локальные записи") { model.send(.localRecordings) }
                        .buttonStyle(.borderless)
                } else {
                    Text(model.snapshot.transitioning ? "Подготавливаем запись…" : model.snapshot.startAvailable ? "Готово к записи" : "Запись пока недоступна")
                        .foregroundStyle(.secondary)
                }
                Button { model.send(.start) } label: {
                    Label("Начать запись", systemImage: "record.circle").frame(maxWidth: .infinity)
                }
                .buttonStyle(DesktopWebButtonStyle(.primary))
                .disabled(!model.snapshot.startAvailable || model.snapshot.transitioning)
            }
            if model.snapshot.active && !model.snapshot.stopping {
                HStack(spacing: 12) {
                    Label(model.snapshot.session?.state == .paused ? "Микрофон на паузе" : "Микрофон", systemImage: "mic")
                        .accessibilityValue(model.snapshot.microphone)
                    Label("Звук Mac", systemImage: "speaker.wave.2")
                        .accessibilityValue(model.snapshot.systemAudio)
                }.font(.caption).foregroundStyle(.secondary)
                if model.snapshot.session?.state == .paused {
                    Text("Пауза не отключает запись звука Mac.").font(.caption).foregroundStyle(.secondary)
                }
            }
            if let blocker = model.snapshot.blocker, !blocker.isEmpty {
                Text(blocker).font(.caption).foregroundStyle(.orange)
                    .lineLimit(2).help(blocker).accessibilityLabel(blocker)
            }
            if model.snapshot.active && !model.snapshot.stopping {
                if ["Нет свежих аудиоданных", "Нужен доступ"].contains(model.snapshot.microphone) {
                    Text("Микрофон: \(model.snapshot.microphone)").font(.caption).foregroundStyle(.orange)
                }
                if ["Нет свежих аудиоданных", "Нужен доступ"].contains(model.snapshot.systemAudio) {
                    Text("Звук Mac: \(model.snapshot.systemAudio)").font(.caption).foregroundStyle(.orange)
                }
            }
        }
        .font(.callout).padding(16).frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .contain)
    }

    var details: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let blocker = model.snapshot.blocker, !blocker.isEmpty {
                Text(blocker).font(.callout).fixedSize(horizontal: false, vertical: true)
                if !model.snapshot.active {
                    Button(model.snapshot.recoveryAction == .localRecordings ? "Открыть локальные записи" : "Проверить доступ") {
                        model.send(model.snapshot.recoveryAction)
                    }.buttonStyle(.borderless)
                }
            }
            if let issue = model.snapshot.localIssues.first {
                Button { model.send(.localRecordings) } label: {
                    HStack(spacing: 10) {
                        Image(systemName: "exclamationmark.circle").foregroundStyle(.orange)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(issue.title).font(.callout.weight(.medium))
                            Text("Посмотреть запись").font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer(minLength: 0)
                        Image(systemName: "chevron.right").font(.caption).foregroundStyle(.secondary)
                    }.contentShape(Rectangle())
                }.buttonStyle(.plain).accessibilityLabel(issue.title + ". Открыть локальные записи")
            }
            DisclosureGroup("Источники звука") {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Микрофон: \(model.snapshot.microphone)")
                    Text("Звук Mac: \(model.snapshot.systemAudio)")
                }.font(.caption).foregroundStyle(.secondary).padding(.top, 6)
            }.font(.caption).foregroundStyle(.secondary)
        }.padding(.horizontal, 16).padding(.vertical, 12)
    }
}

public enum DesktopPanelPlacement {
    public static func frame(_ frame: NSRect, within bounds: NSRect) -> NSRect {
        let width = min(frame.width, bounds.width), height = min(frame.height, bounds.height)
        return NSRect(x: max(bounds.minX, min(frame.minX, bounds.maxX - width)),
                      y: max(bounds.minY, min(frame.minY, bounds.maxY - height)), width: width, height: height)
    }
}

@MainActor
public final class DesktopRecordingWidget {
    private let panel: NSPanel
    private var observation: AnyCancellable?
    private var screensObservation: AnyCancellable?
    private var resizeObservation: AnyCancellable?
    private var hideCompletion: DispatchWorkItem?
    private var wasActive = false
    private func keepVisible() {
        let screen = panel.screen ?? NSScreen.screens.max { left, right in
            let a = left.visibleFrame.intersection(panel.frame), b = right.visibleFrame.intersection(panel.frame)
            return (a.isNull ? 0 : a.width * a.height) < (b.isNull ? 0 : b.width * b.height)
        } ?? NSScreen.main
        guard let screen else { return }
        let bounds = screen.visibleFrame.insetBy(dx: 8, dy: 8)
        var requested = panel.frame
        if let hosting = panel.contentViewController as? NSHostingController<DesktopControlPanel> {
            let width = min(290, bounds.width)
            let fitted = hosting.sizeThatFits(in: NSSize(width: width, height: bounds.height))
            requested.size = panel.frameRect(forContentRect: NSRect(x: 0, y: 0, width: width, height: fitted.height)).size
        }
        let frame = DesktopPanelPlacement.frame(requested, within: bounds)
        if panel.frame != frame { panel.setFrame(frame, display: true) }
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
        let hosting = NSHostingController(rootView: DesktopControlPanel(model: model, compact: true))
        hosting.sizingOptions = []
        panel.contentViewController = hosting
        resizeObservation = NotificationCenter.default.publisher(for: NSWindow.didResizeNotification, object: panel)
            .merge(with: NotificationCenter.default.publisher(for: NSWindow.didChangeScreenNotification, object: panel))
            .sink { [weak self] _ in self?.keepVisible() }
        screensObservation = NotificationCenter.default.publisher(for: NSApplication.didChangeScreenParametersNotification).sink { [weak self] _ in self?.keepVisible() }
        observation = model.$snapshot.sink { [weak self] snapshot in
            guard let self else { return }
            if snapshot.active {
                self.hideCompletion?.cancel()
                model.setVisibleResultSessionID(nil)
                self.keepVisible()
                self.panel.orderFrontRegardless()
            } else if self.wasActive {
                // Keep the confirmed local result visible without a system banner.
                self.keepVisible()
                model.setVisibleResultSessionID(self.panel.isVisible ? snapshot.session?.id : nil)
                let hide = DispatchWorkItem { [weak self, weak model] in
                    self?.panel.orderOut(nil)
                    model?.setVisibleResultSessionID(nil)
                }
                self.hideCompletion = hide
                DispatchQueue.main.asyncAfter(deadline: .now() + 8, execute: hide)
            }
            DispatchQueue.main.async { [weak self] in self?.keepVisible() }
            self.wasActive = snapshot.active
        }
    }
}

public extension Notification.Name {
    static let grafOpenLocalRecordingControls = Notification.Name("pro.graf.openLocalRecordingControls")
}
