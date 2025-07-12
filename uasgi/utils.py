from __future__ import annotations

import sys
import ssl
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import LOG_LEVEL


def create_ssl_context(certfile_path: str, keyfile_path: str, password = None) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    context.load_cert_chain(certfile=certfile_path, keyfile=keyfile_path, password=password)

    context.minimum_version = ssl.TLSVersion.TLSv1_2

    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE

    context.set_ciphers('ECDHE+AESGCM:CHACHA20:DHE+AESGCM:!RC4:!aNULL:!eNULL:!LOW:!3DES:!MD5:!EXP:!PSK:!SRP:!DSS:!CAMELLIA:!SEED')

    return context


def create_logger(name: str, log_level: LOG_LEVEL):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if log_level == 'WARNING' or log_level == 'ERROR':
        handler = logging.StreamHandler(sys.stderr)
    else:
        handler = logging.StreamHandler(sys.stdout)

    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger

