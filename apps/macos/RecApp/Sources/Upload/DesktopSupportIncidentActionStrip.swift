import AppKit
import SwiftUI
import TwoBrainRecShared

public enum DesktopSupportIncidentActionCopy {
    public static let sendTitle = "Связаться с поддержкой"
    public static let syncTitle = "Проверить синхронизацию"
    public static let signInTitle = "Войти в кабинет"
    public static let copyTitle = "Скопировать безопасную сводку"
    public static let sendingMessage = "Отправляем запрос в поддержку…"
    public static let rejectedMessage = "Запрос не принят. Проверьте подключение или скопируйте безопасную сводку."
    public static let failureMessage = rejectedMessage

    public static func successMessage(incidentNumber: String?) -> String {
        guard let incidentNumber = normalized(incidentNumber) else {
            return "Запрос принят и передан в поддержку."
        }
        return "Запрос принят и передан в поддержку. Номер: \(incidentNumber)"
    }

    public static func pendingMessage(incidentNumber: String?) -> String {
        guard let incidentNumber = normalized(incidentNumber) else {
            return "Запрос принят сервером. Синхронизация с поддержкой ожидает проверки."
        }
        return "Запрос принят сервером. Синхронизация с поддержкой ожидает проверки. Номер: \(incidentNumber)"
    }

    public static func signInRequiredMessage(incidentNumber: String?) -> String {
        if let incidentNumber = normalized(incidentNumber) {
            return "Запрос с номером \(incidentNumber) уже принят сервером. Войдите в кабинет, чтобы проверить синхронизацию."
        }
        return "Нужен вход в кабинет, чтобы отправить запрос в поддержку."
    }

    public static func visibleMessage(for state: DesktopSupportIncidentSubmissionState?) -> String? {
        guard let state else { return nil }
        switch state.state {
        case .notSent:
            return nil
        case .sending:
            return sendingMessage
        case .pendingSync:
            return pendingMessage(incidentNumber: state.incidentNumber)
        case .sent:
            return successMessage(incidentNumber: state.incidentNumber)
        case .failedWithCopyFallback:
            return requiresSignIn(state) ? signInRequiredMessage(incidentNumber: state.incidentNumber) : rejectedMessage
        case .unavailable:
            return rejectedMessage
        }
    }

    public static func requiresSignIn(_ state: DesktopSupportIncidentSubmissionState?) -> Bool {
        guard let code = state?.lastFailureCode?.lowercased() else { return false }
        return code == "support_incident.auth_session_required" ||
            code.contains("auth_session") ||
            code.contains("csrf_") ||
            code == "legacy_header_auth_disabled"
    }

    private static func normalized(_ incidentNumber: String?) -> String? {
        guard let value = incidentNumber?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty else {
            return nil
        }
        return value
    }
}

struct DesktopSupportIncidentActionStrip: View {
    let summary: DesktopUploadCustodySummary
    var leadingPadding: CGFloat = 0
    let onSubmit: ([String]) async throws -> DesktopSupportIncidentResponse
    let onSync: ([String]) async throws -> DesktopSupportIncidentResponse
    let onCopyReport: ([String]) throws -> String?
    let onOpenSignIn: () -> Void

    @State private var submissionOverride: DesktopSupportIncidentSubmissionState?

    init(
        summary: DesktopUploadCustodySummary,
        leadingPadding: CGFloat = 0,
        onSubmit: @escaping ([String]) async throws -> DesktopSupportIncidentResponse,
        onSync: @escaping ([String]) async throws -> DesktopSupportIncidentResponse = { _ in
            throw DesktopUploadClientError.httpStatus(401, "support_incident.auth_session_required")
        },
        onCopyReport: @escaping ([String]) throws -> String? = { _ in nil },
        onOpenSignIn: @escaping () -> Void = {}
    ) {
        self.summary = summary
        self.leadingPadding = leadingPadding
        self.onSubmit = onSubmit
        self.onSync = onSync
        self.onCopyReport = onCopyReport
        self.onOpenSignIn = onOpenSignIn
    }

