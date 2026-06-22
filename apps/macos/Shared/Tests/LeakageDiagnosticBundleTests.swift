import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LeakageDiagnosticBundleTests: XCTestCase {
    func testLocalRecordingBundleIncludesMetadataOnlyLeakageFinalization() throws {
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 1),
            startedAt: Date(timeIntervalSince1970: 1),
            stoppedAt: Date(timeIntervalSince1970: 2),
            finalizedAt: Date(timeIntervalSince1970: 3),
            status: .degraded,
            directoryId: "directory",
            transcriptionReadiness: .degraded,
            tracks: [],
            leakageFinalization: LeakageFinalization(
                status: .leakageDetected,
                evaluatedAt: Date(timeIntervalSince1970: 3),
                measurementAttempted: true,
                measurementApplicable: true,
                alignmentStatus: .aligned,
                confidence: 0.9,
                failureReason: .leakageDetected,
                originalEvidenceStatus: .leakageDetected,
                transcriptionGate: .blockedLeakageDetected,
                routeMetadata: RecordingRouteMetadata(outputRouteClass: "built_in"),
                measurement: LeakageMeasurement(
                    speakerReferenceDb: -10,
                    virtualMicLeakageDb: -20,
                    relativeLeakageDb: -10,
                    intelligibilityStatus: .intelligible,
                    status: .blocked,
                    measuredAt: Date(timeIntervalSince1970: 3),
                    directLoopbackSuspicion: true,
                    acousticLeakageSuspicion: true,
                    confidence: 0.9
                )
            ),
            failureReason: .leakageDetected
        )

        let bundle = try DiagnosticBundleService().buildLocalRecordingBundle(manifest: manifest)

        XCTAssertNotNil(bundle.manifest["leakageFinalization"])
        XCTAssertEqual(bundle.manifest["directLoopbackSuspicion"], .bool(true))
        XCTAssertEqual(bundle.manifest["acousticLeakageSuspicion"], .bool(true))
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
    }

    func testRedactorRemovesForbiddenLeakageNestedFields() {
        let result = DiagnosticRedactor().redact([
            "leakageFinalization": .object([
                "status": .string("unproven"),
                "participantSpeech": .string("not allowed"),
                "absolutePath": .string("/Users/example/Meeting/mic.wav")
            ]),
            "leakageMeasurement": .object([
                "confidence": .double(0.42),
                "signedUrls": .string("https://example.presigned/upload")
            ])
        ])

        XCTAssertEqual(result.status, .blockedSensitiveContent)
        guard case .object(let finalization)? = result.manifest["leakageFinalization"] else {
            XCTFail("Expected leakageFinalization object")
            return
        }
        XCTAssertEqual(finalization["status"], .string("unproven"))
        XCTAssertNil(finalization["participantSpeech"])
        XCTAssertNil(finalization["absolutePath"])
    }

    func testLocalRecordingBundleIncludesMetadataOnlyMicrophoneStreamEvidenceForAllStates() throws {
        let cases: [(LocalRecordingSessionStatus, CaptureHealthGateStatus, LocalRecordingFailureReason, FutureProcessingReadiness)] = [
            (.saved, .passed, .none, .readyForFutureProcessing),
            (.blocked, .blocked, .permissionDenied, .blocked),
            (.degraded, .degraded, .silentInput, .unproven),
            (.failed, .failed, .captureFailed, .blocked)
        ]

        for (status, gateStatus, failureReason, readiness) in cases {
            let selection = leakageDiagnosticRecordingMicrophoneSelection(status: status)
            let manifest = LocalRecordingManifest(
                sessionId: "session-\(status.rawValue)",
                createdAt: Date(timeIntervalSince1970: 10),
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                status: status,
                directoryId: "directory-\(status.rawValue)",
                transcriptionReadiness: status == .saved ? .ready : .degraded,
                tracks: [],
                failureReason: failureReason,
                microphoneSelection: selection,
                microphoneStream: AppOwnedMicrophoneStreamSession(
                    sessionId: "session-\(status.rawValue)",
                    selection: selection,
                    permissionState: failureReason == .permissionDenied ? .denied : .granted,
                    streamKind: .appOwnedSampleSource,
                    stoppedAt: Date(timeIntervalSince1970: 20),
                    sampleRate: 48_000,
                    channelCount: 1,
                    writerSampleRate: 16_000,
                    writerChannelCount: 1,
                    frameCount: failureReason == .none ? 160_000 : 0,
                    failureReason: failureReason
                ),
                microphoneStreamHealth: MicrophoneStreamHealth(
                    gateStatus: gateStatus,
                    failureReason: failureReason,
                    framesObserved: failureReason == .none,
                    timingConfidence: failureReason == .none ? .usable : .missing,
                    silenceStatus: failureReason == .silentInput ? .silent : .notMeasured,
                    cleanupReadiness: readiness,
                    evidenceCodes: ["mic_graph_state_\(status.rawValue)"]
                )
            )

            let bundle = try DiagnosticBundleService().buildLocalRecordingBundle(manifest: manifest)

            XCTAssertNotNil(bundle.manifest["microphoneSelection"])
            XCTAssertNotNil(bundle.manifest["microphoneStream"])
            XCTAssertNotNil(bundle.manifest["microphoneStreamHealth"])
            guard case .object(let health)? = bundle.manifest["microphoneStreamHealth"] else {
                XCTFail("Expected microphone stream health diagnostics for \(status)")
                return
            }
            XCTAssertEqual(health["gateStatus"], .string(gateStatus.rawValue))
            XCTAssertEqual(health["failureReason"], .string(failureReason.rawValue))
            XCTAssertEqual(health["cleanupReadiness"], .string(readiness.rawValue))
            XCTAssertNil(bundle.manifest["rawAudio"])
            XCTAssertNil(bundle.manifest["transcriptText"])
        }
    }

    func testLocalRecordingBundleIncludesMetadataOnlyAppleProcessingOutcomeForAllStates() throws {
        let outcomes: [AppleProcessingOutcome] = [
            leakageDiagnosticAppleOutcome(state: .acceptedForBuiltinSpeakerphone, nextStep: .promoteAppleProcessing),
            leakageDiagnosticAppleOutcome(state: .blockedRouteTopology, nextStep: .deferToWebRTCAEC3, failureReason: AppleProcessingFailureReason.routeTopologyBlocked.rawValue),
            leakageDiagnosticAppleOutcome(state: .acceptedForGuidanceOnly, nextStep: .guidanceOnly, failureReason: AppleProcessingFailureReason.userSystemControlled.rawValue),
            leakageDiagnosticAppleOutcome(state: .deferToWebRTCAEC3, nextStep: .deferToWebRTCAEC3, failureReason: AppleProcessingFailureReason.processingUnavailable.rawValue)
        ]

        for outcome in outcomes {
            let bundle = try DiagnosticBundleService().buildLocalRecordingBundle(
                manifest: LocalRecordingManifest(
                    sessionId: "apple-\(outcome.primaryOutcome.rawValue)",
                    createdAt: Date(timeIntervalSince1970: 10),
                    startedAt: Date(timeIntervalSince1970: 10),
                    stoppedAt: Date(timeIntervalSince1970: 20),
                    status: .degraded,
                    directoryId: "directory-\(outcome.primaryOutcome.rawValue)",
                    transcriptionReadiness: .degraded,
                    tracks: [],
                    appleProcessingOutcome: outcome
                )
            )

            guard case .object(let appleOutcome)? = bundle.manifest["appleProcessingOutcome"] else {
                XCTFail("Expected Apple processing outcome diagnostics for \(outcome.primaryOutcome)")
                return
            }
            guard case .array(let rows)? = bundle.manifest["appleProcessingValidationRows"] else {
                XCTFail("Expected Apple processing validation rows for \(outcome.primaryOutcome)")
                return
            }
            XCTAssertEqual(appleOutcome["primaryOutcome"], .string(outcome.primaryOutcome.rawValue))
            XCTAssertEqual(appleOutcome["nextStepRecommendation"], .string(outcome.nextStepRecommendation.rawValue))
            XCTAssertEqual(rows.count, outcome.validationRows.count)
            XCTAssertNil(bundle.manifest["rawAudio"])
            XCTAssertNil(bundle.manifest["transcriptText"])
            XCTAssertNil(bundle.manifest["absolutePath"])
        }
    }

    func testLocalRecordingBundleIncludesMetadataOnlyWebRTCAEC3OutcomeAndRows() throws {
        let outcome = leakageDiagnosticWebRTCAEC3Outcome()
        let bundle = try DiagnosticBundleService().buildLocalRecordingBundle(
            manifest: LocalRecordingManifest(
                sessionId: "aec3-\(outcome.primaryOutcome.rawValue)",
                createdAt: Date(timeIntervalSince1970: 10),
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                status: .degraded,
                directoryId: "directory-\(outcome.primaryOutcome.rawValue)",
                transcriptionReadiness: .degraded,
                tracks: [],
                webRTCAEC3Outcome: outcome
            )
        )

        guard case .object(let diagnosticOutcome)? = bundle.manifest["webRTCAEC3Outcome"] else {
            XCTFail("Expected WebRTC AEC3 outcome diagnostics")
            return
        }
        guard case .array(let rows)? = bundle.manifest["webRTCAEC3ValidationRows"] else {
            XCTFail("Expected WebRTC AEC3 validation rows")
            return
        }
        guard case .object(let firstRow)? = rows.first else {
            XCTFail("Expected first WebRTC AEC3 row object")
            return
        }

        XCTAssertEqual(diagnosticOutcome["primaryOutcome"], .string(outcome.primaryOutcome.rawValue))
        XCTAssertEqual(diagnosticOutcome["primaryOutcomeCount"], .int(1))
        XCTAssertEqual(diagnosticOutcome["nextStepRecommendation"], .string(outcome.nextStepRecommendation.rawValue))
        XCTAssertEqual(diagnosticOutcome["thresholdProfileId"], .string("aec3-threshold-profile-v1"))
        XCTAssertEqual(diagnosticOutcome["fallbackFeatureId"], .string(WebRTCAEC3EvaluationService.fallbackFeatureId))
        XCTAssertEqual(diagnosticOutcome["requiresFallbackPlanning"], .bool(true))
        XCTAssertEqual(diagnosticOutcome["supportingRouteRowCount"], .int(1))
        XCTAssertEqual(diagnosticOutcome["supportingRoutesCanBroadenPromotionScope"], .bool(false))
        XCTAssertEqual(diagnosticOutcome["canClaimCleanBuiltInSpeakerphone"], .bool(false))
        XCTAssertEqual(firstRow["lineageStatus"], .string(WebRTCAEC3LineageStatus.candidateMetadata.rawValue))
        XCTAssertEqual(firstRow["appStatusState"], .string(WebRTCAEC3AppStatusState.usingOriginalMicTruth.rawValue))
        XCTAssertEqual(firstRow["thresholdProfileId"], .string("aec3-threshold-profile-v1"))
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
        XCTAssertNil(bundle.manifest["privateLocalPath"])
    }

    func testLocalRecordingBundleIncludesWebRTCAEC3AppStatusRollbackThresholdAndMetadataOnlyFields() throws {
        let outcome = leakageDiagnosticWebRTCAEC3RollbackOutcome()
        let bundle = try DiagnosticBundleService().buildLocalRecordingBundle(
            manifest: LocalRecordingManifest(
                sessionId: "aec3-rollback",
                createdAt: Date(timeIntervalSince1970: 10),
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                status: .degraded,
                directoryId: "directory-aec3-rollback",
                transcriptionReadiness: .degraded,
                tracks: [],
                webRTCAEC3Outcome: outcome
            )
        )

        guard case .object(let diagnosticOutcome)? = bundle.manifest["webRTCAEC3Outcome"] else {
            XCTFail("Expected WebRTC AEC3 outcome diagnostics")
            return
        }
        guard case .array(let rows)? = bundle.manifest["webRTCAEC3ValidationRows"],
              case .object(let row)? = rows.first else {
            XCTFail("Expected WebRTC AEC3 rollback row diagnostics")
            return
        }
        guard case .array(let rollbackEvents)? = bundle.manifest["webRTCAEC3RollbackEvents"],
              case .object(let rollbackEvent)? = rollbackEvents.first else {
            XCTFail("Expected WebRTC AEC3 rollback event diagnostics")
            return
        }

        XCTAssertEqual(diagnosticOutcome["rollbackEventCount"], .int(1))
        XCTAssertEqual(diagnosticOutcome["appStatusState"], .string(WebRTCAEC3AppStatusState.rolledBackToOriginal.rawValue))
        XCTAssertEqual(row["thresholdSummary"], .string("rollback_restored_original_truth"))
        XCTAssertEqual(row["appStatusState"], .string(WebRTCAEC3AppStatusState.rolledBackToOriginal.rawValue))
        XCTAssertEqual(rollbackEvent["trigger"], .string(AEC3RollbackTrigger.referenceUnsafe.rawValue))
        XCTAssertEqual(rollbackEvent["restoredLineageStatus"], .string(WebRTCAEC3LineageStatus.originalOnly.rawValue))
        XCTAssertEqual(rollbackEvent["cleanRecordingClaimRemoved"], .bool(true))
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
        XCTAssertNil(bundle.manifest["privateLocalPath"])
    }
}

