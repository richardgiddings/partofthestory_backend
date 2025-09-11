from fastapi import FastAPI, Header, HTTPException, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from starlette import status
from decouple import config
import time

from models import *
from auth import *
from database import SessionDep, get_session, create_db_and_tables

# pagination imports
from fastapi_pagination import add_pagination, paginate
from fastapi_pagination.links import Page as BasePage
from fastapi_pagination.customization import UseParamsFields, CustomizedPage
from fastapi_pagination.utils import disable_installed_extensions_check


# pagination setup
PAGE_SIZE = config('PAGE_SIZE', default=15, cast=int)
Page = CustomizedPage[
    BasePage,
    UseParamsFields(
        size=Query(PAGE_SIZE, ge=0),
    ),
]
add_pagination(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # set this once we are no longer testing locally
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add Session middleware
app.add_middleware(SessionMiddleware, secret_key=config("SECRET_KEY"))


@app.on_event('startup')
def on_startup():
    create_db_and_tables()

# # Logging time taken for each api request
@app.middleware("http")
async def log_response_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    print(f"Request: {request.url.path} completed in {process_time:.4f} seconds")
    return response 

app.include_router(router)

@app.get("/home")
async def get_response(current_user: dict = Depends(get_current_user)):
    return {"message": "Welcome!", "user": current_user}

# GET - random completed story
#@app.get('/random_story/')

# GET - a user's stories
#@app.get('/user_stories/')

# GET - a random available part
#@app.get('/available_part/')

# PATCH - assign/unnasign a part to/from a user


# POST - a completed part (pending moderation)

