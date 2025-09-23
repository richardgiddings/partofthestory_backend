from sqlalchemy import create_engine
from typing import Annotated
from sqlmodel import Session, SQLModel
from fastapi import Depends
from decouple import config


# Database config from env
DB_HOST     = config('DB_HOST')
DB_NAME     = config('DB_NAME')
DB_USER     = config('DB_USER')
DB_PASSWORD = config('DB_PASSWORD')
DB_PORT     = config('DB_PORT')

SQLALCHEMY_DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]