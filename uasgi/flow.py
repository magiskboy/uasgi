import asyncio


class FlowControl:
    def __init__(self):
        self._pause_writing = asyncio.Event()
        self._pause_reading = asyncio.Event()

    def pause_writing(self):
        self._pause_writing.set()

    async def wait_write(self):
        await self._pause_writing.wait()
