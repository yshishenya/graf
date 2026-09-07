#include "../../RecApp/Upload/DesktopUploadRecoveryScheduler.h"
#include "../../RecApp/Upload/DesktopApiClient.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <chrono>
#include <filesystem>
#include <memory>
#include <stdexcept>
#include <thread>

namespace {
const graf::windows::DesktopAccountIdentity owner{
    "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"};

std::string meResponse(std::string_view user, std::string_view workspace) {
    return "{\"user_id\":\"" + std::string(user) + "\",\"workspace_id\":\"" + std::string(workspace) +
        R"(","active_session_id":"33333333-3333-4333-8333-333333333333","policy":{"future":[true,false,null,1.2e-3]},"registered_devices":[]})";
}

void testAccountIdentity() {
    using namespace graf::windows;
    const auto json = meResponse(owner.userId, owner.workspaceId);
    const auto identity = DesktopHttpTransport::decodeAccountIdentity(json);
    assert(identity && identity->userId == owner.userId && identity->workspaceId == owner.workspaceId);
    assert(DesktopHttpTransport::decodeAccountIdentity(" \n" + json + "\t"));
    assert(DesktopHttpTransport::decodeAccountIdentity(
        "{ \"user_id\" : \"" + owner.userId + "\", \"workspace_id\" : \"" + owner.workspaceId +
        "\", \"active_session_id\" : \"33333333-3333-4333-8333-333333333333\" }"));
    const auto replace = [&](std::string_view before, std::string_view after) {
        auto changed = json;
        const auto at = changed.find(before);
        assert(at != std::string::npos);
        changed.replace(at, before.size(), after);
        return changed;
    };
    for (const auto& invalid : {
        std::string("{}"), std::string("[]"), json + " trailing", json.substr(0, json.size() - 1),
        "{\"policy\":" + json + "}", // Nested identity is not authority.
        replace("\"33333333-3333-4333-8333-333333333333\"", "null"),
        replace("\"33333333-3333-4333-8333-333333333333\"", "123"),
        replace("active_session_id", "other_session_id"),
        replace("user_id", "other_user_id"),
        replace("user_id", "user_\\u0069d"), // Escaped alias is not a second authority key.
        replace("\"user_id\":", "\"user_id\":null,\"user_id\":"),
        replace("\"workspace_id\":", "\"workspace_id\":false,\"workspace_id\":"),
        replace("1.2e-3", "1e"), replace("1.2e-3", "01"), replace("[true", "[,true"),
        replace("[]", "[\"bad\\q\"]"), replace("[]", "[true,]"),
        meResponse("bad-id", owner.workspaceId), meResponse(owner.userId, ""),
        meResponse("00000000-0000-0000-0000-000000000000", owner.workspaceId)}) {
        assert(!DesktopHttpTransport::decodeAccountIdentity(invalid));
    }
    auto tooDeep = json;
    tooDeep.replace(tooDeep.find("[]"), 2, std::string(40, '[') + "null" + std::string(40, ']'));
    assert(!DesktopHttpTransport::decodeAccountIdentity(tooDeep));
    assert(!DesktopHttpTransport::decodeAccountIdentity(std::string(2 * 1024 * 1024 + 1, ' ')));

    UploadCustodyItem item;
    assert(DesktopHttpTransport::ownerBlockReason(item, identity) == "local_owner_unclaimed");
    assert(DesktopHttpTransport{}.upload(item).safeReason == "local_owner_unclaimed");
    item.ownerUserId = owner.userId; item.ownerWorkspaceId = owner.workspaceId;
    assert(DesktopHttpTransport::ownerBlockReason(item, std::nullopt) == "account_identity_unavailable");
    assert(DesktopHttpTransport::ownerBlockReason(item, identity).empty());
    assert(DesktopHttpTransport::ownerBlockReason(item, DesktopAccountIdentity{owner.workspaceId, owner.workspaceId}) == "account_mismatch");
    assert(DesktopHttpTransport::ownerBlockReason(item, DesktopAccountIdentity{owner.userId, owner.userId}) == "account_mismatch");
    assert(DesktopHttpTransport::ownerBlockReason(item, DesktopAccountIdentity{}) == "account_identity_unavailable");
    assert(!DesktopHttpTransport{}.accountIdentity()); // No session, no network.
}

