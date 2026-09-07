import Combine
import Foundation
import Sparkle

public enum AppUpdatePhase: String, CaseIterable, Equatable, Sendable {
    case unavailable
    case idle
    case checking
    case current
    case available
    case deferredForCapture
    case downloading
    case readyToInstall
    case installing
    case failed
}

public struct AppUpdatePresentation: Equatable, Sendable {
    public let phase: AppUpdatePhase
    public let availableVersion: String?
    public let isUserInitiated: Bool
    public let message: String?

    public init(
        phase: AppUpdatePhase,
        availableVersion: String?,
        isUserInitiated: Bool,
        message: String?
    ) {
        self.phase = phase
        self.availableVersion = availableVersion
        self.isUserInitiated = isUserInitiated
        self.message = message
    }

    public var showsSidebarBadge: Bool {
        availableVersion != nil && phase != .unavailable
    }

    public static let idle = AppUpdatePresentation(
        phase: .idle,
        availableVersion: nil,
        isUserInitiated: false,
        message: nil
    )

    public static let unavailable = AppUpdatePresentation(
        phase: .unavailable,
        availableVersion: nil,
        isUserInitiated: false,
        message: "Безопасная проверка обновлений недоступна в этой сборке GRAF."
    )
}

public struct ProtectedUpdateWork: Equatable, Sendable {
    public let captureActive: Bool
    public let captureTransitioning: Bool
    public let recordingFinalizing: Bool
    public let terminationCleanupPending: Bool

    public init(
        captureActive: Bool = false,
        captureTransitioning: Bool = false,
        recordingFinalizing: Bool = false,
        terminationCleanupPending: Bool = false
    ) {
        self.captureActive = captureActive
        self.captureTransitioning = captureTransitioning
        self.recordingFinalizing = recordingFinalizing
        self.terminationCleanupPending = terminationCleanupPending
    }

    public var isProtected: Bool {
        captureActive || captureTransitioning || recordingFinalizing || terminationCleanupPending
    }

    public static let idle = ProtectedUpdateWork()
}

public struct AppUpdateConfiguration: Codable, Equatable, Sendable {
    public static let checkInterval: TimeInterval = 14_400
    public let feedURL: URL
    public let publicEDKey: String
    public let installedVersion: String

    public init?(infoDictionary: [String: Any]) {
        guard
            infoDictionary["CFBundleIdentifier"] as? String == "pro.2brain.graf",
            infoDictionary["CFBundleName"] as? String == "GRAF",
            infoDictionary["CFBundleDisplayName"] as? String == "GRAF",
            let rawFeedURL = infoDictionary["SUFeedURL"] as? String,
            let feedURL = URL(string: rawFeedURL),
            let components = URLComponents(url: feedURL, resolvingAgainstBaseURL: false),
            components.scheme?.lowercased() == "https",
            components.host?.isEmpty == false,
            components.user == nil,
            components.password == nil,
            components.query == nil,
            components.fragment == nil,
            components.path.hasSuffix("/graf-appcast.xml"),
            let rawPublicKey = infoDictionary["SUPublicEDKey"] as? String,
            let publicKeyData = Data(
                base64Encoded: rawPublicKey.trimmingCharacters(in: .whitespacesAndNewlines)
            ),
            publicKeyData.count == 32,
            Self.boolValue(infoDictionary["SURequireSignedFeed"]) == true,
            Self.boolValue(infoDictionary["SUVerifyUpdateBeforeExtraction"]) == true,
            Self.integerValue(infoDictionary["SUSignedFeedFailureExpirationInterval"]) == 0,
            Self.boolValue(infoDictionary["SUEnableAutomaticChecks"]) == true,
            Self.integerValue(infoDictionary["SUScheduledCheckInterval"]) == Int(Self.checkInterval),
            Self.boolValue(infoDictionary["SUAutomaticallyUpdate"]) == false,
            Self.boolValue(infoDictionary["SUAllowsAutomaticUpdates"]) == false,
            Self.boolValue(infoDictionary["SUEnableSystemProfiling"]) == false,
            let installedVersion = infoDictionary["CFBundleVersion"] as? String,
            infoDictionary["CFBundleShortVersionString"] as? String == installedVersion,
            Self.isValidCalVer(installedVersion)
        else {
            return nil
        }

        self.feedURL = feedURL
        publicEDKey = rawPublicKey.trimmingCharacters(in: .whitespacesAndNewlines)
        self.installedVersion = installedVersion
    }

