const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { chromium } = require("playwright");

const repoRoot = process.cwd();
const serverDir = path.join(repoRoot, "apps/server");
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "rec-048-runtime-"));
const modulePath = path.join(tmpDir, "runtime_app.py");
const infoPath = path.join(tmpDir, "runtime-info.json");
const port = 19248;
const baseUrl = `http://127.0.0.1:${port}`;
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const screenshotDir = process.env.REC_RUNTIME_SCREENSHOT_DIR || null;
const authHeaders = {
  "X-Organization-Id": "10000000-0000-0000-0000-000000000001",
  "X-Workspace-Id": "20000000-0000-0000-0000-000000000001",
  "X-User-Id": "30000000-0000-0000-0000-000000000001",
  "X-Device-Id": "40000000-0000-0000-0000-000000000001",
};

fs.writeFileSync(modulePath, String.raw`
import asyncio
import io
import json
import os
import wave
from pathlib import Path
from hashlib import sha256

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, REVOKED_DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_minio import FakeMinioStorage
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.base import Base
from twobrain_rec_server.db.models import (
    Organization,
    RegisteredDevice,
    TrackArtifact,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.domain.statuses import TrackRole
from twobrain_rec_server.main import create_app


settings = Settings(
    database_url=f"sqlite+aiosqlite:///{os.environ['REC_RUNTIME_DB']}",
    minio_endpoint="localhost:9000",
    minio_access_key="test",
    minio_secret_key="test",
    minio_bucket="test-bucket",
    web_login_workspace_id=WORKSPACE_ID,
)
engine = create_async_engine(settings.database_url)
sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


async def seed_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessionmaker() as session:
        session.add_all(
            [
                Organization(id=ORG_ID, slug="test-org", name="Test Org"),
                Workspace(id=WORKSPACE_ID, organization_id=ORG_ID, slug="test-workspace", name="Test Workspace"),
                UserIdentity(id=USER_ID, organization_id=ORG_ID, external_subject=str(USER_ID), display_name="Test User"),
                WorkspaceMembership(workspace_id=WORKSPACE_ID, user_id=USER_ID, role="owner", status="active"),
                RegisteredDevice(
                    id=DEVICE_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    device_public_id="test-device",
                    status="active",
                ),
                RegisteredDevice(
                    id=REVOKED_DEVICE_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    device_public_id="revoked-device",
                    status="revoked",
                ),
            ]
        )
        await session.commit()


asyncio.run(seed_database())
app = create_app(settings)
app.state.db_engine = engine
app.state.db_sessionmaker = sessionmaker
app.state.storage = FakeMinioStorage()

client = TestClient(app)
client.app_state["engine"] = engine
client.app_state["sessionmaker"] = sessionmaker
client.app_state["storage"] = app.state.storage
seeds = seed_cabinet_meetings(client)


def wav_bytes(*, seconds: int, amplitude: int, sample_rate: int = 16000) -> bytes:
    frames = bytearray()
    for index in range(seconds * sample_rate):
        sample = amplitude if (index // 800) % 2 == 0 else -amplitude
        frames.extend(sample.to_bytes(2, "little", signed=True))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames))
    return buffer.getvalue()


async def replace_retained_audio_with_long_wav() -> None:
    by_role = {
        TrackRole.MICROPHONE.value: wav_bytes(seconds=40, amplitude=1000),
        TrackRole.SYSTEM.value: wav_bytes(seconds=40, amplitude=1500),
    }
    object_key_attr = "storage_" + "object_key"
    async with sessionmaker() as db:
        artifacts = (
            await db.scalars(
                select(TrackArtifact)
                .where(TrackArtifact.workspace_id == WORKSPACE_ID, TrackArtifact.meeting_id == seeds.ready_id)
                .order_by(TrackArtifact.track_role.asc())
            )
        ).all()
        for artifact in artifacts:
            data = by_role.get(artifact.track_role)
            if data is None:
                continue
            app.state.storage.put_bytes(getattr(artifact, object_key_attr), data)
            artifact.codec = "pcm_s16le"
            artifact.sample_rate_hz = 16000
            artifact.channel_count = 1
            artifact.duration_seconds = 40
            artifact.byte_length = len(data)
            artifact.sha256 = sha256(data).hexdigest()
        await db.commit()


asyncio.run(replace_retained_audio_with_long_wav())
Path(os.environ["REC_RUNTIME_INFO"]).write_text(
    json.dumps({"ready_id": str(seeds.ready_id)}, ensure_ascii=False)
)
`);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForRuntime(proc) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (proc.exitCode !== null) throw new Error(`uvicorn exited early with ${proc.exitCode}`);
    if (fs.existsSync(infoPath)) {
      try {
        const health = await fetch(`${baseUrl}/api/v1/health/live`);
        if (health.status === 200) return JSON.parse(fs.readFileSync(infoPath, "utf8"));
      } catch (_error) {
        // Keep polling until uvicorn accepts connections.
      }
    }
    await sleep(250);
  }
  throw new Error("runtime server did not become ready");
}

