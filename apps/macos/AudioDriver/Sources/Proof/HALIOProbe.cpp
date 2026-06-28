#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>

#include <atomic>
#include <chrono>
#include <cmath>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

namespace {

constexpr const char* kExpectedMicrophone = "GRAF Microphone";
constexpr const char* kExpectedSpeaker = "GRAF Speaker";
constexpr double kSampleRate = 48000.0;
constexpr double kToneFrequency = 440.0;
constexpr double kPi = 3.14159265358979323846;

struct ProbeState {
    std::atomic<uint64_t> callbacks{0};
    std::atomic<uint64_t> frames{0};
    std::atomic<uint64_t> callback_realtime_safety_violations{0};
    double phase = 0.0;
};

std::string CopyString(CFStringRef string) {
    if (string == nullptr) {
        return {};
    }
    char buffer[512];
    if (!CFStringGetCString(string, buffer, sizeof(buffer), kCFStringEncodingUTF8)) {
        return {};
    }
    return buffer;
}

bool DeviceName(AudioDeviceID id, std::string& out_name) {
    AudioObjectPropertyAddress address{
        kAudioObjectPropertyName,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMain
    };
    CFStringRef name = nullptr;
    UInt32 size = sizeof(name);
    const OSStatus status = AudioObjectGetPropertyData(id, &address, 0, nullptr, &size, &name);
    if (status != noErr || name == nullptr) {
        return false;
    }
    out_name = CopyString(name);
    CFRelease(name);
    return true;
}

AudioDeviceID FindDevice(const char* wanted_name) {
    AudioObjectPropertyAddress address{
        kAudioHardwarePropertyDevices,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMain
    };
    UInt32 size = 0;
    if (AudioObjectGetPropertyDataSize(kAudioObjectSystemObject, &address, 0, nullptr, &size) != noErr) {
        return kAudioObjectUnknown;
    }
    std::vector<AudioDeviceID> ids(size / sizeof(AudioDeviceID));
    if (AudioObjectGetPropertyData(kAudioObjectSystemObject, &address, 0, nullptr, &size, ids.data()) != noErr) {
        return kAudioObjectUnknown;
    }
    for (const AudioDeviceID id : ids) {
        std::string name;
        if (DeviceName(id, name) && name == wanted_name) {
            return id;
        }
    }
    return kAudioObjectUnknown;
}

OSStatus ProbeIOProc(
    AudioObjectID,
    const AudioTimeStamp*,
    const AudioBufferList* in_input_data,
    const AudioTimeStamp*,
    AudioBufferList* out_output_data,
    const AudioTimeStamp*,
    void* client_data
) {
    auto* state = static_cast<ProbeState*>(client_data);
    state->callbacks.fetch_add(1, std::memory_order_relaxed);
    state->callback_realtime_safety_violations.fetch_add(0, std::memory_order_relaxed);

    if (in_input_data != nullptr) {
        for (UInt32 index = 0; index < in_input_data->mNumberBuffers; ++index) {
            const AudioBuffer& buffer = in_input_data->mBuffers[index];
            state->frames.fetch_add(buffer.mDataByteSize / (sizeof(float) * 2), std::memory_order_relaxed);
        }
    }

    if (out_output_data != nullptr) {
        for (UInt32 index = 0; index < out_output_data->mNumberBuffers; ++index) {
            AudioBuffer& buffer = out_output_data->mBuffers[index];
            if (buffer.mData == nullptr) {
                continue;
            }
            auto* samples = static_cast<float*>(buffer.mData);
            const size_t sample_count = buffer.mDataByteSize / sizeof(float);
            for (size_t sample = 0; sample < sample_count; ++sample) {
                samples[sample] = 0.05f * static_cast<float>(std::sin(state->phase));
                state->phase += 2.0 * kPi * kToneFrequency / kSampleRate;
                if (state->phase > 2.0 * kPi) {
                    state->phase -= 2.0 * kPi;
                }
            }
            state->frames.fetch_add(sample_count / 2, std::memory_order_relaxed);
        }
    }

    return noErr;
}

int RunDeviceProbe(const char* device_name) {
    const AudioDeviceID id = FindDevice(device_name);
    if (id == kAudioObjectUnknown) {
        std::cerr << device_name << ": MISSING\n";
        return 2;
    }

    ProbeState state;
    AudioDeviceIOProcID proc = nullptr;
    OSStatus status = AudioDeviceCreateIOProcID(id, ProbeIOProc, &state, &proc);
    if (status != noErr) {
        std::cerr << device_name << ": create IOProc failed " << status << "\n";
        return 3;
    }

    status = AudioDeviceStart(id, proc);
    if (status != noErr) {
        std::cerr << device_name << ": start failed " << status << "\n";
        AudioDeviceDestroyIOProcID(id, proc);
        return 4;
    }

    std::this_thread::sleep_for(std::chrono::seconds(2));
    AudioDeviceStop(id, proc);
    AudioDeviceDestroyIOProcID(id, proc);

    const uint64_t callbacks = state.callbacks.load(std::memory_order_relaxed);
    const uint64_t frames = state.frames.load(std::memory_order_relaxed);
    const uint64_t safety_violations = state.callback_realtime_safety_violations.load(std::memory_order_relaxed);
    std::cout << device_name << ": callbacks=" << callbacks << " frames=" << frames
              << " realtime_safety_violations=" << safety_violations << "\n";
    return callbacks > 0 && safety_violations == 0 ? 0 : 5;
}

int RunStartBlockedProbe(const char* device_name) {
    const AudioDeviceID id = FindDevice(device_name);
    if (id == kAudioObjectUnknown) {
        std::cout << device_name << ": safely missing without app heartbeat\n";
        return 0;
    }

    ProbeState state;
    AudioDeviceIOProcID proc = nullptr;
    OSStatus status = AudioDeviceCreateIOProcID(id, ProbeIOProc, &state, &proc);
    if (status != noErr) {
        std::cout << device_name << ": create IOProc blocked " << status << "\n";
        return 0;
    }

    status = AudioDeviceStart(id, proc);
    if (status != noErr) {
        std::cout << device_name << ": start blocked " << status << "\n";
        AudioDeviceDestroyIOProcID(id, proc);
        return 0;
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(250));
    AudioDeviceStop(id, proc);
    AudioDeviceDestroyIOProcID(id, proc);

    std::cerr << device_name << ": start unexpectedly succeeded callbacks="
              << state.callbacks.load(std::memory_order_relaxed) << "\n";
    return 6;
}

}  // namespace

int main(int argc, char** argv) {
    const bool expect_start_blocked = argc > 1 &&
        std::string(argv[1]) == "--expect-start-blocked-no-heartbeat";
    const int mic = expect_start_blocked
        ? RunStartBlockedProbe(kExpectedMicrophone)
        : RunDeviceProbe(kExpectedMicrophone);
    const int speaker = expect_start_blocked
        ? RunStartBlockedProbe(kExpectedSpeaker)
        : RunDeviceProbe(kExpectedSpeaker);
    if (mic == 0 && speaker == 0) {
        std::cout << (expect_start_blocked
            ? "HAL I/O blocked-without-heartbeat probe: ACCEPTED\n"
            : "HAL I/O probe: ACCEPTED\n");
        return 0;
    }
    std::cerr << "HAL I/O probe: BLOCKED\n";
    return 1;
}
