from fastapi import FastAPI
from lib import run


def create_app():
    app = FastAPI()

    @app.get('/')
    async def index():
        return {
            "name": "Thanh",
            "age": 20,
            "address": "Vietnam"
        }
        
    return app


def main():
    run(create_app, port=5001, workers=4)


if __name__ == '__main__':
    main()
