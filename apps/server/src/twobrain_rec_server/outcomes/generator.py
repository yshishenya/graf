from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence

from twobrain_rec_server.domain.statuses import OutcomeCategory
from twobrain_rec_server.outcomes.models import (
    GeneratedOutcomeItem,
    GeneratedOutcomePayload,
    OutcomeSourceReference,
    OutcomeTranscriptSegment,
)

CATEGORIES = [category.value for category in OutcomeCategory]
NEGATIVE_CONTEXT_RE = re.compile(r"\b(без|нет|не было|отсутств)\b", re.IGNORECASE)
DECISION_RE = re.compile(r"\b(решили|решение|приняли)\b", re.IGNORECASE)
ACTION_RE = re.compile(r"\b(договорились|нужно|надо|проверить|сделать|подготовить)\b", re.IGNORECASE)
FOLLOWUP_RE = re.compile(r"\b(следующ|follow[- ]?up|вернуться)\b", re.IGNORECASE)
RISK_RE = re.compile(r"\b(риск|блокер|проблем|зависим)\b", re.IGNORECASE)
QUESTION_RE = re.compile(r"\?|\b(вопрос|как|что дальше)\b", re.IGNORECASE)


def generate_outcomes(segments: Sequence[OutcomeTranscriptSegment]) -> GeneratedOutcomePayload:
    ordered = [segment for segment in sorted(segments, key=lambda item: (item.sequence, item.start_seconds)) if segment_text(segment)]
    items_by_category: dict[str, list[GeneratedOutcomeItem]] = {category: [] for category in CATEGORIES}
    states = {category: "not_found" for category in CATEGORIES}
    if not ordered:
        return GeneratedOutcomePayload(category_states={category: "not_inferable" for category in CATEGORIES}, items_by_category=items_by_category)

    summary_segment = ordered[0]
    items_by_category["summary"].append(_item("summary", 0, _bounded_text(summary_segment.text), summary_segment))
    states["summary"] = "available"

    for index, segment in enumerate(ordered[:3]):
        items_by_category["key_points"].append(_item("key_points", index, _bounded_text(segment.text), segment))
    states["key_points"] = "available"

    evidence_segment = ordered[0]
    items_by_category["evidence"].append(
        _item(
            "evidence",
            0,
            f"Фрагмент на {_time_label(float(evidence_segment.start_seconds))}",
            evidence_segment,
        )
    )
    states["evidence"] = "available"

    cue_map = {
        "decisions": DECISION_RE,
        "action_items": ACTION_RE,
        "followups": FOLLOWUP_RE,
        "risks": RISK_RE,
        "questions": QUESTION_RE,
    }
    counters: dict[str, int] = defaultdict(int)
    for segment in ordered:
        lowered = segment.text.lower()
        if NEGATIVE_CONTEXT_RE.search(lowered):
            continue
        for category, pattern in cue_map.items():
            if pattern.search(segment.text):
                sequence = counters[category]
                counters[category] += 1
                items_by_category[category].append(_item(category, sequence, _bounded_text(segment.text), segment))
                states[category] = "available"

    for category in ["decisions", "action_items", "followups", "risks", "questions"]:
        if not items_by_category[category]:
            states[category] = "not_inferable" if category == "action_items" else "not_found"

    return GeneratedOutcomePayload(category_states=states, items_by_category=items_by_category)


def segment_text(segment: OutcomeTranscriptSegment) -> str:
    return " ".join(segment.text.split())


def _bounded_text(text: str, limit: int = 280) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _item(category: str, sequence: int, text: str, segment: OutcomeTranscriptSegment) -> GeneratedOutcomeItem:
    return GeneratedOutcomeItem(
        category=category,
        sequence=sequence,
        text=text,
        truth_label="supported",
        source_refs=[
            OutcomeSourceReference(
                transcript_segment_id=segment.segment_id,
                sequence=segment.sequence,
                start_seconds=float(segment.start_seconds),
                end_seconds=float(segment.end_seconds),
                speaker_label=segment.speaker_label,
                source_role=segment.source_role,
                evidence_kind="segment",
            )
        ],
    )


def _time_label(seconds: float) -> str:
    total = max(0, int(seconds))
    minute, second = divmod(total, 60)
    return f"{minute:02d}:{second:02d}"
