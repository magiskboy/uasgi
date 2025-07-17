from __future__ import annotations

import sys
import ssl
import asyncio
import logging
from typing import TYPE_CHECKING, Literal, Optional, cast
import importlib


if TYPE_CHECKING:
    from .uhttp import ASGIHandler


LOG_LEVEL = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


def create_ssl_context(
    certfile_path: str, keyfile_path: str, password=None
) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    context.load_cert_chain(
        certfile=certfile_path, keyfile=keyfile_path, password=password
    )

    context.minimum_version = ssl.TLSVersion.TLSv1_2

    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE

    context.set_ciphers(
        "ECDHE+AESGCM:CHACHA20:DHE+AESGCM:!RC4:!aNULL:!eNULL:!LOW:!3DES:!MD5:!EXP:!PSK:!SRP:!DSS:!CAMELLIA:!SEED"
    )

    return context


DEFAULT_LOG_FMT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def create_logger(
    name: str,
    log_level: LOG_LEVEL,
    log_fmt: Optional[str] = DEFAULT_LOG_FMT,
):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if not log_fmt:
        log_fmt = DEFAULT_LOG_FMT

    if log_level in {"WARNING", "ERROR"}:
        handler = logging.StreamHandler(sys.stderr)

    else:
        handler = logging.StreamHandler(sys.stdout)

    fmt = logging.Formatter(log_fmt)
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


def import_string(str_import: str) -> "ASGIHandler":
    try:
        module_str, instance_str = str_import.split(":")
    except ValueError as e:
        raise ImportError(
            "Import string must be <module path>:<attribute name> format"
        ) from e

    module = importlib.import_module(module_str)
    instance = getattr(module, instance_str)

    if instance is None:
        raise ImportError(f"{instance_str} is not in {module_str}")

    return instance


def load_app(app) -> "ASGIHandler":
    if isinstance(app, str):
        return import_string(app)

    if callable(app):
        if asyncio.iscoroutinefunction(app):
            return app

        return cast("ASGIHandler", app())

    raise ImportError("Cannot load app")
