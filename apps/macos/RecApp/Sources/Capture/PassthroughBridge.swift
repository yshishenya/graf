import AudioToolbox
import CoreAudio
import Foundation
import TwoBrainRecShared

public enum PassthroughBridgeError: Error {
    case noPhysicalMicFound
    case noPhysicalSpeakerFound
    case audioUnitSetupFailed(OSStatus)
    case sharedMemoryUnavailable
}

private func bridgeLog(_ msg: String) {
    let fd = open("/tmp/2brain-rec-bridge.log", O_CREAT | O_WRONLY | O_APPEND, 0644)
    guard fd >= 0 else { return }
    let ts = Date().timeIntervalSince1970
    let line = "[\(String(format: "%.3f", ts))] \(msg)\n"
    _ = line.withCString { write(fd, $0, strlen($0)) }
    close(fd)
}

public final class PassthroughBridge {
    fileprivate let shm: SharedAudioMemory
    fileprivate var micAU: AudioComponentInstance?
    fileprivate var speakerAU: AudioComponentInstance?
    private var isRunning = false
    private var lastHeartbeatAt: Date?
    private let queue = DispatchQueue(label: "com.2brainrec.passthrough", qos: .userInitiated)

    public init() throws {
        guard let shm = SharedAudioMemory() else {
            bridgeLog("init: sharedMemoryUnavailable")
            throw PassthroughBridgeError.sharedMemoryUnavailable
        }
        self.shm = shm
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

    fileprivate func recordAppIOHeartbeat(at date: Date = Date()) {
        lastHeartbeatAt = date
        shm.writeAppHeartbeat(at: date)
    }

    private func cleanupAudioUnits() {
        if let au = micAU { AudioComponentInstanceDispose(au); micAU = nil; bridgeLog("cleanup: mic disposed") }
        if let au = speakerAU { AudioComponentInstanceDispose(au); speakerAU = nil; bridgeLog("cleanup: speaker disposed") }
    }

    private func findPhysicalDevice(scope: AudioObjectPropertyScope) -> AudioDeviceID? {
        let isInput = scope == kAudioDevicePropertyScopeInput
        let keywords: [String] = isInput
            ? ["Microphone", "Mic", "Input", "Built-in Microphone", "Микрофон"]
            : ["Speaker", "Output", "Built-in Output", "Динамики"]

        var addr = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var dataSize: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &dataSize) == noErr,
              dataSize > 0 else { bridgeLog("findPhysicalDevice: cannot get device count"); return nil }
        let count = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
        var ids = [AudioDeviceID](repeating: 0, count: count)
        guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &dataSize, &ids) == noErr
        else { bridgeLog("findPhysicalDevice: cannot get device list"); return nil }
        for id in ids {
            var nameAddr = AudioObjectPropertyAddress(
                mSelector: kAudioObjectPropertyName,
                mScope: kAudioObjectPropertyScopeGlobal,
                mElement: kAudioObjectPropertyElementMain
            )
            var name: CFString = "" as CFString
            var sz = UInt32(MemoryLayout<CFString>.size)
            let nameStatus = withUnsafeMutableBytes(of: &name) { rawName in
                AudioObjectGetPropertyData(id, &nameAddr, 0, nil, &sz, rawName.baseAddress!)
            }
            guard nameStatus == noErr else { continue }
            let devName = name as String

            if devName.contains("2brain Rec") { continue }

            let nameMatches = keywords.contains { devName.localizedCaseInsensitiveContains($0) }
            if !nameMatches { continue }

            var streamAddr = AudioObjectPropertyAddress(
                mSelector: kAudioDevicePropertyStreamConfiguration,
                mScope: scope,
                mElement: kAudioObjectPropertyElementMain
            )
            var streamSize: UInt32 = 0
            guard AudioObjectGetPropertyDataSize(id, &streamAddr, 0, nil, &streamSize) == noErr,
                  streamSize > 0 else {
                continue
            }

            bridgeLog("findPhysicalDevice: FOUND \(id) '\(devName)' scope=\(scope)")
            return id
        }
        bridgeLog("findPhysicalDevice: no suitable device found")
        return nil
    }

    private func setupMicCapture() throws {
        guard var micID = findPhysicalDevice(scope: kAudioDevicePropertyScopeInput),
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
        bridgeLog("setupMicCapture: OK, micID=\(micID)")
    }

    private func setupSpeakerPlayback() throws {
        guard var speakerID = findPhysicalDevice(scope: kAudioDevicePropertyScopeOutput),
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

    let ok = samples.withUnsafeBufferPointer { sampleBuffer -> Bool in
        guard let baseAddress = sampleBuffer.baseAddress else {
            return false
        }
        return bridge.shm.writeMic(src: baseAddress, count: frameCount * 2)
    }
    if !ok {
        bridgeLog("micCB: writeMic failed (buffer full)")
    }
    bridge.recordAppIOHeartbeat()
    return noErr
}

private let speakerRenderCallback: AURenderCallback = { (inRefCon, ioActionFlags, inTimeStamp, inBusNumber, inNumberFrames, ioData) -> OSStatus in
    let bridge = Unmanaged<PassthroughBridge>.fromOpaque(inRefCon).takeUnretainedValue()

    guard let ioData = ioData else { bridgeLog("spkCB: nil ioData"); return noErr }

    let frameCount = Int(inNumberFrames)
    var temp = [Float](repeating: 0, count: frameCount * 2)

    let read = bridge.shm.readSpeaker(dst: &temp, count: frameCount * 2)
    if read > 0 {
        bridge.recordAppIOHeartbeat()
    }

    let abl = UnsafeMutableAudioBufferListPointer(ioData)
    if abl.count == 1 {
        let buf = abl[0]
        let byteCount = Int(buf.mDataByteSize)
        if let dst = buf.mData {
            let dstPtr = dst.assumingMemoryBound(to: Float.self)
            let copyCount = min(byteCount / MemoryLayout<Float>.size, frameCount * 2)
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

    return noErr
}
