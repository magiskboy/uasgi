from __future__ import annotations

from typing import Optional
import click

from .main import run as _run
from .utils import LOG_LEVEL


cli = click.Group(name="uasgi", help="A High-Performance ASGI Web Server")


@cli.command()
@click.argument(
    "app",
    type=str,
    # help="The ASGI application to run (e.g., 'main:app')."
)
@click.option(
    "--host",
    type=str,
    default="127.0.0.1",
    show_default=True,
    help="The host IP address to bind to.",
)
@click.option(
    "--port",
    type=int,
    default=5000,
    show_default=True,
    help="The port to listen on.",
)
@click.option(
    "--backlog",
    type=int,
    default=1024,
    show_default=True,
    help="The maximum number of pending connections.",
)
@click.option(
    "--workers",
    type=int,
    default=1,
    help="The number of worker processes to use. Defaults to 1 worker.",
)
@click.option(
    "--ssl-cert-file",
    type=click.Path(exists=True, dir_okay=False),
    help="The path to the SSL certificate file (.pem).",
)
@click.option(
    "--ssl-key-file",
    type=click.Path(exists=True, dir_okay=False),
    help="The path to the SSL key file (.pem).",
)
@click.option(
    "--log-level",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=True
    ),
    default="INFO",
    show_default=True,
    help="The logging level.",
)
@click.option(
    "--access-log/--no-access-log",
    is_flag=True,
    default=True,
    show_default=True,
    help="Enable/disable access logging.",
)
@click.option(
    "--lifespan/--no-lifespan",
    is_flag=True,
    default=True,
    show_default=True,
    help="Enable/disable ASGI lifespan protocol.",
)
@click.option(
    "--reload/--no-reload",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable/disable auto reload.",
)
def run(
    app: str,
    host: str,
    port: int,
    backlog: Optional[int],
    workers: Optional[int],
    ssl_cert_file: Optional[str],
    ssl_key_file: Optional[str],
    log_level: LOG_LEVEL,
    access_log: bool,
    lifespan: bool,
    reload: Optional[bool],
):
    _run(
        app=app,
        host=host,
        port=port,
        backlog=backlog,
        workers=workers,
        ssl_key_file=ssl_key_file,
        ssl_cert_file=ssl_cert_file,
        log_level=log_level,
        access_log=access_log,
        lifespan=lifespan,
        reload=reload,
    )
