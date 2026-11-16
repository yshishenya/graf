import AppKit
import SwiftUI
import TwoBrainRecShared

struct LocalCacheCleanupPrompt: Identifiable, Equatable {
    let id = UUID()
    let itemID: String
    let bytes: Int64
}

struct LocalCacheStatusCardView: View {
    let status: LocalCacheStatusPresentation?
    let onSetAutoEvictionEnabled: (Bool) -> Void
    let onRefresh: () -> Void

    @State private var userEnabled = true

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Label(LocalCacheCleanupCopy.cacheTitle, systemImage: "internaldrive")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Spacer()
                Button(action: onRefresh) {
                    Image(systemName: "arrow.clockwise")
                        .frame(minWidth: 24, minHeight: 24)
                }
                .buttonStyle(.borderless)
                .frame(minWidth: 40, minHeight: 40)
                .help("Обновить состояние локального кэша")
                .accessibilityLabel("Обновить состояние локального кэша")
                .accessibilityIdentifier("local-cache-status-refresh")
            }

            if let status {
                Text(
                    LocalCacheCleanupCopy.statusLine(
                        used: LocalCacheByteFormat.string(from: status.usedBytes),
                        budget: LocalCacheByteFormat.string(from: status.budgetBytes)
                    )
                )
                .font(.caption)
                .accessibilityLabel(
                    LocalCacheCleanupCopy.accessibilityStatus(
                        used: LocalCacheByteFormat.string(from: status.usedBytes),
                        budget: LocalCacheByteFormat.string(from: status.budgetBytes)
                    )
                )

                Text(LocalCacheCleanupCopy.cacheExplanation)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                Toggle(
                    isOn: Binding(
                        get: { userEnabled },
                        set: { value in
                            userEnabled = value
                            onSetAutoEvictionEnabled(value)
                        }
                    )
                ) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(LocalCacheCleanupCopy.autoEvictionToggle)
                            .font(.caption)
                        Text(LocalCacheCleanupCopy.autoEvictionToggleDetail)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                .toggleStyle(.switch)
                .disabled(status.settings.operatorDisabled)
                .accessibilityLabel(
                    LocalCacheCleanupCopy.accessibilityToggle(
                        detail: LocalCacheCleanupCopy.autoEvictionToggleDetail
                    )
                )
                .accessibilityIdentifier("local-cache-auto-eviction-toggle")

                if let disabled = status.disabledExplanation {
                    Text(disabled)
                        .font(.caption2)
                        .foregroundStyle(status.settings.operatorDisabled ? .secondary : .primary)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityIdentifier("local-cache-auto-eviction-disabled")
                }
                if status.showsAutomaticCleanupWarning {
                    Text(LocalCacheCleanupCopy.cacheWarning)
                        .font(.caption2)
                        .foregroundStyle(DesktopDesignTokens.amber)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityIdentifier("local-cache-warning")
                }
                if let lastFreed = status.lastFreedBytes, lastFreed > 0 {
                    Text(
                        LocalCacheCleanupCopy.evictionResult(
                            size: LocalCacheByteFormat.string(from: lastFreed)
                        )
                    )
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("local-cache-last-freed")
                }
            } else {
                Text("Состояние локального кэша недоступно.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: DesktopDesignTokens.Radius.sm)
                .fill(DesktopMeetingShellChrome.shellSurfaceColor)
        )
        .overlay(
            RoundedRectangle(cornerRadius: DesktopDesignTokens.Radius.sm)
                .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
        )
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("local-cache-status")
        .onAppear {
            userEnabled = status?.settings.userEnabled ?? true
        }
        .onChange(of: status?.settings.userEnabled) { _, value in
            if let value { userEnabled = value }
        }
    }
}

struct LocalCacheCleanupConfirmationView: View {
    let bytes: Int64
    let isRunning: Bool
    let onConfirm: () -> Void
    let onCancel: () -> Void

    private var formattedBytes: String {
        LocalCacheByteFormat.string(from: bytes)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(LocalCacheCleanupCopy.confirmationTitle)
                .font(.title3.weight(.semibold))
            Text(LocalCacheCleanupCopy.confirmationBody)
                .font(.callout)
                .fixedSize(horizontal: false, vertical: true)
            Text(LocalCacheCleanupCopy.spaceLine(size: formattedBytes))
                .font(.callout.weight(.medium))
            HStack(spacing: 12) {
                Button(LocalCacheCleanupCopy.cancelTitle, action: onCancel)
                    .buttonStyle(DesktopWebButtonStyle(.secondary))
                    .frame(minHeight: 40)
                    .disabled(isRunning)
                    .accessibilityIdentifier("local-cache-cleanup-cancel")
                Button(
                    LocalCacheCleanupCopy.confirmButtonTitle(size: formattedBytes),
                    action: onConfirm
                )
                .buttonStyle(DesktopWebButtonStyle(.destructive))
                .frame(minHeight: 40)
                .disabled(isRunning)
                .accessibilityIdentifier("local-cache-cleanup-confirm")
            }
        }
        .padding(24)
        .frame(width: 480, alignment: .leading)
        .accessibilityElement(children: .contain)
        .accessibilityLabel(LocalCacheCleanupCopy.accessibilityConfirmation)
        .accessibilityIdentifier("local-cache-cleanup-confirmation")
    }
}

