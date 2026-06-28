import AppKit
import SwiftUI
import TwoBrainRecShared

public enum DesktopSupportIncidentActionCopy {
    public static let sendTitle = "Отправить отчет"
    public static let copyTitle = "Скопировать отчет"
    public static let sendingMessage = "Отправляем отчет."
    public static let failureMessage = "Не удалось отправить. Скопируйте отчет и отправьте в поддержку."

    public static func successMessage(incidentNumber: String) -> String {
        "Отчет отправлен. Мы разберемся. Номер: \(incidentNumber)"
    }

    public static func visibleMessage(for state: DesktopSupportIncidentSubmissionState?) -> String? {
        guard let state else { return nil }
        switch state.state {
        case .notSent:
            return nil
        case .sending:
            return sendingMessage
        case .sent:
            return successMessage(incidentNumber: state.incidentNumber ?? "CUST-?")
        case .failedWithCopyFallback, .unavailable:
            return failureMessage
        }
    }
}

struct DesktopSupportIncidentActionStrip: View {
    let summary: DesktopUploadCustodySummary
    var leadingPadding: CGFloat = 0
    let onSubmit: ([String]) async throws -> DesktopSupportIncidentResponse

    @State private var copiedItemID: String?
    @State private var submissionOverride: DesktopSupportIncidentSubmissionState?

    var body: some View {
        if let safeReport = summary.safeReport {
            VStack(alignment: .leading, spacing: 6) {
                if let message = DesktopSupportIncidentActionCopy.visibleMessage(for: submissionState) {
                    Text(message)
                        .font(.caption2)
                        .foregroundStyle(statusTextColor)
                        .lineLimit(3)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityLabel(message)
                }

                HStack(spacing: 8) {
                    if showsSendButton {
                        Button {
                            submit()
                        } label: {
                            Label(sendButtonTitle, systemImage: "paperplane")
                        }
                        .font(.caption)
                        .buttonStyle(.borderedProminent)
                        .controlSize(.small)
                        .disabled(isSending)
                        .accessibilityLabel("Отправить отчет разработчикам")
                        .help("Отправить безопасный отчет разработчикам через сервер GRAF.")
                    }

                    Button {
                        copySafeReport(safeReport)
                    } label: {
                        Label(copyButtonTitle, systemImage: "doc.on.doc")
                    }
                    .font(.caption)
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    .accessibilityLabel(DesktopSupportIncidentActionCopy.copyTitle)
                    .help("Метаданные для поддержки без аудио, текста встречи, локальных путей, токенов и ссылок.")
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
            submissionState?.state != .sent
    }

    private var isSending: Bool {
        submissionState?.state == .sending
    }

    private var sendButtonTitle: String {
        isSending ? "Отправляем" : DesktopSupportIncidentActionCopy.sendTitle
    }

    private var copyButtonTitle: String {
        copiedItemID == summary.primaryItem.id ? "Скопировано" : DesktopSupportIncidentActionCopy.copyTitle
    }

    private var statusTextColor: Color {
        switch submissionState?.state {
        case .sent:
            return .secondary
        case .failedWithCopyFallback, .unavailable:
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
            accessibilityLabel: "Отправляем отчет разработчикам."
        )

        Task {
            do {
                let response = try await onSubmit(itemIDs)
                await MainActor.run {
                    submissionOverride = DesktopSupportIncidentSubmissionState.sent(
                        reportFingerprint: submissionState?.localReportFingerprint ?? "pending",
                        dedupeKey: submissionState?.dedupeKey ?? "pending",
                        incidentNumber: response.incidentId,
                        githubIssueNumber: response.githubIssueNumber,
                        attemptedAt: Date(),
                        copyFallbackAvailable: response.copyFallbackAvailable
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

    private var supportIncidentItemIDs: [String] {
        let ids = summary.affectedItems.map(\.id)
        return ids.isEmpty ? [summary.primaryItem.id] : ids
    }

    private func copySafeReport(_ report: DesktopUploadCustodySafeReport) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(report.clipboardText, forType: .string)
        copiedItemID = summary.primaryItem.id
    }

    private static func failure(_ error: Error) -> (category: String, code: String) {
        if let clientError = error as? DesktopUploadClientError {
            switch clientError {
            case .httpStatus(_, let code):
                return (clientError.failureCategory.rawValue, code)
            case .invalidBaseURL:
                return (clientError.failureCategory.rawValue, "support_incident.invalid_base_url")
            case .invalidResponse:
                return (clientError.failureCategory.rawValue, "support_incident.invalid_response")
            case .localFileMissing, .serverStillMissingRanges:
                return (clientError.failureCategory.rawValue, "support_incident.unavailable")
            }
        }
        return (UploadFailureCategory.network.rawValue, "support_incident.unavailable")
    }
}