void testWorkspaceBootstrap() {
    using namespace graf::windows;
    const auto row = [](std::string_view id, bool active) {
        return "{\"id\":\"" + std::string(id) + "\",\"active\":" + (active ? "true" : "false") + "}";
    };
    const auto active = row(owner.workspaceId, true);
    const auto inactive = row(owner.userId, false);
    const auto spaces = "{\"spaces\":[" + inactive + "," + active + "]}";
    assert(DesktopHttpTransport::decodeActiveWorkspace(spaces) == owner.workspaceId);
    assert(DesktopHttpTransport::decodeActiveWorkspace(" \n" + spaces + "\t") == owner.workspaceId);
    assert(DesktopHttpTransport::decodeActiveWorkspace(
        "{\"spaces\":[ {\"name\":\"text with [,] and \\\"quotes\\\"\", \"active\" : true, \"id\" : \"" +
        owner.workspaceId + "\"} ]}") == owner.workspaceId);
    for (const auto& invalid : {
        std::string("{}"), std::string("[]"), std::string("{\"spaces\":null}"),
        std::string("{\"spaces\":[]}"), spaces + " trailing",
        "{\"spaces\":[],\"spaces\":[" + active + "]}",
        "{\"spaces\":[" + inactive + "]}",
        "{\"spaces\":[" + active + "," + row(owner.userId, true) + "]}",
        "{\"spaces\":[" + active + "," + row(owner.workspaceId, false) + "]}",
        "{\"spaces\":[" + active + ",null]}",
        "{\"spaces\":[" + active + ",[]]}",
        "{\"spaces\":[" + active + ",{\"active\":false}]}",
        "{\"spaces\":[" + active + ",{\"id\":false,\"active\":false}]}",
        "{\"spaces\":[" + active + ",{\"id\":\"bad\",\"active\":false}]}",
        "{\"spaces\":[{\"id\":\"" + owner.workspaceId + "\",\"active\":\"true\"}]}",
        "{\"spaces\":[{\"id\":\"" + owner.workspaceId + "\",\"active\":1}]}",
        "{\"spaces\":[{\"id\":\"" + owner.workspaceId + "\",\"active\":false,\"active\":true}]}",
        "{\"spaces\":[{\"id\":null,\"id\":\"" + owner.workspaceId + "\",\"active\":true}]}",
        "{\"spaces\":[{\"id\":\"" + owner.workspaceId + "\",\"\\u0061ctive\":true}]}",
        "{\"spaces\":[" + active + "],\"extra\":{\"duplicate\":1,\"duplicate\":2}}",
        "{\"spaces\":[" + active + ",]}",
        "{\"nested\":" + spaces + "}",
        std::string(2 * 1024 * 1024 + 1, ' ') + spaces}) {
        assert(!DesktopHttpTransport::decodeActiveWorkspace(invalid));
    }
    std::string large = "{\"spaces\":[";
    for (unsigned i = 1; i <= 1024; ++i) {
        const auto suffix = std::to_string(i);
        const auto id = "44444444-4444-4444-8444-" + std::string(12 - suffix.size(), '0') + suffix;
        if (i > 1) large += ',';
        large += row(id, i == 1);
    }
    assert(DesktopHttpTransport::decodeActiveWorkspace(large + "]}"));
    assert(!DesktopHttpTransport::decodeActiveWorkspace(large + "," + inactive + "]}"));

    DesktopHttpConfig config;
    config.sessionToken = "synthetic-session";
    config.deviceId = "not-an-installation-authority";
    auto cancellation = std::make_shared<std::atomic_bool>(false);
    config.cancellation = cancellation;
    unsigned calls = 0;
    using IdentityResponse = DesktopHttpTransport::IdentityResponse;
    const auto get = [&](const DesktopHttpConfig& request, std::string_view path) -> IdentityResponse {
        ++calls;
        assert(request.sessionToken == config.sessionToken);
        assert(request.baseOrigin == config.baseOrigin && request.deviceId.empty());
        if (calls == 1) {
            assert(path == "/desktop/settings/spaces" && request.workspaceId.empty());
            return {200, spaces};
        }
        assert(calls == 2 && path == "/api/v1/auth/me" && request.workspaceId == owner.workspaceId);
        return {200, meResponse(owner.userId, owner.workspaceId)};
    };
    auto identity = DesktopHttpTransport(config).accountIdentity(get).identity;
    assert(identity && identity->userId == owner.userId && identity->workspaceId == owner.workspaceId && calls == 2);
    // Current server response shapes, synthetic content only. Nested account
    // identifiers and display text must not replace the root authority.
    const auto fullSpaces = R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222",
        "name":"Моё тестовое пространство","kind":"personal","role":"owner","active":true}]})";
    const auto fullMe = R"({"user_id":"11111111-1111-4111-8111-111111111111",
        "workspace_id":"22222222-2222-4222-8222-222222222222",
        "active_session_id":"33333333-3333-4333-8333-333333333333",
        "linked_providers":[{"provider":"yandex","provider_subject":"synthetic",
            "is_primary":true,"confirmed_at":"2026-09-06T00:00:00Z"}],
        "policy":{"workspace_id":"44444444-4444-4444-8444-444444444444",
            "providers":[{"provider":"yandex","enabled":true,"label":"Яндекс","requires_email":true}],
            "residency":{"require_ru_local":true,"residency_region_tag":"ru-local"},
            "enrollment":{"allow_provider_self_enrollment":false},"consent_version":"test",
            "consent":{"language":"ru","version":"test","content_markdown":"Тест [ссылка]\n\"текст\""}},
        "registered_devices":[{"device_id":"55555555-5555-4555-8555-555555555555",
            "status":"active","registration_state":"registered","created_at":"2026-09-06T00:00:00Z"}],
        "billing":{"plan_code":"personal","state":"active","trial_ends_at":null,
            "paid_through":"2026-10-06T00:00:00Z","bonus_until":null,"renewal_resolution":null,
            "processing_unlimited":true,"storage_used_bytes":123,"storage_capacity_bytes":10737418240,
            "handoff_path":"/billing"}})";
    calls = 0;
    identity = DesktopHttpTransport(config).accountIdentity(
        [&](const DesktopHttpConfig& request, std::string_view path) -> IdentityResponse {
            (void)get(request, path); // Check the same headers and two-request order.
            return {200, calls == 1 ? fullSpaces : fullMe};
        }).identity;
    assert(identity && identity->userId == owner.userId && identity->workspaceId == owner.workspaceId && calls == 2);
    for (unsigned failAt : {1U, 2U}) {
        calls = 0;
        assert(!DesktopHttpTransport(config).accountIdentity(
            [&](const DesktopHttpConfig& request, std::string_view path) -> IdentityResponse {
                const auto body = get(request, path);
                return calls == failAt ? IdentityResponse{0, {}, true} : body;
            }).identity);
        assert(calls == failAt);
    }
    for (unsigned cancelAt : {0U, 1U, 2U}) {
        calls = 0;
        cancellation->store(cancelAt == 0);
        assert(!DesktopHttpTransport(config).accountIdentity(
            [&](const DesktopHttpConfig& request, std::string_view path) -> IdentityResponse {
                const auto body = get(request, path);
                if (calls == cancelAt) cancellation->store(true);
                return body;
            }).identity);
        assert(calls == cancelAt);
        cancellation->store(false);
    }
    for (const auto& invalidMe : {meResponse(owner.userId, owner.userId), std::string("{}"),
        "{\"user_id\":\"" + owner.userId + "\",\"workspace_id\":\"" + owner.workspaceId + "\",\"active_session_id\":null}"}) {
        calls = 0;
        assert(!DesktopHttpTransport(config).accountIdentity(
            [&](const DesktopHttpConfig& request, std::string_view path) -> IdentityResponse {
                const auto body = get(request, path);
                return calls == 2 ? IdentityResponse{200, invalidMe} : body;
            }).identity);
    }
    calls = 0;
    assert(!DesktopHttpTransport(config).accountIdentity(
        [&](const auto&, auto) -> IdentityResponse { ++calls; return {200, "{\"spaces\":[]}"}; }).identity);
    assert(calls == 1);
    config.workspaceId = owner.workspaceId;
    calls = 0;
    assert(DesktopHttpTransport(config).accountIdentity(
        [&](const DesktopHttpConfig& request, std::string_view path) -> IdentityResponse {
            ++calls;
            assert(path == "/api/v1/auth/me" && request.workspaceId == owner.workspaceId && request.deviceId.empty());
            return {200, meResponse(owner.userId, owner.workspaceId)};
        }).identity);
    assert(calls == 1);
    config.workspaceId = "invalid";
    calls = 0;
    assert(!DesktopHttpTransport(config).accountIdentity(get).identity && calls == 0);
    config.workspaceId.clear();
    assert(!DesktopHttpTransport(config).accountIdentity(DesktopHttpTransport::IdentityGet{}).identity);
    config.sessionToken.clear();
    calls = 0;
    assert(!DesktopHttpTransport(config).accountIdentity(get).identity && calls == 0);
}

