import SwiftUI

/// The persistent reminder is native so it remains available without a cabinet connection.
public struct AppUpdateNotice: View {
    private let presentation: AppUpdatePresentation
    private let isActionEnabled: Bool
    private let onUpdate: () -> Void

    public init(presentation: AppUpdatePresentation, isActionEnabled: Bool, onUpdate: @escaping () -> Void) {
        self.presentation = presentation
        self.isActionEnabled = isActionEnabled
        self.onUpdate = onUpdate
    }

    public var body: some View {
        if presentation.showsSidebarBadge, let version = presentation.availableVersion {
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 16) {
                    copy(version: version).fixedSize(horizontal: true, vertical: false)
                    Spacer(minLength: 0)
                    updateButton
                }
                VStack(alignment: .leading, spacing: 8) {
                    copy(version: version)
                    updateButton
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.accentColor.opacity(0.08))
            .accessibilityElement(children: .contain)
            .accessibilityIdentifier("graf.appUpdate.notice")
        }
    }

    private func copy(version: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Label("Доступна новая версия GRAF \(version)", systemImage: "arrow.down.circle")
                .font(.callout.weight(.semibold))
            Text(presentation.message ?? "Обновите GRAF, чтобы получить последние улучшения.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .accessibilityElement(children: .combine)
    }

    private var updateButton: some View {
        Button(action: onUpdate) {
            Text(actionTitle)
                .frame(minHeight: 40)
                .padding(.horizontal, 8)
        }
        .buttonStyle(.bordered)
        .disabled(!isActionEnabled)
        .keyboardShortcut("u", modifiers: [.command, .shift])
        .help("Проверить и открыть обновление (⇧⌘U)")
        .accessibilityLabel("Открыть обновление GRAF")
        .accessibilityIdentifier("graf.appUpdate.open")
    }

    private var actionTitle: String {
        switch presentation.phase {
        case .failed: "Повторить"
        case .downloading, .installing: "Открыть обновление"
        default: "Обновить GRAF"
        }
    }
}