private func leakageDiagnosticRecordingMicrophoneSelection(
    status: LocalRecordingSessionStatus
) -> RecordingMicrophoneSelection {
    RecordingMicrophoneSelection(
        selectionId: "selection-\(status.rawValue)",
        mode: .userSelected,
        inputDeviceId: "built-in-mic",
        inputDisplayName: "Built-in Microphone",
        deviceClass: .builtIn,
        workingDeviceKind: .physical,
        selectionResult: .accepted,
        resolvedAt: Date(timeIntervalSince1970: 9)
    )
}

private func leakageDiagnosticAppleOutcome(
    state: AppleProcessingOutcomeState,
    nextStep: AppleProcessingNextStepRecommendation,
    failureReason: String? = nil
) -> AppleProcessingOutcome {
    AppleProcessingOutcome(
        candidateId: "apple-\(state.rawValue)",
        primaryOutcome: state,
        validationRows: [
            AppleProcessingValidationRow(
                candidateId: "apple-\(state.rawValue)",
                candidateKind: state == .acceptedForGuidanceOnly ? .micModeGuidance : .appOwnedGraphVoiceProcessing,
                routeClass: .builtInSpeakerphone,
                scenario: state == .acceptedForBuiltinSpeakerphone ? .farEndOnly : .routeChange,
                baselineStatus: .degraded,
                candidateStatus: state == .acceptedForBuiltinSpeakerphone ? .accepted : .unproven,
                lineageStatus: state == .acceptedForBuiltinSpeakerphone ? .liveAndPersisted : .unproven,
                speechPreservationStatus: state == .acceptedForBuiltinSpeakerphone ? .preserved : .notMeasured,
                alignmentStatus: state == .acceptedForBuiltinSpeakerphone ? .accepted : .notMeasured,
                stabilityStatus: state == .acceptedForBuiltinSpeakerphone ? .accepted : .unproven,
                diagnosticSafe: true,
                failureReason: failureReason
            )
        ],
        nextStepRecommendation: nextStep,
        failureReason: failureReason
    )
}

