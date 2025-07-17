import os
import time
import socket
import errno
import asyncio
import logging
from typing import (
    TYPE_CHECKING,
    Callable,
    Optional,
    List,
    Tuple,
    Literal,
    Iterable,
    Dict,
    TypedDict,
    Coroutine,
)

if TYPE_CHECKING:
    from .config import Config


class ASGIInfo(TypedDict):
    version: str
    spec_version: str


class ASGIScope(TypedDict):
    asgi: ASGIInfo


ASGIHandler = Callable[[ASGIScope, Callable, Callable], Coroutine]


class HTTPScope(ASGIScope):
    type: Literal["http"]
    http_version: str
    method: bytes
    scheme: Optional[Literal["https", "http", "ws", "wss", None]]
    path: str
    raw_path: Optional[bytes]
    query_string: bytes
    root_path: Optional[str]
    headers: Iterable[Tuple[bytes, bytes]]
    client: Optional[Tuple[str, int]]
    server: Optional[Tuple[str, int]]
    state: Optional[Dict]


class HttpScopeRunner:
    __slots__ = (
        "scope",
        "app",
        "transport",
        "message_event",
        "on_response_complete",
        "body",
        "task",
        "more_body",
        "message_complete",
        "ready_write",
        "config",
        "access_logger",
        "status",
        "content_length",
    )

    def __init__(
        self,
        scope: "HTTPScope",
        app: "ASGIHandler",
        transport: asyncio.Transport,
        message_event: asyncio.Event,
        on_response_complete: Callable[[], None],
        message_complete: bool,
        ready_write: asyncio.Event,
        config: "Config",
        access_logger: logging.Logger,
    ) -> None:
        self.app = app
        self.transport = transport
        self.scope = scope
        self.message_event = message_event
        self.body = b""
        self.on_response_complete = on_response_complete
        self.task: asyncio.Task
        self.more_body: bool = False
        self.message_complete: bool = message_complete
        self.ready_write = ready_write
        self.config = config
        self.access_logger = access_logger
        self.status: int = 200
        self.content_length: int = 0

    def set_body(self, body: bytes):
        self.body += body
        self.message_event.set()

    def drain_body(self) -> bytes:
        drain = self.body
        self.body = b""
        self.message_event.clear()
        return drain

    async def run(self):
        start_time = time.perf_counter_ns()
        try:
            return await self.app(self.scope, self.receive, self.send)
        except asyncio.CancelledError:
            ...
        except OSError:
            ...
        finally:
            if not self.more_body:
                self.on_response_complete()
                if self.config.access_log:
                    response_time = (
                        time.perf_counter_ns() - start_time
                    ) / 1_000_000
                    log = '{} - {:.2f} "{} {} {}" {} {}'.format(
                        self.scope["client"][0],  # type: ignore
                        response_time,
                        self.scope["method"],
                        self.scope["path"],
                        self.scope["http_version"],
                        self.status,
                        self.content_length,
                    )
                    self.access_logger.info(log)

    async def receive(self):
        if self.scope["method"] in [b"GET"]:
            event = {
                "type": "http.request",
                "body": None,
                "more_body": not self.message_complete,
            }
            return event

        await self.message_event.wait()
        body = self.drain_body()
        event = {
            "type": "http.request",
            "body": body,
            "more_body": not self.message_complete,
        }
        return event

    async def send(self, event):
        _type = event["type"]

        if _type == "http.response.start":
            data = HttpScopeRunner.build_http_response_header(
                status=event["status"],
                http_version="1.1",
                headers=event["headers"],
            )
            self.status = event["status"]
            self.transport.write(data)

        elif _type == "http.response.body":
            body = event.get("body")
            more_body = event.get("more_body", False)
            self.more_body = more_body

            if body:
                self.transport.write(body)
                self.content_length += len(body)

        elif _type == "http.response.zerocopysend":
            file = event["file"]
            count = event.get("count")
            asyncio.create_task(self.sendfile(file, count))
            self.more_body = False

    async def sendfile(
        self,
        fd: int,
        count: Optional[int] = None,
    ):
        count = count or 512

        offset = 0
        fsize = os.fstat(fd).st_size

        s: socket.socket = self.transport.get_extra_info("socket")
        fd_out = s.fileno()

        while offset < fsize:
            remaining_bytes = fsize - offset
            count_to_send = min(count, remaining_bytes)

            if count_to_send == 0:
                break

            await self.ready_write.wait()
            try:
                bytes_to_sent = os.sendfile(fd_out, fd, offset, count_to_send)

                if bytes_to_sent == 0:
                    raise RuntimeError("Connection have been closed")
            except BlockingIOError as e:
                if e.errno != errno.EAGAIN:
                    raise
                await asyncio.sleep(0)

            else:
                offset += count_to_send

    @classmethod
    def build_http_response_header(
        cls,
        status: int,
        http_version: str,
        headers: List[Tuple[bytes, bytes]],
    ):
        phrase = STATUS_PHRASES.get(status, "Unknown")
        buffer = bytearray()
        buffer.extend(
            f"HTTP/{http_version} {status} {phrase}\r\n".encode("ascii")
        )

        for k, v in headers:
            buffer.extend(k)
            buffer.extend(b":")
            buffer.extend(v)
            buffer.extend(b"\r\n")
        buffer.extend(b"\r\n")

        return bytes(buffer)


STATUS_PHRASES = {
    # 1xx: Informational
    100: "Continue",
    101: "Switching Protocols",
    102: "Processing",
    103: "Early Hints",
    # 2xx: Success
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    207: "Multi-Status",
    208: "Already Reported",
    226: "IM Used",
    # 3xx: Redirection
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    # 4xx: Client Error
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Payload Too Large",
    414: "URI Too Long",
    415: "Unsupported Media Type",
    416: "Range Not Satisfiable",
    417: "Expectation Failed",
    418: "I'm a teapot",
    421: "Misdirected Request",
    422: "Unprocessable Entity",
    423: "Locked",
    424: "Failed Dependency",
    425: "Too Early",
    426: "Upgrade Required",
    428: "Precondition Required",
    429: "Too Many Requests",
    431: "Request Header Fields Too Large",
    451: "Unavailable For Legal Reasons",
    # 5xx: Server Error
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported",
    506: "Variant Also Negotiates",
    507: "Insufficient Storage",
    508: "Loop Detected",
    510: "Not Extended",
    511: "Network Authentication Required",
}
