from __future__ import annotations

import os
import multiprocessing as mp
import sys
from typing import TYPE_CHECKING, Optional

import uvloop

from .server import Server
from .utils import create_logger, load_app


if TYPE_CHECKING:
    from .config import Config

uvloop.install()


class Worker:
    def __init__(self, app, config: "Config", name: str):
        self.app = app
        self.worker = None
        self.config = config
        self.logger = create_logger(
            __name__, self.config.log_level, self.config.log_fmt
        )

        self.name = name
        self.server: Optional[Server] = None
        (self._read_stdout_fd, self._write_stdout_fd) = os.pipe()
        (self._read_stderr_fd, self._write_stderr_fd) = os.pipe()

    @property
    def stdout_fd(self):
        return self._read_stdout_fd

    @property
    def stderr_fd(self):
        return self._read_stderr_fd

    def run(self):
        self.worker = mp.Process(
            target=self.main,
            name=self.name,
            daemon=False,
            args=(
                self._write_stdout_fd.is_integer(),
                self._write_stderr_fd.is_integer(),
            ),
        )
        self.worker.start()

    def main(self, stdout_writer, stderr_writer):
        """Entrypoint where child processes start and run"""
        # https://man7.org/linux/man-pages/man2/dup.2.html
        os.dup2(stdout_writer, sys.stdout.fileno())
        os.dup2(stderr_writer, sys.stderr.fileno())
        sys.stdout = sys.__stdout__ = open(1, "w", buffering=1)
        sys.stderr = sys.__stderr__ = open(2, "w", buffering=1)

        logger = create_logger(
            __name__, self.config.log_level, self.config.log_fmt
        )

        app = load_app(self.app)
        server = Server(
            app=app,
            config=self.config,
        )

        # when user presses Ctrl-C, SIGINT will be sent to all processes
        # includes children so we should catch them in children at here
        try:
            logger.info(f"Worker {self.pid} is running")
            server.run()
        except KeyboardInterrupt:
            server.stop()
        finally:
            self.logger.info(f"Worker {self.pid} was stopped")

    @property
    def pid(self):
        if self.worker:
            return self.worker.pid

        return "Unknown"

    def reload(self):
        self.logger.info("Worker is reloading")
        self.run()

    def join(self):
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=5)