    var body: some View {
        if summary.safeReport != nil, showsSupportSurface {
            VStack(alignment: .leading, spacing: 6) {
                if let message = DesktopSupportIncidentActionCopy.visibleMessage(for: submissionState) {
                    Text(message)
                        .font(.caption2)
                        .foregroundStyle(statusTextColor)
                        .lineLimit(3)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityLabel(message)
                }

                if showsSendButton {
                    Button(action: submit) {
                        Label(sendButtonTitle, systemImage: "questionmark.bubble")
                    }
                    .font(.caption)
                    .buttonStyle(DesktopWebButtonStyle(.secondary))
                    .disabled(isSending)
                    .accessibilityLabel(DesktopSupportIncidentActionCopy.sendTitle)
                    .help("Отправить запрос в поддержку GRAF.")
                }

                if showsSyncButton {
                    Button(action: sync) {
                        Label(DesktopSupportIncidentActionCopy.syncTitle, systemImage: "arrow.triangle.2.circlepath")
                    }
                    .font(.caption)
                    .buttonStyle(DesktopWebButtonStyle(.secondary))
                    .disabled(isSending)
                    .accessibilityLabel(DesktopSupportIncidentActionCopy.syncTitle)
                }

                if DesktopSupportIncidentActionCopy.requiresSignIn(submissionState) {
                    Button(action: onOpenSignIn) {
                        Label(DesktopSupportIncidentActionCopy.signInTitle, systemImage: "person.crop.circle.badge.exclamationmark")
                    }
                    .font(.caption)
                    .buttonStyle(DesktopWebButtonStyle(.secondary))
                    .accessibilityLabel(DesktopSupportIncidentActionCopy.signInTitle)
                }

                if submissionState?.copyFallbackAvailable == true,
                   showsCopyFallbackButton {
                    Button(action: copySafeReport) {
                        Label(DesktopSupportIncidentActionCopy.copyTitle, systemImage: "doc.on.doc")
                    }
                    .font(.caption)
                    .buttonStyle(DesktopWebButtonStyle(.secondary))
                    .accessibilityLabel(DesktopSupportIncidentActionCopy.copyTitle)
                    .help("Скопировать только безопасную metadata-only сводку.")
                }
            }
            .padding(.leading, leadingPadding)
            .accessibilityElement(children: .contain)
        }
    }

    private var submissionState: DesktopSupportIncidentSubmissionState? {
        submissionOverride ?? summary.primaryItem.supportIncidentSubmission
    }

    private var showsSendButton: Bool {
        summary.primaryProjection.normalUserAction == .sendSupportReport &&
            submissionState?.state != .sent &&
            submissionState?.state != .pendingSync
    }

    private var showsSyncButton: Bool {
        submissionState?.state == .pendingSync
    }

    private var showsCopyFallbackButton: Bool {
        switch submissionState?.state {
        case .failedWithCopyFallback, .pendingSync:
            return true
        case .notSent, .sending, .sent, .unavailable, nil:
            return false
        }
    }

    private var showsSupportSurface: Bool {
        summary.primaryProjection.normalUserAction == .sendSupportReport || submissionState != nil
    }

    private var isSending: Bool {
        submissionState?.state == .sending
    }

    private var sendButtonTitle: String {
        isSending ? "Отправляем…" : DesktopSupportIncidentActionCopy.sendTitle
    }

    private var statusTextColor: Color {
        switch submissionState?.state {
        case .sent:
            return .secondary
        case .pendingSync, .failedWithCopyFallback, .unavailable:
            return .orange
        case .sending, .notSent, nil:
            return .secondary
        }
    }