void testIdentityFailures() {
    using namespace graf::windows;
    using Response = DesktopHttpTransport::IdentityResponse;
    DesktopHttpConfig config;
    config.sessionToken = "synthetic-session";
    const auto spaces = "{\"spaces\":[{\"id\":\"" + owner.workspaceId + "\",\"active\":true}]}";
    // Both bootstrap steps must retain the distinction between network/server
    // failure and a missing/revoked session. A valid body cannot override status.
    for (unsigned failAt : {1U, 2U}) {
        for (unsigned status : {0U, 200U, 408U, 429U, 500U, 503U, 504U, 401U, 403U, 302U, 404U}) {
            unsigned calls = 0;
            const bool transportFailed = status == 0 || status == 200;
            const auto result = DesktopHttpTransport(config).accountIdentity(
                [&](const DesktopHttpConfig& request, std::string_view) -> Response {
                    ++calls;
                    assert(request.sessionToken == config.sessionToken && request.deviceId.empty());
                    const auto body = calls == 1 ? spaces : meResponse(owner.userId, owner.workspaceId);
                    return {calls == failAt ? status : 200, body, calls == failAt && transportFailed};
                });
            assert(!result.identity && calls == failAt);
            const auto expected = transportFailed || status == 408 || status == 429 || status >= 500
                ? DesktopTransportStatus::retryableFailure : DesktopTransportStatus::authRequired;
            assert(result.status == expected);
        }
    }
    unsigned calls = 0;
    config.sessionToken.clear();
    const auto missing = DesktopHttpTransport(config).accountIdentity([&](const auto&, auto) -> Response {
        ++calls; return {200, meResponse(owner.userId, owner.workspaceId)};
    });
    assert(!missing.identity && missing.status == DesktopTransportStatus::authRequired && calls == 0);
}

