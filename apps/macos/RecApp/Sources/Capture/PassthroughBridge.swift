import AudioToolbox
import CoreAudio
import Foundation
import TwoBrainRecShared

public enum PassthroughBridgeError: Error {
    case noPhysicalMicFound
    case noPhysicalSpeakerFound
    case selfRoutingDeviceSelected(String)
    case audioUnitSetupFailed(OSStatus)
    case sharedMemoryUnavailable
}

private func bridgeLog(_ msg: String) {
    let fd = open("/tmp/2brain-rec-bridge.log", O_CREAT | O_WRONLY | O_APPEND, 0644)
    guard fd >= 0 else { return }
    fchmod(fd, 0o644)
    let ts = Date().timeIntervalSince1970
    let line = "[\(String(format: "%.3f", ts))] \(msg)\n"
    _ = line.withCString { write(fd, $0, strlen($0)) }
    close(fd)
}

private func peak(_ samples: [Float], count: Int) -> Float {
    var value: Float = 0
    for index in 0..<min(samples.count, count) {
        value = max(value, abs(samples[index]))
    }
    return value
}

private func stretchStereo(_ source: [Float], sourceSampleCount: Int, into destination: inout [Float], destinationFrameCount: Int) {
    let sourceFrameCount = max(0, sourceSampleCount / 2)
    guard sourceFrameCount > 0, destinationFrameCount > 0 else { return }
    if sourceFrameCount == 1 {
        for frame in 0..<destinationFrameCount {
            destination[frame * 2] = source[0]
            destination[frame * 2 + 1] = source[1]
        }
        return
    }

    let scale = Double(sourceFrameCount - 1) / Double(max(destinationFrameCount - 1, 1))
    for frame in 0..<destinationFrameCount {
        let position = Double(frame) * scale
        let leftIndex = Int(position)
        let rightIndex = min(leftIndex + 1, sourceFrameCount - 1)
        let fraction = Float(position - Double(leftIndex))
        let leftBase = leftIndex * 2
        let rightBase = rightIndex * 2
        destination[frame * 2] = source[leftBase] + (source[rightBase] - source[leftBase]) * fraction
        destination[frame * 2 + 1] = source[leftBase + 1] + (source[rightBase + 1] - source[leftBase + 1]) * fraction
    }
}

public final class PassthroughBridge {
    fileprivate let shm: SharedAudioMemory
    fileprivate var micAU: AudioComponentInstance?
    fileprivate var speakerAU: AudioComponentInstance?
    fileprivate var micCallbackCount: UInt64 = 0
    fileprivate var speakerCallbackCount: UInt64 = 0
    fileprivate var micNonZeroCount: UInt64 = 0
    fileprivate var speakerNonZeroCount: UInt64 = 0
    private var isRunning = false
    private var lastHeartbeatAt: Date?
    private let selectedPhysicalInputId: String?
    private let selectedPhysicalOutputId: String?
    private let queue = DispatchQueue(label: "com.2brainrec.passthrough", qos: .userInitiated)

    public init(
        selectedPhysicalInputId: String? = nil,
        selectedPhysicalOutputId: String? = nil
    ) throws {
        guard let shm = SharedAudioMemory() else {
            bridgeLog("init: sharedMemoryUnavailable")
            throw PassthroughBridgeError.sharedMemoryUnavailable
        }
        self.shm = shm
        self.selectedPhysicalInputId = selectedPhysicalInputId
        self.selectedPhysicalOutputId = selectedPhysicalOutputId
        bridgeLog("init: OK")
    }

    deinit {
        bridgeLog("deinit")
        stop()
    }

