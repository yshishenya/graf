#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

case "${1:-}" in
  --self-test-corpus)
    swift run --package-path "${REPO_ROOT}/apps/macos" WebRTCAEC3Validation --self-test-corpus
    swift test --package-path "${REPO_ROOT}/apps/macos" --filter 'WebRTCAEC3ValidationCorpusTests'
    ;;
  --self-test-contracts)
    swift run --package-path "${REPO_ROOT}/apps/macos" WebRTCAEC3Validation --self-test-contracts
    swift test --package-path "${REPO_ROOT}/apps/macos" --filter 'WebRTCAEC3ModelsTests|WebRTCAEC3EvaluationTests|WebRTCAEC3SpikeContractTests'
    ;;
  --self-test-status)
    swift run --package-path "${REPO_ROOT}/apps/macos" WebRTCAEC3Validation --self-test-status
    swift test --package-path "${REPO_ROOT}/apps/macos" --filter 'CaptureControlTests'
    ;;
  --self-test-diagnostics)
    swift run --package-path "${REPO_ROOT}/apps/macos" WebRTCAEC3Validation --self-test-diagnostics
    swift test --package-path "${REPO_ROOT}/apps/macos" --filter 'DiagnosticRedactionTests|LeakageDiagnosticBundleTests'
    ;;
  --self-test-rollback)
    swift run --package-path "${REPO_ROOT}/apps/macos" WebRTCAEC3Validation --self-test-rollback
    swift test --package-path "${REPO_ROOT}/apps/macos" --filter 'WebRTCAEC3EvaluationTests/testRollbackEventRestoresOriginalTruthAndDecisionRemovesCleanClaim'
    ;;
  --self-test-stop-quit)
    swift run --package-path "${REPO_ROOT}/apps/macos" WebRTCAEC3Validation --self-test-stop-quit
    swift test --package-path "${REPO_ROOT}/apps/macos" --filter 'WebRTCAEC3EvaluationTests|WebRTCAEC3SpikeContractTests'
    ;;
  --self-test-decision)
    swift run --package-path "${REPO_ROOT}/apps/macos" WebRTCAEC3Validation --self-test-decision
    swift test --package-path "${REPO_ROOT}/apps/macos" --filter 'WebRTCAEC3EvaluationTests|WebRTCAEC3ValidationCorpusTests'
    ;;
  --help|"")
    swift run --package-path "${REPO_ROOT}/apps/macos" WebRTCAEC3Validation --help
    ;;
  *)
    swift run --package-path "${REPO_ROOT}/apps/macos" WebRTCAEC3Validation "$@"
    ;;
esac
