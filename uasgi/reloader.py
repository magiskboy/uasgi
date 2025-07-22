import os
import time
import threading
from typing import TYPE_CHECKING

from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
    DirCreatedEvent,
    FileCreatedEvent,
    DirModifiedEvent,
    FileModifiedEvent,
    DirMovedEvent,
    FileMovedEvent,
    DirDeletedEvent,
    FileDeletedEvent,
)
from watchdog.observers import Observer

from .utils import create_logger


if TYPE_CHECKING:
    from .config import Config
    from .worker import Worker


class Reloader(FileSystemEventHandler):
    CHANGED_EVENT_TYPES = [
        DirCreatedEvent,
        DirModifiedEvent,
        DirMovedEvent,
        DirDeletedEvent,
        FileCreatedEvent,
        FileModifiedEvent,
        FileMovedEvent,
        FileDeletedEvent,
    ]

    DELAY_TO_LAST_TIME_RELOAD = 1

    def __init__(
        self,
        worker: "Worker",
        config: "Config",
    ):
        self.worker = worker
        self.config = config

        self.logger = create_logger(__name__, config.log_level, config.log_fmt)
        self.changed_event = threading.Event()
        self.stop_event = threading.Event()
        self.observer = Observer()
        self.reload_last_time = time.time()

        self.worker: "Worker"

    def on_any_event(self, event: FileSystemEvent) -> None:
        if self.should_reload(event):
            filename = event.src_path
            self.logger.info(f"{filename} changed")
            self.changed_event.set()

        return super().on_any_event(event)

    def should_reload(self, event: FileSystemEvent):
        diff = time.time() - self.reload_last_time
        if self.changed_event.is_set():
            return False

        if diff < Reloader.DELAY_TO_LAST_TIME_RELOAD:
            return False

        if event.is_directory:
            return False

        filename = str(os.path.basename(event.src_path))
        if filename.endswith(".py"):
            return True

        return False

    def reload_server(self):
        self.worker.reload()
        self.reload_last_time = time.time()

    def main(self):
        self.logger.debug("Reloader is running")
        cwd = os.getcwd()
        self.observer.schedule(
            event_handler=self,
            path=cwd,
            recursive=True,
            event_filter=Reloader.CHANGED_EVENT_TYPES,
        )
        self.observer.start()

        while not self.stop_event.is_set():
            try:
                self.changed_event.wait()

                self.reload_server()
                self.changed_event.clear()
            except KeyboardInterrupt:
                self.stop()

        self.logger.debug("Reloader is stopped")

    def stop(self):
        self.worker.join()
        self.stop_event.set()
