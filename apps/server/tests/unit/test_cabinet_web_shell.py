from datetime import UTC, datetime, timedelta
from uuid import uuid4

from twobrain_rec_server.api.schemas import (
    ArtifactDeletionState,
    ArtifactEgressState,
    DeletionVerificationReport,
    GovernanceActionState,
    GovernanceActionSummary,
    LifecycleActivityItem,
    LocalPurgeTask,
    MeetingAccessState,
    MeetingActivityResponse,
    MeetingFilterState,
    MeetingListItem,
    MeetingListResponse,
    MeetingProvenance,
    MeetingReviewResponse,
    NotesActionCategoryState,
    NotesActionTruthState,
    NotesReviewState,
    OutcomeItemView,
    OutcomeSourceReferenceView,
    PlaybackReviewState,
    ProcessingReviewState,
    SharePanelState,
    SlotState,
    SpeakerLane,
    SpeakerLaneSegment,
    SpeakerReviewState,
    TranscriptReviewState,
    TranscriptSegmentView,
)
from twobrain_rec_server.cabinet.web import (
    render_deletion_report_page,
    render_meeting_detail_page,
    render_meeting_list_page,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
from twobrain_rec_server.domain.statuses import (
    DeletionArtifactState,
    DeletionControlScope,
    DeletionState,
    LocalPurgeTaskState,
    LocalPurgeTaskType,
)


def _governance() -> GovernanceActionSummary:
    return GovernanceActionSummary(
        share=GovernanceActionState(state="available", label="Share", reason="Login-required sharing", destructive=False),
        export=GovernanceActionState(state="disabled", label="Export package", reason="No package", destructive=False),
        download=GovernanceActionState(state="disabled", label="Download", reason="No artifact", destructive=False),
        retention=GovernanceActionState(state="planned", label="Retention policy planned", reason="future", destructive=False),
        delete=GovernanceActionState(
            state="planned",
            label="Delete this meeting everywhere 2brain Rec controls",
            reason="future",
            destructive=True,
        ),
    )


def _access() -> MeetingAccessState:
    return MeetingAccessState(
        state="owner",
        label="Owner",
        reason="You own this meeting.",
        can_view=True,
        can_share=True,
        can_manage_team_visibility=True,
        can_download=True,
        can_export=True,
    )


def _artifacts() -> list[ArtifactEgressState]:
    return [
        ArtifactEgressState(
            artifact_class="transcript",
            state="processing",
            label="Transcript",
            reason="Transcript is still processing.",
            action="disabled",
        )
    ]


def _notes_truth() -> NotesActionTruthState:
    category = NotesActionCategoryState(
        state="processing",
        label="Outcomes processing",
        reason="Transcript and generated outcomes may still be processing.",
        readiness_impact="keeps_gap_open",
        copy_key="notes.outcomes.processing",
    )
    return NotesActionTruthState(
        summary=category,
        decisions=category,
        action_items=category,
        followups=category,
        source_basis="processing_status",
    )


def _item() -> MeetingListItem:
    return MeetingListItem(
        meeting_id=uuid4(),
        title="Проектный синк",
        started_at=datetime(2026, 6, 16, 8, 0, tzinfo=UTC),
        ended_at=None,
        duration_seconds=120,
        source="desktop_recording",
        status="processing",
        status_label="Processing",
        status_reason=None,
        primary_action="wait",
        transcript_available=False,
        diarization_available=False,
        notes_available=False,
        updated_at=None,
        access=_access(),
        artifacts=_artifacts(),
        governance=_governance(),
        future_slots=[
            SlotState(state="planned", label="Star", reason="future"),
            SlotState(state="planned", label="Tag", reason="future"),
        ],
    )


def _review() -> MeetingReviewResponse:
    item = _item()
    return MeetingReviewResponse(
        meeting=item,
        provenance=MeetingProvenance(
            source_roles=["local_microphone", "incoming_system"],
            processing_dependency="mediascribe",
            content_policy="authorized_detail_only",
        ),
        processing=ProcessingReviewState(
            state="processing",
            stage="mediascribe",
            reason_code=None,
            reason_label=None,
            content_available=False,
            transcript_available=False,
            diarization_available=False,
            summary_available=False,
            updated_at=None,
            next_action="wait",
        ),
        transcript=TranscriptReviewState(available=False, language=None, degraded_reason="processing", search_enabled=False, segments=[]),
        speakers=SpeakerReviewState(available=False, assignment_state="reserved", degraded_reason="processing", speakers=[]),
        notes=NotesReviewState(available=False, sections=[], unavailable_reason="processing"),
        playback=PlaybackReviewState(available=False, duration_seconds=120, speed_options=[0.75, 1.0, 1.25, 1.5, 2.0]),
        governance=_governance(),
        access=_access(),
        share=SharePanelState(
            team_visibility="disabled",
            active_grants=[],
            copy_link_state="available",
            public_link_state="disabled_by_default",
        ),
        artifacts=_artifacts(),
        activity=MeetingActivityResponse(meeting_id=item.meeting_id, items=[]),
        notes_action_truth=_notes_truth(),
        deletion_truth_copy="Files already downloaded or exported are outside 2brain Rec deletion control.",
        assistant=SlotState(state="planned", label="Assistant", reason="future"),
        template=SlotState(state="planned", label="Template", reason="future"),
    )


def _deletion_report() -> DeletionVerificationReport:
    expires_at = datetime.now(UTC) + timedelta(days=7)
    return DeletionVerificationReport(
        meeting_id=uuid4(),
        request_id=uuid4(),
        overall_state=DeletionState.DELETING,
        bounded_copy=BOUNDED_DELETE_COPY,
        artifact_states=[
            ArtifactDeletionState(
                artifact_class="audio_object",
                control_scope=DeletionControlScope.CONTROLLED,
                state=DeletionArtifactState.PURGE_REQUESTED,
                label="Server audio purge requested",
                safe_reason="artifact_lifecycle_state",
            )
        ],
        backup=ArtifactDeletionState(
            artifact_class="backup",
            control_scope=DeletionControlScope.BACKUP,
            state=DeletionArtifactState.PENDING_EXPIRY,
            label="Backup expiry pending",
            safe_reason="backup_expiry_pending",
        ),
        dependencies=[
            ArtifactDeletionState(
                artifact_class="mediascribe",
                control_scope=DeletionControlScope.EXTERNAL,
                state=DeletionArtifactState.UNKNOWN,
                label="External deletion support is not confirmed",
                safe_reason="dependency_unconfirmed",
            )
        ],
        post_egress_limits=[
            ArtifactDeletionState(
                artifact_class="post_egress_copy",
                control_scope=DeletionControlScope.POST_EGRESS,
                state=DeletionArtifactState.OUTSIDE_2BRAIN_CONTROL,
                label="Delivered copies are outside 2brain Rec control",
                safe_reason="outside_control",
            )
        ],
        local_purge=[
            LocalPurgeTask(
                task_id=uuid4(),
                meeting_id=uuid4(),
                task_type=LocalPurgeTaskType.PURGE_LOCAL_BUFFERS,
                state=LocalPurgeTaskState.PENDING,
                safe_reason="delete_requested",
                expires_at=expires_at,
            ),
            LocalPurgeTask(
                task_id=uuid4(),
                meeting_id=uuid4(),
                task_type=LocalPurgeTaskType.PURGE_LOCAL_EXPORTS,
                state=LocalPurgeTaskState.ACKNOWLEDGED,
                safe_reason="local_buffers_purged",
                expires_at=expires_at,
            ),
            LocalPurgeTask(
                task_id=uuid4(),
                meeting_id=uuid4(),
                task_type=LocalPurgeTaskType.CONFIRM_LOCAL_EXPIRY,
                state=LocalPurgeTaskState.UNREACHABLE,
                safe_reason="device_unreachable",
                expires_at=expires_at,
            ),
        ],
        activity=[
            LifecycleActivityItem(
                event_id=uuid4(),
                event_type="deletion_requested",
                actor_label="Owner/Admin",
                outcome="accepted",
                safe_reason="user_request",
                created_at=datetime.now(UTC),
            ),
            LifecycleActivityItem(
                event_id=uuid4(),
                event_type="local_purge_acknowledged",
                actor_label="Desktop device",
                outcome="completed",
                safe_reason="local_buffers_purged",
                created_at=datetime.now(UTC),
            ),
        ],
    )


def test_list_shell_renders_dense_controls_without_marketing_copy() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )

    assert "Мои встречи" in page
    assert "Ближайшие" in page
    assert "Записи встреч" in page
    assert "Новая" in page
    assert "Сначала новые" in page
    assert "updated_desc" not in page
    assert ":focus-visible" in page
    assert "hero" not in page.lower()


