import Foundation
import XCTest
@testable import TwoBrainRecAppCore

final class LocalRecordingFootprintTests: XCTestCase {
    private var root: URL!

    override func setUpWithError() throws {
        root = FileManager.default.temporaryDirectory
            .appendingPathComponent("graf-footprint-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    }

    override func tearDownWithError() throws {
        if let root {
            try? FileManager.default.removeItem(at: root)
        }
    }

    func testMeasureUsesActualFiles() throws {
        try Data(repeating: 1, count: 1_024).write(to: root.appendingPathComponent("one.bin"))
        try Data(repeating: 2, count: 2_048).write(to: root.appendingPathComponent("two.bin"))

        let snapshot = try LocalRecordingFootprintMeasurer.measure(
            at: root,
            now: Date(timeIntervalSince1970: 100)
        )

        XCTAssertEqual(snapshot.fileCount, 2)
        XCTAssertGreaterThanOrEqual(snapshot.bytes, 3_072)
        XCTAssertEqual(snapshot.measuredAt, Date(timeIntervalSince1970: 100))
        XCTAssertEqual(snapshot.rootPath, root.path)
    }

    func testMissingRootIsZero() throws {
        let missing = root.appendingPathComponent("missing", isDirectory: true)
        let snapshot = try LocalRecordingFootprintMeasurer.measure(at: missing)
        XCTAssertEqual(snapshot.bytes, 0)
        XCTAssertEqual(snapshot.fileCount, 0)
    }

    func testRootThatIsAFileFailsClosed() throws {
        let file = root.appendingPathComponent("not-a-directory")
        try Data().write(to: file)

        XCTAssertThrowsError(try LocalRecordingFootprintMeasurer.measure(at: file)) { error in
            XCTAssertEqual(error as? LocalRecordingFootprintError, .rootIsNotDirectory)
        }
    }

    func testRootSymlinkFailsClosed() throws {
        let outside = FileManager.default.temporaryDirectory
            .appendingPathComponent("graf-footprint-root-target-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: outside, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: outside) }
        let link = root.appendingPathComponent("root-link", isDirectory: true)
        try FileManager.default.createSymbolicLink(at: link, withDestinationURL: outside)

        XCTAssertThrowsError(try LocalRecordingFootprintMeasurer.measure(at: link)) { error in
            XCTAssertEqual(error as? LocalRecordingFootprintError, .rootIsNotDirectory)
        }
    }

    func testSymlinksAreNotCountedOrFollowed() throws {
        try Data(repeating: 3, count: 128).write(to: root.appendingPathComponent("real.bin"))
        let outside = FileManager.default.temporaryDirectory
            .appendingPathComponent("graf-footprint-outside-\(UUID().uuidString).bin")
        try Data(repeating: 4, count: 100_000).write(to: outside)
        defer { try? FileManager.default.removeItem(at: outside) }
        try FileManager.default.createSymbolicLink(
            at: root.appendingPathComponent("link.bin"),
            withDestinationURL: outside
        )

        let snapshot = try LocalRecordingFootprintMeasurer.measure(at: root)
        XCTAssertEqual(snapshot.fileCount, 1)
        XCTAssertLessThan(snapshot.bytes, 100_000)
    }

    func testHiddenFilesAreSkipped() throws {
        try Data(repeating: 5, count: 64).write(to: root.appendingPathComponent("visible.bin"))
        try Data(repeating: 6, count: 1_000_000).write(to: root.appendingPathComponent(".hidden.bin"))

        let snapshot = try LocalRecordingFootprintMeasurer.measure(at: root)
        XCTAssertEqual(snapshot.fileCount, 1)
        XCTAssertLessThan(snapshot.bytes, 1_000_000)
    }
}
