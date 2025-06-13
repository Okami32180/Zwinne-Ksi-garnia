from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from aplikacja import create_app # Import your Flask app factory

# Create the Flask app instance
# Ensure any necessary configurations or context for Flask app creation are handled here
# or within your create_app factory.
flask_app = create_app()

# Create the FastAPI app instance
app = FastAPI(title="Księgarnia Ebooków - Combined API", version="1.0.0")

# Mount the Flask app (WSGI) to the FastAPI app (ASGI)
# All Flask routes will now be available under /flask_app
app.mount("/flask_app", WSGIMiddleware(flask_app))

# Define a simple FastAPI endpoint
@app.get("/api/v1/hello")
async def read_hello():
    return {"message": "Witam FastAPI!"}

@app.get("/")
async def read_root():
    # You could serve a simple welcome page or redirect to /flask_app or /docs
    return {"message": "Polaczenie FastAPI & Flask application. aplikacja Flask jest dostepna pod /flask_app. FastAPI docsy pod adresem /docs."}


# uvicorn main_asgi:app --reload --port 8000