def test_detail_shell_renders_tabs_and_gated_actions() -> None:
    page = render_meeting_detail_page(_review())

    assert "Итоги" in page
    assert "Запись и расшифровка" in page
    assert 'role="tablist" aria-label="Содержимое встречи"' in page
    assert 'data-detail-tab="recording"' in page
    assert 'aria-selected="true" aria-controls="detail-panel-recording"' in page
    assert 'data-detail-panel="outcomes" hidden' in page
    assert 'data-detail-panel="recording"' in page
    assert "const activate = (name)" in page
    assert "Транскрипт готовится" in page
    assert "Видимость для команды" in page
    assert "Публичные ссылки" in page
    assert "Уже скачанные или экспортированные файлы" in page
    assert 'data-boundary-copy="Files already downloaded' in page
    assert "Удалить встречу в системах 2brain Rec" in page
    assert "Request deletion" not in page
    assert "Запросить удаление" in page


def test_detail_shell_renders_playback_player_and_seekable_timestamps() -> None:
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
                segment_id="safe-segment-1",
                sequence=0,
                start_seconds=0.0,
                end_seconds=10.0,
                timestamp_label="00:00",
                speaker_label="Speaker 1",
                source_role="local_microphone",
                text="Безопасный синтетический текст.",
                seekable=True,
                seek_seconds=0.0,
            ),
            TranscriptSegmentView(
                segment_id="safe-segment-2",
                sequence=1,
                start_seconds=12.5,
                end_seconds=20.0,
                timestamp_label="00:12",
                speaker_label="Speaker 2",
                source_role="incoming_system",
                text="Еще один безопасный синтетический текст.",
                seekable=True,
                seek_seconds=12.5,
            ),
        ],
    )

    page = render_meeting_detail_page(review)

    assert 'class="playback-bar detail-playback"' in page
    assert "data-playback-shell" in page
    assert '<audio class="playback-audio" data-playback-player preload="metadata"' in page
    assert '<audio data-playback-player controls preload="metadata"' not in page
    assert f'src="/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback"' in page
    assert 'data-source-mode="combined_review_stream"' in page
    assert 'data-playback-toggle' in page
    assert 'data-playback-skip="-15"' in page
    assert 'data-playback-skip="15"' in page
    assert "data-playback-current" in page
    assert "data-playback-duration" in page
    assert "data-playback-speed-toggle" in page
    assert 'data-seek-seconds="0.0"' in page
    assert 'data-seek-seconds="12.5"' in page
    assert 'class="timestamp timestamp-seek"' in page
    assert "currentTime = seekSeconds" in page
    assert "syncTime();" in page


