# uASGI: A High-Performance ASGI Web Server

uASGI is a lightweight and efficient ASGI (Asynchronous Server Gateway Interface) web server for Python, designed for speed and flexibility. It supports only HTTP/1.1 protocols, with built-in SSL/TLS capabilities and a multiprocessing worker model for handling concurrent requests.

Inspired by the need for a simple yet powerful ASGI server, uASGI aims to provide a solid foundation for deploying asynchronous Python web applications.

## Features

*   **ASGI Specification Compliance**: Fully compatible with ASGI 2.0 and 3.0 applications (HTTP and Lifespan).
*   **HTTP/1.1 Support**: Robust handling of HTTP/1.1 requests using `httptools`.
*   **Multiprocessing Workers**: Scale your application across multiple CPU cores with a configurable worker pool.
*   **Asynchronous I/O**: Built on `asyncio` and optimized with `uvloop` for high concurrency.

## Installation

uASGI requires Python 3.10 or later.

You can install uASGI and its dependencies using `pip` or `uv`

```bash
pip install uasgi
uv add uasgi
```

## Usage

### Running a Simple ASGI Application

Here's how you can run a basic FastAPI application with uASGI.

First, create an ASGI application in `main.py`

```python
async def app(scope, receive, send):
    assert scope['type'] == 'http'

    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/plain'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': b'Hello, world!',
    })
```

Then, run it from your terminal:

```bash
$ uasgi run main:app
```

Or you can run via gunicorn

```bash
$ gunicorn main:app --worker-class 'uasgi.UASGIWorker.UASGIWorker'
```

This will start the server on `http://127.0.0.1:5000`.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

