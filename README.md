# A FastAPI backend

This is for a website I have built that enables you to write stories with other users. See the about page on the frontend for more detail.

A backend for the React Router frontend here:
https://github.com/richardgiddings/partofthestory_frontend

Some key features:
- Uses Google authentication for login
- Uses pagination for displaying stories
- Uses a Postgres database
- Uses python-decouple to get config from the environment (e.g. .env file)
- Setup to deploy to Render