    public func start() throws {
        bridgeLog("start: called")
        try queue.sync {
            guard !isRunning else { bridgeLog("start: already running"); return }
            do {
                try setupMicCapture()
                bridgeLog("start: mic AU ready")
                try setupSpeakerPlayback()
                bridgeLog("start: speaker AU ready")

                var err = AudioOutputUnitStart(micAU!)
                guard err == noErr else {
                    bridgeLog("start: AudioOutputUnitStart(mic) failed: \(err)")
                    cleanupAudioUnits()
                    throw PassthroughBridgeError.audioUnitSetupFailed(err)
                }
                bridgeLog("start: mic AU started")

                err = AudioOutputUnitStart(speakerAU!)
                guard err == noErr else {
                    bridgeLog("start: AudioOutputUnitStart(speaker) failed: \(err)")
                    AudioOutputUnitStop(micAU!)
                    cleanupAudioUnits()
                    throw PassthroughBridgeError.audioUnitSetupFailed(err)
                }
                bridgeLog("start: speaker AU started")

                isRunning = true
                lastHeartbeatAt = Date()
                shm.writeAppHeartbeat(at: lastHeartbeatAt!)
                bridgeLog("start: OK, experimental bridge started")
            } catch {
                bridgeLog("start: error: \(error)")
                cleanupAudioUnits()
                isRunning = false
                throw error
            }
        }
    }

    public func stop() {
        bridgeLog("stop: called")
        queue.sync {
            guard isRunning else { bridgeLog("stop: not running"); return }
            if let au = micAU { AudioOutputUnitStop(au); bridgeLog("stop: mic stopped") }
            if let au = speakerAU { AudioOutputUnitStop(au); bridgeLog("stop: speaker stopped") }
            cleanupAudioUnits()
            isRunning = false
            lastHeartbeatAt = nil
            shm.clearAppHeartbeat()
            bridgeLog("stop: OK")
        }
    }

    public var passthroughActive: Bool { isRunning }

    public func appIOHealth(now: Date = Date()) -> PrivateAppIOHealth {
        AppIOHealthPolicy().evaluate(lastHeartbeatAt: lastHeartbeatAt, now: now)
    }

    public func livePassthroughStatusDuringServiceOutage(
        backendAvailable: Bool,
        uploadAvailable: Bool,
        transcriptionAvailable: Bool,
        now: Date = Date()
    ) -> LivePassthroughStatus {
        let health = appIOHealth(now: now)
        guard isRunning else { return .inactive }
        guard health.state == .connected else { return .degraded }
        return .active
    }

    @discardableResult
    public func stopIfHeartbeatLost(now: Date = Date()) -> LivePassthroughStatus {
        let health = appIOHealth(now: now)
        guard health.state == .heartbeatLost else {
            return isRunning ? .active : .inactive
        }
        stop()
        return .degraded
    }

    fileprivate func recordAppIOHeartbeat(at date: Date = Date()) {
        lastHeartbeatAt = date
        shm.writeAppHeartbeat(at: date)
    }

    private func cleanupAudioUnits() {
        if let au = micAU { AudioComponentInstanceDispose(au); micAU = nil; bridgeLog("cleanup: mic disposed") }
        if let au = speakerAU { AudioComponentInstanceDispose(au); speakerAU = nil; bridgeLog("cleanup: speaker disposed") }
    }

    private func deviceName(_ id: AudioDeviceID) -> String? {
        var nameAddr = AudioObjectPropertyAddress(
            mSelector: kAudioObjectPropertyName,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var name: CFString = "" as CFString
        var size = UInt32(MemoryLayout<CFString>.size)
        let status = withUnsafeMutableBytes(of: &name) { rawName in
            AudioObjectGetPropertyData(id, &nameAddr, 0, nil, &size, rawName.baseAddress!)
        }
        guard status == noErr else { return nil }
        return name as String
    }

    private func hasStreams(_ id: AudioDeviceID, scope: AudioObjectPropertyScope) -> Bool {
        var streamAddr = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyStreamConfiguration,
            mScope: scope,
            mElement: kAudioObjectPropertyElementMain
        )
        var streamSize: UInt32 = 0
        return AudioObjectGetPropertyDataSize(id, &streamAddr, 0, nil, &streamSize) == noErr && streamSize > 0
    }

