from __future__ import annotations

import logging
import multiprocessing as mp
import time
from typing import TYPE_CHECKING, Callable, List

from .worker import Worker


if TYPE_CHECKING:
    from .config import Config
    from .uhttp import ASGIHandler


class Arbiter:
    def __init__(
        self,
        app: str | Callable[[], "ASGIHandler"],
        config: "Config",
        logger: logging.Logger,
    ):
        self.app = app
        self.config = config
        self.logger = logger
        self.stop_event = mp.Event()
        self.workers: List[Worker] = []

    def start(self):
        if not self.config.workers:
            raise RuntimeError("Number of workers must be greater than 0")

        for i in range(self.config.workers):
            worker = Worker(self.app, self.config, f"worker-{i}")
            worker.run()
            self.logger.info(f"Worker {worker.pid} is starting...")
            self.workers.append(worker)

        while not self.stop_event.is_set():
            time.sleep(1)

    def stop(self):
        for worker in self.workers:
            worker.stop()
            self.logger.info(f"Worker {worker.pid} is stopping...")

        self.stop_event.set()
