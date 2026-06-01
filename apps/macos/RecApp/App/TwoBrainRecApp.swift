import CoreAudio
import SwiftUI
import TwoBrainRecAppCore
import TwoBrainRecShared

@main
struct TwoBrainRecApp: App {
    @State private var snapshot = LocalAudioSnapshot.current()
    @State private var isChecking = false

    var body: some Scene {
        WindowGroup("2brain Rec") {
            ContentView(
                snapshot: snapshot,
                isChecking: isChecking,
                refresh: {
                    let updated = LocalAudioSnapshot.current()
                    AppLog.write(event: "refresh", snapshot: updated)
                    snapshot = updated
                },
                runCheck: {
                    isChecking = true
                    let checked = LocalAudioSnapshot.runReadinessCheck()
                    AppLog.write(event: "readiness_check", snapshot: checked)
                    snapshot = checked
                    isChecking = false
                }
            )
            .frame(minWidth: 720, minHeight: 620)
        }
        .windowResizability(.contentMinSize)
    }
}

private struct ContentView: View {
    @StateObject private var passthroughCoordinator = ExperimentalPassthroughCoordinator(
        logger: AppLog.writeRaw
    )

    let snapshot: LocalAudioSnapshot
    let isChecking: Bool
    let refresh: () -> Void
    let runCheck: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    DriverSetupView(
                        driverState: snapshot.driverState,
                        microphoneState: snapshot.virtualMicrophoneState,
                        speakerState: snapshot.virtualSpeakerState,
                        onInstall: refresh,
                        onRepair: refresh
                    )
                    RouteVerificationView(
                        snapshot: snapshot.routeVerification,
                        canVerify: true,
                        isVerifying: isChecking,
                        onVerify: runCheck
                    )
                    AudioHealthView(state: snapshot.healthState)
                    DiagnosticLogView(
                        path: AppLog.fileURL.path,
                        lastEvent: snapshot.lastEventSummary
                    )
                }
                .padding(18)
            }
        }
        .onAppear {
            passthroughCoordinator.recordLaunchState()
            AppLog.write(event: "app_opened", snapshot: snapshot)
        }
    }

    private var header: some View {
        HStack(spacing: 12) {
            Image(systemName: "waveform.badge.mic")
                .font(.system(size: 28, weight: .semibold))
            VStack(alignment: .leading, spacing: 3) {
                Text("2brain Rec")
                    .font(.title2)
                    .fontWeight(.semibold)
                Text(snapshot.summary)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button(action: refresh) {
                Image(systemName: "arrow.clockwise")
            }
            .help("Refresh audio device status")
        }
        .padding(18)
    }
}