    public static func isValidCalVer(_ version: String) -> Bool {
        let components = version.split(separator: ".", omittingEmptySubsequences: false)
        guard
            components.count == 4,
            components[0].count == 4,
            components[1].count == 2,
            components[2].count == 2,
            let year = Int(components[0]),
            let month = Int(components[1]),
            let day = Int(components[2]),
            let sequence = Int(components[3]),
            (2020...9999).contains(year),
            (1...12).contains(month),
            (1...31).contains(day),
            sequence > 0,
            DateComponents(year: year, month: month, day: day)
                .isValidDate(in: Calendar(identifier: .gregorian))
        else {
            return false
        }
        return true
    }

    private static func boolValue(_ value: Any?) -> Bool? {
        if let value = value as? Bool {
            return value
        }
        if let value = value as? NSNumber {
            return value.boolValue
        }
        return nil
    }

    private static func integerValue(_ value: Any?) -> Int? {
        if let value = value as? Int {
            return value
        }
        if let value = value as? NSNumber {
            return value.intValue
        }
        return nil
    }
}

/// Display-only metadata. Sparkle must validate the current offer again before installation.
public struct AppUpdateReminder: Codable, Equatable, Sendable {
    public let buildVersion: String
    public let displayVersion: String
    public let configuration: AppUpdateConfiguration
    public let systemVersion: String

    public init?(
        buildVersion: String,
        displayVersion: String,
        configuration: AppUpdateConfiguration,
        systemVersion: String = ProcessInfo.processInfo.operatingSystemVersionString
    ) {
        guard AppUpdateConfiguration.isValidCalVer(buildVersion),
              AppUpdateConfiguration.isValidCalVer(displayVersion),
              SUStandardVersionComparator.default.compareVersion(
                buildVersion, toVersion: configuration.installedVersion
              ) == .orderedDescending else { return nil }
        self.buildVersion = buildVersion
        self.displayVersion = displayVersion
        self.configuration = configuration
        self.systemVersion = systemVersion
    }

    public static func restore(
        _ data: Data?,
        configuration: AppUpdateConfiguration,
        systemVersion: String = ProcessInfo.processInfo.operatingSystemVersionString
    ) -> AppUpdateReminder? {
        guard let data, data.count <= 4096,
              let saved = try? JSONDecoder().decode(Self.self, from: data),
              saved.configuration == configuration, saved.systemVersion == systemVersion
        else { return nil }
        return Self(buildVersion: saved.buildVersion, displayVersion: saved.displayVersion,
                    configuration: configuration, systemVersion: systemVersion)
    }

    public func isWithdrawn(from versions: [String], signatureVerified: Bool) -> Bool {
        signatureVerified && !versions.contains(buildVersion)
    }
}

public enum AppUpdateUserChoice: Equatable, Sendable {
    case install
    case dismiss
    case skip
}

public enum AppUpdatePolicy {
    public static func beginCheck(
        from current: AppUpdatePresentation,
        userInitiated: Bool
    ) -> AppUpdatePresentation {
        if current.availableVersion != nil {
            return AppUpdatePresentation(
                phase: current.phase,
                availableVersion: current.availableVersion,
                isUserInitiated: current.isUserInitiated || userInitiated,
                message: current.message
            )
        }
        return AppUpdatePresentation(
            phase: .checking,
            availableVersion: nil,
            isUserInitiated: current.isUserInitiated || userInitiated,
            message: userInitiated ? "Проверяем обновления…" : nil
        )
    }

    public static func available(
        version: String,
        userInitiated: Bool,
        protectedWork: ProtectedUpdateWork
    ) -> AppUpdatePresentation {
        AppUpdatePresentation(
            phase: protectedWork.isProtected ? .deferredForCapture : .available,
            availableVersion: version,
            isUserInitiated: userInitiated,
            message: protectedWork.isProtected
                ? "Обновление GRAF \(version) будет предложено после завершения записи."
                : "Доступно обновление GRAF \(version)."
        )
    }

