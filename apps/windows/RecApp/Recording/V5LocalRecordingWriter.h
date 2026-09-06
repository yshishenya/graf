#pragma once

#include "../Audio/RecordingAudioTimeline.h"
#include "../Contracts/WindowsDesktopContracts.h"

#include <cstdint>
#include <filesystem>
#include <functional>
#include <fstream>
#include <string>

namespace graf::windows {

enum class V5WriterError {
    none,
    storageUnavailable,
    emptyRecording,
    aacEncoderUnavailable,
    encodeFailed,
    integrityFailed,
};

struct V5WriterResult {
    V5WriterError error = V5WriterError::none;
    std::filesystem::path packageDirectory;
    std::filesystem::path manifestPath;
    std::filesystem::path wavPath;
    std::filesystem::path playbackPath;
    std::uint64_t durationMs = 0;
    std::uint64_t wavBytes = 0;
    std::uint64_t playbackBytes = 0;
    std::string wavSha256;
    std::string playbackSha256;
    ReasonCode captureFailure = ReasonCode::none;
    bool trustedPrefixRetained = false;

    [[nodiscard]] bool ok() const noexcept { return error == V5WriterError::none; }
    [[nodiscard]] bool normalPackage() const noexcept { return ok() && captureFailure == ReasonCode::none; }
};

using PlaybackEncoder = std::function<bool(
    const std::filesystem::path& outputPath,
    const std::filesystem::path& canonicalFloatPath,
    std::uint64_t frameCount)>;

class V5LocalRecordingWriter final {
public:
    V5LocalRecordingWriter(std::filesystem::path packageDirectory, PlaybackEncoder encoder = {});
    V5LocalRecordingWriter(
        std::filesystem::path custodyRoot,
        std::filesystem::path packageDirectory,
        PlaybackEncoder encoder = {});
    ~V5LocalRecordingWriter();

    V5LocalRecordingWriter(const V5LocalRecordingWriter&) = delete;
    V5LocalRecordingWriter& operator=(const V5LocalRecordingWriter&) = delete;

    [[nodiscard]] bool append(const CanonicalAudioFrame& frame);
    [[nodiscard]] V5WriterResult finalize(ReasonCode captureFailure = ReasonCode::none);

    [[nodiscard]] std::uint64_t frameCount() const noexcept { return frameCount_; }

private:
    [[nodiscard]] bool openIfNeeded();
    [[nodiscard]] bool closeCanonical();
    void retainPrefix(V5WriterResult& result);
    [[nodiscard]] bool writeWav(const std::filesystem::path& path, std::uint64_t* byteCount);
    [[nodiscard]] bool writePlayback(const std::filesystem::path& path);
    [[nodiscard]] std::string manifestJson(const V5WriterResult& result) const;
    [[nodiscard]] static std::int16_t toPcm16(float value) noexcept;

    std::filesystem::path packageDirectory_;
    std::filesystem::path custodyRoot_;
    std::filesystem::path canonicalFloatPath_;
    PlaybackEncoder encoder_;
    std::ofstream canonicalOutput_;
    std::uint64_t frameCount_ = 0;
    bool finalized_ = false;
    V5WriterError appendError_ = V5WriterError::none;
    V5WriterResult result_;
};

} // namespace graf::windows