async function pageMetrics(browser, label, url, viewport) {
  const page = await browser.newPage({ viewport, extraHTTPHeaders: authHeaders });
  await page.goto(url, { waitUntil: "domcontentloaded" });
  const metrics = await page.evaluate(async () => {
    const audio = document.querySelector("[data-playback-player]");
    if (audio) {
      audio.play = () => {
        audio.dispatchEvent(new Event("play"));
        return Promise.resolve();
      };
    }
    const seekButton = document.querySelectorAll("[data-seek-seconds]")[1];
    if (seekButton) seekButton.click();
    await new Promise((resolve) => setTimeout(resolve, 20));
    const bar = document.querySelector("[data-playback-shell]");
    const transcript = document.querySelector(".transcript");
    return {
      audioCount: document.querySelectorAll("[data-playback-player]").length,
      barCount: document.querySelectorAll("[data-playback-shell]").length,
      seekTargets: document.querySelectorAll("[data-seek-seconds]").length,
      transcriptSeekTargets: document.querySelectorAll(".transcript [data-seek-seconds]").length,
      transcriptTextLength: transcript ? transcript.innerText.length : 0,
      seekCurrentTime: audio ? audio.currentTime : null,
      sourceMode: bar ? bar.getAttribute("data-source-mode") : null,
      timelineSegments: document.querySelectorAll("[data-lane-segment]").length,
      audioDownloadLinks: Array.from(document.querySelectorAll("a[href*='/downloads/audio']")).length,
      horizontalOverflow: Math.max(
        0,
        document.documentElement.scrollWidth - document.documentElement.clientWidth,
        document.body.scrollWidth - document.body.clientWidth,
      ),
      barBottom: bar ? Math.round(window.innerHeight - bar.getBoundingClientRect().bottom) : null,
    };
  });
  if (screenshotDir) {
    fs.mkdirSync(screenshotDir, { recursive: true });
    await page.screenshot({ path: path.join(screenshotDir, `${label}.png`), fullPage: false });
  }
  await page.close();
  return metrics;
}