    public static func noUpdate(
        userInitiated: Bool,
        incompatible: Bool,
        from current: AppUpdatePresentation = .idle
    ) -> AppUpdatePresentation {
        // A background no-update result also excludes versions the user skipped.
        if current.availableVersion != nil && !incompatible { return current }
        return AppUpdatePresentation(
            phase: .current,
            availableVersion: nil,
            isUserInitiated: userInitiated,
            message: incompatible
                ? "Новая версия GRAF не поддерживает этот Mac или установленную версию macOS."
                : "Установлена актуальная версия GRAF."
        )
    }

    public static func failure(
        userInitiated: Bool,
        from current: AppUpdatePresentation = .idle,
        message: String = "Не удалось проверить обновления. Повторите позже."
    ) -> AppUpdatePresentation {
        AppUpdatePresentation(
            phase: .failed,
            availableVersion: current.availableVersion,
            isUserInitiated: userInitiated,
            message: message
        )
    }

    public static func protectedWorkChanged(
        from current: AppUpdatePresentation,
        protectedWork: ProtectedUpdateWork
    ) -> AppUpdatePresentation {
        guard let version = current.availableVersion else { return current }
        if protectedWork.isProtected,
           current.phase == .available || current.phase == .readyToInstall || current.phase == .installing {
            return available(
                version: version,
                userInitiated: current.isUserInitiated,
                protectedWork: protectedWork
            )
        }
        if !protectedWork.isProtected, current.phase == .deferredForCapture {
            return available(
                version: version,
                userInitiated: current.isUserInitiated,
                protectedWork: .idle
            )
        }
        return current
    }

    public static func userChoice(
        _ choice: AppUpdateUserChoice,
        from current: AppUpdatePresentation,
        protectedWork: ProtectedUpdateWork
    ) -> AppUpdatePresentation {
        switch choice {
        case .skip, .dismiss:
            return current
        case .install:
            guard let version = current.availableVersion else { return current }
            return AppUpdatePresentation(
                phase: protectedWork.isProtected ? .deferredForCapture : .installing,
                availableVersion: version,
                isUserInitiated: current.isUserInitiated,
                message: protectedWork.isProtected
                    ? "Обновление GRAF \(version) установится после завершения записи."
                    : "GRAF готовит установку обновления \(version)."
            )
        }
    }
}

@MainActor
public final class AppUpdateRelaunchGate {
    public private(set) var protectedWork: ProtectedUpdateWork
    private var retainedContinuation: (() -> Void)?

    public init(protectedWork: ProtectedUpdateWork = .idle) {
        self.protectedWork = protectedWork
    }

    public var hasRetainedContinuation: Bool {
        retainedContinuation != nil
    }

    public func postponeIfNeeded(_ continuation: @escaping () -> Void) -> Bool {
        guard protectedWork.isProtected else { return false }
        if retainedContinuation == nil {
            retainedContinuation = continuation
        }
        return true
    }

    @discardableResult
    public func updateProtectedWork(_ work: ProtectedUpdateWork) -> Bool {
        protectedWork = work
        guard !work.isProtected, let continuation = retainedContinuation else {
            return false
        }
        retainedContinuation = nil
        continuation()
        return true
    }
}

@MainActor
public final class AppUpdateController: NSObject, ObservableObject {
    public typealias EventLogger = @MainActor @Sendable (_ event: String, _ detail: String) -> Void

    @Published public private(set) var presentation: AppUpdatePresentation

    public private(set) var protectedWork: ProtectedUpdateWork = .idle

    @Published public private(set) var isManualCheckActionEnabled = false

    private let configuration: AppUpdateConfiguration?
    private let defaults: UserDefaults
    private var reminder: AppUpdateReminder?
    private var checkAvailabilityObservation: NSKeyValueObservation?
    public static let reminderDefaultsKey = "graf.appUpdate.reminder"
    private let eventLogger: EventLogger?
    private let relaunchGate = AppUpdateRelaunchGate()
    private var updaterController: SPUStandardUpdaterController?
    private var suppressedScheduledOffer = false
    private var started = false

