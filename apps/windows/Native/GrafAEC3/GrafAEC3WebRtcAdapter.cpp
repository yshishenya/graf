#include "GrafAEC3WebRtcAdapter.h"

#include <array>
#include <algorithm>

#include <api/audio/audio_processing.h>
#include <api/scoped_refptr.h>

namespace graf::windows {

struct GrafAEC3WebRtcAdapter::Impl {
    rtc::scoped_refptr<webrtc::AudioProcessing> audioProcessing;
    webrtc::StreamConfig stream{48'000, 1};
    bool ready = false;
};

std::unique_ptr<GrafAEC3WebRtcAdapter> GrafAEC3WebRtcAdapter::create() {
    auto result = std::unique_ptr<GrafAEC3WebRtcAdapter>(new GrafAEC3WebRtcAdapter());
    return result->initialize() ? std::move(result) : nullptr;
}

GrafAEC3WebRtcAdapter::GrafAEC3WebRtcAdapter()
    : impl_(std::make_unique<Impl>()) {}

GrafAEC3WebRtcAdapter::~GrafAEC3WebRtcAdapter() = default;

bool GrafAEC3WebRtcAdapter::initialize() noexcept {
    try {
        webrtc::AudioProcessing::Config config;
        config.echo_canceller.enabled = true;
        config.echo_canceller.mobile_mode = false;
        config.echo_canceller.enforce_high_pass_filtering = false;
        config.high_pass_filter.enabled = false;
        config.noise_suppression.enabled = false;
        config.gain_controller1.enabled = false;
        config.gain_controller2.enabled = false;
        config.transient_suppression.enabled = false;
        webrtc::AudioProcessingBuilder builder;
        impl_->audioProcessing = builder.SetConfig(config).Create();
        if (impl_->audioProcessing == nullptr || impl_->audioProcessing->Initialize() != 0) return false;
        // A successful construction is not enough: exercise the exact 10 ms
        // reverse-before-near-end contract before opening the Record gate.
        // process() also protects its public entry point with ready(), so mark
        // the object provisionally ready for this self-check and roll it back
        // if the real reverse/near-end call fails.
        impl_->ready = true;
        std::array<float, 480> render{};
        std::array<float, 480> microphone{};
        std::array<float, 480> cleaned{};
        impl_->ready = process(render.data(), microphone.data(), cleaned.data());
    } catch (...) {
        impl_->ready = false;
    }
    return impl_->ready;
}

bool GrafAEC3WebRtcAdapter::ready() const noexcept {
    return impl_ != nullptr && impl_->ready;
}

bool GrafAEC3WebRtcAdapter::process(const float* renderReference,
                                    const float* microphone,
                                    float* cleanedMicrophone) noexcept {
    if (!ready() || renderReference == nullptr || microphone == nullptr || cleanedMicrophone == nullptr) {
        return false;
    }
    std::array<float, 480> renderCopy{};
    std::copy_n(renderReference, renderCopy.size(), renderCopy.data());
    const float* renderChannels[] = {renderCopy.data()};
    float* renderOutput[] = {renderCopy.data()};
    if (impl_->audioProcessing->ProcessReverseStream(renderChannels, impl_->stream, impl_->stream,
                                                     renderOutput) != 0) {
        return false;
    }
    const float* microphoneChannels[] = {microphone};
    float* cleanedChannels[] = {cleanedMicrophone};
    return impl_->audioProcessing->ProcessStream(microphoneChannels, impl_->stream, impl_->stream,
                                                 cleanedChannels) == 0;
}

} // namespace graf::windows
