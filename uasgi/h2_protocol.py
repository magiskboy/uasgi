from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple
import urllib.parse

import h2.config
import h2.connection
import h2.exceptions
import h2.events
import h2.settings
import h2.errors
import hpack
import httptools

if TYPE_CHECKING:
    from .server import ServerState
    from .uhttp import ASGIHandler


class H2Protocol(asyncio.Protocol):
    def __init__(self, app, server_state: "ServerState"):
        # global scope
        self.app: "ASGIHandler" = app
        self.tasks: Set[asyncio.Task] = server_state.tasks
        self.connections: Set[asyncio.Protocol] = server_state.connections
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self.root_path = server_state.root_path
        self.lifespan = server_state.lifespan

        # connection scope
        config = h2.config.H2Configuration(client_side=False)
        self.h2conn = h2.connection.H2Connection(config)
        self.streams: Dict[int, "AppRunner"] = dict()
        self.client: Tuple[str, int]
        self.server: Tuple[str, int]
        self.transport: asyncio.Transport

    def connection_made(self, transport: asyncio.Transport) -> None:  # type:ignore
        self.transport = transport
        self.h2conn.initiate_connection()
        self.transport.write(self.h2conn.data_to_send())
        self.connections.add(self)

        self.server = transport.get_extra_info("socket").getsockname()
        self.client = transport.get_extra_info("peername")

    def data_received(self, data: bytes) -> None:
        try:
            events = self.h2conn.receive_data(data)

        except h2.exceptions.ProtocolError:
            self.transport.write(self.h2conn.data_to_send())
            self.transport.close()
        except Exception:
            self.transport.close()

        else:
            self.transport.write(self.h2conn.data_to_send())

            for event in events:
                if isinstance(event, h2.events.RequestReceived):
                    self.request_received(event.headers, event.stream_id)  # type:ignore

                elif isinstance(event, h2.events.DataReceived):
                    self.receive_data(event.data, event.stream_id)  # type:ignore

                elif isinstance(event, h2.events.StreamEnded):
                    self.stream_complete(event.stream_id)  # type:ignore

                elif isinstance(event, h2.events.ConnectionTerminated):
                    self.transport.close()

                elif isinstance(event, h2.events.StreamReset):
                    self.stream_reset(event.stream_id)  # type:ignore

                elif isinstance(event, h2.events.WindowUpdated):
                    self.window_updated(event.stream_id, event.delta)

                elif isinstance(event, h2.events.RemoteSettingsChanged):
                    if (
                        h2.settings.SettingCodes.INITIAL_WINDOW_SIZE
                        in event.changed_settings
                    ):
                        self.window_updated(None, 0)

                self.transport.write(self.h2conn.data_to_send())

    def request_received(
        self, headers: List[hpack.HeaderTuple] | None, stream_id: int
    ):
        d = dict(headers)  # type: ignore
        url = d[b":scheme"] + b"://" + d[b":authority"] + d[b":path"]
        parsed_url = httptools.parse_url(url)  # type: ignore
        raw_path = parsed_url.path
        path = raw_path.decode("ascii")
        if "%" in path:
            path = urllib.parse.unquote(path)

        # Store off the request data.
        scope = {
            "type": "http",
            "asgi": {
                "version": "2.5",
                "spec_version": "2.0",
            },
            "http_version": "2",
            "method": d[b":method"].decode("ascii"),
            "scheme": "https",
            "path": path,
            "raw_path": raw_path,
            "query_string": parsed_url.query or b"",
            "root_path": self.root_path,
            "headers": headers,
            "client": self.client,
            "server": self.server,
            "state": self.lifespan.app_state,
        }
        runner = AppRunner(
            scope=scope,
            app=self.app,
            message_event=asyncio.Event(),
            protocol=self,
            stream_id=stream_id,
        )
        self.streams[stream_id] = runner
        task = asyncio.create_task(runner.run())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        runner.task = task

    def receive_data(self, data: bytes | None, stream_id: int):
        if not data:
            return

        runner = self.streams[stream_id]
        runner.body += data
        runner.message_event.set()

    def stream_complete(self, stream_id: int):
        self.streams.pop(stream_id)

    def stream_reset(self, stream_id: int):
        runner = self.streams[stream_id]
        if runner.flow_control:
            runner.flow_control.cancel()
            runner.flow_control = None

    def window_updated(self, stream_id: int | None, delta: int | None):
        if stream_id and stream_id in self.streams:
            runner = self.streams[stream_id]
            f = runner.flow_control
            f.set_result(delta)  # type: ignore

        elif not stream_id:
            for runner in self.streams.values():
                if runner.flow_control:
                    runner.flow_control.set_result(delta)
                    runner.flow_control = None

    async def send_data(self, data: bytes, stream_id: int):
        while data:
            while self.h2conn.local_flow_control_window(stream_id) < 1:
                try:
                    await self.wait_for_flow_control(stream_id)
                except asyncio.CancelledError:
                    return data

            chunk_size = min(
                self.h2conn.local_flow_control_window(stream_id),
                len(data),
                self.h2conn.max_outbound_frame_size,
            )

            try:
                self.h2conn.send_data(
                    stream_id,
                    data[:chunk_size],
                    end_stream=(chunk_size == len(data)),
                )
            except (
                h2.exceptions.StreamClosedError,
                h2.exceptions.ProtocolError,
            ):
                break

            self.transport.write(self.h2conn.data_to_send())
            data = data[chunk_size:]

    async def wait_for_flow_control(self, stream_id):
        f = asyncio.Future()
        self.streams[stream_id].flow_control = f
        await f


class AppRunner:
    __slots__ = (
        "scope",
        "app",
        "message_event",
        "body",
        "protocol",
        "stream_id",
        "task",
        "flow_control",
    )

    def __init__(
        self,
        scope,
        app: "ASGIHandler",
        message_event: asyncio.Event,
        protocol: H2Protocol,
        stream_id: int,
    ) -> None:
        self.scope = scope
        self.app = app
        self.message_event = message_event
        self.body = b""
        self.protocol = protocol
        self.stream_id = stream_id
        self.task: asyncio.Task
        self.flow_control: Optional[asyncio.Future] = None

    async def run(self):
        try:
            return await self.app(self.scope, self.receive, self.send)
        except asyncio.CancelledError:
            ...

    async def receive(self):
        await self.message_event.wait()
        self.message_event.clear()
        event = {
            "type": "http.request",
            "body": self.body,
        }
        self.body = b""
        return event

    async def send(self, event):
        _type = event["type"]

        if _type == "http.response.start":
            data = [
                (b":status", str(event["status"]).encode("ascii")),
                *event["headers"],
            ]

            await self.send_headers(data)

        elif _type == "http.response.body":
            body = event.get("body")
            if body:
                await self.send_body(body)

    async def send_headers(self, headers: List[Tuple[bytes, bytes]]):
        try:
            self.protocol.h2conn.send_headers(self.stream_id, headers)
        except h2.exceptions.ProtocolError:
            if self.task:
                self.task.cancel("Error when sending headers")

    async def send_body(self, data: bytes):
        await self.protocol.send_data(data, self.stream_id)
