import os
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager, suppress
from socket import SHUT_RDWR, socket
from threading import Event, Timer
from time import monotonic

import certifi
from urllib3 import HTTPConnectionPool, HTTPSConnectionPool, PoolManager, Timeout
from urllib3.connection import HTTPConnection, HTTPSConnection


def _interrupt(sock: socket) -> None:
    with suppress(OSError):
        sock.shutdown(SHUT_RDWR)


def _stop_watchdog(watchdog: Timer) -> None:
    watchdog.cancel()
    watchdog.join()


@contextmanager
def strict_storage_http(
    deadline: float, cancelled: Event, addresses: list,
    *, permit: Callable[[str, str], bool],
) -> Iterator[PoolManager]:
    """Bound all traffic to resolved addresses and one monotonic deadline."""
    def remaining() -> float:
        seconds = deadline - monotonic()
        if seconds <= 0 or cancelled.is_set():
            raise TimeoutError("Protected storage request stopped")
        return seconds

    with ExitStack() as resources:
        class InterruptibleConnection:
            def _new_conn(self):
                last_error = None
                for family, kind, protocol, _, address in addresses:
                    timeout = remaining()
                    sock = None
                    try:
                        sock = socket(family, kind, protocol)
                        for option in self.socket_options or ():
                            sock.setsockopt(*option)
                        if self.source_address:
                            sock.bind(self.source_address)
                        sock.settimeout(timeout)
                        sock.connect(address)
                        break
                    except OSError as exc:
                        if sock is not None:
                            sock.close()
                        last_error = exc
                else:
                    raise OSError("Protected storage endpoint is unreachable") from last_error

                try:
                    sock.settimeout(remaining())
                    # A duplicate still addresses the same transport after TLS
                    # takes ownership of the original socket descriptor.
                    endpoint = resources.enter_context(sock.dup())
                    watchdog = Timer(remaining(), _interrupt, (endpoint,))
                    watchdog.daemon = True
                    watchdog.start()
                    resources.callback(_stop_watchdog, watchdog)
                except BaseException:
                    sock.close()
                    raise
                return sock

        class BoundedHTTPConnection(InterruptibleConnection, HTTPConnection):
            pass

        class BoundedHTTPSConnection(InterruptibleConnection, HTTPSConnection):
            pass

        class BoundedHTTPPool(HTTPConnectionPool):
            ConnectionCls = BoundedHTTPConnection

        class BoundedHTTPSPool(HTTPSConnectionPool):
            ConnectionCls = BoundedHTTPSConnection

        class BoundedPool(PoolManager):
            def urlopen(self, method, url, **kwargs):
                seconds = remaining()
                if not permit(method, url):
                    raise OSError("Protected storage request is not allowed")
                kwargs.update(
                    redirect=False, retries=False, decode_content=False,
                    timeout=Timeout(total=seconds),
                )
                return super().urlopen(method, url, **kwargs)

        with BoundedPool(
            cert_reqs="CERT_REQUIRED", ca_certs=os.environ.get("SSL_CERT_FILE") or certifi.where()
        ) as pool:
            pool.pool_classes_by_scheme = {"http": BoundedHTTPPool, "https": BoundedHTTPSPool}
            yield pool


@contextmanager
def strict_source_http(deadline: float, cancelled: Event, addresses: list) -> Iterator[PoolManager]:
    sent: set[str] = set()

    def permit(method: str, url: str) -> bool:
        # MinIO may look up the bucket region once before the object GET.
        if method != "GET" or url in sent or len(sent) >= 2:
            return False
        sent.add(url)
        return True

    with strict_storage_http(deadline, cancelled, addresses, permit=permit) as pool:
        yield pool
