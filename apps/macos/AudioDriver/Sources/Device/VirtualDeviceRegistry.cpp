#include "VirtualDeviceRegistry.hpp"

namespace TwoBrainRec::AudioDriver {
namespace {

constexpr VirtualDeviceDescriptor kDevices[] = {
    {
        kMicrophoneDeviceObjectID,
        kMicrophoneStreamObjectID,
        "2brain Rec Microphone",
        "pro.2brain.rec.microphone",
        true
    },
    {
        kSpeakerDeviceObjectID,
        kSpeakerStreamObjectID,
        "2brain Rec Speaker",
        "pro.2brain.rec.speaker",
        false
    }
};

bool ScopeMatches(const VirtualDeviceDescriptor& device, AudioObjectPropertyScope scope) {
    if (scope == kAudioObjectPropertyScopeGlobal) {
        return true;
    }
    return device.is_input
        ? scope == kAudioObjectPropertyScopeInput
        : scope == kAudioObjectPropertyScopeOutput;
}

}  // namespace

UInt32 VirtualDeviceCount() {
    return static_cast<UInt32>(sizeof(kDevices) / sizeof(kDevices[0]));
}

const AudioObjectID* VirtualDeviceObjectIDs() {
    static constexpr AudioObjectID kObjectIDs[] = {
        kMicrophoneDeviceObjectID,
        kSpeakerDeviceObjectID
    };
    return kObjectIDs;
}

const VirtualDeviceDescriptor* FindVirtualDevice(AudioObjectID object_id) {
    for (const auto& device : kDevices) {
        if (device.device_object_id == object_id) {
            return &device;
        }
    }
    return nullptr;
}

const VirtualDeviceDescriptor* FindVirtualStream(AudioObjectID object_id) {
    for (const auto& device : kDevices) {
        if (device.stream_object_id == object_id) {
            return &device;
        }
    }
    return nullptr;
}

bool IsVirtualDevice(AudioObjectID object_id) {
    return FindVirtualDevice(object_id) != nullptr;
}

bool IsVirtualStream(AudioObjectID object_id) {
    return FindVirtualStream(object_id) != nullptr;
}

AudioObjectID OwnerForVirtualObject(AudioObjectID object_id) {
    if (IsVirtualDevice(object_id)) {
        return kAudioObjectPlugInObject;
    }
    if (const auto* stream = FindVirtualStream(object_id)) {
        return stream->device_object_id;
    }
    return kAudioObjectUnknown;
}

AudioObjectID StreamForVirtualDevice(AudioObjectID device_id) {
    if (const auto* device = FindVirtualDevice(device_id)) {
        return device->stream_object_id;
    }
    return kAudioObjectUnknown;
}

bool VirtualStreamIsInput(AudioObjectID stream_id) {
    if (const auto* stream = FindVirtualStream(stream_id)) {
        return stream->is_input;
    }
    return false;
}

UInt32 StreamCountForVirtualDevice(AudioObjectID device_id, AudioObjectPropertyScope scope) {
    if (const auto* device = FindVirtualDevice(device_id)) {
        return ScopeMatches(*device, scope) ? 1 : 0;
    }
    return 0;
}

const char* VirtualDeviceName(AudioObjectID device_id) {
    if (const auto* device = FindVirtualDevice(device_id)) {
        return device->display_name;
    }
    return "2brain Rec Unknown Device";
}

const char* VirtualDeviceUID(AudioObjectID device_id) {
    if (const auto* device = FindVirtualDevice(device_id)) {
        return device->uid;
    }
    return "pro.2brain.rec.unknown";
}

const char* VirtualStreamName(AudioObjectID stream_id) {
    if (const auto* stream = FindVirtualStream(stream_id)) {
        return stream->is_input ? "2brain Rec Microphone Stream" : "2brain Rec Speaker Stream";
    }
    return "2brain Rec Unknown Stream";
}

}  // namespace TwoBrainRec::AudioDriver
