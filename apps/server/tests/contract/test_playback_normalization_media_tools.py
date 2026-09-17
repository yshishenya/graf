"""Selected real media proofs cannot turn missing tools into a passing skip."""
import pytest

from tests.integration import test_playback_normalization_media_matrix as matrix
from tests.integration import test_playback_normalization_test_rec_e2e as test_rec
from tests.integration import test_playback_normalization_workflow as workflow


@pytest.mark.parametrize("missing", ["ffmpeg", "ffprobe"])
@pytest.mark.parametrize("entrypoint", ["matrix", "workflow", "authorized"])
def test_selected_media_requires_both_tools(monkeypatch, tmp_path, missing, entrypoint):
    monkeypatch.setattr(matrix.shutil, "which", lambda name: None if name == missing else "/synthetic/tool")
    monkeypatch.setenv(test_rec.TEST_REC_DIRECTORY_ENV, str(tmp_path))
    try:
        with pytest.raises(pytest.fail.Exception, match="FFmpeg and ffprobe are required"):
            if entrypoint == "matrix":
                matrix._media_tools()
            elif entrypoint == "workflow":
                workflow.test_real_ffmpeg_pipeline_builds_validated_dual_source_playback(tmp_path)
            else:
                test_rec.test_authorized_test_rec_converts_automatically_and_leaves_no_residue(None, tmp_path)
    except pytest.skip.Exception:
        pytest.fail("a missing media tool skipped a required proof")
    assert list(tmp_path.iterdir()) == []


def test_private_recording_remains_opt_in_before_tool_lookup(monkeypatch, tmp_path):
    monkeypatch.delenv(test_rec.TEST_REC_DIRECTORY_ENV, raising=False)

    def unexpected_lookup(name):
        pytest.fail("private recording opt-in must precede tool lookup")

    monkeypatch.setattr(test_rec.shutil, "which", unexpected_lookup)
    with pytest.raises(pytest.skip.Exception, match="authorized local evidence"):
        test_rec.test_authorized_test_rec_converts_automatically_and_leaves_no_residue(None, tmp_path)
    assert list(tmp_path.iterdir()) == []
