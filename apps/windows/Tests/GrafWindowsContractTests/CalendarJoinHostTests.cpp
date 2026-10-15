#include "../../RecApp/Web/WebView2Host.h"
#include "../../RecApp/Contracts/WindowsDesktopContracts.h"
#include "../../RecApp/Contracts/JsonReader.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
#include <stdexcept>
#include <vector>
#ifdef _WIN32
#include <winrt/base.h>
#endif

using namespace graf::windows;
namespace graf::windows {
struct ProtectedUploadQueueValueTestPeer {
    static std::shared_ptr<const ProtectedUploadQueueValue> playbackInventory() {
        auto value = std::const_pointer_cast<ProtectedUploadQueueValue>(inventory(9));
        value->operations_.clear();
        for (auto& row : value->items_) {
            row.status = UploadQueueStatus::pending;
            row.directoryId = row.localRecordingId;
        }
        value->items_[1].meetingId = "66666666-6666-4666-8666-666666666666";
        value->items_[2].status = UploadQueueStatus::quarantined;
        value->items_[3].safeReason = "local_delete_pending";
        value->items_[6].ownerUserId = "44444444-4444-4444-8444-444444444444";
        value->items_[7].ownerWorkspaceId = "55555555-5555-4555-8555-555555555555";
        value->items_[8].ownerUserId.clear();
        for (unsigned n : {4U, 5U}) {
            ProtectedUploadQueueValue::Operation operation;
            operation.targetId = value->items_[n].localRecordingId;
            operation.target = DeletionTarget::ownOrigin;
            operation.actorUserId = value->items_[n].ownerUserId;
            operation.workspaceId = value->items_[n].ownerWorkspaceId;
            operation.phase = n == 4 ? DeletionOperationPhase::queued : DeletionOperationPhase::rejected;
            value->operations_.push_back(std::move(operation));
        }
        return value;
    }
    static std::shared_ptr<const ProtectedUploadQueueValue> inventory(unsigned count = 67,
        const char* workspace = "22222222-2222-4222-8222-222222222222") {
        auto value = std::shared_ptr<ProtectedUploadQueueValue>(new ProtectedUploadQueueValue);
        for (unsigned n = 0; n != count; ++n) {
            ProtectedUploadQueueValue::Item row;
            row.localRecordingId = "synthetic-row-" + std::to_string(n);
            row.directoryId = row.localRecordingId;
            row.ownerUserId = n == 65 ? "44444444-4444-4444-8444-444444444444" : "11111111-1111-4111-8111-111111111111";
            row.ownerWorkspaceId = workspace;
            if (n == 66) { row.ownerUserId.clear(); row.ownerWorkspaceId.clear(); }
            row.status = static_cast<UploadQueueStatus>(n % 7);
            row.updatedAtMs = 1'900'000'000'000; // Not a recording date.
            row.acceptedBytes = {10,20,30}; // Not a percentage without package sizes.
            value->items_.push_back(std::move(row));
        }
        for (unsigned n = 0; n != 3; ++n) {
            ProtectedUploadQueueValue::Operation operation;
            operation.operationId = n == 0 ? "visible-operation" : "hidden-operation";
            operation.actorUserId = "11111111-1111-4111-8111-111111111111";
            operation.workspaceId = "22222222-2222-4222-8222-222222222222";
            operation.serverOrigin = n == 1 ? "https://foreign.invalid" : "https://rec.2brain.pro";
            if (n == 2) operation.workspaceId = "55555555-5555-4555-8555-555555555555";
            operation.target = DeletionTarget::meeting;
            operation.targetId = "66666666-6666-4666-8666-666666666666";
            operation.phase = DeletionOperationPhase::accepted;
            value->operations_.push_back(std::move(operation));
        }
        return value;
    }
};
// Exercise the actual host gate without giving production a document-seeding API.
struct WebView2CalendarJoinFixture {
    WebView2Host host;
    std::vector<WebView2Host::CalendarJoinRequest> accepted, cancelled;
    std::vector<CalendarJoinResult> replies;
    std::vector<std::string> nonces;
    std::function<void(CalendarJoinResult)> onReply;
    std::uint64_t messageId = 0;
    std::vector<WebView2Host::UserTimeRead> timeReads;
    void timeReader() {
        host.nativeReadUserTime_ = [this](auto request) { timeReads.push_back(std::move(request)); };
    }
    void timeAccount(std::string token = "synthetic-session", std::uint64_t generation = 1,
                     std::string user = "11111111-1111-4111-8111-111111111111",
                     std::string workspace = "22222222-2222-4222-8222-222222222222",
                     std::string origin = "https://rec.2brain.pro") {
        host.bindUserTimeAccount(std::move(origin), std::move(user), std::move(workspace), std::move(token), generation);
    }
    void timeCookie(std::string token = "synthetic-session") {
        host.reconcileUserTimeCookie(host.documentGeneration_, host.documentNonce_, host.currentUrl_, std::move(token));
    }
    std::string timeMetadata(std::string zone = "UTC", std::string user = "11111111-1111-4111-8111-111111111111",
                             std::string workspace = "22222222-2222-4222-8222-222222222222",
                             std::string url = "https://rec.2brain.pro/desktop/meetings") {
        return "{\"userId\":\"" + user + "\",\"workspaceId\":\"" + workspace +
            "\",\"sessionId\":\"33333333-3333-4333-8333-333333333333\",\"timeZone\":\"" + zone +
            "\",\"documentURL\":\"" + url + "\"}";
    }
    void finishTime(std::size_t n, std::string raw) {
        host.completeUserTimeRead(timeReads.at(n), raw, host.currentUrl_);
    }
    void timeNonce(std::string value) { host.documentNonce_ = std::move(value); }
    void authTime(std::string token = "synthetic-session") {
        if (host.reconcileAuthSessionForDocument(host.documentGeneration_, host.documentNonce_, host.currentUrl_, token, true))
            timeCookie(std::move(token));
    }
    void timeSource(std::size_t n, std::string_view source) {
        host.completeUserTimeRead(timeReads.at(n), timeMetadata(), source);
    }
    void newTimeDocument() {
        host.setRuntimeState(WebRuntimeState::initializing);
        document("new-time-document");
        timeReader();
    }
    WebView2CalendarJoinFixture() {
        document();
        host.setCalendarJoinHandlers(
            [this](auto request) { accepted.push_back(std::move(request)); },
            [this](auto request) {
                assert(host.documentGeneration_ == request.documentGeneration);
                assert(host.documentNonce_ == request.nonce);
                assert(host.runtimeState_ == WebRuntimeState::ready && host.alive_->load());
                cancelled.push_back(std::move(request));
            });
    }
    ~WebView2CalendarJoinFixture() { host.close(); }
    void document(std::string nonce = "nonce-1") {
        host.currentUrl_ = host.committedDocumentUrl_ = "https://rec.2brain.pro/desktop/meetings";
        host.alive_ = std::make_shared<std::atomic_bool>(true);
        ++host.documentGeneration_;
        host.setRuntimeState(WebRuntimeState::ready);
        host.documentNonce_ = std::move(nonce);
        host.bridge_.rotateNonce(host.documentNonce_);
        host.nativeReplyCalendarJoin_ = [this](const auto& request, auto result) {
            assert(host.calendarDocumentCurrent(request));
            nonces.push_back(request.nonce);
            replies.push_back(result);
            if (onReply) onReply(result);
        };
        messageId = 0;
    }
    static std::string requestId(unsigned n) {
        char value[37];
        std::snprintf(value, sizeof(value), "%08x-ABCD-ABCD-ABCD-000000000000", n);
        return value;
    }
    WebViewBridgeEnvelope message(unsigned n, bool cancel = false) {
        const auto payload = std::string(cancel ? "{" : "{\"action\":\"joinCalendarEvent\",") +
            "\"eventId\":\"ABCDEFAB-1234-4567-89AB-ABCDEFABCDEF\",\"requestId\":\"" + requestId(n) + "\"}";
        return {std::string(kBridgeProtocol), kBridgeProtocolVersion, ++messageId,
            host.documentNonce_, "https://rec.2brain.pro", BridgeDirection::webToNative,
            cancel ? "calendar_join_cancel" : "calendar_join", payload, 1};
    }
    void send(unsigned n, bool cancel = false) {
        host.handleCalendarJoinMessage(message(n, cancel), host.currentUrl_);
    }
    void receive(const WebViewBridgeEnvelope& message, std::string_view source) {
        host.handleCalendarJoinMessage(message, source);
    }
    void presentation(std::function<void(std::string_view)> callback) { host.nativeRunScript_ = std::move(callback); }
    void inventoryPublisher(unsigned& calls) {
        host.nativePublishLocalRecordings_ = [this, &calls] {
            ++calls;
            host.protectedLocalPublicationPending_ = false; // Observe setter dispatch, not COM delivery.
        };
    }
    CustodyString inventoryMessage() const { return host.protectedLocalRecordingsMessage(); }
    void failInventoryPublication() { host.failProtectedLocalPublication(); }
    bool inventoryRetryScheduled(const std::shared_ptr<const ProtectedUploadQueueValue>& value,
        std::chrono::steady_clock::time_point before, std::chrono::steady_clock::time_point after) const {
        return host.protectedLocalPublicationPending_ && host.protectedLocalValue_ == value &&
            host.protectedLocalRetryAt_ >= before + std::chrono::seconds(2) &&
            host.protectedLocalRetryAt_ <= after + std::chrono::seconds(2);
    }
    void publish() { host.publishCalendarJoinAvailability(); }
    void finish(CalendarJoinState state, CalendarJoinReason reason = CalendarJoinReason::none) {
        host.replyCalendarJoin(accepted.back(), {state, reason});
    }
    std::size_t history() const { return host.calendarRequestIds_.size(); }
    void route(std::string_view path) {
        host.currentUrl_ = host.committedDocumentUrl_ = std::string("https://rec.2brain.pro") + std::string(path);
    }
};
}

