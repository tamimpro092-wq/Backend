from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .logging_json import configure_json_logging
from .settings import settings
from .db import init_db
from .api.router import api_router

configure_json_logging(settings.LOG_LEVEL)
logger = logging.getLogger("app")

app = FastAPI(title="Overnight E-commerce Autopilot (JARVIS Mode)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info(
        "startup_complete",
        extra={"extra": {"db": settings.DATABASE_PATH, "dry_run": bool(settings.DRY_RUN)}},
    )


app.include_router(api_router)


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")


if __name__ == "__main__":
    run()
