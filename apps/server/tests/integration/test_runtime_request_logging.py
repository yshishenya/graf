import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

SERVER_ROOT = Path(__file__).resolve().parents[2]
REQUEST_MARKERS = {
    "Authorization": "Bearer synthetic-auth-marker",
    "Cookie": "session=synthetic-cookie-marker",
    "Referer": "https://example.test/synthetic-referer-marker",
    "X-Private-Header": "synthetic-private-header-marker",
}


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _request_health(url: str, process: subprocess.Popen[str]) -> int:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError("The child Uvicorn process stopped before accepting the request")
        try:
            request = Request(url, headers=REQUEST_MARKERS)
            with urlopen(request, timeout=0.5) as response:  # noqa: S310 -- local test child only
                return response.status
        except URLError:
            time.sleep(0.1)
    raise AssertionError("The child Uvicorn process did not become ready")


def test_child_uvicorn_request_logs_contain_only_safe_metadata() -> None:
    port = _free_tcp_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "tests.fixtures.runtime_request_logging_app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
            "--log-level",
            "warning",
        ],
        cwd=SERVER_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = ""
    try:
        status_code = _request_health(
            f"http://127.0.0.1:{port}/health/11111111-1111-1111-1111-111111111111?synthetic-query-marker",
            process,
        )
    finally:
        process.terminate()
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=5)

    assert status_code == 200
    assert "request.end" in output
    assert '"path": "/health/{uuid}"' in output
    assert '"status_code": 200' in output
    assert '"duration_ms":' in output
    assert "synthetic-query-marker" not in output
    assert all(marker not in output for marker in REQUEST_MARKERS.values())
