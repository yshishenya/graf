import AppKit
import SwiftUI
import TwoBrainRecShared

public struct MeetingDetectionSettingsView: View {
    public static let windowTitle = "Настройки"
    public static let sidebarTitle = "Встречи"
    public static let pageTitle = "Автоопределение"
    public static let promptToggleTitle = "Запрашивать запись"
    public static let promptToggleDetail =
        "Если выключено, запросы не показываются и запись не запускается. Определение встреч продолжает работать."
    private let store: MeetingDetectionSettingsStore
    private let notificationCenter: NotificationCenter

    @State private var settings: MeetingDetectionSettings
    @State private var saveError: String?

    public init(
        store: MeetingDetectionSettingsStore = MeetingDetectionSettingsStore(),
        notificationCenter: NotificationCenter = .default
    ) {
        self.store = store
        self.notificationCenter = notificationCenter
        _settings = State(initialValue: (try? store.load()) ?? MeetingDetectionSettings())
    }

    public var body: some View {
        HStack(spacing: 0) {
            sidebar
            Divider()
            content
        }
        .frame(width: 760, height: 500)
        .background(Color(nsColor: .windowBackgroundColor))
        .onReceive(notificationCenter.publisher(for: .twoBrainRecMeetingDetectionSettingsDidChange)) { _ in
            reloadSettings()
        }
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 18) {
            Button {
                NSApp.keyWindow?.close()
            } label: {
                Label("Назад", systemImage: "chevron.left")
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
            .padding(.top, 18)

            VStack(alignment: .leading, spacing: 7) {
                Text(Self.sidebarTitle)
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundStyle(.secondary)

                Label(Self.pageTitle, systemImage: "record.circle")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.accentColor.opacity(0.18), in: RoundedRectangle(cornerRadius: 6))
                    .accessibilityAddTraits(.isSelected)
            }

            Spacer()
        }
        .padding(.horizontal, 16)
        .frame(width: 176)
        .background(.bar)
    }

    private var content: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 28) {
                Label(Self.pageTitle, systemImage: "dot.radiowaves.left.and.right")
                    .font(.headline)

                VStack(alignment: .leading, spacing: 8) {
                    HStack(alignment: .firstTextBaseline, spacing: 12) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(Self.promptToggleTitle)
                                .font(.subheadline)
                                .fontWeight(.semibold)
                            Text(Self.promptToggleDetail)
                                .font(.callout)
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        Spacer()
                        Toggle("", isOn: recordingPromptBinding)
                            .toggleStyle(.switch)
                            .labelsHidden()
                            .accessibilityLabel(Self.promptToggleTitle)
                            .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.meetingDetectionRecordingToggle)
                    }
                }

                if let saveError {
                    Label(saveError, systemImage: "exclamationmark.triangle.fill")
                        .font(.callout)
                        .foregroundStyle(.orange)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer()
            }
            .padding(.horizontal, 34)
            .padding(.vertical, 28)
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var recordingPromptBinding: Binding<Bool> {
        Binding(
            get: { settings.detectionMode == .detectAndAsk },
            set: { enabled in
                updateSettings { draft in
                    draft.detectionMode = enabled ? .detectAndAsk : .detectOnly
                }
            }
        )
    }

    private func updateSettings(_ transform: (inout MeetingDetectionSettings) -> Void) {
        var draft = settings
        transform(&draft)
        do {
            try store.save(draft)
            settings = draft
            saveError = nil
            notificationCenter.post(name: .twoBrainRecMeetingDetectionSettingsDidChange, object: nil)
        } catch {
            saveError = "Настройки временно не сохранены"
        }
    }

    private func reloadSettings() {
        guard let loaded = try? store.load() else {
            saveError = "Настройки временно недоступны"
            return
        }
        settings = loaded
        saveError = nil
    }
}
