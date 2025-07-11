from .types import Config
from .server import Server


def run(
    app_factory,
    host='127.0.0.1',
    port=5000,
    backlog=1024,
    workers=None,
    threaded=False,
):
    config = Config(
        host=host,
        port=port,
        backlog=backlog,
        workers=workers,
        threaded=threaded,
    )
    config.create_socket()

    server = Server(app_factory, config)
    server.run()
