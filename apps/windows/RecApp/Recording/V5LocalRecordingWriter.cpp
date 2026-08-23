#include "V5LocalRecordingWriter.h"

#include "../Storage/AtomicFileStore.h"
#include "../Storage/Sha256.h"
#include "../Contracts/WindowsDesktopContracts.h"

#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <memory>

#ifdef _WIN32
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <wrl/client.h>
#include <windows.h>
#endif

namespace graf::windows {
namespace {

void writeU16(std::ostream& output, std::uint16_t value) {
    output.put(static_cast<char>(value & 0xff)); output.put(static_cast<char>((value >> 8) & 0xff));
}
void writeU32(std::ostream& output, std::uint32_t value) {
    for (int shift = 0; shift < 32; shift += 8) output.put(static_cast<char>((value >> shift) & 0xff));
}

std::uint64_t fileSize(const std::filesystem::path& path) {
    std::error_code error;
    const auto size = std::filesystem::file_size(path, error);
    return error ? 0 : size;
}

#ifdef _WIN32
bool encodeMediaFoundationAac(const std::filesystem::path& outputPath,
                              const std::filesystem::path& canonicalPath,
                              std::uint64_t frameCount) {
    if (FAILED(MFStartup(MF_VERSION))) return false;
    const bool coInitialized = SUCCEEDED(CoInitializeEx(nullptr, COINIT_MULTITHREADED));
    bool success = false;
    do {
        Microsoft::WRL::ComPtr<IMFSinkWriter> writer;
        if (FAILED(MFCreateSinkWriterFromURL(outputPath.wstring().c_str(), nullptr, nullptr, &writer))) break;
        Microsoft::WRL::ComPtr<IMFMediaType> outputType;
        if (FAILED(MFCreateMediaType(&outputType))) break;
        if (FAILED(outputType->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio)) ||
            FAILED(outputType->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_AAC)) ||
            FAILED(outputType->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS, 1)) ||
            FAILED(outputType->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND, 48'000)) ||
            FAILED(outputType->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE, 16)) ||
            FAILED(outputType->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND, 12'000))) break;
        DWORD streamIndex = 0;
        if (FAILED(writer->AddStream(outputType.Get(), &streamIndex))) break;
        Microsoft::WRL::ComPtr<IMFMediaType> inputType;
        if (FAILED(MFCreateMediaType(&inputType))) break;
        if (FAILED(inputType->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio)) ||
            FAILED(inputType->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_PCM)) ||
            FAILED(inputType->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS, 1)) ||
            FAILED(inputType->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND, 48'000)) ||
            FAILED(inputType->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE, 16)) ||
            FAILED(inputType->SetUINT32(MF_MT_AUDIO_BLOCK_ALIGNMENT, 2)) ||
            FAILED(inputType->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND, 96'000)) ||
            FAILED(writer->SetInputMediaType(streamIndex, inputType.Get(), nullptr)) ||
            FAILED(writer->BeginWriting())) break;
        std::ifstream input(canonicalPath, std::ios::binary);
        if (!input) break;
        std::array<float, 480> frame{};
        for (std::uint64_t index = 0; index < frameCount; ++index) {
            input.read(reinterpret_cast<char*>(frame.data()), static_cast<std::streamsize>(frame.size() * sizeof(float)));
            if (!input) break;
            Microsoft::WRL::ComPtr<IMFMediaBuffer> buffer;
            Microsoft::WRL::ComPtr<IMFSample> sample;
            if (FAILED(MFCreateMemoryBuffer(static_cast<DWORD>(frame.size() * sizeof(std::int16_t)), &buffer)) ||
                FAILED(MFCreateSample(&sample))) break;
            BYTE* destination = nullptr; DWORD maxLength = 0; DWORD currentLength = 0;
            if (FAILED(buffer->Lock(&destination, &maxLength, &currentLength))) break;
            for (std::size_t sampleIndex = 0; sampleIndex < frame.size(); ++sampleIndex) {
                const auto clamped = std::max(-1.0F, std::min(1.0F, frame[sampleIndex]));
                reinterpret_cast<std::int16_t*>(destination)[sampleIndex] = static_cast<std::int16_t>(clamped * 32767.0F);
            }
            buffer->Unlock();
            if (FAILED(buffer->SetCurrentLength(static_cast<DWORD>(frame.size() * sizeof(std::int16_t)))) ||
                FAILED(sample->AddBuffer(buffer.Get())) ||
                FAILED(sample->SetSampleTime(static_cast<LONGLONG>(index * 100'000))) ||
                FAILED(sample->SetSampleDuration(100'000)) || FAILED(writer->WriteSample(streamIndex, sample.Get()))) break;
            if (index + 1 == frameCount) success = true;
        }
        if (success && FAILED(writer->Finalize())) success = false;
    } while (false);
    if (coInitialized) CoUninitialize();
    MFShutdown();
    return success;
}
#endif

} // namespace

V5LocalRecordingWriter::V5LocalRecordingWriter(std::filesystem::path packageDirectory, PlaybackEncoder encoder)
    : packageDirectory_(std::move(packageDirectory)),
      custodyRoot_(packageDirectory_.parent_path()),
      canonicalFloatPath_(packageDirectory_ / ".canonical-mix.f32.tmp"),
      encoder_(std::move(encoder)) {
#ifdef _WIN32
    if (!encoder_) encoder_ = encodeMediaFoundationAac;
#endif
}

V5LocalRecordingWriter::V5LocalRecordingWriter(
    std::filesystem::path custodyRoot,
    std::filesystem::path packageDirectory,
    PlaybackEncoder encoder)
    : packageDirectory_(std::move(packageDirectory)),
      custodyRoot_(std::move(custodyRoot)),
      canonicalFloatPath_(packageDirectory_ / ".canonical-mix.f32.tmp"),
      encoder_(std::move(encoder)) {
#ifdef _WIN32
    if (!encoder_) encoder_ = encodeMediaFoundationAac;
#endif
}

V5LocalRecordingWriter::~V5LocalRecordingWriter() { abort(); }

bool V5LocalRecordingWriter::openIfNeeded() {
    if (canonicalOutput_ != nullptr) return true;
    if (!AtomicFileStore::isWithinRoot(custodyRoot_, packageDirectory_)) return false;
    std::error_code error;
    std::filesystem::create_directories(packageDirectory_, error);
    if (error) return false;
    ownedCanonicalOutput_ = std::make_unique<std::ofstream>(canonicalFloatPath_, std::ios::binary | std::ios::trunc);
    if (!ownedCanonicalOutput_->is_open()) return false;
    canonicalOutput_ = ownedCanonicalOutput_.get();
    return true;
}

bool V5LocalRecordingWriter::append(const CanonicalAudioFrame& frame) {
    if (finalized_ || !openIfNeeded()) return false;
    canonicalOutput_->write(reinterpret_cast<const char*>(frame.mixed.data()),
                            static_cast<std::streamsize>(frame.mixed.size() * sizeof(float)));
    if (!canonicalOutput_->good()) return false;
    ++frameCount_;
    return true;
}

bool V5LocalRecordingWriter::writeWav(const std::filesystem::path& path, std::uint64_t* byteCount) {
    std::ifstream input(canonicalFloatPath_, std::ios::binary);
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!input || !output) return false;
    const auto samples48k = frameCount_ * 480;
    const auto samples16k = samples48k / 3;
    const auto dataBytes = samples16k * sizeof(std::int16_t);
    output.write("RIFF", 4); writeU32(output, static_cast<std::uint32_t>(36 + dataBytes)); output.write("WAVE", 4);
    output.write("fmt ", 4); writeU32(output, 16); writeU16(output, 1); writeU16(output, 1);
    writeU32(output, 16'000); writeU32(output, 16'000 * 2); writeU16(output, 2); writeU16(output, 16);
    output.write("data", 4); writeU32(output, static_cast<std::uint32_t>(dataBytes));
    std::array<float, 480> frame{};
    for (std::uint64_t frameIndex = 0; frameIndex < frameCount_; ++frameIndex) {
        input.read(reinterpret_cast<char*>(frame.data()), static_cast<std::streamsize>(frame.size() * sizeof(float)));
        if (!input) return false;
        for (std::size_t index = 0; index < frame.size(); index += 3) {
            const float average = (frame[index] + frame[index + 1] + frame[index + 2]) / 3.0F;
            writeU16(output, static_cast<std::uint16_t>(toPcm16(average)));
        }
    }
    output.flush();
    if (!output.good()) return false;
    const auto size = fileSize(path);
    if (byteCount != nullptr) *byteCount = size;
    return size != 0;
}

bool V5LocalRecordingWriter::writePlayback(const std::filesystem::path& path) {
    if (encoder_) return encoder_(path, canonicalFloatPath_, frameCount_);
#ifndef _WIN32
    return false;
#else
    return false;
#endif
}

std::string V5LocalRecordingWriter::manifestJson(const V5WriterResult& result) const {
    return std::string("{\"schema_version\":\"") + std::string(kManifestSchemaVersion) +
        "\",\"canonical_mix_profile\":\"" + std::string(kCanonicalMixProfile) +
        "\",\"source_kind\":\"" + std::string(kV5SourceKind) +
        "\",\"media_scribe_source_mode\":\"" + std::string(kV5MediaScribeSourceMode) +
        "\",\"duration_ms\":" + std::to_string(result.durationMs) +
        ",\"artifacts\":{\"media\":{\"bytes\":" + std::to_string(result.wavBytes) +
        ",\"sha256\":\"" + result.wavSha256 + "\"},\"playback\":{\"bytes\":" +
        std::to_string(result.playbackBytes) + ",\"sha256\":\"" + result.playbackSha256 + "\"}}}";
}

V5WriterResult V5LocalRecordingWriter::finalize() {
    V5WriterResult result;
    result.packageDirectory = packageDirectory_;
    result.manifestPath = packageDirectory_ / "manifest.json";
    result.wavPath = packageDirectory_ / "meeting-transcription.wav";
    result.playbackPath = packageDirectory_ / "meeting-review.m4a";
    if (finalized_) { result.error = V5WriterError::invalidState; return result; }
    if (canonicalOutput_ == nullptr || frameCount_ == 0) { result.error = V5WriterError::emptyRecording; return result; }
    canonicalOutput_->flush(); canonicalOutput_->close(); canonicalOutput_ = nullptr;
    const auto wavTemp = result.wavPath.string() + ".tmp";
    const auto playbackTemp = result.playbackPath.string() + ".tmp";
    if (!writeWav(wavTemp, &result.wavBytes)) { result.error = V5WriterError::storageUnavailable; return result; }
    std::error_code error;
    std::filesystem::rename(wavTemp, result.wavPath, error);
    if (error || !writePlayback(playbackTemp)) {
        result.error = error ? V5WriterError::storageUnavailable : V5WriterError::aacEncoderUnavailable;
        return result;
    }
    result.playbackBytes = fileSize(playbackTemp);
    if (result.playbackBytes == 0) { result.error = V5WriterError::encodeFailed; return result; }
    std::filesystem::rename(playbackTemp, result.playbackPath, error);
    if (error) { result.error = V5WriterError::storageUnavailable; return result; }
    result.wavBytes = fileSize(result.wavPath);
    result.playbackBytes = fileSize(result.playbackPath);
    result.wavSha256 = sha256File(result.wavPath);
    result.playbackSha256 = sha256File(result.playbackPath);
    result.durationMs = (frameCount_ * 1'000) / 100;
    if (result.wavSha256.empty() || result.playbackSha256.empty() || result.wavBytes == 0 || result.playbackBytes == 0) {
        result.error = V5WriterError::integrityFailed; return result;
    }
    const auto manifest = manifestJson(result);
    if (!AtomicFileStore::writeWithinRoot(custodyRoot_, result.manifestPath, manifest).ok()) {
        result.error = V5WriterError::storageUnavailable;
        return result;
    }
    std::filesystem::remove(canonicalFloatPath_, error);
    finalized_ = true;
    return result;
}

void V5LocalRecordingWriter::abort() noexcept {
    if (canonicalOutput_ != nullptr) canonicalOutput_->close();
    canonicalOutput_ = nullptr;
    ownedCanonicalOutput_.reset();
    std::error_code error;
    if (!finalized_) std::filesystem::remove(canonicalFloatPath_, error);
}

std::int16_t V5LocalRecordingWriter::toPcm16(float value) noexcept {
    const auto clamped = std::max(-1.0F, std::min(1.0F, value));
    return static_cast<std::int16_t>(clamped * 32767.0F);
}

} // namespace graf::windows
