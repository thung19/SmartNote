from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes import notes

# Creates a FastAPI app object
app = FastAPI(title = "SmartNote")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:3000"],
    allow_credentials = True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
def health():
    return {"ok": True}

# Adds the notes router to the main app
app.include_router(notes.router)