fileprivate struct LocalAudioSnapshot {
    let driverState: DriverInstallationState
    let virtualMicrophoneState: VirtualDeviceAvailabilityState
    let virtualSpeakerState: VirtualDeviceAvailabilityState
    let routeVerification: RouteVerificationSnapshot?
    let healthState: AudioHealthState
    let defaultInputName: String?
    let defaultOutputName: String?
    let defaultSystemOutputName: String?
    let coreAudioDeviceSummary: String
    let lastEventSummary: String

    var summary: String {
        if routeVerification?.canShowReady == true {
            return "Ready for audio routing"
        }
        if virtualMicrophoneState == .available && virtualSpeakerState == .available {
            return "Installed, but not ready for calls yet"
        }
        if driverState == .installed {
            return "Driver bundle is installed; Core Audio may need a refresh"
        }
        return "Driver is not installed on this Mac"
    }

    static func current() -> LocalAudioSnapshot {
        makeSnapshot(
            system: CoreAudioSystemSnapshot.current(),
            routeVerification: nil,
            lastEventSummary: "Status refreshed"
        )
    }

    static func runReadinessCheck() -> LocalAudioSnapshot {
        let system = CoreAudioSystemSnapshot.current()
        return makeSnapshot(
            system: system,
            routeVerification: routeSnapshot(system: system, checked: true),
            lastEventSummary: readinessSummary(system: system)
        )
    }

    private static func makeSnapshot(
        system: CoreAudioSystemSnapshot,
        routeVerification: RouteVerificationSnapshot?,
        lastEventSummary: String
    ) -> LocalAudioSnapshot {
        let hasMic = system.hasVirtualMicrophone
        let hasSpeaker = system.hasVirtualSpeaker
        let driverExists = FileManager.default.fileExists(
            atPath: "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver"
        )

        let micState: VirtualDeviceAvailabilityState = hasMic ? .available : (driverExists ? .requiresRestart : .missing)
        let speakerState: VirtualDeviceAvailabilityState = hasSpeaker ? .available : (driverExists ? .requiresRestart : .missing)
        let driverState: DriverInstallationState = driverExists ? .installed : .notInstalled
        let routeSnapshot = routeVerification ?? routeSnapshot(system: system, checked: false)
        let recoveryActions = recoveryActions(system: system, routeSnapshot: routeSnapshot)

        let health = AudioHealthState(
            driverState: driverState,
            virtualMicState: micState,
            virtualSpeakerState: speakerState,
            microphonePermission: .unknown,
            outputPermission: .unknown,
            physicalInput: system.defaultInput?.healthSummary(direction: .input),
            physicalOutput: system.defaultOutput?.healthSummary(direction: .output),
            routeVerification: routeSnapshot,
            passthroughStatus: .unknown,
            continuityStatus: hasMic && hasSpeaker
                ? "Virtual devices are published. Real audio passthrough is not verified yet."
                : "Waiting for virtual devices",
            bufferRisk: .healthy,
            recoveryActions: recoveryActions
        )

        return LocalAudioSnapshot(
            driverState: driverState,
            virtualMicrophoneState: micState,
            virtualSpeakerState: speakerState,
            routeVerification: routeSnapshot,
            healthState: health,
            defaultInputName: system.defaultInput?.name,
            defaultOutputName: system.defaultOutput?.name,
            defaultSystemOutputName: system.defaultSystemOutput?.name,
            coreAudioDeviceSummary: system.deviceLogSummary,
            lastEventSummary: lastEventSummary
        )
    }

    private static func routeSnapshot(
        system: CoreAudioSystemSnapshot,
        checked: Bool
    ) -> RouteVerificationSnapshot {
        let now = Date()
        let micResult = micRouteResult(system: system, checked: checked)
        let speakerResult = speakerRouteResult(system: system, checked: checked)
        return RouteVerificationSnapshot(
            mic: RouteVerification(
                id: "local-mic-publication",
                path: .micToVirtualInput,
                validationType: .syntheticSignal,
                target: "2brain Rec Microphone",
                status: micResult.status,
                failureReason: micResult.reason,
                recoveryAction: micResult.action,
                startedAt: now,
                finishedAt: now
            ),
            speaker: RouteVerification(
                id: "local-speaker-publication",
                path: .remoteOutputToVirtualSpeaker,
                validationType: .syntheticSignal,
                target: "2brain Rec Speaker",
                status: speakerResult.status,
                failureReason: speakerResult.reason,
                recoveryAction: speakerResult.action,
                startedAt: now,
                finishedAt: now
            )
        )
    }

    private static func micRouteResult(
        system: CoreAudioSystemSnapshot,
        checked: Bool
    ) -> (status: RouteVerificationStatus, reason: String?, action: String?) {
        guard system.hasVirtualMicrophone else {
            return (.failed, "virtual_microphone_not_visible", "install_or_repair_driver")
        }
        guard let input = system.defaultInput, input.inputChannels > 0, !input.isTwoBrainVirtual else {
            return checked
                ? (.failed, "physical_microphone_not_selected", "select_physical_microphone")
                : (.notStarted, nil, "run_route_verification")
        }
        return checked
            ? (.stale, "live_passthrough_evidence_missing", "run_controlled_live_passthrough_validation")
            : (.notStarted, nil, "run_route_verification")
    }

    private static func speakerRouteResult(
        system: CoreAudioSystemSnapshot,
        checked: Bool
    ) -> (status: RouteVerificationStatus, reason: String?, action: String?) {
        guard system.hasVirtualSpeaker else {
            return (.failed, "virtual_speaker_not_visible", "install_or_repair_driver")
        }
        guard let output = system.defaultOutput, output.outputChannels > 0, !output.isTwoBrainVirtual else {
            return checked
                ? (.failed, "physical_speaker_not_selected", "select_physical_speaker")
                : (.notStarted, nil, "run_route_verification")
        }
        return checked
            ? (.stale, "live_passthrough_evidence_missing", "run_controlled_live_passthrough_validation")
            : (.notStarted, nil, "run_route_verification")
    }

    private static func recoveryActions(
        system: CoreAudioSystemSnapshot,
        routeSnapshot: RouteVerificationSnapshot
    ) -> [String] {
        var actions: [String] = []
        if !system.hasVirtualMicrophone || !system.hasVirtualSpeaker {
            actions.append("Install or repair the audio driver")
        }
        if system.defaultInput?.isTwoBrainVirtual == true {
            actions.append("Set macOS input back to a physical microphone while testing")
        }
        if system.defaultOutput?.isTwoBrainVirtual == true {
            actions.append("Set macOS output back to physical speakers")
        }
        if let output = system.defaultOutput,
           let systemOutput = system.defaultSystemOutput,
           output.id != systemOutput.id {
            actions.append("Default output and system output are different: \(output.name) / \(systemOutput.name)")
        }
        if routeSnapshot.mic.status != .passed || routeSnapshot.speaker.status != .passed {
            actions.append("Run the readiness check again")
        }
        return actions
    }

    private static func readinessSummary(system: CoreAudioSystemSnapshot) -> String {
        if !system.hasVirtualMicrophone || !system.hasVirtualSpeaker {
            return "Check failed: virtual devices are missing"
        }
        if system.defaultOutput?.isTwoBrainVirtual == true {
            return "Check failed: macOS output is set to the virtual speaker"
        }
        return "Check complete: devices are visible; live passthrough evidence is still required"
    }

    var logDescription: String {
        [
            "summary=\(summary)",
            "driver=\(driverState.rawValue)",
            "virtualMic=\(virtualMicrophoneState.rawValue)",
            "virtualSpeaker=\(virtualSpeakerState.rawValue)",
            "defaultInput=\(defaultInputName ?? "none")",
            "defaultOutput=\(defaultOutputName ?? "none")",
            "defaultSystemOutput=\(defaultSystemOutputName ?? "none")",
            "coreAudioDevices=\(coreAudioDeviceSummary)",
            "micRoute=\(routeVerification?.mic.status.rawValue ?? "none")",
            "micReason=\(routeVerification?.mic.failureReason ?? "none")",
            "speakerRoute=\(routeVerification?.speaker.status.rawValue ?? "none")",
            "speakerReason=\(routeVerification?.speaker.failureReason ?? "none")",
            "passthrough=\(healthState.passthroughStatus.rawValue)"
        ].joined(separator: " ")
    }
}

