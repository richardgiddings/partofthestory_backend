from fastapi import FastAPI, Header, HTTPException, Depends, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from sqlalchemy import func, and_, or_
from sqlalchemy.sql.operators import is_not, is_
from starlette import status
from decouple import config
import time
import datetime

# pagination
from fastapi_pagination import add_pagination, paginate
from fastapi_pagination.links import Page as BasePage
from fastapi_pagination.customization import UseParamsFields, CustomizedPage
from fastapi_pagination.utils import disable_installed_extensions_check

from models import *
from auth import *
from database import SessionDep, get_session, create_db_and_tables

# profanity checker
# https://pypi.org/project/safetext/
from safetext import SafeText


# CORS middleware
ALLOWED_ORIGINS = config("ALLOWED_ORIGINS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # set this once we are no longer testing locally
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add Session middleware
app.add_middleware(SessionMiddleware, secret_key=config("SECRET_KEY"))

# Pagination
PAGE_SIZE = config("PAGE_SIZE")
Page = CustomizedPage[
    BasePage,
    UseParamsFields(
        size=Query(PAGE_SIZE, ge=0),
    ),
]
add_pagination(app)


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


@app.get("/user")
def get_user(session: SessionDep, current_user: dict = Depends(get_current_user)):

    auth_user_id = current_user['user_id']
    user = session.exec(select(Users).where(Users.auth_user_id == auth_user_id)).first()

    return {"user": current_user, "user_id": user.id}


# GET - random completed story
@app.get('/random_complete_story/', response_model=StoryPublicWithParts)
def get_random_story(session: SessionDep):
    story = session.exec(select(Story).where(is_not(Story.date_complete, None)).order_by(func.random())).first()

    if not story:
        raise HTTPException(status_code=204, detail='No stories found')
    return story


# GET - a random available part
@app.get('/get_part/', response_model=PartPublicWithStory)
def get_part(
        session: SessionDep, 
        current_user: dict = Depends(get_current_user_with_refresh), 
        response: Response = None
    ):

    # get the user id from the database using authenticated user_id
    user_id = current_user['user_id']
    user = session.exec(select(Users).where(Users.auth_user_id == user_id)).first()

    # if the user already has a part assigned (not complete) return this
    part = session.exec(select(Part).where(and_(Part.user_id == user.id, is_(Part.date_complete, None)))).first()

    if not part:
        # try to get a random unassigned part
        part = session.exec(select(Part).where(and_(is_(Part.date_complete, None),is_(Part.user_id, None))).order_by(func.random())).first()
        if part:
            # assign the part to the user
            part.user_id = user.id
            part.date_started = datetime.now()
            session.add(part)

            # lock the story the part belongs to
            story = session.get(Story, part.story_id)
            story.locked = True
            session.add(story)

            session.commit()

            print("Assigned existing part to user")
        else:
            # no available parts so create one
            # try to get a random story that is not locked
            story_id = session.exec(select(Story.id).where(is_(Story.locked, False)).order_by(func.random())).first()
            if story_id:
                part_rows = session.exec(select(func.count(Part.story_id)).where(Part.story_id == story_id)).first()
                new_part_number = int(part_rows) + 1
                part = Part(part_number=new_part_number, part_text="", user_id=user.id, story_id=story_id, date_started=datetime.now())
                session.add(part)

                story = session.get(Story, story_id)
                story.locked = True
                session.add(story)

                session.commit()

                print("Created new part for existing story and assigned to user")
            else:
                # All stories have 5 parts so create a new story and a part
                story = Story(title="", locked=True)
                session.add(story)
                session.commit()

                part = Part(part_number=1, part_text="", user_id=user.id, story_id=story.id, date_started=datetime.now())
                session.add(part)
                session.commit()

                print("Created new story and part and assigned to user")

    # Set new access token in cookie
    access_token = current_user['access_token']
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        domain=config("COOKIE_DOMAIN"),
        path=config("COOKIE_PATH"),
        secure=True,  # Ensure you're using HTTPS
        samesite=config("COOKIE_SAMESITE"),  # Set the SameSite attribute to None
    )

    return part


