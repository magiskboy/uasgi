from __future__ import annotations

from typing import Optional, Literal, Tuple, Iterable, Dict, TypedDict, Callable, Coroutine


LOG_LEVEL = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']


class ASGIInfo(TypedDict):
    version: str
    spec_version: str


class ASGIScope(TypedDict):
    type: Literal["http", "websocket", "lifespan"]
    asgi: ASGIInfo
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


ASGIHandler = Callable[[ASGIScope, Callable, Callable], Coroutine]

