#pragma once

#include <CoreAudio/AudioHardware.h>
#include <CoreAudio/AudioServerPlugIn.h>

namespace TwoBrainRec::AudioDriver {

inline constexpr AudioObjectID kMicrophoneDeviceObjectID = 2;
inline constexpr AudioObjectID kSpeakerDeviceObjectID = 3;
inline constexpr AudioObjectID kMicrophoneStreamObjectID = 4;
inline constexpr AudioObjectID kSpeakerStreamObjectID = 5;

struct VirtualDeviceDescriptor {
    AudioObjectID device_object_id;
    AudioObjectID stream_object_id;
    const char* display_name;
    const char* uid;
    bool is_input;
};

UInt32 VirtualDeviceCount();
const AudioObjectID* VirtualDeviceObjectIDs();
const VirtualDeviceDescriptor* FindVirtualDevice(AudioObjectID object_id);
const VirtualDeviceDescriptor* FindVirtualStream(AudioObjectID object_id);
bool IsVirtualDevice(AudioObjectID object_id);
bool IsVirtualStream(AudioObjectID object_id);
AudioObjectID OwnerForVirtualObject(AudioObjectID object_id);
AudioObjectID StreamForVirtualDevice(AudioObjectID device_id);
bool VirtualStreamIsInput(AudioObjectID stream_id);
UInt32 StreamCountForVirtualDevice(AudioObjectID device_id, AudioObjectPropertyScope scope);
const char* VirtualDeviceName(AudioObjectID device_id);
const char* VirtualDeviceUID(AudioObjectID device_id);
const char* VirtualStreamName(AudioObjectID stream_id);

}  // namespace TwoBrainRec::AudioDriver
