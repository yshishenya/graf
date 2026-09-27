import AppKit
import SwiftUI

/// Measures only GRAF's own capture controls. It never inspects other apps.
/// The card owns placement; this passive marker owns no recording state.
@MainActor
public struct DesktopNotificationProtectedRegion: NSViewRepresentable {
    private let card: DesktopNotificationCardPresenter
    public init(card: DesktopNotificationCardPresenter = DesktopNotificationPresenter.shared.card) {
        self.card = card
    }

    public func makeNSView(context: Context) -> NSView {
        let marker = CaptureRegionMarker(card: card)
        card.protectedFramesProvider = { [weak marker] in
            guard let marker, let window = marker.window,
                  window.isVisible, !window.isMiniaturized, window.isOnActiveSpace,
                  !marker.isHiddenOrHasHiddenAncestor, !marker.visibleRect.isEmpty else { return [] }
            return [window.convertToScreen(marker.convert(marker.visibleRect, to: nil))]
        }
        return marker
    }

    public func updateNSView(_ nsView: NSView, context: Context) {
        (nsView as? CaptureRegionMarker)?.schedulePlacement()
    }
}

@MainActor
private final class CaptureRegionMarker: NSView {
    private let card: DesktopNotificationCardPresenter
    private var placementScheduled = false

    init(card: DesktopNotificationCardPresenter) {
        self.card = card
        super.init(frame: .zero)
        setAccessibilityElement(false)
    }
    required init?(coder: NSCoder) { nil }
    override func hitTest(_ point: NSPoint) -> NSView? { nil }
    deinit { NotificationCenter.default.removeObserver(self) }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        NotificationCenter.default.removeObserver(self)
        if let window {
            for name in [NSWindow.didMoveNotification, NSWindow.didResizeNotification,
                         NSWindow.didMiniaturizeNotification, NSWindow.didDeminiaturizeNotification,
                         NSWindow.didChangeOcclusionStateNotification] {
                NotificationCenter.default.addObserver(self, selector: #selector(windowChanged), name: name, object: window)
            }
        }
        schedulePlacement()
    }

    override func setFrameSize(_ newSize: NSSize) {
        super.setFrameSize(newSize)
        schedulePlacement()
    }
    override func setFrameOrigin(_ newOrigin: NSPoint) {
        super.setFrameOrigin(newOrigin)
        schedulePlacement()
    }
    @objc private func windowChanged(_ notification: Notification) { schedulePlacement() }

    func schedulePlacement() {
        guard !placementScheduled else { return }
        placementScheduled = true
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            self.placementScheduled = false
            self.card.reposition()
        }
    }
}