def test_detail_shell_renders_speaker_timeline_segments() -> None:
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
    review.speakers = SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        degraded_reason=None,
        speakers=[
            SpeakerLane(
                speaker_key="speaker-1",
                label="Speaker 1",
                talk_time_percent=35,
                source_roles=["local_microphone"],
                segments=[SpeakerLaneSegment(start_seconds=0.0, end_seconds=12.0)],
            ),
            SpeakerLane(
                speaker_key="speaker-2",
                label="Speaker 2",
                talk_time_percent=65,
                source_roles=["incoming_system"],
                segments=[SpeakerLaneSegment(start_seconds=30.0, end_seconds=90.0)],
            ),
        ],
    )

    page = render_meeting_detail_page(review)

    assert "data-speaker-timeline" in page
    assert 'data-speaker-lane="speaker-1"' in page
    assert 'data-speaker-lane="speaker-2"' in page
    assert page.count("data-lane-segment") == 2
    assert 'title="Спикер 1 00:00-00:12"' in page
    assert 'aria-label="Спикер 2 00:30-01:30"' in page
    assert ".timeline-lane:nth-child(6n+1) .timeline-segment" in page
    assert ".timeline-lane:nth-child(6n+6) .timeline-segment" in page
    assert "left:0.00%" in page
    assert "width:10.00%" in page
    assert "left:25.00%" in page
    assert "width:50.00%" in page


def test_detail_shell_renders_unavailable_playback_without_audio_element() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=False,
        duration_seconds=120,
        unavailable_reason="policy_disabled",
        playback_path=None,
        policy_label="Аудио закрыто политикой доступа",
        source_mode="none",
        included_sources=[],
    )

    page = render_meeting_detail_page(review)

    assert '<section class="playback-bar detail-playback is-unavailable" data-source-mode="none">' in page
    assert "Аудио закрыто политикой доступа" in page
    assert "<audio" not in page
    assert "data-playback-player" not in page


def test_detail_shell_reserves_notes_assistant_template_without_internal_feature_labels() -> None:
    review = _review()
    review.notes = NotesReviewState(available=False, sections=[], unavailable_reason="generation_future")

    page = render_meeting_detail_page(review)

    assert "Кратко" in page
    assert "Решения" in page
    assert "Действия" in page
    assert "Продолжение" in page
    assert "Итоги готовятся" in page
    assert "AI notes are reserved for a later feature" not in page
    assert "No generated summary is shown yet" not in page
    assert "<h3>Ассистент</h3>" in page
    assert "<button type=\"button\" disabled>Ассистент</button>" in page
    assert "<h3>Шаблон</h3>" in page
    assert "feature 016" not in page.lower()
    assert "feature:016" not in page.lower()
    assert "016-meeting-detail" not in page


