from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .database import init_db
from .routers import upload, query

# Starlette 0.41.3 enforces file size via class-level attributes on MultiPartParser
# (not __init__ params). Default is 1 MB — override to unlimited for large dump files.
try:
    from starlette.formparsers import MultiPartParser as _MMP
    _MMP.max_file_size = float('inf')
    _MMP.max_part_size = float('inf')
except Exception:
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="PasswordInspector", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(query.router, prefix="/api")

# Serve frontend static files
static_dir = os.path.join(os.path.dirname(__file__), "../../frontend")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
