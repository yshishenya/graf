// The cabinet bridge that asks this app to delete what the user selected.
//
// macOS parses the same message in `EmbeddedCabinetDeletionSelection.parse`
// (apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift:1066-1078) and
// gates it by route before acting. These cases are the ones that decide whether a
// page can delete something the user did not select, or name a target the server
// does not know.

#include "../../RecApp/Web/RecordingDeletionBridge.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
#include <string>
#include <vector>

namespace {

using namespace graf::windows;

constexpr std::string_view kRow = "0BADCA32-921E-4284-B63C-BFBFB837B7C7";
constexpr std::string_view kOtherRow = "C21D2D2A-CBCA-48B6-A60D-C142A5CEBE32";
constexpr std::string_view kOrigin = "D4C613C4-C35B-4208-8549-23307BA3FC39";
constexpr std::string_view kMeeting = "33333333-3333-4333-8333-333333333333";
constexpr std::string_view kOtherMeeting = "55555555-5555-4555-8555-555555555555";
constexpr std::string_view kRequest = "44444444-4444-4444-8444-444444444444";

std::vector<CabinetLocalRow> rows() {
    return {{std::string(kRow), std::string(kOrigin), true},
            {std::string(kOtherRow), std::string(kOtherRow), true},
            // Known, but this row offers no deletion: the cabinet never shows the
            // button, so a request naming it did not come from the user.
            {"3EBBD476-2D97-40D8-9612-F26105C90069", "3EBBD476-2D97-40D8-9612-F26105C90069", false}};
}

CabinetDeletionInput selection(std::vector<std::string> localIds, std::vector<std::string> meetingIds) {
    CabinetDeletionInput input;
    input.version = 1;
    input.action = "deleteSelection";
    input.requestId = std::string(kRequest);
    input.localIds = std::move(localIds);
    input.meetingIds = std::move(meetingIds);
    return input;
}

void testAcceptsWhatTheCabinetSends() {
    const auto parsed = RecordingDeletionBridge::validate(selection({std::string(kRow)}, {std::string(kMeeting)}), rows());
    assert(parsed && parsed->requestId == kRequest);
    assert(parsed->localIds.size() == 1 && parsed->meetingIds.size() == 1);
    assert(parsed->total() == 2);
    // Local copies alone and meetings alone are both ordinary selections.
    assert(RecordingDeletionBridge::validate(selection({std::string(kRow)}, {}), rows()));
    assert(RecordingDeletionBridge::validate(selection({}, {std::string(kMeeting)}), rows()));
}

void testRefusesEverythingElse() {
    const auto refuses = [](CabinetDeletionInput input) {
        assert(!RecordingDeletionBridge::validate(input, rows()));
    };
    // An empty selection is not a deletion: the cabinet never sends one.
    refuses(selection({}, {}));
    // Only version 1 of this one action.
    auto wrongVersion = selection({std::string(kRow)}, {});
    wrongVersion.version = 2;
    refuses(wrongVersion);
    wrongVersion.version = 0;
    refuses(wrongVersion);
    auto wrongAction = selection({std::string(kRow)}, {});
    wrongAction.action = "delete";
    refuses(wrongAction);
    // The request id comes back inside a script, so it has to be an identifier and
    // nothing else.
    for (const auto& requestId : {std::string(""), std::string("not-a-uuid"),
                                  std::string("'); window.alert(1); //"),
                                  std::string("44444444-4444-4444-8444-44444444444Z")}) {
        auto badRequest = selection({std::string(kRow)}, {});
        badRequest.requestId = requestId;
        refuses(badRequest);
    }
    // A repeated identifier would count one deletion twice.
    refuses(selection({std::string(kRow), std::string(kRow)}, {}));
    refuses(selection({}, {std::string(kMeeting), std::string(kMeeting)}));
    // Meetings are server identifiers.
    refuses(selection({}, {std::string("not-a-meeting")}));
    // A local row the app does not know, or does not offer for deletion.
    refuses(selection({std::string("12345678-1234-4123-8123-123456789012")}, {}));
    refuses(selection({"3EBBD476-2D97-40D8-9612-F26105C90069"}, {}));
    // One bad identifier refuses the whole selection: acting on the rest would
    // delete something other than what the user selected.
    refuses(selection({std::string(kRow), "not-a-row"}, {}));
    refuses(selection({std::string(kRow)}, {std::string(kMeeting), "not-a-meeting"}));
    // The cabinet caps a selection at one hundred, and so does the app.
    std::vector<std::string> oversized;
    for (int index = 0; index <= static_cast<int>(RecordingDeletionBridge::kSelectionLimit); ++index) {
        char buffer[40] = {};
        std::snprintf(buffer, sizeof(buffer), "33333333-3333-4333-8333-%012d", index);
        oversized.push_back(buffer);
    }
    refuses(selection({}, oversized));
    oversized.pop_back();
    // Exactly one hundred distinct targets is the last selection that is accepted.
    assert(RecordingDeletionBridge::validate(selection({}, oversized), rows()));
    assert(oversized.size() == RecordingDeletionBridge::kSelectionLimit);
}

void testRouteGate() {
    const auto localOnly = *RecordingDeletionBridge::validate(selection({std::string(kRow)}, {}), rows());
    const auto thisMeeting = *RecordingDeletionBridge::validate(selection({}, {std::string(kMeeting)}), rows());
    const auto otherMeeting = *RecordingDeletionBridge::validate(selection({}, {std::string(kOtherMeeting)}), rows());
    const auto both = *RecordingDeletionBridge::validate(
        selection({std::string(kRow)}, {std::string(kMeeting)}), rows());
    // The meeting list owns every row it shows.
    assert(RecordingDeletionBridge::fitsRoute(localOnly, ""));
    assert(RecordingDeletionBridge::fitsRoute(thisMeeting, ""));
    assert(RecordingDeletionBridge::fitsRoute(otherMeeting, ""));
    // A meeting page may delete that meeting, or the local copy shown on it.
    assert(RecordingDeletionBridge::fitsRoute(thisMeeting, kMeeting));
    assert(RecordingDeletionBridge::fitsRoute(localOnly, kMeeting));
    assert(!RecordingDeletionBridge::fitsRoute(otherMeeting, kMeeting));
    assert(!RecordingDeletionBridge::fitsRoute(both, kMeeting));
}

void testTargetsNameWhatTheServerKnows() {
    const auto parsed = *RecordingDeletionBridge::validate(
        selection({std::string(kRow)}, {std::string(kMeeting)}), rows());
    const auto planned = RecordingDeletionBridge::targets(parsed, rows());
    assert(planned.size() == 2);
    // The local request names the directory the server knows, not the row id the
    // page displayed.
    assert(planned[0].target == DeletionTarget::ownOrigin && planned[0].targetId == kOrigin);
    assert(planned[1].target == DeletionTarget::meeting && planned[1].targetId == kMeeting);
    // Order follows the cabinet: local copies first, then meetings.
    assert(planned[0].targetId != kRow);
    // A row with no separate origin identifier still requests its own id.
    const auto other = *RecordingDeletionBridge::validate(selection({std::string(kOtherRow)}, {}), rows());
    const auto otherPlan = RecordingDeletionBridge::targets(other, rows());
    assert(otherPlan.size() == 1 && otherPlan[0].targetId == kOtherRow);
}

void testCompletionScript() {
    CabinetDeletionOutcome outcome;
    outcome.saved = true;
    outcome.accepted = 2;
    outcome.pending = 1;
    outcome.rejected = 0;
    const auto script = RecordingDeletionBridge::completionScript(kRequest, outcome);
    assert(script == "window.GRAFLocalRecordings?.deletionCompleted('" + std::string(kRequest) +
        "', {\"saved\":true,\"accepted\":2,\"pending\":1,\"rejected\":0})");
    // The page decides between "check the deletion list" and "try again" from
    // these two shapes, so they must not be mixed up.
    CabinetDeletionOutcome unknown;
    unknown.unknown = true;
    const auto unanswered = RecordingDeletionBridge::completionScript(kRequest, unknown);
    assert(unanswered.find("\"saved\":false") != std::string::npos);
    assert(unanswered.find("\"unknown\":true") != std::string::npos);
    assert(unanswered.find("accepted") == std::string::npos);
    CabinetDeletionOutcome notSaved;
    notSaved.saved = false;
    const auto retry = RecordingDeletionBridge::completionScript(kRequest, notSaved);
    assert(retry.find("\"saved\":false") != std::string::npos);
    assert(retry.find("unknown") == std::string::npos);
    assert(retry.find("\"accepted\":0,\"pending\":0,\"rejected\":0") != std::string::npos);
    // A request id that is not an identifier never reaches the page.
    assert(RecordingDeletionBridge::completionScript("'); alert(1); //", outcome).empty());
    assert(RecordingDeletionBridge::completionScript("", outcome).empty());
}

void testDocumentScriptExposesOnlyTheDeletionBridge() {
    const std::string script(RecordingDeletionBridge::documentScript());
    // The version and the handler name are the gate the cabinet checks.
    assert(script.find("GRAFRecordingDeletionBridgeVersion = 1") != std::string::npos);
    assert(script.find("messageHandlers.grafLocalRecording") != std::string::npos);
    assert(script.find("'deleteSelection'") != std::string::npos);
    // It installs once, and never replaces a handler that is already there.
    assert(script.find("__grafDeletionBridgeBound") != std::string::npos);
    assert(script.find("if (existing) return") != std::string::npos);
    // The selection reaches the native side as an event, so this script never
    // needs the bridge nonce.
    assert(script.find("CustomEvent('graf:delete-selection'") != std::string::npos);
    assert(script.find("nonce") == std::string::npos);
    // A shape this bridge does not own is dropped rather than forwarded.
    assert(script.find("if (!localIds || !meetingIds") != std::string::npos);
    assert(script.find("typeof item === 'string'") != std::string::npos);
}

} // namespace

int main() {
    testAcceptsWhatTheCabinetSends();
    testRefusesEverythingElse();
    testRouteGate();
    testTargetsNameWhatTheServerKnows();
    testCompletionScript();
    testDocumentScriptExposesOnlyTheDeletionBridge();
    return 0;
}