def test_detail_shell_renders_stored_outcomes_with_long_content_and_playback_spacing() -> None:
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
    summary = NotesActionCategoryState(
        state="available",
        label="Итоги готовы",
        reason="Сохраненный итог доступен и связан с расшифровкой.",
        readiness_impact="closes_gap",
        copy_key="notes.summary.available",
        items=[
            OutcomeItemView(
                category="summary",
                sequence=0,
                text=(
                    "Синтетический длинный итог встречи занимает несколько строк, "
                    "чтобы проверить переносы, ширину карточки и совместимость с нижним плеером."
                ),
                truth_label="supported",
                source_refs=[
                    OutcomeSourceReferenceView(
                        sequence=1,
                        start_seconds=12.5,
                        end_seconds=20.0,
                        evidence_kind="segment",
                    )
                ],
            )
        ],
    )
    deferred = NotesActionCategoryState(
        state="not_found",
        label="Не найдено",
        reason="В расшифровке нет надежной опоры для этой категории.",
        readiness_impact="closes_gap",
        copy_key="notes.outcomes.not_found",
    )
    review.notes_action_truth = NotesActionTruthState(
        summary=summary,
        key_points=deferred,
        decisions=deferred,
        action_items=deferred,
        followups=deferred,
        risks=deferred,
        questions=deferred,
        evidence=summary,
        source_basis="stored_output",
    )

    page = render_meeting_detail_page(review)

    assert 'data-outcome-source-basis="stored_output"' in page
    assert 'data-outcome-category="summary"' in page
    assert 'data-outcome-state="available"' in page
    assert "Синтетический длинный итог встречи" in page
    assert "Источник: 00:12" in page
    assert "Ключевое" in page
    assert ".notes-outcome-row .outcome-item" in page
    assert "grid-column: 1 / -1" in page
    assert 'class="playback-bar detail-playback"' in page


def test_embedded_shell_removes_native_capture_controls_and_copy() -> None:
    list_page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        ),
        embedded=True,
    )
    detail_page = render_meeting_detail_page(_review(), embedded=True)
    html = list_page + detail_page

    assert "desktop-embedded" in html
    assert "Recording &amp; Transcript" not in html
    for forbidden in ["Record live", "Stop", "Screen Recording", "Noise", "Accent", "Krisp Devices"]:
        assert forbidden not in html


def test_embedded_detail_preserves_playback_player_and_timestamp_seek() -> None:
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
                segment_id="safe-segment-embedded",
                sequence=0,
                start_seconds=12.5,
                end_seconds=20.0,
                timestamp_label="00:12",
                speaker_label="Speaker 2",
                source_role="incoming_system",
                text="Безопасный синтетический текст.",
                seekable=True,
                seek_seconds=12.5,
            )
        ],
    )

    page = render_meeting_detail_page(review, embedded=True)

    assert 'class="app-shell desktop-embedded"' in page
    assert 'class="playback-bar detail-playback"' in page
    assert "data-playback-shell" in page
    assert '<audio class="playback-audio" data-playback-player preload="metadata"' in page
    assert '<audio data-playback-player controls preload="metadata"' not in page
    assert f'src="/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback"' in page
    assert 'data-source-mode="combined_review_stream"' in page
    assert 'data-playback-toggle' in page
    assert 'data-playback-skip="-15"' in page
    assert 'data-playback-skip="15"' in page
    assert 'data-seek-seconds="12.5"' in page
    assert "currentTime = seekSeconds" in page


def test_deletion_report_shell_renders_metadata_only_lifecycle_truth() -> None:
    page = render_deletion_report_page("Sensitive customer sync", _deletion_report())

    assert "Отчет удаления" in page
    assert "Файлы под контролем 2brain Rec" in page
    assert "Внешние зависимости" in page
    assert "Ограничения после выгрузки" in page
    assert "Очистка на устройстве" in page
    assert "События удаления" in page
    assert "удаление запрошено" in page
    assert "локальная очистка подтверждена" in page
    assert "Владелец/админ" in page
    assert "Десктоп" in page
    assert "ожидает" in page
    assert "подтверждено" in page
    assert "недоступно" in page
    assert BOUNDED_DELETE_COPY in page
    assert "Sensitive customer sync" in page
    assert "storage_object_key" not in page
    assert "external_job_id" not in page
    assert "/Users/" not in page
    assert "SAFE_TRANSCRIPT_TEXT" not in page