private struct CoreAudioDeviceInfo: Equatable {
    let id: AudioDeviceID
    let name: String
    let inputChannels: Int
    let outputChannels: Int

    var isTwoBrainVirtual: Bool {
        name.localizedCaseInsensitiveContains("2brain Rec")
    }

    func healthSummary(direction: AudioDirection) -> HealthPhysicalDeviceSummary {
        HealthPhysicalDeviceSummary(
            id: String(id),
            displayName: name,
            direction: direction,
            className: isTwoBrainVirtual ? .unknown : .builtIn,
            availabilityState: .available
        )
    }
}

private struct CoreAudioSystemSnapshot {
    let devices: [CoreAudioDeviceInfo]
    let defaultInputID: AudioDeviceID?
    let defaultOutputID: AudioDeviceID?
    let defaultSystemOutputID: AudioDeviceID?

    var hasVirtualMicrophone: Bool {
        devices.contains { $0.name == "2brain Rec Microphone" }
    }

    var hasVirtualSpeaker: Bool {
        devices.contains { $0.name == "2brain Rec Speaker" }
    }

    var deviceLogSummary: String {
        devices
            .map { "\($0.name)[in=\($0.inputChannels),out=\($0.outputChannels)]" }
            .joined(separator: "|")
    }

    var defaultInput: CoreAudioDeviceInfo? {
        device(defaultInputID)
    }

    var defaultOutput: CoreAudioDeviceInfo? {
        device(defaultOutputID)
    }

    var defaultSystemOutput: CoreAudioDeviceInfo? {
        device(defaultSystemOutputID)
    }

    var bridgeInputDevice: CoreAudioDeviceInfo? {
        if let defaultInput, defaultInput.inputChannels > 0, !defaultInput.isTwoBrainVirtual {
            return defaultInput
        }
        return devices.first { $0.inputChannels > 0 && !$0.isTwoBrainVirtual }
    }

    var bridgeOutputDevice: CoreAudioDeviceInfo? {
        if let defaultOutput, defaultOutput.outputChannels > 0, !defaultOutput.isTwoBrainVirtual {
            return defaultOutput
        }
        if let defaultSystemOutput, defaultSystemOutput.outputChannels > 0, !defaultSystemOutput.isTwoBrainVirtual {
            return defaultSystemOutput
        }
        return devices.first { $0.outputChannels > 0 && !$0.isTwoBrainVirtual }
    }

    static func current() -> CoreAudioSystemSnapshot {
        let deviceIDs = readDeviceIDs()
        let devices = deviceIDs.compactMap { id -> CoreAudioDeviceInfo? in
            guard let name = deviceName(id) else {
                return nil
            }
            return CoreAudioDeviceInfo(
                id: id,
                name: name,
                inputChannels: channelCount(id, scope: kAudioDevicePropertyScopeInput),
                outputChannels: channelCount(id, scope: kAudioDevicePropertyScopeOutput)
            )
        }

        return CoreAudioSystemSnapshot(
            devices: devices,
            defaultInputID: defaultDeviceID(kAudioHardwarePropertyDefaultInputDevice),
            defaultOutputID: defaultDeviceID(kAudioHardwarePropertyDefaultOutputDevice),
            defaultSystemOutputID: defaultDeviceID(kAudioHardwarePropertyDefaultSystemOutputDevice)
        )
    }

