BEGIN TRANSACTION;

/*
    Table:           users
    Purpose:         Stores user information
    Columns:
    - id:            SERIAL PRIMARY KEY
    - auth_user_id:  Google authentication user ID
    - refresh_token: Refresh token from Google
*/
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    auth_user_id    text,
    refresh_token   text
);


/*
    Table:           story
    Purpose:         Stores story information
    Columns:
    - id:            SERIAL PRIMARY KEY
    - title:         Title of the story
    - date_complete: When the story was completed
    - locked:        Whether the story is locked for editing
    - last_user_id:  ID of the last user who contributed to the story
*/
CREATE TABLE IF NOT EXISTS story (
    id              SERIAL PRIMARY KEY,
    title           text CONSTRAINT title_chk CHECK (length(title) <= 50),
    date_complete   timestamp,
    locked          boolean DEFAULT false,
    last_user_id    integer
);


/*
    Table:           part
    Purpose:         Stores parts of stories
    Columns:
    - id:            SERIAL PRIMARY KEY
    - part_number:   The part number within the story (1-5)
    - part_text:     The text content of the part
    - story_id:      Foreign key referencing the story table
    - user_id:       Foreign key referencing the users table
    - date_started:  When the part was started
    - date_complete: When the part was completed
*/
CREATE TABLE IF NOT EXISTS part (
    id              SERIAL PRIMARY KEY,
    part_number     integer,
    part_text       text CONSTRAINT part_text_chk CHECK (length(part_text) <= 1000),
    story_id        integer REFERENCES story (id),
    user_id         integer REFERENCES users (id),
    date_started    timestamp,
    date_complete   timestamp
);

END TRANSACTION;