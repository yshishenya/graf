const { spawnSync } = require("node:child_process");
const { chromium } = require("playwright");

const repoRoot = process.cwd();
const serverDir = `${repoRoot}/apps/server`;
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const python = String.raw`
import json

from tests.unit.test_cabinet_web_shell import _review
from twobrain_rec_server.api.schemas import (
    PlaybackReviewState,
    SpeakerLane,
    SpeakerLaneSegment,
    SpeakerReviewState,
    TranscriptReviewState,
    TranscriptSegmentView,
)
from twobrain_rec_server.cabinet.web import render_meeting_detail_page


def ready_page(*, embedded: bool) -> str:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=120,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="combined_review_stream",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.transcript = TranscriptReviewState(
        available=True,
        language="ru",
        search_enabled=True,
        segments=[
            TranscriptSegmentView(
                segment_id="safe-runtime-1",
                sequence=0,
                start_seconds=0.0,
                end_seconds=8.0,
                timestamp_label="00:00",
                speaker_label="Speaker 1",
                source_role="local_microphone",
                text="Безопасный синтетический текст для проверки строки.",
                seekable=True,
                seek_seconds=0.0,
            ),
            TranscriptSegmentView(
                segment_id="safe-runtime-2",
                sequence=1,
                start_seconds=12.5,
                end_seconds=18.0,
                timestamp_label="00:12",
                speaker_label="Speaker 2",
                source_role="incoming_system",
                text="Еще один безопасный синтетический текст для проверки.",
                seekable=True,
                seek_seconds=12.5,
            ),
            TranscriptSegmentView(
                segment_id="safe-runtime-3",
                sequence=2,
                start_seconds=31.0,
                end_seconds=35.0,
                timestamp_label="00:31",
                speaker_label="Speaker 1",
                source_role="local_microphone",
                text="Третья безопасная строка нужна для проверки перехода.",
                seekable=True,
                seek_seconds=31.0,
            ),
        ],
    )
    review.speakers = SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        degraded_reason=None,
        speakers=[
            SpeakerLane(
                speaker_key="speaker-1",
                label="Speaker 1",
                talk_time_percent=45,
                source_roles=["local_microphone"],
                segments=[
                    SpeakerLaneSegment(start_seconds=0.0, end_seconds=8.0),
                    SpeakerLaneSegment(start_seconds=31.0, end_seconds=35.0),
                ],
            ),
            SpeakerLane(
                speaker_key="speaker-2",
                label="Speaker 2",
                talk_time_percent=55,
                source_roles=["incoming_system"],
                segments=[SpeakerLaneSegment(start_seconds=12.5, end_seconds=18.0)],
            ),
        ],
    )
    return render_meeting_detail_page(review, embedded=embedded)


def unavailable_page() -> str:
    review = _review()
    review.playback = PlaybackReviewState(
        available=False,
        duration_seconds=120,
        unavailable_reason="processing",
        playback_path=None,
        policy_label="Аудио еще готовится",
        source_mode="none",
        included_sources=[],
    )
    return render_meeting_detail_page(review)


print(json.dumps({
    "webReady": ready_page(embedded=False),
    "embeddedReady": ready_page(embedded=True),
    "unavailable": unavailable_page(),
}, ensure_ascii=False))
`;

function renderPages() {
  const result = spawnSync("uv", ["run", "--extra", "dev", "python", "-c", python], {
    cwd: serverDir,
    env: { ...process.env, PYTHONPATH: "src:." },
    encoding: "utf8",
  });
  if (result.status !== 0) {
    throw new Error(`renderer failed\nstdout=${result.stdout}\nstderr=${result.stderr}`);
  }
  return JSON.parse(result.stdout);
}

