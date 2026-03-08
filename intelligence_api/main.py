import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from fastapi import FastAPI
from contextlib import asynccontextmanager
from intelligence_api.presentation import router
from intelligence_api.presentation.chat_router import chat_router
from intelligence_api.core.config import settings
from intelligence_api.scheduler import start_scheduler
from intelligence_api.subscriber import start_subscriber

_scheduler = None
_subscriber_future = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global _scheduler, _subscriber_future
    _scheduler = start_scheduler()
    _subscriber_future = start_subscriber()
    yield
    # Shutdown
    if _scheduler:
        _scheduler.shutdown()
    if _subscriber_future:
        _subscriber_future.cancel()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Omnisight Intelligence API", lifespan=lifespan)

# Add CORS middleware to allow the UI to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router.router)
app.include_router(chat_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