    private func submit() {
        let itemIDs = supportIncidentItemIDs
        submissionOverride = DesktopSupportIncidentSubmissionState(
            state: .sending,
            localReportFingerprint: submissionState?.localReportFingerprint,
            dedupeKey: submissionState?.dedupeKey,
            lastSubmissionAttemptAt: Date(),
            accessibilityLabel: DesktopSupportIncidentActionCopy.sendingMessage
        )

        Task {
            do {
                let response = try await onSubmit(itemIDs)
                await MainActor.run {
                    submissionOverride = state(
                        for: response,
                        reportFingerprint: submissionState?.localReportFingerprint ?? "pending",
                        dedupeKey: submissionState?.dedupeKey ?? "pending"
                    )
                }
            } catch {
                let failure = Self.failure(error)
                await MainActor.run {
                    submissionOverride = DesktopSupportIncidentSubmissionState.failedWithCopyFallback(
                        reportFingerprint: submissionState?.localReportFingerprint ?? "pending",
                        dedupeKey: submissionState?.dedupeKey ?? "pending",
                        attemptedAt: Date(),
                        failureCategory: failure.category,
                        failureCode: failure.code
                    )
                }
            }
        }
    }

    private func sync() {
        guard let pending = submissionState,
              let incidentNumber = pending.incidentNumber,
              !incidentNumber.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else {
            return
        }
        let itemIDs = supportIncidentItemIDs
        submissionOverride = DesktopSupportIncidentSubmissionState(
            state: .sending,
            localReportFingerprint: pending.localReportFingerprint,
            dedupeKey: pending.dedupeKey,
            incidentNumber: incidentNumber,
            lastSubmissionAttemptAt: Date(),
            copyFallbackAvailable: pending.copyFallbackAvailable,
            accessibilityLabel: DesktopSupportIncidentActionCopy.sendingMessage
        )

        Task {
            do {
                let response = try await onSync(itemIDs)
                await MainActor.run {
                    submissionOverride = state(
                        for: response,
                        reportFingerprint: pending.localReportFingerprint ?? "pending",
                        dedupeKey: pending.dedupeKey ?? "pending"
                    )
                }
            } catch {
                let failure = Self.failure(error)
                await MainActor.run {
                    submissionOverride = DesktopSupportIncidentSubmissionState.pendingSync(
                        reportFingerprint: pending.localReportFingerprint ?? "pending",
                        dedupeKey: pending.dedupeKey ?? "pending",
                        incidentNumber: incidentNumber,
                        attemptedAt: Date(),
                        copyFallbackAvailable: pending.copyFallbackAvailable,
                        failureCode: failure.code
                    )
                }
            }
        }
    }

    private func state(
        for response: DesktopSupportIncidentResponse,
        reportFingerprint: String,
        dedupeKey: String
    ) -> DesktopSupportIncidentSubmissionState {
        if response.isPendingSync {
            return .pendingSync(
                reportFingerprint: reportFingerprint,
                dedupeKey: dedupeKey,
                incidentNumber: response.incidentId,
                attemptedAt: Date(),
                copyFallbackAvailable: response.copyFallbackAvailable
            )
        }
        return .sent(
            reportFingerprint: reportFingerprint,
            dedupeKey: dedupeKey,
            incidentNumber: response.incidentId,
            githubIssueNumber: response.githubIssueNumber,
            attemptedAt: Date(),
            copyFallbackAvailable: response.copyFallbackAvailable
        )
    }

    private func copySafeReport() {
        let text: String
        do {
            guard let value = try onCopyReport(supportIncidentItemIDs), !value.isEmpty else { return }
            text = value
        } catch {
            return
        }
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)
    }

    private var supportIncidentItemIDs: [String] {
        let ids = summary.affectedItems.map(\.id)
        return ids.isEmpty ? [summary.primaryItem.id] : ids
    }

    private static func failure(_ error: Error) -> (category: String, code: String) {
        if let clientError = error as? DesktopUploadClientError {
            switch clientError {
            case .httpStatus(_, let code):
                return (clientError.failureCategory.rawValue, code)
            case .invalidBaseURL:
                return (clientError.failureCategory.rawValue, "support_incident.invalid_base_url")
            case .invalidArtifactPackage:
                return (clientError.failureCategory.rawValue, "support_incident.invalid_artifact_package")
            case .invalidResponse:
                return (clientError.failureCategory.rawValue, "support_incident.invalid_response")
            case .localFileMissing, .serverStillMissingRanges:
                return (clientError.failureCategory.rawValue, "support_incident.unavailable")
            }
        }
        return (UploadFailureCategory.network.rawValue, "support_incident.unavailable")
    }
}
