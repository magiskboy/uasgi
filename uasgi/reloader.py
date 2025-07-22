import asyncio
import os
import sys
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
    ):
        if config.workers and config.workers > 1:
            raise RuntimeError(
                "Number of workers must equals to 1 in reloader mode."
            )
        self.app = app
        self.config = config

        self.logger = create_logger(__name__, config.log_level, config.log_fmt)
        self.changed_event = threading.Event()
        self.stop_event = stop_event
        self.observer = Observer()
        self.reload_last_time = time.time()
        self.cwd = os.getcwd()

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

    def sync_stdio(self):
        loop = asyncio.new_event_loop()

        def handle_for(out_fd, in_fd):
            os.sendfile(out_fd, in_fd, 0, 1024)

        loop.add_reader(
            self.worker.stdout_fd,
            handle_for,
            sys.stdout.fileno(),
            self.worker.stdout_fd,
        )
        loop.add_reader(
            self.worker.stderr_fd,
            handle_for,
            sys.stderr.fileno(),
            self.worker.stderr_fd,
        )

        loop.run_forever()

    def main(self):
        self.logger.debug("Reloader is running")
        self.observer.schedule(
            event_handler=self,
            path=self.cwd,
            recursive=True,
            event_filter=Reloader.CHANGED_EVENT_TYPES,
        )

        self.worker = Worker(
            app=self.app,
            config=self.config,
            name="dev",
        )

        threading.Thread(target=self.sync_stdio, daemon=True).start()

        self.worker.run()

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
