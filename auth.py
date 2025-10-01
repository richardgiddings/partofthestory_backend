from fastapi import FastAPI, Depends, HTTPException, status, Request, Cookie, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Annotated
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timedelta
from jose import jwt, ExpiredSignatureError, JWTError
from decouple import config
import uuid
import traceback
import requests

from sqlmodel import select, Session
from models import Users

from database import SessionDep, get_session, engine

# App Configuration
app = FastAPI()
router = APIRouter()

# Token expiry from env
TOKEN_EXPIRY_IN_MINUTES = config('TOKEN_EXPIRY_IN_MINUTES', default=60, cast=int)

# OAuth Setup
oauth = OAuth()
oauth.register(
    name="auth",
    client_id=config("GOOGLE_CLIENT_ID"),
    client_secret=config("GOOGLE_CLIENT_SECRET"),
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    authorize_params=None,
    access_token_url="https://accounts.google.com/o/oauth2/token",
    access_token_params=None,
    refresh_token_url=None,
    authorize_state=config("SECRET_KEY"),
    redirect_uri=config("REDIRECT_URL"),
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    client_kwargs={"scope": "openid profile email"},
)

# JWT Configurations
JWT_SECRET_KEY = config("JWT_SECRET_KEY")
ALGORITHM = "HS256"

"""
Get the currently logged in user
"""
def get_current_user(access_token: Annotated[str | None, Cookie()] = None):

    print("Getting current user from token...")

    if not access_token:
        print("No access token found in cookies.")
        raise HTTPException(status_code=401, detail="Not authenticated")

    print("Access token found, decoding...")

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(access_token, JWT_SECRET_KEY, algorithms=[ALGORITHM])

        print("Token decoded successfully.")

        user_id: str = payload.get("sub")
        user_name: str = payload.get("user_name")

        if user_id is None or user_name is None:
            raise credentials_exception

        return {"user_id": user_id, "user_name": user_name}

    except ExpiredSignatureError:
        # Specifically handle expired tokens
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please login again.")
    except JWTError:
        # Handle other JWT-related errors
        traceback.print_exc()
        raise credentials_exception
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=401, detail="Not Authenticated")


"""
Login using Google authentication
"""
@router.get("/login")
async def login(request: Request):
    request.session.clear()
    referer = request.headers.get("referer")
    frontend_url = config("FRONTEND_URL")
    redirect_url = config("REDIRECT_URL")
    request.session["login_redirect"] = frontend_url 

    return await oauth.auth.authorize_redirect(request, redirect_url, prompt="consent")

@router.route("/auth")
async def auth(request: Request):
    try:
        token = await oauth.auth.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Google authentication failed.")

    try:
        user_info_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f'Bearer {token["access_token"]}'}
        google_response = requests.get(user_info_endpoint, headers=headers)
        user_info = google_response.json()
    except Exception as e:
        raise HTTPException(status_code=401, detail="Google authentication failed.")

    user = token.get("userinfo")
    expires_in = token.get("expires_in")
    user_id = user.get("sub")
    iss = user.get("iss")
    user_email = user.get("email")
    first_logged_in = datetime.utcnow()
    last_accessed = datetime.utcnow()

    user_name = user_info.get("name")
    user_pic = user_info.get("picture")

    print(f'User details: [user_id = {user_id}, user_name = {user_name} ]')

    if iss not in ["https://accounts.google.com", "accounts.google.com"]:
        raise HTTPException(status_code=401, detail="Google authentication failed.")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Google authentication failed.")

    # Create JWT token
    access_token_expires = timedelta(seconds=expires_in)
    access_token = create_access_token(data={"sub": user_id, "user_name": user_name}, expires_delta=access_token_expires)

    session_id = str(uuid.uuid4())

    # Insert user_id in database if not already there
    insert_user(user_id=user_id)

    redirect_url = request.session.pop("login_redirect", "")
    response = RedirectResponse(redirect_url)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # Ensure you're using HTTPS
        samesite="none",  # Set the SameSite attribute to None
    )
    return response

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    # default expiry is 1 hour from expires_delta
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=TOKEN_EXPIRY_IN_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

"""
Check whether logged in user already on database and if not add them
"""
def insert_user(user_id: str):
    with Session(engine) as session:
        users = session.exec(select(Users).filter_by(auth_user_id=user_id)).all()
        if not users:
            user = Users(auth_user_id=user_id)
            session.add(user)
            session.commit()