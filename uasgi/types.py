from __future__ import annotations

import os
import socket
from typing import Optional, Literal, Tuple, Iterable, Dict, TypedDict, Callable, Coroutine


LOG_LEVEL = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']


class ASGIInfo(TypedDict):
    version: str
    spec_version: str


class ASGIScope(TypedDict):
    type: Literal["http", "websocket", "lifespan"]
    asgi: ASGIInfo
    http_version: str
    method: bytes
    scheme: Optional[Literal["https", "http", "ws", "wss", None]]
    path: str
    raw_path: Optional[bytes]
    query_string: bytes
    root_path: Optional[str]
    headers: Iterable[Tuple[bytes, bytes]]
    client: Optional[Tuple[str, int]]
    server: Optional[Tuple[str, int]]
    state: Optional[Dict]


ASGIHandler = Callable[[ASGIScope, Callable, Callable], Coroutine]


class Config:
    def __init__(
        self,
        host=None,
        port=None,
        sock=None,
        backlog=None,
        workers=None,
        ssl_cert_file=None,
        ssl_key_file=None,
        ssl=None,
        enable_h2=False,
        log_level: LOG_LEVEL = 'INFO',
    ):
        self.host = host
        self.port = port
        self.sock = sock
        self.backlog = backlog
        self.workers = workers
        self.ssl = ssl
        self.ssl_cert_file=ssl_cert_file
        self.ssl_key_file=ssl_key_file
        self.enable_h2 = enable_h2
        self.log_level: LOG_LEVEL = log_level

    def get_ssl(self):
        from .utils import create_ssl_context
        if self.ssl:
            return self.ssl

        if self.ssl_cert_file and self.ssl_key_file:
            self.ssl = create_ssl_context(self.ssl_cert_file, self.ssl_key_file)
            if self.enable_h2:
                self.ssl.set_alpn_protocols(['h2'])

        return self.ssl

    def create_socket(self):
        if self.sock is None:
            host = self.host or '127.0.0.1'
            port = self.port or 5000
            self.sock = socket.create_server(
                address=(host, port),
                family=socket.AF_INET,
                backlog=self.backlog or 4096,
                reuse_port=True,
            )

        if self.workers:
            os.set_inheritable(self.sock.fileno(), True)

        return self.sock

    @property
    def socket(self) -> socket.socket:
        return self.sock #type: ignore

