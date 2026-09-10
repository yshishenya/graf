import AppKit
import AVKit
import TwoBrainRecShared

/// One managed preview: deletion and account changes can release its audio source.
@MainActor
public final class LocalRecordingPlayer: NSObject, NSWindowDelegate {
    public static let shared = LocalRecordingPlayer()
    private var window: NSWindow?
    private var player: AVPlayer?
    private var itemID: String?

    public func open(url: URL, itemID: String) {
        close()
        let player = AVPlayer(url: url)
        let view = AVPlayerView(frame: NSRect(x: 0, y: 0, width: 540, height: 120))
        view.player = player
        view.controlsStyle = .floating
        let window = NSWindow(contentRect: view.frame, styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.title = "Локальная запись"
        window.isReleasedWhenClosed = false
        window.delegate = self
        window.contentView = view
        window.center()
        window.makeKeyAndOrderFront(nil)
        self.window = window
        self.player = player
        self.itemID = itemID
        player.play()
    }

    public func reconcile(items: [DesktopUploadQueueItem]) {
        guard let itemID else { return }
        guard let item = items.first(where: { $0.id == itemID }), !item.lifecycleBlocksContent else {
            close()
            return
        }
    }

    public func windowWillClose(_ notification: Notification) { close() }

    public func revoke(itemIDs: [String]) {
        if let itemID, itemIDs.contains(itemID) { close() }
    }

    public func close() {
        player?.pause()
        player?.replaceCurrentItem(with: nil)
        (window?.contentView as? AVPlayerView)?.player = nil
        window?.delegate = nil
        window?.close()
        player = nil
        window = nil
        itemID = nil
    }
}
