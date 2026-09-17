#include "RecordingDeletionBridge.h"

#include <algorithm>
#include <set>
#include <utility>

namespace graf::windows {
namespace {

// The bridge lives in the page, so its text is part of the contract with the
// cabinet. It hands the selection to the desktop bridge script as an event, which
// that script turns into a validated envelope: this script never needs the nonce,
// and a page that dispatches the event itself has gained nothing, because posting
// the envelope directly was always possible.
//
// The shim is named `webkit` because that is what the cabinet checks
// (`cabinet.js:1516-1522`). On macOS that object is provided by WebKit; here it is
// provided by this script, and it carries the one message shape the deletion flow
// uses. Row actions do not travel through it: on this platform the desktop bridge
// script already reports them as their own command.
constexpr std::string_view kDocumentScript = R"JS(
(() => {
  if (window.__grafDeletionBridgeBound) return;
  window.__grafDeletionBridgeBound = true;
  const existing = window.webkit && window.webkit.messageHandlers
    ? window.webkit.messageHandlers.grafLocalRecording
    : undefined;
  // A real WebKit handler wins, and the version stays unset: the page then knows
  // the deletion bridge is not available here instead of calling into nothing.
  if (existing) return;
  window.GRAFRecordingDeletionBridgeVersion = 1;
  window.webkit = window.webkit || {};
  window.webkit.messageHandlers = window.webkit.messageHandlers || {};
  window.webkit.messageHandlers.grafLocalRecording = {
    postMessage: (body) => {
      if (!body || typeof body !== 'object') return;
      if (body.action !== 'deleteSelection' || body.version !== 1) return;
      const ids = (value) => Array.isArray(value)
        ? value.filter((item) => typeof item === 'string')
        : null;
      const localIds = ids(body.localIds);
      const meetingIds = ids(body.meetingIds);
      if (!localIds || !meetingIds || typeof body.requestId !== 'string') return;
      window.dispatchEvent(new CustomEvent('graf:delete-selection', {
        detail: {
          action: body.action,
          version: body.version,
          requestId: body.requestId,
          localIds: localIds,
          meetingIds: meetingIds
        }
      }));
    }
  };
})();
)JS";

[[nodiscard]] bool isUuid(std::string_view value) {
    return DesktopApiClient::accountId(value);
}

[[nodiscard]] bool uniqueAndValid(const std::vector<std::string>& values) {
    std::set<std::string_view> seen;
    for (const auto& value : values) {
        if (!seen.insert(value).second) return false;
    }
    return true;
}

[[nodiscard]] std::string number(std::size_t value) { return std::to_string(value); }

} // namespace

std::optional<CabinetDeletionSelection> RecordingDeletionBridge::validate(
    const CabinetDeletionInput& input, const std::vector<CabinetLocalRow>& rows) {
    if (input.version != kBridgeVersion || input.action != kDeleteSelectionAction) return std::nullopt;
    if (!isUuid(input.requestId)) return std::nullopt;
    const auto total = input.localIds.size() + input.meetingIds.size();
    if (total == 0 || total > kSelectionLimit) return std::nullopt;
    if (!uniqueAndValid(input.localIds) || !uniqueAndValid(input.meetingIds)) return std::nullopt;
    for (const auto& meetingId : input.meetingIds) {
        if (!isUuid(meetingId)) return std::nullopt;
    }
    // A local id the app does not offer for deletion is not a deletion this app
    // may perform, whatever the page claims.
    for (const auto& localId : input.localIds) {
        const auto known = std::any_of(rows.begin(), rows.end(), [&localId](const auto& row) {
            return row.id == localId && row.canDelete;
        });
        if (!known) return std::nullopt;
    }
    CabinetDeletionSelection selection;
    selection.requestId = input.requestId;
    selection.localIds = input.localIds;
    selection.meetingIds = input.meetingIds;
    return selection;
}

bool RecordingDeletionBridge::fitsRoute(const CabinetDeletionSelection& selection,
                                       std::string_view routeMeetingId) {
    if (routeMeetingId.empty()) return true; // The meeting list owns every row it shows.
    if (selection.localIds.empty() && selection.meetingIds.size() == 1 &&
        selection.meetingIds.front() == routeMeetingId) return true;
    // A local-only selection is the same recording shown alone on its page.
    return selection.meetingIds.empty();
}

std::vector<CabinetDeletionTarget> RecordingDeletionBridge::targets(
    const CabinetDeletionSelection& selection, const std::vector<CabinetLocalRow>& rows) {
    std::vector<CabinetDeletionTarget> result;
    result.reserve(selection.total());
    for (const auto& localId : selection.localIds) {
        const auto row = std::find_if(rows.begin(), rows.end(), [&localId](const auto& candidate) {
            return candidate.id == localId && candidate.canDelete;
        });
        if (row == rows.end()) continue;
        // The request names the identifier the server knows for this local copy,
        // which is the directory the package was written to, not the row id the
        // page saw.
        result.push_back({DeletionTarget::ownOrigin, row->originId});
    }
    for (const auto& meetingId : selection.meetingIds) {
        result.push_back({DeletionTarget::meeting, meetingId});
    }
    return result;
}

std::string RecordingDeletionBridge::completionScript(std::string_view requestId,
                                                     const CabinetDeletionOutcome& outcome) {
    if (!isUuid(requestId)) return {};
    std::string result = "{\"saved\":";
    result += outcome.saved ? "true" : "false";
    if (outcome.unknown) {
        // The cabinet distinguishes "no answer yet" from "could not store":
        // one asks the user to check the deletion list, the other to try again.
        result += ",\"unknown\":true}";
    } else {
        result += ",\"accepted\":" + number(outcome.accepted);
        result += ",\"pending\":" + number(outcome.pending);
        result += ",\"rejected\":" + number(outcome.rejected) + "}";
    }
    return "window.GRAFLocalRecordings?.deletionCompleted('" + std::string(requestId) + "', " + result + ")";
}

std::string_view RecordingDeletionBridge::documentScript() noexcept {
    return kDocumentScript;
}

std::string pageDeletionWaitReason(std::string_view ledgerReason) {
    // The page prints these five reasons itself; anything else it does not know,
    // and an unknown value must not become a state the user was never told about.
    if (ledgerReason == "rate_limit") return "rateLimit";
    if (ledgerReason == "server_update") return "serverUpdate";
    return std::string(ledgerReason);
}

} // namespace graf::windows
