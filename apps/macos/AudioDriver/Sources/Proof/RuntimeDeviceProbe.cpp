#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>

#include <iostream>
#include <string>
#include <vector>

namespace {

constexpr AudioObjectPropertyElement kMainElement = 0;
constexpr const char* kExpectedMicrophone = "2brain Rec Microphone";
constexpr const char* kExpectedSpeaker = "2brain Rec Speaker";

std::string StatusToString(OSStatus status) {
    return std::to_string(static_cast<int>(status));
}

bool GetDeviceIds(std::vector<AudioDeviceID>* devices) {
    AudioObjectPropertyAddress address{
        kAudioHardwarePropertyDevices,
        kAudioObjectPropertyScopeGlobal,
        kMainElement
    };

    UInt32 byte_count = 0;
    OSStatus status = AudioObjectGetPropertyDataSize(
        kAudioObjectSystemObject,
        &address,
        0,
        nullptr,
        &byte_count
    );
    if (status != noErr) {
        std::cerr << "Failed to read Core Audio device list size: " << StatusToString(status) << "\n";
        return false;
    }

    if (byte_count == 0 || byte_count % sizeof(AudioDeviceID) != 0) {
        std::cerr << "Core Audio returned an invalid device list size: " << byte_count << "\n";
        return false;
    }

    devices->resize(byte_count / sizeof(AudioDeviceID));
    status = AudioObjectGetPropertyData(
        kAudioObjectSystemObject,
        &address,
        0,
        nullptr,
        &byte_count,
        devices->data()
    );
    if (status != noErr) {
        std::cerr << "Failed to read Core Audio device list: " << StatusToString(status) << "\n";
        return false;
    }

    return true;
}

std::string GetDeviceName(AudioDeviceID device_id) {
    AudioObjectPropertyAddress address{
        kAudioObjectPropertyName,
        kAudioObjectPropertyScopeGlobal,
        kMainElement
    };

    CFStringRef cf_name = nullptr;
    UInt32 byte_count = sizeof(cf_name);
    OSStatus status = AudioObjectGetPropertyData(
        device_id,
        &address,
        0,
        nullptr,
        &byte_count,
        &cf_name
    );
    if (status != noErr || cf_name == nullptr) {
        return "<unreadable:" + StatusToString(status) + ">";
    }

    char buffer[1024] = {0};
    const Boolean converted = CFStringGetCString(
        cf_name,
        buffer,
        sizeof(buffer),
        kCFStringEncodingUTF8
    );
    CFRelease(cf_name);

    if (!converted) {
        return "<unconvertible>";
    }

    return std::string(buffer);
}

}  // namespace

int main() {
    std::vector<AudioDeviceID> devices;
    if (!GetDeviceIds(&devices)) {
        return 1;
    }

    bool microphone_found = false;
    bool speaker_found = false;

    std::cout << "Core Audio devices visible to this user:\n";
    for (const AudioDeviceID device_id : devices) {
        const std::string name = GetDeviceName(device_id);
        std::cout << "- " << name << "\n";

        if (name == kExpectedMicrophone) {
            microphone_found = true;
        }
        if (name == kExpectedSpeaker) {
            speaker_found = true;
        }
    }

    std::cout << "Expected device visibility:\n";
    std::cout << "- " << kExpectedMicrophone << ": " << (microphone_found ? "FOUND" : "MISSING") << "\n";
    std::cout << "- " << kExpectedSpeaker << ": " << (speaker_found ? "FOUND" : "MISSING") << "\n";

    if (!microphone_found || !speaker_found) {
        std::cerr << "Runtime Core Audio publication proof: BLOCKED\n";
        return 2;
    }

    std::cout << "Runtime Core Audio publication proof: ACCEPTED\n";
    return 0;
}