std::string syncState(std::string_view status, std::string_view conflict,
                      std::string_view action = "contact_operator") {
    return std::string(R"({"meeting":{"meeting_id":"meeting-id"},"upload_session":{"session_id":"session-id","status":")") +
        std::string(status) + R"(","accepted_bytes_by_track":{"manifest":10,"media":20,"playback":30}},"conflict":{"state":")" +
        std::string(conflict) + R"(","next_action":")" + std::string(action) + R"("}})";
}

void testSyncDecoder() {
    using namespace graf::windows;
    for (const auto status : {"finalized", "degraded"}) {
        for (const auto conflict : {"none", "processing_failed", "processing_blocked"}) {
            const auto decoded = DesktopHttpTransport::decodeSyncState(syncState(status, conflict), "local-id");
            assert(decoded && decoded->truth.finalized && !decoded->blockedByConflict);
            assert(!decoded->needsNewUploadSession && decoded->truth.localRecordingId == "local-id");
            assert((decoded->truth.acceptedBytes == std::array<std::uint64_t, 3>{10, 20, 30}));
        }
        for (const auto conflict : {"server_meeting_deleted", "access_revoked", "stale_device_identity",
                                    "metadata_mismatch", "future_unknown_conflict", "upload_session_expired"}) {
            const auto decoded = DesktopHttpTransport::decodeSyncState(syncState(status, conflict, "create_upload_session"), "local-id");
            assert(decoded && decoded->blockedByConflict && !decoded->truth.finalized);
            assert(!decoded->needsNewUploadSession);
        }
    }
    for (const auto status : {"created", "uploading", "expired", "failed"}) {
        for (const auto conflict : {"processing_failed", "processing_blocked", "server_meeting_deleted"}) {
            const auto decoded = DesktopHttpTransport::decodeSyncState(syncState(status, conflict, "create_upload_session"), "local-id");
            assert(decoded && decoded->blockedByConflict && !decoded->truth.finalized);
            assert(!decoded->needsNewUploadSession);
        }
    }
    const auto expired = DesktopHttpTransport::decodeSyncState(syncState("expired", "upload_session_expired"), "local-id");
    assert(expired && expired->needsNewUploadSession && !expired->blockedByConflict && !expired->truth.finalized);
    assert(!DesktopHttpTransport::decodeSyncState("{}", "local-id"));
    const auto noSession = DesktopHttpTransport::decodeSyncState(
        R"({"meeting":{"meeting_id":"meeting-id"},"upload_session":null,"conflict":{"state":"processing_failed"}})", "local-id");
    assert(noSession && noSession->blockedByConflict && !noSession->truth.finalized);
}

template <typename Predicate> void waitFor(Predicate predicate) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
    while (!predicate()) {
        assert(std::chrono::steady_clock::now() < deadline);
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}

std::size_t runWorker(graf::windows::DesktopUploadRecoveryScheduler& scheduler,
                      graf::windows::RecoveryTrigger trigger,
                      graf::windows::DesktopUploadRecoveryScheduler::WorkerHandler worker) {
    assert(scheduler.startAsync(trigger, std::move(worker)));
    std::size_t handled = 0;
    waitFor([&] { handled += scheduler.drain(); return !scheduler.busy(); });
    return handled;
}

