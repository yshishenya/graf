#pragma once

#include "../Storage/AtomicFileStore.h"

#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <string_view>

namespace graf::windows {
class WebViewRoutePolicy;

// F273/F200: data from an untrusted protocol activation, never account authority.
// Times are UTC Unix seconds supplied by the caller (not by URI parameters).
struct ProductAttributionHandoff {
    static constexpr std::int64_t validitySeconds = 90LL * 24 * 60 * 60;
    static constexpr std::size_t maximumLinkBytes = 16 * 1024;
    static constexpr std::size_t maximumLabelBytes = 96;

    std::optional<std::string> bridgeID;
    std::map<std::string, std::string> campaign;
    std::optional<std::string> landingPath;
    bool fallbackRecovered = false;
    std::int64_t receivedAt = 0;

    // Scheme/host select the handler. Other URI components grant no navigation
    // or native capability. First query occurrence wins, including invalid/empty.
    [[nodiscard]] static std::optional<ProductAttributionHandoff> parse(
        std::string_view link, std::int64_t receivedAt);
    [[nodiscard]] bool isExpired(std::int64_t now) const noexcept;
    [[nodiscard]] bool campaignKnown() const noexcept { return !campaign.empty(); }
    [[nodiscard]] std::string_view reliability(bool accountConnected) const noexcept;
};

enum class AttributionStoreError { none, rejected, ioError, invalidData, tooLarge };

struct AttributionStoreRead {
    std::optional<ProductAttributionHandoff> handoff;
    std::optional<std::int64_t> accountConnectedAt;
    AttributionStoreError error = AttributionStoreError::none;
};

// One application-instance owner must serialize calls. Reads always consult disk;
// there is no stale in-memory copy and no multi-process read/modify/write promise.
// The caller supplies a fixed app-data path, never a path from an activation.
class ProductAttributionHandoffStore final {
public:
    static constexpr std::size_t maximumBytes = 4096;
    using Writer = AtomicFileResult (*)(const std::filesystem::path&, std::string_view, std::size_t);

    explicit ProductAttributionHandoffStore(std::filesystem::path path,
        Writer writer = &AtomicFileStore::write);

    [[nodiscard]] AttributionStoreRead current(std::int64_t now) const;
    [[nodiscard]] AttributionStoreError saveLink(std::string_view link, std::int64_t receivedAt);
    [[nodiscard]] AttributionStoreError save(const ProductAttributionHandoff& handoff);
    [[nodiscard]] AttributionStoreError markAccountConnected(std::int64_t at);
    [[nodiscard]] AttributionStoreError clear();

private:
    [[nodiscard]] AttributionStoreRead read() const;
    [[nodiscard]] AttributionStoreError write(const AttributionStoreRead& state) const;
    std::filesystem::path path_;
    Writer writer_;
};

// Decorates an already validated sign-in URL; the caller owns origin, route and
// next validation. Existing non-attribution query bytes/order are preserved,
// including encoded next. Only names emitted by this handoff replace existing
// occurrences (Mac semantics). With no such collisions, plain remains an exact
// prefix before the appended query items (apart from any trailing fragment).
// Missing/expired handoffs return plain unchanged. This grants no navigation.
[[nodiscard]] std::string applyingSignInQueryItems(
    std::string_view plain, const std::optional<ProductAttributionHandoff>& handoff,
    std::int64_t now);

// One helper for initial login, auth recovery and explicit sign-in. next may be
// a relative path or an absolute cabinet URL; the existing route policy chooses
// a safe GET path, strips query/fragment, and falls back to /desktop/meetings.
// The configured origin is supplied by policy, never by the handoff. This only
// builds a URL: callers retain the normal navigation/nonce/account boundaries.
[[nodiscard]] std::string productAttributionSignInUrl(
    const WebViewRoutePolicy& policy, std::string_view next,
    const std::optional<ProductAttributionHandoff>& handoff, std::int64_t now);

} // namespace graf::windows
