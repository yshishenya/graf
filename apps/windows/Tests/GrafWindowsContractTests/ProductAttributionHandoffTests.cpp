#include "../../RecApp/Upload/ProductAttributionHandoff.h"
#include "../../RecApp/Web/WebView2Host.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <limits>

using namespace graf::windows;

namespace {
constexpr std::int64_t now = 1'800'000'000;
constexpr auto link = "grafrec://attribution?bridge=graf_attr_abcdefgh&utm_source=search&utm_campaign=launch&landing_path=%2Fdownload&fallback=yes";

struct Fixture {
    std::filesystem::path root;
    Fixture() {
        const auto seed = std::chrono::steady_clock::now().time_since_epoch().count();
        for (unsigned i = 0; i < 100; ++i) {
            auto candidate = std::filesystem::temp_directory_path() /
                ("graf-attribution-test-" + std::to_string(seed) + "-" + std::to_string(i));
            if (std::filesystem::create_directory(candidate)) { root = candidate; break; }
        }
        assert(!root.empty());
    }
    ~Fixture() { std::error_code error; std::filesystem::remove_all(root, error); }
    std::filesystem::path file() const { return root / "attribution.state"; }
};

std::string bytes(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

AtomicFileResult failWrite(const std::filesystem::path&, std::string_view, std::size_t) {
    return {AtomicFileError::replaceFailed};
}

void parseAndFilter() {
    const auto value = ProductAttributionHandoff::parse(link, now);
    assert(value && value->bridgeID == "graf_attr_abcdefgh");
    assert(value->campaign.at("utm_source") == "search");
    assert(value->landingPath == "/download" && value->fallbackRecovered);
    assert(value->receivedAt == now && value->campaignKnown());
    assert(value->reliability(true) == "weak");
    assert(!ProductAttributionHandoff::parse("https://attribution?utm_source=x", now));
    assert(!ProductAttributionHandoff::parse("grafrec://attribution.evil?utm_source=x", now));
    assert(!ProductAttributionHandoff::parse("grafrec://elsewhere", now));
    assert(!ProductAttributionHandoff::parse("grafrec://attribution", -1));
    assert(!ProductAttributionHandoff::parse("grafrec://attribution?x=" + std::string(17000, 'x'), now));
    assert(ProductAttributionHandoff::parse(" \tGRAFREC://ATTRIBUTION\r\n", now));

    const auto filtered = ProductAttributionHandoff::parse(
        "grafrec://attribution?bridge=bad&utm_source=good&utm_source=second"
        "&utm_medium=user%40example.invalid&utm_campaign=api_key_123"
        "&utm_content=123-456-7890&utm_term=a%2Bb&landing_path=%2F..%2Fprivate"
        "&token=do-not-store&receivedAt=0&next=https%3A%2F%2Fevil.invalid", now);
    assert(filtered && !filtered->bridgeID && !filtered->landingPath);
    assert(filtered->campaign.size() == 1 && filtered->campaign.at("utm_source") == "good");
    assert(filtered->receivedAt == now);
    const auto duplicate = ProductAttributionHandoff::parse(
        "grafrec://attribution?utm_source=secret&utm_source=good&bridge=&bridge=graf_attr_abcdefgh", now);
    assert(duplicate && !duplicate->campaignKnown() && !duplicate->bridgeID);
    assert(duplicate->reliability(true) == "unknown");
    const auto labels = ProductAttributionHandoff::parse(
        "grafrec://attribution?utm_source=Alpha_.:-&fallback=FALSE&landing_path=%2Fok_path-2", now);
    assert(labels && labels->campaignKnown() && !labels->fallbackRecovered);
    assert(labels->reliability(true) == "linked" && labels->reliability(false) == "weak");
    assert(ProductAttributionHandoff::parse("grafrec://attribution?utm_source=%20search%20", now)->campaign.at("utm_source") == "search");
    assert(ProductAttributionHandoff::parse("grafrec://attribution?utm_source=%C2%A0search%E3%80%80", now)->campaign.at("utm_source") == "search");
    assert(ProductAttributionHandoff::parse("grafrec://attribution?utm_source=%E2%80%8Bsearch%E2%80%8B", now)->campaign.at("utm_source") == "search");
    assert(ProductAttributionHandoff::parse(u8"\u00a0grafrec://attribution\u3000", now));
    assert(ProductAttributionHandoff::parse("grafrec://name@attribution:12/ignored#fragment", now));
    assert(ProductAttributionHandoff::parse("grafrec://attribution?%75tm_source=search", now)->campaign.at("utm_source") == "search");
    assert(!ProductAttributionHandoff::parse("grafrec://attribution?utm_source=%00bad", now)->campaignKnown());
    assert(!ProductAttributionHandoff::parse("grafrec://attribution?utm_source=%ZZ", now)->campaignKnown());
    assert(!ProductAttributionHandoff::parse("grafrec://attribution?utm_source=a+b", now)->campaignKnown());
    assert(!ProductAttributionHandoff::parse("grafrec://attribution?utm_source=%2541", now)->campaignKnown());
    assert(!ProductAttributionHandoff::parse("grafrec://attribution#?utm_source=search", now)->campaignKnown());
    assert(!ProductAttributionHandoff::parse("grafrec://attribution?utm_source&utM_source=search", now)->campaignKnown());
    for (const auto size : {7, 8, 64, 65}) {
        const auto parsed = ProductAttributionHandoff::parse("grafrec://attribution?bridge=graf_attr_" + std::string(size, 'a'), now);
        assert(parsed && parsed->bridgeID.has_value() == (size >= 8 && size <= 64));
    }
    for (const auto size : {96, 97}) {
        const auto parsed = ProductAttributionHandoff::parse("grafrec://attribution?utm_source=" + std::string(size, 'a'), now);
        assert(parsed && parsed->campaignKnown() == (size == 96));
    }
}

void expiryAndSignIn() {
    auto value = ProductAttributionHandoff::parse(link, now);
    constexpr auto life = ProductAttributionHandoff::validitySeconds;
    assert(value && !value->isExpired(now + life - 1) && value->isExpired(now + life));
    assert(value->isExpired(std::numeric_limits<std::int64_t>::max()));
    const std::string plain = "https://cabinet.example.invalid/login?next=%2Fbilling";
    assert(applyingSignInQueryItems(plain, value, now + life) == plain);
    assert(applyingSignInQueryItems(plain, std::nullopt, now) == plain);
    // Even an in-process caller cannot smuggle arbitrary query keys into a URL.
    value->campaign["next"] = "https://evil.invalid";
    value->campaign["utm_term"] = "secret-value";
    value->bridgeID = "bad&next=evil";
    assert(applyingSignInQueryItems(plain, value, now).find("evil") == std::string::npos);
    assert(applyingSignInQueryItems(plain, value, now).find("secret") == std::string::npos);
}

void persistedSignInUsesActualHost() {
    Fixture fixture;
    ProductAttributionHandoffStore writer(fixture.file());
    ProductAttributionHandoffStore reader(fixture.file());
    constexpr auto origin = "https://cabinet.example.invalid";
    const std::string billing = std::string(origin) + "/billing";
    const std::string plain = std::string(origin) + "/login?next=%2Fbilling";
    const std::string suffix = "&graf_attribution_fallback=1&graf_attribution_ref=graf_attr_abcdefgh"
        "&utm_source=search&utm_campaign=launch&landing_path=%2Fdownload";
    auto clock = now;
    WebView2Host host{WebViewRoutePolicy(origin)};
    // The same composition as AppMain: read on every request, then decorate
    // the host's validated URL. No parallel route builder exists in this test.
    host.setSignInUrlBuilder([&](std::string_view url) {
        return applyingSignInQueryItems(url, reader.current(clock).handoff, clock);
    });
    assert(host.navigate(billing).decision == RouteDecision::allow);
    assert(host.signInUrl() == plain);
    assert(writer.saveLink(link, now) == AttributionStoreError::none);
    const auto saved = bytes(fixture.file());
    assert(host.signInUrl() == plain + suffix);
    clock = now + ProductAttributionHandoff::validitySeconds - 1;
    assert(host.signInUrl() == plain + suffix);
    assert(bytes(fixture.file()) == saved); // Reading must not extend the 90 days.
    ++clock;
    assert(host.signInUrl() == plain);
    assert(!ProductAttributionHandoffStore(fixture.file()).current(clock).handoff);

    assert(writer.saveLink("grafrec://attribution", clock) == AttributionStoreError::none);
    assert(host.signInUrl() == plain + "&graf_attribution_fallback=1");
    assert(!reader.current(clock).handoff->campaignKnown());
    assert(writer.saveLink(link, clock) == AttributionStoreError::none);
    for (const auto route : {"https://evil.invalid/billing", "//evil.invalid",
                             "https://cabinet.example.invalid/billing/checkout/start"}) {
        (void)host.navigate(route);
        assert(host.signInUrl() == plain + suffix); // Preserve the last safe GET.
    }
    (void)host.navigate(billing + "?next=https://evil.invalid#bad");
    assert(host.signInUrl() == plain + suffix);

    const auto detail = std::string(origin) + "/desktop/meetings/abc-123";
    const auto detailLogin = std::string(origin) + "/login?next=%2Fdesktop%2Fmeetings%2Fabc-123";
    (void)host.beginDocumentNavigation(detail, 1, false, 0);
    (void)host.completeDocumentNavigation(detail, 1, {401}, 1);
    assert(host.recoveryUrl() == detailLogin + suffix);
    assert(host.signInUrl() == host.recoveryUrl());
    assert(writer.clear() == AttributionStoreError::none);
    assert(host.recoveryUrl() == detailLogin); // No stale cached attribution.
    { std::ofstream output(fixture.file()); output << "unsupported state"; }
    assert(host.signInUrl() == detailLogin); // Corruption cannot block sign-in.
    assert(writer.clear() == AttributionStoreError::none);
    std::filesystem::create_directory(fixture.file());
    assert(reader.current(clock).error == AttributionStoreError::ioError);
    assert(host.signInUrl() == detailLogin); // Nor can unavailable storage.
}

void decorateValidatedSignIn() {
    const auto value = ProductAttributionHandoff::parse(link, now);
    const std::string plain = "https://rec.2brain.pro/login?next=%2fbilling%2fcheckout%2fstatus%2fabc&workspace_id=space-1";
    const auto decorated = applyingSignInQueryItems(plain, value, now);
    // The host validates this exact prefix; do not decode/re-encode next or
    // discard another query item supplied by the trusted sign-in builder.
    assert(decorated == plain + "&graf_attribution_fallback=1&graf_attribution_ref=graf_attr_abcdefgh"
        "&utm_source=search&utm_campaign=launch&landing_path=%2Fdownload");
    assert(applyingSignInQueryItems(plain, std::nullopt, now) == plain);
    assert(applyingSignInQueryItems(plain, value, now + ProductAttributionHandoff::validitySeconds) == plain);
    assert(applyingSignInQueryItems(decorated, value, now) == decorated);
    const auto fragment = applyingSignInQueryItems(plain + "#existing", value, now);
    assert(fragment == decorated + "#existing");
    assert(applyingSignInQueryItems("https://rec.2brain.pro/login", value, now).find("/login?graf_attribution_fallback=1") != std::string::npos);
    assert(applyingSignInQueryItems("https://rec.2brain.pro/login?", value, now).find("/login?graf_attribution_fallback=1") != std::string::npos);
    assert(applyingSignInQueryItems(plain + "&", value, now) == decorated);
    assert(applyingSignInQueryItems(plain + "&other=?", value, now).find(
        plain + "&other=?&graf_attribution_fallback=1") == 0);
    const auto replaced = applyingSignInQueryItems(
        plain + "&%67raf_attribution_ref=old&graf_attribution_ref=older&utm_source=old&utm_term=retained", value, now);
    // Mac removes all occurrences of names it emits, not unrelated parameters.
    assert(replaced == plain + "&utm_term=retained&graf_attribution_fallback=1&graf_attribution_ref=graf_attr_abcdefgh"
        "&utm_source=search&utm_campaign=launch&landing_path=%2Fdownload");
    assert(applyingSignInQueryItems(plain + "#existing", std::nullopt, now) == plain + "#existing");
}

void storeRoundTripAndFailure() {
    Fixture fixture;
    ProductAttributionHandoffStore store(fixture.file());
    assert(store.current(now).error == AttributionStoreError::none);
    assert(!store.current(now).handoff);
    assert(store.markAccountConnected(now - 1) == AttributionStoreError::none);
    assert(store.saveLink(link, now) == AttributionStoreError::none);
    ProductAttributionHandoffStore reopened(fixture.file());
    auto loaded = reopened.current(now + 1);
    assert(loaded.handoff && loaded.handoff->campaign.at("utm_source") == "search");
    assert(loaded.accountConnectedAt == now - 1);
    const auto before = bytes(fixture.file());
    assert(before.find("grafrec://") == std::string::npos);
    assert(store.current(now + 30).handoff->receivedAt == now); // Reads never refresh TTL.
    assert(store.saveLink("https://wrong.invalid", now) == AttributionStoreError::rejected);
    assert(bytes(fixture.file()) == before);
    ProductAttributionHandoffStore failing(fixture.file(), failWrite);
    assert(failing.saveLink("grafrec://attribution?utm_source=new", now + 1) == AttributionStoreError::ioError);
    assert(bytes(fixture.file()) == before);
    // Expired data is never returned, even if expiry cleanup cannot be persisted.
    const auto expiredFailure = failing.current(now + ProductAttributionHandoff::validitySeconds);
    assert(!expiredFailure.handoff && expiredFailure.error == AttributionStoreError::ioError);
    assert(bytes(fixture.file()) == before);
    assert(store.saveLink("grafrec://attribution", now + 2) == AttributionStoreError::none);
    assert(!reopened.current(now + 3).handoff->campaignKnown());
    assert(reopened.current(now + 3).accountConnectedAt == now - 1);
    assert(!store.current(now + 2 + ProductAttributionHandoff::validitySeconds).handoff);
    assert(!reopened.current(now + 3 + ProductAttributionHandoff::validitySeconds).handoff);
    assert(store.clear() == AttributionStoreError::none);
    assert(!store.current(now).accountConnectedAt && !store.current(now).handoff);
    assert(store.clear() == AttributionStoreError::none);
}

void boundedAndCorruptStorage() {
    Fixture fixture;
    ProductAttributionHandoffStore store(fixture.file());
    { std::ofstream output(fixture.file()); output << "not a supported schema"; }
    assert(store.current(now).error == AttributionStoreError::invalidData);
    assert(!store.current(now).handoff);
    // Like Mac, a new accepted handoff can replace an unreadable payload.
    assert(store.saveLink(link, now) == AttributionStoreError::none);
    auto corrupt = bytes(fixture.file());
    const auto offset = corrupt.find("search");
    assert(offset != std::string::npos);
    corrupt.replace(offset, 6, "secret");
    { std::ofstream output(fixture.file()); output << corrupt; }
    assert(store.current(now).error == AttributionStoreError::invalidData);
    assert(!store.current(now).handoff && !store.current(now).accountConnectedAt);
    assert(store.saveLink(link, now) == AttributionStoreError::none);
    { std::ofstream output(fixture.file(), std::ios::app); output << "unexpected\n"; }
    assert(store.current(now).error == AttributionStoreError::invalidData);
    { std::ofstream output(fixture.file()); output << std::string(ProductAttributionHandoffStore::maximumBytes + 1, 'x'); }
    assert(store.current(now).error == AttributionStoreError::tooLarge);
    assert(!store.current(now).handoff);
    assert(store.clear() == AttributionStoreError::none);
    std::filesystem::create_directory(fixture.file());
    assert(store.saveLink(link, now) == AttributionStoreError::ioError);
    assert(std::filesystem::is_directory(fixture.file()));
}
} // namespace

int main() {
    parseAndFilter();
    expiryAndSignIn();
    persistedSignInUsesActualHost();
    decorateValidatedSignIn();
    storeRoundTripAndFailure();
    boundedAndCorruptStorage();
    std::puts("ProductAttributionHandoffTests: 6 groups passed");
}
