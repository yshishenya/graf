#pragma once

#include <CoreAudio/CoreAudio.h>
#include "AudioRingBuffer.hpp"

namespace TwoBrainRec {

constexpr size_t kRingBufferCapacity = 16384;

class PhysicalDeviceBridge {
public:
    PhysicalDeviceBridge();
    ~PhysicalDeviceBridge();

    bool Start(AudioObjectID micDeviceID, AudioObjectID speakerDeviceID);
    void Stop();

    AudioRingBuffer& MicBuffer() { return mic_buffer_; }
    AudioRingBuffer& SpeakerBuffer() { return speaker_buffer_; }
    AudioRingBuffer& CaptureBuffer() { return capture_buffer_; }

    bool IsRunning() const { return running_; }

private:
    AudioRingBuffer mic_buffer_;
    AudioRingBuffer speaker_buffer_;
    AudioRingBuffer capture_buffer_;

    AudioDeviceIOProcID mic_io_proc_id_{nullptr};
    AudioDeviceIOProcID speaker_io_proc_id_{nullptr};
    AudioObjectID mic_device_{kAudioObjectUnknown};
    AudioObjectID speaker_device_{kAudioObjectUnknown};
    bool running_{false};

    static OSStatus MicIOProc(AudioObjectID inDevice,
                              const AudioTimeStamp* inNow,
                              const AudioBufferList* inInputData,
                              const AudioTimeStamp* inInputTime,
                              AudioBufferList* outOutputData,
                              const AudioTimeStamp* inOutputTime,
                              void* inClientData);

    static OSStatus SpeakerIOProc(AudioObjectID inDevice,
                                  const AudioTimeStamp* inNow,
                                  const AudioBufferList* inInputData,
                                  const AudioTimeStamp* inInputTime,
                                  AudioBufferList* outOutputData,
                                  const AudioTimeStamp* inOutputTime,
                                  void* inClientData);
};

AudioObjectID GetDefaultInputDevice();
AudioObjectID GetDefaultOutputDevice();
Float64 GetDeviceSampleRate(AudioObjectID deviceID);
bool MatchDeviceSampleRate(AudioObjectID deviceID, Float64 targetRate);

} // namespace TwoBrainRec