async function checkReadyPage(browser, label, html, viewport) {
  const page = await browser.newPage({ viewport });
  const failures = [];
  await page.setContent(html, { waitUntil: "domcontentloaded" });
  const metrics = await page.evaluate(async () => {
    const audio = document.querySelector("[data-playback-player]");
    if (audio) {
      audio.play = () => {
        audio.dispatchEvent(new Event("play"));
        return Promise.resolve();
      };
    }
    const seekButtons = Array.from(document.querySelectorAll("[data-seek-seconds]"));
    const thirdSeek = seekButtons[2];
    if (thirdSeek) thirdSeek.click();
    await new Promise((resolve) => setTimeout(resolve, 20));
    const bar = document.querySelector("[data-playback-shell]");
    const progress = document.querySelector("[data-playback-progress]");
    const overflow = Math.max(
      0,
      document.documentElement.scrollWidth - document.documentElement.clientWidth,
      document.body.scrollWidth - document.body.clientWidth,
    );
    return {
      audioCount: document.querySelectorAll("[data-playback-player]").length,
      barCount: document.querySelectorAll("[data-playback-shell]").length,
      seekTargets: seekButtons.length,
      seekCurrentTime: audio ? audio.currentTime : null,
      sourceMode: bar ? bar.getAttribute("data-source-mode") : null,
      timelineSegments: document.querySelectorAll("[data-lane-segment]").length,
      progressMax: progress ? progress.getAttribute("max") : null,
      horizontalOverflow: overflow,
      toggleText: document.querySelector("[data-playback-toggle]")?.textContent || "",
      barBottom: bar ? Math.round(window.innerHeight - bar.getBoundingClientRect().bottom) : null,
    };
  });
  if (metrics.audioCount !== 1) failures.push("expected one playback audio element");
  if (metrics.barCount !== 1) failures.push("expected one playback shell");
  if (metrics.seekTargets !== 3) failures.push(`expected 3 seek targets, got ${metrics.seekTargets}`);
  if (Math.abs(metrics.seekCurrentTime - 31.0) > 0.2) failures.push(`seekCurrentTime=${metrics.seekCurrentTime}`);
  if (metrics.sourceMode !== "combined_review_stream") failures.push(`sourceMode=${metrics.sourceMode}`);
  if (metrics.timelineSegments !== 3) failures.push(`timelineSegments=${metrics.timelineSegments}`);
  if (metrics.progressMax !== "120") failures.push(`progressMax=${metrics.progressMax}`);
  if (metrics.horizontalOverflow > 1) failures.push(`horizontalOverflow=${metrics.horizontalOverflow}`);
  if (metrics.toggleText !== "Pause") failures.push(`toggleText=${metrics.toggleText}`);
  if (metrics.barBottom !== 0) failures.push(`barBottom=${metrics.barBottom}`);
  await page.close();
  return { label, viewport, failures, metrics };
}

async function checkUnavailablePage(browser, label, html, viewport) {
  const page = await browser.newPage({ viewport });
  await page.setContent(html, { waitUntil: "domcontentloaded" });
  const metrics = await page.evaluate(() => ({
    audioCount: document.querySelectorAll("[data-playback-player]").length,
    unavailableCount: document.querySelectorAll(".detail-playback.is-unavailable").length,
    copy: document.querySelector(".detail-playback.is-unavailable")?.textContent || "",
    horizontalOverflow: Math.max(
      0,
      document.documentElement.scrollWidth - document.documentElement.clientWidth,
      document.body.scrollWidth - document.body.clientWidth,
    ),
  }));
  const failures = [];
  if (metrics.audioCount !== 0) failures.push("unavailable page must not render audio");
  if (metrics.unavailableCount !== 1) failures.push("expected unavailable playback bar");
  if (!metrics.copy.includes("Аудио еще готовится")) failures.push("missing unavailable copy");
  if (metrics.horizontalOverflow > 1) failures.push(`horizontalOverflow=${metrics.horizontalOverflow}`);
  await page.close();
  return { label, viewport, failures, metrics };
}

(async () => {
  const pages = renderPages();
  const browser = await chromium.launch({ headless: true, executablePath: chromePath });
  const results = [
    await checkReadyPage(browser, "web-ready-desktop", pages.webReady, { width: 1440, height: 900 }),
    await checkReadyPage(browser, "web-ready-mobile", pages.webReady, { width: 390, height: 844 }),
    await checkReadyPage(browser, "embedded-ready-desktop", pages.embeddedReady, { width: 1200, height: 820 }),
    await checkReadyPage(browser, "embedded-ready-mobile", pages.embeddedReady, { width: 390, height: 844 }),
    await checkUnavailablePage(browser, "unavailable-desktop", pages.unavailable, { width: 1440, height: 900 }),
    await checkUnavailablePage(browser, "unavailable-mobile", pages.unavailable, { width: 390, height: 844 }),
  ];
  await browser.close();
  const failures = results.flatMap((result) => result.failures.map((failure) => `${result.label}: ${failure}`));
  console.log(JSON.stringify({ failures, results }, null, 2));
  process.exit(failures.length === 0 ? 0 : 1);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