    public init(
        infoDictionary: [String: Any] = Bundle.main.infoDictionary ?? [:],
        defaults: UserDefaults = .standard,
        eventLogger: EventLogger? = nil
    ) {
        let configuration = AppUpdateConfiguration(infoDictionary: infoDictionary)
        self.configuration = configuration
        self.defaults = defaults
        self.eventLogger = eventLogger
        reminder = configuration.flatMap {
            AppUpdateReminder.restore(defaults.data(forKey: Self.reminderDefaultsKey), configuration: $0)
        }
        presentation = reminder.map {
            AppUpdatePresentation(phase: .available, availableVersion: $0.displayVersion,
                                  isUserInitiated: false,
                                  message: "Проверьте и установите обновление. Перед установкой GRAF проверит его доступность.")
        } ?? (configuration == nil ? .unavailable : .idle)
        if reminder == nil { defaults.removeObject(forKey: Self.reminderDefaultsKey) }
        super.init()

        if configuration != nil {
            updaterController = SPUStandardUpdaterController(
                startingUpdater: false,
                updaterDelegate: self,
                userDriverDelegate: self
            )
            checkAvailabilityObservation = updaterController?.updater.observe(
                \.canCheckForUpdates, options: [.initial, .new]
            ) { [weak self] _, change in
                let enabled = change.newValue == true
                Task { @MainActor [weak self] in self?.isManualCheckActionEnabled = enabled }
            }
        } else {
            isManualCheckActionEnabled = true
        }
    }

    public func start() {
        guard !started, let updaterController else { return }
        started = true
        let updater = updaterController.updater
        if !defaults.bool(forKey: "graf.appUpdate.intervalMigrated") {
            if updater.updateCheckInterval == 86_400 {
                updater.updateCheckInterval = AppUpdateConfiguration.checkInterval
            }
            defaults.set(true, forKey: "graf.appUpdate.intervalMigrated")
        }
        updaterController.startUpdater()
        log(event: "app_update.started")
        if updater.automaticallyChecksForUpdates && updater.canCheckForUpdates {
            updater.checkForUpdatesInBackground()
        }
    }

    @discardableResult
    public func checkForUpdates(_ sender: Any? = nil) -> Bool {
        guard started, let updaterController else {
            updatePresentation(.unavailable, event: "app_update.manual_unavailable")
            return false
        }
        guard updaterController.updater.canCheckForUpdates else { return true }

        updatePresentation(
            AppUpdatePolicy.beginCheck(from: presentation, userInitiated: true),
            event: "app_update.manual_check_requested"
        )
        updaterController.checkForUpdates(sender)
        return true
    }

    public func updateProtectedWork(_ work: ProtectedUpdateWork) {
        let wasProtected = protectedWork.isProtected
        protectedWork = work
        let releasedRelaunch = relaunchGate.updateProtectedWork(work)
        updatePresentation(
            AppUpdatePolicy.protectedWorkChanged(from: presentation, protectedWork: work),
            event: "app_update.protected_work_changed"
        )

        guard wasProtected, !work.isProtected else { return }
        if releasedRelaunch {
            suppressedScheduledOffer = false
            updatePresentation(
                AppUpdatePolicy.userChoice(.install, from: presentation, protectedWork: .idle),
                event: "app_update.relaunch_released"
            )
            return
        }
        if suppressedScheduledOffer {
            suppressedScheduledOffer = false
            updaterController?.checkForUpdates(nil)
            log(event: "app_update.deferred_offer_presented")
        }
    }

    private func updatePresentation(_ next: AppUpdatePresentation, event: String, error: NSError? = nil) {
        presentation = next
        log(event: event, error: error)
    }

    private func clearReminder() {
        reminder = nil
        defaults.removeObject(forKey: Self.reminderDefaultsKey)
    }

    private func log(event: String, error: NSError? = nil) {
        var fields = [
            "installedVersion=\(configuration?.installedVersion ?? "unknown")",
            "offeredVersion=\(presentation.availableVersion ?? "none")",
            "phase=\(presentation.phase.rawValue)",
            "userInitiated=\(presentation.isUserInitiated)",
            "protectedWork=\(protectedWork.isProtected)"
        ]
        if let error {
            fields.append("errorDomain=\(Self.sanitized(error.domain))")
            fields.append("errorCode=\(error.code)")
        }
        eventLogger?(event, fields.joined(separator: " "))
    }

