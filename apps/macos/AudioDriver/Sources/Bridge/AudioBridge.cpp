#include "AudioBridge.hpp"

#include <cstdio>

namespace TwoBrainRec {

PhysicalDeviceBridge::PhysicalDeviceBridge()
    : mic_buffer_(kRingBufferCapacity),
      speaker_buffer_(kRingBufferCapacity),
      capture_buffer_(kRingBufferCapacity) {}

PhysicalDeviceBridge::~PhysicalDeviceBridge() {
    Stop();
}

bool PhysicalDeviceBridge::Start(AudioObjectID micDeviceID, AudioObjectID speakerDeviceID) {
    Stop();

    mic_device_ = micDeviceID;
    speaker_device_ = speakerDeviceID;

    mic_buffer_.Reset();
    speaker_buffer_.Reset();
    capture_buffer_.Reset();

    OSStatus status = AudioDeviceCreateIOProcID(
        mic_device_,
        MicIOProc,
        this,
        &mic_io_proc_id_
    );
    if (status != noErr) {
        fprintf(stderr, "AudioBridge: failed to create mic IO proc: %d\n", status);
        Stop();
        return false;
    }

    status = AudioDeviceStart(mic_device_, mic_io_proc_id_);
    if (status != noErr) {
        fprintf(stderr, "AudioBridge: failed to start mic IO: %d\n", status);
        Stop();
        return false;
    }

    status = AudioDeviceCreateIOProcID(
        speaker_device_,
        SpeakerIOProc,
        this,
        &speaker_io_proc_id_
    );
    if (status != noErr) {
        fprintf(stderr, "AudioBridge: failed to create speaker IO proc: %d\n", status);
        Stop();
        return false;
    }

    status = AudioDeviceStart(speaker_device_, speaker_io_proc_id_);
    if (status != noErr) {
        fprintf(stderr, "AudioBridge: failed to start speaker IO: %d\n", status);
        Stop();
        return false;
    }

    running_ = true;
    return true;
}

void PhysicalDeviceBridge::Stop() {
    if (mic_io_proc_id_ != nullptr) {
        AudioDeviceStop(mic_device_, mic_io_proc_id_);
        AudioDeviceDestroyIOProcID(mic_device_, mic_io_proc_id_);
        mic_io_proc_id_ = nullptr;
    }
    if (speaker_io_proc_id_ != nullptr) {
        AudioDeviceStop(speaker_device_, speaker_io_proc_id_);
        AudioDeviceDestroyIOProcID(speaker_device_, speaker_io_proc_id_);
        speaker_io_proc_id_ = nullptr;
    }
    mic_device_ = kAudioObjectUnknown;
    speaker_device_ = kAudioObjectUnknown;
    running_ = false;
}

OSStatus PhysicalDeviceBridge::MicIOProc(
    AudioObjectID,
    const AudioTimeStamp*,
    const AudioBufferList* inInputData,
    const AudioTimeStamp*,
    AudioBufferList*,
    const AudioTimeStamp*,
    void* inClientData
) {
    auto* bridge = static_cast<PhysicalDeviceBridge*>(inClientData);
    if (inInputData == nullptr || inInputData->mNumberBuffers == 0) {
        return noErr;
    }
    const auto& buffer = inInputData->mBuffers[0];
    if (buffer.mData == nullptr) {
        return noErr;
    }
    auto* src = static_cast<const float*>(buffer.mData);
    const size_t frameCount = buffer.mDataByteSize / sizeof(float);
    bridge->mic_buffer_.Write(src, frameCount);
    return noErr;
}

OSStatus PhysicalDeviceBridge::SpeakerIOProc(
    AudioObjectID,
    const AudioTimeStamp*,
    const AudioBufferList*,
    const AudioTimeStamp*,
    AudioBufferList* outOutputData,
    const AudioTimeStamp*,
    void* inClientData
) {
    auto* bridge = static_cast<PhysicalDeviceBridge*>(inClientData);
    if (outOutputData == nullptr || outOutputData->mNumberBuffers == 0) {
        return noErr;
    }
    auto& buffer = outOutputData->mBuffers[0];
    if (buffer.mData == nullptr) {
        return noErr;
    }
    auto* dst = static_cast<float*>(buffer.mData);
    const size_t frameCount = buffer.mDataByteSize / sizeof(float);
    const size_t read = bridge->speaker_buffer_.Read(dst, frameCount);
    if (read < frameCount) {
        std::memset(dst + read, 0, (frameCount - read) * sizeof(float));
    }
    return noErr;
}

static AudioObjectID GetDefaultDevice(bool isInput) {
    AudioObjectPropertyAddress addr = {
        isInput ? kAudioHardwarePropertyDefaultInputDevice : kAudioHardwarePropertyDefaultOutputDevice,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMain
    };
    AudioObjectID device = kAudioObjectUnknown;
    UInt32 size = sizeof(device);
    OSStatus status = AudioObjectGetPropertyData(
        kAudioObjectSystemObject,
        &addr,
        0, nullptr,
        &size, &device
    );
    if (status != noErr) {
        return kAudioObjectUnknown;
    }
    return device;
}

AudioObjectID GetDefaultInputDevice() {
    return GetDefaultDevice(true);
}

AudioObjectID GetDefaultOutputDevice() {
    return GetDefaultDevice(false);
}

Float64 GetDeviceSampleRate(AudioObjectID deviceID) {
    AudioObjectPropertyAddress addr = {
        kAudioDevicePropertyNominalSampleRate,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMain
    };
    Float64 rate = 0.0;
    UInt32 size = sizeof(rate);
    OSStatus status = AudioObjectGetPropertyData(
        deviceID, &addr, 0, nullptr, &size, &rate
    );
    if (status != noErr) {
        return 0.0;
    }
    return rate;
}

bool MatchDeviceSampleRate(AudioObjectID deviceID, Float64 targetRate) {
    if (deviceID == kAudioObjectUnknown) {
        return false;
    }
    Float64 actual = GetDeviceSampleRate(deviceID);
    if (actual <= 0.0) {
        return false;
    }
    return actual == targetRate;
}

} // namespace TwoBrainRec