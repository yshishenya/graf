#ifndef GRAF_AEC3_H
#define GRAF_AEC3_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    GRAF_AEC3_SAMPLE_RATE = 48000,
    GRAF_AEC3_CHANNEL_COUNT = 1,
    GRAF_AEC3_FRAME_SAMPLES = 480
};

typedef enum GrafAEC3Status {
    GRAF_AEC3_OK = 0,
    GRAF_AEC3_INVALID_ARGUMENT = 1,
    GRAF_AEC3_CREATION_FAILED = 2,
    GRAF_AEC3_RENDER_FAILED = 3,
    GRAF_AEC3_CAPTURE_FAILED = 4,
    GRAF_AEC3_CLOSED = 5,
    GRAF_AEC3_INTERNAL_ERROR = 6
} GrafAEC3Status;

typedef struct GrafAEC3Statistics {
    int32_t has_delay_ms;
    int32_t delay_ms;
    int32_t has_echo_return_loss_db;
    double echo_return_loss_db;
    int32_t has_echo_return_loss_enhancement_db;
    double echo_return_loss_enhancement_db;
} GrafAEC3Statistics;

typedef struct GrafAEC3Processor GrafAEC3Processor;

GrafAEC3Processor *graf_aec3_create(void);

GrafAEC3Status graf_aec3_process(
    GrafAEC3Processor *processor,
    const float *render_samples,
    const float *capture_samples,
    uint32_t frame_samples,
    int32_t stream_delay_ms,
    float *cleaned_capture_samples
);

GrafAEC3Status graf_aec3_get_statistics(
    GrafAEC3Processor *processor,
    GrafAEC3Statistics *statistics
);

void graf_aec3_destroy(GrafAEC3Processor *processor);

const char *graf_aec3_library_version(void);
const char *graf_aec3_source_commit(void);
int32_t graf_aec3_optional_processing_enabled(void);

#ifdef __cplusplus
}
#endif

#endif
