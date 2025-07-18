from __future__ import annotations

import logging
import signal
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

    def on_stop_signal(self, handler):
        STOP_SIGNALS = [signal.SIGINT, signal.SIGHUP, signal.SIGTERM]
        for s in STOP_SIGNALS:
            signal.signal(s, handler)

    def start(self):
        if not self.config.workers:
            raise RuntimeError("Number of workers must be greater than 0")

        _workers: List[Worker] = []
        stop_event = mp.Event()

        def shutdown(*_):
            nonlocal stop_event

            for worker in _workers:
                worker.stop()
                self.logger.info(f"Worker {worker.pid} is stopping...")

            stop_event.set()

        self.on_stop_signal(shutdown)

        for i in range(self.config.workers):
            worker = Worker(self.app, self.config, f"worker-{i}")
            worker.run()
            self.logger.info(f"Worker {worker.pid} is starting...")
            _workers.append(worker)

        while not stop_event.is_set():
            time.sleep(1)
