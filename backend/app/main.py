from fastapi import FastAPI
from app.routes import notes
    
app = FastAPI(title = "SmartNote")
@app.get("/health")
def health():
    return {"ok": True}

app.include_router(notes.router)