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

