from fastapi import APIRouter

# Create API router instance
router = APIRouter(prefix="/notes", tags=["notes"])