#pragma once

#include "../../RecApp/Audio/RecordingAudioTimeline.h"

#include <memory>

namespace graf::windows {

class GrafAEC3WebRtcAdapter final : public IAec3Processor {
public:
    [[nodiscard]] static std::unique_ptr<GrafAEC3WebRtcAdapter> create();

    ~GrafAEC3WebRtcAdapter() override;

    GrafAEC3WebRtcAdapter(const GrafAEC3WebRtcAdapter&) = delete;
    GrafAEC3WebRtcAdapter& operator=(const GrafAEC3WebRtcAdapter&) = delete;

    [[nodiscard]] bool ready() const noexcept;
    [[nodiscard]] bool process(const float* renderReference,
                               const float* microphone,
                               float* cleanedMicrophone) noexcept override;

private:
    GrafAEC3WebRtcAdapter();
    [[nodiscard]] bool initialize() noexcept;

    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace graf::windows
