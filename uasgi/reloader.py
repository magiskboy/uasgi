import os
import time
import logging
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

from .worker import Worker


if TYPE_CHECKING:
    from .config import Config


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
        app: str,
        config: "Config",
        stop_event: threading.Event,
        logger: logging.Logger,
    ):
        self.app = app
        self.config = config

        self.logger = logger
        self.changed_event = threading.Event()
        self.stop_event = stop_event
        self.observer = Observer()
        self.reload_last_time = time.time()

        self.worker: "Worker"

    def on_any_event(self, event: FileSystemEvent) -> None:
        if self.should_reload(event):
            self.logger.info(event)
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

    def run(self):
        cwd = os.getcwd()
        self.observer.schedule(
            event_handler=self,
            path=cwd,
            recursive=True,
            event_filter=Reloader.CHANGED_EVENT_TYPES,
        )

        self.worker = Worker(
            app=self.app,
            config=self.config,
            name="dev",
        )
        self.worker.run()

        while not self.stop_event.is_set():
            self.changed_event.wait()

            self.reload_server()
            self.changed_event.clear()

        self.worker.stop()

    def stop(self):
        self.stop_event.set()
