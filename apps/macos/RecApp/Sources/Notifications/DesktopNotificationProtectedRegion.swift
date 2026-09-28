import AppKit
import SwiftUI

private struct DesktopNotificationCardKey: EnvironmentKey {
    static let defaultValue: DesktopNotificationCardPresenter? = nil
}

extension EnvironmentValues {
    var desktopNotificationCard: DesktopNotificationCardPresenter? {
        get { self[DesktopNotificationCardKey.self] }
        set { self[DesktopNotificationCardKey.self] = newValue }
    }
}

/// Measures only GRAF's own capture controls. It never inspects other apps.
/// The card owns placement; this passive marker owns no recording state.
@MainActor
public struct DesktopNotificationProtectedRegion: NSViewRepresentable {
    @Environment(\.desktopNotificationCard) private var environmentCard
    private let card: DesktopNotificationCardPresenter?
    public init(card: DesktopNotificationCardPresenter? = nil) {
        self.card = card
    }

    public func makeNSView(context: Context) -> NSView {
        CaptureRegionMarker(card: card ?? environmentCard ?? DesktopNotificationPresenter.shared.card)
    }

    public func updateNSView(_ nsView: NSView, context: Context) {
        (nsView as? CaptureRegionMarker)?.update(card: card ?? environmentCard ?? DesktopNotificationPresenter.shared.card)
    }

    public static func dismantleNSView(_ nsView: NSView, coordinator: ()) {
        (nsView as? CaptureRegionMarker)?.detach()
    }
}

@MainActor
private final class CaptureRegionMarker: NSView {
    private var card: DesktopNotificationCardPresenter
    private let registrationID = UUID()
    private var registered = false
    private var lastFrame: NSRect?
    private var ancestorIDs: [ObjectIdentifier] = []
    private var dismantled = false

    init(card: DesktopNotificationCardPresenter) {
        self.card = card
        super.init(frame: .zero)
        setAccessibilityElement(false)
    }
    required init?(coder: NSCoder) { nil }
    override func hitTest(_ point: NSPoint) -> NSView? { nil }
    deinit {
        let owner = card
        let id = registrationID
        NotificationCenter.default.removeObserver(self)
        Task { @MainActor in owner.unregisterProtectedRegion(id: id) }
    }

    private var screenFrame: NSRect? {
        guard !dismantled, let window, window.isVisible, !window.isMiniaturized,
              window.isOnActiveSpace, !isHiddenOrHasHiddenAncestor else { return nil }
        // Non-clipping AppKit views may report a visibleRect larger than bounds.
        // Protect only this control, never its surrounding empty viewport.
        let visible = visibleRect.intersection(bounds)
        guard !visible.isEmpty, !visible.isNull else { return nil }
        return window.convertToScreen(convert(visible, to: nil))
    }

    func update(card: DesktopNotificationCardPresenter) {
        if self.card !== card {
            self.card.unregisterProtectedRegion(id: registrationID)
            self.card = card
            registered = false
        }
        refreshObservers()
    }

    func detach() {
        dismantled = true
        NotificationCenter.default.removeObserver(self)
        ancestorIDs = []
        card.unregisterProtectedRegion(id: registrationID)
        registered = false
        lastFrame = nil
    }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        refreshObservers()
    }

    override func viewDidMoveToSuperview() {
        super.viewDidMoveToSuperview()
        refreshObservers()
    }

    private func refreshObservers() {
        let center = NotificationCenter.default
        center.removeObserver(self)
        ancestorIDs = []
        guard !dismantled else { return }
        if let window {
            if !registered {
                card.registerProtectedRegion(id: registrationID) { [weak self] in self?.screenFrame }
                registered = true
            }
            for name in [NSWindow.didMoveNotification, NSWindow.didResizeNotification,
                         NSWindow.didMiniaturizeNotification, NSWindow.didDeminiaturizeNotification,
                         NSWindow.didChangeOcclusionStateNotification, NSWindow.didUpdateNotification] {
                center.addObserver(self, selector: #selector(geometryChanged), name: name, object: window)
            }
            var ancestor = superview
            while let view = ancestor {
                ancestorIDs.append(ObjectIdentifier(view))
                // NSView posts these by default. Observe only our own ancestors
                // without changing shared view flags or retaining the hierarchy.
                for name in [NSView.frameDidChangeNotification, NSView.boundsDidChangeNotification] {
                    center.addObserver(self, selector: #selector(geometryChanged), name: name, object: view)
                }
                if let scroll = view as? NSScrollView {
                    center.addObserver(self, selector: #selector(geometryChanged),
                                       name: NSScrollView.didLiveScrollNotification, object: scroll)
                }
                ancestor = view.superview
            }
        } else {
            card.unregisterProtectedRegion(id: registrationID)
            registered = false
        }
        geometryChanged()
    }

    override func setFrameSize(_ newSize: NSSize) {
        super.setFrameSize(newSize)
        geometryChanged()
    }
    override func setFrameOrigin(_ newOrigin: NSPoint) {
        super.setFrameOrigin(newOrigin)
        geometryChanged()
    }
    override func viewDidHide() {
        super.viewDidHide()
        geometryChanged()
    }
    override func viewDidUnhide() {
        super.viewDidUnhide()
        geometryChanged()
    }

    @objc private func geometryChanged() {
        guard !dismantled else { return }
        var currentIDs: [ObjectIdentifier] = []
        var ancestor = superview
        while let view = ancestor {
            currentIDs.append(ObjectIdentifier(view))
            ancestor = view.superview
        }
        if window != nil, currentIDs != ancestorIDs {
            refreshObservers()
            return
        }
        let frame = screenFrame
        guard frame != lastFrame else { return }
        lastFrame = frame
        card.scheduleProtectedPlacement()
    }
}
