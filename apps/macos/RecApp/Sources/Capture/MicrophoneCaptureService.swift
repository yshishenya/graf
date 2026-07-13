import Foundation
import TwoBrainRecShared
#if canImport(AVFoundation)
import AVFoundation
#endif
#if canImport(CoreMedia)
import CoreMedia
#endif
#if canImport(AudioToolbox)
import AudioToolbox
#endif

public protocol MicrophonePermissionAuthorizing: Sendable {
    func currentPermissionState() -> CapturePermissionState
    func requestPermission() async -> CapturePermissionState
}

public protocol RecordingMicrophoneInputProviding: Sendable {
    func availableInputs() -> [PhysicalAudioDevice]
    func defaultInputDevice() -> PhysicalAudioDevice?
    func inputDevice(id: String) -> PhysicalAudioDevice?
}

public enum RecordingMicrophoneSampleSourceError: Error {
    case selectionNotAccepted
    case runtimeUnavailable
    case runtimeStartFailed
}

public final class AppOwnedMicrophoneSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    public let inputDeviceId: String?

    private let bufferedSource: BufferedLocalRecordingSampleSource
    private let stateLock = NSLock()
    #if canImport(AVFoundation) && canImport(CoreMedia) && canImport(AudioToolbox)
    private let captureQueue = DispatchQueue(label: "com.2brain.rec.microphone-sample-source")
    private var session: AVCaptureSession?
    private var audioOutput: AVCaptureAudioDataOutput?
    private var captureDelegate: AppOwnedMicrophoneCaptureDelegate?
    #endif

    public init(
        bufferCapacity: Int = 48_000 * 30,
        inputDeviceId: String? = nil
    ) {
        let normalizedInputDeviceId = inputDeviceId?.trimmingCharacters(in: .whitespacesAndNewlines)
        self.inputDeviceId = normalizedInputDeviceId?.isEmpty == true ? nil : normalizedInputDeviceId
        self.bufferedSource = BufferedLocalRecordingSampleSource(
            capacity: bufferCapacity,
            channelCount: 1
        )
    }

    deinit {
        stop()
    }

    public var channelCount: Int {
        1
    }

    public func start() throws {
        #if canImport(AVFoundation) && canImport(CoreMedia) && canImport(AudioToolbox)
        try captureQueue.sync {
            try startCaptureSession()
        }
        #else
        throw RecordingMicrophoneSampleSourceError.runtimeUnavailable
        #endif
    }

    public func stop() {
        #if canImport(AVFoundation) && canImport(CoreMedia) && canImport(AudioToolbox)
        captureQueue.sync {
            stopCaptureSession()
        }
        #endif
    }

    public func stats() -> (frameCount: Int64, lastFrameAt: Date?) {
        bufferedSource.stats()
    }

    public func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        bufferedSource.readSamples(into: destination, capacity: capacity)
    }

    #if canImport(AVFoundation) && canImport(CoreMedia) && canImport(AudioToolbox)
    private func startCaptureSession() throws {
        stateLock.lock()
        let isAlreadyRunning = session != nil
        stateLock.unlock()
        guard !isAlreadyRunning else { return }

        guard let captureDevice = Self.captureDevice(id: inputDeviceId) else {
            throw RecordingMicrophoneSampleSourceError.runtimeUnavailable
        }

        let session = AVCaptureSession()
        let input: AVCaptureDeviceInput
        do {
            input = try AVCaptureDeviceInput(device: captureDevice)
        } catch {
            throw RecordingMicrophoneSampleSourceError.runtimeUnavailable
        }

        let output = AVCaptureAudioDataOutput()
        let captureDelegate = AppOwnedMicrophoneCaptureDelegate { [weak self] sampleBuffer in
            self?.append(sampleBuffer)
        }

        session.beginConfiguration()
        var committedConfiguration = false
        defer {
            if !committedConfiguration {
                session.commitConfiguration()
            }
        }

        guard session.canAddInput(input) else {
            throw RecordingMicrophoneSampleSourceError.runtimeStartFailed
        }
        session.addInput(input)

        guard session.canAddOutput(output) else {
            throw RecordingMicrophoneSampleSourceError.runtimeStartFailed
        }
        session.addOutput(output)
        output.setSampleBufferDelegate(captureDelegate, queue: captureQueue)

        session.commitConfiguration()
        committedConfiguration = true
        session.startRunning()
        guard session.isRunning else {
            output.setSampleBufferDelegate(nil, queue: nil)
            throw RecordingMicrophoneSampleSourceError.runtimeStartFailed
        }

        stateLock.lock()
        self.session = session
        self.audioOutput = output
        self.captureDelegate = captureDelegate
        stateLock.unlock()
    }

    private func stopCaptureSession() {
        stateLock.lock()
        let session = self.session
        let output = self.audioOutput
        self.session = nil
        self.audioOutput = nil
        self.captureDelegate = nil
        stateLock.unlock()

        output?.setSampleBufferDelegate(nil, queue: nil)
        session?.stopRunning()
    }

    private func append(_ sampleBuffer: CMSampleBuffer) {
        let samples = SystemAudioSampleExtractor.extractMonoFloatSamples(from: sampleBuffer)
        guard !samples.isEmpty else { return }
        bufferedSource.append(samples)
    }

    private static func captureDevice(id: String?) -> AVCaptureDevice? {
        let normalizedId = id?.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let normalizedId, !normalizedId.isEmpty else {
            return AVCaptureDevice.default(for: .audio)
        }
        if let discoveredDevice = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.microphone, .external],
            mediaType: .audio,
            position: .unspecified
        ).devices.first(where: { $0.uniqueID == normalizedId }) {
            return discoveredDevice
        }

        let defaultDevice = AVCaptureDevice.default(for: .audio)
        return defaultDevice?.uniqueID == normalizedId ? defaultDevice : nil
    }

    private final class AppOwnedMicrophoneCaptureDelegate: NSObject, AVCaptureAudioDataOutputSampleBufferDelegate {
        private let sampleHandler: (CMSampleBuffer) -> Void

        init(sampleHandler: @escaping (CMSampleBuffer) -> Void) {
            self.sampleHandler = sampleHandler
        }

        func captureOutput(
            _ output: AVCaptureOutput,
            didOutput sampleBuffer: CMSampleBuffer,
            from connection: AVCaptureConnection
        ) {
            sampleHandler(sampleBuffer)
        }
    }
    #endif
}

