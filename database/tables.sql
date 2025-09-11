BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS story (
    id              SERIAL PRIMARY KEY,
    title           text CONSTRAINT title_chk CHECK (length(title) <= 50),
    complete        boolean DEFAULT FALSE,
    date_complete   timestamp
);

CREATE TABLE IF NOT EXISTS part (
    id              SERIAL PRIMARY KEY,
    part_number     integer,
    part_text       text CONSTRAINT part_text_chk CHECK (length(part_text) <= 500),
    available       boolean DEFAULT TRUE,
    story_id        integer REFERENCES story (id),
    date_complete   timestamp
);

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    user_id         text,
    part_assigned   integer REFERENCES part (id)
);

END TRANSACTION;