    private func allDeviceIDs() -> [AudioDeviceID] {
        var addr = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var dataSize: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &dataSize) == noErr,
              dataSize > 0 else { bridgeLog("allDeviceIDs: cannot get device count"); return [] }
        let count = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
        var ids = [AudioDeviceID](repeating: 0, count: count)
        guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &dataSize, &ids) == noErr
        else { bridgeLog("allDeviceIDs: cannot get device list"); return [] }
        return ids
    }

    private func selectedDeviceID(_ selectedId: String?, scope: AudioObjectPropertyScope) throws -> AudioDeviceID? {
        guard let selectedId, !selectedId.isEmpty else { return nil }
        let ids = allDeviceIDs()
        let numericId = UInt32(selectedId)
        for id in ids where numericId == id || deviceName(id) == selectedId {
            guard let devName = deviceName(id) else { continue }
            if devName.localizedCaseInsensitiveContains("2brain Rec") {
                throw PassthroughBridgeError.selfRoutingDeviceSelected(devName)
            }
            guard hasStreams(id, scope: scope) else { continue }
            bridgeLog("selectedDeviceID: FOUND \(id) '\(devName)' scope=\(scope)")
            return id
        }
        bridgeLog("selectedDeviceID: selected device not found id=\(selectedId) scope=\(scope)")
        return nil
    }

    private func findPhysicalDevice(scope: AudioObjectPropertyScope, selectedId: String?) throws -> AudioDeviceID? {
        if let selected = try selectedDeviceID(selectedId, scope: scope) {
            return selected
        }

        let isInput = scope == kAudioDevicePropertyScopeInput
        let keywords: [String] = isInput
            ? ["Microphone", "Mic", "Input", "Built-in Microphone", "Микрофон"]
            : ["Speaker", "Output", "Built-in Output", "Динамики"]

        for id in allDeviceIDs() {
            guard let devName = deviceName(id) else { continue }

            if devName.contains("2brain Rec") { continue }

            let nameMatches = keywords.contains { devName.localizedCaseInsensitiveContains($0) }
            if !nameMatches { continue }

            guard hasStreams(id, scope: scope) else { continue }

            bridgeLog("findPhysicalDevice: FOUND \(id) '\(devName)' scope=\(scope)")
            return id
        }
        bridgeLog("findPhysicalDevice: no suitable device found")
        return nil
    }

    private func setupMicCapture() throws {
        guard var micID = try findPhysicalDevice(scope: kAudioDevicePropertyScopeInput, selectedId: selectedPhysicalInputId),
              micID != kAudioDeviceUnknown else {
            bridgeLog("setupMicCapture: no physical mic found")
            throw PassthroughBridgeError.noPhysicalMicFound
        }

        var desc = AudioComponentDescription(
            componentType: kAudioUnitType_Output,
            componentSubType: kAudioUnitSubType_HALOutput,
            componentManufacturer: kAudioUnitManufacturer_Apple,
            componentFlags: 0, componentFlagsMask: 0
        )
        guard let comp = AudioComponentFindNext(nil, &desc) else {
            throw PassthroughBridgeError.audioUnitSetupFailed(1)
        }

        var err: OSStatus
        err = AudioComponentInstanceNew(comp, &micAU)
        guard err == noErr, let au = micAU else {
            bridgeLog("setupMicCapture: AudioComponentInstanceNew failed: \(err)")
            throw PassthroughBridgeError.audioUnitSetupFailed(err)
        }

        var enable: UInt32 = 1
        err = AudioUnitSetProperty(au, kAudioOutputUnitProperty_EnableIO,
                                   kAudioUnitScope_Input, 1, &enable, UInt32(MemoryLayout<UInt32>.size))
        guard err == noErr else { bridgeLog("setupMicCapture: EnableIO input failed: \(err)"); throw PassthroughBridgeError.audioUnitSetupFailed(err) }

        var disable: UInt32 = 0
        err = AudioUnitSetProperty(au, kAudioOutputUnitProperty_EnableIO,
                                   kAudioUnitScope_Output, 0, &disable, UInt32(MemoryLayout<UInt32>.size))
        guard err == noErr else { bridgeLog("setupMicCapture: EnableIO output disable failed: \(err)"); throw PassthroughBridgeError.audioUnitSetupFailed(err) }

        err = AudioUnitSetProperty(au, kAudioOutputUnitProperty_CurrentDevice,
                                   kAudioUnitScope_Global, 0, &micID, UInt32(MemoryLayout<AudioDeviceID>.size))
        guard err == noErr else { bridgeLog("setupMicCapture: CurrentDevice failed: \(err)"); throw PassthroughBridgeError.audioUnitSetupFailed(err) }

        var inputCallback = AURenderCallbackStruct(
            inputProc: micInputCallback,
            inputProcRefCon: Unmanaged.passUnretained(self).toOpaque()
        )
        err = AudioUnitSetProperty(au, kAudioOutputUnitProperty_SetInputCallback,
                                   kAudioUnitScope_Global, 0, &inputCallback, UInt32(MemoryLayout<AURenderCallbackStruct>.size))
        guard err == noErr else { bridgeLog("setupMicCapture: SetInputCallback failed: \(err)"); throw PassthroughBridgeError.audioUnitSetupFailed(err) }

        var format = AudioStreamBasicDescription(
            mSampleRate: 48000,
            mFormatID: kAudioFormatLinearPCM,
            mFormatFlags: kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked,
            mBytesPerPacket: 8,
            mFramesPerPacket: 1,
            mBytesPerFrame: 8,
            mChannelsPerFrame: 2,
            mBitsPerChannel: 32,
            mReserved: 0
        )
        err = AudioUnitSetProperty(au, kAudioUnitProperty_StreamFormat,
                                   kAudioUnitScope_Output, 1, &format, UInt32(MemoryLayout<AudioStreamBasicDescription>.size))
        guard err == noErr else { bridgeLog("setupMicCapture: StreamFormat failed: \(err)"); throw PassthroughBridgeError.audioUnitSetupFailed(err) }

        err = AudioUnitInitialize(au)
        guard err == noErr else { bridgeLog("setupMicCapture: AudioUnitInitialize failed: \(err)"); throw PassthroughBridgeError.audioUnitSetupFailed(err) }
        var actualFormat = AudioStreamBasicDescription()
        var actualFormatSize = UInt32(MemoryLayout<AudioStreamBasicDescription>.size)
        if AudioUnitGetProperty(
            au,
            kAudioUnitProperty_StreamFormat,
            kAudioUnitScope_Output,
            1,
            &actualFormat,
            &actualFormatSize
        ) == noErr {
            bridgeLog("setupMicCapture: actual format rate=\(actualFormat.mSampleRate) channels=\(actualFormat.mChannelsPerFrame) flags=\(actualFormat.mFormatFlags) bytesPerFrame=\(actualFormat.mBytesPerFrame)")
        }
        bridgeLog("setupMicCapture: OK, micID=\(micID)")
    }

    private func setupSpeakerPlayback() throws {
        guard var speakerID = try findPhysicalDevice(scope: kAudioDevicePropertyScopeOutput, selectedId: selectedPhysicalOutputId),
              speakerID != kAudioDeviceUnknown else {
            bridgeLog("setupSpeakerPlayback: no physical speaker found")
            throw PassthroughBridgeError.noPhysicalSpeakerFound
        }

        var desc = AudioComponentDescription(
            componentType: kAudioUnitType_Output,
            componentSubType: kAudioUnitSubType_HALOutput,
            componentManufacturer: kAudioUnitManufacturer_Apple,
            componentFlags: 0, componentFlagsMask: 0
        )
        guard let comp = AudioComponentFindNext(nil, &desc) else {
            throw PassthroughBridgeError.audioUnitSetupFailed(2)
        }

        var err: OSStatus
        err = AudioComponentInstanceNew(comp, &speakerAU)
        guard err == noErr, let au = speakerAU else {
            bridgeLog("setupSpeakerPlayback: AudioComponentInstanceNew failed: \(err)")
            throw PassthroughBridgeError.audioUnitSetupFailed(err)
        }

        err = AudioUnitSetProperty(au, kAudioOutputUnitProperty_CurrentDevice,
                                   kAudioUnitScope_Global, 0, &speakerID, UInt32(MemoryLayout<AudioDeviceID>.size))
        guard err == noErr else { bridgeLog("setupSpeakerPlayback: CurrentDevice failed: \(err)"); throw PassthroughBridgeError.audioUnitSetupFailed(err) }

        var renderCallback = AURenderCallbackStruct(
            inputProc: speakerRenderCallback,
            inputProcRefCon: Unmanaged.passUnretained(self).toOpaque()
        )
        err = AudioUnitSetProperty(au, kAudioUnitProperty_SetRenderCallback,
                                   kAudioUnitScope_Input, 0, &renderCallback, UInt32(MemoryLayout<AURenderCallbackStruct>.size))
        guard err == noErr else { bridgeLog("setupSpeakerPlayback: SetRenderCallback failed: \(err)"); throw PassthroughBridgeError.audioUnitSetupFailed(err) }

        var format = AudioStreamBasicDescription(
            mSampleRate: 48000,
            mFormatID: kAudioFormatLinearPCM,
            mFormatFlags: kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked,
            mBytesPerPacket: 8,
            mFramesPerPacket: 1,
            mBytesPerFrame: 8,
            mChannelsPerFrame: 2,
            mBitsPerChannel: 32,
            mReserved: 0
        )
        err = AudioUnitSetProperty(au, kAudioUnitProperty_StreamFormat,
                                   kAudioUnitScope_Input, 0, &format, UInt32(MemoryLayout<AudioStreamBasicDescription>.size))
        guard err == noErr else { bridgeLog("setupSpeakerPlayback: StreamFormat failed: \(err)"); throw PassthroughBridgeError.audioUnitSetupFailed(err) }

        err = AudioUnitInitialize(au)
        guard err == noErr else { bridgeLog("setupSpeakerPlayback: AudioUnitInitialize failed: \(err)"); throw PassthroughBridgeError.audioUnitSetupFailed(err) }
        var actualFormat = AudioStreamBasicDescription()
        var actualFormatSize = UInt32(MemoryLayout<AudioStreamBasicDescription>.size)
        if AudioUnitGetProperty(
            au,
            kAudioUnitProperty_StreamFormat,
            kAudioUnitScope_Input,
            0,
            &actualFormat,
            &actualFormatSize
        ) == noErr {
            bridgeLog("setupSpeakerPlayback: actual format rate=\(actualFormat.mSampleRate) channels=\(actualFormat.mChannelsPerFrame) flags=\(actualFormat.mFormatFlags) bytesPerFrame=\(actualFormat.mBytesPerFrame)")
        }
        bridgeLog("setupSpeakerPlayback: OK, speakerID=\(speakerID)")
    }
}

