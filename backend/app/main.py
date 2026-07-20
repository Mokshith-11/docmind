"""FastAPI application entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .ratelimit import limiter
from .routers import billing, chat, documents, health, metrics, workspaces

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="DocMind API", version="0.7.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_origins = list({settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"})
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "docmind-api", "docs": "/docs"}
