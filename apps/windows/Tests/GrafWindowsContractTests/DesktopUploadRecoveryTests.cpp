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
    // A finalize whose response was lost: the server drops the terminal session
    // from its active selection, so the meeting status is the only evidence that
    // this revision was already accepted. Without it the client would create a
    // second session for an immutable revision and then exhaust its retries.
    for (const auto status : {"ingested_pending_processing", "degraded", "INGESTED_PENDING_PROCESSING", " degraded "}) {
        const auto dropped = DesktopHttpTransport::decodeSyncState(
            std::string(R"({"meeting":{"meeting_id":"meeting-id","status":")") + status +
            R"("},"upload_session":null,"conflict":{"state":"none"}})", "local-id");
        assert(dropped && dropped->truth.finalized && !dropped->blockedByConflict);
        assert(!dropped->needsNewUploadSession && dropped->truth.meetingExists);
        assert(!dropped->truth.uploadSessionExists && dropped->sessionId.empty());
        const auto withProcessing = DesktopHttpTransport::decodeSyncState(
            std::string(R"({"meeting":{"meeting_id":"meeting-id","status":")") + status +
            R"("},"upload_session":null,"conflict":{"state":"processing_failed","next_action":"contact_operator"}})", "local-id");
        assert(withProcessing && withProcessing->truth.finalized && !withProcessing->blockedByConflict);
    }
    // A meeting that is still being ingested is not finalized, and its absent
    // session is not an instruction to open a new one.
    for (const auto status : {"created", "uploading", "processing", ""}) {
        const auto active = DesktopHttpTransport::decodeSyncState(
            std::string(R"({"meeting":{"meeting_id":"meeting-id","status":")") + status +
            R"("},"upload_session":null,"conflict":{"state":"none"}})", "local-id");
        assert(active && !active->truth.finalized && !active->needsNewUploadSession && !active->blockedByConflict);
    }
    // The server owns the retry classification; the port records it verbatim,
    // normalized, and keeps it empty when the server said nothing.
    const auto classified = DesktopHttpTransport::decodeSyncState(
        R"({"meeting":{"meeting_id":"meeting-id"},"upload_session":null,"conflict":{"state":"server_meeting_deleted"},"custody":{"retry_class":" PAUSED_UNTIL_ADMIN_ACTION "}})", "local-id");
    assert(classified && classified->blockedByConflict && classified->retryClass == "paused_until_admin_action");
    // The meeting id travels with the truth so the cabinet can bind the local
    // row to the server meeting it belongs to.
    assert(classified->truth.meetingId == "meeting-id" && classified->truth.meetingExists);
    const auto unclassified = DesktopHttpTransport::decodeSyncState(
        R"({"meeting":{"meeting_id":"meeting-id"},"upload_session":null,"conflict":{"state":"server_meeting_deleted"},"custody":{"retry_class":""}})", "local-id");
    assert(unclassified && unclassified->blockedByConflict && unclassified->retryClass.empty());
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

void testRetryClassClassification(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root / "package");
    DesktopUploadQueueService queue(root / "queue.json", root);
    assert(queue.load());
    // One row per server-owned retry class, plus an unclassified rejection that
    // must keep the ordinary retry path.
    const std::array<std::string, 5> ids{"class-user", "class-admin", "class-not-retryable", "class-terminal", "class-unclassified"};
    const std::array<std::string, 5> classes{"paused_until_user_action", "paused_until_admin_action",
        "not_retryable", "terminal", ""};
    for (std::size_t index = 0; index < ids.size(); ++index) {
        assert(queue.enqueue({ids[index], ids[index], "session", root / "package",
            UploadQueueStatus::retry, {}, 0, "", owner.userId, owner.workspaceId}));
    }
    DesktopUploadRecoveryScheduler scheduler(queue);
    assert(runWorker(scheduler, RecoveryTrigger::scheduled, [&](const UploadCustodyItem& item, auto) {
        std::size_t index = 0;
        while (index < ids.size() && ids[index] != item.localRecordingId) ++index;
        assert(index < ids.size());
        return DesktopTransportResult{DesktopTransportStatus::serverRejected,
            UploadServerTruth{item.localRecordingId, true, true, {1, 2, 3}, false}, "conflict", classes[index]};
    }) == static_cast<std::size_t>(ids.size()));

    // A sign-in is a user action the account flow can recover from.
    assert(queue.items()[0].status == UploadQueueStatus::needsAuth && queue.items()[0].safeReason == "auth_required");
    // An admin pause and a not-retryable conflict stop automatic attempts but
    // stay recoverable by an explicit request from the owner.
    assert(queue.items()[1].status == UploadQueueStatus::blocked && queue.items()[1].safeReason == "needs_admin");
    assert(queue.items()[2].status == UploadQueueStatus::blocked && queue.items()[2].safeReason == "not_retryable");
    // A terminal conflict cannot be sent at all.
    assert(queue.items()[3].status == UploadQueueStatus::quarantined && queue.items()[3].safeReason == "terminal_undelivered");
    // The server expressed no opinion, so the row keeps retrying.
    assert(queue.items()[4].status == UploadQueueStatus::retry && queue.items()[4].safeReason == "server_rejected");

    // None of the classified rows may be picked up by another automatic pass.
    std::size_t automatic = 0;
    assert(scheduler.startAsync(RecoveryTrigger::scheduled, [&](const UploadCustodyItem&, auto) {
        ++automatic;
        return DesktopTransportResult{DesktopTransportStatus::retryableFailure, std::nullopt};
    }));
    waitFor([&] { (void)scheduler.drain(); return !scheduler.busy(); });
    assert(automatic == 1);

    // An explicit request still rearms a blocked row, but never a terminally
    // quarantined one.
    assert(queue.requestRetry("class-admin"));
    assert(queue.items()[1].status == UploadQueueStatus::retry && queue.items()[1].attempts == 0);
    assert(!queue.requestRetry("class-terminal"));
    assert(queue.items()[3].status == UploadQueueStatus::quarantined);
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

