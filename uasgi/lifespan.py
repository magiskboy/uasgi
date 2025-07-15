from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Dict, Literal, TypedDict

if TYPE_CHECKING:
    from uasgi.types import ASGIInfo


class LifespanScope(TypedDict):
    type: Literal["lifespan"]
    asgi: "ASGIInfo"
    state: Dict


class Lifespan:
    def __init__(self, app):
        self.app = app
        self.app_state = dict()
        self.event_queue = asyncio.Queue()
        self.scope: LifespanScope = {
            "type": "lifespan",
            "asgi": {
                "version": "2.5",
                "spec_version": "2.0"
            },
            "state": self.app_state,
        }
        self.startup_done = asyncio.Event()
        self.shutdown_done = asyncio.Event()
        self.shutdown_complete = True
        self.startup_complete = True
        self.message = None

    async def startup(self):
        await self.event_queue.put({"type": "lifespan.startup"})
        asyncio.create_task(self.main())

        await self.startup_done.wait()

        if not self.startup_complete:
            raise RuntimeError(self.message or 'Lifespan startup failed')

    async def send(self, event):
        _type = event['type']
        
        if _type == 'lifespan.startup.complete':
            self.startup_done.set()
        elif _type == 'lifespan.startup.failed':
            self.startup_done.set()
            self.startup_complete = False
            self.message = event["message"]
        elif _type == 'lifespan.shutdown.complete':
            self.shutdown_done.set()
        elif _type == 'lifespan.shutdown.failed':
            self.shutdown_done.set()
            self.shutdown_complete = False
            self.message = event["message"]
        else:
            raise RuntimeError(f'Event {_type} is invalid')

    async def receive(self):
        return await self.event_queue.get()

    async def main(self):
        try:
            await self.app(self.scope, self.receive, self.send)

        except Exception:
            ...

    async def shutdown(self):
        await self.event_queue.put({"type": "lifespan.shutdown"})
        await self.shutdown_done.wait()

        if not self.shutdown_complete:
            raise RuntimeError(self.message or "Lifespan shutdown failed")

