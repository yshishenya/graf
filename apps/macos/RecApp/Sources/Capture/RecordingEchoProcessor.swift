import Foundation
import GrafAEC3

public enum RecordingEchoProcessorError: Error, Equatable, Sendable {
    case unavailable
    case invalidFrame
    case renderFailed
    case captureFailed
    case closed
    case internalFailure
}

public struct RecordingEchoStatistics: Equatable, Sendable {
    public let delayMs: Int?
    public let echoReturnLossDb: Double?
    public let echoReturnLossEnhancementDb: Double?
}

/// Owns the only WebRTC AEC3 instance used by one recording.
public final class RecordingEchoProcessor: @unchecked Sendable {
    public static let frameSamples = 480
    public static let sampleRate = 48_000
    public static let libraryVersion = String(cString: graf_aec3_library_version())
    public static let sourceCommit = String(cString: graf_aec3_source_commit())

    private var processor: OpaquePointer?
    public private(set) var terminalError: RecordingEchoProcessorError?

    public init() throws {
        guard graf_aec3_optional_processing_enabled() == 0,
              let processor = graf_aec3_create()
        else {
            throw RecordingEchoProcessorError.unavailable
        }
        self.processor = processor
    }

    deinit {
        graf_aec3_destroy(processor)
    }

    public func process(render: [Float], capture: [Float]) throws -> [Float] {
        guard render.count == Self.frameSamples,
              capture.count == Self.frameSamples,
              render.allSatisfy(\.isFinite),
              capture.allSatisfy(\.isFinite)
        else {
            terminalError = .invalidFrame
            throw RecordingEchoProcessorError.invalidFrame
        }
        guard let processor else { throw RecordingEchoProcessorError.closed }
        let boundedRender = render.map { min(1, max(-1, $0)) }
        let boundedCapture = capture.map { min(1, max(-1, $0)) }

        var output = [Float](repeating: 0, count: Self.frameSamples)
        let status = boundedRender.withUnsafeBufferPointer { renderBuffer in
            boundedCapture.withUnsafeBufferPointer { captureBuffer in
                output.withUnsafeMutableBufferPointer { outputBuffer in
                    graf_aec3_process(
                        processor,
                        renderBuffer.baseAddress,
                        captureBuffer.baseAddress,
                        UInt32(Self.frameSamples),
                        0,
                        outputBuffer.baseAddress
                    )
                }
            }
        }
        guard status == GRAF_AEC3_OK else {
            self.processor = nil
            graf_aec3_destroy(processor)
            let error = Self.error(for: status)
            terminalError = error
            throw error
        }
        return output
    }

    public func statistics() throws -> RecordingEchoStatistics {
        guard let processor else { throw RecordingEchoProcessorError.closed }
        var values = GrafAEC3Statistics()
        let status = graf_aec3_get_statistics(processor, &values)
        guard status == GRAF_AEC3_OK else { throw Self.error(for: status) }
        return RecordingEchoStatistics(
            delayMs: values.has_delay_ms == 0 ? nil : Int(values.delay_ms),
            echoReturnLossDb: values.has_echo_return_loss_db == 0 ? nil : values.echo_return_loss_db,
            echoReturnLossEnhancementDb: values.has_echo_return_loss_enhancement_db == 0
                ? nil
                : values.echo_return_loss_enhancement_db
        )
    }

    private static func error(for status: GrafAEC3Status) -> RecordingEchoProcessorError {
        switch status {
        case GRAF_AEC3_INVALID_ARGUMENT:
            .invalidFrame
        case GRAF_AEC3_RENDER_FAILED:
            .renderFailed
        case GRAF_AEC3_CAPTURE_FAILED:
            .captureFailed
        case GRAF_AEC3_CLOSED:
            .closed
        default:
            .internalFailure
        }
    }
}
