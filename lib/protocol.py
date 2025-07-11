import os
from typing import cast
import asyncio
from urllib.parse import urlparse
import socket

import httptools

from .types import ASGIHandler


class HTTPProtocol(asyncio.Protocol):
    def __init__(self, app):
        self.app = app

        self.parser = httptools.HttpRequestParser(self) #type: ignore

        self.url = None
        self.headers = []
        self.method = None
        self.http_version = None
        self.transport: asyncio.Transport
        
        self.body_queue = asyncio.Queue()
        self.task = None

        self.loop = asyncio.get_running_loop()

        self.client = None
        self.server = None

        self.scope = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.Transport, transport)
        self.server = cast(socket.socket, transport.get_extra_info('socket')).getsockname()
        self.client = transport.get_extra_info('peername')
        self.ssl = transport.get_extra_info("sslcontext")

        return super().connection_made(transport)

    def connection_lost(self, exc: Exception | None) -> None:
        if self.task and not self.task.done():
            self.task.cancel('Lost connection')

    def data_received(self, data: bytes) -> None:
        self.parser.feed_data(data)

    def eof_received(self) -> bool | None:
        return super().eof_received()

    # -------------------- for parser ------------------------
    def on_url(self, url: bytes):
        self.url = url

    def on_header(self, name: bytes, value: bytes):
        self.headers.append((name, value))

    def on_headers_complete(self):
        self.method = self.parser.get_method()
        self.http_version = self.parser.get_http_version()

        scope = self.make_scope()
        cycle = RequestLifeCycle(scope, self.app, self.transport.write)
        task = asyncio.create_task(cycle.run())
        task.add_done_callback(self.on_done)
        self.task = task

    def on_body(self, body: bytes):
        self.loop.create_task(self.body_queue.put(body))

    # ---------------- Extra ---------------------
    def on_done(self, _: asyncio.Task):
        if not self.parser.should_keep_alive():
            self.transport.close()

    def make_scope(self):
        url_o = urlparse(cast(bytes, self.url).decode('utf-8'))
        is_ssl = self.ssl is not None
        scope = {
            "type": "http",
            "asgi": {
                "version": "1.0.0",
                "spec_version": "1.0.0",
            },
            "http_version": cast(str, self.http_version),
            "method": cast(bytes, self.method).decode("utf-8"),
            "schema": 'https' if is_ssl else 'http',
            "path": url_o.path,
            "raw_path": self.url,
            "query_string": url_o.query.encode("utf-8"),
            "root_path": os.getcwd(),
            "headers": self.headers,
            "client": self.client,
            "server": self.server,
            "state": None
        }

        return scope


class RequestLifeCycle:
    CLF = b"\r\n"

    def __init__(self, scope, app: ASGIHandler, writer) -> None:
        self.app = app
        self.request_event = asyncio.Queue()
        self.writer = writer
        self.scope = scope
        self.receivable = self.make_receivable()

    async def run(self):
        try:
            return await self.app(self.scope, self.receive, self.send)
        except asyncio.CancelledError:
            ...

    async def receive(self):
        return await self.receivable.asend(None)

    async def send(self, event):
        _type = event['type']
        http_version = self.scope['http_version']

        if _type == 'http.response.start':
            status = event['status']
            headers = event['headers']

            buffer = bytearray()
            buffer.extend(f"HTTP/{http_version} {status}\r\n".encode("utf-8"))
            for k, v in headers:
                buffer.extend(k)
                buffer.extend(b":")
                buffer.extend(v)
                buffer.extend(self.CLF)
            buffer.extend(self.CLF)
            self.writer(bytes(buffer))

        elif _type == 'http.response.body':
            body = event.get("body", b"")
            self.writer(body)

    async def make_receivable(self):
        while True:
            if not self.request_event.empty():
                chunk = await self.request_event.get()
                more = chunk[:-2] != "\n\n"
                yield {
                    "type": "http.request",
                    "body": chunk,
                    "more_body": more,
                }
