// The cabinet's settings pages ask the app the way macOS lets them ask it, and the
// page validates every answer before it shows or saves anything. These checks hold
// the two ends of that agreement: what the app accepts as a request, and what it
// sends back.
#include "../../RecApp/Web/NativeSettingsBridge.h"
#include "../../RecApp/Shell/MeetingReminderModel.h"
#include "../../RecApp/Shell/RecordingNoticePresenter.h"
#include "../../RecApp/Shell/MeetingReminderPresenter.h"
#include "../../RecApp/Storage/Sha256.h"
#include "../../RecApp/Upload/DesktopUploadQueueService.h"

#ifdef NDEBUG
#undef NDEBUG
#endif

#include <cassert>
#include <algorithm>
#include <cstdio>
#include <string>
#include <limits>
#include <stdexcept>

using graf::windows::NativeSettingsBridge::Action;
using graf::windows::NativeSettingsBridge::Target;

namespace {

void testUserTimeMetadataIsBoundedDataOnly() {
    using graf::windows::DesktopApiClient;
    const std::string valid = R"({"userId":"11111111-1111-1111-1111-111111111111","workspaceId":"22222222-2222-2222-2222-222222222222","sessionId":"33333333-3333-3333-3333-333333333333","timeZone":"Asia/Kathmandu","documentURL":"https://one.example/desktop/meetings"})";
    auto raw = valid;
    const auto result = DesktopApiClient::decodeUserTimeMetadata(raw);
    assert(result && result->userId == "11111111-1111-1111-1111-111111111111");
    assert(result->workspaceId == "22222222-2222-2222-2222-222222222222");
    assert(result->sessionId == "33333333-3333-3333-3333-333333333333");
    assert(result->timeZone == "Asia/Kathmandu" && result->documentUrl == "https://one.example/desktop/meetings");
    raw.assign(2048, 'x'); // No views into ExecuteScript's temporary JSON.
    assert(result->timeZone == "Asia/Kathmandu");
    const auto replace = [&](std::string_view from, std::string_view to) {
        auto text = valid;
        const auto at = text.find(from); assert(at != std::string::npos);
        text.replace(at, from.size(), to); return text;
    };
    for (const auto zone : {"", "UTC", "America/New_York"}) {
        assert(DesktopApiClient::decodeUserTimeMetadata(replace("Asia/Kathmandu", zone)));
    }
    assert(DesktopApiClient::decodeUserTimeMetadata(replace("\"userId\"", "\"\\u0075serId\"")));
    assert(DesktopApiClient::decodeUserTimeMetadata(replace("Asia/Kathmandu", "Asia\\/Kathmandu")));
    assert(DesktopApiClient::decodeUserTimeMetadata(replace("Asia/Kathmandu", std::string(98, 'A') + "/B")));
    assert(DesktopApiClient::decodeUserTimeMetadata(replace("https://one.example/desktop/meetings", std::string(1024, 'x'))));
    auto boundary = valid; boundary.resize(2048, ' ');
    assert(DesktopApiClient::decodeUserTimeMetadata(boundary));
    boundary += ' '; assert(!DesktopApiClient::decodeUserTimeMetadata(boundary));
    for (const auto& bad : {
        std::string{}, std::string("null"), std::string("[]"), valid + "x",
        replace("\"timeZone\":\"Asia/Kathmandu\",", ""),
        replace("\"Asia/Kathmandu\"", "null"), replace("\"Asia/Kathmandu\"", "true"),
        replace("\"Asia/Kathmandu\"", "[]"), replace("\"Asia/Kathmandu\"", "{\"timeZone\":\"UTC\"}"),
        replace("\"userId\"", "\"unknown\""),
        replace("\"userId\"", "\"userId\":\"11111111-1111-1111-1111-111111111111\",\"userId\""),
        replace("\"userId\"", "\"userId\":\"11111111-1111-1111-1111-111111111111\",\"\\u0075serId\""),
        replace("\"timeZone\"", "\"extra\":\"UTC\",\"timeZone\""),
        replace("11111111-1111-1111-1111-111111111111", ""),
        replace("11111111-1111-1111-1111-111111111111", "00000000-0000-0000-0000-000000000000"),
        replace("22222222-2222-2222-2222-222222222222", "22222222-2222-2222-2222-22222222222A"),
        replace("33333333-3333-3333-3333-333333333333", "not-a-session"),
        replace("Asia/Kathmandu", "GMT"), replace("Asia/Kathmandu", "Asia/Kathmandu "),
        replace("Asia/Kathmandu", "Asia/\\u0000"), replace("Asia/Kathmandu", "Asia/\\n"),
        replace("Asia/Kathmandu", "Asia/\\u007f"), replace("Asia/Kathmandu", "Asia/\\u0410"),
        replace("Asia/Kathmandu", "Asia/\\ud800"), replace("Asia/Kathmandu", std::string("Asia/\xc0\xaf")),
        replace("Asia/Kathmandu", std::string(99, 'A') + "/B"),
        replace("https://one.example/desktop/meetings", ""),
        replace("https://one.example/desktop/meetings", "https://one.example/\\n"),
        replace("https://one.example/desktop/meetings", std::string(1025, 'x')),
    }) assert(!DesktopApiClient::decodeUserTimeMetadata(bad));
    // This decoder does NOT attest route, account, native zone support or auth.
    assert(DesktopApiClient::decodeUserTimeMetadata(replace("Asia/Kathmandu", "Invalid/NoSuchZone")));
    assert(DesktopApiClient::decodeUserTimeMetadata(replace("https://one.example/desktop/meetings", "https://external.example/")));
}

graf::windows::UploadCustodyItem problemRow(std::string id, std::string session,
    graf::windows::UploadQueueStatus status, std::uint64_t updatedAt = 900'000) {
    graf::windows::UploadCustodyItem row;
    row.localRecordingId = std::move(id); row.sessionId = std::move(session);
    row.ownerUserId = "owner"; row.ownerWorkspaceId = "workspace";
    row.status = status; row.updatedAtMs = updatedAt;
    return row;
}

void testLocalProblemsGroupSessionAndKeepStableIdentity() {
    using namespace graf::windows;
    const LocalProblemContext context{"https://one.example", "owner", "workspace"};
    std::vector<UploadCustodyItem> rows{
        problemRow("item-b", "session", UploadQueueStatus::quarantined, 999'000),
        problemRow("item-a", "session", UploadQueueStatus::needsAuth, 998'000)};
    const CurrentCaptureProblem capture{"session", context, true};
    auto projected = projectLocalRecordingProblems(context, context, rows, true, capture, 1'000'000);
    assert(projected.size() == 1);
    assert(projected[0].sessionId == "session" && projected[0].state == LocalProblemState::problem);
    assert(projected[0].fresh && projected[0].occurredAtMs == 998'000);
    const auto identity = projected[0].incidentId;
    assert(!identity.empty());
    rows[0].safeReason = "private text is not an identity"; rows[0].attempts = 14;
    rows[0].updatedAtMs = 1'000'000;
    std::swap(rows[0], rows[1]);
    projected = projectLocalRecordingProblems(context, context, rows, true, std::nullopt, 1'000'001);
    assert(projected.size() == 1 && projected[0].incidentId == identity);
    assert(projected[0].incidentId.find("private") == std::string::npos);
    rows.push_back(problemRow("item-c", "other-session", UploadQueueStatus::blocked));
    const auto two = projectLocalRecordingProblems(context, context, rows, true, capture, 1'000'001);
    assert(two.size() == 2 && two[0].incidentId != two[1].incidentId);
    std::reverse(rows.begin(), rows.end());
    const auto reordered = projectLocalRecordingProblems(context, context, rows, true, capture, 1'000'001);
    assert(reordered.size() == two.size());
    for (std::size_t i = 0; i < two.size(); ++i) assert(reordered[i].incidentId == two[i].incidentId);
}

void testLocalProblemsClassifyOnlyTypedStatesAndExactRetryReason() {
    using namespace graf::windows;
    const LocalProblemContext context{"https://one.example", "owner", "workspace"};
    for (const auto status : {UploadQueueStatus::pending, UploadQueueStatus::uploading,
        UploadQueueStatus::retry, UploadQueueStatus::needsAuth, UploadQueueStatus::uploaded,
        UploadQueueStatus::quarantined, UploadQueueStatus::blocked}) {
        auto row = problemRow("item", "session", status);
        row.safeReason = "some_auth_failed_upload_blocked_private_text";
        row.processingStatus = "failed";
        const auto result = projectLocalRecordingProblems(context, context, {row}, true, std::nullopt, 1'000'000);
        assert(result.size() == 1);
        const auto expected = status == UploadQueueStatus::uploaded ? LocalProblemState::positivelyResolved :
            status == UploadQueueStatus::needsAuth || status == UploadQueueStatus::quarantined || status == UploadQueueStatus::blocked
                ? LocalProblemState::problem : LocalProblemState::unknown;
        assert(result[0].state == expected);
        assert(result[0].fresh == (expected == LocalProblemState::problem));
    }
    for (const auto reason : {"manual_retry", "auth_recovered", "rate_limited", "transport_unavailable",
        "retry_budget_exhausted", "prefix_retry_budget_exhausted", "retry_budget_exhausted_suffix"}) {
        auto row = problemRow("item", "session", UploadQueueStatus::retry);
        row.safeReason = reason;
        const auto result = projectLocalRecordingProblems(context, context, {row}, true, std::nullopt, 1'000'000);
        assert(result.size() == 1 && result[0].state ==
            (row.safeReason == "retry_budget_exhausted" ? LocalProblemState::problem : LocalProblemState::unknown));
    }
}

void testLocalProblemsFreshnessIsStrictAndDoesNotResolveOldProblems() {
    using namespace graf::windows;
    const LocalProblemContext context{"https://one.example", "owner", "workspace"};
    for (const auto stamp : {0ULL, 700'000ULL, 700'001ULL, 1'000'000ULL, 1'000'001ULL,
        std::numeric_limits<unsigned long long>::max()}) {
        const auto row = problemRow("item", "session", UploadQueueStatus::quarantined, stamp);
        const auto result = projectLocalRecordingProblems(context, context, {row}, true, std::nullopt, 1'000'000);
        assert(result.size() == 1 && result[0].state == LocalProblemState::problem);
        assert(result[0].fresh == (stamp > 700'000 && stamp <= 1'000'000));
    }
    auto oldProblem = problemRow("old", "session", UploadQueueStatus::blocked, 500'000);
    auto newHealthy = problemRow("new", "session", UploadQueueStatus::uploaded, 999'999);
    auto result = projectLocalRecordingProblems(context, context, {oldProblem, newHealthy}, true, std::nullopt, 1'000'000);
    assert(result.size() == 1 && result[0].state == LocalProblemState::problem && !result[0].fresh);
    const CurrentCaptureProblem capture{"session", context, true};
    result = projectLocalRecordingProblems(context, context, {oldProblem}, true, capture, 1'000'000);
    assert(result[0].state == LocalProblemState::problem && result[0].fresh);
    result = projectLocalRecordingProblems(context, context, {}, true, capture, 1'000'000);
    assert(result.size() == 1 && result[0].fresh && result[0].occurredAtMs == 1'000'000);
}

void testLocalProblemsRequireExactOwnershipAndFrozenCaptureContext() {
    using namespace graf::windows;
    const LocalProblemContext context{"https://one.example", "owner", "workspace"};
    const auto row = problemRow("item", "session", UploadQueueStatus::uploaded);
    for (const auto& other : {LocalProblemContext{"https://two.example", "owner", "workspace"},
        LocalProblemContext{"https://one.example", "other", "workspace"},
        LocalProblemContext{"https://one.example", "owner", "other"},
        LocalProblemContext{"https://one.example/", "owner", "workspace"},
        LocalProblemContext{"https://one.example", "OWNER", "workspace"},
        LocalProblemContext{"", "owner", "workspace"},
        LocalProblemContext{"https://one.example", "", "workspace"},
        LocalProblemContext{"https://one.example", "owner", ""}, LocalProblemContext{}}) {
        const auto result = projectLocalRecordingProblems(context, other, {row}, true, std::nullopt, 1'000'000);
        assert(result.size() == 1 && result[0].state == LocalProblemState::unknown && !result[0].fresh);
        const CurrentCaptureProblem capture{"session", other, true};
        const auto blocked = projectLocalRecordingProblems(context, context, {row}, true, capture, 1'000'000);
        assert(blocked.size() == 1 && blocked[0].state == LocalProblemState::unknown && !blocked[0].fresh);
    }
    for (const auto owner : {"", "other", "OWNER"}) {
        auto foreign = problemRow("foreign", "session", UploadQueueStatus::blocked);
        foreign.ownerUserId = owner;
        const auto result = projectLocalRecordingProblems(context, context, {row, foreign}, true, std::nullopt, 1'000'000);
        assert(result.size() == 1 && result[0].state == LocalProblemState::unknown && !result[0].fresh);
    }
    auto foreign = row; foreign.ownerWorkspaceId = "other";
    const auto result = projectLocalRecordingProblems(context, context, {foreign}, true, std::nullopt, 1'000'000);
    assert(result[0].state == LocalProblemState::unknown);
    const auto unbound = projectLocalRecordingProblems({}, {}, {row}, true,
        CurrentCaptureProblem{"session", {}, true}, 1'000'000);
    assert(unbound.size() == 1 && unbound[0].state == LocalProblemState::unknown);
}

void testLocalProblemsResolveOnlyCompleteAllUploadedSessions() {
    using namespace graf::windows;
    const LocalProblemContext context{"https://one.example", "owner", "workspace"};
    auto a = problemRow("a", "session", UploadQueueStatus::uploaded);
    auto b = problemRow("b", "session", UploadQueueStatus::uploaded);
    const auto classify = [&](bool complete, std::optional<CurrentCaptureProblem> capture = std::nullopt) {
        const auto result = projectLocalRecordingProblems(context, context, {a, b}, complete, capture, 1'000'000);
        assert(result.size() == 1); return result[0].state;
    };
    assert(classify(true) == LocalProblemState::positivelyResolved);
    assert(classify(false) == LocalProblemState::unknown);
    assert(classify(true, CurrentCaptureProblem{"session", context, true}) == LocalProblemState::problem);
    assert(classify(true, CurrentCaptureProblem{"session", context, false}) == LocalProblemState::positivelyResolved);
    for (const auto reason : {"manual_retry", "auth_recovered"}) {
        b.status = UploadQueueStatus::retry; b.safeReason = reason;
        assert(classify(true) == LocalProblemState::unknown);
    }
    b.status = UploadQueueStatus::quarantined;
    assert(classify(false) == LocalProblemState::problem); // partial known failure is still a failure
    assert(projectLocalRecordingProblems(context, context, {}, true, std::nullopt, 1'000'000).empty());
    const auto captureOnly = projectLocalRecordingProblems(context, context, {}, true,
        CurrentCaptureProblem{"session", context, false}, 1'000'000);
    assert(captureOnly.size() == 1 && captureOnly[0].state == LocalProblemState::unknown);
}

void testProtectedLocalProblemsPreserveClassificationAndOwnership() {
    using namespace graf::windows;
    const auto baseline = CustodyOwnedMemory::usedBytes();
    const LocalProblemContext context{"https://one.example", "owner", "workspace"};
    const auto compare = [&](const std::vector<UploadCustodyItem>& rows, bool complete,
        const LocalProblemContext& queueContext, const std::optional<CurrentCaptureProblem>& capture = std::nullopt) {
        CustodyVector<ProtectedUploadQueueValue::Item> protectedRows;
        for (const auto& row : rows) {
            ProtectedUploadQueueValue::Item item;
            item.localRecordingId = row.localRecordingId.c_str(); item.sessionId = row.sessionId.c_str();
            item.ownerUserId = row.ownerUserId.c_str(); item.ownerWorkspaceId = row.ownerWorkspaceId.c_str();
            item.status = row.status; item.safeReason = row.safeReason.c_str(); item.updatedAtMs = row.updatedAtMs;
            protectedRows.push_back(std::move(item));
        }
        const auto expected = projectLocalRecordingProblems(context, queueContext, rows, complete, capture, 1'000'000);
        const auto actual = projectProtectedLocalRecordingProblems(context, queueContext, protectedRows, complete, capture, 1'000'000);
        assert(actual.size() == expected.size() && "protected_projection_preserves_all_sessions");
        for (std::size_t i = 0; i < actual.size(); ++i) {
            assert(std::string_view(actual[i].sessionId) == expected[i].sessionId);
            assert(std::string_view(actual[i].incidentId) == expected[i].incidentId);
            assert(actual[i].state == expected[i].state && actual[i].fresh == expected[i].fresh);
            assert(actual[i].occurredAtMs == expected[i].occurredAtMs);
        }
    };
    for (const bool complete : {false, true}) {
        for (const auto status : {UploadQueueStatus::pending, UploadQueueStatus::uploading,
            UploadQueueStatus::retry, UploadQueueStatus::needsAuth, UploadQueueStatus::uploaded,
            UploadQueueStatus::quarantined, UploadQueueStatus::blocked}) {
            auto row = problemRow("item", "session", status);
            for (const auto reason : {"auth_recovered", "retry_budget_exhausted", "retry_budget_exhausted_suffix"}) {
                row.safeReason = reason;
                compare({row}, complete, context);
            }
        }
        auto row = problemRow("item", "session", UploadQueueStatus::uploaded);
        for (const auto& other : {LocalProblemContext{"https://other.example", "owner", "workspace"},
            LocalProblemContext{"https://one.example", "other", "workspace"},
            LocalProblemContext{"https://one.example", "owner", "other"}, LocalProblemContext{}}) {
            compare({row}, complete, other);
            compare({row}, complete, context, CurrentCaptureProblem{"session", other, true});
        }
        compare({row}, complete, context, CurrentCaptureProblem{"session", context, true});
        compare({}, complete, context, CurrentCaptureProblem{"capture-only", context, false});
        compare({}, complete, context);
        for (const auto stamp : {0ULL, 700'000ULL, 700'001ULL, 1'000'000ULL, 1'000'001ULL})
            compare({problemRow("item", "session", UploadQueueStatus::blocked, stamp)}, complete, context);
        std::vector<UploadCustodyItem> inventory;
        for (int i = 0; i < 65; ++i) inventory.push_back(problemRow("item-" + std::to_string(i),
            "session-" + std::to_string(i), UploadQueueStatus::uploaded));
        compare(inventory, complete, context); // Inventory is not a bounded 32-command flight.
        auto foreign = inventory.front(); foreign.localRecordingId = "foreign"; foreign.ownerUserId = "other";
        inventory.push_back(foreign); compare(inventory, complete, context);
        foreign.ownerUserId.clear(); compare({row, foreign}, complete, context);
        row.localRecordingId.clear(); compare({row}, complete, context);
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
}

void testProtectedLocalProblemsOwnResultsAndRefuseQuotaExhaustion() {
    using namespace graf::windows;
    const auto baseline = CustodyOwnedMemory::usedBytes();
    const LocalProblemContext context{"https://one.example", "owner", "workspace"};
    {
        CustodyVector<ProtectedLocalProblemProjection> result;
        const std::string session(256, 's');
        {
            CustodyVector<ProtectedUploadQueueValue::Item> rows;
            ProtectedUploadQueueValue::Item item;
            item.localRecordingId = "item"; item.sessionId = session.c_str(); item.status = UploadQueueStatus::needsAuth;
            item.ownerUserId = "owner"; item.ownerWorkspaceId = "workspace";
            rows.push_back(std::move(item));
            result = projectProtectedLocalRecordingProblems(context, context, rows, false, std::nullopt, 1'000'000);
        }
        assert(result.size() == 1 && std::string_view(result[0].sessionId) == session);
        assert(std::string_view(result[0].incidentId) == "capture-problem:" + session);
        assert(result[0].state == LocalProblemState::problem && CustodyOwnedMemory::usedBytes() > baseline);
        const CustodyVector<ProtectedUploadQueueValue::Item> noRows;
        const std::optional<CurrentCaptureProblem> capture{CurrentCaptureProblem{session, context, false}};
        CustodyAllocator<char> allocator;
        const auto remaining = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
        auto* reserved = allocator.allocate(remaining);
        bool refused = false;
        try {
            (void)projectProtectedLocalRecordingProblems(context, context, noRows, true, capture, 1'000'000);
        } catch (const std::bad_alloc&) { refused = true; }
        allocator.deallocate(reserved, remaining);
        assert(refused && "protected_projection_quota_refusal_is_not_empty_success");
        assert(result[0].state == LocalProblemState::problem); // Failed refresh cannot resolve the retained result.
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
}

void testF277NotificationContractBeforeImplementation() {
    using namespace graf::windows;
    using namespace NativeSettingsBridge;
    const auto quiet = parseNotificationRequest(
        R"({"version":2,"nonce":"current","action":"set","field":"quiet","value":true})", "current");
    assert(quiet && quiet->booleanValue);
    assert(!parseNotificationRequest(R"({"version":1,"nonce":"current","action":"read"})", "current"));
    assert(!parseNotificationRequest(R"({"version":2,"nonce":"current","action":"requestPermission"})", "current"));
    const auto reply = notificationSettingsReply({}, true);
    assert(reply.find("\"version\":2") != std::string::npos);
    assert(reply.find("\"quiet\":false") != std::string::npos);
    assert(reply.find("permission") == std::string::npos);
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", false, ""};
    assert(MeetingReminderModel::deadline(event) == 10'060);
    assert(!MeetingReminderModel::eligible(event, 9'100, false));
    assert(MeetingReminderModel::eligible(event, 9'940, false));
}

struct ReminderDisk {
    std::map<std::string, std::string> values;
    bool writable = true, loseWrite = false;
    graf::windows::NotificationPreferenceStore store() {
        return {
            [this](std::string_view key) -> std::optional<std::string> {
                const auto it = values.find(std::string(key));
                return it == values.end() ? std::nullopt : std::optional<std::string>(it->second);
            },
            [this](std::string_view key, std::string_view value) {
                if (!writable) return false;
                if (!loseWrite) values[std::string(key)] = value;
                return true;
            }};
    }
};

void testLocalProblemProjectionDoesNotForgetPersistedClaims() {
    using namespace graf::windows;
    const LocalProblemContext context{"https://one.example", "owner", "workspace"};
    ReminderDisk disk;
    auto row = problemRow("item", "session", UploadQueueStatus::blocked);
    auto projected = projectLocalRecordingProblems(context, context, {row}, true, std::nullopt, 1'000'000);
    assert(projected.size() == 1 && projected[0].state == LocalProblemState::problem);
    const auto id = projected[0].incidentId;
    assert(disk.store().claimProblem(context.origin, context.owner, context.workspace, id));
    const auto claimed = disk.values;
    // Pure projection has no storage capability. Neither absence nor a retry is
    // a signal for its consumer to erase the durable deny marker.
    assert(projectLocalRecordingProblems(context, context, {}, false, std::nullopt, 1'000'000).empty());
    row.status = UploadQueueStatus::retry; row.safeReason = "manual_retry";
    projected = projectLocalRecordingProblems(context, context, {row}, true, std::nullopt, 1'000'000);
    assert(projected[0].state == LocalProblemState::unknown && projected[0].incidentId == id);
    assert(row.status == UploadQueueStatus::retry && row.safeReason == "manual_retry");
    row.status = UploadQueueStatus::uploaded;
    projected = projectLocalRecordingProblems(context, context, {row}, false, std::nullopt, 1'000'000);
    assert(projected[0].state == LocalProblemState::unknown);
    assert(disk.values == claimed && !disk.store().claimProblem(context.origin, context.owner, context.workspace, id));
    projected = projectLocalRecordingProblems(context, context, {row}, true, std::nullopt, 1'000'000);
    assert(projected[0].state == LocalProblemState::positivelyResolved);
    assert(disk.values == claimed); // only the explicit consumer action below mutates storage
    assert(disk.store().resolveProblem(context.origin, context.owner, context.workspace, projected[0].incidentId));
    row.status = UploadQueueStatus::blocked;
    projected = projectLocalRecordingProblems(context, context, {row}, true, std::nullopt, 1'000'001);
    assert(projected[0].state == LocalProblemState::problem && projected[0].incidentId == id);
    assert(disk.store().claimProblem(context.origin, context.owner, context.workspace, id));
}

void testProblemClaimsPersistUntilExplicitResolution() {
    using namespace graf::windows;
    ReminderDisk disk;
    const auto claim = [&] { return disk.store().claimProblem("https://one.example", "a", "w", "session:audio-failed"); };
    assert(claim());
    assert(!claim()); // a fresh store object represents restart; no in-memory authority
    assert(disk.store().claimProblem("https://one.example", "a", "w", "session:upload-blocked"));
    const auto saved = disk.values;
    // Partial/empty calendar state and context reset have no authority to resolve a problem.
    MeetingReminderModel model; model.bind("a", "w", "https://one.example");
    assert(model.update({"a", "w", {}}, model.epoch()));
    assert(disk.store().pruneMeetingReceipts(model.contextKey(), 1e12));
    model.invalidate();
    assert(!claim() && disk.values == saved); // no timeout-based problem cleanup
    assert(disk.store().resolveProblem("https://one.example", "a", "w", "unknown-problem"));
    assert(disk.values == saved);
    assert(disk.store().resolveProblem("https://one.example", "a", "w", "session:audio-failed"));
    assert(disk.store().resolveProblem("https://one.example", "a", "w", "session:audio-failed"));
    assert(claim()); // a new occurrence after positively confirmed recovery
    assert(!disk.store().claimProblem("https://one.example", "a", "w", "session:upload-blocked"));
}

void testProblemClaimsArePrivateAndContextScoped() {
    using namespace graf::windows;
    ReminderDisk disk;
    const std::string incident = "synthetic-session/type-with-private-text";
    assert(disk.store().claimProblem("https://one.example", "a", "w", incident));
    assert(!disk.store().claimProblem("HTTPS://ONE.EXAMPLE:443/", "A", "W", incident));
    assert(disk.store().claimProblem("https://two.example", "a", "w", incident));
    assert(disk.store().claimProblem("https://one.example", "b", "w", incident));
    assert(disk.store().claimProblem("https://one.example", "a", "other", incident));
    assert(disk.store().resolveProblem("https://two.example", "a", "w", incident));
    assert(!disk.store().claimProblem("https://one.example", "a", "w", incident));
    for (const auto& [key, value] : disk.values) {
        assert(key.size() == 64 + std::string(".problems").size());
        assert(key.find("example") == std::string::npos);
        assert(value.find("synthetic") == std::string::npos && value.find("private") == std::string::npos);
        assert(value.find("https") == std::string::npos);
    }
    const auto saved = disk.values;
    for (int empty = 0; empty < 4; ++empty) {
        const auto origin = empty == 0 ? "" : "https://one.example";
        const auto owner = empty == 1 ? "" : "a";
        const auto workspace = empty == 2 ? "" : "w";
        const auto identity = empty == 3 ? "" : "incident";
        assert(!disk.store().claimProblem(origin, owner, workspace, identity));
        assert(!disk.store().resolveProblem(origin, owner, workspace, identity));
    }
    assert(disk.values == saved);
}

void testProblemClaimsVerifyBothWritesAndFailClosedReads() {
    using namespace graf::windows;
    ReminderDisk disk;
    auto store = disk.store();
    disk.loseWrite = true;
    assert(!store.claimProblem("https://one.example", "a", "w", "incident"));
    disk.loseWrite = false; disk.writable = false;
    assert(!store.claimProblem("https://one.example", "a", "w", "incident"));
    disk.writable = true;
    assert(store.claimProblem("https://one.example", "a", "w", "incident"));
    const auto saved = disk.values;
    disk.loseWrite = true;
    assert(!store.resolveProblem("https://one.example", "a", "w", "incident"));
    disk.loseWrite = false; disk.writable = false;
    assert(!store.resolveProblem("https://one.example", "a", "w", "incident"));
    assert(disk.values == saved && !store.claimProblem("https://one.example", "a", "w", "incident"));
    disk.writable = true;
    const auto read = store.read;
    store.read = [](std::string_view) -> std::optional<std::string> { throw std::runtime_error("synthetic-read-error"); };
    assert(!store.claimProblem("https://one.example", "a", "w", "new-incident"));
    assert(!store.resolveProblem("https://one.example", "a", "w", "incident"));
    store.read = [](std::string_view) -> std::optional<std::string> { return std::string{}; }; // native read failure sentinel
    assert(!store.claimProblem("https://one.example", "a", "w", "new-incident"));
    assert(!store.resolveProblem("https://one.example", "a", "w", "incident"));
    assert(disk.values == saved);
    store.read = read;
    store.write = [](std::string_view, std::string_view) -> bool { throw std::runtime_error("synthetic-write-error"); };
    assert(!store.claimProblem("https://one.example", "a", "w", "new-incident"));
    assert(!store.resolveProblem("https://one.example", "a", "w", "incident"));
    assert(disk.values == saved);
    store = disk.store();
    int reads = 0;
    store.read = [&](std::string_view key) -> std::optional<std::string> {
        if (++reads > 1) return std::string{}; // failed verification after a successful write
        return read(key);
    };
    assert(!store.claimProblem("https://one.example", "a", "w", "new-incident"));
    assert(!disk.store().claimProblem("https://one.example", "a", "w", "new-incident"));
}

void testProblemClaimsCorruptionAndCapacityDoNotForgetIncidents() {
    using namespace graf::windows;
    MeetingReminderModel model; model.bind("a", "w", "https://one.example");
    const auto key = model.contextKey() + ".problems";
    const auto digest = sha256("incident");
    for (const auto& bytes : {std::string{}, std::string("problems-v2\n"),
        "problems-v1\n" + digest, "problems-v1\n" + digest + " extra\n",
        "problems-v1\n" + digest + "\n" + digest + "\n",
        "problems-v1\n" + std::string(64, 'z') + "\n", std::string(128 * 1024 + 1, 'x')}) {
        ReminderDisk disk; disk.values[key] = bytes;
        assert(!disk.store().claimProblem("https://one.example", "a", "w", "incident"));
        assert(!disk.store().resolveProblem("https://one.example", "a", "w", "incident"));
        assert(disk.values[key] == bytes);
    }
    ReminderDisk disk;
    std::string bytes = "problems-v1\n";
    for (int i = 0; i < 1024; ++i) bytes += sha256(std::to_string(i)) + "\n";
    disk.values[key] = bytes;
    assert(!disk.store().claimProblem("https://one.example", "a", "w", "overflow"));
    assert(disk.values[key] == bytes);
    assert(disk.store().resolveProblem("https://one.example", "a", "w", "0"));
    assert(disk.store().claimProblem("https://one.example", "a", "w", "overflow"));
    assert(!disk.store().claimProblem("https://one.example", "a", "w", "1"));
}

void testF277PreferencesMigrateAndVerifyWrites() {
    using namespace graf::windows;
    ReminderDisk disk;
    disk.values[sha256("a")] = "v1:\n0115";
    auto preferences = disk.store().load("a");
    assert(!preferences.reminders && preferences.showTitles && preferences.sound);
    assert(preferences.offsetMinutes == 5 && !preferences.quiet);
    preferences.quiet = true;
    assert(disk.store().save(preferences, "a"));
    assert(disk.store().load("a").quiet && !disk.store().load("b").quiet);
    disk.loseWrite = true; preferences.quiet = false;
    assert(!disk.store().save(preferences, "a"));
    assert(disk.store().load("a").quiet);
    preferences.offsetMinutes = 2;
    assert(!disk.store().save(preferences, "a"));
}

void testF277OffsetsContextAndLinkIdentity() {
    using namespace graf::windows;
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", true, "https://meet.example.com/a"};
    for (int offset : {0, 1, 5}) {
        const auto due = event.startsAt - offset * 60;
        assert(!MeetingReminderModel::eligible(event, due - .001, false, offset));
        assert(MeetingReminderModel::eligible(event, due, false, offset));
        assert(MeetingReminderModel::eligible(event, due + 119.999, false, offset));
        assert(!MeetingReminderModel::eligible(event, due + 120, false, offset));
        assert(!MeetingReminderModel::eligible(event, due, true, offset));
        assert(MeetingReminderModel::deadline(event, offset) == due + 120);
    }
    assert(!MeetingReminderModel::eligible(event, 10'000, false, 2));
    assert(!MeetingReminderModel::eligible(event, std::numeric_limits<double>::quiet_NaN(), false));
    MeetingReminderModel model;
    model.bind("a", "w", "https://one.example");
    assert(model.update({"a", "w", {event}}, model.epoch()));
    auto target = model.actionTarget(event);
    const auto key = model.dismissalKey(event);
    event.meetingUrl = "https://meet.example.com/b";
    assert(model.update({"a", "w", {event}}, model.epoch()));
    assert(!model.revalidate(target, 9'950, false));
    target = model.actionTarget(event); event.meetingLinkPresent = false;
    assert(model.update({"a", "w", {event}}, model.epoch()));
    assert(!model.revalidate(target, 9'950, false));
    model.bind("a", "w", "https://two.example");
    assert(model.dismissalKey(event) != key);
    assert(!model.revalidate(target, 9'950, false));
    const auto context = model.contextKey();
    model.bind("a", "w", "HTTPS://TWO.EXAMPLE:443/");
    assert(model.contextKey() == context); // one origin, not a fresh receipt namespace
    model.bind("a", "other", "https://two.example");
    assert(model.contextKey() != context);
    model.bind("a", "w", "");
    assert(!model.update({"a", "w", {event}}, model.epoch()));
}

void testF277PersistedReceiptsFailClosedAndExpire() {
    using namespace graf::windows;
    ReminderDisk disk;
    MeetingReminderModel model; model.bind("a", "w", "https://one.example");
    CalendarReminderEvent event{"event", 10'000, 10'001, true, false, "private title", true, "https://meet.example.com/private"};
    const auto context = model.contextKey();
    assert(disk.store().claimMeeting(context, event, 9'950));
    event.endsAt = 11'000; // A changed end or offset cannot grant a new receipt.
    assert(!disk.store().claimMeeting(context, event, 10'001));
    assert(!disk.store().claimMeeting(context, event, 9'951)); // recreated store / clock rollback
    event.startsAt += 1;
    assert(disk.store().claimMeeting(context, event, 9'951));
    event.startsAt -= 1;
    assert(!disk.store().claimMeeting(context, event, 9'951));
    model.bind("b", "w", "https://one.example");
    assert(disk.store().claimMeeting(model.contextKey(), event, 9'951));
    model.bind("a", "other", "https://one.example");
    assert(disk.store().claimMeeting(model.contextKey(), event, 9'951));
    model.bind("a", "w", "https://two.example");
    assert(disk.store().claimMeeting(model.contextKey(), event, 9'951));
    assert(!disk.store().claimMeeting({}, event, 9'951));
    for (const auto& [key, value] : disk.values) {
        assert(key.find("example") == std::string::npos);
        assert(value.find("private") == std::string::npos && value.find("event") == std::string::npos);
    }
    ReminderDisk broken; broken.loseWrite = true;
    assert(!broken.store().claimMeeting(context, event, 9'951));
    broken.loseWrite = false; broken.writable = false;
    assert(!broken.store().claimMeeting(context, event, 9'951));
    for (auto& [key, value] : disk.values) value = "corrupt";
    assert(!disk.store().claimMeeting(context, event, 9'952));
    ReminderDisk expiry;
    assert(expiry.store().claimMeeting(context, event, 9'950));
    assert(expiry.store().pruneMeetingReceipts(context, 10'120));
    assert(!expiry.store().claimMeeting(context, event, 10'120));
    event.startsAt = 10'500;
    assert(expiry.store().claimMeeting(context, event, 10'450));
    for (auto& [key, value] : expiry.values) value.pop_back(); // incomplete last row
    event.startsAt += 1;
    assert(!expiry.store().claimMeeting(context, event, 10'450));
}

void testF277PresenterRestartQuietAndExactAction() {
    using namespace graf::windows;
    using namespace NativeSettingsBridge;
    ReminderDisk disk;
    const auto now = RecordingNoticePresenter::Clock::now();
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", true, "https://meet.example.com/a"};
    RecordingNoticePresenter card;
    card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
    int sounds = 0;
    {
        MeetingReminderPresenter p(card, disk.store());
        p.bind("a", "w", "https://one.example");
        p.onMeetingPresented = [&] { ++sounds; };
        assert(p.update({"a", "w", {event}}, p.epoch()));
        (void)p.settings({NotificationAction::set, "sound", true, 1}, 9'930, now, false);
        (void)p.settings({NotificationAction::set, "quiet", true, 1}, 9'940, now, false);
        assert(!card.visible());
        (void)p.settings({NotificationAction::set, "quiet", false, 1}, 9'940, now, false);
        assert(card.visible() && sounds == 1);
        p.reconcile(9'941, now + std::chrono::seconds(1), false);
        assert(card.visible() && sounds == 1);
        std::optional<ReminderActionTarget> clicked;
        int requests = 0;
        p.onActionRequested = [&](auto target, auto) { clicked = target; ++requests; };
        card.invoke(NoticeAction::join); card.invoke(NoticeAction::join);
        assert(clicked && requests == 1);
        event.meetingUrl = "https://meet.example.com/b";
        assert(p.update({"a", "w", {event}}, p.epoch()));
        assert(!p.completeAction(*clicked, NoticeAction::join, 9'942, false));
        p.reconcile(9'943, now, false); assert(!card.visible());
        p.invalidate();
    }
    MeetingReminderPresenter restarted(card, disk.store());
    restarted.bind("a", "w", "https://one.example");
    assert(restarted.update({"a", "w", {event}}, restarted.epoch()));
    restarted.reconcile(9'944, now, false); assert(!card.visible());
    event.startsAt += 10;
    assert(restarted.update({"a", "w", {event}}, restarted.epoch()));
    restarted.reconcile(9'950, now, false); assert(card.visible());
    std::optional<ReminderActionTarget> clicked;
    restarted.onActionRequested = [&](auto target, auto) { clicked = target; };
    card.invoke(NoticeAction::join); assert(clicked);
    assert(restarted.completeAction(*clicked, NoticeAction::join, 9'951, false));
    assert(!restarted.completeAction(*clicked, NoticeAction::join, 9'951, false));
    restarted.invalidate();
}

void testUpcomingProjectionAndFrozenTarget() {
    using namespace graf::windows;
    MeetingReminderModel model;
    assert(!model.upcoming());
    model.bind("owner", "workspace", "https://one.example");
    const auto epoch = model.epoch();
    CalendarReminderEvent frozen{"11111111-1111-4111-8111-111111111111", 10'000, 11'000,
        false, true, "Synthetic title", true, "https://meet.example.com/synthetic", true};
    CalendarReminderSnapshot snapshot{"owner", "workspace", {frozen}, false, false};
    for (int i = 12; i > 0; --i) {
        auto event = frozen;
        event.eventId = "row-" + std::to_string(i);
        event.startsAt += i;
        event.endsAt += i;
        snapshot.events.push_back(event);
    }
    assert(model.update(snapshot, epoch));
    model.dismiss(frozen);
    auto projection = model.upcoming();
    assert(projection && projection->events.size() == 12);
    assert(projection->userId == "owner" && projection->workspaceId == "workspace");
    assert(!projection->showUpcomingTime && !projection->showUpcomingTitle);
    assert(projection->events.front().eventId == frozen.eventId && projection->events.front().allDay);
    for (std::size_t i = 1; i < projection->events.size(); ++i)
        assert(projection->events[i - 1].startsAt < projection->events[i].startsAt);
    assert(!model.revalidate(model.actionTarget(frozen), 9'940, false));
    assert(model.upcomingCurrent(frozen, epoch, 9'000)); // Not due; canSurface=false, dismissed.
    assert(model.upcomingCurrent(frozen, epoch, 10'500)); // Card deadline is irrelevant.
    assert(!model.upcomingCurrent(frozen, epoch, 11'000));
    assert(!model.upcomingCurrent(frozen, epoch + 1, 9'000));
    assert(!model.upcomingCurrent(frozen, epoch, std::numeric_limits<double>::quiet_NaN()));

    // Equal starts sort by identity; changing presentation never replaces a target.
    auto earlierId = frozen;
    earlierId.eventId = "00000000-0000-4000-8000-000000000000";
    snapshot.events = {frozen, earlierId};
    snapshot.events.front().title = "Changed presentation";
    snapshot.events.front().titleAvailable = false;
    snapshot.events.front().allDay = false;
    snapshot.events.front().canSurface = true;
    snapshot.showUpcomingTime = snapshot.showUpcomingTitle = true;
    assert(model.update(snapshot, epoch));
    projection = model.upcoming();
    assert(projection && projection->events.front().eventId == earlierId.eventId);
    assert(projection->showUpcomingTime && projection->showUpcomingTitle);
    assert(model.upcomingCurrent(frozen, epoch, 10'500));

    // An admitted unchanged event remains current outside a newly sorted prefix12.
    for (int i = 0; i < 12; ++i) {
        auto event = earlierId; event.eventId = "earlier-" + std::to_string(i);
        event.startsAt -= 100 + i;
        snapshot.events.push_back(event);
    }
    assert(model.update(snapshot, epoch));
    projection = model.upcoming();
    assert(projection && projection->events.size() == 12);
    assert(std::none_of(projection->events.begin(), projection->events.end(),
        [&](const auto& event) { return event.eventId == frozen.eventId; }));
    assert(model.upcomingCurrent(frozen, epoch, 10'500));

    for (int replacement = 0; replacement < 6; ++replacement) {
        auto changed = frozen;
        switch (replacement) {
        case 0: changed.eventId = earlierId.eventId; break;
        case 1: ++changed.startsAt; break;
        case 2: ++changed.endsAt; break;
        case 3: changed.meetingUrl += "-changed"; break;
        case 4: changed.meetingLinkPresent = false; break;
        case 5: changed.meetingUrl = "http://meet.example.com/unsafe"; break;
        }
        assert(model.update({"owner", "workspace", {changed}}, epoch));
        assert(!model.upcomingCurrent(frozen, epoch, 9'000));
        if (replacement >= 4) assert(!model.upcomingCurrent(changed, epoch, 9'000));
    }
    assert(model.update({"owner", "workspace", {frozen}}, epoch));
    assert(!model.update({"other", "workspace", {}}, epoch));
    assert(!model.update({"owner", "workspace", {}}, epoch + 1));
    assert(model.upcomingCurrent(frozen, epoch, 9'000));
    model.invalidateUpcoming();
    assert(!model.upcoming() && !model.upcomingCurrent(frozen, epoch, 9'000));
    assert(model.update({"owner", "workspace", {}}, epoch));
    assert(model.upcoming() && model.upcoming()->events.empty());
    assert(!model.upcomingCurrent(frozen, epoch, 9'000));
    auto invalid = frozen; invalid.startsAt = std::numeric_limits<double>::quiet_NaN();
    assert(model.update({"owner", "workspace", {frozen, invalid}}, epoch));
    assert(!model.upcoming() && !model.upcomingCurrent(frozen, epoch, 9'000));
    for (const auto& context : {LocalProblemContext{"https://two.example", "owner", "workspace"},
        LocalProblemContext{"https://one.example", "other", "workspace"},
        LocalProblemContext{"https://one.example", "owner", "other"}}) {
        model.bind("owner", "workspace", "https://one.example");
        const auto acceptedEpoch = model.epoch();
        assert(model.update({"owner", "workspace", {frozen}}, acceptedEpoch));
        model.bind(context.owner, context.workspace, context.origin);
        assert(!model.upcoming() && !model.upcomingCurrent(frozen, acceptedEpoch, 9'000));
    }
}

void testUpcomingPresenterIgnoresReminderSettingsAndCapture() {
    using namespace graf::windows;
    ReminderDisk disk;
    RecordingNoticePresenter card;
    MeetingReminderPresenter presenter(card, disk.store());
    presenter.bind("owner", "workspace", "https://one.example");
    const auto epoch = presenter.epoch();
    CalendarReminderEvent event{"11111111-1111-4111-8111-111111111111", 10'000, 11'000,
        false, true, "Synthetic title", true, "https://meet.example.com/synthetic"};
    assert(presenter.update({"owner", "workspace", {event}, false, true}, epoch));
    const auto now = RecordingNoticePresenter::Clock::now();
    using namespace NativeSettingsBridge;
    (void)presenter.settings({NotificationAction::set, "reminders", false}, 9'000, now, true);
    (void)presenter.settings({NotificationAction::set, "quiet", true}, 9'000, now, true);
    assert(!presenter.preferences().reminders && presenter.preferences().quiet);
    presenter.reconcile(10'500, now, true);
    assert(!card.visible());
    const auto projection = presenter.upcoming();
    assert(projection && projection->events.size() == 1);
    assert(!projection->showUpcomingTime && projection->showUpcomingTitle);
    assert(presenter.upcomingCurrent(event, epoch, 10'500));
    presenter.calendarFailed();
    assert(!presenter.upcoming() && !presenter.upcomingCurrent(event, epoch, 10'500));
    assert(presenter.update({"owner", "workspace", {event}}, epoch));
    presenter.invalidate();
    assert(!presenter.upcoming() && !presenter.upcomingCurrent(event, epoch, 10'500));
}

void testCalendarJoinCardWaitsForHandoff() {
    using namespace graf::windows;
    for (const auto action : {NoticeAction::join, NoticeAction::joinAndRecord}) {
        ReminderDisk disk;
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        MeetingReminderPresenter presenter(card, disk.store());
        presenter.bind("owner", "workspace", "https://one.example");
        const auto now = RecordingNoticePresenter::Clock::now();
        CalendarReminderEvent event{"11111111-1111-4111-8111-111111111111", 10'000, 11'000,
            true, false, "", true, "https://meet.example.com/synthetic"};
        assert(presenter.update({"owner", "workspace", {event}}, presenter.epoch()));
        presenter.reconcile(9'940, now, false);
        const auto generation = card.generation();
        const auto deadline = card.deadline();
        std::optional<ReminderActionTarget> clicked;
        int requests = 0;
        presenter.onActionRequested = [&](auto target, auto requested) {
            assert(requested == action);
            assert(card.visible()); // The click is not an OS handoff.
            clicked = std::move(target); ++requests;
            card.invoke(action, generation, now); // Reentry cannot dispatch twice.
        };
        card.invoke(action, generation, now);
        assert(clicked && requests == 1 && card.visible());
        const auto expiry = presenter.pendingActionExpiry(*clicked, action, 9'940, false);
        assert(expiry && *expiry == deadline);
        assert(card.generation() == generation && card.deadline() == deadline);
        assert(card.content().body.find(L"Открываем") != std::wstring::npos);
        card.invoke(NoticeAction::join, generation, now);
        card.invoke(NoticeAction::joinAndRecord, generation, now);
        assert(requests == 1);
        presenter.reconcile(9'941, now + std::chrono::seconds(1), false);
        assert(card.visible() && card.deadline() == deadline);
        card.close(generation);
        assert(!card.visible());
        assert(!presenter.completeAction(*clicked, action, 9'942, false));
    }
}

void testCalendarJoinFailureAndRetryKeepOriginalExpiry() {
    using namespace graf::windows;
    for (const auto action : {NoticeAction::join, NoticeAction::joinAndRecord}) {
        ReminderDisk disk;
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        MeetingReminderPresenter presenter(card, disk.store());
        presenter.bind("owner", "workspace", "https://one.example");
        const auto now = RecordingNoticePresenter::Clock::now();
        CalendarReminderEvent event{"11111111-1111-4111-8111-111111111111", 10'000, 11'000,
            true, false, "", true, "https://meet.example.com/synthetic"};
        assert(presenter.update({"owner", "workspace", {event}}, presenter.epoch()));
        presenter.reconcile(9'940, now, false);
        const auto deadline = card.deadline();
        const auto generation = card.generation();
        std::optional<ReminderActionTarget> clicked;
        int requests = 0;
        presenter.onActionRequested = [&](auto target, auto) { clicked = std::move(target); ++requests; };
        card.invoke(action, generation, now);
        assert(clicked && requests == 1);
        presenter.failAction(*clicked, action, CalendarJoinReason::launchFailed, 9'941, false);
        assert(card.visible() && card.deadline() <= deadline && card.generation() == generation);
        assert(card.content().body.find(L"Не удалось подключиться") != std::wstring::npos);
        assert(!presenter.pendingActionExpiry(*clicked, action, 9'941, false));
        assert(presenter.upcoming() && presenter.upcomingCurrent(event, presenter.epoch(), 9'941));
        presenter.calendarFailed(); // Background refresh cannot erase retry/error.
        assert(card.visible());
        assert(!presenter.upcoming() && !presenter.upcomingCurrent(event, presenter.epoch(), 9'941));
        card.invoke(action, generation, now);
        assert(requests == 2);
        const auto retryExpiry = presenter.pendingActionExpiry(*clicked, action, 9'942, false);
        assert(retryExpiry && *retryExpiry <= deadline);
        assert(!presenter.pendingActionExpiry(*clicked, action, 9'942, true));
        assert(card.visible()); // Applicability check itself never closes the card.
        assert(presenter.completeAction(*clicked, action, 9'943, false));
        assert(!card.visible());
        assert(!presenter.completeAction(*clicked, action, 9'943, false));
        assert(presenter.handoffRecordingCurrent(*clicked, 9'944, false));
        assert(!presenter.handoffRecordingCurrent(*clicked, 9'944, true));
        // Same account/epoch cannot make a replaced or removed event current.
        const auto epoch = presenter.epoch();
        event.meetingUrl = "https://meet.example.com/replaced";
        assert(presenter.update({"owner", "workspace", {event}}, epoch));
        assert(presenter.epoch() == epoch);
        assert(!presenter.handoffRecordingCurrent(*clicked, 9'944, false));
        assert(presenter.update({"owner", "workspace", {}}, epoch));
        assert(!presenter.handoffRecordingCurrent(*clicked, 9'944, false));
    }
}

void testCalendarJoinFailureCannotReviveRetiredAction() {
    using namespace graf::windows;
    for (const auto reason : {CalendarJoinReason::authRequired, CalendarJoinReason::eventUnavailable,
        CalendarJoinReason::stale, CalendarJoinReason::cancelled}) {
        ReminderDisk disk;
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        MeetingReminderPresenter presenter(card, disk.store());
        presenter.bind("owner", "workspace", "https://one.example");
        const auto now = RecordingNoticePresenter::Clock::now();
        CalendarReminderEvent event{"11111111-1111-4111-8111-111111111111", 10'000, 11'000,
            true, false, "", true, "https://meet.example.com/synthetic"};
        assert(presenter.update({"owner", "workspace", {event}}, presenter.epoch()));
        presenter.reconcile(9'940, now, false);
        std::optional<ReminderActionTarget> clicked;
        presenter.onActionRequested = [&](auto target, auto) { clicked = std::move(target); };
        card.invoke(NoticeAction::join);
        assert(clicked);
        presenter.failAction(*clicked, NoticeAction::join, reason, 9'941, false);
        assert(!card.visible());
        presenter.failAction(*clicked, NoticeAction::join, CalendarJoinReason::launchFailed, 9'941, false);
        presenter.reconcile(9'942, now, false);
        assert(!card.visible());
        assert(!presenter.completeAction(*clicked, NoticeAction::join, 9'942, false));
    }
}

void testF277QuietPreviewAndDeadlineNeverRestart() {
    using namespace graf::windows;
    using namespace NativeSettingsBridge;
    ReminderDisk disk;
    RecordingNoticePresenter card;
    card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
    MeetingReminderPresenter p(card, disk.store());
    p.bind("a", "w", "https://one.example");
    const auto now = RecordingNoticePresenter::Clock::now();
    (void)p.settings({NotificationAction::set, "quiet", true, 1}, 9'930, now, false);
    assert(p.settings({NotificationAction::test, {}, false, 1}, 9'930, now, false).find("\"error\"") == std::string::npos);
    assert(card.visible() && card.kind() == NoticeKind::preview);
    assert(card.history().empty());
    (void)p.settings({NotificationAction::set, "quiet", false, 1}, 9'930, now, false);
    CalendarReminderEvent event{"event", 10'000, 10'010, true, false, "", false, ""};
    assert(p.update({"a", "w", {event}}, p.epoch()));
    p.reconcile(9'940, now, false);
    const auto original = card.deadline();
    assert(original == now + std::chrono::seconds(70));
    event.endsAt = 11'000;
    assert(p.update({"a", "w", {event}}, p.epoch()));
    p.reconcile(9'941, now + std::chrono::seconds(1), false);
    assert(card.deadline() == original);
    event.endsAt = 10'005;
    assert(p.update({"a", "w", {event}}, p.epoch()));
    p.reconcile(9'942, now + std::chrono::seconds(2), false);
    assert(card.deadline() == now + std::chrono::seconds(65));
    p.reconcile(10'005, now + std::chrono::seconds(65), false);
    assert(!card.visible());
    (void)p.settings({NotificationAction::set, "offsetMinutes", false, 0}, 10'005, now + std::chrono::seconds(65), false);
    assert(!card.visible()); // new offset is not a new occurrence
}

void testF277BlockedSurfaceAndRestartWhileVisible() {
    using namespace graf::windows;
    ReminderDisk disk;
    RecordingNoticePresenter card;
    card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
    auto now = RecordingNoticePresenter::Clock::now();
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", false, ""};
    {
        MeetingReminderPresenter p(card, disk.store());
        p.bind("a", "w", "https://one.example");
        assert(p.update({"a", "w", {event}}, p.epoch()));
        assert(card.present({NoticeKind::recordingPrompt, "prompt-7", L"", L"", {}}, now, now + std::chrono::seconds(8)));
        now = card.deadline() - std::chrono::seconds(8); // first visible instant, after preparation
        p.reconcile(9'940, now, false);
        assert(card.visible() && card.kind() == NoticeKind::recordingPrompt);
        card.dismiss();
        p.reconcile(9'941, now, false); assert(card.visible());
        // A new store/presenter must already see the receipt while the first is open.
        RecordingNoticePresenter otherCard;
        otherCard.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        MeetingReminderPresenter restarted(otherCard, disk.store());
        restarted.bind("a", "w", "https://one.example");
        assert(restarted.update({"a", "w", {event}}, restarted.epoch()));
        restarted.reconcile(9'942, now, false); assert(!otherCard.visible());
        assert(card.present({NoticeKind::problem, "problem", L"", L"", {}}, now, now + std::chrono::seconds(20)));
        p.reconcile(9'943, now, false);
        card.close(); p.reconcile(9'944, now, false); assert(!card.visible());
    }
    assert(!card.visible());
}

void testF277ReceiptCorruptionAndCapacityNeverEvictLiveClaims() {
    using namespace graf::windows;
    MeetingReminderModel model; model.bind("a", "w", "https://one.example");
    const auto context = model.contextKey();
    const auto key = context + ".meetings";
    const auto digest = sha256("synthetic");
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", false, ""};
    for (const auto& bytes : {std::string{}, std::string("receipts-v2\n"),
        "receipts-v1\n" + digest + " nan\n", "receipts-v1\n" + digest + " -1\n",
        "receipts-v1\n" + digest + " 10120 extra\n",
        "receipts-v1\n" + digest + " 10120\n" + digest + " 10121\n",
        "receipts-v1\n" + std::string(63, '0') + " 10120\n"}) {
        ReminderDisk disk; disk.values[key] = bytes;
        assert(!disk.store().claimMeeting(context, event, 9'950));
        assert(!disk.store().pruneMeetingReceipts(context, 9'950));
        assert(disk.values[key] == bytes); // Do not replace corrupt evidence with an empty set.
    }
    ReminderDisk full;
    std::string bytes = "receipts-v1\n";
    for (int i = 0; i < 1024; ++i) bytes += sha256(std::to_string(i)) + " 10120\n";
    full.values[key] = bytes;
    assert(!full.store().claimMeeting(context, event, 9'950));
    assert(full.values[key] == bytes);
    assert(full.store().pruneMeetingReceipts(context, 10'120));
    assert(full.values[key] == "receipts-v1\n");
}

void testF277PendingActionCannotOutliveMonotonicDeadline() {
    using namespace graf::windows;
    ReminderDisk disk;
    RecordingNoticePresenter card;
    card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
    MeetingReminderPresenter p(card, disk.store());
    p.bind("a", "w", "https://one.example");
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", false, ""};
    assert(p.update({"a", "w", {event}}, p.epoch()));
    const auto before = RecordingNoticePresenter::Clock::now() - std::chrono::seconds(121);
    p.reconcile(9'940, before, false);
    std::optional<ReminderActionTarget> clicked;
    p.onActionRequested = [&](auto target, auto) { clicked = target; };
    card.invoke(NoticeAction::record, card.generation(), before + std::chrono::seconds(1));
    assert(clicked);
    assert(!p.completeAction(*clicked, NoticeAction::record, 9'941, false));
}

void testF277PendingActionCannotReturnAfterAnotherCard() {
    using namespace graf::windows;
    ReminderDisk disk;
    RecordingNoticePresenter card;
    card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
    MeetingReminderPresenter p(card, disk.store());
    p.bind("a", "w", "https://one.example");
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", false, ""};
    assert(p.update({"a", "w", {event}}, p.epoch()));
    const auto now = RecordingNoticePresenter::Clock::now();
    p.reconcile(9'940, now, false);
    std::optional<ReminderActionTarget> clicked;
    p.onActionRequested = [&](auto target, auto) { clicked = target; };
    card.invoke(NoticeAction::record); assert(clicked);
    assert(card.present({NoticeKind::problem, "problem", L"", L"", {}}, now, now + std::chrono::seconds(20)));
    p.reconcile(9'941, now, false);
    card.close();
    assert(!p.completeAction(*clicked, NoticeAction::record, 9'942, false));
}

void testOnlyTheSettingsPageMayUseTheBridge() {
    // The route macOS bridges: the recording settings page, addressed plainly.
    assert(graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording"));
    assert(graf::windows::NativeSettingsBridge::isSettingsRoute(
        "http://127.0.0.1:8080/desktop/settings/recording"));
    // The notification settings page is also a supported native bridge route;
    // a query, a fragment and a look-alike path are not.
    assert(graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/notifications"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording?next=/desktop/meetings"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording#section"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording/extra"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute("/desktop/settings/recording"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(""));
}

void testTheRequestVocabularyIsThePagesOwn() {
    using namespace graf::windows::NativeSettingsBridge;
    assert(actionFromToken("read") == Action::read);
    assert(actionFromToken("set") == Action::set);
    assert(actionFromToken("setAll") == Action::setAll);
    // Unknown, differently cased and empty actions are not actions.
    assert(!actionFromToken("write"));
    assert(!actionFromToken("SET"));
    assert(!actionFromToken(""));
    assert(actionToken(Action::read) == "read");
    assert(actionToken(Action::set) == "set");
    assert(actionToken(Action::setAll) == "setAll");

    // The stored preference and the page's select share these three words.
    assert(isRule("always"));
    assert(isRule("ask"));
    assert(isRule("never"));
    assert(!isRule("Always"));
    assert(!isRule("sometimes"));
    assert(!isRule(""));
}

void testTheReplyCarriesWhatThePageValidates() {
    using namespace graf::windows::NativeSettingsBridge;
    const std::vector<Target> targets{
        {"yandex-telemost", "Яндекс Телемост", "always"},
        {"zoom", "Zoom Workplace", "never"},
    };
    const auto reply = settingsReply(targets);
    // The page reads `version`, `targets[].id`, `targets[].name` and `targets[].rule`.
    assert(reply.find("\"version\":1") != std::string::npos);
    assert(reply.find("{\"id\":\"yandex-telemost\",\"name\":\"Яндекс Телемост\",\"rule\":\"always\"}") != std::string::npos);
    assert(reply.find("{\"id\":\"zoom\",\"name\":\"Zoom Workplace\",\"rule\":\"never\"}") != std::string::npos);
    // Russian text is sent as UTF-8; it is not escaped into something else.
    assert(reply.find("Яндекс") != std::string::npos);
}

void testATargetThatWouldBreakTheReplyIsLeftOut() {
    using namespace graf::windows::NativeSettingsBridge;
    // The page refuses the whole reply over one unusable row, and then it would
    // show nothing at all: a row that cannot be answered is dropped instead.
    const std::vector<Target> targets{
        {"", "Без ключа", "always"},
        {"broken-rule", "Сломанное правило", "sometimes"},
        {"good", "Рабочее приложение", "ask"},
    };
    const auto reply = settingsReply(targets);
    assert(reply.find("Без ключа") == std::string::npos);
    assert(reply.find("Сломанное правило") == std::string::npos);
    assert(reply.find("good") != std::string::npos);
    assert(reply.find("always") == std::string::npos);
    // Exactly one target, so exactly one comma-free object after the colon.
    assert(reply.find(",\"name\"") != std::string::npos);
}

void testQuotesAndControlCharactersCannotLeaveTheJson() {
    using namespace graf::windows::NativeSettingsBridge;
    const std::vector<Target> targets{{"we\"ird", "Имя \"в кавычках\"\nи перенос", "ask"}};
    const auto reply = settingsReply(targets);
    // A name that would otherwise end the string early is escaped.
    assert(reply.find("Имя \\\"в кавычках\\\"\\nи перенос") != std::string::npos);
    assert(reply.find("we\\\"ird") != std::string::npos);
    // No raw newline survived: the page parses this as one JSON document.
    assert(reply.find('\n') == std::string::npos);
}

void testARefusalIsStillAnAnswer() {
    using namespace graf::windows::NativeSettingsBridge;
    const auto reply = failureReply("Настройки не сохранены.");
    // The page checks the version before it believes anything, including a refusal.
    assert(reply.find("\"version\":1") != std::string::npos);
    assert(reply.find("\"error\":\"Настройки не сохранены.\"") != std::string::npos);
    // An empty message is never sent as an empty reason.
    const auto blank = failureReply("");
    assert(blank.find("\"error\":\"\"") == std::string::npos);
}

void testEachSettingsPageHasItsOwnRoute() {
    using namespace graf::windows::NativeSettingsBridge;
    assert(isRecordingSettingsRoute("https://rec.2brain.pro/desktop/settings/recording"));
    assert(isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications"));
    // Neither page answers for the other, and the general check accepts both.
    assert(!isRecordingSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications"));
    assert(!isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings/recording"));
    assert(isSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications"));
    assert(!isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications?tab=1"));
    assert(!isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings"));
}

void testTheNotificationReplyIsThePlatformTruth() {
    using namespace graf::windows::NativeSettingsBridge;
    const auto reply = notificationSettingsReply({}, true);
    // The page refuses a reply that misses one of these, and then it would show
    // nothing at all, so the shape is checked here.
    assert(reply.find("\"version\":2") != std::string::npos);
    assert(reply.find("\"preferences\":{\"reminders\":true,\"showTitles\":false,\"sound\":false,\"quiet\":false,\"offsetMinutes\":1}") != std::string::npos);
    assert(reply.find("\"canEdit\":true") != std::string::npos);
    assert(reply.find("canRequestPermission") == std::string::npos);
    assert(reply.find("permission") == std::string::npos);
    assert(reply.find("\"message\":\"\"") != std::string::npos);
    // A reason given by the app is used as it is.
    assert(notificationSettingsReply({}, false).find("\"canEdit\":false") != std::string::npos);
}

void testNotificationRequestsAndOwnerPersistence() {
    using namespace graf::windows;
    using namespace NativeSettingsBridge;
    const auto parse = [](std::string fields) {
        return parseNotificationRequest("{\"version\":2,\"nonce\":\"current\"," + fields + "}", "current");
    };
    assert(parse("\"action\":\"read\""));
    assert(parse("\"action\":\"test\""));
    assert(!parse("\"action\":\"requestPermission\""));
    assert(!parse("\"action\":\"openSystemSettings\""));
    for (const auto field : {"reminders", "showTitles", "sound", "quiet"}) {
        assert(parse(std::string("\"action\":\"set\",\"field\":\"") + field + "\",\"value\":true"));
        assert(!parse(std::string("\"action\":\"set\",\"field\":\"") + field + "\",\"value\":\"true\""));
    }
    for (const auto offset : {"0", "1", "5"})
        assert(parse(std::string("\"action\":\"set\",\"field\":\"offsetMinutes\",\"value\":") + offset));
    assert(!parse("\"action\":\"read\",\"value\":true"));
    assert(!parse("\"action\":\"set\",\"field\":\"sound\",\"value\":1"));
    assert(!parse("\"action\":\"set\",\"field\":\"offsetMinutes\",\"value\":1.0"));
    assert(!parse("\"action\":\"set\",\"field\":\"offsetMinutes\",\"value\":2"));
    assert(!parse("\"action\":\"set\",\"field\":\"sound\",\"value\":true,\"extra\":0"));
    assert(!parseNotificationRequest(R"({"version":2,"nonce":"old","action":"test"})", "current"));
    assert(!parse("\"action\":\"test\",\"action\":\"read\""));
    const auto payload = [](std::string id, std::string extra = "") {
        return "{\"handler\":\"grafNotificationSettings\",\"requestId\":" + id +
            ",\"request\":{\"version\":2,\"nonce\":\"current\",\"action\":\"test\"}" + extra + "}";
    };
    assert(parseNotificationPayload(payload("1"), "current"));
    assert(!parseNotificationPayload(payload("0"), "current"));
    assert(!parseNotificationPayload(payload("1.0"), "current"));
    assert(!parseNotificationPayload(payload("-1"), "current"));
    assert(!parseNotificationPayload(payload("9007199254740992"), "current"));
    assert(!parseNotificationPayload(payload("1", ",\"extra\":true"), "current"));
    assert(!parseNotificationPayload(payload("1", ",\"requestId\":2"), "current"));
    assert(!parseNotificationPayload(payload("1"), "old"));
    std::map<std::string, std::string> saved;
    bool writes = true;
    NotificationPreferenceStore store{
        [&](std::string_view key) -> std::optional<std::string> {
            auto it = saved.find(std::string(key));
            return it == saved.end() ? std::nullopt : std::optional<std::string>(it->second);
        },
        [&](std::string_view key, std::string_view value) {
            if (!writes) return false;
            saved[std::string(key)] = value; return true;
        }};
    NotificationPreferences preferences;
    const auto edit = parse("\"action\":\"set\",\"field\":\"showTitles\",\"value\":true");
    assert(edit && applyNotificationSetting(preferences, *edit));
    assert(preferences.showTitles && preferences.offsetMinutes == 1);
    assert(!store.save(preferences, ""));
    assert(store.save(preferences, "owner-a"));
    assert(store.load("owner-a").showTitles);
    assert(!store.load("owner-b").showTitles);
    writes = false;
    preferences.showTitles = false;
    assert(!store.save(preferences, "owner-a"));
    assert(store.load("owner-a").showTitles);
    assert(saved.begin()->first.find("owner-a") == std::string::npos);
}

void testReminderOccurrenceAndRevalidation() {
    using namespace graf::windows;
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", false, ""};
    MeetingReminderModel model;
    model.bind("a", "w", "https://one.example");
    const auto epoch = model.epoch();
    assert(model.update({"a", "w", {event}}, epoch));
    auto selected = model.candidate(9'950, false);
    assert(selected && selected->eventId == "event");
    auto earlier = event; earlier.eventId = "earlier"; earlier.startsAt = 9'990;
    assert(model.update({"a", "w", {event, earlier}}, epoch));
    assert(model.candidate(9'950, false)->eventId == "earlier");
    model.dismiss(event);
    event.startsAt += 10; // A new start is a new occurrence; moving back stays dismissed.
    assert(model.update({"a", "w", {event}}, epoch));
    assert(model.candidate(9'960, false));
    event.startsAt -= 10;
    assert(model.update({"a", "w", {event}}, epoch));
    assert(!model.candidate(9'960, false));
    model.bind("b", "w", "https://one.example");
    assert(!model.update({"a", "w", {event}}, epoch));
    assert(!model.candidate(9'960, false));
    assert(model.update({"b", "w", {event}}, model.epoch()));
    assert(model.candidate(9'960, false));
    const auto target = model.actionTarget(event);
    event.startsAt += 1;
    assert(model.update({"b", "w", {event}}, model.epoch()));
    assert(!model.revalidate(target, 9'960, false)); // a stale click cannot follow a moved occurrence
    auto current = model.actionTarget(event);
    assert(model.revalidate(current, 9'960, false));
    assert(!model.revalidate(current, 9'960, true));
    event.canSurface = false;
    assert(model.update({"b", "w", {event}}, model.epoch()));
    assert(!model.revalidate(current, 9'960, false));
    model.clearCalendar();
    assert(!model.revalidate(current, 9'960, false));
    model.invalidate();
    assert(model.owner().empty());
    assert(!model.update({"b", "w", {event}}, epoch));
    // A restart during/after the expired fixed window never grants a new 120s.
    MeetingReminderModel restarted;
    restarted.bind("b", "w", "https://one.example"); event.canSurface = true;
    assert(restarted.update({"b", "w", {event}}, restarted.epoch()));
    assert(!restarted.candidate(10'121, false));
}

void testSharedCardPriorityAndManualClose() {
    using namespace graf::windows;
    RecordingNoticePresenter presenter;
    presenter.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
    const auto now = std::chrono::steady_clock::now();
    int closed = 0;
    assert(presenter.present({NoticeKind::preview, "preview", L"Проверка", L"", {}}, now, now + std::chrono::seconds(6)));
    assert(presenter.present({NoticeKind::meeting, "a", L"Встреча", L"", {}}, now, now + std::chrono::seconds(90), {}, [&] { ++closed; }));
    assert(!presenter.present({NoticeKind::preview, "preview", L"Проверка", L"", {}}, now, now + std::chrono::seconds(6)));
    assert(!presenter.present({NoticeKind::meeting, "b", L"Встреча", L"", {}}, now, now + std::chrono::seconds(90)));
    presenter.showShortRecordingDiscarded(now);
    assert(presenter.kind() == NoticeKind::shortRecording);
    assert(closed == 0); // replacement/expiry must not dismiss the real event
    presenter.tick(now + std::chrono::seconds(20));
    assert(!presenter.visible());
    assert(!presenter.present({NoticeKind::meeting, "a", L"Встреча", L"", {}}, now, now + std::chrono::seconds(90)));
    assert(presenter.present({NoticeKind::meeting, "c", L"Встреча", L"", {}}, now, now + std::chrono::seconds(90), {}, [&] { ++closed; }));
    presenter.close();
    assert(!presenter.visible() && closed == 1);
    assert(presenter.present({NoticeKind::preview, "preview", L"Проверка", L"", {}}, now, now + std::chrono::seconds(6)));
    presenter.tick(now + std::chrono::milliseconds(5999)); assert(presenter.visible());
    presenter.tick(now + std::chrono::seconds(6)); assert(!presenter.visible());
}

void testCalendarSchemaAndSafeJoin() {
    using namespace graf::windows;
    const std::string response = R"({"notification_owner_id":"11111111-1111-4111-8111-111111111111","notification_workspace_id":"22222222-2222-4222-8222-222222222222","events":[{"event_id":"33333333-3333-4333-8333-333333333333","starts_at":"2026-09-26T12:00:00.125+03:00","ends_at":"2026-09-26T10:00:00Z","join_prompt_state":"not_due","title_state":"available","title":"Test \u0412\u0441\u0442\u0440\u0435\u0447\u0430","meeting_link_present":true,"open_meeting_url":"https://meet.example.com/room"}]})";
    const auto result = DesktopApiClient::decodeCalendarReminders(response);
    assert(result && result->events.size() == 1);
    assert(result->events[0].title == "Test Встреча");
    assert(result->events[0].canSurface);
    assert(result->showUpcomingTime && result->showUpcomingTitle && !result->events[0].allDay);
    assert(DesktopApiClient::formatUtcInstant(static_cast<std::uint64_t>(result->events[0].startsAt * 1000)) == "2026-09-26T09:00:00Z");
    const auto withPresentationField = [&](std::string_view key, std::string_view value) {
        auto json = response;
        json.insert(key == "all_day" ? json.find("\"event_id\"") : 1,
            "\"" + std::string(key) + "\":" + std::string(value) + ",");
        return json;
    };
    for (const auto key : {"show_upcoming_time", "show_upcoming_title", "all_day"})
        for (const auto value : {"\"true\"", "\"false\"", "0", "1", "{}", "[]"})
            assert(!DesktopApiClient::decodeCalendarReminders(withPresentationField(key, value)));
    for (const std::string_view key : {"show_upcoming_time", "show_upcoming_title", "all_day"}) {
        for (const std::string_view value : {"null", "true", "false"}) {
            const auto projected = DesktopApiClient::decodeCalendarReminders(withPresentationField(key, value));
            assert(projected && projected->events.size() == 1);
            assert(projected->showUpcomingTime == (key == "show_upcoming_time" ? value != "false" : true));
            assert(projected->showUpcomingTitle == (key == "show_upcoming_title" ? value != "false" : true));
            assert(projected->events[0].allDay == (key == "all_day" && value == "true"));
        }
    }
    auto privateTitle = withPresentationField("show_upcoming_title", "false");
    privateTitle.replace(privateTitle.find("\"available\""), 11, "\"private\"");
    const auto hidden = DesktopApiClient::decodeCalendarReminders(privateTitle);
    assert(hidden && !hidden->showUpcomingTitle && !hidden->events[0].titleAvailable && hidden->events[0].title.empty());
    auto secondEvent = response.substr(response.find('[') + 1);
    secondEvent.resize(secondEvent.size() - 2); // Only the event object, without the root ]}.
    secondEvent.replace(secondEvent.find("33333333-3333-4333-8333-333333333333"), 36,
        "44444444-4444-4444-8444-444444444444");
    secondEvent.insert(1, "\"all_day\":[],");
    auto twoEvents = response;
    twoEvents.insert(twoEvents.rfind(']'), "," + secondEvent);
    assert(!DesktopApiClient::decodeCalendarReminders(twoEvents));
    auto invalid = response;
    invalid.replace(invalid.find("2026-09-26T12"), 10, "2026-02-30");
    assert(!DesktopApiClient::decodeCalendarReminders(invalid));
    assert(!DesktopApiClient::decodeCalendarReminders(R"({"events":[]})"));
    assert(!DesktopApiClient::decodeCalendarReminders(R"({"notification_owner_id":null,"notification_workspace_id":null,"events":[]})"));
    for (const auto url : {"http://meet.example.com", "https://user@meet.example.com", "https://localhost/x", "https://127.0.0.1/x", "https://10.1.2.3/x", "https://meet.example.com\\evil", "https://2130706433/x"})
        assert(!MeetingReminderModel::safeMeetingUrl(url));
    assert(MeetingReminderModel::safeMeetingUrl("https://meet.example.com/room"));
    assert(MeetingReminderModel::safeMeetingUrl("https://abc.de/room"));
    assert(MeetingReminderModel::safeMeetingUrl("https://[2606:4700::1111]/room"));
    assert(MeetingReminderModel::safeMeetingUrl("https://meet.example.com/#secret"));
    assert(!MeetingReminderModel::safeMeetingUrl("https://[2001:::1]/room"));
    assert(!MeetingReminderModel::safeMeetingUrl("https://0177.0.0.1/room"));
    assert(!MeetingReminderModel::safeMeetingUrl("https://.localhost/room"));
}

void testAutomaticPromptSharesCardPriority() {
    using namespace graf::windows;
    RecordingNoticePresenter card;
    card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
    auto now = RecordingNoticePresenter::Clock::now();
    int dismissed = 0;
    assert(card.present({NoticeKind::meeting, "event", L"", L"", {}}, now,
        now + std::chrono::seconds(90), {}, [&] { ++dismissed; }));
    const auto meetingGeneration = card.generation();
    const NoticeContent prompt{NoticeKind::recordingPrompt, "prompt-1", L"", L"", {}};
    assert(card.present(prompt, now, now + std::chrono::seconds(8)));
    const auto firstPromptDeadline = card.deadline();
    now = firstPromptDeadline - std::chrono::seconds(8);
    const auto firstPromptGeneration = card.generation();
    assert(card.visible() && card.occupied() && card.automaticPromptActive());
    assert(dismissed == 0); // Preemption is not a dismissal of the meeting.
    assert(card.present(prompt, now, now + std::chrono::seconds(8)));
    assert(card.generation() == firstPromptGeneration && card.deadline() == firstPromptDeadline);
    assert(!card.present({NoticeKind::recordingPrompt, "prompt-2", L"", L"", {}}, now, now + std::chrono::seconds(8)));
    assert(!card.present({NoticeKind::preview, "preview", L"", L"", {}}, now, now + std::chrono::seconds(6)));
    assert(!card.present({NoticeKind::meeting, "event", L"", L"", {}}, now, now + std::chrono::seconds(90)));
    card.showShortRecordingDiscarded(now);
    assert(card.visible() && card.automaticPromptActive());
    card.close(meetingGeneration); // A stale close from the replaced meeting is harmless.
    assert(card.automaticPromptActive());
    assert(!card.present({NoticeKind::problem, "problem", L"", L"", {}}, now, now + std::chrono::seconds(20)));
    assert(card.automaticPromptActive() && card.visible());
    card.dismiss();
    assert(!card.occupied() && !card.automaticPromptActive());
    card.tick(now + std::chrono::seconds(21)); // unshown short has expired
    const auto later = now + std::chrono::seconds(21);
    card.showShortRecordingDiscarded(later);
    assert(card.present({NoticeKind::recordingPrompt, "prompt-2", L"", L"", {}}, later, later + std::chrono::seconds(8)));
    card.close(firstPromptGeneration); // A late close cannot affect the new prompt.
    assert(card.automaticPromptActive());
    card.dismiss();
    assert(!card.occupied());
    now = later + std::chrono::seconds(1);

    ReminderDisk disk;
    MeetingReminderPresenter reminders(card, disk.store());
    reminders.bind("owner", "workspace", "https://one.example");
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", false, ""};
    assert(reminders.update({"owner", "workspace", {event}}, reminders.epoch()));
    assert(card.present({NoticeKind::recordingPrompt, "prompt-3", L"", L"", {}}, now, now + std::chrono::seconds(8)));
    now = card.deadline() - std::chrono::seconds(8);
    reminders.reconcile(9'940, now, false);
    const auto reply = reminders.settings({NativeSettingsBridge::NotificationAction::test, {}, false, 1}, 9'940, now, false);
    assert(reply.find("важное сообщение") != std::string::npos && reply.find("\"error\"") == std::string::npos);
    assert(!reminders.completeAction({reminders.epoch(), "event", event.startsAt}, NoticeAction::record, 9'940, false));
    card.dismiss();
    reminders.reconcile(9'941, now, false);
    assert(card.visible() && card.kind() == NoticeKind::meeting); // Not consumed by the prompt.
    card.showShortRecordingDiscarded(now);
    assert(!reminders.completeAction({reminders.epoch(), "event", event.startsAt}, NoticeAction::record, 9'941, false));
    assert(card.visible() && card.kind() == NoticeKind::shortRecording);
    assert(card.present({NoticeKind::problem, "problem", L"", L"", {}}, now, now + std::chrono::seconds(20)));
    assert(!reminders.completeAction({reminders.epoch(), "event", event.startsAt}, NoticeAction::record, 9'941, false));
    assert(card.visible() && card.kind() == NoticeKind::problem);
}

void testAutomaticPromptProtectedUntilClosedOrInvalidated() {
    using namespace graf::windows;
    RecordingNoticePresenter card;
    card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
    auto now = RecordingNoticePresenter::Clock::now();
    const NoticeContent problem{NoticeKind::problem, "problem", L"", L"", {}};
    int closes = 0, expires = 0;
    NoticePresentationHooks hooks;
    hooks.onExpired = [&] { ++expires; };
    assert(card.present({NoticeKind::recordingPrompt, "prompt-10", L"", L"", {}}, now,
        now + std::chrono::seconds(8), {}, [&] { ++closes; }, hooks));
    now = card.deadline() - std::chrono::seconds(8);
    const auto oldGeneration = card.generation();
    assert(!card.present(problem, now, now + std::chrono::seconds(20)));
    assert(closes == 0 && expires == 0 && card.visible() && card.automaticPromptActive());
    assert(!card.present({NoticeKind::recordingPrompt, "prompt-11", L"", L"", {}}, now, now + std::chrono::seconds(8)));
    assert(!card.present({NoticeKind::preview, "preview", L"", L"", {}}, now, now + std::chrono::seconds(6)));
    card.close(oldGeneration);
    assert(closes == 1 && expires == 0 && !card.occupied());
    assert(card.present(problem, now, now + std::chrono::seconds(20)));
    assert(card.visible() && !card.automaticPromptActive());
    assert(card.present({NoticeKind::recordingPrompt, "prompt-11", L"", L"", {}}, now,
        now + std::chrono::seconds(8), {}, [&] { ++closes; }, hooks));
    now = card.deadline() - std::chrono::seconds(8);
    card.close(oldGeneration); // stale close cannot close the new prompt
    assert(card.automaticPromptActive());
    assert(!card.present(problem, now, now + std::chrono::seconds(20)));
    card.resetContext();
    assert(closes == 1 && expires == 0 && !card.occupied() && !card.automaticPromptActive());
}

void testReminderAuthExpiryPropagation() {
    using namespace graf::windows;
    for (const auto invalid : {"", "-1", "+1", " 123", "123 ", "1.2", "1e9", "9223372036854775808", "9999999999999999999", "12345678901234567890"})
        assert(!DesktopApiClient::calendarAuthExpiryFromHeader(invalid));
    assert(DesktopApiClient::calendarAuthExpiryFromHeader("1800000000") == 1'800'000'000);
    assert(DesktopApiClient::calendarAuthExpiryFromHeader("9223372036854775807") == INT64_MAX);
    CalendarReminderResponse response{200, std::nullopt};
    response.inheritAuthExpiry(2000);
    assert(response.renewedSessionExpiry(1000) == 2000);
    response.authExpiresAt = 3000;
    response.inheritAuthExpiry(4000); // The later calendar response owns its header.
    assert(response.renewedSessionExpiry(1000) == 3000);
    assert(!response.renewedSessionExpiry(3000));
    for (auto status : {0u, 429u, 503u}) {
        response = {status, std::nullopt};
        response.inheritAuthExpiry(2000); // A valid context header survives a calendar failure.
        assert(response.renewedSessionExpiry(1000) == 2000);
    }
    for (auto status : {401u, 403u}) {
        response = {status, std::nullopt, 3000};
        response.inheritAuthExpiry(2000);
        assert(!response.renewedSessionExpiry(1000));
    }
    ReminderRequestIdentity request{7, 11, "synthetic-session"};
    assert(request.matches(7, 11, "synthetic-session"));
    assert(!request.matches(8, 11, "synthetic-session"));
    assert(!request.matches(7, 12, "synthetic-session"));
    assert(!request.matches(7, 11, "replacement-session"));
    assert(!request.matches(7, 11, ""));
    request = {};
    assert(!request.matches(0, 0, ""));
}

void testMeetingUrlIpLiteralSyntax() {
    using graf::windows::MeetingReminderModel;
    for (const auto url : {
        "https://[2001::db8:]/room", "https://[:2001::db8]/room",
        "https://[.2606:4700::1111]/room", "https://[2606:4700::1111.]/room",
        "https://[.2606:4700::1111.]/room", "https://[2606%3A4700::1111]/room",
        "https://[2001::db8::1]/room", "https://[2001:db8:0:0:0:0:1]/room",
        "https://[2001:db8:0:0:0:0:0:0:1]/room", "https://[2001:db8::12345]/room",
        "https://[2001:db8::gg]/room", "https://[::ffff:192.0.2.999]/room",
        "https://[2001:db8::1]extra/room", "https://[2001:db8::1]:0/room",
        "https://[2001:db8::1]:65536/room", "https://[fe80::1%25en0]/room",
        "https://127.0.0.1/room", "https://10.255.255.255/room",
        "https://172.16.0.1/room", "https://172.31.255.255/room",
        "https://192.168.1.1/room", "https://0.0.0.0/room",
        "https://192.000.2.1/room", "https://[2001:db8::1]/room", "https://192.0.2.1/room",
        "https://[::ffff:192.0.2.1]/room",
        "https://192.0.2/room", "https://3221225985/room",
        "https://0xc0000201/room", "https://0xc0.0.2.1/room"}) {
        assert(!MeetingReminderModel::safeMeetingUrl(url));
    }
    for (const auto url : {
        "https://[2606:4700::1111]/room", "https://[2606:4700:0:0:0:0:0:1111]:443/room",
        "https://[2606:4700::]/room", "https://[::ffff:8.8.8.8]/room",
        "https://[2606:4700::8.8.8.8]:65535/room", "https://example.org:0/room",
        "https://256.0.2.1/room", "https://172.15.255.255/room",
        "https://172.32.0.1/room", "https://192.169.0.1:443/room"}) {
        assert(MeetingReminderModel::safeMeetingUrl(url));
    }
}

void testReminderPresenterNeverConsumesRealEventsForPreview() {
    using namespace graf::windows;
    using namespace NativeSettingsBridge;
    std::map<std::string, std::string> disk;
    bool writeAllowed = true;
    NotificationPreferenceStore store{
        [&](std::string_view key) -> std::optional<std::string> { auto it = disk.find(std::string(key)); return it == disk.end() ? std::nullopt : std::optional<std::string>(it->second); },
        [&](std::string_view key, std::string_view value) { if (!writeAllowed) return false; disk[std::string(key)] = value; return true; }};
    RecordingNoticePresenter card;
    card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
    MeetingReminderPresenter presenter(card, store);
    auto now = RecordingNoticePresenter::Clock::now();
    const NotificationRequest preview{NotificationAction::test, {}, false, 1};
    assert(presenter.settings(preview, 9'100, now, false).find("\"error\"") != std::string::npos);
    assert(!card.visible());
    presenter.bind("a", "w", "https://one.example");
    CalendarReminderEvent event{"event", 10'000, 11'000, true, true, "Синтетическая встреча", true, "https://meet.example.com/current"};
    assert(presenter.update({"a", "w", {event}}, presenter.epoch()));
    (void)presenter.settings(preview, 9'939, now, false);
    assert(card.visible() && card.kind() == NoticeKind::preview);
    presenter.reconcile(9'940, now, false);
    assert(card.kind() == NoticeKind::meeting && card.content().title == L"Встреча в календаре");
    (void)presenter.settings(preview, 9'940, now, false);
    assert(card.kind() == NoticeKind::meeting);
    auto edit = NotificationRequest{NotificationAction::set, "showTitles", true, 1};
    assert(presenter.settings(edit, 9'940, now, false).find("\"error\"") == std::string::npos);
    assert(card.content().title == L"Синтетическая встреча");
    writeAllowed = false; edit.booleanValue = false;
    assert(presenter.settings(edit, 9'940, now, false).find("\"error\"") != std::string::npos);
    assert(card.content().title == L"Синтетическая встреча");
    std::optional<ReminderActionTarget> clicked;
    presenter.onActionRequested = [&](auto target, auto action) { assert(action == NoticeAction::join); clicked = target; };
    card.invoke(NoticeAction::join); assert(clicked);
    // A changed URL invalidates the old action; it must not redirect the click.
    event.meetingUrl = "https://meet.example.com/revalidated";
    assert(presenter.update({"a", "w", {event}}, presenter.epoch()));
    assert(!presenter.completeAction(*clicked, NoticeAction::join, 9'941, false));
    presenter.reconcile(9'942, now, false); assert(!card.visible());
    // Preview does not clear dismissal, nor refresh the calendar, nor alter settings.
    (void)presenter.settings(preview, 9'942, now, false);
    presenter.reconcile(9'948, now + std::chrono::seconds(6), false); assert(!card.visible());
    presenter.invalidate(); presenter.bind("a", "w", "https://one.example");
    assert(presenter.update({"a", "w", {event}}, presenter.epoch()));
    presenter.reconcile(9'949, now, false); assert(!card.visible());
    presenter.bind("b", "w", "https://one.example");
    assert(presenter.update({"b", "w", {event}}, presenter.epoch()));
    writeAllowed = true;
    presenter.reconcile(9'949, now, false); assert(card.visible());
    presenter.calendarFailed(); assert(!card.visible());
    assert(!presenter.completeAction(*clicked, NoticeAction::record, 9'950, false));
    // Test remains six seconds even when meeting reminders are disabled.
    writeAllowed = true;
    (void)presenter.settings({NotificationAction::set, "reminders", false, 1}, 9'950, now, false);
    (void)presenter.settings(preview, 9'950, now, false);
    presenter.reconcile(9'955, now + std::chrono::seconds(5), false); assert(card.visible());
    presenter.reconcile(9'956, now + std::chrono::seconds(6), false); assert(!card.visible());
    presenter.invalidate(); assert(!card.visible());
    // A restarted presenter reloads persisted preferences but never old calendar data.
    MeetingReminderPresenter restarted(card, store); restarted.bind("a", "w", "https://one.example");
    assert(restarted.settings({}, 9'950, now, false).find("\"showTitles\":true") != std::string::npos);
    restarted.reconcile(9'950, now, false); assert(!card.visible());
}

void testTheShimAsksOnlyWhatTheAppCanAnswer() {
    const auto script = std::string(graf::windows::NativeSettingsBridge::documentScript());
    // The page calls exactly this handler and awaits the promise the shim returns.
    assert(script.find("window.webkit.messageHandlers.grafRecordingSettings") != std::string::npos);
    assert(script.find("graf:native-settings") != std::string::npos);
    assert(script.find("graf:native-settings-reply") != std::string::npos);
    assert(script.find("__grafNativeSettingsInstalled") != std::string::npos);
    // Both settings pages the app can answer are advertised, and only those.
    assert(script.find("window.webkit.messageHandlers.grafNotificationSettings") != std::string::npos);
    // Installing it twice would replace a page's own pending requests.
    assert(script.find("if (window.__grafNativeSettingsInstalled) return;") != std::string::npos);
}

void testSettingsTransportDoesNotRewritePageContent() {
    const auto script = std::string(graf::windows::NativeSettingsBridge::documentScript());
    // The transport must not inspect user content or own presentation.
    assert(script.find("TreeWalker") == std::string::npos);
    assert(script.find("platformWords") == std::string::npos);
    assert(script.find("setTimeout") == std::string::npos);
    assert(script.find("document.body") == std::string::npos);
    assert(script.find("GRAFDesktopPlatform") == std::string::npos);
    const auto reply = graf::windows::NativeSettingsBridge::notificationSettingsReply({}, true);
    assert(reply.find("canOpenSystemSettings") == std::string::npos);
}

} // namespace

int main() {
    testUserTimeMetadataIsBoundedDataOnly();
    testLocalProblemsGroupSessionAndKeepStableIdentity();
    testLocalProblemsClassifyOnlyTypedStatesAndExactRetryReason();
    testLocalProblemsFreshnessIsStrictAndDoesNotResolveOldProblems();
    testLocalProblemsRequireExactOwnershipAndFrozenCaptureContext();
    testLocalProblemsResolveOnlyCompleteAllUploadedSessions();
    testProtectedLocalProblemsPreserveClassificationAndOwnership();
    testProtectedLocalProblemsOwnResultsAndRefuseQuotaExhaustion();
    testLocalProblemProjectionDoesNotForgetPersistedClaims();
    testProblemClaimsPersistUntilExplicitResolution();
    testProblemClaimsArePrivateAndContextScoped();
    testProblemClaimsVerifyBothWritesAndFailClosedReads();
    testProblemClaimsCorruptionAndCapacityDoNotForgetIncidents();
    testF277NotificationContractBeforeImplementation();
    testF277PreferencesMigrateAndVerifyWrites();
    testF277OffsetsContextAndLinkIdentity();
    testF277PersistedReceiptsFailClosedAndExpire();
    testF277PresenterRestartQuietAndExactAction();
    testUpcomingProjectionAndFrozenTarget();
    testUpcomingPresenterIgnoresReminderSettingsAndCapture();
    testCalendarJoinCardWaitsForHandoff();
    testCalendarJoinFailureAndRetryKeepOriginalExpiry();
    testCalendarJoinFailureCannotReviveRetiredAction();
    testF277ReceiptCorruptionAndCapacityNeverEvictLiveClaims();
    testF277PendingActionCannotOutliveMonotonicDeadline();
    testF277PendingActionCannotReturnAfterAnotherCard();
    testF277QuietPreviewAndDeadlineNeverRestart();
    testF277BlockedSurfaceAndRestartWhileVisible();
    testOnlyTheSettingsPageMayUseTheBridge();
    testTheRequestVocabularyIsThePagesOwn();
    testTheReplyCarriesWhatThePageValidates();
    testATargetThatWouldBreakTheReplyIsLeftOut();
    testQuotesAndControlCharactersCannotLeaveTheJson();
    testARefusalIsStillAnAnswer();
    testEachSettingsPageHasItsOwnRoute();
    testSettingsTransportDoesNotRewritePageContent();
    testTheNotificationReplyIsThePlatformTruth();
    testNotificationRequestsAndOwnerPersistence();
    testReminderOccurrenceAndRevalidation();
    testSharedCardPriorityAndManualClose();
    testCalendarSchemaAndSafeJoin();
    testMeetingUrlIpLiteralSyntax();
    testAutomaticPromptSharesCardPriority();
    testAutomaticPromptProtectedUntilClosedOrInvalidated();
    testReminderAuthExpiryPropagation();
    testReminderPresenterNeverConsumesRealEventsForPreview();
    testTheShimAsksOnlyWhatTheAppCanAnswer();
    std::puts("NativeSettingsBridgeTests passed");
    return 0;
}
