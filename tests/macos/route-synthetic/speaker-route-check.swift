#!/usr/bin/env swift

import CoreAudio
import Foundation

struct AudioDevice {
    let id: AudioDeviceID
    let name: String
    let inputChannels: UInt32
    let outputChannels: UInt32
}

let expectedName = "2brain Rec Speaker"
let devices = try allAudioDevices()

print("Synthetic speaker route preflight:")
for device in devices {
    print("- \(device.name) input=\(device.inputChannels) output=\(device.outputChannels)")
}

guard let virtualSpeaker = devices.first(where: { $0.name == expectedName }) else {
    fail("Expected \(expectedName) to be visible to Core Audio.")
}

guard virtualSpeaker.outputChannels > 0 else {
    fail("\(expectedName) is visible but has no output channels.")
}

guard virtualSpeaker.inputChannels == 0 else {
    fail("\(expectedName) must not expose input channels; speaker capture mirror must remain separate.")
}

print("Synthetic speaker route preflight: ACCEPTED")

func allAudioDevices() throws -> [AudioDevice] {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDevices,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var byteCount: UInt32 = 0
    var status = AudioObjectGetPropertyDataSize(
        AudioObjectID(kAudioObjectSystemObject),
        &address,
        0,
        nil,
        &byteCount
    )
    guard status == noErr else {
        throw NSError(domain: NSOSStatusErrorDomain, code: Int(status))
    }

    let count = Int(byteCount) / MemoryLayout<AudioDeviceID>.size
    var ids = Array(repeating: AudioDeviceID(), count: count)
    status = AudioObjectGetPropertyData(
        AudioObjectID(kAudioObjectSystemObject),
        &address,
        0,
        nil,
        &byteCount,
        &ids
    )
    guard status == noErr else {
        throw NSError(domain: NSOSStatusErrorDomain, code: Int(status))
    }

    return ids.compactMap { id in
        guard let name = deviceName(id) else {
            return nil
        }
        return AudioDevice(
            id: id,
            name: name,
            inputChannels: channelCount(for: id, scope: kAudioDevicePropertyScopeInput),
            outputChannels: channelCount(for: id, scope: kAudioDevicePropertyScopeOutput)
        )
    }
}

func deviceName(_ id: AudioDeviceID) -> String? {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioObjectPropertyName,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var name: CFString = "" as CFString
    var byteCount = UInt32(MemoryLayout<CFString>.size)
    let status = withUnsafeMutablePointer(to: &name) { namePointer in
        AudioObjectGetPropertyData(id, &address, 0, nil, &byteCount, namePointer)
    }
    guard status == noErr else {
        return nil
    }
    return name as String
}

func channelCount(for id: AudioDeviceID, scope: AudioObjectPropertyScope) -> UInt32 {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyStreamConfiguration,
        mScope: scope,
        mElement: kAudioObjectPropertyElementMain
    )
    var byteCount: UInt32 = 0
    guard AudioObjectGetPropertyDataSize(id, &address, 0, nil, &byteCount) == noErr, byteCount > 0 else {
        return 0
    }

    let bufferList = UnsafeMutableRawPointer.allocate(
        byteCount: Int(byteCount),
        alignment: MemoryLayout<AudioBufferList>.alignment
    )
    defer { bufferList.deallocate() }

    guard AudioObjectGetPropertyData(id, &address, 0, nil, &byteCount, bufferList) == noErr else {
        return 0
    }

    let audioBufferList = UnsafeMutableAudioBufferListPointer(bufferList.assumingMemoryBound(to: AudioBufferList.self))
    return audioBufferList.reduce(0) { $0 + $1.mNumberChannels }
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}
