import asyncio
import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
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
    async def app(scope, receive, send):
        if scope['type'] == 'http':
            fd = os.open('/Users/nkthanh/Downloads/512KB-min.json', os.O_RDONLY | os.O_NONBLOCK, 0o777)
            fsize = os.fstat(fd).st_size
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [(b'Content-Length', str(fsize).encode('ascii'))]
            })

            await send({
                'type': 'http.response.zerocopysend',
                'file': fd,
                'count': 512,
            })

    return app
    app = FastAPI(
        lifespan=lifespan,
    )

    @app.get('/')
    async def index(request: Request):
        return {
            "name": "Thanh",
            "age": 20,
            "address": "Vietnam",
            "state.property": request.state.property,
        }

    @app.get('/stream')
    async def stream():

        async def gen():
            for i in range(100):
                await asyncio.sleep(1)
                yield str(i).encode("utf-8")

        return StreamingResponse(content=gen())

    @app.get('/files')
    async def file():
        return FileResponse('/Users/nkthanh/Downloads/512KB-min.json')

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
        # ssl_cert_file='/tmp/certificates/server.crt',
        # ssl_key_file='/tmp/certificates/server.key',
    )


if __name__ == '__main__':
    main()