struct LocalCacheCleanupResultBanner: View {
    let message: String
    let onDismiss: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "internaldrive")
                .foregroundStyle(DesktopDesignTokens.muted)
            Text(message)
                .font(.caption)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 8)
            Button(action: onDismiss) {
                Image(systemName: "xmark")
            }
            .buttonStyle(.borderless)
            .accessibilityLabel("Закрыть сообщение")
            .accessibilityIdentifier("local-cache-cleanup-result-dismiss")
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: DesktopDesignTokens.Radius.sm)
                .fill(DesktopMeetingShellChrome.shellSurfaceColor)
        )
        .overlay(
            RoundedRectangle(cornerRadius: DesktopDesignTokens.Radius.sm)
                .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
        )
        .accessibilityElement(children: .contain)
        .accessibilityLabel(message)
        .accessibilityIdentifier("local-cache-cleanup-result")
    }
}

struct LocalCachePanelView: View {
    let initialStatus: LocalCacheStatusPresentation?
    let candidates: [LocalCacheCleanupCandidate]
    let totalCandidateCount: Int
    let timeZone: TimeZone
    let onRefreshStatus: () async -> LocalCacheStatusPresentation?
    let onSetAutoEvictionEnabled: (Bool) -> Void
    let onRequestCleanup: (LocalCacheCleanupPrompt) -> Void
    let onClose: () -> Void

    @State private var status: LocalCacheStatusPresentation?
    @State private var refreshInProgress = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 12) {
                Text(LocalCacheCleanupCopy.cacheTitle)
                    .font(.title3.weight(.semibold))
                Spacer()
                Button(action: onClose) {
                    Image(systemName: "xmark")
                        .frame(minWidth: 24, minHeight: 24)
                }
                .buttonStyle(.borderless)
                .frame(minWidth: 40, minHeight: 40)
                .help("Закрыть")
                .accessibilityLabel("Закрыть локальный кэш")
                .accessibilityIdentifier("local-cache-panel-close")
            }

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    LocalCacheStatusCardView(
                        status: status,
                        onSetAutoEvictionEnabled: { enabled in
                            onSetAutoEvictionEnabled(enabled)
                            Task { await refresh() }
                        },
                        onRefresh: {
                            Task { await refresh() }
                        }
                    )
                    candidatesSection
                }
            }
        }
        .padding(20)
        .frame(width: 560, height: 560, alignment: .topLeading)
        .background(Color(nsColor: .windowBackgroundColor))
        .onAppear {
            if status == nil { status = initialStatus }
        }
        .task { await refresh() }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("local-cache-panel")
    }

    private var candidatesSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Файлы транскрипции, готовые к очистке")
                .font(.subheadline)
                .fontWeight(.semibold)
            Text(
                "Показаны записи, которые можно очистить после проверки серверной копии. " +
                "Аудио для прослушивания и описание записи остаются."
            )
            .font(.caption2)
            .foregroundStyle(.secondary)
            .fixedSize(horizontal: false, vertical: true)

            if candidates.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Нет файлов, готовых к очистке.")
                        .font(.callout)
                    Text("Когда локальные файлы транскрипции будут готовы к очистке, они появятся здесь.")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(14)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: DesktopDesignTokens.Radius.sm)
                        .fill(DesktopMeetingShellChrome.shellSurfaceColor)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: DesktopDesignTokens.Radius.sm)
                        .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
                )
                .accessibilityElement(children: .combine)
                .accessibilityIdentifier("local-cache-panel-empty")
            } else {
                VStack(spacing: 0) {
                    ForEach(candidates) { candidate in
                        candidateRow(candidate)
                        if candidate.id != candidates.last?.id {
                            Divider()
                        }
                    }
                }
                .background(
                    RoundedRectangle(cornerRadius: DesktopDesignTokens.Radius.sm)
                        .fill(DesktopMeetingShellChrome.shellSurfaceColor)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: DesktopDesignTokens.Radius.sm)
                        .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
                )
                if totalCandidateCount > candidates.count {
                    Text("Показаны первые \(candidates.count) записей. Остальные доступны в общем списке.")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    private func candidateRow(_ candidate: LocalCacheCleanupCandidate) -> some View {
        HStack(spacing: 12) {
            Image(systemName: "waveform")
                .frame(width: 18)
                .foregroundStyle(DesktopDesignTokens.muted)
            VStack(alignment: .leading, spacing: 3) {
                Text(UserTime.format(candidate.startedAt, showZone: true, timeZone: timeZone))
                    .font(.callout.weight(.medium))
                    .lineLimit(1)
                Text(LocalCacheByteFormat.string(from: candidate.bytes))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 8)
            Button(LocalCacheCleanupCopy.actionTitle) {
                onRequestCleanup(
                    LocalCacheCleanupPrompt(itemID: candidate.itemID, bytes: candidate.bytes)
                )
            }
            .buttonStyle(DesktopWebButtonStyle(.secondary))
            .frame(minHeight: 40)
            .help(LocalCacheCleanupCopy.accessibilityAction)
            .accessibilityLabel(LocalCacheCleanupCopy.accessibilityAction)
            .accessibilityIdentifier("local-cache-panel-cleanup-\(candidate.itemID)")
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
        .accessibilityElement(children: .contain)
    }

    @MainActor
    private func refresh() async {
        guard !refreshInProgress else { return }
        refreshInProgress = true
        defer { refreshInProgress = false }
        status = await onRefreshStatus()
    }
}
