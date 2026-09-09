from html.parser import HTMLParser
from uuid import UUID

import pytest

from tests.fixtures.calendar_visual_ui_harness import _theme_review
from twobrain_rec_server.api.schemas import ArtifactEgressState, ContentExportCapabilityResponse
from twobrain_rec_server.cabinet.rendering import render_meeting_detail_page


class Elements(HTMLParser):
    """Keep ancestry so private controls and accessible roles can be checked."""

    def __init__(self, html):
        super().__init__()
        self.stack = []
        self.nodes = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = (tag, dict(attrs), tuple(self.stack))
        self.nodes.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def with_attr(self, name):
        return [node for node in self.nodes if name in node[1]]


def reference_review():
    review = _theme_review()
    review.meeting.title_version = "1"
    review.content_exports = ContentExportCapabilityResponse(
        transcript={"state": "available"},
        summary={"state": "partial"},
        combined={"state": "missing"},
        formats={"transcript": ["txt", "srt"], "summary": ["txt"], "combined": []},
        duration_seconds=40,
    )
    return review


@pytest.mark.parametrize("embedded", [False, True])
def test_detail_controls_stay_inside_private_main_and_outside_tab_roles(embedded):
    html = render_meeting_detail_page(reference_review(), embedded=embedded)
    dom = Elements(html)
    for name in ("data-meeting-title-form", "data-summary-format-controls", "data-detail-copy", "data-content-export-form"):
        nodes = dom.with_attr(name)
        assert len(nodes) == 1
        assert any(parent[1].get("id") == "cabinet-main" for parent in nodes[0][2])
    controls = dom.with_attr("data-summary-format-controls")[0]
    assert any("data-meeting-detail-header" in parent[1] for parent in controls[2])
    assert not any(parent[1].get("role") in {"tab", "tablist", "tabpanel"} for parent in controls[2])
    tabs = dom.with_attr("data-detail-tab")
    assert {node[1]["aria-controls"] for node in tabs} == {"detail-panel-outcomes", "detail-panel-recording"}
    assert all(any(parent[1].get("role") == "tablist" for parent in node[2]) for node in tabs)
    assert "hidden" in dom.with_attr("data-detail-copy")[0][1]  # No inert no-JS copy button.
    assert "data-playback-transcript" in html
    assert 'value="combined"  disabled' in html
    back = dom.with_attr("data-source-return")[0]
    assert any(parent[1].get("data-detail-panel") == "recording" for parent in back[2])


def test_unavailable_transcript_does_not_create_format_or_copy_capabilities():
    review = reference_review()
    review.transcript.available = False
    review.content_exports = None
    dom = Elements(render_meeting_detail_page(review))
    assert not dom.with_attr("data-summary-format-controls")
    assert not dom.with_attr("data-detail-copy")
    assert dom.with_attr("data-detail-panel")


def test_replacement_retains_one_boundary_for_header_document_and_player():
    review = reference_review()
    review.processing.attempt_ordinal = 2
    review.processing.state = "processing"
    dom = Elements(render_meeting_detail_page(review))
    main = dom.with_attr("data-processing-replacement-active")[0]
    assert main[1]["data-processing-replacement-active"] == "true"
    assert any("data-meeting-detail-navigation" in node[1] for node in dom.nodes)
    for node in dom.with_attr("data-detail-panel") + dom.with_attr("data-processing-recovery"):
        assert main in node[2]


@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize("available", [False, True])
@pytest.mark.parametrize("replacement", [False, True])
def test_no_js_downloads_only_expose_permitted_current_artifacts(shared, available, replacement):
    review = reference_review()
    review.artifacts = [ArtifactEgressState(
        artifact_class="transcript", state="available", label="Расшифровка",
        action="download" if available else "disabled",
    )]
    if replacement:
        review.processing.attempt_ordinal = 2
        review.processing.state = "processing"
    workspace_id = UUID(int=257) if shared else None
    dom = Elements(render_meeting_detail_page(review, shared_workspace_id=workspace_id))
    links = [node for node in dom.with_attr("href") if "/downloads/" in node[1]["href"]
             and any(parent[0] == "noscript" for parent in node[2])]
    # Shared readers keep the server-authorized published artifact; only the
    # owner surface runs the processing replacement state machine.
    assert len(links) == (1 if available and (shared or not replacement) else 0)
    if links:
        href = links[0][1]["href"]
        assert href.endswith(f"/downloads/transcript?workspace_id={workspace_id}" if shared else "/downloads/transcript")
        assert ("/shared-meetings/" in href) == shared