void testManualRetry(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root / "package");
    DesktopUploadQueueService queue(root / "queue.json", root);
    assert(queue.load());
    assert(queue.enqueue({"exhausted", "directory", "session", root / "package",
        UploadQueueStatus::pending, {}, 0, "", owner.userId, owner.workspaceId}));
    DesktopUploadRecoveryScheduler scheduler(queue);
    for (unsigned attempt = 0; attempt < 8; ++attempt) {
        assert(runWorker(scheduler, RecoveryTrigger::scheduled, [](const auto& item, auto) {
            return DesktopTransportResult{DesktopTransportStatus::retryableFailure,
                UploadServerTruth{item.localRecordingId, true, true, {11, 22, 33}, false}};
        }) == 1);
    }
    // Manual retry must not revive another auth-blocked/exhausted item.
    assert(queue.enqueue({"auth-blocked", "auth-directory", "auth-session", root / "package",
        UploadQueueStatus::needsAuth, {}, 8, "account_mismatch", owner.userId, owner.workspaceId}));
    assert(queue.enqueue({"other-exhausted", "other-directory", "other-session", root / "package",
        UploadQueueStatus::retry, {}, 8, "transport_unavailable", owner.userId, owner.workspaceId}));
    assert(queue.requestRetry("exhausted"));
    assert(queue.items()[0].attempts == 0 && queue.items()[0].ownerUserId == owner.userId);
    assert(queue.items()[0].ownerWorkspaceId == owner.workspaceId);
    assert(runWorker(scheduler, RecoveryTrigger::scheduled, [](const auto& item, auto) {
        assert((item.acceptedBytes == std::array<std::uint64_t, 3>{11, 22, 33}));
        return DesktopTransportResult{DesktopTransportStatus::uploaded,
            UploadServerTruth{item.localRecordingId, true, true, {11, 22, 33}, true}};
    }) == 1);
    assert(queue.items()[0].status == UploadQueueStatus::uploaded);
    assert(queue.items()[1].status == UploadQueueStatus::needsAuth && queue.items()[1].attempts == 8);
    assert(queue.items()[2].status == UploadQueueStatus::retry && queue.items()[2].attempts >= 8);
    assert(!queue.requestRetry("exhausted") && !queue.requestRetry("unknown"));

    // The selected row can follow more than one bounded batch of exhausted rows.
    for (unsigned i = 0; i < 32; ++i) {
        const auto id = "budget-" + std::to_string(i);
        assert(queue.enqueue({id, id, id, root / "package", UploadQueueStatus::retry, {}, 8,
            "retry_budget_exhausted", owner.userId, owner.workspaceId}));
    }
    assert(queue.enqueue({"selected", "selected", "selected", root / "package", UploadQueueStatus::needsAuth,
        {}, 8, "auth_required", owner.userId, owner.workspaceId}));
    assert(queue.requestRetry("selected"));
    assert(runWorker(scheduler, RecoveryTrigger::scheduled, [](const auto& item, auto) {
        assert(item.localRecordingId == "selected" && item.attempts == 0);
        return DesktopTransportResult{DesktopTransportStatus::uploaded, std::nullopt};
    }) == 1);
}

void testReplacementSessionKey() {
    using namespace graf::windows;
    UploadCustodyItem item{"local", "directory", "session", {}, UploadQueueStatus::retry, {}, 8, ""};
    const auto first = DesktopHttpTransport::replacementUploadSessionKey(item, "expired-first");
    assert(!first.empty() && first != DesktopApiClient::idempotencyKey("upload-session", item.directoryId, item.sessionId));
    item.attempts = 0; // Explicit retry cannot replay the key of an expired session.
    assert(DesktopHttpTransport::replacementUploadSessionKey(item, "expired-first") == first);
    const auto second = DesktopHttpTransport::replacementUploadSessionKey(item, "expired-second");
    assert(!second.empty() && second != first);
    item.attempts = 7;
    assert(DesktopHttpTransport::replacementUploadSessionKey(item, "expired-second") == second);
    assert(DesktopHttpTransport::replacementUploadSessionKey(item, "").empty());
    assert(DesktopHttpTransport::replacementUploadSessionKey(item, "../invalid").empty());
    assert(DesktopHttpTransport::replacementUploadSessionKey(item, std::string(301, 's')).empty());
    item.directoryId = "../invalid";
    assert(DesktopHttpTransport::replacementUploadSessionKey(item, "expired-first").empty());
}