private let micInputCallback: AURenderCallback = { (inRefCon, ioActionFlags, inTimeStamp, inBusNumber, inNumberFrames, ioData) -> OSStatus in
    let bridge = Unmanaged<PassthroughBridge>.fromOpaque(inRefCon).takeUnretainedValue()
    guard let au = bridge.micAU else { bridgeLog("micCB: no micAU"); return noErr }

    let frameCount = Int(inNumberFrames)
    var samples = [Float](repeating: 0, count: frameCount * 2)
    let err = samples.withUnsafeMutableBufferPointer { sampleBuffer -> OSStatus in
        var bufferList = AudioBufferList(
            mNumberBuffers: 1,
            mBuffers: AudioBuffer(
                mNumberChannels: 2,
                mDataByteSize: UInt32(frameCount * 2 * MemoryLayout<Float>.stride),
                mData: sampleBuffer.baseAddress
            )
        )
        return AudioUnitRender(au, ioActionFlags, inTimeStamp, 1, inNumberFrames, &bufferList)
    }
    guard err == noErr else {
        bridgeLog("micCB: AudioUnitRender failed: \(err)")
        return err
    }
    bridge.micCallbackCount += 1
    let samplePeak = peak(samples, count: frameCount * 2)
    if samplePeak > 0.0001 {
        bridge.micNonZeroCount += 1
    }

    let ok = samples.withUnsafeBufferPointer { sampleBuffer -> Bool in
        guard let baseAddress = sampleBuffer.baseAddress else {
            return false
        }
        return bridge.shm.writeMic(src: baseAddress, count: frameCount * 2)
    }
    if bridge.micCallbackCount <= 10 || bridge.micCallbackCount % 100 == 0 || !ok {
        bridgeLog("micCB: count=\(bridge.micCallbackCount) frames=\(frameCount) peak=\(samplePeak) nonzero=\(bridge.micNonZeroCount) write=\(ok) micAvail=\(bridge.shm.micAvailable())")
    }
    bridge.recordAppIOHeartbeat()
    return noErr
}

