#include "Sha256.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>

#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#endif

namespace graf::windows {
namespace {

constexpr std::array<std::uint32_t, 64> kRoundConstants = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
};

constexpr std::array<std::uint32_t, 8> kInitial = {
    0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19,
};

constexpr std::uint32_t rotateRight(std::uint32_t value, std::uint32_t count) noexcept {
    return (value >> count) | (value << (32 - count));
}

std::string hexDigest(const std::array<std::uint8_t, 32>& bytes) {
    constexpr char digits[] = "0123456789abcdef";
    std::string result;
    result.reserve(64);
    for (const auto byte : bytes) {
        result += digits[byte >> 4];
        result += digits[byte & 15];
    }
    return result;
}

// Preserve the existing provider-independent digest for in-memory identity callers.
class PortableHash {
public:
    bool update(std::string_view bytes) {
        if (bytes.size() > std::numeric_limits<std::uint64_t>::max() / 8 - total_) return false;
        total_ += bytes.size();
        while (!bytes.empty()) {
            const auto count = std::min(bytes.size(), buffer_.size() - used_);
            std::memcpy(buffer_.data() + used_, bytes.data(), count);
            used_ += count;
            bytes.remove_prefix(count);
            if (used_ == buffer_.size()) {
                compress(buffer_.data());
                used_ = 0;
            }
        }
        return true;
    }

    std::string finish() {
        std::array<std::uint8_t, 32> digest{};
        buffer_[used_++] = 0x80;
        if (used_ > 56) {
            std::fill(buffer_.begin() + used_, buffer_.end(), std::uint8_t{0});
            compress(buffer_.data());
            used_ = 0;
        }
        std::fill(buffer_.begin() + used_, buffer_.begin() + 56, std::uint8_t{0});
        const auto bitLength = total_ * 8;
        for (std::size_t index = 0; index < 8; ++index)
            buffer_[56 + index] = static_cast<std::uint8_t>(bitLength >> (56 - index * 8));
        compress(buffer_.data());
        for (std::size_t index = 0; index < digest.size(); ++index)
            digest[index] = static_cast<std::uint8_t>(hash_[index / 4] >> (24 - (index % 4) * 8));
        return hexDigest(digest);
    }

private:
    std::array<std::uint32_t, 8> hash_ = kInitial;
    std::array<std::uint8_t, 64> buffer_{};
    std::size_t used_ = 0;
    std::uint64_t total_ = 0;

    void compress(const std::uint8_t* data) {
        std::array<std::uint32_t, 64> words{};
        for (std::size_t index = 0; index < 16; ++index) {
            const auto base = index * 4;
            words[index] = (static_cast<std::uint32_t>(data[base]) << 24) |
                (static_cast<std::uint32_t>(data[base + 1]) << 16) |
                (static_cast<std::uint32_t>(data[base + 2]) << 8) | data[base + 3];
        }
        for (std::size_t index = 16; index < words.size(); ++index) {
            const auto s0 = rotateRight(words[index - 15], 7) ^ rotateRight(words[index - 15], 18) ^ (words[index - 15] >> 3);
            const auto s1 = rotateRight(words[index - 2], 17) ^ rotateRight(words[index - 2], 19) ^ (words[index - 2] >> 10);
            words[index] = words[index - 16] + s0 + words[index - 7] + s1;
        }
        auto a = hash_[0], b = hash_[1], c = hash_[2], d = hash_[3];
        auto e = hash_[4], f = hash_[5], g = hash_[6], h = hash_[7];
        for (std::size_t index = 0; index < words.size(); ++index) {
            const auto s1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
            const auto choose = (e & f) ^ ((~e) & g);
            const auto temp1 = h + s1 + choose + kRoundConstants[index] + words[index];
            const auto s0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
            const auto majority = (a & b) ^ (a & c) ^ (b & c);
            const auto temp2 = s0 + majority;
            h = g; g = f; f = e; e = d + temp1; d = c; c = b; b = a; a = temp1 + temp2;
        }
        hash_[0] += a; hash_[1] += b; hash_[2] += c; hash_[3] += d;
        hash_[4] += e; hash_[5] += f; hash_[6] += g; hash_[7] += h;
    }
};

#ifdef _WIN32
class NativeHash {
public:
    NativeHash() {
        ready_ = BCryptCreateHash(BCRYPT_SHA256_ALG_HANDLE, &hash_, nullptr, 0, nullptr, 0, 0) >= 0;
    }
    ~NativeHash() {
        if (hash_) BCryptDestroyHash(hash_);
    }
    NativeHash(const NativeHash&) = delete;
    NativeHash& operator=(const NativeHash&) = delete;
    bool update(std::string_view bytes) {
        if (!ready_) return false;
        while (!bytes.empty()) {
            const auto count = std::min(bytes.size(), std::size_t(64 * 1024));
            if (BCryptHashData(hash_, reinterpret_cast<PUCHAR>(const_cast<char*>(bytes.data())),
                               static_cast<ULONG>(count), 0) < 0) return false;
            bytes.remove_prefix(count);
        }
        return true;
    }
    std::string finish() {
        std::array<std::uint8_t, 32> digest{};
        if (!ready_ || BCryptFinishHash(hash_, digest.data(), static_cast<ULONG>(digest.size()), 0) < 0)
            return {};
        return hexDigest(digest);
    }
private:
    BCRYPT_HASH_HANDLE hash_ = nullptr;
    bool ready_ = false;
};
#endif

} // namespace

std::string sha256(std::string_view bytes) {
    PortableHash hash;
    if (!hash.update(bytes)) throw std::length_error("SHA-256 input too large");
    return hash.finish();
}

std::string sha256Stream(std::istream& input) {
    if (!input.good()) return {};
#ifdef _WIN32
    NativeHash hash;
#else
    PortableHash hash;
#endif
    std::array<char, 64 * 1024> buffer{};
    for (;;) {
        try {
            input.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        } catch (...) {
            // EOF can throw with failbit exceptions enabled; a failed read cannot be hashed.
            if (input.bad() || !input.eof()) return {};
        }
        if (input.bad() || (input.fail() && !input.eof())) return {};
        const auto count = input.gcount();
        if (count < 0 || count > static_cast<std::streamsize>(buffer.size()) ||
            !hash.update(std::string_view(buffer.data(), static_cast<std::size_t>(count)))) return {};
        if (input.eof()) return hash.finish();
    }
}

std::string sha256File(const std::filesystem::path& path) {
    std::error_code error;
    if (!std::filesystem::is_regular_file(path, error) || error) return {};
    std::ifstream input(path, std::ios::binary);
    if (!input) return {};
    return sha256Stream(input);
}

} // namespace graf::windows
