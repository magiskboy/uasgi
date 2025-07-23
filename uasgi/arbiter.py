from __future__ import annotations

import os
import sys
import asyncio
import multiprocessing as mp
from typing import TYPE_CHECKING, List

from .utils import create_logger, to_thread
from .worker import Worker


if TYPE_CHECKING:
    from .config import Config


class Arbiter:
    def __init__(
        self,
        config: "Config",
    ):
        if asyncio.iscoroutinefunction(config.app):
            raise RuntimeError(
                "You must use str or factory function in worker mode"
            )

        self.app = config.app
        self.config = config
        self.logger = create_logger(__name__, config.log_level, config.log_fmt)
        self.stop_event = mp.Event()
        self.workers: List[Worker] = []
        self.loop = asyncio.new_event_loop()

    def main(self):
        self._validate_config()

        self.logger.debug("Arbitter is running")

        to_thread(self.loop.run_forever, daemon=True, start=True)

        for _ in range(self.config.workers):
            self._spawn_worker()

        try:
            self.stop_event.wait()
        except KeyboardInterrupt:
            ...
        finally:
            self.stop()

        self.logger.debug("Arbiter was stopped")

    def stop(self):
        self.stop_event.set()
        for worker in self.workers:
            worker.join()
        self.loop.stop()

    def _spawn_worker(self):
        worker = Worker(self.config)
        self.workers.append(worker)
        self._sync_stdio_worker(worker)
        worker.run()

    def _pipe_fd(self, out_fd, in_fd):
        os.sendfile(out_fd, in_fd, 0, 1024)

    def _sync_stdio_worker(self, worker: Worker):
        self.loop.add_reader(
            worker.stdout_fd,
            self._pipe_fd,
            sys.stdout.fileno(),
            worker.stdout_fd,
        )
        self.loop.add_reader(
            worker.stderr_fd,
            self._pipe_fd,
            sys.stderr.fileno(),
            worker.stderr_fd,
        )

    def _validate_config(self):
        if not self.config.workers:
            raise RuntimeError("Number of workers must be greater than 0")
