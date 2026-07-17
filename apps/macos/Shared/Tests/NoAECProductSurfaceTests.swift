import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class NoAECProductSurfaceTests: XCTestCase {
    private let activeV5ProductSources = [
        "apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift",
        "apps/macos/RecApp/Sources/Capture/CanonicalRecordingWriter.swift",
        "apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift",
        "apps/macos/RecApp/Sources/Capture/LocalRecordingStore.swift",
        "apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift",
        "apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift",
        "apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleCoreService.swift",
        "apps/macos/RecApp/App/TwoBrainRecApp.swift"
    ]

    func testActiveV5CaptureSurfaceContainsNoRetiredProcessing() throws {
        let root = try repositoryRoot()
        let forbiddenTerms = [
            ["A", "EC"].joined(),
            ["Apple", "Voice", "Processing"].joined(),
            ["Web", "RTC"].joined(),
            ["Leak", "age"].joined(),
            ["echo", "-cleanup"].joined()
        ]

        for relativePath in activeV5ProductSources {
            let source = try String(contentsOf: root.appendingPathComponent(relativePath), encoding: .utf8)
            for forbiddenTerm in forbiddenTerms {
                XCTAssertFalse(
                    source.contains(forbiddenTerm),
                    "\\(relativePath) must not retain retired capture processing: \\(forbiddenTerm)"
                )
            }
        }
    }

    func testV5WriterPublishesOnlyCanonicalFinalArtifactNames() throws {
        let root = try repositoryRoot()
        let writer = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(writer.contains("meeting-transcription.wav"))
        XCTAssertTrue(writer.contains("meeting-review.m4a"))
        for historicalArtifactName in [["mic", ".wav"].joined(), ["incoming", ".wav"].joined()] {
            XCTAssertFalse(writer.contains(historicalArtifactName))
        }
    }

    func testV5ArtifactValidatorAcceptsOnlyTheCanonicalFinalMemberSet() throws {
        let root = try repositoryRoot()
        let validator = try String(
            contentsOf: root.appendingPathComponent(
                "apps/macos/Scripts/validate-system-audio-capture-pivot.sh"
            ),
            encoding: .utf8
        )

        XCTAssertTrue(validator.contains("meeting-transcription.wav"))
        XCTAssertTrue(validator.contains("meeting-review.m4a"))
        for historicalArtifactName in [["mic", ".wav"].joined(), ["incoming", ".wav"].joined()] {
            XCTAssertFalse(validator.contains(historicalArtifactName))
        }
    }

    private func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        let fileManager = FileManager.default

        while true {
            if fileManager.fileExists(atPath: candidate.appendingPathComponent("apps/macos/Package.swift").path) {
                return candidate
            }
            let parent = candidate.deletingLastPathComponent()
            if parent.path == candidate.path {
                throw NSError(
                    domain: "NoAECProductSurfaceTests",
                    code: 1,
                    userInfo: [NSLocalizedDescriptionKey: "Could not locate repository root"]
                )
            }
            candidate = parent
        }
    }
}
#endif
