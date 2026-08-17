from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, SessionLocal
from api import api_router
from greeter import Greeter

app = FastAPI(
    title='Main Application',
    description='This is the main application.',
    version='1.0.0',
    contact={
        'name': 'Your Name',
        'email': 'your@email.com'
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router)

def main() -> None:
    greeter = Greeter()
    print(greeter.greet())
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)

if __name__ == '__main__':
    main()