void testTransientIdentityRecovery(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root / "package");
    DesktopUploadQueueService queue(root / "queue.json", root);
    assert(queue.load());
    assert(queue.enqueue({"identity-recovery", "directory", "session", root / "package", UploadQueueStatus::pending,
        {11, 22, 33}, 0, "", owner.userId, owner.workspaceId}));
    DesktopUploadRecoveryScheduler scheduler(queue);
    DesktopHttpConfig config;
    config.sessionToken = "synthetic-session";
    config.workspaceId = owner.workspaceId; // AppMain already resolved the account.
    unsigned httpStatus = 503, mediaCalls = 0, identityCalls = 0;
    auto currentUser = owner.userId;
    const auto worker = [&](const UploadCustodyItem& item, auto cancellation) {
        config.cancellation = cancellation;
        const auto result = DesktopHttpTransport(config).accountIdentity(
            [&](const DesktopHttpConfig&, std::string_view path) -> DesktopHttpTransport::IdentityResponse {
                ++identityCalls;
                assert(path == "/api/v1/auth/me");
                return {httpStatus, meResponse(currentUser, owner.workspaceId)};
            });
        const auto block = DesktopHttpTransport::ownerBlockReason(item, result.identity);
        if (!block.empty()) return DesktopTransportResult{
            result.identity ? DesktopTransportStatus::authRequired : result.status, std::nullopt, std::string(block)};
        ++mediaCalls;
        assert((item.acceptedBytes == std::array<std::uint64_t, 3>{11, 22, 33}));
        return DesktopTransportResult{DesktopTransportStatus::uploaded, std::nullopt};
    };
    assert(runWorker(scheduler, RecoveryTrigger::scheduled, worker) == 1);
    assert(queue.items()[0].status == UploadQueueStatus::retry && mediaCalls == 0);
    httpStatus = 200;
    assert(runWorker(scheduler, RecoveryTrigger::scheduled, worker) == 1);
    assert(queue.items()[0].status == UploadQueueStatus::uploaded && mediaCalls == 1);

    for (unsigned denied : {401U, 403U, 200U}) {
        const auto id = "denied-" + std::to_string(denied);
        assert(queue.enqueue({id, id, id, root / "package", UploadQueueStatus::pending,
            {}, 0, "", owner.userId, owner.workspaceId}));
        httpStatus = denied;
        if (denied == 200) currentUser = owner.workspaceId; // Valid but different account.
        assert(runWorker(scheduler, RecoveryTrigger::scheduled, worker) == 1);
        assert(queue.items().back().status == UploadQueueStatus::needsAuth && mediaCalls == 1);
        const auto before = identityCalls;
        assert(!scheduler.startAsync(RecoveryTrigger::scheduled, worker));
        assert(identityCalls == before && queue.items().back().attempts == 0);
    }
}

void testOwnerRecovery(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root / "package");
    DesktopUploadQueueService queue(root / "queue.json", root);
    assert(queue.load());
    assert(queue.enqueue({"unclaimed", "directory", "session", root / "package", UploadQueueStatus::pending, {}, 0, ""}));
    DesktopUploadRecoveryScheduler scheduler(queue);
    const auto forbidden = [](const auto&, auto) -> DesktopTransportResult {
        assert(false && "unclaimed recording must never invoke a transport worker");
        return {};
    };
    assert(runWorker(scheduler, RecoveryTrigger::launch, forbidden) == 1);
    assert(queue.items()[0].status == UploadQueueStatus::needsAuth);
    assert(queue.items()[0].safeReason == "local_owner_unclaimed" && queue.items()[0].attempts == 0);
    assert(runWorker(scheduler, RecoveryTrigger::authRecovered, forbidden) == 1);
    assert(queue.items()[0].ownerUserId.empty()); // Login is not an explicit claim.
    assert(queue.assignOwner("unclaimed", owner));

    const auto gated = [](std::optional<DesktopAccountIdentity> identity) {
        return [identity = std::move(identity)](const UploadCustodyItem& item, auto) -> DesktopTransportResult {
            const auto block = DesktopHttpTransport::ownerBlockReason(item, identity);
            if (!block.empty()) return {DesktopTransportStatus::authRequired, std::nullopt, std::string(block)};
            return {DesktopTransportStatus::uploaded, UploadServerTruth{item.localRecordingId, true, true, {1, 2, 3}, true}};
        };
    };
    assert(runWorker(scheduler, RecoveryTrigger::activation, gated(DesktopAccountIdentity{owner.workspaceId, owner.workspaceId})) == 1);
    assert(queue.items()[0].status == UploadQueueStatus::needsAuth && queue.items()[0].safeReason == "account_mismatch");
    assert(queue.items()[0].ownerUserId == owner.userId && queue.items()[0].acceptedBytes[0] == 0);
    assert(!queue.assignOwner("unclaimed", {owner.workspaceId, owner.workspaceId}));
    assert(runWorker(scheduler, RecoveryTrigger::authRecovered, gated(std::nullopt)) == 1);
    assert(queue.items()[0].safeReason == "account_identity_unavailable" && queue.items()[0].attempts == 0);
    assert(runWorker(scheduler, RecoveryTrigger::authRecovered, gated(owner)) == 1);
    assert(queue.items()[0].status == UploadQueueStatus::uploaded);
    DesktopUploadQueueService reloaded(root / "queue.json", root);
    assert(reloaded.load() && reloaded.items()[0].ownerUserId == owner.userId);
}

