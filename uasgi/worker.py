from __future__ import annotations

import os
import sys
import signal
import threading
import multiprocessing as mp
from typing import TYPE_CHECKING, Optional

import uvloop

from .server import Server
from .utils import create_logger, load_app
from .reloader import Reloader


if TYPE_CHECKING:
    from .config import Config

uvloop.install()


class Worker:
    def __init__(self, config: "Config"):
        self.app = config.app
        self.worker = None
        self.config = config
        self.logger = create_logger(
            __name__, self.config.log_level, self.config.log_fmt
        )
        self.server: Optional[Server] = None
        (self._read_stdout_fd, self._write_stdout_fd) = os.pipe()
        (self._read_stderr_fd, self._write_stderr_fd) = os.pipe()

    @property
    def stdout_fd(self):
        return self._read_stdout_fd

    @property
    def stderr_fd(self):
        return self._read_stderr_fd

    def run(self, blocking=False):
        if self.config.workers > 1 and self.config.reload:
            raise RuntimeError(
                "Number of workers must be 1 in auto reloading mode"
            )

        if not isinstance(self.app, str) and self.config.reload:
            raise RuntimeError(
                "app must be str or factory function in auto reloading mode"
            )

        self.worker = mp.Process(
            target=self.main,
            daemon=False,
            args=(
                self._write_stdout_fd.is_integer(),
                self._write_stderr_fd.is_integer(),
            ),
        )

        self.worker.start()

        if blocking:
            if self.config.reload:
                reloader = Reloader(self, self.config)
                reloader.main()

            else:
                stop_event = threading.Event()
                try:
                    stop_event.wait()
                except KeyboardInterrupt:
                    self.worker.join(timeout=5)
                    return 1

        return 0

    def _sync_to_stdio(self, stdout_fd: int, stderr_fd: int):
        # https://man7.org/linux/man-pages/man2/dup.2.html
        os.dup2(stdout_fd, sys.stdout.fileno())
        os.dup2(stderr_fd, sys.stderr.fileno())
        sys.stdout = sys.__stdout__ = open(1, "w", buffering=1)
        sys.stderr = sys.__stderr__ = open(2, "w", buffering=1)

    def main(self, stdout_fd: int, stderr_fd: int):
        """Entrypoint where child processes start and run"""

        self._sync_to_stdio(stdout_fd, stderr_fd)

        logger = create_logger(
            __name__, self.config.log_level, self.config.log_fmt
        )

        app = load_app(self.app)
        server = Server(
            app=app,
            config=self.config,
        )

        logger.info(f"Worker {self.pid} is running")

        # when user presses Ctrl-C, SIGINT will be sent to all processes
        # (what belongs to the process group) includes children so we
        # should catch them in children at here
        try:
            server.main()
        except KeyboardInterrupt:
            server.stop()
        finally:
            self.logger.info(f"Worker {self.pid} was stopped")

    @property
    def pid(self):
        if self.worker:
            return self.worker.pid

    def reload(self):
        if self.pid:
            self.logger.info("Worker is reloading")
            os.kill(self.pid, signal.SIGINT)
            self.join()
            self.run()

    def join(self):
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=5)