# GET - end of previous part
@app.get('/get_previous_part/', response_model=PartPublic)
def get_previous_part(session: SessionDep, current_user: dict = Depends(get_current_user)):

    # aside: we could use part_number and story_id as parameters then just use the last query
    # but this opens up people being able to see any story through urls

    # get the part assigned to the user 
    user_id = current_user['user_id']
    user = session.exec(select(Users).where(Users.auth_user_id == user_id)).first()
    part = session.exec(select(Part).where(and_(Part.user_id == user.id, is_(Part.date_complete, None)))).first()

    # get the previous part
    prev_part_number = part.part_number - 1
    story_id = part.story_id
    prev_part = session.exec(select(Part).where(and_(Part.story_id == story_id, Part.part_number == prev_part_number))).first()

    return prev_part


# PATCH - submit a completed part (pending moderation)
@app.patch("/complete_part/{part_id}")
def complete_part(part_id: int, part: PartUpdate, session: SessionDep, current_user: dict = Depends(get_current_user)):

    date_complete = datetime.now()
    
    # get part from request
    part_data = part.model_dump(exclude_unset=True)
    part_text = part_data.get("part_text")

    # get part from database
    db_part = session.get(Part, part_id)

    # profanity check for part_text
    st = SafeText(language='en')
    text_results = st.check_profanity(text=part_text)
    if text_results:
        return {"results": text_results, "status": 400}
    db_part.sqlmodel_update({"part_text": part_text, "date_complete": date_complete})

    # update the story if necessary
    title_results = []
    db_story = session.get(Story, db_part.story_id)

    if db_part.part_number == 1:
        story_title = part_data.get("story_title")

        # profanity check on story title
        title_results = st.check_profanity(text=story_title)
        if title_results:
            return {"results": title_results, "status": 400}
        db_story.sqlmodel_update({"title": story_title})

    if db_part.part_number == 5:
        db_story.sqlmodel_update({"date_complete": date_complete})

     # unlock the story for someone else to write the next part
    if db_part.part_number != 5:
        db_story.sqlmodel_update({"locked": False})

    if not title_results:
        session.add(db_part)
        session.add(db_story)
        session.commit()
    
    return {"results": title_results, "status": 200}


# PATCH - save a part so you can come back to it (not complete)
@app.patch("/save_part/{part_id}")
def save_part(part_id: int, part: PartUpdate, session: SessionDep, current_user: dict = Depends(get_current_user)):

    # get the data from the request
    part_data = part.model_dump(exclude_unset=True)
    part_text = part_data.get("part_text")
    story_title = part_data.get("story_title")

    # profanity check
    st = SafeText(language='en')
    title_results = []
    if story_title:
        title_results = st.check_profanity(text=story_title)
    text_results = st.check_profanity(text=part_text)
    results = title_results + text_results

    if results:
        status = 400 # Bad Request
    else: 
        # get the part and story we are updating from the database
        # and update

        db_part = session.get(Part, part_id)
        db_story = session.get(Story, db_part.story_id)

        db_part.sqlmodel_update({"part_text": part_text})
        session.add(db_part)
        
        if story_title is not None:
            db_story.sqlmodel_update({"title": story_title})
            session.add(db_story)
        
        session.commit()
        status = 200

    return {"results": results, "status": status}

# GET - a user's stories
@app.get('/my_stories/')
def get_my_stories(
        session: SessionDep, 
        current_user: dict = Depends(get_current_user_with_refresh), 
        response: Response = None
    ) -> Page[StoryPublicWithParts]:

    # get distinct story_ids from parts by the logged in user
    user_id = current_user['user_id']
    user = session.exec(select(Users).where(Users.auth_user_id == user_id)).first()
    story_ids = session.exec(select(Part.story_id).distinct().where(Part.user_id == user.id)).all()

    # now get the stories 
    stories = session.exec(
                select(Story).where(and_(is_not(Story.date_complete, None), Story.id.in_(story_ids)))
                             .order_by(Story.date_complete)
            ).all()

    # Set new access token in cookie
    access_token = current_user['access_token']
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        domain=config("COOKIE_DOMAIN"),
        path=config("COOKIE_PATH"),
        secure=True,  # Ensure you're using HTTPS
        samesite=config("COOKIE_SAMESITE"),  # Set the SameSite attribute to None
    )

    return paginate(stories)