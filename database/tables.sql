BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    auth_user_id    text,
    refresh_token   text
);

CREATE TABLE IF NOT EXISTS story (
    id              SERIAL PRIMARY KEY,
    title           text CONSTRAINT title_chk CHECK (length(title) <= 50),
    date_complete   timestamp,
    locked          boolean DEFAULT false
);

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