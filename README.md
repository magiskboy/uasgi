# uASGI: A High-Performance ASGI Web Server

uASGI is a lightweight and efficient ASGI (Asynchronous Server Gateway Interface) web server for Python, designed for speed and flexibility. It supports only HTTP/1.1 protocols, with built-in SSL/TLS capabilities and a multiprocessing worker model for handling concurrent requests.

Inspired by the need for a simple yet powerful ASGI server, uASGI aims to provide a solid foundation for deploying asynchronous Python web applications.

## Features

*   **ASGI Specification Compliance**: Fully compatible with ASGI 2.0 and 3.0 applications (HTTP and Lifespan).
*   **HTTP/1.1 Support**: Robust handling of HTTP/1.1 requests using `httptools`.
*   **SSL/TLS**: Secure communication with built-in SSL context creation.
*   **Multiprocessing Workers**: Scale your application across multiple CPU cores with a configurable worker pool.
*   **Asynchronous I/O**: Built on `asyncio` and optimized with `uvloop` for high concurrency.

## Installation

uASGI requires Python 3.13 or later.

You can install uASGI and its dependencies using `pip` or `uv`

```bash
pip install uasgi
uv add uasgi
```

## Usage

### Running a Simple ASGI Application

Here's how you can run a basic FastAPI application with uASGI.

First, create an `example.py` (or similar) file:

```python
import os
from fastapi import FastAPI
from uasgi import run, create_logger
from contextlib import asynccontextmanager

logger = create_logger('app', 'INFO')

@asynccontextmanager
async def lifespan(_):
    logger.info('Application is starting...')
    yield {
        'property': 'value'
    }
    logger.info('Application is shutdown...')


def create_app():
    app = FastAPI(
        lifespan=lifespan,
    )

    @app.get('/')
    async def index():
        return {
            "Hello": "World"
        }

    return app


def main():
    run(
        app_factory=create_app, 
    )


if __name__ == '__main__':
    main()
```

Then, run it from your terminal:

```bash
python example.py
```

This will start the server on `http://127.0.0.1:5000` with HTTP/1.1.

### Configuration Options

The `run` function accepts several parameters to configure the server:

*   `app_factory`: A callable that returns your ASGI application instance.
*   `host` (str): The host address to bind to (default: `'127.0.0.1'`).
*   `port` (int): The port to listen on (default: `5000`).
*   `backlog` (int): The maximum number of pending connections (default: `1024`).
*   `workers` (int, optional): The number of worker processes to spawn. If `None`, runs in a single process.
*   `ssl_cert_file` (str, optional): Path to the SSL certificate file.
*   `ssl_key_file` (str, optional): Path to the SSL key file.
*   `log_level` (str): Set the logging level (`'DEBUG'`, `'INFO'`, `'WARNING'`, `'ERROR'`).

## Development

To set up the development environment:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/uasgi.git
    cd uasgi
    ```
2.  **Install dependencies**:
    ```bash
    uv sync # or pip install -e .
    ```

## Contributing

Contributions are welcome! Please see the `CONTRIBUTING.md` (to be created) for guidelines.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
