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
        if presentation.showsActionBanner {
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 16) {
                    copy.fixedSize(horizontal: true, vertical: false)
                    Spacer(minLength: 0)
                    updateButton
                }
                VStack(alignment: .leading, spacing: 8) {
                    copy
                    updateButton
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesktopDesignTokens.accentSurface)
            .accessibilityElement(children: .contain)
            .accessibilityIdentifier("graf.appUpdate.notice")
        }
    }

    private var copy: some View {
        VStack(alignment: .leading, spacing: 4) {
            Label(presentation.bannerTitle, systemImage: "arrow.down.circle")
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
            Text(presentation.bannerActionTitle)
                .frame(minHeight: 40)
                .padding(.horizontal, 8)
        }
        .buttonStyle(.bordered)
        .tint(DesktopDesignTokens.accentSolid)
        .disabled(!isActionEnabled)
        .keyboardShortcut("u", modifiers: [.command, .shift])
        .help("Проверить и открыть обновление (⇧⌘U)")
        .accessibilityLabel("Открыть обновление GRAF")
        .accessibilityIdentifier("graf.appUpdate.open")
    }
}