    private func device(_ id: AudioDeviceID?) -> CoreAudioDeviceInfo? {
        guard let id else {
            return nil
        }
        return devices.first { $0.id == id }
    }

    private static func readDeviceIDs() -> [AudioDeviceID] {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        var dataSize: UInt32 = 0
        let sizeStatus = AudioObjectGetPropertyDataSize(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            0,
            nil,
            &dataSize
        )
        guard sizeStatus == noErr, dataSize > 0 else {
            return []
        }

        let count = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
        var deviceIDs = [AudioDeviceID](repeating: 0, count: count)
        let dataStatus = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            0,
            nil,
            &dataSize,
            &deviceIDs
        )
        guard dataStatus == noErr else {
            return []
        }

        return deviceIDs
    }

    private static func defaultDeviceID(_ selector: AudioObjectPropertySelector) -> AudioDeviceID? {
        var address = AudioObjectPropertyAddress(
            mSelector: selector,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var deviceID = AudioDeviceID(kAudioObjectUnknown)
        var dataSize = UInt32(MemoryLayout<AudioDeviceID>.size)
        let status = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            0,
            nil,
            &dataSize,
            &deviceID
        )
        guard status == noErr, deviceID != kAudioObjectUnknown else {
            return nil
        }
        return deviceID
    }

    private static func deviceName(_ deviceID: AudioDeviceID) -> String? {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioObjectPropertyName,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var name: CFString = "" as CFString
        var dataSize = UInt32(MemoryLayout<CFString>.size)
        let status = withUnsafeMutableBytes(of: &name) { rawName in
            AudioObjectGetPropertyData(
                deviceID,
                &address,
                0,
                nil,
                &dataSize,
                rawName.baseAddress!
            )
        }
        guard status == noErr else {
            return nil
        }
        return name as String
    }

    private static func channelCount(_ deviceID: AudioDeviceID, scope: AudioObjectPropertyScope) -> Int {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyStreamConfiguration,
            mScope: scope,
            mElement: kAudioObjectPropertyElementMain
        )
        var dataSize: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(deviceID, &address, 0, nil, &dataSize) == noErr,
              dataSize > 0 else {
            return 0
        }

        let raw = UnsafeMutableRawPointer.allocate(
            byteCount: Int(dataSize),
            alignment: MemoryLayout<AudioBufferList>.alignment
        )
        defer { raw.deallocate() }

        guard AudioObjectGetPropertyData(deviceID, &address, 0, nil, &dataSize, raw) == noErr else {
            return 0
        }

        let buffers = UnsafeMutableAudioBufferListPointer(
            raw.bindMemory(to: AudioBufferList.self, capacity: 1)
        )
        return buffers.reduce(0) { $0 + Int($1.mNumberChannels) }
    }
}

private struct DiagnosticLogView: View {
    let path: String
    let lastEvent: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "doc.text.magnifyingglass")
                    .foregroundStyle(.blue)
                Text("Diagnostics")
                    .font(.callout)
                    .fontWeight(.semibold)
            }
            row(label: "Last event", detail: lastEvent)
            row(label: "Log file", detail: path)
        }
        .padding(16)
    }

    private func row(label: String, detail: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(width: 90, alignment: .leading)
            Text(detail)
                .font(.body)
                .lineLimit(2)
                .minimumScaleFactor(0.85)
            Spacer()
        }
        .accessibilityElement(children: .combine)
    }
}

private enum AppLog {
    static let fileURL: URL = {
        let base = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/2brain Rec", isDirectory: true)
        return base.appendingPathComponent("2brain-rec.log")
    }()

    static func write(event: String, snapshot: LocalAudioSnapshot) {
        let line = "\(timestamp()) event=\(event) \(snapshot.logDescription)\n"
        writeLine(line)
    }

    static func writeRaw(event: String, detail: String) {
        let sanitized = detail
            .replacingOccurrences(of: "\n", with: " ")
            .replacingOccurrences(of: "\r", with: " ")
        writeLine("\(timestamp()) event=\(event) detail=\(sanitized)\n")
    }

    private static func writeLine(_ line: String) {
        do {
            try FileManager.default.createDirectory(
                at: fileURL.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            if FileManager.default.fileExists(atPath: fileURL.path),
               let handle = try? FileHandle(forWritingTo: fileURL) {
                try handle.seekToEnd()
                if let data = line.data(using: .utf8) {
                    try handle.write(contentsOf: data)
                }
                try handle.close()
            } else {
                try line.write(to: fileURL, atomically: true, encoding: .utf8)
            }
        } catch {
            print("2brain Rec log write failed: \(error)")
        }
    }

    private static func timestamp() -> String {
        ISO8601DateFormatter().string(from: Date())
    }
}