    private static func sanitized(_ value: String) -> String {
        value
            .replacingOccurrences(of: " ", with: "_")
            .replacingOccurrences(of: "\n", with: "_")
            .replacingOccurrences(of: "\r", with: "_")
    }
}

extension AppUpdateController: SPUUpdaterDelegate {
    public func updater(_ updater: SPUUpdater, didFinishLoading appcast: SUAppcast) {
        // The signed, complete feed precedes Sparkle's skip/phased-rollout filtering.
        // Only reconcile an existing offer; never select new offers here.
        guard let reminder, reminder.isWithdrawn(
            from: appcast.items.map(\.versionString),
            signatureVerified: appcast.signingValidationStatus == .succeeded
        )
        else { return }
        clearReminder()
        updatePresentation(.idle, event: "app_update.offer_withdrawn")
    }

    public func updater(_ updater: SPUUpdater, didFindValidUpdate item: SUAppcastItem) {
        guard let configuration,
              let found = AppUpdateReminder(buildVersion: item.versionString,
                                            displayVersion: item.displayVersionString,
                                            configuration: configuration) else { return }
        reminder = found
        defaults.set(try? JSONEncoder().encode(found), forKey: Self.reminderDefaultsKey)
        let next = AppUpdatePolicy.available(
            version: item.displayVersionString,
            userInitiated: presentation.isUserInitiated,
            protectedWork: protectedWork
        )
        updatePresentation(next, event: "app_update.available")
    }

    public func updaterDidNotFindUpdate(_ updater: SPUUpdater, error: Error) {
        let nsError = error as NSError
        let reason = (nsError.userInfo[SPUNoUpdateFoundReasonKey] as? NSNumber)?.intValue
        let incompatibleReasons: Set<Int> = [
            Int(SPUNoUpdateFoundReason.systemIsTooOld.rawValue),
            Int(SPUNoUpdateFoundReason.systemIsTooNew.rawValue),
            Int(SPUNoUpdateFoundReason.hardwareDoesNotSupportARM64.rawValue)
        ]
        let incompatible = reason.map { incompatibleReasons.contains($0) } ?? false
        let userInitiated = (nsError.userInfo[SPUNoUpdateFoundUserInitiatedKey] as? NSNumber)?.boolValue
            ?? presentation.isUserInitiated
        let latest = nsError.userInfo[SPULatestAppcastItemFoundKey] as? SUAppcastItem
        let knownIncompatible = incompatible && latest?.versionString == reminder?.buildVersion
        if knownIncompatible { clearReminder() }
        updatePresentation(
            AppUpdatePolicy.noUpdate(userInitiated: userInitiated,
                                     incompatible: reminder == nil && incompatible,
                                     from: presentation),
            event: incompatible ? "app_update.incompatible" : "app_update.current"
        )
    }

    public func updater(
        _ updater: SPUUpdater,
        userDidMake choice: SPUUserUpdateChoice,
        forUpdate updateItem: SUAppcastItem,
        state: SPUUserUpdateState
    ) {
        let appChoice: AppUpdateUserChoice = switch choice {
        case .install:
            .install
        case .dismiss:
            .dismiss
        case .skip:
            .skip
        @unknown default:
            .dismiss
        }
        let current = presentation.availableVersion == nil
            ? AppUpdatePolicy.available(
                version: updateItem.displayVersionString,
                userInitiated: state.userInitiated,
                protectedWork: protectedWork
            )
            : presentation
        updatePresentation(
            AppUpdatePolicy.userChoice(appChoice, from: current, protectedWork: protectedWork),
            event: "app_update.user_choice_\(String(describing: appChoice))"
        )
    }

    public func updater(_ updater: SPUUpdater, willDownloadUpdate item: SUAppcastItem, with request: NSMutableURLRequest) {
        updatePresentation(
            AppUpdatePresentation(
                phase: .downloading,
                availableVersion: item.displayVersionString,
                isUserInitiated: presentation.isUserInitiated,
                message: "Загружаем обновление GRAF \(item.displayVersionString)…"
            ),
            event: "app_update.download_started"
        )
    }

