import AppKit
import AVKit
import Foundation
@testable import TwoBrainRecAppCore
import XCTest

final class LocalRecordingPlayerTests: XCTestCase {
    @MainActor
    func testManagedSourceIsReleasedOnDeletionAccessLossAndReplacement() throws {
        _ = NSApplication.shared
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { LocalRecordingPlayer.shared.close(); try? FileManager.default.removeItem(at: root) }
        let url = root.appendingPathComponent("synthetic.wav")
        let format = try XCTUnwrap(AVAudioFormat(standardFormatWithSampleRate: 8000, channels: 1))
        let buffer = try XCTUnwrap(AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 8000))
        buffer.frameLength = 8000
        buffer.floatChannelData![0].initialize(repeating: 0, count: 8000)
        let file = try AVAudioFile(forWriting: url, settings: format.settings)
        try file.write(from: buffer)
        let preview = LocalRecordingPlayer.shared
        preview.open(url: url, itemID: "synthetic-one")
        let window = try XCTUnwrap(NSApp.windows.first { $0.title == "Локальная запись" && $0.isVisible })
        let view = try XCTUnwrap(window.contentView as? AVPlayerView)
        let player = try XCTUnwrap(view.player)
        XCTAssertNotNil(player.currentItem)
        preview.revoke(itemIDs: ["unrelated"])
        XCTAssertTrue(window.isVisible)
        let start = Date()
        preview.revoke(itemIDs: ["synthetic-one"])
        XCTAssertLessThan(Date().timeIntervalSince(start), 1)
        XCTAssertNil(player.currentItem)
        XCTAssertNil(view.player)
        XCTAssertFalse(window.isVisible)

        preview.open(url: url, itemID: "synthetic-two")
        let second = try XCTUnwrap(NSApp.windows.first { $0.title == "Локальная запись" && $0.isVisible })
        let secondPlayer = try XCTUnwrap((second.contentView as? AVPlayerView)?.player)
        var denied = custodyFixtureQueueItem(id: "synthetic-two")
        denied.serverTruth.accessState = "revoked"
        preview.reconcile(items: [denied])
        XCTAssertNil(secondPlayer.currentItem)
        XCTAssertFalse(second.isVisible)

        preview.open(url: url, itemID: "synthetic-three")
        let third = try XCTUnwrap(NSApp.windows.first { $0.title == "Локальная запись" && $0.isVisible })
        let thirdPlayer = try XCTUnwrap((third.contentView as? AVPlayerView)?.player)
        preview.open(url: url, itemID: "synthetic-four")
        XCTAssertNil(thirdPlayer.currentItem)
        XCTAssertFalse(third.isVisible)
        preview.reconcile(items: [])
        XCTAssertFalse(NSApp.windows.contains { $0.title == "Локальная запись" && $0.isVisible })
    }
}
