import os
import typing
import socket


class ASGIInfo(typing.TypedDict):
    version: str
    spec_version: str


class ASGIScope(typing.TypedDict):
    type: typing.Literal["http", "websocket"]
    asgi: ASGIInfo
    http_version: str
    method: bytes
    schema: typing.Literal["https", "http", "ws", "wss"]
    path: bytes
    raw_path: bytes
    query_string: bytes
    root_path: str
    headers: typing.Iterable[typing.Tuple[bytes, bytes]]
    client: typing.Tuple[str, int]
    server: typing.Tuple[str, int]
    state: typing.Optional[typing.Dict]


ASGIHandler = typing.Callable[[typing.Dict, typing.Callable, typing.Callable], typing.Coroutine]


class Config:
    def __init__(
        self,
        host=None,
        port=None,
        sock=None,
        backlog=None,
        workers=None,
        threaded=False,
    ):
        self.host = host
        self.port = port
        self.sock = sock
        self.backlog = backlog
        self.workers = workers
        self.threaded = threaded

    def create_socket(self):
        if self.sock is None:
            host = self.host or '127.0.0.1'
            port = self.port or 5000
            self.sock = socket.create_server(
                address=(host, port),
                family=socket.AF_INET,
                backlog=4096,
                reuse_port=True,
            )

        if self.workers:
            os.set_inheritable(self.sock.fileno(), True)

        return self.sock

    @property
    def socket(self) -> socket.socket:
        return self.sock #type: ignore