async function main() {
  const env = {
    ...process.env,
    PYTHONPATH: `src:.:${tmpDir}`,
    REC_RUNTIME_DB: path.join(tmpDir, "runtime.sqlite3"),
    REC_RUNTIME_INFO: infoPath,
  };
  const server = spawn(
    "uv",
    ["run", "--extra", "dev", "uvicorn", "runtime_app:app", "--host", "127.0.0.1", "--port", String(port), "--log-level", "warning"],
    { cwd: serverDir, env, stdio: ["ignore", "pipe", "pipe"] },
  );
  let stdout = "";
  let stderr = "";
  server.stdout.on("data", (chunk) => {
    stdout += chunk.toString();
    if (stdout.length > 20000) stdout = stdout.slice(-20000);
  });
  server.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
    if (stderr.length > 20000) stderr = stderr.slice(-20000);
  });

  try {
    const info = await waitForRuntime(server);
    const readyId = info.ready_id;
    const rangeResponse = await fetch(`${baseUrl}/api/v1/cabinet/meetings/${readyId}/playback`, {
      headers: { ...authHeaders, Range: "bytes=0-15" },
    });
    const rangeBody = Buffer.from(await rangeResponse.arrayBuffer());
    const browser = await chromium.launch({ headless: true, executablePath: chromePath });
    const webDesktop = await pageMetrics(browser, "web-desktop", `${baseUrl}/meetings/${readyId}`, {
      width: 1440,
      height: 900,
    });
    const webMobile = await pageMetrics(browser, "web-mobile", `${baseUrl}/meetings/${readyId}`, {
      width: 390,
      height: 844,
    });
    const embeddedDesktop = await pageMetrics(browser, "embedded-desktop", `${baseUrl}/desktop/meetings/${readyId}`, {
      width: 1200,
      height: 820,
    });
    await browser.close();

    const results = {
      readyId,
      range: {
        status: rangeResponse.status,
        acceptRanges: rangeResponse.headers.get("accept-ranges"),
        contentRange: rangeResponse.headers.get("content-range"),
        contentLength: rangeResponse.headers.get("content-length"),
        forbiddenMarkerPresent: [
          "storage_" + "object_key",
          "X-" + "Amz",
          "private-" + "run-id",
          "raw_" + "audio",
        ].some((marker) =>
          Buffer.concat([rangeBody, Buffer.from(JSON.stringify(Object.fromEntries(rangeResponse.headers)))]).toString(
            "utf8",
          ).includes(marker),
        ),
      },
      webDesktop,
      webMobile,
      embeddedDesktop,
    };
    const failures = [];
    for (const [label, metrics] of Object.entries({ webDesktop, webMobile, embeddedDesktop })) {
      if (metrics.audioCount !== 1) failures.push(`${label}: expected one audio`);
      if (metrics.barCount !== 1) failures.push(`${label}: expected one bottom player`);
      if (metrics.seekTargets < 2) failures.push(`${label}: expected seek targets`);
      if (Math.abs(metrics.seekCurrentTime - 12.5) > 0.2) failures.push(`${label}: seekCurrentTime=${metrics.seekCurrentTime}`);
      if (metrics.sourceMode !== "combined_review_stream") failures.push(`${label}: sourceMode=${metrics.sourceMode}`);
      if (metrics.timelineSegments < 2) failures.push(`${label}: expected speaker timeline segments`);
      if (metrics.audioDownloadLinks !== 0) failures.push(`${label}: audio download link visible`);
      if (metrics.horizontalOverflow > 1) failures.push(`${label}: horizontalOverflow=${metrics.horizontalOverflow}`);
      if (metrics.barBottom !== 0) failures.push(`${label}: barBottom=${metrics.barBottom}`);
      if (metrics.transcriptSeekTargets < 2) failures.push(`${label}: transcript seek targets missing`);
      if (metrics.transcriptTextLength < 20) failures.push(`${label}: transcript content missing`);
    }
    if (results.range.status !== 206) failures.push(`range: status=${results.range.status}`);
    if (results.range.acceptRanges !== "bytes") failures.push(`range: accept-ranges=${results.range.acceptRanges}`);
    if (!String(results.range.contentRange || "").startsWith("bytes 0-15/")) failures.push(`range: content-range=${results.range.contentRange}`);
    if (results.range.contentLength !== "16") failures.push(`range: content-length=${results.range.contentLength}`);
    if (results.range.forbiddenMarkerPresent) failures.push("range: forbidden marker present");

    console.log(JSON.stringify({ failures, results }, null, 2));
    process.exitCode = failures.length === 0 ? 0 : 1;
  } finally {
    server.kill("SIGTERM");
    await sleep(500);
    if (server.exitCode === null) server.kill("SIGKILL");
    if (process.exitCode && (stdout.trim() || stderr.trim())) {
      console.error([stdout.trim(), stderr.trim()].filter(Boolean).join("\n"));
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
