import Foundation
@testable import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class RecordingEchoProcessorTests: XCTestCase {
    func testPinnedAEC3ProcessesOnlyExactFiniteFrames() throws {
        let processor = try RecordingEchoProcessor()
        let silence = [Float](repeating: 0, count: RecordingEchoProcessor.frameSamples)

        let output = try processor.process(render: silence, capture: silence)

        XCTAssertEqual(output.count, 480)
        XCTAssertTrue(output.allSatisfy { $0 == 0 })
        XCTAssertThrowsError(try processor.process(render: [0], capture: [0])) {
            XCTAssertEqual($0 as? RecordingEchoProcessorError, .invalidFrame)
        }
        var invalid = silence
        invalid[0] = .nan
        XCTAssertThrowsError(try processor.process(render: invalid, capture: silence)) {
            XCTAssertEqual($0 as? RecordingEchoProcessorError, .invalidFrame)
        }
    }

    func testPinnedIdentityAndOptionalProcessingContract() throws {
        XCTAssertEqual(RecordingEchoProcessor.libraryVersion, "2.1")
        XCTAssertEqual(
            RecordingEchoProcessor.sourceCommit,
            "846fe90a289f58b7c9303a635142aa2c7caa93e5"
        )

        let processor = try RecordingEchoProcessor()
        let statistics = try processor.statistics()
        XCTAssertNil(statistics.delayMs)
        XCTAssertNil(statistics.echoReturnLossDb)
        XCTAssertNil(statistics.echoReturnLossEnhancementDb)
    }
}
#endif
