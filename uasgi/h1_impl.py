from __future__ import annotations

from typing import TYPE_CHECKING, List, Literal, Optional, Set, Tuple
import asyncio
import urllib.parse
from collections import deque

import httptools

from .types import ASGIScope
from .http import build_http_response_header


if TYPE_CHECKING:
    from .server import ServerState
    from .types import ASGIHandler


class H1Connection(asyncio.Protocol):
    def __init__(self, app, server_state: "ServerState"):
        # global scope
        self.app: "ASGIHandler" = app
        self.tasks: Set[asyncio.Task] = server_state.tasks
        self.connections: Set[asyncio.Protocol] = server_state.connections
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self.server_state = server_state

        # connection scope
        self.parser: httptools.HttpRequestParser = httptools.HttpRequestParser(self) #type: ignore
        self.parser.set_dangerous_leniencies(lenient_data_after_close=True)
        self.client: Tuple[str, int]
        self.server: Tuple[str, int]
        self.transport: asyncio.Transport
        self.pipeline: deque["AppRunner"] = deque()

        # request state
        self.url: bytes
        self.scope: ASGIScope
        self.scheme: Optional[Literal["https", "http", "ws", "wss"]]
        self.headers: List[Tuple[bytes, bytes]]
        self.current_runner: Optional["AppRunner"] = None

    def connection_made(self, transport: asyncio.Transport) -> None: #type:ignore
        self.transport = transport
        self.server = transport.get_extra_info('socket').getsockname()
        self.client = transport.get_extra_info('peername')
        self.ssl = transport.get_extra_info("sslcontext")
        if self.ssl:
            self.scheme = "https"
        else:
            self.scheme = "http"

    def connection_lost(self, exc: Exception | None) -> None:
        self.connections.discard(self)

    def data_received(self, data: bytes) -> None:
        self.parser.feed_data(data)

    # -------------------- for parser ------------------------
    def on_url(self, url: bytes):
        self.url += url

    def on_message_begin(self):
        self.url = b""
        self.headers = []

        self.scope = {
            "method": b"",
            "query_string": b"",
            "path": "",
            "type": "http",
            "asgi": {
                "version": "2.5",
                "spec_version": "2.0",
            },
            "raw_path": None,
            "scheme": self.scheme,
            "http_version": "1.1",
            "root_path": self.server_state.root_path,
            "headers": self.headers,
            "client": self.client,
            "server": self.server,
            "state": None
        }

    def on_header(self, name: bytes, value: bytes):
        self.headers.append((name, value))

    def on_headers_complete(self):
        parsed_url = httptools.parse_url(self.url) #type: ignore
        raw_path = parsed_url.path
        path = raw_path.decode("ascii")
        if "%" in path:
            path = urllib.parse.unquote(path)

        self.scope["method"] = self.parser.get_method().decode("ascii")
        self.scope["path"] = path
        self.scope["raw_path"] = raw_path
        self.scope["query_string"] = parsed_url.query or b""

        runner = AppRunner(
            scope=self.scope,
            app=self.app,
            transport=self.transport,
            message_event=asyncio.Event(),
            on_response_complete=self.on_response_complete,
        )

        if self.current_runner:
            self.pipeline.appendleft(runner)
        else:
            self.current_runner = runner
            self.schedule_runner(runner)

    def schedule_runner(self, runner: "AppRunner"):
        task = asyncio.create_task(runner.run())
        runner.task = task
        task.add_done_callback(self.tasks.discard)
        self.tasks.add(task)

    def on_response_complete(self):
        self.current_runner = None

        if self.pipeline:
            runner = self.pipeline.pop()
            self.schedule_runner(runner)

    def on_body(self, body: bytes):
        if self.current_runner:
            self.current_runner.set_body(body)


class AppRunner:
    __slots__ = (
        'scope',
        'app',
        'transport',
        'message_event',
        'on_response_complete',
        'body',
        'task',
    )

    def __init__(
        self,
        scope,
        app: "ASGIHandler",
        transport: asyncio.Transport,
        message_event: asyncio.Event,
        on_response_complete,
    ) -> None:
        self.app = app
        self.transport = transport
        self.scope = scope
        self.message_event = message_event
        self.body = b""
        self.on_response_complete = on_response_complete
        self.task: asyncio.Task

    def set_body(self, body: bytes):
        self.body += body
        self.message_event.set()

    def drain_body(self) -> bytes:
        drain = self.body
        self.body = b""
        self.message_event.clear()
        return drain

    async def run(self):
        try:
            # start lifespan
            return await self.app(self.scope, self.receive, self.send)
            # end lifespan
        except asyncio.CancelledError:
            ...
        finally:
            self.on_response_complete()

    async def receive(self):
        await self.message_event.wait()
        body = self.drain_body()
        event = {
            "type": "http.request",
            "body": body,
        }
        return event

    async def send(self, event):
        _type = event['type']

        if _type == 'http.response.start':
            data = build_http_response_header(
                status=event['status'],
                http_version='1.1',
                headers=event['headers'],
            )
            self.transport.write(data)

        elif _type == 'http.response.body':
            body = event.get("body")
            if body:
                self.transport.write(body)