struct PausedWork {
    std::atomic_bool entered{false};
    std::atomic_bool release{false};
    std::atomic_bool sawCancellation{false};
    graf::windows::DesktopTransportResult operator()(
        const graf::windows::UploadCustodyItem& item,
        graf::windows::DesktopUploadRecoveryScheduler::Cancellation cancellation) {
        entered.store(true);
        // Simulate one in-flight OS request which cannot return until released.
        waitFor([&] { return release.load(); });
        sawCancellation.store(cancellation->load());
        const auto decoded = graf::windows::DesktopHttpTransport::decodeSyncState(
            syncState("finalized", "processing_blocked"), item.localRecordingId);
        assert(decoded && decoded->truth.finalized);
        return {graf::windows::DesktopTransportStatus::uploaded, decoded->truth};
    }
};

void testWorker(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root / "package");
    DesktopUploadQueueService queue(root / "queue.json", root);
    assert(queue.load());
    const auto add = [&](const std::string& id) {
        assert(queue.enqueue({id, id + "-directory", id + "-session", root / "package",
                              UploadQueueStatus::pending, {}, 0, "", owner.userId, owner.workspaceId}));
    };
    add("async");
    auto paused = std::make_shared<PausedWork>();
    const DesktopUploadRecoveryScheduler::WorkerHandler worker =
        [paused](const auto& item, auto cancellation) { return (*paused)(item, std::move(cancellation)); };
    DesktopUploadRecoveryScheduler scheduler(queue);
    assert(scheduler.startAsync(RecoveryTrigger::launch, worker));
    waitFor([&] { return paused->entered.load(); });
    assert(scheduler.busy() && scheduler.drain() == 0);
    assert(!scheduler.startAsync(RecoveryTrigger::wake, worker));
    DesktopUploadRecoveryScheduler sameLedger(queue);
    assert(!sameLedger.startAsync(RecoveryTrigger::launch, worker));
    assert(queue.items()[0].status == UploadQueueStatus::pending);
    DesktopUploadQueueService disk(root / "queue.json", root);
    assert(disk.load() && disk.items()[0].status == UploadQueueStatus::pending);
    add("added-on-ui"); // A copied batch cannot see a concurrent UI enqueue.
    paused->release.store(true);
    std::size_t drained = 0;
    waitFor([&] { drained += scheduler.drain(); return !scheduler.busy(); });
    assert(drained == 1 && queue.items()[0].status == UploadQueueStatus::uploaded);
    assert(queue.items()[1].status == UploadQueueStatus::pending);
    assert(disk.load() && disk.items()[0].status == UploadQueueStatus::uploaded);

    // Shutdown does not join a blocked request or leave a raw queue/owner ref.
    paused = std::make_shared<PausedWork>();
    auto oldOwner = std::make_unique<DesktopUploadRecoveryScheduler>(queue);
    assert(oldOwner->startAsync(RecoveryTrigger::launch,
        [paused](const auto& item, auto cancellation) { return (*paused)(item, std::move(cancellation)); }));
    waitFor([&] { return paused->entered.load(); });
    oldOwner->cancel();
    oldOwner.reset(); // Must return before PausedWork can be released.
    assert(!sameLedger.startAsync(RecoveryTrigger::launch, worker));
    paused->release.store(true);
    waitFor([&] { return paused->sawCancellation.load(); });
    assert(queue.items()[1].status == UploadQueueStatus::pending);
    waitFor([&] {
        return sameLedger.startAsync(RecoveryTrigger::launch, [](const UploadCustodyItem&, auto) -> DesktopTransportResult {
            throw std::runtime_error("synthetic transport failure");
        });
    });
    waitFor([&] { (void)sameLedger.drain(); return !sameLedger.busy(); });
    assert(queue.items()[1].status == UploadQueueStatus::retry && queue.items()[1].attempts == 1);
    assert(queue.items()[1].safeReason == "transport_unavailable");

    // Results completed with an old auth/capture state cannot override UI action.
    paused = std::make_shared<PausedWork>();
    assert(scheduler.startAsync(RecoveryTrigger::activation,
        [paused](const auto& item, auto cancellation) { return (*paused)(item, std::move(cancellation)); }));
    waitFor([&] { return paused->entered.load(); });
    assert(queue.markQuarantined("added-on-ui", "user_action"));
    paused->release.store(true);
    waitFor([&] { assert(scheduler.drain() == 0); return !scheduler.busy(); });
    assert(queue.items()[1].status == UploadQueueStatus::quarantined);

    add("auth-snapshot");
    DesktopHttpConfig config;
    config.sessionToken = "synthetic-session";
    // The synthetic package has no manifest: no platform makes a network call.
    assert(scheduler.startAsync(RecoveryTrigger::authRecovered, config));
    config.sessionToken.clear(); // Does not mutate the worker's value copy.
    assert(!scheduler.startAsync(RecoveryTrigger::activation, config));
    waitFor([&] { (void)scheduler.drain(); return !scheduler.busy(); });
    assert(DesktopHttpTransport(config).upload(queue.items()[2]).status == DesktopTransportStatus::authRequired);

    auto cancelled = std::make_shared<std::atomic_bool>(true);
    config.cancellation = cancelled;
    assert(DesktopHttpTransport(config).upload(queue.items()[2]).status == DesktopTransportStatus::retryableFailure);

    add("cancel-with-owner");
    paused = std::make_shared<PausedWork>();
    assert(scheduler.startAsync(RecoveryTrigger::activation,
        [paused](const auto& item, auto cancellation) { return (*paused)(item, std::move(cancellation)); }));
    waitFor([&] { return paused->entered.load(); });
    scheduler.cancel();
    paused->release.store(true);
    waitFor([&] { assert(scheduler.drain() == 0); return !scheduler.busy(); });
    assert(queue.items().back().status == UploadQueueStatus::pending);
}
} // namespace

