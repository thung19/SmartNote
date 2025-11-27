from fastapi import FastAPI
from app.routes import notes

# Creates a FastAPI app object
app = FastAPI(title = "SmartNote")

# Health check endpoint
@app.get("/health")
def health():
    return {"ok": True}

# Adds the notes router to the main app
app.include_router(notes.router)