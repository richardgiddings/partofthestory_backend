from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from pydantic import BaseModel


# Users
class UsersBase(SQLModel):
    auth_user_id:       str

class Users(UsersBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    parts: list["Part"] = Relationship(back_populates="user")


# Story
class StoryBase(SQLModel):
    title:          str | None
    date_complete:  datetime | None

class Story(StoryBase, table=True):
    id:    int = Field(default=None, primary_key=True)
    
    parts: list["Part"] = Relationship(back_populates="story")

class StoryPublic(StoryBase):
    id: int

# Part
class PartBase(SQLModel):
    part_number:    int
    part_text:      str | None
    story_id:       int = Field(foreign_key="story.id")
    user_id:        int | None = Field(default=None, foreign_key="users.id") 
    date_complete:  datetime | None

class Part(PartBase, table=True):
    id:    int = Field(default=None, primary_key=True)
    
    story: Story | None = Relationship(back_populates="parts")
    user:  Users | None = Relationship(back_populates="parts")

class PartPublic(PartBase):
    id: int

class PartUpdate(SQLModel):
    part_text:      str | None
    story_title:    str | None

# Get relationships in return data
class PartPublicWithStory(PartPublic):
    story: StoryPublic | None = None

class StoryPublicWithParts(StoryPublic):
    parts: list[PartPublic] = []

class StoryPublicWithPartsAndCount(BaseModel):
    the_story: StoryPublicWithParts
    count: int
    current_story: int