private func leakageDiagnosticWebRTCAEC3Outcome() -> WebRTCAEC3DecisionRecord {
    WebRTCAEC3DecisionRecord(
        candidateId: "aec3-diagnostic-guidance",
        primaryOutcome: .acceptedForGuidanceOnly,
        validationRows: [
            WebRTCAEC3ValidationRow(
                rowId: "aec3-diagnostic-row",
                candidateId: "aec3-diagnostic-guidance",
                scenarioFamily: .farEndOnlyLeakage,
                validationKind: .fullFile,
                routeClass: .builtInSpeakerphone,
                baselineStatus: .leakageDetected,
                candidateStatus: .unproven,
                lineageStatus: .candidateMetadata,
                speechPreservationStatus: .notMeasured,
                residualLeakageStatus: .unproven,
                timingConfidence: .notMeasured,
                referenceStatus: .present,
                stabilityStatus: .unproven,
                thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
                thresholdSummary: "guidance_only",
                appStatusState: .usingOriginalMicTruth,
                diagnosticSafe: true
            )
        ],
        nextStepRecommendation: .guidanceOnly,
        supportingRouteRows: [
            WebRTCAEC3ValidationRow(
                rowId: "aec3-diagnostic-supporting-usb",
                candidateId: "aec3-diagnostic-guidance",
                scenarioFamily: .farEndOnlyLeakage,
                validationKind: .controlledRealHardware,
                routeClass: .usbHeadset,
                baselineStatus: .leakageDetected,
                candidateStatus: .accepted,
                lineageStatus: .guidanceOnly,
                speechPreservationStatus: .preserved,
                residualLeakageStatus: .clean,
                timingConfidence: .safe,
                referenceStatus: .present,
                stabilityStatus: .accepted,
                thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
                thresholdSummary: "supporting_route_evidence_only",
                appStatusState: .fallbackRelevant,
                diagnosticSafe: true
            )
        ],
        limitations: [
            "supporting_routes_evidence_only",
            "fallback_required_040"
        ],
        fallbackFeatureId: WebRTCAEC3EvaluationService.fallbackFeatureId
    )
}

