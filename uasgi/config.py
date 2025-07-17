from __future__ import annotations

import os
import socket
from typing import TYPE_CHECKING, Optional

from .utils import DEFAULT_LOG_FMT


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
        log_fmt: Optional[str] = None,
        access_log_fmt: Optional[str] = None,
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
        self.log_fmt = log_fmt
        self.access_log_fmt = access_log_fmt

    def get_ssl(self):
        from .utils import create_ssl_context

        if self.ssl:
            return self.ssl

        if self.ssl_cert_file and self.ssl_key_file:
            self.ssl = create_ssl_context(
                self.ssl_cert_file, self.ssl_key_file
            )

        return self.ssl

    def setup_socket(self):
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

    @property
    def socket(self) -> socket.socket:  # ty: ignore[unresolved-attribute]
        if self.sock:
            return self.sock

        return self.setup_socket()

    def __str__(self) -> str:
        output = ""

        def fmt(value) -> str:
            if isinstance(value, str):
                return value
            return str(value)

        title = "Starting ASGI Web Server with Configuration\n"
        output += title
        output += "=" * len(title) + "\n"

        entries = {
            "Host": self.host,
            "Port": self.port,
            "Socket": self.sock,
            "Backlog": self.backlog,
            "Workers": self.workers,
            "SSL Enabled": self.ssl is not None,
            "SSL Cert File": self.ssl_cert_file,
            "SSL Key File": self.ssl_key_file,
            "Log Level": self.log_level,
            "Access Log": self.access_log,
            "Access Log Format": self.access_log_fmt or DEFAULT_LOG_FMT,
            "Log Format": self.log_fmt or DEFAULT_LOG_FMT,
            "Lifespan": self.lifespan,
        }

        max_key_len = max(len(k) for k in entries)

        for key, val in entries.items():
            line = f"{key:<{max_key_len}} : {fmt(val)}\n"
            output += line

        output += "=" * len(title) + "\n"
        return output
