# A FastAPI backend

This is for a website I have built that enables you to write stories with other users. See the about page on the frontend for more detail.

A backend for the React Router frontend here:
https://github.com/richardgiddings/partofthestory_frontend

Some key features:
- Uses Google authentication for login
- Uses pagination for displaying stories
- Uses a Postgres database
- Uses python-decouple to get config from the environment (e.g. .env file)
- Checks profanity in submitted text using https://pypi.org/project/safetext/
- Setup to deploy to Render

I used this helpful guide to base the authentication on:
https://blog.futuresmart.ai/integrating-google-authentication-with-fastapi-a-step-by-step-guide

## Environment variables

The following environment variables are required:

**Database variables with examples**
- DB_HOST=localhost
- DB_NAME=partofthestory
- DB_USER=postgres
- DB_PASSWORD=postgres
- DB_PORT=5432

**Auth variables**
- SECRET_KEY= Used for registering OAuth
- GOOGLE_CLIENT_ID= Obtained when auth setup with Google
- GOOGLE_CLIENT_SECRET= Obtained when auth setup with Google
- REDIRECT_URL= Backend url plus /auth. End point for authorisation
- JWT_SECRET_KEY= Key to encode and decode access token
- FRONTEND_URL= Frontend url that we redirect to after authorisation
- TOKEN_EXPIRY_IN_MINUTES= Backup for token expiry

- COOKIE_DOMAIN= The front end url
- COOKIE_PATH=/
- COOKIE_SAMESITE=none

**CORS config**
- ALLOWED_ORIGINS= URLs that requests to backend can come from 

**Pagination**
- PAGE_SIZE= How many results per page to display on 'My Stories' page

NOTE: Keys can be generated with a command like:
```
openssl rand -hex 32 
```