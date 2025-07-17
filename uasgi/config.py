from __future__ import annotations

import os
import socket
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .utils import LOG_LEVEL


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
        log_level: "LOG_LEVEL" = "INFO",
        lifespan: bool = False,
        access_log: bool = True,
    ):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = sock
        self.backlog = backlog
        self.workers = workers
        self.ssl = ssl
        self.ssl_cert_file = ssl_cert_file
        self.ssl_key_file = ssl_key_file
        self.log_level: LOG_LEVEL = log_level
        self.lifespan = lifespan
        self.access_log = access_log

    def get_ssl(self):
        from .utils import create_ssl_context

        if self.ssl:
            return self.ssl

        if self.ssl_cert_file and self.ssl_key_file:
            self.ssl = create_ssl_context(
                self.ssl_cert_file, self.ssl_key_file
            )

        return self.ssl

    @property
    def socket(self) -> socket.socket:  # ty: ignore[unresolved-attribute]
        if self.sock is None:
            host = self.host or "127.0.0.1"
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
