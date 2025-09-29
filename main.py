from fastapi import FastAPI, Header, HTTPException, Depends, Request, Query
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

@app.get("/home")
def get_response(session: SessionDep, current_user: dict = Depends(get_current_user)):

    auth_user_id = current_user['user_id']
    user = session.exec(select(Users).where(Users.auth_user_id == auth_user_id)).first()

    if user:
        return {"message": "Welcome!", "user": current_user, "user_id": user.id}
    return HTTPException(status_code=500, detail='Not logged in')


# GET - random completed story
@app.get('/random_complete_story/', response_model=StoryPublicWithParts)
def get_random_story(session: SessionDep):
    story = session.exec(select(Story).where(is_not(Story.date_complete, None)).order_by(func.random())).first()

    if not story:
        raise HTTPException(status_code=204, detail='No stories found')
    return story


# GET - a random available part
@app.get('/get_part/', response_model=PartPublicWithStory)
def get_part(session: SessionDep, current_user: dict = Depends(get_current_user)):

    # get the user id from the database using authenticated user_id
    user_id = current_user['user_id']
    user = session.exec(select(Users).where(Users.auth_user_id == user_id)).first()

    # if the user already has a part assigned (not complete) return this
    part = session.exec(select(Part).where(and_(Part.user_id == user.id, is_(Part.date_complete, None)))).first()

    if not part:
        # get a random available part
        part = session.exec(select(Part).where(is_(Part.date_complete, None)).order_by(func.random())).first()
    
        if not part: # no parts currently available so create one
            # can we create a part for an existing story?
            # get the first story with <5 completed parts
            story_id = session.exec(select(Part.story_id).group_by(Part.story_id).having(func.count(Part.story_id) < 5)).first()
            if story_id:
                part_rows = session.exec(select(func.count(Part.story_id)).where(Part.story_id == story_id)).first()
                new_part_number = int(part_rows) + 1

                part = Part(part_number=new_part_number, part_text="", user_id=user.id, story_id=story_id)
                session.add(part)
                session.commit()
            else:
                # All stories have 5 parts so create a new story and a part
                story = Story()
                session.add(story)
                session.commit()

                part = Part(part_number=1, part_text="", user_id=user.id, story_id=story.id)
                session.add(part)
                session.commit()

    return part


# GET - end of previous part
@app.get('/get_previous_part/', response_model=PartPublic)
def get_previous_part(session: SessionDep, current_user: dict = Depends(get_current_user)):

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
    
    # update part from database using request
    db_part = session.get(Part, part_id)
    part_data = part.model_dump(exclude_unset=True)
    part_text = part_data.get("part_text")

    # profanity check
    st = SafeText(language='en')
    text_results = st.check_profanity(text=part_text)
    if text_results:
        status = 418 # I'm a teapot
    else:
        db_part.sqlmodel_update({"part_text": part_text, "date_complete": date_complete})
        session.add(db_part)

    # update the story if necessary
    title_results = []
    if db_part.part_number == 1 or db_part.part_number == 5:
        db_story = session.get(Story, db_part.story_id)
        if db_part.part_number == 1:
            story_title = part_data.get("story_title")

            # profanity check
            title_results = st.check_profanity(text=story_title)
            if title_results:
                status = 418 # I'm a teapot
            else:
                db_story.sqlmodel_update({"title": story_title}) 

        if db_part.part_number == 5:
            db_story.sqlmodel_update({"date_complete": date_complete})

        if not title_results:
            session.add(db_story)

    results = title_results + text_results

    if not results:
        # refresh the session with the saved data and return the part
        session.commit()
        session.refresh(db_part)
        if db_part.part_number == 1 or db_part.part_number == 5:
            session.refresh(db_story)
        status = 200
    
    return {"results": results, "status": status}


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
        status = 418 # I'm a teapot
    else: 
        # get the part we are updating from the database
        db_part = session.get(Part, part_id)

        # get the story we are updating
        db_story = session.get(Story, db_part.story_id)

        # update the part db model with the request data
        db_part.sqlmodel_update({"part_text": part_text})
        session.add(db_part)
        
        # update the story db model with the request data
        # if we are writing the first part of the story
        if story_title is not None:
            db_story.sqlmodel_update({"title": story_title})
            session.add(db_story)
        
        # refresh the session with the saved data and return the part
        session.commit()
        session.refresh(db_part)
        session.refresh(db_story)

        status = 200

    return {"results": results, "status": status}

# GET - a user's stories
@app.get('/my_stories/')
def get_my_stories(session: SessionDep, current_user: dict = Depends(get_current_user)) -> Page[StoryPublicWithParts]:

    # get distinct story_ids from parts by the logged in user
    user_id = current_user['user_id']
    user = session.exec(select(Users).where(Users.auth_user_id == user_id)).first()
    story_ids = session.exec(select(Part.story_id).distinct().where(Part.user_id == user.id))
    
    story_id_list = []
    for story_id in story_ids:
        story_id_list.append(story_id)

    # now get the stories 
    stories = session.exec(
                select(Story).where(and_(is_not(Story.date_complete, None), Story.id.in_(story_id_list)))
                             .order_by(Story.date_complete)
            ).all()

    return paginate(stories)