#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

constexpr AudioObjectPropertyElement kMainElement = 0;
constexpr const char* kExpectedMicrophone = "2brain Rec Microphone";
constexpr const char* kExpectedSpeaker = "2brain Rec Speaker";

enum class ExpectationMode {
    PublicationOnly,
    DefaultSafe,
    NonRunningSurface,
    VisibleAliveSurface
};

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

ExpectationMode ParseExpectationMode(int argc, char** argv) {
    if (argc <= 1) {
        return ExpectationMode::PublicationOnly;
    }
    const std::string arg = argv[1];
    if (arg == "--expect-default-safe") {
        return ExpectationMode::DefaultSafe;
    }
    if (arg == "--expect-non-running-surface") {
        return ExpectationMode::NonRunningSurface;
    }
    if (arg == "--expect-visible-alive-surface") {
        return ExpectationMode::VisibleAliveSurface;
    }
    if (arg == "--help" || arg == "-h") {
        std::cout << "Usage: runtime-device-probe [--expect-default-safe|--expect-non-running-surface|--expect-visible-alive-surface]\n";
        std::cout << "  no argument             require both 2brain Rec devices to be published\n";
        std::cout << "  --expect-default-safe   require visible/alive/non-running default safe state\n";
        std::cout << "  --expect-non-running-surface require readable devices with no public running state\n";
        std::cout << "  --expect-visible-alive-surface require visible/alive devices only; measured audio evidence is separate\n";
        std::exit(0);
    }
    std::cerr << "Unknown runtime probe argument: " << arg << "\n";
    std::exit(64);
}

bool HasReadableState(const ExpectedDeviceState& state) {
    return state.hidden_read && state.alive_read && state.running_read;
}

bool MatchesDefaultSafe(const ExpectedDeviceState& state) {
    return state.found &&
           HasReadableState(state) &&
           !state.hidden &&
           state.alive &&
           !state.running;
}

bool MatchesNonRunningSurface(const ExpectedDeviceState& state) {
    return state.found &&
           HasReadableState(state) &&
           !state.running;
}

bool MatchesVisibleAliveSurface(const ExpectedDeviceState& state) {
    return state.found &&
           HasReadableState(state) &&
           !state.hidden &&
           state.alive;
}

bool ValidateExpectation(
    ExpectationMode mode,
    const ExpectedDeviceState& microphone,
    const ExpectedDeviceState& speaker
) {
    switch (mode) {
    case ExpectationMode::PublicationOnly:
        return microphone.found && speaker.found;
    case ExpectationMode::DefaultSafe:
        return MatchesDefaultSafe(microphone) && MatchesDefaultSafe(speaker);
    case ExpectationMode::NonRunningSurface:
        return MatchesNonRunningSurface(microphone) && MatchesNonRunningSurface(speaker);
    case ExpectationMode::VisibleAliveSurface:
        return MatchesVisibleAliveSurface(microphone) && MatchesVisibleAliveSurface(speaker);
    }
}

const char* ExpectationLabel(ExpectationMode mode) {
    switch (mode) {
    case ExpectationMode::PublicationOnly:
        return "publication-only";
    case ExpectationMode::DefaultSafe:
        return "default-safe";
    case ExpectationMode::NonRunningSurface:
        return "non-running-surface";
    case ExpectationMode::VisibleAliveSurface:
        return "visible-alive-surface";
    }
}

}  // namespace

int main(int argc, char** argv) {
    const ExpectationMode mode = ParseExpectationMode(argc, argv);

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

    std::cout << "Runtime passthrough evidence: " << ExpectationLabel(mode)
              << "; this is Core Audio surface state only, not measured live audio acceptance.\n";
    std::cout << "Expected device visibility:\n";
    std::cout << "- " << kExpectedMicrophone << ": " << (microphone.found ? "FOUND" : "MISSING") << "\n";
    std::cout << "  hidden=" << TriState(microphone.hidden_read, microphone.hidden)
              << " alive=" << TriState(microphone.alive_read, microphone.alive)
              << " running=" << TriState(microphone.running_read, microphone.running) << "\n";
    std::cout << "- " << kExpectedSpeaker << ": " << (speaker.found ? "FOUND" : "MISSING") << "\n";
    std::cout << "  hidden=" << TriState(speaker.hidden_read, speaker.hidden)
              << " alive=" << TriState(speaker.alive_read, speaker.alive)
              << " running=" << TriState(speaker.running_read, speaker.running) << "\n";

    if (!ValidateExpectation(mode, microphone, speaker)) {
        std::cerr << "Runtime Core Audio publication proof: BLOCKED\n";
        return 2;
    }

    std::cout << "Runtime Core Audio publication proof: ACCEPTED\n";
    return 0;
}