public struct AVFoundationMicrophonePermissionAuthorizer: MicrophonePermissionAuthorizing {
    public init() {}

    public func currentPermissionState() -> CapturePermissionState {
        #if canImport(AVFoundation)
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized:
            return .granted
        case .denied:
            return .denied
        case .restricted:
            return .restricted
        case .notDetermined:
            return .unknown
        @unknown default:
            return .unknown
        }
        #else
        return .unknown
        #endif
    }

    public func requestPermission() async -> CapturePermissionState {
        #if canImport(AVFoundation)
        let granted = await AVCaptureDevice.requestAccess(for: .audio)
        return granted ? .granted : currentPermissionState()
        #else
        return .unknown
        #endif
    }
}

public struct AVFoundationRecordingMicrophoneInputProvider: RecordingMicrophoneInputProviding {
    public init() {}

    public func availableInputs() -> [PhysicalAudioDevice] {
        #if canImport(AVFoundation)
        return AVCaptureDevice.DiscoverySession(
            deviceTypes: [.microphone, .external],
            mediaType: .audio,
            position: .unspecified
        ).devices.map(Self.physicalDevice)
        #else
        return []
        #endif
    }

    public func defaultInputDevice() -> PhysicalAudioDevice? {
        #if canImport(AVFoundation)
        return AVCaptureDevice.default(for: .audio).map(Self.physicalDevice)
        #else
        return nil
        #endif
    }

