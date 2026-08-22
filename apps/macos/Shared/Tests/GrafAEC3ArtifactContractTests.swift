#if canImport(XCTest)
import Foundation
import GrafAEC3
import XCTest

final class GrafAEC3ArtifactContractTests: XCTestCase {
    func testPinnedDependencyIdentityAndAECOnlyConfiguration() throws {
        let lock = try Self.readRepositoryFile("apps/macos/Native/GrafAEC3/upstream.lock")
        let source = try Self.readRepositoryFile("apps/macos/Native/GrafAEC3/Sources/GrafAEC3.cpp")

        XCTAssertTrue(lock.contains("webrtc_audio_processing_version=2.1"))
        XCTAssertTrue(lock.contains("webrtc_audio_processing_commit=846fe90a289f58b7c9303a635142aa2c7caa93e5"))
        XCTAssertTrue(lock.contains("webrtc_revision=M131"))
        XCTAssertTrue(lock.contains("architectures=arm64,x86_64"))
        XCTAssertTrue(lock.contains("library_kind=static"))
        XCTAssertTrue(source.contains("config.echo_canceller.enabled = true"))
        XCTAssertTrue(source.contains("config.echo_canceller.enforce_high_pass_filtering = false"))
        for disabled in [
            "high_pass_filter",
            "noise_suppression",
            "gain_controller1",
            "gain_controller2",
            "transient_suppression",
        ] {
            XCTAssertTrue(source.contains("config.\(disabled).enabled = false"))
        }
        XCTAssertFalse(source.contains("AecDump"))
    }

    func testCABIRequiresExactTenMillisecondFrames() throws {
        XCTAssertEqual(Int(GRAF_AEC3_SAMPLE_RATE), 48_000)
        XCTAssertEqual(Int(GRAF_AEC3_CHANNEL_COUNT), 1)
        XCTAssertEqual(Int(GRAF_AEC3_FRAME_SAMPLES), 480)
        XCTAssertEqual(String(cString: graf_aec3_library_version()), "2.1")
        XCTAssertEqual(
            String(cString: graf_aec3_source_commit()),
            "846fe90a289f58b7c9303a635142aa2c7caa93e5"
        )
        XCTAssertEqual(graf_aec3_optional_processing_enabled(), 0)

        let processor = try XCTUnwrap(graf_aec3_create())
        defer { graf_aec3_destroy(processor) }
        let render = [Float](repeating: 0, count: 480)
        let capture = [Float](repeating: 0, count: 480)
        var output = [Float](repeating: 0, count: 480)
        let exactStatus = render.withUnsafeBufferPointer { renderBuffer in
            capture.withUnsafeBufferPointer { captureBuffer in
                output.withUnsafeMutableBufferPointer { outputBuffer in
                    graf_aec3_process(
                        processor,
                        renderBuffer.baseAddress,
                        captureBuffer.baseAddress,
                        480,
                        0,
                        outputBuffer.baseAddress
                    )
                }
            }
        }
        XCTAssertEqual(exactStatus, GRAF_AEC3_OK)

        let shortStatus = render.withUnsafeBufferPointer { renderBuffer in
            capture.withUnsafeBufferPointer { captureBuffer in
                output.withUnsafeMutableBufferPointer { outputBuffer in
                    graf_aec3_process(
                        processor,
                        renderBuffer.baseAddress,
                        captureBuffer.baseAddress,
                        479,
                        0,
                        outputBuffer.baseAddress
                    )
                }
            }
        }
        XCTAssertEqual(shortStatus, GRAF_AEC3_INVALID_ARGUMENT)
    }

    private static func readRepositoryFile(_ relativePath: String) throws -> String {
        try String(
            contentsOf: repositoryRoot().appendingPathComponent(relativePath),
            encoding: .utf8
        )
    }

    private static func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            let marker = candidate.appendingPathComponent("apps/macos/Native/GrafAEC3/upstream.lock")
            if FileManager.default.fileExists(atPath: marker.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "GrafAEC3ArtifactContractTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
#endif
