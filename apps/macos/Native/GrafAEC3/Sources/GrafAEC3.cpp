#include "GrafAEC3.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <new>

#include "api/audio/audio_processing.h"

struct GrafAEC3Processor {
    rtc::scoped_refptr<webrtc::AudioProcessing> audio_processing;
    bool closed = false;
};

namespace {

constexpr char kLibraryVersion[] = "2.1";
constexpr char kSourceCommit[] = "846fe90a289f58b7c9303a635142aa2c7caa93e5";

bool IsValidFrame(const float *samples, uint32_t frame_samples) {
    if (samples == nullptr || frame_samples != GRAF_AEC3_FRAME_SAMPLES) {
        return false;
    }
    for (uint32_t index = 0; index < frame_samples; ++index) {
        if (!std::isfinite(samples[index]) || samples[index] < -1.0f || samples[index] > 1.0f) {
            return false;
        }
    }
    return true;
}

}  // namespace

GrafAEC3Processor *graf_aec3_create(void) {
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

        auto audio_processing = webrtc::AudioProcessingBuilder().SetConfig(config).Create();
        if (audio_processing == nullptr || audio_processing->Initialize() != webrtc::AudioProcessing::kNoError) {
            return nullptr;
        }
        auto *processor = new (std::nothrow) GrafAEC3Processor;
        if (processor == nullptr) {
            return nullptr;
        }
        processor->audio_processing = std::move(audio_processing);
        return processor;
    } catch (...) {
        return nullptr;
    }
}

GrafAEC3Status graf_aec3_process(
    GrafAEC3Processor *processor,
    const float *render_samples,
    const float *capture_samples,
    uint32_t frame_samples,
    int32_t stream_delay_ms,
    float *cleaned_capture_samples
) {
    if (cleaned_capture_samples != nullptr && frame_samples == GRAF_AEC3_FRAME_SAMPLES) {
        std::fill_n(cleaned_capture_samples, GRAF_AEC3_FRAME_SAMPLES, 0.0f);
    }
    if (processor == nullptr || cleaned_capture_samples == nullptr ||
        !IsValidFrame(render_samples, frame_samples) ||
        !IsValidFrame(capture_samples, frame_samples) ||
        stream_delay_ms < 0 || stream_delay_ms > 500) {
        return GRAF_AEC3_INVALID_ARGUMENT;
    }
    if (processor->closed || processor->audio_processing == nullptr) {
        return GRAF_AEC3_CLOSED;
    }

    try {
        const webrtc::StreamConfig stream_config(GRAF_AEC3_SAMPLE_RATE, GRAF_AEC3_CHANNEL_COUNT);
        std::array<float, GRAF_AEC3_FRAME_SAMPLES> render_copy;
        std::copy_n(render_samples, frame_samples, render_copy.begin());
        const float *render_input[] = {render_copy.data()};
        float *render_output[] = {render_copy.data()};
        if (processor->audio_processing->ProcessReverseStream(
                render_input, stream_config, stream_config, render_output) !=
            webrtc::AudioProcessing::kNoError) {
            processor->closed = true;
            return GRAF_AEC3_RENDER_FAILED;
        }
        if (processor->audio_processing->set_stream_delay_ms(stream_delay_ms) !=
            webrtc::AudioProcessing::kNoError) {
            processor->closed = true;
            return GRAF_AEC3_CAPTURE_FAILED;
        }
        const float *capture_input[] = {capture_samples};
        float *capture_output[] = {cleaned_capture_samples};
        if (processor->audio_processing->ProcessStream(
                capture_input, stream_config, stream_config, capture_output) !=
            webrtc::AudioProcessing::kNoError) {
            std::fill_n(cleaned_capture_samples, frame_samples, 0.0f);
            processor->closed = true;
            return GRAF_AEC3_CAPTURE_FAILED;
        }
        return GRAF_AEC3_OK;
    } catch (...) {
        std::fill_n(cleaned_capture_samples, frame_samples, 0.0f);
        processor->closed = true;
        return GRAF_AEC3_INTERNAL_ERROR;
    }
}

GrafAEC3Status graf_aec3_get_statistics(
    GrafAEC3Processor *processor,
    GrafAEC3Statistics *statistics
) {
    if (processor == nullptr || statistics == nullptr) {
        return GRAF_AEC3_INVALID_ARGUMENT;
    }
    *statistics = {};
    if (processor->closed || processor->audio_processing == nullptr) {
        return GRAF_AEC3_CLOSED;
    }
    try {
        const auto values = processor->audio_processing->GetStatistics();
        if (values.delay_ms.has_value()) {
            statistics->has_delay_ms = 1;
            statistics->delay_ms = *values.delay_ms;
        }
        if (values.echo_return_loss.has_value() && std::isfinite(*values.echo_return_loss)) {
            statistics->has_echo_return_loss_db = 1;
            statistics->echo_return_loss_db = *values.echo_return_loss;
        }
        if (values.echo_return_loss_enhancement.has_value() &&
            std::isfinite(*values.echo_return_loss_enhancement)) {
            statistics->has_echo_return_loss_enhancement_db = 1;
            statistics->echo_return_loss_enhancement_db = *values.echo_return_loss_enhancement;
        }
        return GRAF_AEC3_OK;
    } catch (...) {
        return GRAF_AEC3_INTERNAL_ERROR;
    }
}

void graf_aec3_destroy(GrafAEC3Processor *processor) {
    delete processor;
}

const char *graf_aec3_library_version(void) {
    return kLibraryVersion;
}

const char *graf_aec3_source_commit(void) {
    return kSourceCommit;
}

int32_t graf_aec3_optional_processing_enabled(void) {
    return 0;
}