    public func updater(_ updater: SPUUpdater, didDownloadUpdate item: SUAppcastItem) {
        let next = protectedWork.isProtected
            ? AppUpdatePolicy.available(
                version: item.displayVersionString,
                userInitiated: presentation.isUserInitiated,
                protectedWork: protectedWork
            )
            : AppUpdatePresentation(
                phase: .readyToInstall,
                availableVersion: item.displayVersionString,
                isUserInitiated: presentation.isUserInitiated,
                message: "Обновление GRAF \(item.displayVersionString) готово к установке."
            )
        updatePresentation(next, event: "app_update.download_finished")
    }

    public func updater(_ updater: SPUUpdater, failedToDownloadUpdate item: SUAppcastItem, error: Error) {
        updatePresentation(
            AppUpdatePolicy.failure(userInitiated: presentation.isUserInitiated, from: presentation,
                                    message: "Не удалось загрузить обновление. Повторите попытку."),
            event: "app_update.download_failed",
            error: error as NSError
        )
    }

    public func userDidCancelDownload(_ updater: SPUUpdater) {
        guard let version = presentation.availableVersion else { return }
        updatePresentation(
            AppUpdatePolicy.available(version: version, userInitiated: false, protectedWork: protectedWork),
            event: "app_update.download_cancelled"
        )
    }

    public func updater(_ updater: SPUUpdater, willInstallUpdate item: SUAppcastItem) {
        let next = AppUpdatePolicy.userChoice(
            .install,
            from: AppUpdatePolicy.available(
                version: item.displayVersionString,
                userInitiated: presentation.isUserInitiated,
                protectedWork: protectedWork
            ),
            protectedWork: protectedWork
        )
        updatePresentation(next, event: "app_update.install_requested")
    }

    public func updater(
        _ updater: SPUUpdater,
        shouldPostponeRelaunchForUpdate item: SUAppcastItem,
        untilInvokingBlock installHandler: @escaping () -> Void
    ) -> Bool {
        let postponed = relaunchGate.postponeIfNeeded(installHandler)
        guard postponed else { return false }

        updatePresentation(
            AppUpdatePolicy.available(
                version: item.displayVersionString,
                userInitiated: presentation.isUserInitiated,
                protectedWork: protectedWork
            ),
            event: "app_update.relaunch_deferred"
        )
        return true
    }

    public func updater(_ updater: SPUUpdater, didAbortWithError error: Error) {
        let nsError = error as NSError
        if nsError.domain == SUSparkleErrorDomain,
           nsError.code == SUError.noUpdateError.rawValue {
            return
        }
        updatePresentation(
            AppUpdatePolicy.failure(userInitiated: presentation.isUserInitiated, from: presentation),
            event: "app_update.failed",
            error: nsError
        )
    }
}

extension AppUpdateController: @preconcurrency SPUStandardUserDriverDelegate {
    public var supportsGentleScheduledUpdateReminders: Bool {
        true
    }

    public func standardUserDriverShouldHandleShowingScheduledUpdate(
        _ update: SUAppcastItem,
        andInImmediateFocus immediateFocus: Bool
    ) -> Bool {
        !protectedWork.isProtected
    }

    public func standardUserDriverWillHandleShowingUpdate(
        _ handleShowingUpdate: Bool,
        forUpdate update: SUAppcastItem,
        state: SPUUserUpdateState
    ) {
        suppressedScheduledOffer = !handleShowingUpdate && !state.userInitiated
        updatePresentation(
            AppUpdatePolicy.available(
                version: update.displayVersionString,
                userInitiated: state.userInitiated,
                protectedWork: protectedWork
            ),
            event: suppressedScheduledOffer
                ? "app_update.scheduled_offer_deferred"
                : "app_update.offer_presented"
        )
    }

    public func standardUserDriverDidReceiveUserAttention(forUpdate _: SUAppcastItem) {
        suppressedScheduledOffer = false
        log(event: "app_update.offer_received_attention")
    }
}
