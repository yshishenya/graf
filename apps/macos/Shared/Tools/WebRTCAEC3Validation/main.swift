import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

@main
enum WebRTCAEC3ValidationTool {
    static func main() throws {
        let arguments = Array(CommandLine.arguments.dropFirst())
        if arguments.contains("--help") || arguments.isEmpty {
            print("""
            WebRTCAEC3Validation

            Usage:
              WebRTCAEC3Validation --self-test-corpus
              WebRTCAEC3Validation --self-test-contracts
              WebRTCAEC3Validation --self-test-status
              WebRTCAEC3Validation --self-test-diagnostics
              WebRTCAEC3Validation --self-test-rollback
              WebRTCAEC3Validation --self-test-stop-quit
              WebRTCAEC3Validation --self-test-decision

            This tool emits metadata-only validation results for feature 039.
            """)
            return
        }

        switch arguments {
        case ["--self-test-corpus"]:
            try runCorpusSelfTest()
        case ["--self-test-contracts"]:
            try runContractsSelfTest()
        case ["--self-test-status"]:
            try runStatusSelfTest()
        case ["--self-test-diagnostics"]:
            try runDiagnosticsSelfTest()
        case ["--self-test-rollback"]:
            try runRollbackSelfTest()
        case ["--self-test-stop-quit"]:
            try runStopQuitSelfTest()
        case ["--self-test-decision"]:
            try runDecisionSelfTest()
        default:
            throw ValidationToolError.unsupportedArguments(arguments)
        }
    }

    private static func runCorpusSelfTest() throws {
        let corpus = try decodeFixture(WebRTCAEC3ValidationCorpus.self, fileName: "lab-grade-corpus.json")
        let invalidCases = try decodeFixture(WebRTCAEC3InvalidCorpusCases.self, fileName: "invalid-corpus-cases.json")
        let hardwareMatrix = try decodeFixture(
            WebRTCAEC3ControlledHardwareMatrix.self,
            fileName: "controlled-real-hardware.json"
        )

        guard corpus.isEligibleForImmediatePromotion else {
            throw ValidationToolError.corpusFailed(corpus.promotionCoverageFailures)
        }
        guard invalidCases.promotionBlockers.count == invalidCases.cases.count else {
            throw ValidationToolError.corpusFailed(["invalid_case_blocker_mapping_missing"])
        }
        guard hardwareMatrix.hasAllImmediatePromotionCriticalRows,
              hardwareMatrix.isMetadataOnly,
              !hardwareMatrix.supportingRoutesCanBroadenPromotionScope else {
            throw ValidationToolError.corpusFailed(["controlled_hardware_matrix_failed"])
        }

        print(
            "webrtc_aec3_corpus=pass full_files=\(corpus.totalFullFileValidations) slices=\(corpus.totalSlicedWindowValidations) controlled_rows=\(hardwareMatrix.criticalRows.count)"
        )
    }

    private static func runContractsSelfTest() throws {
        let row = WebRTCAEC3ValidationRow.acceptedFixture(
            scenarioFamily: .appStatus,
            validationKind: .appStatus,
            thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId
        )
        let encoded = try JSONEncoder().encode(row)
        let json = String(decoding: encoded, as: UTF8.self)
        let forbiddenFragments = ["rawAudio", "transcriptText", "signedUrl", "privateLocalPath"]
        let leakedFragments = forbiddenFragments.filter { json.contains($0) }
        guard leakedFragments.isEmpty else {
            throw ValidationToolError.contractFailed(leakedFragments)
        }

        let service = WebRTCAEC3EvaluationService(clock: { Date(timeIntervalSince1970: 600) })
        let decision = WebRTCAEC3DecisionRecord(
            candidateId: "aec3-contract-self-test",
            primaryOutcome: .blockedRouteTopology,
            validationRows: [
                service.failClosedRow(
                    candidateId: "aec3-contract-self-test",
                    routeClass: .builtInSpeakerphone,
                    scenarioFamily: .unsafeReferenceNegativeControl,
                    reason: .referenceMissing
                )
            ],
            nextStepRecommendation: .fallbackDecision,
            failureReason: WebRTCAEC3FailureReason.referenceMissing.rawValue
        )
        let record = service.decisionRecord(decision)
        for requiredKey in ["feature", "primaryOutcome", "thresholdProfileId", "appStatusState", "failureReason"] {
            guard record[requiredKey]?.isEmpty == false else {
                throw ValidationToolError.contractFailed(["missing_\(requiredKey)"])
            }
        }

        print("webrtc_aec3_contracts=pass primaryOutcome=\(decision.primaryOutcome.rawValue)")
    }

