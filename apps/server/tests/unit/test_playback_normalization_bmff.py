from __future__ import annotations

import struct

import pytest

from twobrain_rec_server.normalization.media import MediaPolicyError, inspect_bmff


def _box(box_type: bytes, payload: bytes = b"") -> bytes:
    return struct.pack(">I4s", len(payload) + 8, box_type) + payload


def test_bmff_parser_proves_faststart_and_nonfragmented_layout(tmp_path) -> None:
    source = tmp_path / "output.m4a"
    source.write_bytes(
        _box(b"ftyp", b"M4A \x00\x00\x00\x00") + _box(b"moov") + _box(b"mdat", b"\x00" * 8)
    )

    layout = inspect_bmff(source)

    assert layout.box_types == ("ftyp", "moov", "mdat")
    assert layout.moov_before_mdat is True
    assert layout.fragmented is False


def test_bmff_parser_reports_structurally_valid_non_faststart_layout(tmp_path) -> None:
    source = tmp_path / "remux-required.m4a"
    source.write_bytes(_box(b"ftyp", b"M4A \x00\x00\x00\x00") + _box(b"mdat") + _box(b"moov"))

    layout = inspect_bmff(source)

    assert layout.moov_before_mdat is False
    assert layout.fragmented is False


def test_bmff_parser_allows_empty_muxer_metadata_shell_but_flags_metadata_items(
    tmp_path,
) -> None:
    meta_header = b"\x00\x00\x00\x00"
    metadata_shell = _box(b"udta", _box(b"meta", meta_header + _box(b"ilst")))
    source = tmp_path / "metadata-shell.m4a"
    source.write_bytes(
        _box(b"ftyp", b"M4A \x00\x00\x00\x00")
        + _box(b"moov", metadata_shell)
        + _box(b"mdat", b"\x00" * 8)
    )

    assert inspect_bmff(source).has_private_metadata is False

    metadata_items = _box(
        b"udta",
        _box(b"meta", meta_header + _box(b"ilst", _box(b"data", b"private"))),
    )
    source.write_bytes(
        _box(b"ftyp", b"M4A \x00\x00\x00\x00")
        + _box(b"moov", metadata_items)
        + _box(b"mdat", b"\x00" * 8)
    )

    assert inspect_bmff(source).has_private_metadata is True


@pytest.mark.parametrize(
    "private_box",
    [
        _box(b"uuid", b"private-marker"),
        _box(b"free", b"private-marker"),
    ],
)
def test_bmff_parser_flags_unknown_or_nonempty_top_level_boxes(
    tmp_path,
    private_box: bytes,
) -> None:
    source = tmp_path / "private-top-level.m4a"
    source.write_bytes(
        _box(b"ftyp", b"M4A \x00\x00\x00\x00")
        + _box(b"moov")
        + _box(b"free")
        + _box(b"mdat", b"\x00" * 8)
        + private_box
    )

    layout = inspect_bmff(source)

    assert layout.has_private_metadata is True


@pytest.mark.parametrize(
    "private_child",
    [
        _box(b"junk", b"private-marker"),
        _box(b"\xa9nam", b"private-title"),
        _box(b"meta", b"\x00\x00\x00\x00" + _box(b"hdlr", b"\x00" * 24 + b"name")),
    ],
)
def test_bmff_parser_flags_unknown_nested_or_named_metadata_boxes(
    tmp_path,
    private_child: bytes,
) -> None:
    source = tmp_path / "private-nested.m4a"
    source.write_bytes(
        _box(b"ftyp", b"M4A \x00\x00\x00\x00")
        + _box(b"moov", _box(b"udta", private_child))
        + _box(b"mdat", b"\x00" * 8)
    )

    assert inspect_bmff(source).has_private_metadata is True


def test_bmff_parser_allows_header_only_free_and_empty_metadata_handler(tmp_path) -> None:
    metadata_shell = _box(
        b"udta",
        _box(
            b"meta",
            b"\x00\x00\x00\x00" + _box(b"hdlr", b"\x00" * 24) + _box(b"ilst"),
        ),
    )
    source = tmp_path / "safe-shell.m4a"
    source.write_bytes(
        _box(b"ftyp", b"M4A \x00\x00\x00\x00")
        + _box(b"moov", metadata_shell)
        + _box(b"free")
        + _box(b"mdat", b"\x00" * 8)
    )

    assert inspect_bmff(source).has_private_metadata is False


@pytest.mark.parametrize(
    "payload",
    [
        _box(b"ftyp", b"M4A \x00\x00\x00\x00") + _box(b"moov") + _box(b"moof") + _box(b"mdat"),
        struct.pack(">I4s", 1024, b"ftyp") + b"short",
        struct.pack(">I4s", 0, b"mdat"),
    ],
)
def test_bmff_parser_rejects_noncanonical_or_unbounded_layout(tmp_path, payload: bytes) -> None:
    source = tmp_path / "invalid.m4a"
    source.write_bytes(payload)

    with pytest.raises(MediaPolicyError) as exc_info:
        inspect_bmff(source)
    assert exc_info.value.reason_code == "generated_output_invalid"
