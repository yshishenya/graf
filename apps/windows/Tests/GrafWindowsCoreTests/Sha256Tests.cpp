#include "../../RecApp/Storage/Sha256.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <algorithm>
#include <array>
#include <cstring>
#include <filesystem>
#include <sstream>
#include <streambuf>
#include <string>
#include <utility>

namespace {
// Generate bytes only when requested; do not allocate the whole synthetic file.
class GeneratedBytes final : public std::streambuf {
public:
    explicit GeneratedBytes(std::size_t size, bool failAfterFirstRead = false)
        : remaining_(size), failAfterFirstRead_(failAfterFirstRead) {}
    std::size_t reads = 0;
private:
    std::size_t remaining_;
    bool failAfterFirstRead_;
    std::streamsize xsgetn(char* destination, std::streamsize requested) override {
        assert(requested > 0 && requested <= 64 * 1024);
        if (failAfterFirstRead_ && reads != 0) throw std::ios_base::failure("synthetic read failure");
        ++reads;
        const auto count = std::min(remaining_, static_cast<std::size_t>(requested));
        std::memset(destination, 'a', count);
        remaining_ -= count;
        return static_cast<std::streamsize>(count);
    }
};
}

int main() {
    using namespace graf::windows;
    // A directory is not an empty readable file, even if ifstream opens it.
    assert(sha256File(std::filesystem::temp_directory_path()).empty());
    assert(sha256("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    assert(sha256("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    assert(sha256(std::string(1'000'000, 'a')) ==
           "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
    const std::array<std::pair<std::size_t, const char*>, 7> boundaries = {{
        {55, "9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318"},
        {56, "b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a"},
        {63, "7d3e74a05d7db15bce4ad9ec0658ea98e3f06eeecf16b4c6fff2da457ddc2f34"},
        {64, "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb"},
        {65, "635361c48bb9eab14198e76ea8ab7f1a41685d6ad62aa9146d301d4f17eb0ae0"},
        {65536, "bf718b6f653bebc184e1479f1935b8da974d701b893afcf49e701f3e2f9f9c5a"},
        {65537, "008ffc88d3c96a9f307524eb361e47c5222a887fc45fa0c1fb8d429c5c23b430"},
    }};
    for (const auto& [length, expected] : boundaries) {
        const std::string bytes(length, 'a');
        assert(sha256(bytes) == expected);
        const auto digest = sha256Digest(bytes);
        std::string hex;
        for (const auto byte : digest) {
            hex += "0123456789abcdef"[byte >> 4];
            hex += "0123456789abcdef"[byte & 15];
        }
        assert(hex == expected);
        std::istringstream input(bytes);
        assert(sha256Stream(input) == expected);
        std::istringstream throwing(bytes);
        throwing.exceptions(std::ios::badbit | std::ios::failbit);
        assert(sha256Stream(throwing) == expected);
    }
    std::istringstream empty;
    assert(sha256Stream(empty) == sha256(""));
    std::istringstream cursor("prefixabc");
    cursor.seekg(6);
    assert(sha256Stream(cursor) == sha256("abc"));
    std::istringstream binary(std::string("a\0b", 3));
    assert(sha256Stream(binary) == sha256(std::string_view("a\0b", 3)));
    std::istringstream failed("abc");
    failed.setstate(std::ios::failbit);
    assert(sha256Stream(failed).empty());
    for (const bool exceptions : {false, true}) {
        GeneratedBytes faulty(128 * 1024, true);
        std::istream input(&faulty);
        if (exceptions) input.exceptions(std::ios::badbit | std::ios::failbit);
        assert(sha256Stream(input).empty()); // Never return the successfully read 64KiB prefix hash.
        assert(faulty.reads == 1);
    }
    GeneratedBytes large(64 * 1024 * 1024 + 5);
    std::istream input(&large);
    assert(sha256Stream(input) == "490ccf096fcee078cad8671d5323fa4640e85b5d57fc75781fd76b5ff034d3e2");
    assert(large.reads == 1025);
}
