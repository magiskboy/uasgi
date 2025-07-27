import threading
import time
from gunicorn.workers.base import Worker
from gunicorn.sock import TCPSocket

from .utils import load_app, to_thread
from .config import Config
from .server import Server


class UASGIWorker(Worker):
    def run(self):
        bind = self.cfg.bind[0]
        host, port = bind.split(":")
        sock: TCPSocket = self.sockets[0]
        app = load_app(self.app.app_uri)
        config = Config(
            app=app,
            host=host,
            port=port,
            sock=sock.sock,
            lifespan=False,
            access_log=False,
        )

        server = Server(app, config)

        event = threading.Event()
        to_thread(self.respond_master, args=(event,), start=True, daemon=True)

        try:
            server.main()
        except KeyboardInterrupt:
            event.set()

    def respond_master(self, event: threading.Event):
        while not event.is_set():
            try:
                self.notify()
            except ValueError:
                break

            time.sleep(self.timeout)
