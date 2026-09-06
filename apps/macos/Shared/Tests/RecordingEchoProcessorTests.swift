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
        XCTAssertEqual(processor.terminalError, .invalidFrame)
    }

    func testFiniteOvershootIsClampedAtSharedAECBoundary() throws {
        let processor = try RecordingEchoProcessor()
        var render = [Float](repeating: 0, count: RecordingEchoProcessor.frameSamples)
        var capture = render
        render[0] = 1.25
        capture[0] = -1.5

        for _ in 0..<1_000 {
            let output = try processor.process(render: render, capture: capture)
            XCTAssertEqual(output.count, RecordingEchoProcessor.frameSamples)
            XCTAssertTrue(output.allSatisfy(\.isFinite))
        }
        XCTAssertNil(processor.terminalError)
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

    func testSustainedProcessingP95StaysWithinTenMillisecondFrameBudget() throws {
        let processor = try RecordingEchoProcessor()
        let silence = [Float](repeating: 0, count: RecordingEchoProcessor.frameSamples)
        for _ in 0..<100 {
            _ = try processor.process(render: silence, capture: silence)
        }
        var durations: [Double] = []
        durations.reserveCapacity(1_000)
        for _ in 0..<1_000 {
            let startedAt = ProcessInfo.processInfo.systemUptime
            _ = try processor.process(render: silence, capture: silence)
            durations.append((ProcessInfo.processInfo.systemUptime - startedAt) * 1_000)
        }
        durations.sort()

        XCTAssertLessThan(durations[949], 10)
    }
}
#endif
