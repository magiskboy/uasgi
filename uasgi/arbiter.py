from __future__ import annotations

import os
import asyncio
import sys
import threading
import time
import multiprocessing as mp
from typing import TYPE_CHECKING, List

from .utils import create_logger
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

    def sync_stdio(self):
        def handle_for(out_fd, in_fd):
            os.sendfile(out_fd, in_fd, 0, 1024)

        loop = asyncio.new_event_loop()
        for worker in self.workers:
            loop.add_reader(
                worker.stdout_fd,
                handle_for,
                sys.stdout.fileno(),
                worker.stdout_fd,
            )
            loop.add_reader(
                worker.stderr_fd,
                handle_for,
                sys.stderr.fileno(),
                worker.stderr_fd,
            )

        loop.run_forever()

    def main(self):
        if not self.config.workers:
            raise RuntimeError("Number of workers must be greater than 0")

        self.logger.debug("Arbitter is running")

        for _ in range(self.config.workers):
            worker = Worker(self.config)
            self.workers.append(worker)

        threading.Thread(target=self.sync_stdio, daemon=True).start()

        for worker in self.workers:
            worker.run()

        while not self.stop_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.stop()

        self.logger.debug("Arbiter was stopped")

    def stop(self):
        self.stop_event.set()
        for worker in self.workers:
            worker.join()