    private static func runStatusSelfTest() throws {
        let states: [WebRTCAEC3AppStatusState] = [
            .evaluatingAEC3,
            .usingOriginalMicTruth,
            .candidateBlocked,
            .promotedBuiltinRoute,
            .rolledBackToOriginal,
            .fallbackRelevant,
            .requiresUserAttention
        ]

        for state in states {
            let status = appStatus(state: state)
            guard let copy = CaptureControlView.webRTCAEC3StatusCopy(for: status),
                  CaptureControlView.webRTCAEC3StatusCopyIsClaimSafe(copy, state: state),
                  !CaptureControlView.webRTCAEC3StatusTitle(for: state).isEmpty,
                  !CaptureControlView.webRTCAEC3StatusIconName(for: state).isEmpty else {
                throw ValidationToolError.contractFailed(["status_failed_\(state.rawValue)"])
            }
        }

        guard !CaptureControlView.webRTCAEC3StatusIsNoisyAlert(for: appStatus(state: .fallbackRelevant)),
              !CaptureControlView.webRTCAEC3StatusIsNoisyAlert(for: appStatus(state: .rolledBackToOriginal)) else {
            throw ValidationToolError.contractFailed(["status_noisy_alert"])
        }

        print("webrtc_aec3_status=pass states=\(states.count)")
    }

    private static func runDiagnosticsSelfTest() throws {
        let result = DiagnosticRedactor().redact([
            "webRTCAEC3Diagnostics": .object([
                "candidateId": .string("aec3-diagnostics"),
                "echoDelayMedianMs": .double(18),
                "rawSamples": .string("forbidden"),
                "transcriptText": .string("forbidden"),
                "privateLocalPath": .string("/Users/example/private/aec3.wav"),
                "signedUrl": .string("https://example.presigned/download"),
                "unboundedLog": .string(String(repeating: "trace", count: 2_000))
            ]),
            "webRTCAEC3AppStatus": .object([
                "state": .string(WebRTCAEC3AppStatusState.fallbackRelevant.rawValue),
                "copySafety": .string(WebRTCAEC3StatusCopySafety.safe.rawValue)
            ]),
            "webRTCAEC3Rollback": .object([
                "trigger": .string(AEC3RollbackTrigger.referenceUnsafe.rawValue),
                "debugLog": .string(String(repeating: "debug", count: 2_000))
            ]),
            "webRTCAEC3EchoDelaySummary": .string("median_ms=18")
        ])
        let requiredRemovals = [
            "webRTCAEC3Diagnostics.rawSamples",
            "webRTCAEC3Diagnostics.transcriptText",
            "webRTCAEC3Diagnostics.privateLocalPath",
            "webRTCAEC3Diagnostics.signedUrl",
            "webRTCAEC3Diagnostics.unboundedLog",
            "webRTCAEC3Rollback.debugLog"
        ]

        guard requiredRemovals.allSatisfy(result.removedFields.contains),
              result.manifest["webRTCAEC3Diagnostics"] != nil,
              result.manifest["webRTCAEC3AppStatus"] != nil,
              result.manifest["webRTCAEC3Rollback"] != nil else {
            throw ValidationToolError.contractFailed(["diagnostics_redaction_failed"])
        }

        print("webrtc_aec3_diagnostics=pass removed=\(requiredRemovals.count)")
    }

    private static func runRollbackSelfTest() throws {
        let service = WebRTCAEC3EvaluationService(clock: { Date(timeIntervalSince1970: 700) })
        let decision = service.rollbackDecision(
            candidateId: "aec3-rollback-self-test",
            trigger: .referenceUnsafe
        )
        guard let event = decision.rollbackEvents?.first,
              let row = decision.validationRows.first,
              event.restoresOriginalTruth,
              row.appStatusState == .rolledBackToOriginal,
              row.lineageStatus == .rolledBackToOriginal,
              !decision.canClaimCleanBuiltInSpeakerphone else {
            throw ValidationToolError.contractFailed(["rollback_failed"])
        }

        print("webrtc_aec3_rollback=pass trigger=\(event.trigger.rawValue)")
    }

    private static func runStopQuitSelfTest() throws {
        let row = WebRTCAEC3EvaluationService().failClosedRow(
            candidateId: "aec3-stop-quit-self-test",
            routeClass: .builtInSpeakerphone,
            scenarioFamily: .stopQuit,
            reason: .stopQuitFailed
        )
        guard row.validationKind == .stopQuit,
              row.scenarioFamily == .stopQuit,
              row.candidateStatus == .blocked,
              row.diagnosticSafe,
              !row.isAcceptedForImmediatePromotion else {
            throw ValidationToolError.contractFailed(["stop_quit_failed"])
        }

        print("webrtc_aec3_stop_quit=pass status=\(row.candidateStatus.rawValue)")
    }