    public func inputDevice(id: String) -> PhysicalAudioDevice? {
        availableInputs().first { $0.id == id }
    }

    #if canImport(AVFoundation)
    private static func physicalDevice(from device: AVCaptureDevice) -> PhysicalAudioDevice {
        PhysicalAudioDevice(
            id: device.uniqueID,
            displayName: device.localizedName,
            direction: .input,
            deviceClass: deviceClass(id: device.uniqueID, name: device.localizedName),
            availabilityState: .available
        )
    }
    #endif

    private static func deviceClass(id: String, name: String) -> PhysicalDeviceClass {
        let normalized = "\(id) \(name)".lowercased()
        if normalized.contains("virtual") ||
            normalized.contains("blackhole") ||
            normalized.contains("soundflower") {
            return .otherVirtual
        }
        if normalized.contains("airpods") {
            return .airpodsClass
        }
        if normalized.contains("bluetooth") {
            return .bluetooth
        }
        if normalized.contains("usb") {
            return .usb
        }
        if normalized.contains("built-in") ||
            normalized.contains("built in") ||
            normalized.contains("macbook") ||
            normalized.contains("imac") {
            return .builtIn
        }
        return .unknown
    }
}

public final class MicrophoneCaptureService: Sendable {
    public typealias Clock = @Sendable () -> Date

    private let authorizer: MicrophonePermissionAuthorizing
    private let inputProvider: RecordingMicrophoneInputProviding
    private let clock: Clock
    private let inputPolicy: RecordingMicrophoneInputPolicy

    public init(
        authorizer: MicrophonePermissionAuthorizing = AVFoundationMicrophonePermissionAuthorizer(),
        inputProvider: RecordingMicrophoneInputProviding = AVFoundationRecordingMicrophoneInputProvider(),
        clock: @escaping Clock = Date.init,
        inputPolicy: RecordingMicrophoneInputPolicy = RecordingMicrophoneInputPolicy()
    ) {
        self.authorizer = authorizer
        self.inputProvider = inputProvider
        self.clock = clock
        self.inputPolicy = inputPolicy
    }

    public func preflight(
        sessionId: String,
        inputDeviceId: String? = nil,
        inputDisplayName: String = "Default Microphone"
    ) -> MicrophoneCaptureSession {
        MicrophoneCaptureSession(
            sessionId: sessionId,
            permissionState: authorizer.currentPermissionState(),
            inputDeviceId: inputDeviceId,
            inputDisplayName: inputDisplayName
        )
    }

    public func requestPermissionAndPreflight(
        sessionId: String,
        inputDeviceId: String? = nil,
        inputDisplayName: String = "Default Microphone"
    ) async -> MicrophoneCaptureSession {
        let state = await authorizer.requestPermission()
        return MicrophoneCaptureSession(
            sessionId: sessionId,
            permissionState: state,
            inputDeviceId: inputDeviceId,
            inputDisplayName: inputDisplayName
        )
    }

    public func availableRecordingMicrophoneInputs() -> [PhysicalAudioDevice] {
        inputProvider.availableInputs()
    }

    public func makeAppOwnedMicrophoneSampleSource(
        for selection: RecordingMicrophoneSelection
    ) throws -> AppOwnedMicrophoneSampleSource {
        guard selection.isAccepted else {
            throw RecordingMicrophoneSampleSourceError.selectionNotAccepted
        }
        return AppOwnedMicrophoneSampleSource(inputDeviceId: selection.inputDeviceId)
    }

    public func startAppOwnedMicrophoneSampleSource(
        for selection: RecordingMicrophoneSelection
    ) throws -> AppOwnedMicrophoneSampleSource {
        let source = try makeAppOwnedMicrophoneSampleSource(for: selection)
        try source.start()
        return source
    }

