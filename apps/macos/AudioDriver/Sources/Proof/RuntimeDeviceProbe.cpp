#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>

#include <iostream>
#include <string>
#include <vector>

namespace {

constexpr AudioObjectPropertyElement kMainElement = 0;
constexpr const char* kExpectedMicrophone = "2brain Rec Microphone";
constexpr const char* kExpectedSpeaker = "2brain Rec Speaker";

struct ExpectedDeviceState {
    std::string name;
    bool found = false;
    bool hidden = false;
    bool hidden_read = false;
    bool alive = false;
    bool alive_read = false;
    bool running = false;
    bool running_read = false;
};

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

bool ReadUInt32Property(
    AudioDeviceID device_id,
    AudioObjectPropertySelector selector,
    UInt32* value
) {
    AudioObjectPropertyAddress address{
        selector,
        kAudioObjectPropertyScopeGlobal,
        kMainElement
    };

    UInt32 byte_count = sizeof(*value);
    const OSStatus status = AudioObjectGetPropertyData(
        device_id,
        &address,
        0,
        nullptr,
        &byte_count,
        value
    );
    return status == noErr && byte_count == sizeof(*value);
}

void CaptureExpectedState(
    AudioDeviceID device_id,
    const std::string& name,
    ExpectedDeviceState* state
) {
    if (state == nullptr || name != state->name) {
        return;
    }

    state->found = true;

    UInt32 value = 0;
    if (ReadUInt32Property(device_id, kAudioDevicePropertyIsHidden, &value)) {
        state->hidden_read = true;
        state->hidden = value != 0;
    }
    if (ReadUInt32Property(device_id, kAudioDevicePropertyDeviceIsAlive, &value)) {
        state->alive_read = true;
        state->alive = value != 0;
    }
    if (ReadUInt32Property(device_id, kAudioDevicePropertyDeviceIsRunning, &value)) {
        state->running_read = true;
        state->running = value != 0;
    }
}

std::string TriState(bool read, bool value) {
    if (!read) {
        return "unreadable";
    }
    return value ? "1" : "0";
}

}  // namespace

int main() {
    std::vector<AudioDeviceID> devices;
    if (!GetDeviceIds(&devices)) {
        return 1;
    }

    ExpectedDeviceState microphone{kExpectedMicrophone};
    ExpectedDeviceState speaker{kExpectedSpeaker};

    std::cout << "Core Audio devices visible to this user:\n";
    for (const AudioDeviceID device_id : devices) {
        const std::string name = GetDeviceName(device_id);
        std::cout << "- " << name << "\n";

        CaptureExpectedState(device_id, name, &microphone);
        CaptureExpectedState(device_id, name, &speaker);
    }

    std::cout << "Expected device visibility:\n";
    std::cout << "- " << kExpectedMicrophone << ": " << (microphone.found ? "FOUND" : "MISSING") << "\n";
    std::cout << "  hidden=" << TriState(microphone.hidden_read, microphone.hidden)
              << " alive=" << TriState(microphone.alive_read, microphone.alive)
              << " running=" << TriState(microphone.running_read, microphone.running) << "\n";
    std::cout << "- " << kExpectedSpeaker << ": " << (speaker.found ? "FOUND" : "MISSING") << "\n";
    std::cout << "  hidden=" << TriState(speaker.hidden_read, speaker.hidden)
              << " alive=" << TriState(speaker.alive_read, speaker.alive)
              << " running=" << TriState(speaker.running_read, speaker.running) << "\n";

    if (!microphone.found || !speaker.found) {
        std::cerr << "Runtime Core Audio publication proof: BLOCKED\n";
        return 2;
    }

    std::cout << "Runtime Core Audio publication proof: ACCEPTED\n";
    return 0;
}