    private static func runDecisionSelfTest() throws {
        let service = WebRTCAEC3EvaluationService(clock: { Date(timeIntervalSince1970: 900) })
        let candidate = WebRTCAEC3Candidate(
            candidateId: "aec3-decision-self-test",
            candidateKind: .nativeWebRTCAEC3,
            routeClass: .builtInSpeakerphone,
            promotionScope: .builtInMacMicAndSpeakers,
            dependencyReadiness: .ready,
            renderReferenceStatus: .present,
            captureTimingStatus: .safe,
            metricsStatus: .available,
            thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
            diagnosticSafe: true
        )
        let decision = service.finalDecision(
            candidate: candidate,
            corpus: try decodeFixture(WebRTCAEC3ValidationCorpus.self, fileName: "lab-grade-corpus.json"),
            validationRows: [],
            supportingRouteRows: [
                WebRTCAEC3ValidationRow.acceptedFixture(
                    scenarioFamily: .farEndOnlyLeakage,
                    validationKind: .controlledRealHardware,
                    thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId
                )
            ].map { row in
                var supporting = row
                supporting.routeClass = .usbHeadset
                supporting.lineageStatus = .guidanceOnly
                supporting.appStatusState = .fallbackRelevant
                supporting.thresholdSummary = "supporting_route_evidence_only"
                return supporting
            },
            controlledHardwareRows: [],
            licenseReady: true,
            packagingReady: true,
            signingReady: true
        )
        let record = service.decisionRecord(decision)
        guard decision.primaryOutcomeCount == 1,
              decision.primaryOutcome == .deferToFallbackDecision,
              decision.fallbackFeatureId == WebRTCAEC3EvaluationService.fallbackFeatureId,
              decision.supportingRoutesCanBroadenPromotionScope == false,
              record["fallbackFeatureId"] == WebRTCAEC3EvaluationService.fallbackFeatureId,
              record["supportingRoutesCanBroadenPromotionScope"] == "false",
              record["rawAudio"] == nil,
              record["transcriptText"] == nil,
              record["signedUrl"] == nil,
              record["privateLocalPath"] == nil else {
            throw ValidationToolError.contractFailed(["decision_record_failed"])
        }

        print(
            "webrtc_aec3_decision=pass primaryOutcome=\(decision.primaryOutcome.rawValue) fallbackFeature=\(decision.fallbackFeatureId ?? "none")"
        )
    }

    private static func appStatus(state: WebRTCAEC3AppStatusState) -> AppRecordingStatus {
        AppRecordingStatus(
            statusId: "status-\(state.rawValue)",
            candidateId: "aec3-\(state.rawValue)",
            state: state,
            routeScope: state == .promotedBuiltinRoute ? .builtInMacMicAndSpeakers : .notApplicable,
            copySafety: .safe,
            actionHint: state == .requiresUserAttention ? .reviewStatus : .continueRecording,
            matchesPackageTruth: true,
            diagnosticSafe: true
        )
    }

    private static func decodeFixture<T: Decodable>(_ type: T.Type, fileName: String) throws -> T {
        let url = try fixtureURL(fileName)
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private static func fixtureURL(_ fileName: String) throws -> URL {
        let fileManager = FileManager.default
        let current = URL(fileURLWithPath: fileManager.currentDirectoryPath)
        let source = URL(fileURLWithPath: #filePath)
        let candidates = [
            current.appendingPathComponent("apps/macos/Shared/Tests/Fixtures/WebRTCAEC3/\(fileName)"),
            current.appendingPathComponent("Shared/Tests/Fixtures/WebRTCAEC3/\(fileName)"),
            source
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("Tests/Fixtures/WebRTCAEC3/\(fileName)")
        ]
        if let url = candidates.first(where: { fileManager.fileExists(atPath: $0.path) }) {
            return url
        }
        throw ValidationToolError.fixtureMissing(fileName)
    }
}

enum ValidationToolError: Error, CustomStringConvertible {
    case unsupportedArguments([String])
    case fixtureMissing(String)
    case corpusFailed([String])
    case contractFailed([String])

    var description: String {
        switch self {
        case .unsupportedArguments(let arguments):
            return "Unsupported WebRTC AEC3 validation arguments: \(arguments.joined(separator: " "))"
        case .fixtureMissing(let fileName):
            return "Missing WebRTC AEC3 fixture: \(fileName)"
        case .corpusFailed(let failures):
            return "WebRTC AEC3 corpus self-test failed: \(failures.joined(separator: ","))"
        case .contractFailed(let failures):
            return "WebRTC AEC3 contract self-test failed: \(failures.joined(separator: ","))"
        }
    }
}
