import asyncio
import multiprocessing as mp
import uvloop

from .server import Server
from .types import Config


class Worker:
    def __init__(self, app_factory, config: Config):
        self.app_factory = app_factory
        self.worker = None
        self.config = config

    def run(self):
        self.worker = mp.Process(target=self.serve)
        self.worker.start()

    def serve(self):
        uvloop.install()

        server = Server(self.app_factory, self.config)
        asyncio.run(server.serve(self.config.socket))

    def join(self):
        if self.worker and self.worker.is_alive():
            self.worker.join()

