# uASGI: A High-Performance ASGI Web Server

uASGI is a lightweight and efficient ASGI (Asynchronous Server Gateway Interface) web server for Python, designed for speed and flexibility. It supports both HTTP/1.1 and HTTP/2 protocols, with built-in SSL/TLS capabilities and a multiprocessing worker model for handling concurrent requests.

Inspired by the need for a simple yet powerful ASGI server, uASGI aims to provide a solid foundation for deploying asynchronous Python web applications.

## Features

*   **ASGI Specification Compliance**: Fully compatible with ASGI 2.0 and 3.0 applications (HTTP and Lifespan).
*   **HTTP/1.1 Support**: Robust handling of HTTP/1.1 requests using `httptools`.
*   **HTTP/2 Support**: Native HTTP/2 (H2) implementation using `h2` for improved performance and multiplexing.
*   **SSL/TLS**: Secure communication with built-in SSL context creation.
*   **Multiprocessing Workers**: Scale your application across multiple CPU cores with a configurable worker pool.
*   **Asynchronous I/O**: Built on `asyncio` and optimized with `uvloop` for high concurrency.
*   **Logging**: Configurable logging for server operations and access logs.

## Installation

uASGI requires Python 3.13 or later.

You can install uASGI and its dependencies using `pip`:

```bash
pip install uasgi
```

Alternatively, if you have `uv` installed (as indicated by `uv.lock`), you can install dependencies from the lock file:

```bash
uv sync
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
            "name": "Thanh",
            "age": 20,
            "address": "Vietnam"
        }

    return app


def main():
    enable_http2 = os.getenv('H2', 'false') == 'true'
    if enable_http2:
        print('Server is running with HTTP/2')
    else:
        print('Server is running with HTTP/1.1')

    run(
        app_factory=create_app, 
        host='127.0.0.1',
        port=5001,
        backlog=1024,
        workers=4,
        ssl_key_file='./certificates/server.key',
        ssl_cert_file='./certificates/server.crt',
        enable_h2=enable_http2,
        log_level='DEBUG',
    )


if __name__ == '__main__':
    main()
```

Then, run it from your terminal:

```bash
python example.py
```

This will start the server on `http://127.0.0.1:5001` with HTTP/1.1.

### Configuration Options

The `run` function accepts several parameters to configure the server:

*   `app_factory`: A callable that returns your ASGI application instance.
*   `host` (str): The host address to bind to (default: `'127.0.0.1'`).
*   `port` (int): The port to listen on (default: `5000`).
*   `backlog` (int): The maximum number of pending connections (default: `1024`).
*   `workers` (int, optional): The number of worker processes to spawn. If `None`, runs in a single process.
*   `ssl_cert_file` (str, optional): Path to the SSL certificate file.
*   `ssl_key_file` (str, optional): Path to the SSL key file.
*   `enable_h2` (bool): Enable HTTP/2 protocol (default: `False`). Requires SSL.
*   `log_level` (str): Set the logging level (`'DEBUG'`, `'INFO'`, `'WARNING'`, `'ERROR'`).

### Running with HTTP/2 and SSL

To enable HTTP/2, you must provide SSL certificate and key files. You can generate self-signed certificates for testing purposes.

1.  **Generate Certificates (for testing)**:
    ```bash
    mkdir -p certificates
    openssl req -x509 -newkey rsa:4096 -nodes -out certificates/server.crt -keyout certificates/server.key -days 365 -subj "/CN=localhost"
    ```

2.  **Run the server with HTTP/2 and SSL**:
    Set the `H2` environment variable to `true` and ensure `ssl_cert_file` and `ssl_key_file` are provided in your `run` call.

    ```bash
    H2=true python example.py
    ```
    Access your application via `https://127.0.0.1:5001`.

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