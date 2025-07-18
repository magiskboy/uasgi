import asyncio
import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
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

    @app.get('/stream')
    async def stream():

        async def gen():
            for i in range(100):
                await asyncio.sleep(1)
                yield str(i).encode("utf-8")

        return StreamingResponse(content=gen())

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
        workers=4,
        log_level='DEBUG',
    )


if __name__ == '__main__':
    main()