void testSessionDeadlineHeader() {
    using namespace graf::windows;
    // The header is a deadline the server names for its own session. macOS reads
    // it with the same rule, so anything that is not a run of digits is not a
    // deadline: a decorated or negative value must not become a date in the past
    // or a date in the far future that the app would then write onto its cookie.
    assert(DesktopHttpTransport::epochSecondsFromHeader("1800000000") == 1800000000);
    assert(DesktopHttpTransport::epochSecondsFromHeader("0") == 0);
    for (const auto value : {"", " ", "abc", " 1800000000", "1800000000 ", "+1800000000",
                             "1800000000.5", "1.8e9", "-1800000000", "1800000000s"}) {
        assert(!DesktopHttpTransport::epochSecondsFromHeader(value).has_value());
    }
    // A value longer than any real instant is refused as a whole instead of
    // overflowing into a number the app would trust.
    assert(!DesktopHttpTransport::epochSecondsFromHeader("99999999999999999999").has_value());
    assert(DesktopHttpTransport::epochSecondsFromHeader("9999999999999999999").has_value());
}

void testRateLimitPause(const std::filesystem::path& root) {
    using namespace graf::windows;
    // Only a rate limit is a request to wait. macOS reads the same header with a
    // 60-second fallback, so a value this client cannot read must never turn into
    // "retry immediately", and an endpoint that is merely unavailable keeps the
    // client's own schedule.
    assert(DesktopHttpTransport::rateLimitPauseSeconds(429, "120") == 120);
    assert(DesktopHttpTransport::rateLimitPauseSeconds(429, "1") == 1);
    assert(DesktopHttpTransport::rateLimitPauseSeconds(429, "86400") == 86400);
    for (const auto value : {"", "0", "abc", " 30", "30 ", "+30", "3.5", "60s", "1e2", "-5"}) {
        assert(DesktopHttpTransport::rateLimitPauseSeconds(429, value) == 60);
    }
    // A pause longer than a day is not a pause this client will hold: it looks
    // again on its own, and the server can ask again. This also covers values so
    // long that they would otherwise overflow.
    for (const auto value : {"999999999", "99999999999999999999"}) {
        assert(DesktopHttpTransport::rateLimitPauseSeconds(429, value) == 86400);
    }
    for (const auto status : {200u, 301u, 401u, 403u, 404u, 408u, 500u, 503u}) {
        assert(DesktopHttpTransport::rateLimitPauseSeconds(status, "120") == 0);
    }

    std::filesystem::create_directories(root / "package");
    DesktopUploadQueueService queue(root / "queue.json", root);
    assert(queue.load());
    assert(queue.enqueue({"rate-limited", "rate-limited", "session", root / "package",
        UploadQueueStatus::retry, {}, 3, "", owner.userId, owner.workspaceId}));
    DesktopUploadRecoveryScheduler scheduler(queue);
    assert(runWorker(scheduler, RecoveryTrigger::scheduled, [](const UploadCustodyItem&, auto) {
        DesktopTransportResult result{DesktopTransportStatus::retryableFailure, std::nullopt};
        result.safeReason = "transport_unavailable";
        result.retryAfterSeconds = 1;
        return result;
    }) == 1);
    // Waiting is not failing: the row stays retryable with its attempt count, and
    // no automatic pass may start while the pause the server asked for is running.
    assert(queue.items()[0].status == UploadQueueStatus::retry && queue.items()[0].safeReason == "rate_limited");
    assert(queue.items()[0].attempts == 3);
    assert(scheduler.deferralRemainingMs() > 0);
    assert(!scheduler.startAsync(RecoveryTrigger::scheduled, [](const UploadCustodyItem&, auto) {
        return DesktopTransportResult{DesktopTransportStatus::uploaded, std::nullopt};
    }));

    // The pause is bounded, and the ordinary cadence takes over when it elapses.
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (scheduler.deferralRemainingMs() > 0) {
        assert(std::chrono::steady_clock::now() < deadline);
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    assert(runWorker(scheduler, RecoveryTrigger::scheduled, [](const UploadCustodyItem&, auto) {
        return DesktopTransportResult{DesktopTransportStatus::uploaded, std::nullopt};
    }) == 1);
    assert(queue.items()[0].status == UploadQueueStatus::uploaded);

    // A failure the server did not ask to delay still spends an attempt.
    assert(queue.enqueue({"plain-failure", "plain-failure", "session", root / "package",
        UploadQueueStatus::retry, {}, 3, "", owner.userId, owner.workspaceId}));
    assert(runWorker(scheduler, RecoveryTrigger::scheduled, [](const UploadCustodyItem&, auto) {
        return DesktopTransportResult{DesktopTransportStatus::retryableFailure, std::nullopt};
    }) == 1);
    assert(queue.items()[1].status == UploadQueueStatus::retry && queue.items()[1].attempts == 4);
    assert(queue.items()[1].safeReason == "transport_unavailable" && scheduler.deferralRemainingMs() == 0);
}

void testConfirmedIdentitySnapshot() {
    using namespace graf::windows;
    // The shell confirms the account once for the session it holds. The transport
    // reuses that snapshot instead of asking /auth/me for every attempt, and only
    // falls back to the server when it has no confirmed identity. The count of
    // requests is the point of the test: the old behaviour asked for every try.
    std::size_t calls = 0;
    const DesktopHttpTransport::IdentityGet counter = [&calls](const DesktopHttpConfig&, std::string_view path) {
        ++calls;
        const auto spaces = "{\"spaces\":[{\"id\":\"" + owner.workspaceId + "\",\"active\":true}]}";
        return DesktopHttpTransport::IdentityResponse{
            200, path == "/desktop/settings/spaces" ? spaces : meResponse(owner.userId, owner.workspaceId), false};
    };

    DesktopHttpConfig config;
    config.sessionToken = "00000000-0000-4000-8000-0000000000ff";
    config.workspaceId = owner.workspaceId;
    config.confirmedIdentity = owner;
    const auto snapshot = DesktopHttpTransport::resolveAccountIdentity(config, counter);
    assert(snapshot.identity && snapshot.identity->userId == owner.userId &&
           snapshot.identity->workspaceId == owner.workspaceId);
    assert(calls == 0);

    // Without a snapshot the client asks, and an unknown workspace still needs the
    // spaces bootstrap before /auth/me.
    auto unresolved = config;
    unresolved.confirmedIdentity.reset();
    assert(DesktopHttpTransport::resolveAccountIdentity(unresolved, counter).identity.has_value());
    assert(calls == 1);
    unresolved.workspaceId.clear();
    assert(DesktopHttpTransport::resolveAccountIdentity(unresolved, counter).identity.has_value());
    assert(calls == 3);

    // A snapshot is not authority by itself: it must describe a real account and
    // agree with the workspace it travels with. A cancelled or incomplete attempt
    // asks nothing at all.
    auto mismatched = config;
    mismatched.workspaceId = owner.userId;
    assert(!DesktopHttpTransport::resolveAccountIdentity(mismatched, counter).identity);
    auto invalid = config;
    invalid.confirmedIdentity = DesktopAccountIdentity{"not-a-uuid", owner.workspaceId};
    assert(!DesktopHttpTransport::resolveAccountIdentity(invalid, counter).identity);
    auto unclaimed = config;
    unclaimed.confirmedIdentity.reset();
    unclaimed.sessionToken.clear();
    assert(!DesktopHttpTransport::resolveAccountIdentity(unclaimed, counter).identity);
    auto cancelledConfig = config;
    cancelledConfig.cancellation = std::make_shared<const std::atomic_bool>(true);
    const auto cancelledResult = DesktopHttpTransport::resolveAccountIdentity(cancelledConfig, counter);
    assert(!cancelledResult.identity && cancelledResult.status == DesktopTransportStatus::retryableFailure);
    assert(calls == 3);

    // The owner check still runs against whatever identity was resolved, and the
    // old local row of another account is refused before any audio request.
    UploadCustodyItem foreign;
    foreign.localRecordingId = "foreign";
    foreign.ownerUserId = owner.workspaceId;
    foreign.ownerWorkspaceId = owner.workspaceId;
    assert(DesktopHttpTransport::ownerBlockReason(foreign, snapshot.identity) == "account_mismatch");
}

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
    testRetryClassClassification(root / "retry-class");
    testRateLimitPause(root / "rate-limit");
    testSessionDeadlineHeader();
    testConfirmedIdentitySnapshot();
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