void testProtectedPlaybackPermission() {
    const auto before = CustodyOwnedMemory::usedBytes();
    {
        WebView2CalendarJoinFixture f;
        const auto value = ProtectedUploadQueueValueTestPeer::playbackInventory();
        const auto update = [&](bool complete = true, std::uint64_t epoch = 1) {
            f.host.setProtectedLocalRecordings(value, complete, "https://rec.2brain.pro",
                "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", epoch);
        };
        update();
        assert(!f.host.localRecordingActionAllowed("open", "synthetic-row-0"));
        f.timeReader(); f.timeAccount(); f.timeCookie(); f.finishTime(0, f.timeMetadata());
        const auto document = f.host.documentGeneration();
        assert(f.host.localPlaybackDocumentCurrent(document, "nonce-1"));
        assert(!f.host.localPlaybackDocumentCurrent(0, "nonce-1"));
        assert(!f.host.localPlaybackDocumentCurrent(document + 1, "nonce-1"));
        assert(!f.host.localPlaybackDocumentCurrent(document, "stale-nonce"));
        assert(f.host.localRecordingActionAllowed("open", "synthetic-row-0") &&
            "protected_owned_local_row_must_allow_validation_request");
        assert(f.host.localRecordingActionAllowed("open", "synthetic-row-5")); // Rejected deletion does not revoke content.
        for (unsigned n : {1U,2U,3U,4U,6U,7U,8U})
            assert(!f.host.localRecordingActionAllowed("open", "synthetic-row-" + std::to_string(n)));
        assert(f.host.localRecordingActionAllowed("send", "synthetic-row-0"));
        assert(f.host.localRecordingActionAllowed("send", "synthetic-row-1")); // Reconcile an existing server identity.
        assert(f.host.localRecordingActionAllowed("send", "synthetic-row-5"));
        for (unsigned n : {2U,3U,4U,6U,7U,8U})
            assert(!f.host.localRecordingActionAllowed("send", "synthetic-row-" + std::to_string(n)));
        assert(f.host.localRecordingActionAllowed("delete", "synthetic-row-0") &&
            "protected_owned_local_copy_must_allow_native_confirmation");
        assert(f.host.localRecordingActionAllowed("delete", "synthetic-row-1") &&
            "local_copy_removal_must_not_be_disabled_by_server_history");
        assert(!f.host.localRecordingActionAllowed("read_file", "synthetic-row-0"));
        assert(!f.host.localRecordingActionAllowed("open", "missing"));
        assert(!f.host.localRecordingActionAllowed("open", ""));
        assert(!f.host.localRecordingActionAllowed("open", std::string(301, 'x')));
        const auto message = f.inventoryMessage();
        const auto fields = json_detail::JsonReader<>(message).read(); assert(fields);
        const auto rows = json_detail::JsonReader<>(fields->at("rows")).readArray(); assert(rows);
        for (const auto row : *rows) {
            const auto rowFields = json_detail::JsonReader<>(row).read(); assert(rowFields);
            const bool allowed = rowFields->at("id") == "\"synthetic-row-0\"" || rowFields->at("id") == "\"synthetic-row-5\"";
            assert(rowFields->at("canOpen") == (allowed ? "true" : "false"));
            const bool sendAllowed = allowed || rowFields->at("id") == "\"synthetic-row-1\"";
            assert(rowFields->at("canSend") == (sendAllowed ? "true" : "false"));
            assert(rowFields->at("canDelete") == (rowFields->at("id") == "\"synthetic-row-3\"" ? "false" : "true"));
        }
        update(false);
        assert(!f.host.localRecordingActionAllowed("open", "synthetic-row-0"));
        assert(!f.host.localRecordingActionAllowed("send", "synthetic-row-0"));
        assert(!f.host.localRecordingActionAllowed("delete", "synthetic-row-0"));
        assert(f.host.localPlaybackDocumentCurrent(document, "nonce-1")); // Pause/Close need no full-queue grant.
        update(true, 2);
        assert(!f.host.localRecordingActionAllowed("open", "synthetic-row-0")); // Epoch mismatch.
        assert(!f.host.localRecordingActionAllowed("send", "synthetic-row-0"));
        assert(!f.host.localRecordingActionAllowed("delete", "synthetic-row-0"));
        update();
        f.newTimeDocument();
        assert(!f.host.localPlaybackDocumentCurrent(document, "nonce-1"));
        assert(!f.host.localRecordingActionAllowed("open", "synthetic-row-0"));
        f.host.close();
        assert(!f.host.localRecordingActionAllowed("open", "synthetic-row-0"));
    }
    for (unsigned edge = 0; edge != 4; ++edge) {
        WebView2CalendarJoinFixture f;
        f.host.setProtectedLocalRecordings(ProtectedUploadQueueValueTestPeer::playbackInventory(), true, "https://rec.2brain.pro",
            "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", 1);
        f.timeReader(); f.timeAccount(); f.timeCookie(); f.finishTime(0, f.timeMetadata());
        const auto document = f.host.documentGeneration();
        assert(f.host.localPlaybackDocumentCurrent(document, "nonce-1"));
        if (edge == 0) f.timeAccount({}, 2); // Logout.
        if (edge == 1) f.timeAccount("synthetic-session", 2, "44444444-4444-4444-8444-444444444444");
        if (edge == 2) f.timeAccount("synthetic-session", 2, "11111111-1111-4111-8111-111111111111", "55555555-5555-4555-8555-555555555555");
        if (edge == 3) f.timeCookie("replacement-session");
        assert(!f.host.localPlaybackDocumentCurrent(document, "nonce-1"));
        assert(!f.host.localRecordingActionAllowed("open", "synthetic-row-0"));
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}

void testProtectedInventoryPresentation() {
    const auto before = CustodyOwnedMemory::usedBytes();
    {
        WebView2CalendarJoinFixture f;
        const auto value = ProtectedUploadQueueValueTestPeer::inventory();
        const auto update = [&](bool complete = true, std::uint64_t generation = 1) {
            f.host.setProtectedLocalRecordings(value, complete, "https://rec.2brain.pro",
                "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", generation);
        };
        update();
        assert(f.inventoryMessage().find("synthetic-row") == CustodyString::npos); // Ready is not adoption/auth.
        unsigned fallbackAttempts = 0;
        f.presentation([&](std::string_view) { ++fallbackAttempts; throw std::runtime_error("synthetic-unavailable-WebView"); });
        bool fallbackEscaped = false;
        const auto beforeFallback = std::chrono::steady_clock::now();
        try { f.failInventoryPublication(); } catch (...) { fallbackEscaped = true; }
        const auto afterFallback = std::chrono::steady_clock::now();
        assert(!fallbackEscaped && fallbackAttempts == 1 && f.inventoryRetryScheduled(value, beforeFallback, afterFallback));
        f.presentation({});
        f.timeReader(); f.timeAccount(); f.timeCookie();
        assert(f.inventoryMessage().find("synthetic-row") == CustodyString::npos); // Cookie is not HTML identity.
        f.finishTime(0, f.timeMetadata());
        f.host.setProtectedLocalRecordings(ProtectedUploadQueueValueTestPeer::inventory(302), true, "https://rec.2brain.pro",
            "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", 1);
        const auto fullMessage = f.inventoryMessage();
        assert(fullMessage.size() > kBridgeMaxSerializedBytes); // Incoming envelope limit is not an inventory cap.
        const auto fullFields = json_detail::JsonReader<>(fullMessage).read(); assert(fullFields);
        const auto fullRows = json_detail::JsonReader<>(fullFields->at("rows")).readArray(); assert(fullRows && fullRows->size() == 300);
        assert(fullMessage.find("synthetic-row-301") != CustodyString::npos);
        update();
        {
            const auto message = f.inventoryMessage();
            json_detail::JsonReader<> reader(message);
            const auto fields = reader.read(); assert(fields);
            assert(fields->at("state") == "\"ready\"" && fields->at("recoveryRequired") == "true");
            json_detail::JsonReader<> rowsReader(fields->at("rows"));
            const auto rows = rowsReader.readArray(); assert(rows && rows->size() == 65);
            assert(message.find("synthetic-row-65") == CustodyString::npos && message.find("synthetic-row-66") == CustodyString::npos);
            assert(message.find("hidden-operation") == CustodyString::npos && message.find("visible-operation") != CustodyString::npos);
            unsigned index = 0;
            for (const auto row : *rows) {
                const auto rowFields = json_detail::JsonReader<>(row).read(); assert(rowFields);
                const auto status = static_cast<UploadQueueStatus>(index++ % 7);
                assert(rowFields->at("canOpen") == (status == UploadQueueStatus::quarantined ? "false" : "true"));
                const bool send = status == UploadQueueStatus::pending || status == UploadQueueStatus::retry ||
                    status == UploadQueueStatus::needsAuth || status == UploadQueueStatus::blocked;
                assert(rowFields->at("canSend") == (send ? "true" : "false"));
                assert(rowFields->at("canDelete") == (status == UploadQueueStatus::uploading ? "false" : "true"));
                for (const auto unknown : {"durationSeconds", "sessionDurationSeconds", "startedAt", "updatedAt", "progressPercent"})
                    assert(rowFields->count(unknown) == 0);
            }
        }
        assert(f.host.localRecordingActionAllowed("open", "synthetic-row-0"));
        assert(f.host.localRecordingActionAllowed("send", "synthetic-row-0"));
        assert(f.host.localRecordingActionAllowed("delete", "synthetic-row-0"));
        update(false);
        assert(f.inventoryMessage().find("\"state\":\"checking\"") != CustodyString::npos);
        assert(f.inventoryMessage().find("synthetic-row-64") != CustodyString::npos); // Last known complete value, not a prefix.
        update();
        {
            CustodyBytes full;
            full.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
            bool refused = false;
            try { (void)f.inventoryMessage(); } catch (const std::bad_alloc&) { refused = true; }
            assert(refused); // No ordinary allocator fallback / successful empty message.
        }
        f.timeAccount("synthetic-session", 2, "11111111-1111-4111-8111-111111111111", "55555555-5555-4555-8555-555555555555");
        f.host.setProtectedLocalRecordings(ProtectedUploadQueueValueTestPeer::inventory(67, "55555555-5555-4555-8555-555555555555"), true,
            "https://rec.2brain.pro", "11111111-1111-4111-8111-111111111111", "55555555-5555-4555-8555-555555555555", 2);
        assert(f.inventoryMessage().find("synthetic-row") == CustodyString::npos);
        f.finishTime(0, f.timeMetadata()); // Old callback cannot accept the previous HTML workspace.
        assert(f.inventoryMessage().find("synthetic-row") == CustodyString::npos);
        f.finishTime(1, f.timeMetadata()); // Current callback, old HTML identity.
        assert(f.inventoryMessage().find("synthetic-row") == CustodyString::npos);
        f.timeAccount("synthetic-session", 3); f.finishTime(2, f.timeMetadata("Europe/Unknown"));
        update(true, 3);
        assert(f.host.preferredUserTimeZone().empty());
        assert(f.inventoryMessage().find("synthetic-row-64") != CustodyString::npos); // No dependency on timezone formatter.
        f.host.setProtectedLocalRecordings({}, false, "https://rec.2brain.pro", "11111111-1111-4111-8111-111111111111",
            "22222222-2222-4222-8222-222222222222", 3);
        assert(f.inventoryMessage().find("\"state\":\"unavailable\"") != CustodyString::npos);
        update(true, 3);
        f.host.setRuntimeState(WebRuntimeState::initializing);
        assert(f.inventoryMessage().find("synthetic-row") == CustodyString::npos);
        f.timeAccount({}, 4);
        assert(f.inventoryMessage().find("synthetic-row") == CustodyString::npos);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}

void testProtectedInventoryTimings() {
    const auto before = CustodyOwnedMemory::usedBytes();
    {
        WebView2CalendarJoinFixture f;
        const auto value = ProtectedUploadQueueValueTestPeer::inventory(2);
        auto timings = std::allocate_shared<ProtectedLocalRecordingTimings>(CustodyAllocator<ProtectedLocalRecordingTimings>{});
        timings->snapshot = value;
        timings->rows.resize(value->items().size());
        constexpr std::uint64_t started = 1'700'000'000'123;
        timings->rows[0] = ProtectedLocalRecordingTiming{999, started, started + 1201, 180};
        unsigned publications = 0;
        f.inventoryPublisher(publications);
        const auto update = [&](std::shared_ptr<const ProtectedLocalRecordingTimings> metadata = {}) {
            f.host.setProtectedLocalRecordings(value, true, "https://rec.2brain.pro",
                "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", 1, std::move(metadata));
        };
        f.timeReader(); f.timeAccount(); f.timeCookie(); f.finishTime(0, f.timeMetadata());
        update();
        const auto check = [&](bool known, const char* duration = "0", const char* session = "2") {
            const auto message = f.inventoryMessage();
            const auto fields = json_detail::JsonReader<>(message).read(); assert(fields);
            const auto rows = json_detail::JsonReader<>(fields->at("rows")).readArray(); assert(rows && rows->size() == 2);
            const auto first = json_detail::JsonReader<>(rows->at(0)).read(); assert(first);
            const auto second = json_detail::JsonReader<>(rows->at(1)).read(); assert(second);
            if (known) {
                assert(first->count("startedAt") && first->count("durationSeconds") && first->count("sessionDurationSeconds") &&
                    first->count("generatedTitlePrefix") && "protected_inventory_known_timing_is_not_unknown");
                assert(first->at("startedAt") == "\"2023-11-14T22:13:20Z\"" && first->at("generatedTitlePrefix") == "\"Запись \"");
                assert(first->at("durationSeconds") == duration && first->at("sessionDurationSeconds") == session);
            } else for (const auto field : {"startedAt", "generatedTitlePrefix", "durationSeconds", "sessionDurationSeconds"})
                assert(first->count(field) == 0);
            for (const auto field : {"startedAt", "generatedTitlePrefix", "durationSeconds", "sessionDurationSeconds"})
                assert(second->count(field) == 0); // Unknown is not a measured subsecond duration.
            for (const auto* row : {&*first, &*second}) {
                assert(row->at("canOpen") == "true"); // Permission is independent of timing availability.
                assert(row->at("canSend") == (row == &*first ? "true" : "false")); // Second row is already uploading.
                assert(row->at("canDelete") == (row == &*first ? "true" : "false"));
                assert(row->at("showsPartialDuration") == "false");
                assert(row->count("updatedAt") == 0 && row->count("progressPercent") == 0);
            }
        };
        check(false);
        const auto beforeMetadata = publications;
        update(timings);
        check(true);
        assert(publications == beforeMetadata + 1 && "protected_inventory_metadata_only_arrival_must_publish");
        update(timings); assert(publications == beforeMetadata + 1);
        auto longer = std::allocate_shared<ProtectedLocalRecordingTimings>(CustodyAllocator<ProtectedLocalRecordingTimings>{}, *timings);
        longer->rows[0]->durationMs = 5000;
        update(longer); check(true, "5", "5"); // Session duration never understates saved duration.
        auto mismatched = std::allocate_shared<ProtectedLocalRecordingTimings>(CustodyAllocator<ProtectedLocalRecordingTimings>{}, *timings);
        mismatched->snapshot = ProtectedUploadQueueValueTestPeer::inventory(2); // Equal rows are not the same adopted snapshot.
        update(mismatched); check(false);
        auto incomplete = std::allocate_shared<ProtectedLocalRecordingTimings>(CustodyAllocator<ProtectedLocalRecordingTimings>{}, *timings);
        incomplete->rows.resize(1);
        update(incomplete); check(false); // No prefix metadata attachment.
        update(timings); check(true);
        f.timeAccount("synthetic-session", 2, "11111111-1111-4111-8111-111111111111", "55555555-5555-4555-8555-555555555555");
        f.finishTime(0, f.timeMetadata()); // Stale document callback cannot expose retained timings.
        const auto revoked = f.inventoryMessage();
        assert(revoked.find("synthetic-row") == CustodyString::npos && revoked.find("2023-11-14") == CustodyString::npos);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}

void testUserTimeIsBoundToNativeAccountAndDocument() {
    using F = WebView2CalendarJoinFixture;
    for (unsigned boundary = 0; boundary != 4; ++boundary) {
        F f; f.timeReader(); f.timeAccount();
        f.host.setAuthSessionHandler([&, boundary](std::string token) {
            if (boundary == 1) f.newTimeDocument();
            if (boundary == 2) { f.host.close(); f.newTimeDocument(); }
            f.timeAccount(token, boundary == 0 ? 2 : 1); f.timeCookie(token);
            f.finishTime(0, f.timeMetadata());
            throw std::runtime_error("old auth handler after new context");
        });
        f.authTime();
        assert(f.host.preferredUserTimeZone() == "UTC");
    }
    {
        F f; f.timeReader(); f.timeAccount();
        const auto revision = f.host.userTimeRevision();
        f.host.setAuthSessionHandler([](std::string) { throw std::runtime_error("matching auth handler failure"); });
        f.authTime();
        assert(f.host.preferredUserTimeZone().empty() && f.host.userTimeRevision() > revision && f.timeReads.empty());
    }
    {
        F f; f.timeReader(); f.timeAccount();
        assert(f.timeReads.empty()); // Ready is not cookie reconciliation.
        f.timeCookie(); assert(f.timeReads.size() == 1);
        f.finishTime(0, f.timeMetadata());
        assert(f.host.preferredUserTimeZone() == "UTC");
        const auto revision = f.host.userTimeRevision();
        f.timeAccount(); f.timeCookie();
        assert(f.timeReads.size() == 1 && f.host.userTimeRevision() == revision);
        f.timeAccount("synthetic-session", 2); // Same token, new auth generation.
        assert(f.host.preferredUserTimeZone().empty() && f.timeReads.size() == 2);
        f.finishTime(1, f.timeMetadata());
        const auto accepted = f.host.userTimeRevision();
        f.finishTime(0, "null"); // Late invalid callback cannot erase a new preference.
        assert(f.host.preferredUserTimeZone() == "UTC" && f.host.userTimeRevision() == accepted);
        f.timeAccount("changed-session", 3);
        assert(f.host.preferredUserTimeZone().empty() && f.timeReads.size() == 2);
        f.timeCookie("changed-session"); assert(f.timeReads.size() == 3);
        f.finishTime(2, f.timeMetadata()); assert(f.host.preferredUserTimeZone() == "UTC");
        f.timeAccount(""); assert(f.host.preferredUserTimeZone().empty());
        f.finishTime(2, f.timeMetadata()); assert(f.host.preferredUserTimeZone().empty());
    }
    for (unsigned invalid = 0; invalid != 9; ++invalid) {
        F f; f.timeReader(); f.timeCookie(); f.timeAccount();
        assert(f.timeReads.size() == 1);
        auto raw = f.timeMetadata();
        if (invalid == 0) raw = "null";
        if (invalid == 1) raw = f.timeMetadata("Unknown/Zone");
        if (invalid == 2) raw = f.timeMetadata("UTC", "44444444-4444-4444-8444-444444444444");
        if (invalid == 3) raw = f.timeMetadata("UTC", "11111111-1111-4111-8111-111111111111", "44444444-4444-4444-8444-444444444444");
        if (invalid == 4) raw = f.timeMetadata("UTC", "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", "https://evil.test/desktop/meetings");
        if (invalid == 5) raw = f.timeMetadata("UTC", "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", "https://rec.2brain.pro/desktop/settings");
        if (invalid == 6) raw = std::string(2049, ' ');
        if (invalid == 7) raw = "{}";
        if (invalid == 8) raw = f.timeMetadata(""); // Accepted system fallback.
        const auto revision = f.host.userTimeRevision();
        f.finishTime(0, raw);
        assert(f.host.preferredUserTimeZone().empty() && f.host.userTimeRevision() > revision);
        f.timeAccount(); assert(f.timeReads.size() == 1); // No automatic script retry loop.
    }
    for (unsigned change = 0; change != 7; ++change) {
        F f; f.timeReader(); f.timeCookie(); f.timeAccount();
        f.finishTime(0, f.timeMetadata()); assert(f.host.preferredUserTimeZone() == "UTC");
        if (change == 0) f.host.close();
        if (change == 1) f.host.handleProcessFailure(WebProcessFailure::renderExited, 0);
        if (change == 2) f.host.setRuntimeState(WebRuntimeState::authRequired);
        if (change == 3) (void)f.host.beginDocumentNavigation("https://rec.2brain.pro/desktop/meetings", 9, false, 0);
        if (change == 4) f.timeAccount("synthetic-session", 1, "44444444-4444-4444-8444-444444444444");
        if (change == 5) f.timeAccount("synthetic-session", 1, "11111111-1111-4111-8111-111111111111", "44444444-4444-4444-8444-444444444444");
        if (change == 6) f.timeAccount("synthetic-session", 1, "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", "https://evil.test");
        assert(f.host.preferredUserTimeZone().empty());
        f.finishTime(0, f.timeMetadata()); assert(f.host.preferredUserTimeZone().empty());
    }
    for (const auto route : {"/login", "/settings/account/email-link/start", "/billing/checkout/start", "/frame/calendar", "/review", "/unknown"}) {
        F f; f.route(route); f.timeReader(); f.timeCookie(); f.timeAccount();
        assert(f.timeReads.empty()); // A same-origin URL is not a presentation authority.
    }
    {
        F f; f.timeReader(); f.timeCookie(); f.timeAccount();
        // A nonce change makes even an otherwise identical callback stale.
        f.timeNonce("new-nonce");
        const auto revision = f.host.userTimeRevision();
        f.finishTime(0, f.timeMetadata());
        assert(f.host.preferredUserTimeZone().empty() && f.host.userTimeRevision() == revision);
    }
    {
        F f; f.timeReader(); f.timeCookie(); f.timeAccount();
        f.timeSource(0, "https://evil.test/desktop/meetings");
        assert(f.host.preferredUserTimeZone().empty());
        f.newTimeDocument(); f.timeAccount(); assert(f.timeReads.size() == 1);
        f.timeCookie(); assert(f.timeReads.size() == 2);
        f.finishTime(1, f.timeMetadata());
        f.finishTime(0, "null"); assert(f.host.preferredUserTimeZone() == "UTC");
    }
    for (const auto route : {"/desktop/settings", "/desktop/settings/account", "/billing", "/billing/usage", "/desktop/share/synthetic"}) {
        F f; f.route(route); f.timeReader(); f.timeCookie(); f.timeAccount();
        assert(f.timeReads.size() == 1);
        f.finishTime(0, f.timeMetadata("UTC", "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", f.host.currentUrl()));
        assert(f.host.preferredUserTimeZone() == "UTC");
    }
}

int main() {
    {
        // Reuse the existing host/presentation fixture, not a copy of AppMain.
        WebView2CalendarJoinFixture f;
        const auto generation = f.host.documentGeneration();
        constexpr std::string_view id = "77777777-7777-4777-8777-777777777777";
        CabinetDeletionOutcome outcome; outcome.saved = true; outcome.accepted = 1;
        unsigned calls = 0;
        f.presentation([&](std::string_view script) {
            assert(script == RecordingDeletionBridge::completionScript(id, outcome)); ++calls;
        });
        CustodyAllocator<char> allocator;
        const auto count = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
        auto* reserved = allocator.allocate(count);
        bool refused = false;
        try { (void)f.host.completeDeletionSelection(generation, id, outcome); }
        catch (const std::bad_alloc&) { refused = true; }
        assert(refused && !calls);
        assert(f.host.completeDeletionSelection(generation + 1, id, outcome)); // Stale discard does not allocate.
        allocator.deallocate(reserved, count);
        assert(f.host.completeDeletionSelection(generation, id, outcome) && calls == 1);
        f.presentation([](auto) { throw std::runtime_error("generated handoff refusal"); });
        bool failed = false;
        try { (void)f.host.completeDeletionSelection(generation, id, outcome); }
        catch (const std::runtime_error&) { failed = true; }
        assert(failed);
        f.presentation([&](auto) { ++calls; });
        assert(f.host.completeDeletionSelection(generation, id, outcome) && calls == 2);
        f.presentation({});
        assert(!f.host.completeDeletionSelection(generation, id, outcome) && calls == 2);
        f.host.setRuntimeState(WebRuntimeState::initializing);
        assert(f.host.documentGeneration() == generation);
        assert(!f.host.completeDeletionSelection(generation, id, outcome) && calls == 2);
        f.document("new-deletion-document");
        assert(f.host.completeDeletionSelection(generation, id, outcome) && calls == 2);
    }
#ifdef _WIN32
    winrt::init_apartment(winrt::apartment_type::single_threaded);
#endif
    testProtectedPlaybackPermission();
    testProtectedInventoryPresentation();
    testProtectedInventoryTimings();
    testUserTimeIsBoundToNativeAccountAndDocument();
    using F = WebView2CalendarJoinFixture;
    {
        F f; std::vector<std::string> scripts;
        f.presentation([&](auto script) { scripts.emplace_back(script); });
        f.host.setCalendarJoinHandlers([](auto) {}, [](auto) {});
        assert(scripts.back() == "window.__grafSetCalendarJoinAvailable?.(true)");
        f.host.setCalendarJoinHandlers([](auto) {}, {});
        assert(scripts.back() == "window.__grafSetCalendarJoinAvailable?.(false)");
        f.route("/settings");
        f.host.setCalendarJoinHandlers([](auto) {}, [](auto) {});
        assert(scripts.back() == "window.__grafSetCalendarJoinAvailable?.(false)");
        f.presentation({}); // Fixture captures must not outlive the local vector.
    }
    {
        F f; f.send(1);
        f.presentation([](auto) { throw std::runtime_error("synthetic-script-failure"); });
        f.host.setCalendarJoinHandlers([](auto) {}, [](auto) {});
        assert(f.cancelled.size() == 1 && f.replies.back().state == CalendarJoinState::cancelled);
        f.send(2); assert(f.accepted.size() == 1 && f.history() == 1 && f.replies.size() == 2);
        // Failed publication cannot admit a request even if its callback is a no-op.
        std::string published;
        f.presentation([&](auto script) {published = script;});
        f.publish(); // Successful replay after the transient error must preserve native denial.
        assert(published == "window.__grafSetCalendarJoinAvailable?.(false)");
        f.send(2); assert(f.history() == 1 && f.replies.size() == 2);
        f.host.setCalendarJoinHandlers([&](auto request) {f.accepted.push_back(std::move(request));}, [](auto) {});
        assert(published == "window.__grafSetCalendarJoinAvailable?.(true)");
        f.send(2); assert(f.accepted.size() == 2 && f.history() == 2);
        f.presentation({});
    }
    {
        F f;
        f.host.setCalendarJoinHandlers({}, {});
        f.send(1);
        assert(f.accepted.empty() && f.replies.empty() && f.history() == 0);
        f.host.setCalendarJoinHandlers([](auto) {}, {});
        f.send(1); assert(f.replies.empty());
        f.host.setCalendarJoinHandlers({}, [](auto) {});
        f.send(1); assert(f.replies.empty());
    }
    {
        F f; f.send(1);
        assert(f.accepted.size() == 1 && f.accepted[0].intent.eventId == "abcdefab-1234-4567-89ab-abcdefabcdef");
        assert(f.replies.back().state == CalendarJoinState::resolving);
        f.finish(CalendarJoinState::handedOff); // Cannot skip opening.
        assert(f.replies.size() == 1);
        f.finish(CalendarJoinState::opening);
        f.finish(CalendarJoinState::opening); // Cannot duplicate/rewind.
        f.finish(CalendarJoinState::resolving);
        assert(f.replies.size() == 2);
        f.finish(CalendarJoinState::handedOff);
        f.finish(CalendarJoinState::failed, CalendarJoinReason::launchFailed);
        assert(f.replies.size() == 3 && f.replies.back().state == CalendarJoinState::handedOff);
        f.send(1); // Different message ID, same request UUID.
        assert(f.accepted.size() == 1 && f.replies.size() == 3);
    }
    {
        F f; f.send(1); f.send(2);
        assert(f.accepted.size() == 1 && f.history() == 2 && f.replies.back().reason == CalendarJoinReason::busy);
        f.send(2); assert(f.replies.size() == 2);
        f.send(2, true); assert(f.cancelled.empty());
        auto wrong = f.message(1, true);
        wrong.payloadJson.replace(wrong.payloadJson.find("ABCDEFAB"), 8, "11111111");
        f.receive(wrong, f.host.currentUrl());
        assert(f.cancelled.empty());
        f.send(1, true);
        assert(f.cancelled.size() == 1 && f.replies.back().state == CalendarJoinState::cancelled);
        f.finish(CalendarJoinState::opening); assert(f.replies.size() == 3);
        f.send(3); assert(f.accepted.size() == 2);
        f.send(1, true); assert(f.cancelled.size() == 1); // Late cancel never affects 3.
        f.host.replyCalendarJoin(f.accepted.front(), {CalendarJoinState::failed, CalendarJoinReason::stale});
        assert(f.replies.size() == 4);
    }
    {
        F f;
        for (unsigned n = 0; n < 1024; ++n) { f.send(n); f.finish(CalendarJoinState::cancelled, CalendarJoinReason::notReady); }
        assert(f.history() == 1024);
        const auto total = f.replies.size();
        f.send(0); assert(f.replies.size() == total); // replay before cap
        f.send(1024); f.send(1024);
        assert(f.accepted.size() == 1024 && f.history() == 1024 && f.replies.size() == total + 2);
        assert(f.replies.back().state == CalendarJoinState::cancelled && f.replies.back().reason == CalendarJoinReason::notReady);
    }
    for (unsigned failure = 0; failure < 8; ++failure) {
        F f; auto message = f.message(1);
        auto source = f.host.currentUrl();
        switch (failure) {
        case 0: message.nonce = "stale"; break;
        case 1: message.origin = "https://example.org"; break;
        case 2: source += "#frame"; break;
        case 3: message.direction = BridgeDirection::nativeToWeb; break;
        case 4: message.version = 2; break;
        case 5: message.messageId = 0; break;
        case 6: message.payloadJson = "{}"; break;
        case 7: message.payloadJson.insert(1, "\"action\":\"joinCalendarEvent\","); break;
        }
        f.receive(message, source);
        assert(f.accepted.empty() && f.replies.empty() && f.history() == 0);
    }
    for (const auto route : {"/settings", "/billing", "/login", "/meetings/abcdefab-1234-4567-89ab-abcdefabcdef", "/review"}) {
        F f;
        f.route(route);
        f.send(1); assert(f.accepted.empty() && f.replies.empty());
    }
    for (unsigned invalidation = 0; invalidation < 5; ++invalidation) {
        F f; f.send(1);
        switch (invalidation) {
        case 0: (void)f.host.beginDocumentNavigation("https://rec.2brain.pro/desktop/meetings", 2, false, 10); break;
        case 1: f.host.close(); break;
        case 2: f.host.handleProcessFailure(WebProcessFailure::renderExited, 0); break;
        case 3: f.host.setRuntimeState(WebRuntimeState::authRequired); break;
        case 4: f.host.setCalendarJoinHandlers({}, {}); break;
        }
        assert(f.cancelled.size() == 1 && f.replies.size() == 2 && f.nonces.back() == "nonce-1");
        f.host.replyCalendarJoin(f.accepted[0], {CalendarJoinState::opening, CalendarJoinReason::none});
        assert(f.replies.size() == 2);
    }
    {
        F f; f.send(1);
        const auto old = f.accepted[0];
        f.host.setRuntimeState(WebRuntimeState::initializing);
        f.document("nonce-2");
        assert(f.history() == 0);
        f.send(1);
        f.host.replyCalendarJoin(old, {CalendarJoinState::opening, CalendarJoinReason::none});
        assert(f.replies.size() == 3 && f.nonces.back() == "nonce-2");
    }
    {
        F f; bool reentered = false;
        f.onReply = [&](auto result) {
            if (result.state == CalendarJoinState::resolving && !reentered) {
                reentered = true;
                f.send(1, true);
                f.send(2);
            }
        };
        f.send(1);
        assert(f.accepted.size() == 1 && f.accepted[0].intent.requestId == "00000002-abcd-abcd-abcd-000000000000");
        assert(f.cancelled.size() == 1);
    }
    {
        F f;
        f.host.setCalendarJoinHandlers([](auto) { throw std::runtime_error("synthetic"); },
            [&](auto request) { f.cancelled.push_back(std::move(request)); });
        f.send(1);
        assert(f.cancelled.size() == 1 && f.replies.size() == 2 && f.replies.back().state == CalendarJoinState::cancelled);
        f.send(1); assert(f.replies.size() == 2);
    }
    {
        F f;
        f.onReply = [](auto) { throw std::runtime_error("synthetic delivery failure"); };
        f.send(1);
        assert(f.accepted.empty() && f.cancelled.size() == 1);
        f.onReply = {};
        f.send(2); assert(f.accepted.size() == 1);
    }
    for (const bool delivery : {false, true}) {
        F f; bool reentered = false;
        if (delivery) {
            f.onReply = [&](auto result) {
                if (result.state != CalendarJoinState::resolving || reentered) return;
                reentered = true;
                f.send(1, true);
                f.send(2);
                throw std::runtime_error("old delivery");
            };
        } else {
            f.host.setCalendarJoinHandlers([&](auto request) {
                f.accepted.push_back(request);
                if (reentered) return;
                reentered = true;
                f.host.replyCalendarJoin(request, {CalendarJoinState::failed, CalendarJoinReason::launchFailed});
                f.send(2);
                throw std::runtime_error("old dispatch");
            }, [&](auto request) { f.cancelled.push_back(std::move(request)); });
        }
        f.send(1);
        assert(f.cancelled.size() == (delivery ? 1U : 0U));
        assert(f.accepted.back().intent.requestId == "00000002-abcd-abcd-abcd-000000000000");
        const auto before = f.replies.size();
        f.finish(CalendarJoinState::opening);
        f.finish(CalendarJoinState::handedOff);
        assert(f.replies.size() == before + 2 && f.replies.back().state == CalendarJoinState::handedOff);
    }
}