private let speakerRenderCallback: AURenderCallback = { (inRefCon, ioActionFlags, inTimeStamp, inBusNumber, inNumberFrames, ioData) -> OSStatus in
    let bridge = Unmanaged<PassthroughBridge>.fromOpaque(inRefCon).takeUnretainedValue()

    guard let ioData = ioData else { bridgeLog("spkCB: nil ioData"); return noErr }

    let frameCount = Int(inNumberFrames)
    let requestedSampleCount = frameCount * 2
    var temp = [Float](repeating: 0, count: requestedSampleCount)

    let available = bridge.shm.speakerAvailable()
    let readCount = min(requestedSampleCount, Int(available))
    var source = [Float](repeating: 0, count: max(readCount, 0))
    let read = readCount > 0
        ? bridge.shm.readSpeaker(dst: &source, count: readCount)
        : 0
    let outputMode: String
    if read == requestedSampleCount {
        temp = source
        outputMode = "full"
    } else if read > 0 {
        stretchStereo(source, sourceSampleCount: read, into: &temp, destinationFrameCount: frameCount)
        outputMode = "stretch"
    } else {
        outputMode = "silence"
    }
    bridge.speakerCallbackCount += 1
    let samplePeak = peak(temp, count: read)
    if samplePeak > 0.0001 {
        bridge.speakerNonZeroCount += 1
    }
    if read > 0 {
        bridge.recordAppIOHeartbeat()
    }

    let abl = UnsafeMutableAudioBufferListPointer(ioData)
    if abl.count == 1 {
        let buf = abl[0]
        let byteCount = Int(buf.mDataByteSize)
        if let dst = buf.mData {
            let dstPtr = dst.assumingMemoryBound(to: Float.self)
            let copyCount = min(byteCount / MemoryLayout<Float>.size, requestedSampleCount)
            if read > 0 {
                dstPtr.update(from: temp, count: copyCount)
            } else {
                memset(dst, 0, byteCount)
            }
        }
    } else {
        for ch in 0..<min(abl.count, 2) {
            let buf = abl[ch]
            let byteCount = Int(buf.mDataByteSize)
            if let dst = buf.mData {
                let dstPtr = dst.assumingMemoryBound(to: Float.self)
                let chFrames = min(byteCount / MemoryLayout<Float>.size, frameCount)
                if read > 0 {
                    for f in 0..<chFrames {
                        dstPtr[f] = temp[f * 2 + ch]
                    }
                } else {
                    memset(dst, 0, byteCount)
                }
            }
        }
    }

    if bridge.speakerCallbackCount <= 10 || bridge.speakerCallbackCount % 100 == 0 {
        bridgeLog("spkCB: count=\(bridge.speakerCallbackCount) mode=\(outputMode) frames=\(frameCount) requested=\(requestedSampleCount) read=\(read) peak=\(samplePeak) nonzero=\(bridge.speakerNonZeroCount) speakerAvailBefore=\(available) speakerAvailAfter=\(bridge.shm.speakerAvailable()) buffers=\(abl.count)")
    }

    return noErr
}