private func leakageDiagnosticWebRTCAEC3RollbackOutcome() -> WebRTCAEC3DecisionRecord {
    WebRTCAEC3DecisionRecord(
        candidateId: "aec3-diagnostic-rollback",
        primaryOutcome: .blockedStability,
        validationRows: [
            WebRTCAEC3ValidationRow(
                rowId: "aec3-diagnostic-rollback-row",
                candidateId: "aec3-diagnostic-rollback",
                scenarioFamily: .rollback,
                validationKind: .rollback,
                routeClass: .builtInSpeakerphone,
                baselineStatus: .unproven,
                candidateStatus: .blocked,
                lineageStatus: .rolledBackToOriginal,
                speechPreservationStatus: .unknown,
                residualLeakageStatus: .unproven,
                timingConfidence: .unknown,
                referenceStatus: .notRepresentative,
                stabilityStatus: .rollbackRequired,
                thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
                thresholdSummary: "rollback_restored_original_truth",
                appStatusState: .rolledBackToOriginal,
                diagnosticSafe: true,
                failureReason: WebRTCAEC3FailureReason.referenceNotRepresentative.rawValue
            )
        ],
        nextStepRecommendation: .fallbackDecision,
        rollbackEvents: [
            AEC3RollbackEvent(
                rollbackId: "rollback-aec3-diagnostic-rollback",
                candidateId: "aec3-diagnostic-rollback",
                trigger: .referenceUnsafe,
                previousLineageStatus: .promotedBuiltinRoute,
                restoredLineageStatus: .originalOnly,
                cleanRecordingClaimRemoved: true,
                appStatusShown: true,
                thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
                occurredAt: Date(timeIntervalSince1970: 21)
            )
        ],
        failureReason: WebRTCAEC3FailureReason.referenceNotRepresentative.rawValue
    )
}
#endif