    public func blockedMicrophoneStreamEvidence(
        sessionId: String,
        selection: RecordingMicrophoneSelection,
        permissionState: CapturePermissionState,
        failureReason: LocalRecordingFailureReason
    ) -> (stream: AppOwnedMicrophoneStreamSession, health: MicrophoneStreamHealth) {
        let stream = AppOwnedMicrophoneStreamSession(
            sessionId: sessionId,
            selection: selection,
            permissionState: permissionState,
            streamKind: .appOwnedSampleSource,
            frameCount: 0,
            failureReason: failureReason
        )
        let health = MicrophoneStreamHealth(
            gateStatus: .blocked,
            failureReason: failureReason,
            framesObserved: false,
            timingConfidence: .missing,
            silenceStatus: .unknown,
            cleanupReadiness: .blocked,
            evidenceCodes: [
                permissionState.rawValue,
                failureReason.rawValue,
                FutureProcessingReadiness.blocked.rawValue
            ]
        )
        return (stream, health)
    }

    public func resolveRecordingMicrophoneSelection(
        selectedInputDeviceId: String?
    ) -> RecordingMicrophoneSelection {
        let selectedInputDeviceId = selectedInputDeviceId?.trimmingCharacters(in: .whitespacesAndNewlines)
        if let selectedInputDeviceId, !selectedInputDeviceId.isEmpty {
            guard let selected = inputProvider.inputDevice(id: selectedInputDeviceId) else {
                return RecordingMicrophoneSelection(
                    selectionId: "recording-microphone-user-selected-\(selectedInputDeviceId)",
                    mode: .userSelected,
                    inputDeviceId: selectedInputDeviceId,
                    selectionResult: .unavailable,
                    rejectionReason: .deviceUnavailable,
                    resolvedAt: clock()
                )
            }
            return selection(for: selected, mode: .userSelected)
        }

        guard let defaultInput = inputProvider.defaultInputDevice() else {
            return RecordingMicrophoneSelection(
                selectionId: "recording-microphone-macos-default-missing",
                mode: .macOSDefaultFallback,
                selectionResult: .unavailable,
                rejectionReason: .deviceUnavailable,
                resolvedAt: clock()
            )
        }
        return selection(for: defaultInput, mode: .macOSDefaultFallback)
    }

    private func selection(
        for device: PhysicalAudioDevice,
        mode: RecordingMicrophoneSelectionMode
    ) -> RecordingMicrophoneSelection {
        let workingKind = inputPolicy.workingDeviceKind(for: device)
        if device.direction != .input {
            return selection(
                for: device,
                mode: mode,
                workingKind: workingKind,
                result: .rejected,
                rejectionReason: .inputIdentityUnproven
            )
        }

        if device.availabilityState != .available {
            return selection(
                for: device,
                mode: mode,
                workingKind: workingKind,
                result: .unavailable,
                rejectionReason: .deviceUnavailable
            )
        }

        if let rejectionReason = inputPolicy.rejectionReason(for: workingKind) {
            return selection(
                for: device,
                mode: mode,
                workingKind: workingKind,
                result: .rejected,
                rejectionReason: rejectionReason
            )
        }

        return selection(
            for: device,
            mode: mode,
            workingKind: workingKind,
            result: .accepted,
            rejectionReason: nil
        )
    }

    private func selection(
        for device: PhysicalAudioDevice,
        mode: RecordingMicrophoneSelectionMode,
        workingKind: PhysicalWorkingDeviceKind,
        result: RecordingMicrophoneSelectionResult,
        rejectionReason: RecordingMicrophoneSelectionRejectionReason?
    ) -> RecordingMicrophoneSelection {
        RecordingMicrophoneSelection(
            selectionId: "recording-microphone-\(mode.rawValue)-\(device.id)",
            mode: mode,
            inputDeviceId: device.id,
            inputDisplayName: device.displayName,
            deviceClass: device.deviceClass,
            workingDeviceKind: workingKind,
            selectionResult: result,
            rejectionReason: rejectionReason,
            resolvedAt: clock()
        )
    }

}