int main() {
    using namespace graf::windows;
    testSyncDecoder();
    testAccountIdentity();
    testWorkspaceBootstrap();
    testIdentityFailures();
    testReplacementSessionKey();
    const auto root = std::filesystem::temp_directory_path() /
        ("graf-feature-200-recovery-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    const auto path = root / "desktop-upload-queue.json";
    const auto package = root / "recording";
    std::filesystem::create_directories(package);
    testManualRetry(root / "manual");
    testTransientIdentityRecovery(root / "identity-recovery");
    testWorker(root / "worker");
    testOwnerRecovery(root / "owner");
    DesktopUploadQueueService queue(path, root); assert(queue.load());
    assert(queue.enqueue({"recording", "directory", "session", package, UploadQueueStatus::pending, {}, 0, "", owner.userId, owner.workspaceId}));
    assert(queue.enqueue({"auth-recording", "auth-directory", "auth-session", package, UploadQueueStatus::pending, {}, 0, "", owner.userId, owner.workspaceId}));
    assert(queue.enqueue({"invalid-recording", "invalid-directory", "invalid-session", package, UploadQueueStatus::pending, {}, 0, "", owner.userId, owner.workspaceId}));
    DesktopUploadRecoveryScheduler scheduler(queue);
    assert(runWorker(scheduler, RecoveryTrigger::launch, [](const UploadCustodyItem& item, auto) {
        if (item.localRecordingId == "auth-recording") return DesktopTransportResult{DesktopTransportStatus::authRequired, std::nullopt};
        if (item.localRecordingId == "invalid-recording") return DesktopTransportResult{DesktopTransportStatus::invalidPackage, std::nullopt};
        const auto decoded = DesktopHttpTransport::decodeSyncState(syncState("finalized", "processing_failed"), item.localRecordingId);
        assert(decoded && decoded->truth.finalized && !decoded->blockedByConflict);
        return DesktopTransportResult{DesktopTransportStatus::uploaded, decoded->truth};
    }) == 3);
    assert(queue.items()[0].status == UploadQueueStatus::uploaded);
    const std::array<std::uint64_t, 3> uploadedBytes{10, 20, 30};
    assert(queue.items()[0].acceptedBytes == uploadedBytes);
    assert(queue.items()[1].status == UploadQueueStatus::needsAuth);
    assert(queue.items()[2].status == UploadQueueStatus::quarantined);

    auto authRecovered = std::make_shared<std::atomic_bool>(false);
    DesktopUploadRecoveryScheduler authScheduler(queue);
    assert(runWorker(authScheduler, RecoveryTrigger::authRecovered, [authRecovered](const UploadCustodyItem& item, auto) {
        assert(item.localRecordingId == "auth-recording");
        authRecovered->store(true);
        return DesktopTransportResult{DesktopTransportStatus::uploaded,
                                      UploadServerTruth{"auth-recording", true, true, {1, 2, 3}, true}};
    }) == 1);
    assert(authRecovered->load() && queue.items()[1].status == UploadQueueStatus::uploaded);

    assert(queue.enqueue({"retry-recording", "retry-directory", "retry-session", package, UploadQueueStatus::pending, {}, 0, "", owner.userId, owner.workspaceId}));
    DesktopUploadRecoveryScheduler retryScheduler(queue);
    assert(runWorker(retryScheduler, RecoveryTrigger::networkRecovered, [](const UploadCustodyItem&, auto) {
        return DesktopTransportResult{
            DesktopTransportStatus::retryableFailure,
            UploadServerTruth{"retry-recording", true, true, {11, 22, 33}, false},
        };
    }) == 1);
    assert(queue.items()[3].status == UploadQueueStatus::retry);
    const std::array<std::uint64_t, 3> retriedBytes{11, 22, 33};
    assert(queue.items()[3].acceptedBytes == retriedBytes);
    std::filesystem::remove_all(root);
    return 0;
}
