from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime


# Story
class StoryBase(SQLModel):
    title:          str
    complete:       bool
    date_complete:  datetime

class Story(StoryBase, table=True):
    id: int = Field(default=None, primary_key=True)

    parts: list["Part"] = Relationship(back_populates="story")

class StoryPublic(StoryBase):
    id: int


# Part
class PartBase(SQLModel):
    part_number:    int
    part_text:      str
    available:      bool
    story_id:       int = Field(foreign_key="story.id")
    date_complete:  datetime

class Part(PartBase, table=True):
    id: int = Field(default=None, primary_key=True)
    
    story: Story | None = Relationship(back_populates="parts")

    users: list["Users"] = Relationship(back_populates="part")

class PartPublic(PartBase):
    id: int


# Users
class UsersBase(SQLModel):
    user_id:            str
    part_assigned:      int = Field(foreign_key="part.id")

class Users(UsersBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    # Foreign Key 
    part: Part | None = Relationship(back_populates="users")