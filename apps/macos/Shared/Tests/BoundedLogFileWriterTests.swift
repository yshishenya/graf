import Foundation
@testable import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class BoundedLogFileWriterTests: XCTestCase {
    func testWriterRotatesAndBoundsCurrentAndPreviousLogs() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("bounded-log-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let fileURL = root.appendingPathComponent("graf.log")
        let writer = BoundedLogFileWriter(fileURL: fileURL, maximumBytes: 64)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data(repeating: 65, count: 256).write(to: fileURL)

        for index in 0..<20 {
            try writer.append("event=retry index=\(index)\n")
        }

        let backupURL = fileURL.appendingPathExtension("1")
        XCTAssertTrue(FileManager.default.fileExists(atPath: backupURL.path))
        XCTAssertLessThanOrEqual(try fileSize(fileURL), 64)
        XCTAssertLessThanOrEqual(try fileSize(backupURL), 64)
    }

    private func fileSize(_ url: URL) throws -> Int {
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        return try XCTUnwrap(attributes[.size] as? NSNumber).intValue
    }
}
#endif
