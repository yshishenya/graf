import SwiftUI

public struct UninstallResult: Equatable, Sendable {
    public let succeeded: Bool
    public let requiresRestart: Bool
    public let manualRemediation: [String]
    public let restoredInput: String?
    public let restoredOutput: String?
    public let warningMessage: String?

    public init(
        succeeded: Bool,
        requiresRestart: Bool,
        manualRemediation: [String],
        restoredInput: String? = nil,
        restoredOutput: String? = nil,
        warningMessage: String? = nil
    ) {
        self.succeeded = succeeded
        self.requiresRestart = requiresRestart
        self.manualRemediation = manualRemediation
        self.restoredInput = restoredInput
        self.restoredOutput = restoredOutput
        self.warningMessage = warningMessage
    }
}

public struct UninstallResultView: View {
    public static let openSoundSettingsAccessibilityLabel = "Open Sound Settings"
    public static let doneAccessibilityLabel = "Close uninstall result"

    private let result: UninstallResult
    private let onDone: () -> Void
    private let onOpenSettings: (() -> Void)?

    public init(
        result: UninstallResult,
        onDone: @escaping () -> Void,
        onOpenSettings: (() -> Void)? = nil
    ) {
        self.result = result
        self.onDone = onDone
        self.onOpenSettings = onOpenSettings
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            statusHeader
            if let warningMessage = result.warningMessage {
                Text(warningMessage)
                    .font(.callout)
                    .foregroundStyle(.orange)
                    .padding(8)
                    .background(RoundedRectangle(cornerRadius: 8).fill(.orange.opacity(0.15)))
            }

            if let restoredInput = result.restoredInput {
                line("Input restored", detail: restoredInput)
            }
            if let restoredOutput = result.restoredOutput {
                line("Output restored", detail: restoredOutput)
            }

            if !result.manualRemediation.isEmpty {
                Divider()
                Text("Manual remediation")
                    .font(.callout)
                    .fontWeight(.semibold)
                ForEach(result.manualRemediation.indices, id: \.self) { index in
                    Text("• \(result.manualRemediation[index])")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            HStack {
                if let onOpenSettings {
                    Button("Open Sound Settings") {
                        onOpenSettings()
                    }
                    .buttonStyle(.bordered)
                    .accessibilityLabel(Self.openSoundSettingsAccessibilityLabel)
                    .help(Self.openSoundSettingsAccessibilityLabel)
                }
                Spacer()
                Button("Done") {
                    onDone()
                }
                .buttonStyle(.borderedProminent)
                .accessibilityLabel(Self.doneAccessibilityLabel)
                .help(Self.doneAccessibilityLabel)
            }
        }
        .padding(16)
    }

    @ViewBuilder
    private var statusHeader: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Image(systemName: result.succeeded ? "checkmark.seal.fill" : "exclamationmark.octagon.fill")
                    .foregroundStyle(result.succeeded ? .green : .orange)
                Text(result.succeeded ? "Uninstall completed" : "Uninstall partial")
                    .font(.title3)
                    .fontWeight(.semibold)
            }
            if result.requiresRestart {
                Text("Restart required")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func line(_ label: String, detail: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(detail)
                .font(.caption)
                .foregroundStyle(.primary)
                .lineLimit(1)
                .truncationMode(.tail)
        }
        .accessibilityElement(children: .combine)
    }
}
