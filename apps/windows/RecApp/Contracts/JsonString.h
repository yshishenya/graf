#pragma once

#include <cstddef>
#include <optional>
#include <string_view>

namespace graf::windows::json_detail {
// Shared existing calendar traversal. Emits decoded UTF-8 bytes; the caller
// owns allocation, bounds and wiping. No DOM, retained views or normalization.
template<class Emit> bool decodeString(std::string_view raw, std::size_t maxRawBytes, bool allowNul, Emit emit) {
    if (raw.size() < 2 || raw.front() != '"' || raw.back() != '"' || raw.size() > maxRawBytes) return false;
    const auto append = [&](unsigned cp) {
        if (cp < 0x80) emit(static_cast<char>(cp));
        else if (cp < 0x800) { emit(static_cast<char>(0xc0 | (cp >> 6))); emit(static_cast<char>(0x80 | (cp & 63))); }
        else if (cp < 0x10000) {
            emit(static_cast<char>(0xe0 | (cp >> 12))); emit(static_cast<char>(0x80 | ((cp >> 6) & 63)));
            emit(static_cast<char>(0x80 | (cp & 63)));
        } else {
            emit(static_cast<char>(0xf0 | (cp >> 18))); emit(static_cast<char>(0x80 | ((cp >> 12) & 63)));
            emit(static_cast<char>(0x80 | ((cp >> 6) & 63))); emit(static_cast<char>(0x80 | (cp & 63)));
        }
    };
    const auto hex = [&](std::size_t& i) -> std::optional<unsigned> {
        unsigned cp = 0;
        for (int n = 0; n < 4; ++n) {
            if (++i >= raw.size() - 1) return std::nullopt;
            char c = raw[i];
            if (c >= '0' && c <= '9') cp = cp * 16 + (c - '0');
            else if (c >= 'a' && c <= 'f') cp = cp * 16 + (c - 'a' + 10);
            else if (c >= 'A' && c <= 'F') cp = cp * 16 + (c - 'A' + 10);
            else return std::nullopt;
        }
        return cp;
    };
    for (std::size_t i = 1; i < raw.size() - 1; ++i) {
        auto c = raw[i];
        if (c != '\\') {
            if (static_cast<unsigned char>(c) < 0x20 || c == '"') return false;
            unsigned cp = static_cast<unsigned char>(c), count = 0, minimum = 0;
            if (cp >= 0xf0 && cp <= 0xf4) { cp &= 7; count = 3; minimum = 0x10000; }
            else if (cp >= 0xe0 && cp <= 0xef) { cp &= 15; count = 2; minimum = 0x800; }
            else if (cp >= 0xc2 && cp <= 0xdf) { cp &= 31; count = 1; minimum = 0x80; }
            else if (cp >= 0x80) return false;
            while (count--) {
                if (++i >= raw.size() - 1) return false;
                const auto next = static_cast<unsigned char>(raw[i]);
                if ((next & 0xc0) != 0x80) return false;
                cp = (cp << 6) | (next & 63);
            }
            if (cp < minimum || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) return false;
            append(cp); continue;
        }
        if (++i >= raw.size() - 1) return false;
        switch (raw[i]) {
        case '"': emit('"'); break;
        case '\\': emit('\\'); break;
        case '/': emit('/'); break;
        case 'n': emit('\n'); break;
        case 'r': emit('\r'); break;
        case 't': emit('\t'); break;
        case 'b': emit('\b'); break;
        case 'f': emit('\f'); break;
        case 'u': {
            auto cp = hex(i); if (!cp) return false;
            if (*cp >= 0xd800 && *cp <= 0xdbff) {
                if (i + 2 >= raw.size() - 1 || raw[++i] != '\\' || raw[++i] != 'u') return false;
                const auto low = hex(i);
                if (!low || *low < 0xdc00 || *low > 0xdfff) return false;
                *cp = 0x10000 + ((*cp - 0xd800) << 10) + *low - 0xdc00;
            } else if (*cp >= 0xdc00 && *cp <= 0xdfff) return false;
            if (*cp == 0 && !allowNul) return false;
            append(*cp); break;
        }
        default: return false;
        }
    }
    return true;
}
} // namespace graf::windows::json_detail
