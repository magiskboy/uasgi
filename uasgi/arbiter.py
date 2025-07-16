from __future__ import annotations

import logging
import time
import signal
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, List

from .worker import Worker

if TYPE_CHECKING:
    from .types import Config


class Arbiter:
    def __init__(self, app_factory, config: "Config", logger: logging.Logger):
        self.app_factory = app_factory
        self.config = config
        self.logger = logger

    def on_stop_signal(self, handler):
        STOP_SIGNALS = [signal.SIGINT, signal.SIGHUP, signal.SIGTERM]
        for s in STOP_SIGNALS:
            signal.signal(s, handler)

    def start(self):
        if not self.config.workers:
            raise RuntimeError('Number of workers must be greater than 0')

        _workers: List[Worker] = []
        stop_event = mp.Event()

        def shutdown(*_):
            nonlocal stop_event

            for worker in _workers:
                worker.stop()

            stop_event.set()

        self.on_stop_signal(shutdown)

        for _ in range(self.config.workers):
            worker = Worker(self.app_factory, self.config)
            worker.run()
            _workers.append(worker)

        with ThreadPoolExecutor(max_workers=len(_workers)) as pool:
            while not stop_event.is_set():
                fs = [pool.submit(worker.receiver.recv) for worker in _workers]
                for future in as_completed(fs, timeout=5):
                    ...

                time.sleep(1)

